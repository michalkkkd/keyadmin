# Architektura Oprogramowania

## A. KeySec (Python na PC)
**Glowny plik:** compass_rpc.py (i nowszy transport.py)
Aplikacja kontrolna z Windowsa wysylajaca polecenia. Utrzymuje polaczenie szeregowe. Rozwiazalismy w niej problemy desynchronizacji buforow za pomoca eset_input_buffer() oraz celowo wylaczylismy poleganie na sprzetowym resecie DTR, zapewniajac stale, plynne polaczenie (czytanie w paczkach przez ead_all).

## B. KeyFirmware (C na krzemie)
**Glowny plik:** pp.c w srodowisku (Simplicity Studio).
Firmware, ktory na okraglo (bez blokowania rdzenia) nasluchuje portu VCOM przy pomocy natywnego SDK (sl_iostream_getchar). Parsuje cale linie i wywoluje procedury RPC. Odsyla odpowiedz przy uzyciu blyskawicznego sl_iostream_write(), dodajac mikrosekundowe opoznienie blokujace (sl_sleeptimer_delay_millisecond), by dac fizyczny czas danym na opuszczenie portu przed kolejnym taktem stosu Bluetooth.

### INSTRUKCJE KOMPILACJI DLA AGENTA
1. Aby skompilowac: cd cmake_gcc && cmake --build --preset default_config
2. Aby wgrywac: .\xiao_mg24_flash.bat (lub skrypt w Pythonie) znajdujacy sie w cmake_gcc\build\base.

## Strategia TrustZone i Architektura Docelowa (Faza 3+)
Docelowo kod zostanie podzielony na dwa fizyczne projekty wymuszane przez procesor Cortex-M33 (ARM TrustZone):
1. **Non-Secure World (Projekt B):** Zajmuje sie otwartym kodem, oblusga USB, UART, petla zdarzen (app.c, rpc_router.c, admin_cli.c) i surowym dyskiem NVM3 (security_nvm.c).
2. **Secure World (Projekt A):** Srodowisko ufortyfikowane. Znajdzie sie tu logika sprawdzajaca waznosc licencji (security_rtc.c) oraz glowna, tajna logika algorytmow (compass_core.cpp). Ten kod wykorzystuje bramki NSC (Non-Secure Callables), by z Non-Secure odpytywac bezpieczna strefe.
