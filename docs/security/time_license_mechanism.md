# Mechanizm licencji czasowej

## 1. Przegląd
System licencji czasowej gwarantuje, że aplikację i jej krytyczne funkcje można uruchomić tylko wtedy, gdy na donglu USB znajduje się ważna licencja, która nie wygasła.

## 2. Komponenty
* **Zegar sprzętowy (RTC):** EFR32MG24 nie ma RTC z podtrzymaniem bateryjnym. Aby symulować ciągły upływ czasu, dongle zapisuje początkowy `boot_time` (Unix timestamp) w bezpiecznej pamięci NVM3. Bieżący czas oblicza się, dodając do tego `boot_time` czas pracy procesora (uptime, w tickach).
* **Admin API:** `AdminApi.update_current_date()` i `AdminApi.set_license_days()` (`MSG_ADMIN_DATE`, `MSG_ADMIN_LIC`) ustawiają bieżący czas i długość licencji (w dniach). Istnieją wyłącznie w firmware fabrycznym (`keyfirmware_prov.hex`); firmware produkcyjny ich nie zawiera.
* **Compass API:** Aplikacja Python wywołuje check_license przy starcie lub przed krytycznymi obliczeniami. Dongle odpowiada statusem ważności licencji.

## 3. Środki bezpieczeństwa (anti-tampering)
* **Ochrona przed cofnięciem czasu:** Firmware aktywnie zapobiega atakom polegającym na cofnięciu czasu (time rollback). Jeśli komputer hosta spróbuje przesłać synchronizację czasu wcześniejszą niż czas aktualnie wyliczony przez dongle, firmware ją odrzuca i rejestruje próbę ataku.
* **Bezpieczeństwo przechowywania:** lic_start_time i lic_days są przechowywane w NVM3, w świecie Secure (ARM TrustZone), bez szyfrowania; przed ich odczytem lub zapisem przez SWD chroni Secure Debug Lock.
* **Stan fail-secure (bezpieczny w razie awarii):** Gdy dongle traci zasilanie, jego wewnętrzny zegar się zatrzymuje. Po ponownym podłączeniu host musi jawnie zsynchronizować czas (forward-sync). Bez synchronizacji wszystkie żądania algorytmów są odrzucane.
