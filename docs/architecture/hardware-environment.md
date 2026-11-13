# Sprzęt i środowisko (ważne informacje)

* **Główny mikrokontroler:** EFR32MG24B220F1536IM48 (Silicon Labs) - na nim działa logika `app.c`. Ma Secure Vault (sprzętowy moduł bezpieczeństwa) obsługujący anti-tampering (ochronę przed fizyczną ingerencją), kryptografię i bezpieczne przechowywanie kluczy.
* **Płytka deweloperska:** Seeed Studio XIAO MG24.
* **Mostek / debugger:** Na spodzie płytki znajduje się ukryty koprocesor **SAMD11**. Pełni on rolę sprzętowego debuggera (CMSIS-DAP) i mostka USB-UART. Oznacza to, że Windows komunikuje się z SAMD11, a SAMD11 przekazuje dane do EFR32.
* **KRYTYCZNA ZASADA:** **Nigdy nie przytrzymuj przycisku RESET na płytce podczas podłączania jej kablem USB.** Spowoduje to przejście SAMD11 w tryb bootloadera, co całkowicie wyłącza interfejs debuggera CMSIS-DAP i uniemożliwia flashowanie płytki. Podłącz kabel USB normalnie, niczego nie wciskając.

## Aktywowane moduły i komponenty (w Simplicity Studio)

Podczas konfiguracji projektu (`keyfirmware.slcp`) dodaliśmy do rdzenia EFR32 następujące komponenty:

* **IO Stream: EUSART** (instancja: `Io_Stream_USERT`, pełni rolę VCOM): 
  * Mapowanie pinów: PA08 (TX) i PA09 (RX).
  * Prędkość transmisji (baud rate): 921600 (`SL_IOSTREAM_EUSART_IO_STREAM_USERT_BAUDRATE`).
  * Przeznaczenie: fizyczne poprowadzenie komunikacji z procesora EFR32 do mostka SAMD11.
* **Retarget STDIO**: 
  * Przeznaczenie: historycznie obsługa printf(). Pozwala przekierować standardowe strumienie wejścia/wyjścia (C) na wybrany interfejs (u nas: `vcom`).
* **Power Manager**: 
  * Przeznaczenie: sterowanie stanami uśpienia. Wymaganie `sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1)` jest trzymane **tylko podczas aktywnej komunikacji** (blokuje wtedy EM2, by nie gubić bajtów UART); po utracie heartbeatu wymaganie jest zdejmowane i dongle **celowo schodzi do EM2** na baterii (zob. [`../firmware/power-and-sleep.md`](../firmware/power-and-sleep.md)).
* **cJSON** (biblioteka zewnętrzna):
  * Dodaliśmy bibliotekę sprzętową z GitHuba do profesjonalnego i bezpiecznego parsowania obiektów JSON, zamiast prymitywnych i dziurawych metod skanowania tekstu.


## UWAGA PRODUKCYJNA: bateria RTC
Obecna płytka (Seeed Studio XIAO MG24) **ma** fizyczne ogniwo LiPo (Akyga LP301525), które podtrzymuje całość układu — w tym SYSRTC zegara licencji — po odłączeniu USB, ale **nie ma osobnej, dedykowanej baterii domeny RTC** (podtrzymującej wyłącznie zegar przy całkowitym zaniku zasilania). Docelowy sprzęt produkcyjny może dostać dedykowaną baterię RTC; architektura oprogramowania powinna uwzględniać tę możliwość.

## Odkrycia i pułapki (kluczowe notatki)

* **Zegar licencji (bateria na stałe):** EFR32MG24 nie ma RTC z podtrzymaniem bateryjnym, ale bateria zasila cały układ, więc po odłączeniu USB MCU śpi w EM2, a licznik SYSRTC (32 768 Hz) dalej liczy. Świat Secure nie może używać sleeptimera (jego kopia w obrazie Secure nigdy nie jest inicjalizowana, `sl_sleeptimer_get_timer_frequency()` zwraca 0), więc czyta licznik sam i sumuje przyrosty (`security_rtc.c`), koniecznie przez `SYSRTC0_NS` (w buildzie Secure samo `SYSRTC0` to alias Secure → fault). Pętla NS woła `nsc_rtc_process()` co 30 s. Licznik zeruje się przy resecie, dlatego czas Unix trafia co 60 s do NVM3 (checkpoint), a po resecie zegar rusza od checkpointu + 150 s kary. Dawny model `boot_time + uptime` cofał zegar do daty provisioningu — nie wracać. Szczegóły: [`../security/time-license.md`](../security/time-license.md).
* **Błąd LF→CRLF w SiLabs SDK:** domyślnie `sl_iostream_eusart` działa jak terminal tekstowy i zamienia `0x0A` na `0x0D 0x0A`, co psuje binarne ramki TinyFrame (bajty payloadu / sumy CRC). Rozwiązanie: w `config/sl_iostream_eusart_Io_Stream_USERT_config.h` ustawić `...CONVERT_BY_DEFAULT_LF_TO_CRLF` na `0`.
* **Diagnostyka pamięci i linker:** zamiast sztywnych offsetów do liczenia zużycia Flash/RAM mapujemy symbole GNU Linkera (`__etext`, `__data_start__`, `__HeapBase`, `__HeapLimit`) przez `MSG_MEM_INFO`.
* **Newlib-nano i wartości 64-bit:** lekka `newlib-nano` (domyślna dla Cortex-M33 w SiLabs) może wywołać HardFault przy `printf`/`snprintf` wartości 64-bitowej przez `%llu`. Rzutować w dół do u32, gdy bezpieczne.