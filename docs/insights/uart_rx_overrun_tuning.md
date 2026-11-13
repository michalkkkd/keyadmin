# Strojenie przepełnienia odbioru UART (RX overrun) i stabilności

## Problem (15-sekundowe zawieszenia)
Podczas ekstremalnych testów obciążeniowych (1000 kolejnych żądań kryptograficznych z opóźnieniem 0 ms) mikrokontroler EFR32MG24 gubił bajty z przychodzących pakietów TinyFrame, co prowadziło do TimeoutError po stronie Pythona i wcześniej powodowało 15-sekundowe zawieszenia systemu.

## Analiza przyczyny źródłowej
1. **Brak sprzętowego sterowania przepływem (RTS/CTS)**: System korzysta z prostego, 2-przewodowego połączenia UART (TX/RX) przez mostek USB-UART SAMD11 (CMSIS-DAP, na płytce XIAO MG24). PC wysyła dane z maksymalną prędkością USB, bez żadnej możliwości, by MCU mógł zdławić (throttle) przychodzący strumień.
2. **Mały sprzętowy FIFO**: Peryferium EUSART układu EFR32MG24 ma sprzętowy FIFO (bufor) o pojemności dokładnie 16 bajtów.
3. **Mały programowy bufor RAM**: Sterownik sl_iostream używa DMA do przenoszenia bajtów ze sprzętowego FIFO do pamięci RAM. Domyślna konfiguracja Simplicity Studio dla `SL_IOSTREAM_EUSART_IO_STREAM_USERT_RX_BUFFER_SIZE` wynosiła jednak zaledwie **32 bajty**.
4. **Zagłodzenie CPU (CPU starvation)**: Podczas szyfrowania/odszyfrowywania AES-256-GCM (mbedTLS/PSA) CPU mikrokontrolera jest zablokowany w bare-metalowej superpętli while(1). 
5. **Przepełnienie**: Nasze zaszyfrowane żądanie TinyFrame ma długość 51 bajtów. Gdy CPU jest zajęty szyfrowaniem poprzedniej odpowiedzi, Python wysyła kolejne 51-bajtowe żądanie. DMA zapełnia 32-bajtowy bufor RAM, sprzętowy FIFO zapełnia swoje 16 bajtów (łącznie 48 bajtów). Pozostałe 3 bajty przepełniają bufor i są bezpowrotnie tracone. Gdy CPU kończy szyfrowanie, zastaje uszkodzony, niekompletny pakiet.

## Rozwiązanie (strojenie buforów)
Aby definitywnie usunąć wąskie gardło bez migracji do RTOS (co dodałoby znaczną złożoność i potencjalne wyścigi (race conditions) w warstwie kryptograficznej), przeprowadziliśmy następujące strojenie zasobów:

1. **Zwiększenie bufora RX sl_iostream (MCU)**
   - **Plik**: KeyFirmware/config/sl_iostream_eusart_Io_Stream_USERT_config.h
   - **Zmiana**: Zwiększono `SL_IOSTREAM_EUSART_IO_STREAM_USERT_RX_BUFFER_SIZE` z 32 do **2048** bajtów.
   - **Wpływ**: Wykorzystuje ok. 0,8% z 256 KB pamięci RAM układu EFR32MG24, ale pozwala DMA bezpiecznie wchłonąć kilkadziesiąt pełnych zaszyfrowanych żądań, gdy CPU jest zajęty kryptografią.

2. **Zwiększenie bufora aplikacji (MCU)**
   - **Plik**: KeyFirmware/src/rpc_router.c
   - **Zmiana**: Zwiększono lokalne tablice składania payloadu char out_buf[64] do char out_buf[256].
   - **Wpływ**: Zapewnia warstwie aplikacji wystarczającą ilość pamięci stosu, aby bezpiecznie przetwarzać większe pakiety.

3. **Zoptymalizowana logika timeoutu w Pythonie (PC)**
   - **Plik**: KeySec/api/compass_api.py i KeySec/core/protocol.py
   - **Zmiana**: Zmniejszono timeout execute_command z 15,0 s do 0,5 s i dodano 0,2 s opóźnienia na odzyskanie po uszkodzeniu pakietu.
   - **Wpływ**: Jeśli w przyszłości poważna usterka sprzętowa lub zakłócenie EMI nadal uszkodzi bajt, Python wykryje brakującą odpowiedź w 500 ms (zamiast 15 sekund), po cichu odzyska sprawność i bezbłędnie ponownie wyśle pakiet.
