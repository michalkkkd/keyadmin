# Antitamper obudowy, tryby EM i bateria (zapis debaty z 2026-11-03)

Ten plik zbiera ustalenia z rozmowy o tym, czy dongle wykrywa otwarcie obudowy, gdy śpi. Służy do powrotu do tematu (także z AI). Stan opisany poniżej dotyczy repozytoriów KeyFirmware i KeySec z 2026-11-03. Nic z tego nie jest jeszcze zacommitowane.

## 1. Stan sprzętu i firmware

| | Sprzęt (wg kolegi) | Firmware (`src/core/tamper_simulation.c:14-17`) |
| :--- | :--- | :--- |
| Wejście tamper 1 | D5 = **PC05** | PC5 (zgodne) |
| Wejście tamper 2 | D0 = **PC00** | **PC6** (D6, nic nie podpięte) |

* **Błąd:** firmware pilnuje PC6 zamiast PC0, więc przerwanie obwodu na D0 nie jest wykrywane w żadnym trybie.
* Mapowanie pinów XIAO MG24: `KeyFirmware/xiao_pins.txt` (D0 = PC0, D5 = PC5, D6 = PC6).
* Konfiguracja wejść: `SL_GPIO_MODE_INPUT_PULL_FILTER` z pull-upem, zwykłe przerwanie GPIO na oba zbocza (`sl_gpio_configure_external_interrupt`). Zdarzenie trafia do `nsc_tamper_manager_detected()` (Secure).
* **Próg wipe:**
  * było: 3 zbocza na pin w ciągu jednego startu, a liczniki zerują się przy każdym starcie (`tamper_manager.c:127-128`). Jedno otwarcie (1–2 zbocza) dawało wpis w logu, ale bez wipe;
  * decyzja: **jedno otwarcie lub przerwanie obwodu = wipe**. Próg 1 dla `TAMPER_TYPE_PHYSICAL_PIN1/PIN2` jest już w źródle (`tamper_manager.c:32-33`, backup `backup/src_core/tamper_manager.c__20261103_212108`), ale nie jest zbudowany ani wgrany.
* **Rodzaj wipe:**
  * `KEYFIRMWARE_TAMPER_LIVE_WIPE` domyślnie OFF (`cmake_gcc/CMakeLists.txt:106`, `flashbat/compile.bat:31`): kasowane jest tylko NVM3 (licencja, zegar, tożsamość, certyfikat), kod zostaje, dongle wymaga ponownego provisioningu;
  * ON: kasowany cały układ.
* Fizyczne skasowanie NVM3 sprawdzone na donglu (zrzut flash przez SWD, `KeySec/temp/nvm3_dump.py`): 4425 → 60 niepustych bajtów (same nagłówki stron), 0 kopii zegara i licencji. Klucz tożsamości zostaje w pamięci podręcznej PSA w RAM do resetu.
* Tamper log leży na stronie User Data (`0x0FE00000`), poza NVM3, więc z kodu wynika, że przetrwa wipe. **Na sprzęcie nie jest to jeszcze sprawdzone**, bo log był pusty przed i po wipe.

## 2. Tryby EM a wykrywanie zmiany na pinie

Źródła (Silicon Labs, przez MCP `silabs-knowledge-base`):
* **Reference manual EFR32xG24, 24.3.10.1:** „In EM2 and EM3, only signals on Port A and Port B are available as standard interrupts. Standard interrupts are available to all pins in EM0 and EM1.”
* **Datasheet EFR32MG24, 3.3:** piny portów A i B są „EM2 capable”, piny portów C i D są w EM2 tylko zatrzaskiwane w obecnym stanie.
* **Reference manual EFR32xG24, 24.3.10.2:** „any of the dedicated EM4WU (EM4 wake-up) signals on PA, PB, PC or PD may be used to generate edge-sensitive interrupts in EM0, EM1, EM2, and EM3.”
  * Tabela 24.2: przy `EM4WUEN = 1` i `EM4WUIEN = 1` pin budzi z EM1, EM2, EM3 i EM4 oraz daje przerwanie w EM0–EM3.
  * Kierunek wybiera się w `GPIO_EM4WUPOL` (0 = zbocze opadające, 1 = narastające): **tylko jeden kierunek na pin**.
* **Datasheet EFR32MG24, tabela 6.5 (nasz układ EFR32MG24B220F1536IM48):** **PC00 = EM4WU6**, **PC05 = EM4WU7**. PC06 nie ma EM4WU. Pozostałe piny EM4WU: PA05, PB01, PB03, PC07, PD02, PD05.
* Forum Silicon Labs, odpowiedzi pracowników: porty C i D nie są taktowane poniżej EM1, a obejściem są piny EM4WU.

| Tryb | Pobór (datasheet) | Zwykłe przerwanie na PC00/PC05 | Przerwanie EM4WU na PC00/PC05 | Pin z portu A/B |
| :--- | :--- | :--- | :--- | :--- |
| EM0 (praca) | kilka mA | ✅ | ✅ | ✅ |
| EM1 (sleep) | ok. 1–3 mA (rdzeń 24,4 µA/MHz × 39 MHz ≈ 0,95 mA) | ✅ | ✅ | ✅ |
| EM2 (deep sleep) | ok. 4,2 µA | ❌ | ✅ | ✅ |
| EM3 (stop) | ok. 3,9 µA | ❌ | ✅ | ✅ |
| EM4 (shutoff) | ok. 0,3–0,6 µA, RAM i SYSRTC tracone, wybudzenie = reset | ❌ | tylko budzi resetem | tylko piny EM4WU |

**Wyjaśnienie nieporozumienia:** „EM4WU” to tylko nazwa układu budzenia podpiętego do tych pinów. Działa on w EM3 i **nie wymaga używania trybu EM4**. Trybu EM4 nie używamy, bo traci zegar licencji.

## 3. Jak dongle dziś śpi

* `app.c`:
  * w trybie pracy (Compass podłączony, heartbeat co 3 s) obowiązuje wymaganie EM1;
  * po utracie heartbeatu (`INACTIVITY_TIMEOUT_MS` 4500 ms, potem `HEARTBEAT_LOST_LED_MS` 3000 ms) `heartbeat_lost_timer_callback` zdejmuje wymaganie EM1 (`app.c:54`) i loguje „Entering EM3 sleep”;
  * budzi go zegar co 30 s (`RTC_WAKEUP_MS`) dla zegara licencji.
* **Faktycznie to EM2, nie EM3:** menedżer zasilania z SDK w tym projekcie nigdy nie schodzi niżej niż EM2 (`simplicity_sdk_2026.6.1/.../power_manager/src/sleep_loop/sl_power_manager.c:775`, `get_lowest_em()` zwraca najwyżej `SL_POWER_MANAGER_EM2`). Napis „EM3” w logu jest mylący.
* **Użytkownik chce EM3.** Uwaga na przyszłość: w prawdziwym EM3 zatrzymują się LFRCO i LFXO. Zegar licencji to SYSRTC taktowany z LFRCO (`config/sl_clock_manager_tree_config.h:79`, kontrola źródła w `security_rtc.c:55-57`). W EM3 przestałby więc liczyć czas, a budzenie co 30 s by nie działało. Dla antitamper przez EM4WU nie ma różnicy między EM2 i EM3.
* Skutek obecnego kodu: gdy Compass nie działa, dongle śpi, a zwykłe przerwania na PC00/PC05 nie działają. **Otwarcie obudowy w tym czasie nie jest wykrywane.** Nie ma też odczytu stanu pinów przy starcie ani po wybudzeniu.

## 4. Bateria

* Założenie: bateria na 5 lat. Odpięcie baterii wymaga otwarcia obudowy.
* 5 lat jest możliwe tylko przy śnie EM2/EM3 (ok. 4 µA). W EM1 (bez uśpienia) pobór jest ok. 250 razy większy, więc odłączony od USB dongle rozładuje baterię w dni albo tygodnie, a potem traci zegar i licencję.
* Wniosek: wyłączenie uśpienia odrzucone. Dongle śpi, a antitamper musi działać w uśpieniu.
* **Prąd pull-upu:** wewnętrzny pull-up GPIO to 35–55 kΩ, typowo 44 kΩ (datasheet, tabela 4.31).
  * Jeśli nienaruszony obwód zwiera pin do GND, płynie ok. 3 V / 44 kΩ ≈ **68 µA na pin**, dla dwóch pinów ok. 136 µA, czyli kilkadziesiąt razy więcej niż całe EM2.
  * Na 5 lat trzeba wtedy zewnętrznego rezystora rzędu MΩ (wewnętrzny pull-up wyłączony) albo układu, w którym stan nienaruszony nie przewodzi prądu.
  * Schematu nie sprawdzono.

## 5. Rozważone warianty

| Wariant | Detekcja w uśpieniu | Bateria | Zmiana sprzętu | Status |
| :--- | :--- | :--- | :--- | :--- |
| A. Wyłączyć uśpienie (stałe EM1) | ✅ | dni lub tygodnie | nie | odrzucony |
| B. Przepiąć tamper na piny portu A/B (XIAO: D8 = PA3, D9 = PA4, D10 = PA5; pady D13 = PB2, D14 = PB3, D15 = PB0, D16 = PB1, D17 = PA0) | ✅, oba zbocza | bez zmian | tak | niepotrzebny, bo PC00/PC05 są pinami EM4WU |
| **C. Przerwania EM4WU na PC00 (EM4WU6) i PC05 (EM4WU7)** | ✅ w EM0–EM3, jeden kierunek | bez zmian | nie | **wybrany kierunek** |
| D. Odczyt stanu pinów przy starcie i przy każdym wybudzeniu co 30 s | z opóźnieniem do 30 s | bez zmian | nie | jako zabezpieczenie zapasowe do C |

## 6. Plan (nie zrobione)

1. `tamper_simulation.c`: drugi pin z PC6 na **PC0**.
2. Oba piny jako przerwania EM4WU: `sl_gpio_configure_wakeup_em4_interrupt()` (`sl_gpio.h:387`), kierunek „obwód przerwany”.
   * Dokumentacja SDK nazywa to „level-sensitive”, a reference manual „edge-sensitive”. Trzeba sprawdzić na sprzęcie.
3. Próg 1 dla pinów fizycznych (już w źródle).
4. Odczyt stanu obu pinów przy starcie i przy budzeniu co 30 s.
5. Poprawić napis „EM3” w logu `app.c` na właściwy tryb.
6. Build (`flashbat/compile.bat`), wgranie, test na donglu:
   * zworki D0/D5 w stanie „obudowa zamknięta”;
   * odłączyć Compass (brak heartbeatu, dongle śpi);
   * zdjąć zworkę: oczekiwany wipe;
   * sprawdzić, że wpis w tamper logu przetrwał (`KeySec/temp/userdata_dump.py`, `run_customer_diag.py` + `decode_diag_payload.py`);
   * ponowny provisioning (`provision_dongle.py 365 3 --skip-compile`, bez `--lock`).

## 7. Otwarte pytania

* **Jaki stan jest na D0/D5 przy zamkniętej obudowie: niski (do GND) czy wysoki (do 3V3)?** Od tego zależy kierunek EM4WU i odczyt stanu przy starcie.
* Jak zrobione jest podciąganie na płytce (wewnętrzny pull-up czy zewnętrzny rezystor)? Ma to wpływ na baterię (punkt 4).
* Czy produkcja ma używać `TAMPER_LIVE_WIPE=ON` (kasowanie całego układu), czy wystarczy kasowanie NVM3?
* Czy na pewno EM3? Prawdziwe EM3 zatrzymuje zegar licencji (punkt 3); dziś dongle i tak śpi w EM2.

## 8. Pliki

* Firmware:
  * `KeyFirmware/src/core/tamper_simulation.c` (piny, przerwania);
  * `KeyFirmware/src/core/tamper_manager.c` (progi, log, wipe);
  * `KeyFirmware/app.c` (uśpienie);
  * `KeyFirmware/src/core/security_rtc.c` (zegar licencji);
  * `KeyFirmware/src/core/security_nvm.c` (`security_nvm_wipe_all`).
* Skrypty testowe:
  * `KeySec/temp/nvm3_dump.py`, `userdata_dump.py` (zrzuty przez SWD);
  * `tamper_entry.py` (wpis VRX_SHORT z PC);
  * `admin_wipe.py`;
  * `dongle_state.py`.
* Powiązane dokumenty: `KeySec/docs/security/antitamper.md`, `KeySec/docs/security/time_license_mechanism.md`.
