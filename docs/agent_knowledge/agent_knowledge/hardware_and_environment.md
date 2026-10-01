# Sprzet i Srodowisko (Wazne Informacje)

* **Mikrokontroler Glowny:** EFR32MG24B220F1536IM48 (Silicon Labs) - to na nim dziala funkcja pp.c. Posiada Secure Vault wspierajacy anty-tampering, kryptografie i bezpieczne przechowywanie kluczy.
* **Plytka Deweloperska:** Seeed Studio XIAO MG24.
* **Mostek / Debugger:** Na spodzie plytki znajduje sie ukryty koprocesor **SAMD11**. Sluzy on jako sprzetowy debugger (CMSIS-DAP) oraz mostek USB-UART. Oznacza to, ze Windows rozmawia z SAMD11, a SAMD11 przekazuje informacje do EFR32.
* **KRYTYCZNA ZASADA:** **Nigdy nie trzymaj wcisnietego przycisku RESET na plytce podczas podlaczania jej do kabla USB.** Spowoduje to wejscie SAMD11 w tryb bootloadera, calkowicie wylaczajac interfejs debuggera CMSIS-DAP i uniemozliwiajac flashowanie plytki. Wkladaj kabel USB normalnie, bez wciskania czegokolwiek.

## Aktywowane Moduly i Komponenty (w Simplicity Studio)

Podczas konfiguracji projektu (t_soc_empty.slcp) dolaczylismy do jadra EFR32 nastepujace komponenty:

* **IO Stream: USART** (instancja: com): 
  * Mapowanie pinow: PA08 (TX) oraz PA09 (RX).
  * Predkosc (Baud rate): 115200.
  * Cel: Fizyczne wyprowadzenie komunikacji z procesora EFR32 do mostka SAMD11.
* **Retarget STDIO**: 
  * Cel: Historycznie do obslugi printf(). Pozwala na kierowanie standardowych strumieni wejscia/wyjscia (C) do wybranego interfejsu (w naszym przypadku com).
* **Power Manager**: 
  * Cel: Kontrola stanow uspienia. Uzywamy komendy sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1); by zablokowac procesorowi mozliwosc przejscia w Deep Sleep (EM2), co uniemozliwiloby odpowiednia, bezstratna komunikacje UART.
* **cJSON** (Biblioteka zewnetrzna):
  * Dolozylismy sprzetowa biblioteke z GitHuba do profesjonalnego i bezpiecznego parsowania obiektow JSON z pominieciem prymitywnych i dziurawych metod skanowania tekstu.
