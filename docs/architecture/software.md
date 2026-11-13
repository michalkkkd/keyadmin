# Architektura oprogramowania i podział repozytoriów

> **Kanon architektury.** Główne pliki, podział TrustZone, dwupoziomowy podział repozytoriów (KeyFirmware i KeySec) oraz tabela komend protokołu TinyFrame.

## A. KeySec (Python na PC)
**Główny plik:** `keycomm/core/transport.py`
Aplikacja sterująca w Windows, wysyłająca polecenia. Utrzymuje połączenie szeregowe. Problemy z desynchronizacją bufora rozwiązaliśmy w niej za pomocą `reset_input_buffer()` i celowo wyłączyliśmy poleganie na sprzętowym resecie DTR, co zapewnia stabilne, płynne połączenie (odczyt w pętli, bez metody `read_all` — takiej w kodzie nie ma).

## B. KeyFirmware (C na krzemie)
**Główny plik:** `app.c` w IDE (Simplicity Studio).
Firmware, który stale nasłuchuje na porcie VCOM (bez blokowania rdzenia) przy użyciu natywnego SDK: czyta porcjami do bufora przez `sl_iostream_read` (`app.c`) i dekoduje **ramki TinyFrame** (`TF_Accept`) — protokół jest binarny, nie liniowy (brak `sl_iostream_getchar`). Zdekodowane ramki wywołują procedury RPC, a odpowiedź odsyła `sl_iostream_write()`.

### Instrukcje kompilacji dla agenta
1. Kompilacja: `cd cmake_gcc && cmake --build --preset default_config`
2. Flashowanie: `.\flash.bat` (lub `python xiao_mg24_flash.py`) w katalogu `KeyFirmware/flashbat/`; domyślnie wgrywa `cmake_gcc/build/base/keyfirmware.hex`.

Narzędzia build/flash i provisioning opisuje [`../security/provisioning.md`](../security/provisioning.md).

## C. Podział TrustZone (Cortex-M33)

Kod jest podzielony na dwa światy, których rozdział wymusza procesor:

1. **Świat Non-Secure:** otwarty kod, operacje USB/UART, pętla zdarzeń (`app.c`), warstwa routingu `src/core/router_common.c` + routery domenowe (`diag_router.c` / `debug_lock_router.c` / `tamper_otp_router.c`, `src/admin/admin_router.c`; init `firmware_router_init`) oraz surowy dysk NVM3 (`security_nvm.c`). *(Uwaga: pliku `rpc_router.c` nie ma — routing jest w `router_common.c`.)*
2. **Świat Secure:** wzmocnione środowisko. Logika licencji (`security_rtc.c`), limit użytkowników, krypto i tajna logika algorytmów (`compass_core.cpp`). Korzysta z bramek NSC (Non-Secure Callables), przez które strona Non-Secure odpytuje strefę bezpieczną.

---

## D. Dwupoziomowy podział repozytoriów

Cel: zapobiec **wyciekowi IP (algorytmów) w produkcji fabrycznej** oraz **backdoorom administracyjnym u klienta**. Ścisły, fizyczny podział po obu stronach — firmware (C) i PC (Python).

### D.1 KeyFirmware (dwa rozłączne binaria z jednego repo)

CMake ([`cmake_gcc/CMakeLists.txt`](../../../KeyFirmware/cmake_gcc/CMakeLists.txt)) generuje dwa pliki HEX:

1. **Produkcyjny (`keyfirmware.hex` — dla klientów)**
   - **Brak funkcji administracyjnych:** moduły `src/admin/admin_router.c`, `src/admin/admin_cli.c` są **fizycznie wycięte** na etapie kompilacji. Komendy admina (`MSG_ADMIN_*`, `MSG_PROVISION_IDENTITY`, `MSG_SAVE_CERTIFICATE`) trafiają do domyślnego handlera → `ERR: Unknown command (ID)`.
   - **Pełne IP:** statycznie zlinkowane wszystkie algorytmy (`src/prod/compass_core.cpp`, `src/prod/logic/*.c`), bufory robocze ~135 KB SRAM.
   - **Diagnostyka:** odczyt tamper/baterii/logów RAM + tymczasowa diagnostyka pre-produkcyjna.

2. **Fabryczny (`keyfirmware_prov.hex` — tylko wewnętrznie)**
   - **Brak kodu medycznego:** ani linijki `src/prod/` — monterzy ani zrzut Flash nie ujawnią algorytmów.
   - **Pełna konfiguracja:** `admin_router.c` / `admin_cli.c` — RTC, licencja, limit użytkowników, generacja klucza tożsamości (`auth_manager`), zapis certyfikatu.
   - **<6 KB SRAM**, bez buforów symulacyjnych.

### D.2 KeySec (dwa pakiety Python)

1. **`keycomm` (runtime, zaszywany w Compass u klienta):** ramkowanie TinyFrame + `SerialTransport`, handshake ECDHE (`SecureChannel`) + walidacja certyfikatu wobec `root_ca_pub.pem`, AES-256-GCM, wysokopoziomowe API (`CompassApi`: licencja, limit, `execute_*`). **Żadnej** logiki admina ani kluczy prywatnych.
2. **`keyadmin` (narzędzia fabryczne, wewnętrzne):** `provision_dongle.py` (zob. [`../security/provisioning.md`](../security/provisioning.md)), konsola diagnostyczna `keyadmin/main.py`. Klucze prywatne (`root_ca_key.pem`, `debug_command_key.pem`, `tamper_log_key.bin`) tylko w `keyadmin/keys/`, nigdy w dystrybucji klienckiej.

---

## E. Tabela komend protokołu TinyFrame

Obsługa komend w obu wersjach firmware. „Nie (Odrzucona)" = kod nie zarejestrowany w routerze danej kompilacji → `ERR: Unknown command (ID)`.

| Opcode | Hex | Nazwa | Fabryczna | Produkcyjna | Działanie |
| :--- | :---: | :--- | :---: | :---: | :--- |
| `MSG_PING` | `0x01` | Ping / Heartbeat | Tak | Tak | Łączność, mignięcie LED, blokada EM2. |
| `MSG_CHECK_LIC` | `0x02` | Sprawdzenie licencji | Tak | Tak | Weryfikacja licencji (RTC + NVM3), wydanie tokenu VRX. |
| `MSG_ADMIN_DATE` | `0x03` | Ustawienie daty RTC | Tak | Nie | Tylko fabryczna; bazowy czas w NVM3. |
| `MSG_ADMIN_LIC` | `0x04` | Ustawienie licencji | Tak | Nie | Tylko fabryczna; czas licencji (dni). |
| `MSG_ADMIN_WIPE` | `0x05` | Reset fabryczny | Tak | Nie | Tylko fabryczna; `nvm3_eraseAll`. |
| `MSG_TEST_ADD` | `0x06` | Algorytm testowy `alg1` | Nie | Tak | Obliczenia testowe + rejestracja użytkownika. |
| `MSG_DEBUG_TIME` | `0x07` | Diagnostyka RTC | Tak | Nie (factory; [`../security/diagnostics.md`](../security/diagnostics.md)) | Rejestry RTC, synchronizacja. |
| `MSG_ADMIN_USERS` | `0x08` | Limit użytkowników | Tak | Nie | Tylko fabryczna; max stanowisk w NVM3. |
| `MSG_COMPASS_USERS` | `0x09` | Odczyt limitu | Tak | Tak | Limit + liczba aktywnych sesji. |
| `MSG_MEM_INFO` | `0x0A` | Diagnostyka pamięci | Tak | Nie (factory) | Flash/SRAM/sterta. |
| `MSG_PROVISION_IDENTITY` | `0x0B` | Klucz tożsamości | Tak | Nie | SECP256R1 w koprocesorze. |
| `MSG_SAVE_CERTIFICATE` | `0x0C` | Zapis certyfikatu | Tak | Nie | Certyfikat Root CA w NVM3. |
| `MSG_HANDSHAKE_INIT` | `0x0D` | Handshake ECDHE | Tak | Tak | Wymiana kluczy P-256, klucz sesji. |
| `MSG_BATTERY_INFO` | `0x0E` | Stan baterii | Tak | Nie (factory) | Napięcie/ładowanie przez IADC. |
| `MSG_NVM_DIAG` | `0x0F` | Diagnostyka NVM3 | Tak | Nie (factory) | Licznik kasowań, wolne miejsce. |
| `MSG_SYS_HEALTH` | `0x10` | Status / anti-tamper | Tak | Nie (factory) | TamperEvents, temperatura, TamperLog:N. |
| `MSG_GET_LOG_SIZE` | `0x11` | Rozmiar logów RAM | Tak | Tak | Długość bufora logów. |
| `MSG_GET_LOG_CHUNK` | `0x12` | Fragment logu | Tak | Tak | Chunk z 10 KB bufora cyklicznego. |
| `MSG_DIAG_BEGIN/_DATA/_NEXT` | `0x13/0x14/0x17` | Strumień DIAG | Tak | Tak | Bez sesji; szyfrowany AES-128-GCM (Tamper Log Key). Zob. [`../security/diagnostics.md`](../security/diagnostics.md). |
| `MSG_COMPASS_SIM_PK` | `0x15` | Symulacja PK | Nie | Tak | PK z kontrolą licencji/użytkowników. |
| `MSG_VRX` | `0x16` | Weryfikacja/unieważnienie VRX | Nie | Tak | Rotacja tokenów VRX (zob. [`../security/users-limit.md`](../security/users-limit.md)). |
| `MSG_SIM_PK_GI_*` | `0x30`-`0x33` | Symulacja Motility | Nie | Tak | Szyfrowany potok (JSON/chunks). |
| `MSG_SAFE_SPACE_*` | `0x40`-`0x45` | Safe Space | Nie | Tak | Granice parametrów FaSSGF/FaSSIF. |
| `MSG_SSP_*` | `0x50`-`0x58` | Wykresy Safe Space | Nie | Tak | Chmura punktów, krzywe rozpuszczania. |
| `MSG_DEBUG_LOCK_*` | `0x60`-`0x63` | Secure Debug | Tak | Tak | Jawne; token weryfikuje SE. Zob. [`../security/secure_debug_lock.md`](../security/secure_debug_lock.md). |
| `MSG_TAMPER_OTP_*` | `0x64`-`0x65` | SE OTP tamper: status, arm | Tak | Tak | `ARM` wypala poziomy tamper + secure boot OFF do OTP (pieczętowanie; `--no-lock` pomija). |

**Szyfrowanie w wersji produkcyjnej:** `MSG_CHECK_LIC`, `MSG_VRX`, `MSG_COMPASS_USERS`, `MSG_GET_LOG_*`, `MSG_TEST_ADD`, `MSG_COMPASS_SIM_PK`, `MSG_SIM_PK_GI_*`, `MSG_SAFE_SPACE_*`, `MSG_SSP_*` wymagają aktywnej sesji (AES-256-GCM z AAD: typ komendy, OK/ERR). Jawne: `MSG_PING`, `MSG_HANDSHAKE_INIT`, `MSG_DEBUG_LOCK_*`; w fabrycznej także komendy admina i diagnostyka tekstowa. Produkcyjna oddaje diagnostykę tylko szyfrowanym strumieniem DIAG.
