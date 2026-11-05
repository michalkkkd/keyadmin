# Ochrona anti-tamper (EFR32MG24 / Secure Vault High)

Mikrokontroler EFR32MG24 z Secure Vault High ma rozbudowany sprzętowy moduł anti-tamper, którego zadaniem jest utrudnienie zarówno inżynierii wstecznej, jak i ataków logicznych. Pozwala on szybko wykryć próbę ingerencji (tamper) i zareagować wyzwoleniem przerwania, resetem urządzenia albo całkowitym skasowaniem pamięci OTP (One-Time-Programmable, pamięć jednokrotnego zapisu), co trwale unieruchamia urządzenie (bricking).

## Co jest wykrywane?

Moduł anti-tamper monitoruje szereg sygnałów sprzętowych i programowych. Zapewnia szybkie wykrywanie zarówno zewnętrznej, fizycznej ingerencji, jak i wewnętrznych ataków logicznych lub środowiskowych:

### Zabezpieczenia wewnętrzne:
1. **Glitching napięcia:** wykrywa nagłe skoki lub spadki napięcia zasilania (`VGLITCHFALLING`, `VGLITCHRISING`), często używane do pomijania instrukcji lub obchodzenia kontroli bezpieczeństwa.
2. **Glitching cyfrowy (`DGLITCH`):** wykrywa zakłócenia na poziomie logiki wewnątrz układu.
3. **Skrajne temperatury:** wykrywa wymuszone nagrzewanie lub zamrażanie układu, stosowane do wywoływania błędów lub odczytu zawartości SRAM.
4. **Impulsy elektromagnetyczne (EMP):** wykrywa silne pola magnetyczne lub promieniowanie, często używane w atakach typu fault injection (wstrzykiwanie błędów).
5. **Ingerencja w podsystem bezpieczeństwa:** wykrywa ataki logiczne, takie jak nieudane próby uwierzytelnienia, błędy Secure Boot (RTSL) i nieautoryzowany dostęp debug.

### Zabezpieczenia zewnętrzne (przełączniki sprzętowe i pętle przewodów):
Urządzenie ma do 8 zewnętrznych, konfigurowalnych źródeł tamper (albo obsługiwanych przez zewnętrzne przerwania GPIO z filtrami glitchy). Zwykle służą one do wykrywania:
- **Otwarcia obudowy / ingerencji w obudowę:** fizyczne otwarcie obudowy urządzenia.
- **Przecięcia siatki/przewodu:** przecięcie zabezpieczającej pętli przewodu lub przerwanie obwodu mikroprzełącznika wokół PCB.

> **Uwaga sprzętowa (EFR32MG24 a ETAMPDET):** Sprzętowy moduł peryferyjny `ETAMPDET` (External Tamper Detect z generowaniem pseudolosowej sekwencji bitów PRBS przez LFSR) jest dostępny tylko w EFR32xG25, EFR32xG27, EFR32xG29 i układach Series 3. EFR32MG24 (Seeed XIAO MG24) NIE ma modułu ETAMPDET; zewnętrzna ochrona fizyczna jest zrealizowana przez zewnętrzne przerwania GPIO z rezystorami pull-up i cyfrowym filtrowaniem glitchy, kierowane bezpośrednio do `TamperManager` (`tamper_manager_detected()`).

## Wymagania dotyczące fizycznej implementacji

Aby korzystać z zewnętrznego wykrywania tamper na EFR32MG24:
1. **Przełącznik tamper lub pętla przewodu:** fizyczny mikroprzełącznik (dla otwarcia obudowy) lub pętla przewodu musi być podłączona między wyznaczonymi pinami GPIO tamper (PC5 / PC6 w XIAO MG24) a masą (GND).
2. **Pull-up i filtr glitchy:** piny są skonfigurowane w trybie `SL_GPIO_MODE_INPUT_PULL_FILTER`. Gdy obudowa jest zamknięta, obwód ściąga pin do GND (logiczne 0).
3. Jeśli pętla zostanie przecięta, przewód odłączony lub obudowa otwarta, wewnętrzny rezystor pull-up natychmiast podciąga linię do VCC (logiczne 1), co wyzwala przerwanie na zboczu narastającym i powiadamia `TamperManager`.

## Przykłady kodu

Są dwie główne konfiguracje anti-tamper: konfiguracja OTP w Secure Engine (SE), aby obsługiwał autonomiczne reakcje sprzętowe, oraz konfiguracja wejść zewnętrznych przerwań GPIO z TamperManager, aby wykrywać fizyczne naruszenia obudowy i przewodów.

### 1. Konfiguracja Secure Engine (zabezpieczenia wewnętrzne)

Reakcje na tamper są na stałe programowane w pamięci OTP Secure Engine za pomocą `sl_se_init_otp()`. 
**OSTRZEŻENIE:** Ta operacja jest nieodwracalna. Konfiguruje sprzęt tak, by w razie ataku automatycznie kasował swoje sekrety.

```c
#include "sl_se_manager.h"

// Poniższe nazwy sygnałów to nazwy dla EFR32MG24 (Series 2 config 4) z sl_se_manager_defines.h.
// Nazwy takie jak VGLITCHFALLING / DGLITCH istnieją tylko w EFR32xG21 i nie kompilują się dla MG24.
void configure_secure_engine_tamper(sl_se_command_context_t *cmd_ctx)
{
    sl_se_otp_init_t otp_settings_init = SL_SE_OTP_INIT_DEFAULT;  // zawiera też ustawienia secure boot!

    // Glitche mogą mieć fałszywe aktywacje. Zamiast od razu kasować OTP,
    // kierujemy je do filtra. Jeśli w oknie czasowym wystąpi zbyt wiele glitchy,
    // filtr wyzwala główną reakcję.
    otp_settings_init.tamper_levels[SL_SE_TAMPER_SIGNAL_FILTER_COUNTER] = SL_SE_TAMPER_LEVEL_PERMANENTLY_ERASE_OTP;

    // Skieruj detektory glitchy do filtra
    otp_settings_init.tamper_levels[SL_SE_TAMPER_ATAMPDET_SUPGD] = SL_SE_TAMPER_LEVEL_FILTER;  // 18: glitch zasilania
    otp_settings_init.tamper_levels[SL_SE_TAMPER_ATAMPDET_EMPGD] = SL_SE_TAMPER_LEVEL_FILTER;  // 17: glitch cyfrowy / EMP

    // Konfiguracja filtra: wyzwól, jeśli w ciągu 1 minuty wystąpią 4 incydenty
    otp_settings_init.tamper_filter_period = SL_SE_TAMPER_FILTER_PERIOD_1MIN;
    otp_settings_init.tamper_filter_threshold = SL_SE_TAMPER_FILTER_THRESHOLD_4;

    // Zapisz ustawienia do OTP (OPERACJA JEDNORAZOWA, łącznie z ustawieniami secure boot!)
    sl_se_init_otp(cmd_ctx, &otp_settings_init);
}
```

#### 2. Konfiguracja zewnętrznych pinów tamper (GPIO EFR32MG24 i TamperManager)

Poniższy kod (zaimplementowany w [`tamper_simulation.c`](../../../KeyFirmware/src/core/tamper_simulation.c)) pokazuje, jak na EFR32MG24 konfigurowane i obsługiwane są zewnętrzne, fizyczne zdarzenia tamper (np. otwarcie obudowy lub przecięcie pętli przewodu na PC5 / PC6) z użyciem cyfrowego filtrowania glitchy i przerwań:

```c
#include "sl_gpio.h"
#include "tamper_manager.h"

// Definicja fizycznych pinów w Seeed XIAO MG24
#define TAMPER1_PORT  SL_GPIO_PORT_C
#define TAMPER1_PIN   5

static sl_gpio_t tamper_gpio = { .port = TAMPER1_PORT, .pin = TAMPER1_PIN };
static int32_t int_no = -1;

// Callback sprzętowego przerwania GPIO (wywoływany, gdy obwód zostanie przerwany / obudowa otwarta)
static void tamper1_callback(uint8_t pin, void *ctx)
{
    (void)pin;
    (void)ctx;
    // Powiadom centralny TamperManager
    tamper_manager_detected(TAMPER_TYPE_PHYSICAL_PIN1, "Casing opened / Wire 1 severed");
}

void configure_external_tamper_pin(void)
{
    // Skonfiguruj pin jako wejście z pull-upem i włączonym cyfrowym filtrem glitchy
    sl_gpio_set_pin_mode(&tamper_gpio, SL_GPIO_MODE_INPUT_PULL_FILTER, 1);

    // Przydziel i skonfiguruj przerwanie na zboczu narastającym
    sl_gpio_configure_external_interrupt(
        &tamper_gpio,
        &int_no,
        SL_GPIO_INTERRUPT_RISING_EDGE,
        tamper1_callback,
        NULL
    );
}
```

## Instrukcja Testowania dla Marka

Obecny kod w KeyFirmware wykorzystuje bezpieczną "piaskownicę" do testów otwarcia obudowy. Omija ona nieodwracalne przepalanie pamięci OTP, ale w 100% symuluje zachowanie sprzętu dla oprogramowania.

### 1. Co dokładnie zrobić fizycznie (Podłączenie)?
* Zlokalizuj na płytce **Seeed XIAO MG24** pin oznaczony jako **D0** (w kodzie C jest to mapowane jako port PA00).
* Zlokalizuj dowolny pin **GND** (masa).
* Podłącz zwykły przycisk (krańcówkę) lub pętlę z przewodu pomiędzy pinem **D0** a **GND**.
* **Stan Normalny (Zabezpieczony):** Przycisk jest wciśnięty (obwód zwarty do masy). Symuluje to prawidłowo zamkniętą, nienaruszoną obudowę.
* **Stan Alarmowy (Atak):** Puszczenie przycisku (lub przecięcie drutu zabezpieczającego) powoduje rozwarcie obwodu. Wbudowany w procesor rezystor *Pull-up* natychmiast podciąga napięcie na pinie D0 do zasilania (VCC). To wyzwala błyskawiczne sprzętowe przerwanie.

### 2. Jak to sprawdzić i co dokładnie zobaczysz?

**Krok 1: Test Wizualny (Urządzenie zasilane, bez włączonego skryptu Python na PC)**
* Dopóki trzymasz przycisk wciśnięty (obudowa zamknięta) - dioda nie reaguje.
* Gdy tylko puścisz przycisk (otwarcie obudowy), wewnętrzny licznik `tamper_event_count` rośnie o 1. Wbudowana dioda na płytce XIAO **zamiga szybko jeden raz**.
* Jeśli znów wciśniesz i po chwili puścisz przycisk, układ zanotuje to jako drugi atak. Dioda zamiga **dwa razy pod rząd**. Liczba błysków LED zawsze obrazuje całkowitą sumę zarejestrowanych naruszeń.

**Krok 2: Test Telemetrii (Komunikacja z Windows)**
* Włącz Dongle'a i uruchom w systemie Windows nasz skrypt backendowy: python main.py.
* Jeśli wcześniej klikałeś przyciskiem, Dongle ciągle przechowuje to w pamięci RAM.
* W trakcie autoryzacji (krok 1.7), Python odpyta dongle'a o kondycję sprzętową (MSG_SYS_HEALTH).
* Ponieważ dongle zanotował atak, wyśle raport do Windowsa.
* W konsoli Windowsa natychmiast po połączeniu zobaczysz ogromny alert bezpieczeństwa:
```text
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!! CRITICAL SECURITY ALERT: PHYSICAL TAMPER DETECTED !!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```
Oraz bieżący odczyt parametrów środowiskowych wyciągnięty ze sprzętu, np.:
TamperEvents: 2, Temp: 24.5C

> **Ważna uwaga fizyczna:** Obecna konfiguracja "wersji testowej" przechowuje wynik w szybkiej pamięci RAM, by uchronić żywotność Flasha i nie uszkodzić Secure Engine (OTP). To oznacza, że jeżeli **całkowicie odłączysz zasilanie** (np. wyjmiesz układ z USB w celu przeniesienia na inne biurko), to log w RAM zniknie i po podłączeniu licznik znowu będzie wynosił zero. Do testowania samej mechaniki obudowy wystarczy zasilanie z powerbanka i obserwacja diody LED!

## TamperManager w KeyFirmware: wykrywanie, logowanie i kasowanie (stan implementacji)

Kod: `KeyFirmware/src/core/tamper_manager.c` (świat Secure), punkty wejścia przez bramki NSC w `src/secure/nsc_interface.c`.

### Mechanizm centralny

Każdy detektor kończy się w jednej funkcji, `tamper_manager_detected(type, metadata)`, która działa w **świecie Secure**. Zwiększa ona licznik danego typu, a gdy licznik osiągnie próg dla tego typu, wywołuje `tamper_manager_trigger_wipe()` (raz na uruchomienie).

| Typ | Źródło (kto wywołuje) | Próg |
|---|---|---|
| `PHYSICAL_PIN1` / `PIN2` | Przerwania GPIO PC5 / PC6, `tamper_simulation.c` (Non-Secure) → `nsc_tamper_manager_detected` | 3 / 3 |
| `LOGICAL_VRX_SHORT` | Obcięty pakiet VRX, `prod_router.c` (Non-Secure) | 5 |
| `LOGICAL_VRX_INVALID` / `MISMATCH` / `NO_SESSION` | `security_users.c` (Secure) | 5 / 3 / 5 |
| `VOLTAGE_GLITCH` | Flagi brown-out (spadku napięcia) AVDD / IOVDD0 w `EMU->IF`, odpytywane przez `tamper_manager_process()` | 2 |
| `DIGITAL_GLITCH` | Flagi błędów HFXO w `HFXO0->IF`, to samo odpytywanie | 2 |
| `TEMP_EXTREME` | `EMU_TemperatureGet()` co 5 s, poza zakresem -10..+70 °C | 3 |
| `EMP` | `tamper_manager_report_emp()` istnieje, ale **nic jej nie wywołuje** (brak czujnika EMP) | 1 |

`tamper_manager_process()` jest wywoływana z pętli głównej świata Non-Secure (`app.c`) przez `nsc_tamper_manager_process()`. Własne sprzętowe reakcje tamper Secure Engine (`sl_se_otp_init_t.tamper_levels`) **nie** są skonfigurowane; są tylko opisane w komentarzach.

Liczniki są trzymane wyłącznie w RAM świata Secure. Reset lub wyłączenie zasilania zeruje je, więc każdy próg oznacza „N zdarzeń w obrębie jednego cyklu zasilania”.

### Logowanie

* **Nic, co loguje świat Secure, nie trafia na USB.** W obrazie Secure `send_log()` jest zaślepką (`sec_main.c`), a `tamper_manager_init(NULL)` pozostawia `active_tf` puste. Linia `SECURITY ALERT` dla każdego zdarzenia i końcowa linia `CRITICAL: SELF-DESTRUCT` są budowane, ale odrzucane.
* Co host faktycznie widzi:
  * PC5 / PC6 events: in the factory provisioning firmware `tamper_simulation.c` (Non-Secure) sends its own `SECURITY ALERT` log; production firmware sends nothing over USB. In both builds the LED lights for 1 s.
  * Zdarzenia VRX: tylko odpowiedź z błędem na nieudane wywołanie (`ERR: Tamper attempt detected`). Token wydany przez dongle, ale już zamknięty, dostaje `ERR: VRX token expired` i **nie** jest zdarzeniem tamper ([compass_security_mechanisms.md, 7.1 pkt 6](compass_security_mechanisms.md#71-architektura-zabezpieczenia-i-zasady-ochrony)).
  * `MSG_SYS_HEALTH` (`0x10`, factory provisioning firmware only): `TamperEvents:<total>, Temp:<t>, TamperLog:<entries in the persistent log>`.
  * Production firmware: the tamper counters and the tamper log page reach the host only inside the DIAG stream that the dongle encrypts with the Tamper Log Key ([diagnostics.md](diagnostics.md)), readable by KeySec admin only.
* **Trwały log zdarzeń**: każde zdarzenie tamper jest zapisywane, zaszyfrowane AES, na **stronie User Data `0x0FE00000`**, która przetrwa kasowanie. Wpis zdarzenia, które osiągnęło próg, ma flagę WIPE. Zob. [Trwały log tamper](#trwały-log-tamper-strona-user-data). Stary rekord Black Box (192 B, zapisywany jednorazowo po osiągnięciu progu) został usunięty: log zawiera już zdarzenie wyzwalające, jego czas i temperaturę.

### Reakcja po osiągnięciu progu

1. Zdarzenie wyzwalające jest już w trwałym logu z flagą WIPE.
2. Reakcja zależy od przełącznika kompilacji `TAMPER_ENABLE_CODE_FLASH_SELF_DESTRUCT`:

| | Tryb deweloperski (domyślny, `0`) | Kasowanie na żywo (`1`) |
|---|---|---|
| NVM3 (licencja, certyfikat, maks. liczba użytkowników, klucz tożsamości) | Usuwane (`security_nvm_wipe_all`) | Kasowane razem z resztą flasha |
| Kod Secure + Non-Secure | Zachowany: dongle działa dalej | **Kasowany**: `sl_se_erase_device()`, masowe kasowanie przez Secure Engine, które czyści i weryfikuje całą główną pamięć flash **oraz RAM** |
| Blokada debug | Bez zmian | Resetowana do stanu odblokowanego przez SE: pusty układ można ponownie sflashować, a stronę User Data odczytać bez tokenu odblokowującego (log jest zaszyfrowany) |
| Jeśli SE odmówi (device erase wyłączony) | nie dotyczy | Rozwiązanie awaryjne: obiekty NVM3 są usuwane, potem `tamper_manager_self_destruct_ram()` kasuje główną pamięć flash strona po stronie, działając z RAM, a następnie zatrzymuje układ |

> **Nawet tryb deweloperski niszczy dane klienta:** 3 niezgodności tokenu VRX w jednym cyklu zasilania wystarczą, by usunąć licencję i klucz tożsamości z NVM3. Tak się stało 2026-11-05 (benchmark Compass, 12 równoległych bloków SSD dzielących jeden token); od tej pory dongle trzyma pulę tokenów, a zamknięty token nie daje punktu.

Device erase pozostaje dostępny, ponieważ `sec_debug_lock.c` nigdy nie wywołuje `sl_se_disable_device_erase()`. Jeśli kiedykolwiek zostanie wywołana, zostanie tylko awaryjne kasowanie z RAM. Nie sprawdzono, czy MSC (kontroler pamięci flash) świata Non-Secure może kasować strony flasha świata Secure, więc rozwiązanie awaryjne może pozostawić kod Secure nienaruszony.

### Włączanie kasowania na żywo

```bat
set TAMPER_LIVE_WIPE=ON
flashbat\compile.bat
```

`compile.bat` przekazuje `-D KEYFIRMWARE_TAMPER_LIVE_WIPE=ON|OFF` przy każdej konfiguracji, więc ustawienie nigdy nie zostaje w cache CMake. Gdy jest włączone (ON), CMake wypisuje ostrzeżenie. Każda kompilacja bez tej zmiennej to bezpieczna kompilacja w trybie deweloperskim.

**Przed wysyłką z włączonym kasowaniem na żywo przejrzyj progi.** Zdarzenia osiągalne programowo (typy VRX) i środowiskowe (brown-out, HFXO, temperatura) mogą wtedy zniszczyć dongle klienta. Wystarczyłby błąd klienta, który w jednej sesji wyśle 3 błędne tokeny VRX.

**Test sprzętowy (dongle do poświęcenia):**
1. Wgraj kompilację z kasowaniem na żywo.
2. Trzykrotnie zewrzyj PC5 do GND.
3. Dongle znika z USB. Jego flash odczytuje się jako `0xFF`, a `read_tamper_log.py` pokazuje zdarzenia PIN1, ostatnie z `-> WIPE`.

Ta ścieżka nie była jeszcze uruchamiana na sprzęcie.

## Mechanizmy anti-tamper: stan na donglu

Sprawdzone względem nagłówków Simplicity SDK 2026.6.1 (`sl_se_manager_defines.h`, `efr32mg24b220f1536im48.h`) i dokumentacji tamper Secure Vault firmy Silicon Labs (AN1247, Dodatek C „Other Series 2 HSE-SVH devices”). Układ w XIAO MG24 to **EFR32MG24B220F1536IM48**, Secure Vault **High** (`_SILICON_LABS_SECURITY_FEATURE_VAULT`), Series 2 config 4, więc pełny moduł tamper SE jest obecny. Sama płytka XIAO **nie** ma żadnego sprzętu tamper: przełączniki, siatki i zalewanie (potting) musimy dodać sami.

**Kluczowe ograniczenie:** wszystkie reakcje Secure Engine są zapisywane przez `sl_se_init_otp()` do OTP SE **jednorazowo, razem z ustawieniami secure boot**, i nigdy nie można ich zmienić. Jeśli zapiszemy konfigurację tamper z wyłączonym secure boot, secure boot nigdy nie będzie mógł zostać włączony na tym układzie. Obie rzeczy trzeba zdecydować i zaprovisionować w jednym kroku fabrycznym.

Legenda: **Aktywne** = działa dziś na donglach. **Tylko kod** = zaimplementowane, zależy od flag kompilacji lub okablowania. **Możliwe** = sprzęt to obsługuje, nic jeszcze nie zrobiono. **N/A** = niedostępne na tym układzie.

### Sprzętowe źródła tamper Secure Engine (EFR32MG24, numeracja z SDK)

| Źródło SE | Co wykrywa | Domyślna reakcja (bez konfiguracji OTP) | Status | Co jest potrzebne do włączenia |
|---|---|---|---|---|
| 2, 4, 5, 7, 8, 12, 14, 16, 19 (watchdog SE, ECC2 RAM SE, hard fault SE, asercja SE, secure boot firmware'u SE, odczyt OTP, autotest, secure lock, ICACHE SE) | Błędy wewnątrz samego Secure Engine | 4 = Reset | **Aktywne** (wbudowane, nie można obniżyć) | Nic. Od tej zmiany reset spowodowany przez dowolne źródło tamper SE jest zapisywany do trwałego logu przy następnym uruchomieniu (`EMU_RSTCAUSE_SETAMPER`). |
| 21 BOD | Brown-out (spadek) napięcia zasilania | 4 = Reset | **Aktywne** (tylko reset) | Nic. To samo logowanie przyczyny resetu co wyżej. |
| 17 Glitch cyfrowy (`SL_SE_TAMPER_ATAMPDET_EMPGD`, „EMP glitch detector”) | Fault injection impulsem EM / glitchem zegara / logiki. **To jedyny prawdziwy czujnik EMP w układzie.** | 0 = Ignore | **Możliwe**, nieskonfigurowane. Nasz `TAMPER_TYPE_EMP` nie ma źródła. | Poziom OTP 1 (przerwanie), aby logować przez `SETAMPERHOST_IRQHandler`, albo 2 (filtr) / 4 (reset). Domyślnie działa tylko wtedy, gdy SE wykonuje komendę; stałe uzbrojenie wymaga flagi OTP „digital glitch always on” lub `sl_se_enter_active_mode()` (większy pobór prądu). |
| 18 Glitch napięcia (`SL_SE_TAMPER_ATAMPDET_SUPGD`) | Szybkie zakłócenia zasilania (fault injection) | 0 = Ignore | **Możliwe**, nieskonfigurowane | Poziom OTP 1 / 2 / 4. |
| 22 Czujnik temperatury | Temperatura struktury układu w granicach 5 °C od limitów urządzenia (MG24: -40..+125 °C) | 0 = Ignore | **Możliwe**, nieskonfigurowane | Poziom OTP 1 / 2 / 4. Dużo rozsądniejsze limity niż nasze programowe -10..+70 °C. |
| 23 / 24 DPLL lock fail low / high | Manipulacja zegarem przez DPLL | 0 = Ignore | **Możliwe**, mała wartość (nasz firmware nie polega na DPLL) | Poziom OTP. |
| 25-31 PRS0-PRS6 | Dowolny sygnał wewnątrz układu przekierowany przez PRS, np. **piny tamper PC5 / PC6** | 0 = Ignore | **Możliwe**, nieskonfigurowane | Przekierować GPIO przez PRS do odbiornika tamper SE + poziom OTP 4 (reset) lub 7. SE reaguje wtedy nawet przy skompromitowanym firmware CPU. |
| ETAMPDET (zewnętrzne wykrywanie tamper z siatką LFSR) | Aktywna siatka z pseudolosowym wzorcem | nie dotyczy | **N/A**: tylko w Series 2 config 5 / 9 (xG25, xG29...) i Series 3 | Zamiast tego użyć PC5 / PC6 (+ PRS). |
| 10 / 11 Autoryzacja Mailbox / DCI | Błędne tokeny debug-unlock, próby eksportu nieeksportowalnych kluczy | 0 = Ignore | **Możliwe**, nieskonfigurowane | Poziom OTP 2 (filtr) spowolniłby brute force na odblokowanie Secure Debug. |
| 15 Monitor TRNG | Brak entropii (TRNG zaatakowany lub uszkodzony) | 0 = Ignore | **Możliwe**, nieskonfigurowane | Poziom OTP 1 lub 4. |
| 9 User secure boot | Niepoprawny podpis naszego firmware'u | 0 = Ignore | **N/A do czasu włączenia secure boot** | Secure boot (RTSL) nie jest włączony (`compass_security_mechanisms.md` §10). |
| Poziom reakcji 7 „Erase OTP” | Trwale brickuje układ (klucze OTP znikają, układ już nigdy się nie uruchomi) | nie dotyczy | Nieużywany | Tylko dla źródeł z zerowym odsetkiem fałszywych alarmów. Niezalecany dla nas. |

### Funkcje układu poza modułem tamper SE

| Mechanizm | Status | Uwagi |
|---|---|---|
| Secure Debug Lock (SWD zamknięte, odblokowanie tokenem) | **Aktywne**, gdy keyadmin zablokuje dongle (`sec_debug_lock.c`) | Device Erase pozostaje włączony (nigdy nie wywołujemy `sl_se_disable_device_erase()`). |
| Secure boot (RTSL) | **Możliwe**, niewłączone | Trzeba zdecydować razem z OTP tamper SE (jedno wywołanie). |
| Podział TrustZone (Secure / Non-Secure) | **Aktywne** | Logika tamper i sekrety znajdują się w świecie Secure. |
| Device erase SE jako kasowanie | **Tylko kod** (`TAMPER_LIVE_WIPE=ON`), domyślnie OFF | Nietestowane na sprzęcie. |

### Nasze detektory programowe (`tamper_manager.c`)

| Detektor | Status | Uwagi |
|---|---|---|
| Przerwania GPIO PC5 / PC6 (przełącznik obudowy, siatka przewodów) | **Tylko kod** | Wymaga przełącznika lub siatki podłączonych od PC5 / PC6 do GND. Bez tego pull-up trzyma piny w stanie wysokim i nic się nie wyzwala. Próg 3. |
| Kontrole VRX (short / invalid / mismatch / no session) | **Aktywne** | Progi 5 / 5 / 3 / 5. Może je też wyzwolić błąd klienta. |
| Flagi brown-out EMU (AVDD / IOVDD0) -> `VOLTAGE_GLITCH` | **Aktywne** | Próg 2. `tamper_manager_init()` nie czyści starych flag, więc flaga pozostała po włączeniu zasilania lub podłączeniu USB może zostać policzona jako zdarzenie (niezweryfikowane na sprzęcie). |
| Flagi błędów HFXO (did-not-start, buffer freeze) -> `DIGITAL_GLITCH` | **Aktywne** | Próg 2. Słaby start kwarcu też ustawia te flagi. |
| `EMU_TemperatureGet()` poza -10..+70 °C -> `TEMP_EXTREME` | **Aktywne** | Próg 3, odpytywanie co 5 s. Dużo ostrzejsze niż specyfikacja układu -40..+125 °C; dongle w nagrzanym samochodzie lub w zimnym aucie kuriera może go wyzwolić. |
| `tamper_manager_report_voltage_glitch()` (monitor baterii) | **Tylko API** | Nic jej nie wywołuje. |
| `tamper_manager_report_emp()` | **Tylko API** | Nic jej nie wywołuje. Prawdziwy czujnik EMP to źródło SE 17 powyżej. |
| Szyfrowany trwały log zdarzeń na stronie User Data | **Aktywne** | Zob. niżej. |

## Trwały log tamper (strona User Data)

Strona User Data (`0x0FE00000`, **1 KB**, jedyny obszar flash poza główną pamięcią flash w Series 2) nie jest kasowana przez device erase SE, mass erase, flashowanie ani odblokowanie debug. Cała strona mieści log zdarzeń: **64 wpisy x 16 B** (`tamper_log_entry_t`), pusty slot to same `0xFF`.

**Jeden wpis logu (16 B):** typ zdarzenia (lub `0xF0` = uruchomienie po resecie tamper Secure Engine), licznik danego typu w tym cyklu zasilania, flaga „to zdarzenie wyzwoliło kasowanie”, timestamp RTC, uptime w sekundach, temperatura, CRC-16. Dowolne metadane tekstowe nie są zapisywane (zajmowałyby 4-8x więcej miejsca).

* **Szyfrowanie:** każdy wpis to jeden blok AES-128, szyfrowany przez Secure Engine (`sl_se_aes_crypt_ecb`) kluczem **Tamper Log Key** przed zapisem. Klucz jest wkompilowany w obraz Secure (`KeyFirmware/src/core/tamper_log_key.h`), więc kasowanie usuwa kopię w firmware. Kopia fabryczna to `KeySec/keyadmin/keys/tamper_log_key.bin`. Bez niej zrzut skasowanego dongla pokazuje tylko szyfrogram. Każdy wpis jest inny (RTC, uptime, licznik), więc ECB na pojedynczych blokach nie zdradza niczego użytecznego; atakujący widzi tylko, ile slotów jest zajętych. Jeśli SE odmówi szyfrowania, wpis jest pomijany, a nie zapisywany jawnym tekstem.
* **Zarządzanie kluczem:** `python keyadmin/scripts/generate_tamper_log_key.py` tworzy klucz jednorazowo i zapisuje nagłówek; `--header-only` generuje ponownie nagłówek z istniejącego klucza. Nie twórz nowego klucza, gdy dongle są już u klientów: ich logów nie dałoby się wtedy odczytać. Po wygenerowaniu przebuduj firmware.
* **Pojemność:** 64 zdarzenia. Gdy log jest pełny, 32 najstarsze wpisy są odrzucane, a 32 najnowsze zachowywane (jedno kasowanie strony). Najnowsze zdarzenia są więc zawsze dostępne.
* **Zużycie:** wpisy są zapisywane do pustych slotów bez kasowania; kasowanie następuje tylko raz na 32 zdarzenia. Przy typowych 10 000 cyklach kasowania flasha daje to około 320 000 zdarzeń na dongle.
* **Utrata zasilania:** zapis przerwany w połowie nie przechodzi CRC po odszyfrowaniu i jest pokazywany jako `[CORRUPT or wrong key]`. Zanik zasilania podczas przepisywania strony (log pełny) może spowodować utratę logu: okno trwa kilka milisekund.
* **Czego się nie loguje:** własnych zdarzeń tamper Secure Engine, poza resetami, które one powodują (brak jeszcze konfiguracji OTP), oraz niczego sprzed tej wersji firmware'u.

### Jak fabryka go odczytuje

| Stan dongla | Jak odczytać |
|---|---|
| Skasowany przez kasowanie na żywo (device erase SE się powiódł) | Kasowanie usunęło też blokadę debug, a dongle nie ma firmware'u (brak USB). Podłącz SWD i uruchom `python keyadmin/scripts/read_tamper_log.py`. Skrypt zrzuca 1 KB przez pyOCD, odszyfrowuje go kluczem `keyadmin/keys/tamper_log_key.bin` (lub `--key FILE`) i wypisuje log. |
| Nadal działa (tryb deweloperski albo zablokowany, ale nieskasowany) | `secure_debug_lock.py unlock` lub odblokowanie z menu administracyjnego: po odblokowaniu tokenem keyadmin automatycznie zrzuca i dekoduje stronę (`userdata_dump.bin` w folderze dongla). |
| Wcześniejszy plik zrzutu | `python keyadmin/scripts/read_tamper_log.py --file <dump.bin>` |

Po odczycie, zanim dongle wróci do użytku, skasuj stronę, bo ponowne flashowanie ją zachowuje: `commander device pageerase --region @userdata` (jeszcze nie uruchamiane na naszych donglach).

### Blokada debug po kasowaniu

`sl_se_erase_device()` to komenda SE „Erase Device”. W Series 2 zawsze pozostawia układ **odblokowany** po następnym resecie. Tak działają standardowa i bezpieczna blokada debug, dopóki Device Erase jest włączony, i nie możemy tego zmienić. Fabryka może ponownie zablokować dongle po ponownym sflashowaniu (keyadmin `lock`; command key w OTP pozostaje).

Jeśli skasowany dongle musi pozostać zablokowany, alternatywą jest wyłączenie Device Erase (`sl_se_disable_device_erase()`, nieodwracalne) i poleganie na kasowaniu strona po stronie z RAM:

* Blokada pozostaje wtedy włączona.
* Tylko fabryka może otworzyć dongle tokenem secure debug, by odczytać log i ponownie sflashować.
* Koszt: utracony command key oznacza, że dongla nie da się już nigdy otworzyć.
* Nie zweryfikowano, czy kasowanie z RAM potrafi skasować strony świata Secure.

Przed wyborem tej opcji potrzebne są testy sprzętowe.
