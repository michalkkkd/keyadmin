# Antitamper obudowy, tryby EM, bateria i zegar licencji (debata 2026-11-03 i 2026-11-04)

Ten plik zbiera ustalenia z rozmów o tym, jak dongle (Seeed XIAO MG24, EFR32MG24B220F1536IM48) śpi na baterii, czy wtedy wykrywa otwarcie obudowy i jak liczy czas licencji. Służy do kontynuowania tematu z innym AI. Stan: repozytoria KeyFirmware i KeySec z 2026-11-04 wieczorem. **Nic nie jest zacommitowane. Najnowszy firmware jest zbudowany, ale nie wgrany na dongle.**

## 0. Podsumowanie dla kolejnego AI (czytaj najpierw)

### Decyzje użytkownika (nie podważać)
* Bateria jest **zawsze podpięta**, USB ją ładuje. Oszczędzać trzeba w czasie, gdy dongle nie jest w USB.
* **Jedno otwarcie obudowy = wipe** (próg 1, już w źródle).
* **Nie dokładamy na płytce rezystorów, dzielników ani innych elementów.** Kolega przylutował tylko druciki do D0 i D5; przy otwarciu obudowy drucik się zrywa.
* Błąd zegara licencji ±3 % na rok (LFRCO bez trybu precision) jest **akceptowalny**.
* Bluetooth **usunięty całkowicie** z KeyFirmware (zrobione 2026-11-04, nie wgrane).
* Własny kod usypiania z **ominięciem menedżera zasilania SDK (prawdziwe EM3) odrzucony całkowicie**.
* Przeniesienie SYSRTC/LFRCO/CMU do świata Secure **odłożone** (dziś świat Non-Secure mógłby zamrozić zegar licencji).

### Do wyboru przez użytkownika (otwarte)
* **Rekomendacja: EM2 + SYSRTC na LFXO + odczyt antitamper impulsowy.** Działa bez zmian sprzętu, budzi się z USB, ok. 10–14 mies. na baterii, zegar ok. ±26 min/rok.
* Alternatywa: EM4 + BURTC na LFXO. Wymaga jednego dodatkowego drucika (PA09 na wolny pin EM4WU) i opłaca się tylko przy styku antitamper, który przy zamkniętej obudowie nie przewodzi prądu. Przy drucikach zrywanych daje ok. 6 tygodni, czyli gorzej niż EM2.

### Najważniejsze odkrycia
1. **Bateria padła po ok. 6 h od odpięcia USB** (noc 2026-11-03/04). Przyczyna: strumień UART (`config/sl_iostream_eusart_Io_Stream_USERT_config.h`, `RESTRICT_ENERGY_MODE_TO_ALLOW_RECEPTION 1`) trzymał wymaganie EM1 przez cały czas, więc dongle nigdy nie zszedł do EM2 (średnio 8,6–12 mA). Poprawione na 0, zbudowane, nie wgrane.
2. **Zegar licencji nie liczy bez zasilania.** Przez 9 h 42 min martwej baterii stał; po starcie wznowił z ostatniego zapisu NVM3 + 150 s, więc licencja „zyskała” 9,5 h. Firmware produkcyjny nigdy nie przesuwa zegara do przodu z czasu PC (propozycja: korekta tylko do przodu, jeszcze nie zrobiona).
3. **Drucik antitamper zrywany przy otwarciu bierze prąd cały czas**, dopóki obudowa jest zamknięta: wewnętrzny pull-up (35–55 kΩ, typ. 44 kΩ) do 3,3 V, drucik do masy, ok. **75 µA na pętlę** (sam drucik rozładowuje 85 mAh w ok. 47 dni, dwie pętle ok. 24 dni). Obejście bez rezystorów: **odczyt impulsowy** (co ok. 1 s włączyć pull-up na kilka µs, odczytać, wyłączyć): ok. 0,1–0,3 µA, opóźnienie wykrycia do 1 s. **Działa tylko w EM2**, bo w EM4 każde wybudzenie to pełny restart.
4. **Kwarc LFXO 32,768 kHz na płytce jest:** oficjalna definicja płytki w Zephyrze (`boards/seeed/xiao_mg24/xiao_mg24.dts`) ma `&lfxo` ze `status = "okay"`, `ctune = <44>`, `precision = <50>`, a SYSRTC jest tam taktowany z LFXO. Piny kwarcu to PD00/PD01 (datasheet, tabela 6.5); mapa pinów Silicon Labs Arduino (`KeyFirmware/variant.txt`) ich nie używa. U nas `SL_CLOCK_MANAGER_LFXO_EN 0` i `CTUNE 63`; przy włączeniu ustawić CTUNE 44. Serwery MCP Silicon Labs mają dane procesora, ale nie płytki Seeed.
5. **Prawdziwe EM3 jest u nas niemożliwe:** menedżer zasilania SDK schodzi najwyżej do EM2 (`simplicity_sdk_2026.6.1/platform_core/platform/service/power_manager/src/sleep_loop/sl_power_manager.c:775-785` i assert w linii 434), a w EM3 LFRCO i LFXO są zatrzymane (RM 12.3.1.5, s. 295; tabela 8.1, s. 161). Napis „EM3” w starym logu był błędny; dongle śpi w EM2.
6. **5 lat na tej baterii (LiPo 85 mAh, Akyga LP301525) jest niemożliwe** nawet bez obciążenia: samorozładowanie LiPo z układem zabezpieczającym ok. 2–5 %/mies., czyli stały pobór 2,4–5,9 µA.

## 1. Stan sprzętu i firmware antitamper

| | Sprzęt (wg kolegi) | Firmware (`KeyFirmware/src/core/tamper_simulation.c:14-17`) |
| :--- | :--- | :--- |
| Wejście tamper 1 | D5 = **PC05** (EM4WU7) | PC5 (zgodne) |
| Wejście tamper 2 | D0 = **PC00** (EM4WU6) | **PC6** (D6, nic nie podpięte; PC06 nie ma EM4WU) |

* **Błąd:** firmware pilnuje PC6 zamiast PC0.
* Wejścia: `SL_GPIO_MODE_INPUT_PULL_FILTER` z pull-upem, zwykłe przerwanie GPIO na oba zbocza. **Zwykłe przerwania portów C/D nie działają w EM2/EM3** (RM 24.3.10.1), więc dziś w uśpieniu otwarcie nie jest wykrywane.
* **Jak kolega podłączył druciki: nie wiadomo** (D0 do GND i D5 do GND, czy D0 z D5). Sprawdzić multimetrem przy zamkniętej obudowie: opór D0–GND i D0–D5. Bliski 0 Ω oznacza drut normalnie zamknięty (patrz odkrycie 3). Przy D0–D5 firmware musi jeden pin ustawić jako wyjście w stanie niskim, inaczej zerwanie niczego nie zmieni.
* **Próg wipe:** 1 dla `TAMPER_TYPE_PHYSICAL_PIN1/PIN2` (`tamper_manager.c:32-33`).
* **Rodzaj wipe:** `KEYFIRMWARE_TAMPER_LIVE_WIPE` domyślnie OFF: kasowane jest tylko NVM3 (licencja, zegar, tożsamość, certyfikat), potem potrzebny ponowny provisioning. ON: kasowany cały układ.
* Fizyczne skasowanie NVM3 sprawdzone przez SWD (`KeySec/temp/nvm3_dump.py`): 4425 → 60 niepustych bajtów.
* Tamper log leży na stronie User Data (`0x0FE00000`), poza NVM3. Że przetrwa wipe, wynika z kodu; **na sprzęcie niesprawdzone**.

## 2. Tryby EM a wykrywanie zmiany na pinie

Źródła (MCP `silabs-knowledge-base`):
* RM EFR32xG24 24.3.10.1: w EM2 i EM3 zwykłe przerwania mają tylko porty A i B.
* RM EFR32xG24 24.3.10.2 i tabela 24.2: piny EM4WU dają przerwanie w EM0–EM3 i budzą z EM4 (`EM4WUEN`, `EM4WUIEN`, kierunek w `GPIO_EM4WUPOL`, jeden kierunek na pin).
* Datasheet EFR32MG24 tabela 6.5 (s. 115): EM4WU0 = PA05, EM4WU3 = PB01, EM4WU4 = PB03, **EM4WU6 = PC00**, **EM4WU7 = PC05**, EM4WU8 = PC07, EM4WU9 = PD02, EM4WU10 = PD05. **PA09 (odbiór UART z hosta) nie jest pinem EM4WU.**
* RM 12.3.1.6 (EM4, s. 295): nie ma retencji poza stanem pinów i BURAM; wybudzenie = reset; w EM4 działa tylko BURTC (na LFRCO, LFXO lub ULFRCO); budzą BURTC, reset, POR i piny EM4WU.
* RM 24.3.7 (s. 812): bez ustawienia `EM4IORETMODE` piny w EM4 wracają do stanu po resecie (znikają pull-upy). EM4EXIT trzyma stan pinów w EM4. U nas `SL_POWER_MANAGER_INIT_EMU_EM4_PIN_RETENTION_MODE` = DISABLE.
* RM 16.2 (BURTC, s. 457): „Reset only by External Pin and Power-On Resets”, czyli reset programowy, watchdog i wybudzenie z EM4 go nie zerują.

| Tryb | Prąd MCU (datasheet tab. 4.5, s. 30) | Zwykłe przerwanie PC00/PC05 | EM4WU na PC00/PC05 | Port A (PA09 od hosta) |
| :--- | :--- | :--- | :--- | :--- |
| EM0 | kilka mA | ✅ | ✅ | ✅ |
| EM1 | 22,6 µA/MHz (DCDC) | ✅ | ✅ | ✅ |
| EM2 | 2,9 µA (256 kB RAM), 1,3 µA (16 kB) | ❌ | ✅ | ✅ |
| EM3 | 2,7 µA; LFRCO/LFXO zatrzymane; u nas niedostępny | ❌ | ✅ | ✅ |
| EM4 | 0,25 µA, z BURTC na LFXO 0,64 µA; wybudzenie = reset | ❌ | budzi resetem | ❌ |

## 3. Jak dongle śpi (firmware po zmianach z 2026-11-04, zbudowany, nie wgrany)

* `app.c`: przy heartbeacie z Compass (co 3 s) firmware trzyma wymaganie EM1. Po utracie heartbeatu (4500 ms, potem 3000 ms świecenia LED) zdejmuje je i loguje „Sleeping (EM2 allowed)”.
* **Nowe:**
  * blokada EM1 w UART zdjęta (`RESTRICT_ENERGY_MODE_TO_ALLOW_RECEPTION 0`);
  * po resecie bez hosta sen włącza się po 60 s (`BOOT_SLEEP_GRACE_MS`); wcześniej bez pierwszego heartbeatu dongle nie zasypiał nigdy;
  * `src/core/power_stats.c` liczy sekundy w EM0/EM1/EM2 i liczbę wejść w EM2 (rekord DIAG v7, linia „Energy modes” w raporcie; log `[MCU] Awake (host traffic). Since boot: ...` po wybudzeniu);
  * Bluetooth usunięty, przez co zniknęło też pytanie stosu BLE w handlerze zasilania (`sli_bt_is_ok_to_sleep`).
* **Budzenie z EM2:** pierwszy bajt od Compass na PA09 daje przerwanie, które budzi procesor. UART w EM2 jest wyłączony, więc ta pierwsza ramka przepada. Następny heartbeat (3 s później) już przechodzi, bo firmware trzyma dongle obudzony przez 4,5 s + 3 s. Przy stałym heartbeacie dongle nie zasypia. **Do sprawdzenia testem na donglu.**
* Budzenie co 30 s (`RTC_WAKEUP_MS`) dla zapisu zegara licencji do NVM3 (co 60 s).

## 4. Zegar licencji

* Dziś: SYSRTC taktowany z LFRCO w trybie normalnym (±3 %, datasheet tab. 4.29), zapis do NVM3 co 60 s, po resecie start z ostatniego zapisu + 150 s (zegar nigdy się nie cofa, każdy reset dodaje do 150 s). `security_rtc.c:57` uznaje zegar za działający tylko przy źródle LFRCO; przy przejściu na LFXO trzeba to zmienić.
* Bez zasilania żaden licznik w układzie nie liczy. Przy BURTC zwykłe resety nie są problemem, ale POR (pusta bateria) już tak.
* Bezpieczeństwo (odłożone): SYSRTC, LFRCO i CMU są peryferiami Non-Secure (`src/secure/sec_boot.c:97-98`), więc przejęty świat NS mógłby zamrozić zegar licencji.

## 5. Porównanie wariantów (do wyboru)

Bateria 85 mAh, dongle bez USB, po wszystkich poprawkach poboru z punktu 6. Wariant z prawdziwym EM3 odrzucony (ominięcie menedżera zasilania).

| Tryb + źródło | Błąd zegara / rok | Zegar po resecie | Antitamper | Bateria: drucik zrywany (dziś) | Bateria: styk bez prądu przy zamkniętej obudowie | Budzi się po wpięciu USB | Gdy USB i heartbeat są cały czas |
|---|---|---|---|---|---|---|---|
| EM2 + LFRCO (dziś) | ±11 dni | stop, NVM3 + 150 s | TAK | 10–14 mies. (odczyt impulsowy) | 10–14 mies. | TAK, bez zmian sprzętu | TAK |
| EM2 + LFRCO precision | ±4,4 h | jak wyżej | TAK | 10–13 mies. | 10–13 mies. | TAK | TAK |
| **EM2 + LFXO (rekomendacja)** | **ok. ±26 min (50 ppm)** | jak wyżej | TAK | **10–14 mies.** | 10–14 mies. | **TAK** | **TAK** |
| EM4 + BURTC + LFXO, bez drucika | ok. ±26 min | **liczy dalej** (poza POR i pinem reset) | TAK (EM4WU budzi resetem; wymaga EM4EXIT) | ok. 6 tyg. (pull-up cały czas) | 1,2–2 lata | **NIE** | TAK, dopóki nie wejdzie w EM4 |
| EM4 + BURTC + LFXO + drucik PA09 do EM4WU | ok. ±26 min | liczy dalej | TAK | ok. 6 tyg. | 1,2–2 lata | TAK, po wpięciu kabla | TAK |

Antitamper TAK wszędzie pod warunkiem zmiany firmware: PC00 i PC05 jako piny EM4WU (przerwanie w EM0–EM3, w EM4 budzenie resetem i potem wipe); w EM2 dodatkowo odczyt impulsowy przy drucikach zrywanych; w EM4 `EM4IORETMODE` = EM4EXIT.

**EM4: co dołożyć na płytce.** Jeden drucik, bez rezystorów: od linii nadawczej mostka USB SAMD11 do procesora (PA09, w mapie Arduino D11 „Serial Rx”) do wolnego pinu EM4WU: PC07 (D7), PA05 (D10), PB03 (D14), PB01 (D16) lub PD02 (D18). SAMD11 jest zasilany z USB; po wpięciu kabla jego linia nadawcza przechodzi w stan wysoki i budzi procesor. Kolega ma sprawdzić na schemacie, czy PA09 jest na padzie. Wariant z VBUS na pinie EM4WU odpada, bo 5 V wymaga dzielnika. Bez drucika EM4 musiałby budzić się sam (np. co 10 min, nasłuch ok. 3,5 s): ok. +15 µA, ok. 7 mies., a Compass czekałby do 10 min.

Szacunki baterii: prąd MCU + płytka ok. 1,7 µA (Seeed zmierzył 1,95 µA w EM4 z uśpioną pamięcią flash) + okresowe zadania w EM2 ok. 1,5 µA + samorozładowanie LiPo 2,4–5,9 µA. Dokładne liczby dadzą liczniki EM0/EM1/EM2 po wgraniu firmware i amperomierz.

## 6. Inne źródła poboru prądu (do zrobienia, jeszcze nie zrobione)

1. Pin TX do SAMD11 (PA08) w stanie wysokim zasila odłączony mostek; według forum Seeed ok. 100 µA. Przed snem wyłączać, po wybudzeniu przywracać.
2. Pamięć SPI flash na płytce nie jest uśpiona: komendy `0x06` i `0xB9` (deep power-down), piny CS PA6, SCK PA0, MOSI PB0, MISO PB1.
3. Pomiar baterii co 60 s z 20 ms aktywnego czekania w EM0 (`battery_monitor.c`), ok. 1,1 µA średnio; na baterii wystarczy co 10 min.
4. `SL_POWER_MANAGER_INIT_EMU_EM2_DEBUG_ENABLE 1`: w buildzie produkcyjnym wyłączyć (kilka µA).
5. Druciki antitamper: odczyt impulsowy w EM2 (punkt 0, odkrycie 3).
6. **Do sprawdzenia na schemacie:** mapa pinów Silicon Labs opisuje PD3 jako „Battery charger enable”, a `battery_monitor.c` używa PD3 jako włącznika dzielnika do pomiaru baterii.

## 7. Wiarygodność odczytu baterii

* mV: ADC skalibrowany fabrycznie, 16 próbek; bezwzględnie ok. ±40–80 mV (napięcie odniesienia 1,21 V, dzielnik liczony jako dokładne 1:2).
* %: ogólna krzywa LiPo, ważna dla ogniwa w spoczynku. Przy podpiętym USB ładowarka zawyża odczyt.
* Najbardziej wiarygodne jest `vbat_min_mv` (najniższa próbka od startu, czyli napięcie z końca pracy na baterii).
* Dokładność bezwzględną poprawi tylko jeden pomiar multimetrem na stykach baterii (współczynnik korekcji).

## 8. Plan (nie zrobione)

1. Użytkownik wybiera wariant z punktu 5.
2. Wgrać obecny firmware produkcyjny (nie zmienia startu licencji) i sprawdzić: handshake, klucze PSA (Bluetooth usunięty), budzenie z EM2 heartbeatem, test baterii 30 min bez USB i odczyt „Energy modes” w DIAG (oczekiwane ok. 99 % EM2).
3. Antitamper: drugi pin z PC6 na PC0; oba jako EM4WU (`sl_gpio_configure_wakeup_em4_interrupt()`, `sl_gpio.h:387`), kierunek „obwód przerwany”; odczyt impulsowy; odczyt stanu przy starcie.
4. LFXO: `SL_CLOCK_MANAGER_LFXO_EN 1`, CTUNE 44, SYSRTC na LFXO, zmiana kontroli źródła w `security_rtc.c:57`.
5. Poprawki poboru z punktu 6.
6. Korekta zegara licencji z czasu PC, tylko do przodu.
7. Test na donglu: obudowa zamknięta, Compass odłączony (dongle śpi), zerwać drucik: oczekiwany wipe; sprawdzić wpis w tamper logu (`KeySec/temp/userdata_dump.py`); ponowny provisioning (`provision_dongle.py 365 3 --skip-compile`, bez `--lock`, start licencji zostaje bez odpowiedzi „TAK, NADPISZ”).

## 9. Pliki

* Firmware:
  * `KeyFirmware/src/core/tamper_simulation.c` (piny, przerwania), `tamper_manager.c` (progi, log, wipe);
  * `KeyFirmware/app.c` (uśpienie), `src/core/power_stats.c` (czasy EM);
  * `KeyFirmware/src/core/security_rtc.c` (zegar licencji), `security_nvm.c`;
  * `KeyFirmware/src/core/battery_monitor.c`;
  * konfiguracja: `config/sl_iostream_eusart_Io_Stream_USERT_config.h`, `config/sl_clock_manager_oscillator_config.h`, `config/sl_clock_manager_tree_config.h`, `config/sl_power_manager_config.h`;
  * zasady regeneracji projektu SLC (ręczne edycje): `KeyFirmware/AGENTS.md`.
* Skrypty: `KeySec/temp/diag_power.py` (bateria i reset z DIAG), `nvm3_dump.py`, `userdata_dump.py`, `tamper_entry.py`, `admin_wipe.py`, `dongle_state.py`.
* Dokumenty: `KeySec/docs/security/antitamper.md`, `time_license_mechanism.md`, `diagnostics.md` (rekord DIAG v7).

## 10. Źródła

* Reference manual EFR32xG24: https://www.silabs.com/documents/public/reference-manuals/efr32xg24-rm.pdf (12.3.1.5 EM3 i 12.3.1.6 EM4 s. 295; tabela 8.1 s. 161; 16 BURTC s. 457; 24.3.7 s. 812; 24.3.10).
* Datasheet EFR32MG24: https://www.silabs.com/documents/public/data-sheets/efr32mg24-datasheet.pdf (tab. 4.5 s. 29–30 prądy; 4.26 LFXO s. 61; 4.27 HFRCO s. 62; 4.29/4.30 LFRCO/ULFRCO s. 64; 6.5 piny s. 115).
* Definicja płytki: https://raw.githubusercontent.com/zephyrproject-rtos/zephyr/main/boards/seeed/xiao_mg24/xiao_mg24.dts
* Seeed XIAO MG24 wiki: https://wiki.seeedstudio.com/xiao_mg24_getting_started/
* Forum Seeed (pobór prądu XIAO MG24): https://forum.seeedstudio.com/t/power-consumption-of-xiao-mg24/291139?page=2
* `EMU_EnterEM3()` niezgodne z Power Managerem: https://github.com/SiliconLabs/simplicity_sdk/blob/sisdk-2025.6/platform/emlib/src/em_emu.c#L1104-L1200
