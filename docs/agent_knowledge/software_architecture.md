# Architektura oprogramowania

## A. KeySec (Python na PC)
**Główny plik:** compass_rpc.py (oraz nowszy `transport.py`)
Aplikacja sterująca w Windows, wysyłająca polecenia. Utrzymuje połączenie szeregowe. Problemy z desynchronizacją bufora rozwiązaliśmy w niej za pomocą `reset_input_buffer()` i celowo wyłączyliśmy poleganie na sprzętowym resecie DTR, co zapewnia stabilne, płynne połączenie (odczyt porcjami przez `read_all`).

## B. KeyFirmware (C na krzemie)
**Główny plik:** `app.c` w IDE (Simplicity Studio).
Firmware, który stale nasłuchuje na porcie VCOM (bez blokowania rdzenia) przy użyciu natywnego SDK (sl_iostream_getchar). Parsuje pełne linie i wywołuje procedury RPC. Odpowiedź odsyła błyskawiczną funkcją sl_iostream_write(), dodając mikrosekundowe opóźnienie blokujące (sl_sleeptimer_delay_millisecond), aby dane fizycznie zdążyły opuścić port przed kolejnym tickiem stosu Bluetooth.

### INSTRUKCJE KOMPILACJI DLA AGENTA
1. Kompilacja: cd cmake_gcc && cmake --build --preset default_config
2. Flashowanie: .\xiao_mg24_flash.bat (lub skrypt Python) w katalogu cmake_gcc\build\base.

## Strategia TrustZone i architektura docelowa (faza 3+)
Docelowo kod zostanie podzielony na dwa fizyczne projekty, których rozdział wymusza procesor Cortex-M33 (ARM TrustZone):
1. **Świat Non-Secure (projekt B):** Obsługuje otwarty kod, operacje USB i UART, pętlę zdarzeń (`app.c`, `rpc_router.c`, `admin_cli.c`) oraz surowy dysk NVM3 (security_nvm.c).
2. **Świat Secure (projekt A):** Wzmocnione środowisko. Znajdzie się tu logika weryfikująca ważność licencji (security_rtc.c) oraz główna, tajna logika algorytmów (compass_core.cpp). Ten kod korzysta z bramek NSC (Non-Secure Callables), dzięki którym strona Non-Secure może odpytywać strefę bezpieczną.
