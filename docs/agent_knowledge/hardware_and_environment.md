# Sprzęt i środowisko (ważne informacje)

* **Główny mikrokontroler:** EFR32MG24B220F1536IM48 (Silicon Labs) - na nim działa logika `app.c`. Ma Secure Vault (sprzętowy moduł bezpieczeństwa) obsługujący anti-tampering (ochronę przed fizyczną ingerencją), kryptografię i bezpieczne przechowywanie kluczy.
* **Płytka deweloperska:** Seeed Studio XIAO MG24.
* **Mostek / debugger:** Na spodzie płytki znajduje się ukryty koprocesor **SAMD11**. Pełni on rolę sprzętowego debuggera (CMSIS-DAP) i mostka USB-UART. Oznacza to, że Windows komunikuje się z SAMD11, a SAMD11 przekazuje dane do EFR32.
* **KRYTYCZNA ZASADA:** **Nigdy nie przytrzymuj przycisku RESET na płytce podczas podłączania jej kablem USB.** Spowoduje to przejście SAMD11 w tryb bootloadera, co całkowicie wyłącza interfejs debuggera CMSIS-DAP i uniemożliwia flashowanie płytki. Podłącz kabel USB normalnie, niczego nie wciskając.

## Aktywowane moduły i komponenty (w Simplicity Studio)

Podczas konfiguracji projektu (`bt_soc_empty`.slcp) dodaliśmy do rdzenia EFR32 następujące komponenty:

* **IO Stream: USART** (instancja: `vcom`): 
  * Mapowanie pinów: PA08 (TX) i PA09 (RX).
  * Prędkość transmisji (baud rate): 115200.
  * Przeznaczenie: fizyczne poprowadzenie komunikacji z procesora EFR32 do mostka SAMD11.
* **Retarget STDIO**: 
  * Przeznaczenie: historycznie obsługa printf(). Pozwala przekierować standardowe strumienie wejścia/wyjścia (C) na wybrany interfejs (u nas: `vcom`).
* **Power Manager**: 
  * Przeznaczenie: sterowanie stanami uśpienia. Poleceniem sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1); blokujemy przejście procesora w głębokie uśpienie (Deep Sleep, EM2), które uniemożliwiłoby poprawną, bezstratną komunikację UART.
* **cJSON** (biblioteka zewnętrzna):
  * Dodaliśmy bibliotekę sprzętową z GitHuba do profesjonalnego i bezpiecznego parsowania obiektów JSON, zamiast prymitywnych i dziurawych metod skanowania tekstu.


## UWAGA PRODUKCYJNA: bateria RTC
Obecna płytka deweloperska (Seeed Studio XIAO MG24) nie ma fizycznej baterii RTC (podtrzymującej zegar czasu rzeczywistego), jednak **docelowy sprzęt produkcyjny BĘDZIE miał dedykowaną baterię RTC**. Architektura oprogramowania powinna uwzględniać tę przyszłą możliwość.