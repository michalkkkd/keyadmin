# Architektura oprogramowania

## A. KeySec (Python na PC)
**Główny plik:** `keycomm/core/transport.py`
Aplikacja sterująca w Windows, wysyłająca polecenia. Utrzymuje połączenie szeregowe. Problemy z desynchronizacją bufora rozwiązaliśmy w niej za pomocą `reset_input_buffer()` i celowo wyłączyliśmy poleganie na sprzętowym resecie DTR, co zapewnia stabilne, płynne połączenie (odczyt w pętli, bez metody `read_all` — takiej w kodzie nie ma).

## B. KeyFirmware (C na krzemie)
**Główny plik:** `app.c` w IDE (Simplicity Studio).
Firmware, który stale nasłuchuje na porcie VCOM (bez blokowania rdzenia) przy użyciu natywnego SDK: czyta porcjami do bufora przez `sl_iostream_read` (`app.c`) i dekoduje **ramki TinyFrame** (`TF_Accept`) — protokół jest binarny, nie liniowy (brak `sl_iostream_getchar`). Zdekodowane ramki wywołują procedury RPC, a odpowiedź odsyła `sl_iostream_write()`.

### INSTRUKCJE KOMPILACJI DLA AGENTA
1. Kompilacja: cd cmake_gcc && cmake --build --preset default_config
2. Flashowanie: .\xiao_mg24_flash.bat (lub skrypt Python) w katalogu cmake_gcc\build\base.

## Strategia TrustZone i architektura docelowa (faza 3+)
Docelowo kod zostanie podzielony na dwa fizyczne projekty, których rozdział wymusza procesor Cortex-M33 (ARM TrustZone):
1. **Świat Non-Secure (projekt B):** Obsługuje otwarty kod, operacje USB i UART, pętlę zdarzeń (`app.c`, warstwa routingu `src/core/router_common.c` + routery domenowe `diag_router.c`/`debug_lock_router.c`/`tamper_otp_router.c`, `src/admin/admin_router.c`; init `firmware_router_init`) oraz surowy dysk NVM3 (security_nvm.c). *(Uwaga: pliku `rpc_router.c` nie ma — routing jest w `router_common.c`.)*
2. **Świat Secure (projekt A):** Wzmocnione środowisko. Znajdzie się tu logika weryfikująca ważność licencji (security_rtc.c) oraz główna, tajna logika algorytmów (compass_core.cpp). Ten kod korzysta z bramek NSC (Non-Secure Callables), dzięki którym strona Non-Secure może odpytywać strefę bezpieczną.
