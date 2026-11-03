# Odkrycia architektoniczne i sprzętowe (kluczowe notatki)

* **Zegar licencji (bateria podłączona na stałe):**
  - EFR32MG24 nie ma RTC z podtrzymaniem bateryjnym, ale bateria zasila cały układ, więc po odłączeniu USB MCU śpi w EM2, a licznik SYSRTC (32 768 Hz) dalej liczy.
  - Świat Secure nie może używać sleeptimera (jego kopia w obrazie Secure nigdy nie jest inicjalizowana, `sl_sleeptimer_get_timer_frequency()` zwraca tam 0). Czyta więc licznik sam i sumuje przyrosty (`security_rtc.c`), koniecznie przez `SYSRTC0_NS`: SYSRTC jest peryferium NS, a w buildzie Secure samo `SYSRTC0` to alias Secure i dostęp kończy się faultem. Pętla NS woła `nsc_rtc_process()` co 30 s (timer okresowy budzi ją też w EM2).
  - Licznik zeruje się przy resecie, dlatego czas Unix trafia co 60 s do NVM3 (checkpoint), a po resecie zegar rusza od checkpointu + 150 s kary. Szczegóły: [time_license_mechanism.md](../security/time_license_mechanism.md).
  - Dawny model `boot_time + uptime` cofał zegar przy każdym resecie do daty provisioningu (licencja praktycznie nie wygasała). Nie wracać do niego.

* **Błąd zamiany znaków LF na CRLF w SiLabs SDK:** Straciliśmy mnóstwo czasu na błędy CRC w pakietach TinyFrame. Okazało się, że domyślnie sl_iostream_usart w Silicon Labs SDK działa jak terminal tekstowy i po cichu zamienia wysyłany bajt `0x0A` (\n) na sekwencję `0x0D` 0x0A (\r\n). 
  - Dla strumieni binarnych, takich jak TinyFrame, to katastrofa (psuje bajty payloadu lub sumy kontrolne).
  - Rozwiązanie: trzeba to wyłączyć w config/sl_iostream_usart_Io_Stream_USERT_config.h (ustawiając opcję ...CONVERT_BY_DEFAULT_LF_TO_CRLF na `0`).

* **Diagnostyka pamięci i linker:** Zamiast wpisywać offsety na sztywno, do obliczania zużycia zasobów sprzętowych (Flash, RAM) w czasie rzeczywistym mapujemy zmienne systemowe eksportowane przez GNU Linker, takie jak __etext, __data_start__, __HeapBase, __HeapLimit (przez funkcję diagnostyczną MSG_MEM_INFO).

* **Newlib-nano i wartości 64-bitowe:** Lekka biblioteka C 
ewlib-nano, domyślnie włączona dla Cortex-M33 w SiLabs, może wywołać HardFault przy próbie bezpośredniego wypisania (printf, snprintf) wartości 64-bitowych za pomocą %llu. Trzeba je rzutować w dół do u32 (jeśli jest to bezpieczne).
