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
  * Przeznaczenie: sterowanie stanami uśpienia. Wymaganie `sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1)` jest trzymane **tylko podczas aktywnej komunikacji** (blokuje wtedy EM2, by nie gubić bajtów UART); po utracie heartbeatu wymaganie jest zdejmowane i dongle **celowo schodzi do EM2** na baterii (zob. `features/battery_sleep.md`).
* **cJSON** (biblioteka zewnętrzna):
  * Dodaliśmy bibliotekę sprzętową z GitHuba do profesjonalnego i bezpiecznego parsowania obiektów JSON, zamiast prymitywnych i dziurawych metod skanowania tekstu.


## UWAGA PRODUKCYJNA: bateria RTC
Obecna płytka (Seeed Studio XIAO MG24) **ma** fizyczne ogniwo LiPo (Akyga LP301525), które podtrzymuje całość układu — w tym SYSRTC zegara licencji — po odłączeniu USB, ale **nie ma osobnej, dedykowanej baterii domeny RTC** (podtrzymującej wyłącznie zegar przy całkowitym zaniku zasilania). Docelowy sprzęt produkcyjny może dostać dedykowaną baterię RTC; architektura oprogramowania powinna uwzględniać tę możliwość.