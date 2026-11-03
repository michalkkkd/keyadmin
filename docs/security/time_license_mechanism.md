# Mechanizm licencji czasowej

## 1. Przegląd
System licencji czasowej gwarantuje, że aplikację i jej krytyczne funkcje można uruchomić tylko wtedy, gdy na donglu USB znajduje się ważna licencja, która nie wygasła.

Licencja jest ustalana raz, w momencie provisioningu: dongle zapisuje datę startu (`lic_start_time`, czas Unix z chwili provisioningu) i liczbę dni (`lic_days`). Koniec licencji to `lic_start_time + lic_days × 86 400 s` i nie zmienia się aż do ponownego provisioningu. Firmware produkcyjny nie ma żadnej komendy, która by te wartości zmieniała.

## 2. Zegar dongla
EFR32MG24 nie ma klasycznego RTC z podtrzymaniem bateryjnym, więc zegar licencji składa się z dwóch elementów:

* **Licznik SYSRTC (32 768 Hz, z LFRCO).** Uruchamia go świat Non-Secure (sleeptimer). Licznik pracuje także w uśpieniu EM2, czyli wtedy, gdy dongle śpi na baterii z odłączonym USB. Świat Secure odczytuje rejestr `CNT` bezpośrednio (przez alias NS `SYSRTC0_NS`, bo SYSRTC jest peryferium Non-Secure) i sam sumuje przyrosty (`security_rtc.c`), dzięki czemu obsługuje też przepełnienie 32-bitowego licznika (co ok. 36 h). Główna pętla NS wywołuje `nsc_rtc_process()` co najmniej co 30 s: budzi ją timer okresowy `RTC_WAKEUP_MS` także w EM2.
* **Checkpoint w NVM3.** Licznik SYSRTC zeruje się przy każdym resecie, dlatego bieżący czas Unix jest zapisywany w NVM3 świata Secure co 60 s (`RTC_CHECKPOINT_INTERVAL_S`). Po resecie zegar startuje od ostatniego checkpointu plus 150 s kary (`RTC_RESET_PENALTY_S`). Kara jest większa niż najdłuższa możliwa przerwa między checkpointami (60 s interwału + 30 s budzenia + do ok. 33 s pętli zablokowanej długim obliczeniem, ograniczonej watchdogiem), więc:
  * reset nigdy nie cofa zegara, przesuwa go najwyżej o ok. 2,5 minuty do przodu;
  * resetowanie dongla w kółko (np. przyciskiem RESET albo układem podłączonym do pinu reset) nie zatrzymuje licencji, tylko przyspiesza jej wygasanie.

Dokładność zegara zależy od LFRCO w trybie precyzyjnym (ok. ±500 ppm, czyli do ok. 45 s na dobę). Zapis checkpointu co minutę to ok. 1 440 małych obiektów NVM3 na dobę; przy 40 KB NVM3 i wyrównywaniu zużycia daje to kilkaset kasowań strony rocznie, przy wytrzymałości flash 10 000 cykli.

**Utrata zasilania.** Bateria jest podłączona na stałe, więc w normalnej pracy zegar biegnie bez przerwy. Jeśli bateria całkowicie się rozładuje i USB jest odłączone, czas bez zasilania nie jest liczony: po włączeniu zegar rusza od ostatniego checkpointu. Licencja w takim wypadku nie wygasa szybciej, ale też nigdy nie cofa się przed ostatni zapisany moment.

## 3. Komponenty
* **Admin API:** `AdminApi.update_current_date()` i `AdminApi.set_license_days()` (`MSG_ADMIN_DATE`, `MSG_ADMIN_LIC`) ustawiają zegar i licencję. Istnieją wyłącznie w firmware fabrycznym (`keyfirmware_prov.hex`); firmware produkcyjny ich nie zawiera. `provision_dongle.py` najpierw synchronizuje zegar z czasem komputera, potem zapisuje licencję, więc start licencji to rzeczywisty moment provisioningu.
* **Compass API:** Aplikacja Python wywołuje `check_license` przy starcie lub przed krytycznymi obliczeniami. Dongle odpowiada statusem ważności licencji, a każde chronione obliczenie w świecie Secure sprawdza licencję ponownie (`security_verify_license_and_users`).

## 4. Środki bezpieczeństwa (anti-tampering)
* **Brak cofania zegara w produkcji:** w firmware produkcyjnym zegar może iść tylko do przodu: jedynym źródłem czasu jest licznik SYSRTC i checkpoint, a reset dolicza karę. Host nie ma komendy ustawiającej czas.
* **Synchronizacja fabryczna może cofnąć zegar:** `MSG_ADMIN_DATE` (tylko firmware fabryczny) ustawia zegar na podany czas, także wcześniejszy, bo start licencji musi być rzeczywistym momentem provisioningu (np. przy ponownym provisioningu krótko po resecie). Nie osłabia to ochrony: kto może uruchomić firmware fabryczny, i tak może ustawić dowolną licencję. Firmware odrzuca czas sprzed 2024-01-01, a cofnięcie zegara zapisuje w logu.
* **Bezpieczeństwo przechowywania:** `lic_start_time`, `lic_days` i checkpoint zegara leżą w NVM3 świata Secure, w obszarze flasha Secure (`0x08026000`-`0x0802FFFF`), którego kod Non-Secure nie może odczytać. Przed odczytem lub zapisem przez SWD chroni je Secure Debug Lock.
* **Stan fail-secure (bezpieczny w razie awarii):** status `NO_RTC` (wszystkie żądania algorytmów odrzucane) pojawia się, gdy:
  * brak checkpointu: dongle bez provisioningu albo po `MSG_ADMIN_WIPE` / wipe po tamperze (wipe czyści też licencję trzymaną w RAM);
  * licznik SYSRTC zatrzymał się po starcie;
  * checkpoint nie zapisał się przez ponad 210 s (np. błąd zapisu NVM3), bo wtedy reset mógłby cofnąć zegar.

  Brak licencji daje `NO_LICENSE`.
