# Zarządzanie energią i wykrywanie USB (uśpienie na baterii)

## Kontekst architektoniczny
Układ EFR32MG24 nie ma wbudowanego sprzętowego kontrolera USB. Na płytkach deweloperskich Seeed Studio XIAO MG24 łączność USB zapewnia umieszczony na płytce koprocesor (SAMD11 / DAPLink CMSIS-DAP), który pełni rolę mostka USB-UART. EFR32MG24 komunikuje się z nim wyłącznie przez piny `PA08` (TX) i `PA09` (RX) z prędkością 921 600 bodów.

Ponieważ bateria podtrzymująca (zasilająca zegar czasu rzeczywistego RTC i obwody anti-tamper, czyli wykrywania ingerencji) jest podłączona na stałe, układ musi automatycznie przechodzić w tryb głębokiego uśpienia o ultraniskim poborze energii (**EM3**) za każdym razem, gdy kabel USB zostanie odłączony, komputer przejdzie w stan uśpienia albo aplikacja hosta zakończy działanie. Ponieważ do mikrokontrolera EFR32 nie doprowadzono dedykowanej sprzętowej linii wykrywania VBUS (napięcia zasilania z USB), wykrywanie połączenia odbywa się **w 100% programowo, za pomocą aktywnego protokołu Heartbeat i asynchronicznego wybudzania Wake-on-RX**.

---

## Tryby pracy (Energy Modes)

System pracuje w trzech różnych trybach energetycznych Silicon Labs (Energy Modes, EM):

| Tryb | Nazwa | Rdzeń CPU | Peryferia (EUSART0, DMA, zegary) | Pobór prądu | Czas wybudzenia | Opis |
|:---|:---|:---|:---|:---:|:---:|:---|
| **EM0** | **Aktywny** | ARM Cortex-M33 pracuje z częstotliwością 78 MHz | Wszystkie szybkie zegary (HFXO/DPLL), DMA, EUSART i sprzętowa kryptografia Vault aktywne | ~6–8 mA | 0 ns | Aktywne odszyfrowywanie, wykonywanie bezpiecznych algorytmów (RPC) i szyfrowanie odpowiedzi. |
| **EM1** | **Aktywny bezczynny** | Wstrzymany przez `WFI` (Wait For Interrupt, czekanie na przerwanie) | **W 100% aktywne.** Oscylator wysokiej częstotliwości (HFXO), DMA i EUSART0 nasłuchują z prędkością 921 600 bodów | ~1,5–2,5 mA | ~38 ns (3 cykle CPU) | Mikrouśpienie między bajtami/pakietami UART. Zachowuje natychmiastową odpowiedź bez opóźnień. |
| **EM3** | **Głębokie uśpienie** | Wyłączony; zawartość RAM zachowana | Szybkie zegary i UART wyłączone. Aktywne są tylko ULFRCO (1 kHz) i wykrywanie przerwań GPIO | **~1 µA** | ~10 µs | Tryb oszczędzania baterii o ultraniskim poborze energii, uruchamiany, gdy brakuje sygnału heartbeat z aplikacji hosta. |

---

## Opis rozwiązania programowego (Heartbeat + asynchroniczne Wake-on-RX)

Architektura opiera się na dwóch współdziałających mechanizmach:

```
[ Aplikacja PC (KeySec) ]
       |
       |  (Wysyła RPC i okresowe heartbeaty MSG_PING co 3,0 s)
       v
+-----------------------------------------------------------------------------------+
| 1. STAN AKTYWNY (EM0 / EM1)                                                       |
|    - Blokada utrzymywana: sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1) |
|    - Przerwanie GPIO na zboczu opadającym PA09 jest BEZWZGLĘDNIE WYŁĄCZONE,       |
|      aby zapobiec burzy przerwań (ISR)                                            |
|    - EUSART0 i DMA odbierają bajty z prędkością 921 600 bodów bez narzutu         |
|    - Heartbeat odświeża inactivity_timer (odliczanie 4,5 s)                       |
+-----------------------------------------------------------------------------------+
       |
       |  (Przekroczenie czasu bezczynności: 4,5 s bez heartbeatu / ruchu)
       v
+-----------------------------------------------------------------------------------+
| 2. OSTRZEŻENIE O UTRACIE HEARTBEATU (przejście 3,0 s)                             |
|    - Dioda LED statusu świeci ciągle przez 3,0 sekundy jako ostrzeżenie wizualne  |
|    - Urządzenie pozostaje w EM1 (może natychmiast wrócić, jeśli nadejdzie         |
|      heartbeat)                                                                   |
+-----------------------------------------------------------------------------------+
       |
       |  (Ostrzeżenie mija bez wznowienia heartbeatu: łącznie upłynęło 7,5 s)
       v
+-----------------------------------------------------------------------------------+
| 3. GŁĘBOKIE UŚPIENIE (tryb EM3)                                                   |
|    - Blokada zwolniona: sl_power_manager_remove_em_requirement(SL_POWER_MANAGER_EM1) |
|    - Przerwanie GPIO na zboczu opadającym PA09 jest UZBROJONE                     |
|      (sl_gpio_enable_interrupts)                                                  |
|    - MCU przechodzi w EM3 (pobór ~1 µA)                                           |
|    - Pierwsze zbocze opadające na RX wywołuje rx_wakeup_callback, rozbraja ISR    |
|      GPIO, przywraca wymaganie EM1 i wybudza MCU do EM0                           |
+-----------------------------------------------------------------------------------+
```

### 1. Protokół bezczynności i heartbeatu (odliczanie ping-pong)
1. **Bramka pierwszego heartbeatu**: Po włączeniu zasilania i starcie `sleep_feature_enabled` jest inicjalizowane wartością `false`. Odliczanie timera uśpienia nie startuje, dopóki od hosta nie nadejdzie pierwszy prawidłowy `MSG_PING`. Dzięki temu MCU nie zasypia w oczekiwaniu na początkową konfigurację ani tuż po wgraniu firmware'u.
2. **Okresowy heartbeat hosta**: Aplikacja hosta na PC (`KeySec/keycomm/core/transport.py`) utrzymuje wątek w tle (`_heartbeat_loop`), który wysyła ramki `MSG_PING` co **3,0 sekundy**.
3. **Odliczanie bezczynności**: Na MCU `trigger_led_timer()` restartuje `inactivity_timer` z **limitem czasu 4,5 sekundy** (`INACTIVITY_TIMEOUT_MS = 4500`).
4. **Ostrzeżenie o utracie heartbeatu**: Jeśli upłyną 4,5 sekundy bez komunikacji:
   - `inactivity_timer_callback` włącza diodę LED statusu na stałe na **3,0 sekundy** (`HEARTBEAT_LOST_LED_MS = 3000`).
   - Jeśli host wznowi komunikację w ciągu tych 3 sekund, `trigger_led_timer()` zatrzymuje odliczanie, gasi diodę ostrzegawczą i przywraca normalną pracę.
5. **Wejście w głębokie uśpienie EM3**: Jeśli po 3-sekundowym ostrzeżeniu nie nadejdzie żaden heartbeat (łącznie **7,5 sekundy** bezczynności):
   - `heartbeat_lost_timer_callback` gasi diodę LED.
   - Usuwa wymaganie zasilania EM1 (`sl_power_manager_remove_em_requirement(SL_POWER_MANAGER_EM1)`).
   - Włącza zewnętrzne przerwanie GPIO na zboczu opadającym na pinie `PA09`.
   - Power Manager Silicon Labs przełącza urządzenie w **głębokie uśpienie EM3** (~1 µA).

### 2. Zapobieganie burzy przerwań i Wake-on-RX
Aby zagwarantować stabilność wysokoprzepustowej komunikacji UART przy 921 600 bodów:
* **Pułapka burzy przerwań GPIO na PA09**: We wczesnych implementacjach przerwanie GPIO na zboczu opadającym PA09 pozostawało aktywne podczas komunikacji. Przy 921 600 bodów każdy bit startu i każdy bit zerowy generował setki przerwań GPIO na pakiet, blokując kolejkę sleeptimera i „głodząc” 16-bajtowy sprzętowy FIFO EUSART (bufor odbiorczy układu).
* **Ścisła izolacja przerwań**:
  - W EM0 i EM1 zewnętrzne przerwanie GPIO na PA09 jest **bezwzględnie wyłączone** (`sl_gpio_disable_interrupts(1 << rx_wakeup_int_no)`).
  - Przerwanie GPIO jest włączane **wyłącznie** przy przejściu do EM3.
  - Gdy PC wyśle bajt wybudzający (zbocze opadające na RX), wywoływany jest `rx_wakeup_callback`, który **natychmiast wyłącza przerwanie GPIO**, ponownie ustawia `SL_POWER_MANAGER_EM1` i zwraca `SL_POWER_MANAGER_WAKEUP`.
  - Wszystkie kolejne bajty danych są przetwarzane wyłącznie przez sprzętowy EUSART i DMA, bez żadnej ingerencji przerwań GPIO.

### 3. Wstrzymywanie i wznawianie heartbeatu po stronie PC
Podczas intensywnych benchmarków lub wysokoprzepustowych operacji wsadowych oprogramowanie hosta może zapobiec rywalizacji wątków o magistralę szeregową za pomocą:
- `transport.pause_heartbeat()`: wstrzymuje automatyczne wysyłanie `MSG_PING` co 3,0 s.
- `transport.resume_heartbeat()`: przywraca automatyczne wysyłanie heartbeatu.

---

## Scenariusze użycia (przypadki brzegowe i zabezpieczenia)

### Scenariusz A: urządzenie odłączone ➔ start aplikacji ➔ podłączenie urządzenia
* **Stan początkowy:** Urządzenie jest w głębokim uśpieniu EM3, zasilane z baterii. Aplikacja na PC czeka na wykrycie portu COM.
* **Przebieg:** Urządzenie zostaje podłączone do USB. Aplikacja na PC otwiera port COM i rozpoczyna kryptograficzny handshake.
* **Wynik:** Pierwsze zbocze na RX natychmiast wybudza EFR32MG24 do EM0. Przerwanie GPIO zostaje wyłączone, wymaganie EM1 zablokowane, handshake się kończy, a okresowe heartbeaty utrzymują urządzenie w stanie aktywnym.

### Scenariusz B: urządzenie podłączone ➔ start aplikacji na PC
* **Stan początkowy:** Urządzenie jest podłączone do USB, ale znajduje się w głębokim uśpieniu EM3, ponieważ aplikacja na PC została wcześniej zamknięta (>7,5 s temu).
* **Przebieg:** Użytkownik uruchamia aplikację. Warstwa transportowa otwiera COM10 i wysyła początkowy ping synchronizacyjny.
* **Wynik:** Zbocze opadające wybudza EFR32MG24 do EM0. Normalna komunikacja zostaje natychmiast wznowiona.

### Scenariusz C: normalna praca ➔ aplikacja kończy działanie lub ulega awarii
* **Stan początkowy:** Urządzenie jest w stanie aktywnym (EM0/EM1) i normalnie się komunikuje.
* **Przebieg:** Aplikacja na PC zostaje zamknięta lub nieoczekiwanie ulega awarii. Wysyłanie heartbeatu w tle ustaje.
* **Wynik:** 
  1. W chwili $t = 4.5\text{ s}$ MCU wykrywa brak heartbeatu i zapala diodę LED statusu.
  2. W chwili $t = 7.5\text{ s}$ ostrzeżenie wygasa; MCU włącza przerwanie GPIO na PA09, usuwa wymaganie EM1 i przechodzi w głębokie uśpienie EM3 (~1 µA), w pełni oszczędzając energię baterii.

### Scenariusz D: normalna praca ➔ fizyczne odłączenie kabla USB
* **Stan początkowy:** Urządzenie jest w stanie aktywnym (EM0/EM1).
* **Przebieg:** Kabel USB zostaje odłączony. Mostek USB-UART na płytce traci zasilanie VBUS.
* **Wynik:** Tak samo jak w scenariuszu C. Po ostrzeżeniu po 4,5 s i odliczaniu 3,0 s EFR32MG24 bezpiecznie przechodzi w głębokie uśpienie EM3 na zasilaniu bateryjnym.

### Scenariusz E: przypadkowe zakłócenia lub obce programy portu szeregowego (fałszywe wybudzenie)
* **Stan początkowy:** Urządzenie jest w głębokim uśpieniu EM3.
* **Przebieg:** Zakłócenia elektryczne na kablu lub zewnętrzny monitor portu szeregowego (np. PuTTY) otwiera port i wysyła przypadkowy znak.
* **Wynik:** EFR32MG24 wybudza się do EM0/EM1 i rozbraja przerwanie GPIO. Ponieważ jednak obcy program nie wysyła prawidłowych kryptograficznych heartbeatów `KeySec`, po 4,5 s + 3,0 s MCU przekracza limit czasu i bezpiecznie wraca do głębokiego uśpienia EM3.
