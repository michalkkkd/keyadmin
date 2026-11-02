# Mechanizm limitu aktywnych użytkowników (okno 10-minutowe)

## 1. Przegląd
Aplikacja Compass działa jako serwer WWW oparty na Tornado. Ponieważ wielu użytkowników może łączyć się przez sesje przeglądarki, system musi twardo ograniczać maksymalną liczbę *jednocześnie aktywnych użytkowników*. Użytkownik jest uznawany za „aktywnego” tylko wtedy, gdy korzystał z aplikacji w ciągu ostatnich **10 minut** (600 sekund).

## 2. Zbieranie danych (aplikacja Compass)
Aby egzekwować tę regułę, backend Compass (przez SessionManager i session_store.json) musi śledzić określone dane telemetryczne dla każdego podłączonego użytkownika:
* **Token sesji / ID użytkownika:** Unikalny identyfikator użytkownika (np. hash SHA-256 jego adresu e-mail lub odcisku przeglądarki - browser fingerprint).
* **Timestamp ostatniej aktywności (last_seen_at):** Unix timestamp aktualizowany przy każdym wywołaniu API lub interakcji z UI w ramach danej sesji.

## 3. Warianty egzekwowania (poziomy bezpieczeństwa)

### Wariant 1: egzekwowanie programowe (najsłabsze)
* **Mechanizm:** Compass odczytuje MAX_USERS z dongla KeySec przy starcie. Następnie wewnętrznie filtruje swój session_store.json, licząc sesje, dla których (current_time - last_seen_at) <= 600. Jeśli ich liczba przekroczy limit, UI Compass odrzuca nowe logowania.
* **Podatność:** Atakujący, który rozpakuje plik wykonywalny Nuitki, może wyciąć patchem sprawdzenie if active_count > MAX_USERS. Sprzętowy dongle nie ma pojęcia, ilu użytkowników faktycznie wykonuje obliczenia.

### Wariant 2: egzekwowanie sprzętowe przez blokowanie algorytmów (silne)
* **Mechanizm:** Za liczenie aktywnych użytkowników odpowiada sam dongle.
  - Aplikacja Compass musi dołączać user_id_hash do każdego żądania obliczenia algorytmu (np. MSG_COMPASS_ALG1).
  - Firmware EFR32 utrzymuje wewnętrzną tablicę w RAM: struct ActiveUser { uint32_t user_hash; uint32_t last_seen; };
  - Po otrzymaniu żądania obliczenia dongle aktualizuje last_seen dla danego hasha.
  - Następnie dongle przegląda tablicę i usuwa wszystkie hashe starsze niż 10 minut (korzystając ze swojego zsynchronizowanego Global RTC).
  - Jeśli przyjdzie nowy hash, a tablica zawiera już MAX_USERS aktywnych slotów, dongle zwraca bezwzględny błąd ERR_USER_LIMIT i odmawia wykonania obliczeń.
* **Zaleta:** Nawet jeśli aplikacja Python zostanie całkowicie zdekompilowana i spatchowana, sprzęt fizycznie odmówi obsługi żądań nadmiarowych użytkowników.

### Wariant 3: egzekwowanie sprzętowe z tokenami sesji (najsilniejsze)
* **Mechanizm:** Zamiast wysyłać sam hash, Compass musi jawnie poprosić dongle o „sprzętowy slot sesji” (Hardware Session Slot).
  - Compass wysyła MSG_REQUEST_SESSION (user_id_hash).
  - Dongle sprawdza limit w przesuwnym oknie 10 minut. Jeśli slot jest wolny, generuje tymczasowy 16-bajtowy session_key (przez TRNG, czyli sprzętowy generator liczb losowych w Secure Vault) i go zwraca.
  - Przez kolejne 10 minut wszystkie żądania algorytmów tego użytkownika MUSZĄ być szyfrowane właśnie tym session_key.
  - Po 10 minutach bezczynności dongle po cichu usuwa klucz ze swojej pamięci RAM.
* **Zaleta:** Całkowicie zapobiega atakom typu replay oraz multipleksowaniu Man-in-the-Middle (gdy zhakowana aplikacja hosta próbuje przepuścić wielu użytkowników przez jeden sprzętowy slot sesji).

## 4. Zalecana implementacja
Zdecydowanie zalecamy **Wariant 2** jako podstawę, z możliwością późniejszego przejścia na **Wariant 3**. 
* **Dane do wysłania do KeySec:** user_id_hash (4 bajty) dołączony do payloadu MSG_COMPASS_ALG1.
* **Narzut na RAM sprzętu:** Minimalny. Śledzenie 50 użytkowników wymaga zaledwie 50 * 8 bajtów = 400 bajtów RAM w EFR32.
