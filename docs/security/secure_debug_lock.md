# Secure Debug Lock (blokada SWD z odblokowaniem typu challenge-response)

> **Zakres:** KeyFirmware (Seeed XIAO MG24 / EFR32MG24, Secure Engine "Secure Vault High") + narzędzia KeySec `keyadmin`.
> **Status:** Zaimplementowane. Stosowane **tylko na żądanie** (`provision_dongle.py <days> <users> --lock`, z CLI lub z menu administracyjnego).
> **Zweryfikowane na sprzęcie:** status, challenge, odrzucanie nieprawidłowych tokenów, odmowa dla urządzeń chronionych.
> **Jeszcze niezweryfikowane na sprzęcie:** prawdziwa blokada, a po niej udane odblokowanie (zapisuje OTP; do wykonania na zapasowej płytce).

---

## 1. Co się zmienia po włączeniu blokady

Bez blokady każdy, kto ma 2-przewodową sondę SWD (albo wbudowany w XIAO interfejs CMSIS-DAP), może zatrzymać CPU, zrzucić całą pamięć flash i RAM, wykonywać krok po kroku kod świata Secure i wgrać dowolny firmware.

Włączenie Secure Debug Lock wykonuje trzy operacje Secure Engine (SE, wbudowany w układ moduł bezpieczeństwa), w tej kolejności:

| Krok | Operacja SE | Trwałość | Efekt |
|---|---|---|---|
| 1 | `sl_se_init_otp_key(SL_SE_KEY_TYPE_IMMUTABLE_AUTH)` | **OTP (pamięć jednokrotnego zapisu), na stałe** | Instaluje nasz **publiczny Command Key**. Od tej chwili układ ufa wyłącznie tokenom odblokowującym podpisanym pasującym kluczem prywatnym. |
| 2 | `sl_se_enable_secure_debug()` | Konfiguracja SE (resetowana przez device erase) | Pozwala na tymczasowe, kryptograficznie autoryzowane odblokowanie. Musi nastąpić **przed** krokiem 3. |
| 3 | `sl_se_apply_debug_lock()` | Konfiguracja SE (resetowana przez device erase) | Zamyka port dostępu debug przy każdym uruchomieniu. |

Celowo **nie** wykonujemy: `disabledeviceerase`. Device erase (pełne kasowanie układu) pozostaje dostępny jako ostateczna metoda odzyskania układu.

### Przed czym chroni
* **Wyciąganie firmware'u / własności intelektualnej przez SWD:** zastrzeżonych algorytmów Compass w świecie Secure, logiki licencji i logu tamper nie da się już odczytać debuggerem.
* **Ataki przez debugowanie na żywo:** zatrzymanie CPU, łatanie sprawdzania licencji w RAM, odczyt kluczy sesji z RAM, wykonywanie kodu TrustZone krok po kroku.
* **Ponowne flashowanie dongla** zmodyfikowanym firmware'em z zachowaniem jego stanu NVM3 (licencja, klucz tożsamości, certyfikat).

### Czego NIE zmienia
* Normalnego działania: Compass, VCOM/USB RPC, szyfrowane sesje, licencja i limity użytkowników działają dokładnie jak wcześniej.
* Logi RAM przez USB (`MSG_GET_LOG_*`) nadal działają bez żadnego odblokowania.
* **Device erase** nadal jest możliwy: ponownie otwiera port, ale kasuje **całą** główną pamięć flash (firmware, licencję w NVM3, klucz tożsamości, certyfikat). Przetrwa tylko strona User Data z zaszyfrowanym logiem tamper. Atakujący zyskuje pusty układ, nigdy nasze dane.
* Klucz tożsamości w NVM3 jest opakowany kluczem PUF (dongle provisionowane firmware'em od 2026-10-30); blokada dodaje ochronę kodu, RAM i danych licencji, czego opakowanie nie obejmuje.

### Jak firmware to implementuje
* **Świat Secure** ([`KeyFirmware/src/secure/sec_debug_lock.c`](../../../KeyFirmware/src/secure/sec_debug_lock.c)): wszystkie wywołania SE; publiczny Command Key jest **wkompilowany** z [`debug_command_pubkey.h`](../../../KeyFirmware/src/secure/debug_command_pubkey.h) i nigdy nie jest przyjmowany od hosta, więc nikt nie zainstaluje własnego klucza przez RPC.
* **Bramki NSC** (`nsc_debug_lock_*` w `nsc_interface.c`): walidacja wskaźników; token odblokowujący jest kopiowany do pamięci Secure przed użyciem.
* **Router świata Non-Secure** ([`KeyFirmware/src/core/debug_lock_router.c`](../../../KeyFirmware/src/core/debug_lock_router.c)): jawne (nieszyfrowane) komendy RPC, obecne **zarówno** w firmware produkcyjnym, jak i provisioningowym:

| ID | Komenda | Payload | Odpowiedź |
|---|---|---|---|
| `0x60` | STATUS | – | `SERIAL:<32 hex>;CMD_KEY:NONE/MATCH/MISMATCH;BUILTIN_KEY;SECURE_DEBUG;LOCK_APPLIED;LOCK_ACTIVE;DEVICE_ERASE` |
| `0x61` | LOCK | – | Jednokierunkowa i idempotentna. Odrzucana, jeśli firmware nie ma wbudowanego klucza albo OTP zawiera inny klucz. |
| `0x62` | CHALLENGE | – | `SERIAL:<32 hex>;CHALLENGE:<32 hex>` |
| `0x63` | UNLOCK | token 220-bajtowy | Otwiera port debug **do najbliższego resetu / wyłączenia zasilania**. |

Jawny tekst jest zamierzony: SE sam weryfikuje token (numer seryjny + bieżący challenge + podpis Command Key), a UNLOCK musi działać także na donglu, którego certyfikat tożsamości lub warstwa sesji są uszkodzone.

---

## 2. Dongle wraca od klienta: co możemy zrobić?

**Bez odblokowania (tylko USB):** odczytać przez konsolę administracyjną stan systemu, liczniki tamper, baterię, RTC, licencję i bufor logów w RAM.

**Po `secure_debug_lock.py unlock`** (port otwarty do najbliższego resetu):

| Działanie | Jak | Uwagi |
|---|---|---|
| Odczyt zaszyfrowanego logu zdarzeń tamper (strona User Data `0x0FE00000`, 1 KB) | Wykonywany i dekodowany automatycznie po `unlock`; ręcznie: `python -m pyocd cmd ... -M attach -c "savemem 0x0FE00000 1024 <file>"`, dekodowanie przez `keyadmin/scripts/read_tamper_log.py --file <file>` (dokładną komendę wypisuje narzędzie) | Używaj trybu **attach**: reset ponownie blokuje port. |
| Zrzut dowolnego obszaru flash / RAM, inspekcja świata Secure | pyOCD / GDB w trybie attach | Pełny dostęp: Non-Secure + Secure, inwazyjny + nieinwazyjny. |
| Debugowanie błędu na żywo | GDB attach | Port pozostaje otwarty do resetu. |
| Ponowne wgranie firmware'u (aktualizacja / poprawka) | `unlock`, potem `flash.bat` lub `set_production_mode.bat` | Reset na końcu flashowania ponownie blokuje port, więc osobne ponowne blokowanie nie jest potrzebne. Klucz w OTP i blokada pozostają. |
| Ponowny provisioning (nowa licencja, nowy klient) | `unlock` → `set_factory_mode.bat` → provisioning przez USB → ponownie `unlock` (firmware provisioningowy też ma `0x63`) → `set_production_mode.bat` | Flashowanie zachowuje NVM3; aby zacząć od zera, użyj `MSG_ADMIN_WIPE` w trybie fabrycznym. |

**Ograniczenia:**
* Odblokowanie przez VCOM wymaga **działającego firmware'u**. Po kasowaniu tamper na żywo (live wipe) odblokowanie nie jest potrzebne: device erase wykonany przez Secure Engine resetuje też blokadę debug, więc log tamper (strona User Data, zachowana przez kasowanie) można odczytać bezpośrednio przez SWD i odszyfrować kluczem `tamper_log_key.bin` (zob. [antitamper.md](antitamper.md)). Jeśli firmware jest uszkodzony z innego powodu, odblokowanie musi przejść przez interfejs debug: Simplicity Commander z J-Linkiem i tym samym kluczem (`commander security unlock --command-key debug_command_key.pem`). Ta ścieżka nie była jeszcze testowana na XIAO.
* **Klucza w OTP nigdy nie da się usunąć**. Układ zablokowany danym Command Key jest z nim związany na zawsze.
* Ostateczność: pełny **device erase** przez interfejs debug SE (np. `commander device recover`). Otwiera port na stałe, ale niszczy wszystko poza OTP. Nie sprawdzono, czy wbudowany w XIAO CMSIS-DAP potrafi go wykonać przez pyOCD; sprawdzoną ścieżką jest J-Link podłączony do padów SWD.

---

## 3. Klucze i pliki

### 3.1 Gdzie znajduje się każdy klucz

| Klucz | Gdzie | Przeznaczenie |
|---|---|---|
| **Klucz prywatny Root CA** | `keyadmin/keys/root_ca_key.pem` (host) | Podpisuje klucz publiczny tożsamości każdego dongla podczas provisioningu (`provision_dongle.py`). |
| **Klucz publiczny Root CA** | `keyadmin/keys/root_ca_pub.pem`, `keycomm/keys/root_ca_pub.pem`, dostarczany z Compass | Compass sprawdza, czy certyfikat tożsamości dongla został podpisany przez nas (oryginalny dongle). |
| **Klucz tożsamości urządzenia** | Wewnątrz każdego dongla (NVM3 świata Secure, opakowany kluczem PUF `SL_PSA_KEY_LOCATION_WRAPPED`; starsze dongle jawnie do czasu ponownego provisioningu; nigdy nie opuszcza urządzenia) | Podpisuje handshake ECDHE, co dowodzi tożsamości dongla i zapobiega atakom MitM. |
| **Certyfikat urządzenia** | Wewnątrz każdego dongla (NVM3) | Podpis Root CA nad publicznym kluczem tożsamości. |
| **Command Key, prywatny** | `keyadmin/keys/debug_command_key.pem` (host) | **Jeden na produkt/fabrykę, nie na urządzenie, i jedyny sekret odblokowujący.** keyadmin podpisuje nim każdy token odblokowujący, w pamięci. |
| **Command Key, publiczny** | `keyadmin/keys/debug_command_pubkey.pem` + wkompilowany w firmware (`debug_command_pubkey.h`) + OTP każdego zablokowanego dongla | Kotwica zaufania, której SE używa do weryfikacji tokenów odblokowujących. |
| **Klucze sesji** | Tylko RAM (ECDHE + HKDF, AES-256-GCM) | Szyfrowanie pojedynczego połączenia; niezwiązane z blokadą debug. |

Łańcuch Root CA i łańcuch Command Key są **niezależne**. Root CA dowodzi wobec Compass, że „ten dongle jest oryginalny”. Command Key dowodzi wobec Secure Engine dongla, że „ten host to producent”.

### 3.2 Łańcuch zaufania przy odblokowaniu

```
debug_command_key.pem (prywatny, wspólny dla całej fabryki)
        │ przy każdym odblokowaniu, w pamięci: nowy jednorazowy klucz certyfikatu, certyfikat podpisany Command Key
        ▼
certyfikat dostępu      = magic | auth bits | SE serial[16] | cert_pubkey[64] | signature[64]   (156 B)
        │ jednorazowy klucz certyfikatu podpisuje
        ▼
odpowiedź na challenge  = DEBUG_ACCESS_CMD | unlock params | challenge[16]                     (24 B)

token odblokowujący     = certyfikat dostępu + podpis challenge'u                              (220 B)
```

Format SE wymaga dwustopniowego łańcucha (certyfikat + podpis challenge'u), ale keyadmin przy każdym odblokowaniu buduje oba elementy w pamięci z Command Key i żadnego nie zapisuje: **Command Key jest jedynym sekretem odblokowującym.**

SE akceptuje token tylko wtedy, gdy:
1. certyfikat został podpisany Command Key zapisanym w **jego** OTP;
2. numer seryjny w certyfikacie jest **jego własnym**, więc tokenu nie można użyć ponownie na innym donglu;
3. podpis challenge'u pasuje do jego **bieżącego** challenge'u. Challenge pozostaje ten sam, dopóki nie zostanie zmieniony (rolled); nie zmieniamy go, bo tokeny powstają wyłącznie w fabryce i nigdy nie są przechowywane.

### 3.3 Struktura folderu `keyadmin/keys/`

```
keyadmin/keys/
├── root_ca_key.pem                 Klucz prywatny Root CA (łańcuch tożsamości)
├── root_ca_pub.pem                 Klucz publiczny Root CA
├── debug_command_key.pem           Command Key prywatny (OBECNY KLUCZ JEST KLUCZEM DEWELOPERSKIM)
├── debug_command_pubkey.pem        Command Key publiczny (te same bajty co debug_command_pubkey.h)
└── secure_debug/
    ├── protected_devices.json      Numery seryjne, których narzędzia keyadmin NIGDY nie zablokują (płytki deweloperskie)
    └── devices/
        └── device_<SE serial>/     Jeden folder na dongle, nazwany 16-bajtowym numerem seryjnym Secure Engine
            ├── device.json         Ostatni status + historia zdarzeń STATUS / LOCK / UNLOCK (timestamp, port, odpowiedź)
            └── userdata_dump.bin   Zrzut strony User Data (log tamper, zapisany przez pyOCD)
```

Żaden materiał odblokowujący (certyfikat, jego klucz, token) nigdy nie jest tu zapisywany.

**Numer seryjny:** każdy EFR32MG24 ma unikalny, nadany fabrycznie 16-bajtowy numer seryjny SE (na przykład `0000000000000000880F62FFFE3E183B`; ostatnie 8 bajtów to EUI-64 układu). Różni się on od numeru seryjnego USB wbudowanego w XIAO mostka USB, więc nie używaj tożsamości portu COM do nazywania urządzeń.


---

## 4. Jak obecnie działa włączanie blokady

| Punkt wejścia | Blokuje? | Szczegóły |
|---|---|---|
| `compile.bat` | Nie | Buduje oba firmware'y; osadza publiczny Command Key z `debug_command_pubkey.h`. |
| `flash.bat`, `set_factory_mode.bat`, `set_production_mode.bat` | Nie | Tylko flashują przez pyOCD. Na zablokowanym donglu działają wyłącznie zaraz po `unlock`. |
| `python keyadmin/scripts/provision_dongle.py <days> <users>` | **Nie** | kompilacja → firmware fabryczny → sekrety → firmware produkcyjny → weryfikacja. Krok blokady jest pomijany. |
| `python keyadmin/scripts/provision_dongle.py <days> <users> --lock` | **Tak** | Po weryfikacji: sprawdzenie listy chronionych → sprawdzenie, czy już zablokowany → potwierdzenie przez wpisanie `LOCK` (`--yes` je pomija) → `0x61` → ponowny odczyt. |
| Konsola administracyjna, sekcja *FACTORY* → *Provision Dongle* | Tylko po odpowiedzi `y` | Ten sam pipeline; pyta o liczbę dni, użytkowników, blokadę oraz o potwierdzenie przez wpisanie `PROVISION`. |
| `python keyadmin/scripts/secure_debug_lock.py lock` | Tak | Ten sam przebieg, samodzielnie. |
| Konsola administracyjna (`python keyadmin/main.py`), sekcja *SECURE DEBUG LOCK (SWD)* | Tak | Status / Apply lock (prosi o wpisanie `LOCK`) / Unlock until next reset. |

Przebieg `secure_debug_lock.py lock`:
1. Łączy się i odczytuje STATUS (numer seryjny, stan klucza w OTP, flagi blokady), po czym zapisuje go w `device.json`.
2. **Odmawia**, jeśli numer seryjny jest w `protected_devices.json`; nic nie jest wysyłane do dongla.
3. Kończy się sukcesem, jeśli dongle jest już zablokowany (secure-locked).
4. **Smoke test:** wymaga nawiązanej szyfrowanej sesji ECDHE (oryginalny, sprovisionowany dongle z firmware'em produkcyjnym) i poprawnego sprawdzenia licencji.
5. Pokazuje ostrzeżenie i prosi operatora o wpisanie `LOCK` (pomijane z `--yes`).
6. Wysyła `0x61`, ponownie odczytuje STATUS i sprawdza `LOCK_APPLIED=1`, `SECURE_DEBUG=1`, `CMD_KEY=MATCH`; zapisuje wynik.

Warstwy zabezpieczeń przed przypadkowym zablokowaniem płytek deweloperskich:
1. `protected_devices.json` (podłączoną płytkę dodaje się przez `secure_debug_lock.py protect`; numer seryjny usuwa się tylko ręczną edycją pliku);
2. `--lock` trzeba jawnie przekazać do `provision_dongle.py` (albo odpowiedzieć `y` w menu) i potwierdzić, wpisując `LOCK`;
3. firmware zbudowany przed powstaniem Command Key (`BUILTIN_KEY:0`) w ogóle nie potrafi zablokować.

Inne komendy CLI: `status`, `unlock` (buduje token w pamięci, zapisuje zdarzenie w `device.json`, zrzuca log tamper i wypisuje komendę pyOCD), `protect`. Opcje: `--port COMx`, `--store DIR` (dane urządzeń), `--keys DIR` (folder z Command Key).

---

## 5. Ponowne generowanie (rotacja) Command Key

`generate_debug_command_key.py`:
* tworzy `debug_command_key.pem` + `debug_command_pubkey.pem` w `keyadmin/keys/` (lub `--keys DIR`);
* **odmawia nadpisania** istniejącego klucza;
* zapisuje klucz publiczny do `KeyFirmware/src/secure/debug_command_pubkey.h` (wraz z odciskiem SHA-256);
* `--header-only` generuje ponownie nagłówek z istniejącego klucza, nie tworząc nowego.

### Skutki nowego klucza
Klucz w OTP dongla nigdy się nie zmienia, więc po rotacji istnieją dwie grupy urządzeń:

| Stan dongla | Z nowym firmware'em (wbudowany nowy klucz) | Jak go odblokować |
|---|---|---|
| Nigdy nie zablokowany (OTP puste) | LOCK instaluje **nowy** klucz | Nowy klucz |
| Zablokowany **starym** kluczem | STATUS pokazuje `CMD_KEY:MISMATCH`; LOCK jest odrzucany (i tak jest już zablokowany) | Wymaga **starego** Command Key: `secure_debug_lock.py unlock --keys <old keys dir>` |

### Procedura przejścia do prawdziwej produkcji
1. Wygeneruj klucz produkcyjny do osobnego folderu: `python keyadmin/scripts/generate_debug_command_key.py --keys <production keys dir>`. To również nadpisuje nagłówek firmware'u.
2. Przebuduj przez `compile.bat` i potwierdź odcisk w `debug_command_pubkey.h`.
3. Zablokuj dongle produkcyjne. Sama blokada nie odczytuje klucza prywatnego (firmware instaluje swój wbudowany klucz publiczny), ale odblokowania już tak. `provision_dongle.py ... --lock` działa więc bez zmian. Do odblokowań używaj `secure_debug_lock.py unlock --keys <production keys dir>`. Konsola administracyjna zawsze używa domyślnego `keyadmin/keys`.
4. **Zachowaj klucz deweloperski**: dongle już nim zablokowane zależą od niego na zawsze.
5. Przechowuj produkcyjny klucz prywatny **offline / poza git**, z kopią zapasową. Obecny klucz deweloperski oraz klucz prywatny Root CA są śledzone w git, co jest dopuszczalne wyłącznie na etapie rozwoju.

**Utrata Command Key** oznacza, że każdy nim zablokowany dongle da się odzyskać tylko przez pełny device erase (licencja i tożsamość przepadają; log tamper na stronie User Data przetrwa).

---

## 6. Trzy tryby: nigdy nie zablokowany, zablokowany, odblokowany do resetu

### 6.1 Czym jest SWD i dlaczego XIAO robi z niego skrót

**SWD (Serial Wire Debug)** to dwuprzewodowy interfejs debug firmy ARM (`SWDIO` dane + `SWCLK` zegar), wbudowany w każdy rdzeń Cortex-M, w tym w Cortex-M33 układu EFR32MG24. To nie jest zwykły port komunikacyjny. To bezpośrednie drzwi do wnętrza układu:

* SWD komunikuje się z **Debug Access Port (DAP)**. Za nim znajduje się **AHB-AP**, master magistrali na wewnętrznej magistrali pamięci układu, tak samo jak CPU.
* Przez AHB-AP debugger może **czytać i zapisywać dowolny adres**: całą pamięć flash (firmware i NVM3 z danymi licencji), RAM (stan w czasie działania, klucze sesji, wyniki pośrednie) i wszystkie rejestry peryferiów.
* Może też **zatrzymać CPU**, wykonywać instrukcje krok po kroku, ustawiać breakpointy i zmieniać rejestry. Firmware nie może tego zauważyć ani temu zapobiec. Zatrzymany CPU nie wykonuje żadnego kodu anti-tamper.
* W ten sposób w ogóle programuje się firmware: `flash.bat`, `set_factory_mode.bat` i `set_production_mode.bat` zapisują flash przez SWD (za pomocą pyOCD).

Na zwykłej płytce użycie SWD wymaga fizycznego wysiłku: otwarcia obudowy, znalezienia padów debug, przylutowania lub podpięcia przewodów i posiadania sondy debug (J-Link, ST-Link, ...). **Seeed XIAO MG24 eliminuje to wszystko.** Ma na płytce mały mikrokontroler mostka USB z firmware'em **CMSIS-DAP**, więc sonda debug jest częścią samego dongla. Przez **ten sam kabel USB** komputer widzi dwie rzeczy:

| Interfejs USB | Czym jest | Kto go używa |
|---|---|---|
| Port szeregowy (VCOM, np. `COM10`) | Mostek UART do firmware'u EFR32 | Compass, keycomm i keyadmin: komendy RPC, na które firmware zdecyduje się odpowiedzieć |
| Sonda debug CMSIS-DAP (HID) | **Mostek SWD** do portu debug EFR32 | pyOCD, skrypty flashujące; a także każdy inny z darmowymi narzędziami |

Każdy, kto ma dongle w ręku, może więc podłączyć go do laptopa, zainstalować pyOCD (`pip install pyocd`) i jedną komendą zrzucić cały układ. Bez otwierania obudowy, bez lutowania, bez specjalnego sprzętu. To jest „skrót SWD” i dlatego niezablokowany dongle nigdy nie może opuścić fabryki.

**Secure Engine (SE)** to jedyny element, który może zamknąć te drzwi. Blokada debug każe SE utrzymywać AHB-AP (ścieżkę dostępu do pamięci/CPU) wyłączony przy każdym uruchomieniu. W stanie zablokowanym przez SWD dostępny pozostaje tylko **Debug Challenge Interface (DCI)** SE: wąska skrzynka pocztowa, która przyjmuje wyłącznie komendy SE (odczyt stanu blokady, pobranie challenge'u, device erase, podpisane odblokowanie). Nie daje dostępu do pamięci.

> W tym projekcie odblokowanie **nie** przechodzi przez DCI. Firmware pobiera challenge i przekazuje podpisany token do SE przez szeregowe RPC po USB (`0x62` / `0x63`). Efekt jest ten sam: SE weryfikuje token i ponownie otwiera AHB-AP do najbliższego resetu.

### 6.2 Odczyt pamięci dongla

| | (a) nigdy nie zablokowany | (b) zablokowany (secure debug lock) | (c) zablokowany, potem odblokowany do resetu |
|---|---|---|---|
| **Port szeregowy USB (RPC)** | Tylko to, na co pozwala firmware: status, logi, sprawdzenie licencji. Brak surowych odczytów pamięci. | **To samo** | **To samo** |
| **SWD: flash, RAM, NVM3, rejestry** | **Wszystko**, dla każdego z kablem USB | **Nic**: SE trzyma port zamknięty | **Wszystko**, do najbliższego resetu |
| **Klucze wewnątrz SE** (klucz tożsamości dongla) | Nieczytelne w postaci jawnej (przechowywane opakowane unikalnym dla układu kluczem PUF) | Nieczytelne | Nieczytelne |

Blokada w ogóle nie zmienia kanału szeregowego USB. Zamyka tylko SWD.

### 6.3 Flashowanie

| | (a) nigdy nie zablokowany | (b) zablokowany (secure debug lock) | (c) odblokowany do resetu |
|---|---|---|---|
| **Zwykłe flashowanie** (`flash.bat`, `set_*_mode.bat`) | Każdy; NVM3 (licencja, tożsamość) zostaje zachowane | **Niemożliwe** | Możliwe; działa jak (a) do resetu |
| **Ponowny provisioning** (`provision_dongle.py`) | Tak | Najpierw uruchom `secure_debug_lock.py unlock` (kontrola wstępna odrzuca zablokowany port SWD) | Tak |
| **Device erase** | Tak | Tak, ale **kasuje flash i RAM**: firmware, licencję, tożsamość (strona User Data z zaszyfrowanym logiem tamper przetrwa) | Tak |
| **Co przetrwa kasowanie** | — | Command Key w OTP: układ pozostaje związany z tym kluczem na zawsze | To samo |

### 6.4 Powierzchnia ataku dla inżynierii wstecznej

**(a) Nigdy nie zablokowany: szeroko otwarty dla każdego z kablem USB.**
* **Zrzut całego firmware'u**, łącznie z tajnymi obliczeniami Compass, i deasemblacja offline.
* **Debugowanie na żywo:** zatrzymanie CPU w trakcie komunikacji Compass z donglem i odczyt kluczy sesji oraz wyników z RAM; przechodzenie krok po kroku przez sprawdzanie licencji i RTC.
* **Łatanie i ponowne flashowanie z zachowaniem NVM3.** Na przykład wgranie firmware'u z usuniętym sprawdzaniem licencji. Nadal ma oryginalny certyfikat podpisany przez Root CA, więc Compass uznaje go za autentyczny. To najgorszy scenariusz.
* Wykorzystanie dongla jako wyroczni algorytmu przez debugger.

**(b) Zablokowany (secure debug lock): SWD znika.** Co zostaje:
* **Protokół szeregowy USB:** fuzzing, błędy logiczne w obsłudze RPC, ataki na sesję ECDHE. Jest identyczny we wszystkich trzech trybach i staje się główną powierzchnią ataku.
* **Device erase:** daje atakującemu pusty układ. Bez firmware'u, bez licencji, bez certyfikatu; firmware napisany przez atakującego Compass odrzuci, bo nie ma tożsamości podpisanej przez Root CA. Nic przydatnego nie zyskuje.
* **Ataki fizyczne:** glitching napięcia lub zegara, aby pominąć sprawdzenie blokady przez SE (układ ma detektory glitchy i tamper, a logika anti-tamper firmware'u na nie reaguje), albo zdjęcie obudowy z samego układu (decapping). Wymagają drogiego sprzętu i wiedzy.
* **Kradzież `debug_command_key.pem`.** To dziś realna słabość: klucz deweloperski jest w git, więc każdy z dostępem do repozytorium może odblokować każdy dongle nim zablokowany. Produkcja dostaje więc nowy klucz przechowywany offline (sekcja 5).

**(c) Zablokowany, potem odblokowany do resetu:** to samo co (a), ale tylko do najbliższego resetu po włączeniu zasilania lub resetu urządzenia. Dotarcie tu wymaga ważnego tokenu odblokowującego:
* Każdy token jest związany z **numerem seryjnym tego układu** i jego **bieżącym challenge'em SE**, więc na innym donglu jest bezużyteczny. Challenge nie jest zmieniany, więc token działałby dalej na tym samym układzie; keyadmin nigdy go nie przechowuje, a istnieje on tylko w fabryce, w pamięci, podczas odblokowania.
* Okno istnieje tylko wtedy, gdy dongle jest w laboratorium. Po resecie wraca do trybu (b).

**Podsumowanie:** (a) nigdy nie jest akceptowalne dla klienta, bo dongle nosi w sobie własny debugger. (b) to stan wysyłkowy. (c) to okno serwisowe, które może otworzyć tylko posiadacz kluczy, i które zamyka się przy resecie.

> **Status weryfikacji na sprzęcie (2026-10-27, dongle `0000000000000000880F62FFFE3E183B`):** blokada założona i zweryfikowana (`CMD_KEY:MATCH`, `SECURE_DEBUG:1`, `LOCK_APPLIED:1`); odblokowanie challenge-response zaakceptowane przez SE; odczyty SWD potwierdzone w stanie odblokowanym (tablica wektorów pod `0x08000000`, Black Box w starej lokalizacji `0x0817E000`, obecnie przeniesiony na stronę User Data `0x0FE00000`). Programowy reset przez pyOCD **nie** zamknął ponownie portu; ponowne zablokowanie po resecie pinem (przycisk RESET) lub po resecie zasilania z odłączoną baterią wciąż wymaga potwierdzenia.
