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

Zwykłe przerwania GPIO portów C/D **nie** wyzwalają się w uśpieniu EM2 (RM EFR32xG24 24.3.10.1), dlatego firmware ([`tamper_external.c`](../../../KeyFirmware/src/core/tamper_external.c)) stosuje **odczyt impulsowy**: co 1 s timer okresowy (`sl_sleeptimer`) na chwilę włącza wewnętrzny pull-up, próbkuje piny tamper i natychmiast go wyłącza, żeby nie pobierać prądu przez pętlę. Zerwana pętla / otwarta obudowa odczytuje się jako logiczne `1` i powiadamia `TamperManager` przez bramkę NSC. Mechanizm jest inicjowany w `app.c` (`tamper_external_init()`) i działa na donglu:

```c
#include "sl_gpio.h"
#include "sl_sleeptimer.h"
#include "tamper_manager.h"

// Piny fizyczne (konfiguracja w tamper_external.c)
#define TAMPER1_PORT SL_GPIO_PORT_C
#define TAMPER1_PIN  5
static sl_gpio_t tamper1_gpio = { TAMPER1_PORT, TAMPER1_PIN };
static sl_sleeptimer_timer_handle_t tamper_timer;

// Odczyt impulsowy co 1 s (działa też w EM2, w przeciwieństwie do przerwań GPIO portu C)
static void tamper_timer_callback(sl_sleeptimer_timer_handle_t *h, void *d)
{
    (void)h; (void)d;
    sl_gpio_set_pin_mode(&tamper1_gpio, SL_GPIO_MODE_INPUT_PULL_FILTER, 1); // włącz pull-up
    __NOP(); __NOP(); __NOP(); __NOP();                                     // ustalenie napięcia
    bool tampered = 0;
    sl_gpio_get_pin_input(&tamper1_gpio, &tampered);
    sl_gpio_set_pin_mode(&tamper1_gpio, SL_GPIO_MODE_DISABLED, 0);          // wyłącz pull-up (oszczędność prądu)
    if (tampered) {
        nsc_tamper_manager_detected(TAMPER_TYPE_PHYSICAL_PIN1, "Chassis enclosure microswitch triggered");
    }
}

void tamper_external_init(void)
{
    sl_sleeptimer_start_periodic_timer_ms(&tamper_timer, 1000, tamper_timer_callback, NULL, 0, 0);
}
```

## TamperManager w KeyFirmware: wykrywanie, logowanie i kasowanie (stan implementacji)

Kod: `KeyFirmware/src/core/tamper_manager.c` (świat Secure), punkty wejścia przez bramki NSC w `src/secure/nsc_interface.c`.

### Mechanizm centralny

Każdy detektor kończy się w jednej funkcji, `tamper_manager_detected(type, metadata)`, która działa w **świecie Secure**. Zwiększa ona licznik danego typu, a gdy licznik osiągnie próg dla tego typu, wywołuje `tamper_manager_trigger_wipe()` (raz na uruchomienie).

Progi pochodzą z tablicy `tamper_thresholds[]` w [`tamper_manager.c`](../../../KeyFirmware/src/core/tamper_manager.c#L34-L45). Poniżej master table z planem po ustaleniach **2026-11-12** (obejmuje warstwę software oraz planowaną warstwę Secure Engine / OTP):

| # | Detektor | Warstwa | OTP | Kiedy licznik rośnie | Licznik | Log? | Stary próg | **Nowy próg** | Wipe? |
|:--:|---|:--:|:--:|---|---|:--:|:--:|:--:|:--:|
| 1 | Obudowa PC5/PC0 | soft | — | pin „otwarte” (poll co 1 s) | RAM / per-cykl | TAK | 1 / 1 | **1** | TAK, po 1 |
| 2 | VRX_SHORT | soft | — | ucięty token (przy komendzie) | RAM / per-cykl | TAK | 30 | **50** | TAK, po 50 |
| 3 | VRX_INVALID | soft | — | pusty token | RAM / per-cykl | TAK | 30 | **50** | TAK, po 50 |
| 4 | VRX_MISMATCH | soft | — | niezgodny token | RAM / per-cykl | TAK | 50 | **50** | TAK, po 50 |
| 5 | VRX_NO_SESSION | soft | — | token bez sesji | RAM / per-cykl | TAK | 30 | **50** | TAK, po 50 |
| 6 | Temperatura (−10/+70) | soft | — | odczyt poza zakresem (co 5 s) | RAM / per-cykl | TAK | 3 | **12** (=1 min) | TAK, po 12 |
| 7 | Voltage (BOD) | soft | — | flaga brown-out (ciągle) | RAM / per-cykl | TAK | 2 | **—** | **NIE** (tylko log) |
| 8 | Digital (HFXO) | soft | — | flaga błędu kwarcu (ciągle) | RAM / per-cykl | TAK | 2 | **—** | **NIE** (tylko log) |
| 9 | SE 17 EMPGD (glitch EM) | SE | **4 reset** | sprzęt SE → reset | NVM3 / persistent | TAK (na reboot) | — (0) | **50 resetów** | TAK, po 50 resetach |
| 10 | SE 18 SUPGD (glitch napięcia) | SE | **4 reset** | sprzęt SE → reset | NVM3 / persistent | TAK (na reboot) | — (0) | **50 resetów** | TAK, po 50 resetach |
| 11 | SE 10/11 Mailbox/DCI (brute-force unlock) | SE | **1** | zła komenda SE | NVM3 / persistent | TAK | — (0) | **10** | TAK, po 10 |
| 12 | SE 15 TRNG (brak entropii) | SE | **1** | monitor TRNG | — | TAK | — (0) | **—** | **NIE** (tylko log) |
| 13 | SE 22 temp / 23–24 DPLL | SE | **0 pomiń** | — | — | — | — | — | NIE |
| — | **erase OTP (poziom 7)** | SE | **NIGDY** | — | — | — | — | — | — |

Jak to czytać:
* **RAM / per-cykl** — licznik zeruje się przy resecie / braku prądu. W serwerze na USB (do roku bez resetu) praktycznie nie zeruje się przez rok — stąd tolerancyjne progi.
* **NVM3 / persistent** — przeżywa reset; potrzebny tylko dla glitcha, bo glitch sam robi reset (zeruje RAM).
* **Log?** — każde zdarzenie (nie tylko to z wipe) idzie do zaszyfrowanego logu na stronie User Data; log **przeżywa wipe**, więc fabryka zawsze ma co czytać.
* **Wipe** = `sl_se_erase_device` — **odwracalny** (reflash + provisioning). **Nigdy** erase-OTP (brick).
* Temperatura to jedyny detektor czasowy (odczyt co 5 s → próg 12 = 60 s poza zakresem). Reszta liczy zdarzenia/flagi.

`tamper_manager_process()` jest wołana z pętli głównej świata Non-Secure (`app.c`) przez `nsc_tamper_manager_process()`. Szczegóły warstwy SE / OTP: [Plan warstwy OTP / Secure Engine](#plan-warstwy-otp--secure-engine-decyzje-2026-11-12).

### Logowanie

* **Nic, co loguje świat Secure, nie trafia na USB.** W obrazie Secure `send_log()` jest zaślepką (`sec_main.c`), a `tamper_manager_init(NULL)` pozostawia `active_tf` puste. Linia `SECURITY ALERT` dla każdego zdarzenia i końcowa linia `CRITICAL: SELF-DESTRUCT` są budowane, ale odrzucane.
* Co host faktycznie widzi:
  * PC5 / PC6 events: in the factory provisioning firmware `tamper_external.c` (Non-Secure) sends its own `SECURITY ALERT` log; production firmware sends nothing over USB. In both builds the LED lights for 1 s.
  * Zdarzenia VRX: tylko odpowiedź z błędem na nieudane wywołanie (`ERR: Tamper attempt detected`). Token wydany przez dongle, ale już zamknięty, dostaje `ERR: VRX token expired` i **nie** jest zdarzeniem tamper ([compass_security_mechanisms.md, 7.1 pkt 6](compass_security_mechanisms.md#71-architektura-zabezpieczenia-i-zasady-ochrony)).
  * `MSG_SYS_HEALTH` (`0x10`, factory provisioning firmware only): `TamperEvents:<total>, Temp:<t>, TamperLog:<entries in the persistent log>`.
  * Production firmware: the tamper counters and the tamper log page reach the host only inside the DIAG stream that the dongle encrypts with the Tamper Log Key ([diagnostics.md](diagnostics.md)), readable by KeySec admin only.
* **Trwały log zdarzeń**: każde zdarzenie tamper jest zapisywane, zaszyfrowane AES, na **stronie User Data `0x0FE00000`**, która przetrwa kasowanie. Wpis zdarzenia, które osiągnęło próg, ma flagę WIPE. Zob. [Trwały log tamper](#trwały-log-tamper-strona-user-data). Stary rekord Black Box (192 B, zapisywany jednorazowo po osiągnięciu progu) został usunięty: log zawiera już zdarzenie wyzwalające, jego czas i temperaturę.

### Reakcja po osiągnięciu progu

Jest **jedna** reakcja, taka sama w każdej kompilacji (stary przełącznik `TAMPER_ENABLE_CODE_FLASH_SELF_DESTRUCT` / `TAMPER_LIVE_WIPE` i tryb deweloperski zostały usunięte). `tamper_manager_trigger_wipe()` wykonuje po kolei:

1. Zdarzenie wyzwalające jest już w trwałym logu z flagą WIPE.
2. **Zrzut liczników użycia** (wpis `TAMPER_LOG_TYPE_USAGE_DUMP`): 6 liczników wywołań algorytmów (`usage_counters`) zapisywanych do logu jako jeden blok, zanim NVM3 zostanie skasowane.
3. `sl_se_erase_device()` — masowe kasowanie przez Secure Engine, które **czyści i weryfikuje całą główną pamięć flash oraz RAM**: kod Secure + Non-Secure, NVM3 (licencja, liczniki, certyfikat, maks. liczba użytkowników, klucz tożsamości). Resetuje też konfigurację debug do stanu odblokowanego. **Przetrwają tylko: strona User Data (log tamper) oraz dane jednorazowe OTP w SE (Command Key).**
4. Rozwiązanie awaryjne (gdy SE odmówi, tj. po `DEVICE_ERASE_DISABLE`): `tamper_manager_self_destruct_ram()` kasuje główną pamięć flash strona po stronie, działając z RAM, a potem zatrzymuje układ. U nas device erase pozostaje włączony (`sec_debug_lock.c` nigdy nie wywołuje `sl_se_disable_device_erase()`), więc ta gałąź praktycznie nie jest używana (a czy kasowanie z RAM na pewno obejmuje strony świata Secure — niezweryfikowane na sprzęcie).

**To nie jest trwały bric.** Po `sl_se_erase_device()` port debug jest otwarty, więc dongle flashujesz sondą SWD i provisionujesz normalnie — Command Key w OTP przeżywa, a `install_command_key` jest idempotentny. Trwale zbrickować mógłby tylko permanentny lock (`sl_se_disable_device_erase()` / reakcja „Erase OTP”), którego **nie** wykonujemy.

> **Kasowanie niszczy dane klienta — progi są celowo tolerancyjne.** Fizyczny tamper (PC5/PC0) kasuje już od 1 zdarzenia (otwarcia obudowy nie zrobisz przypadkiem); błędne tokeny VRX dopiero po **50** w jednym cyklu zasilania, żeby zacięta lub powtarzająca żądania aplikacja nie zbrickowała dongla. Incydent 2026-11-05 (benchmark Compass, 12 równoległych bloków SSD dzielących jeden token) był powodem podniesienia progów. Temperatura: próg **12** odczytów (≈1 min poza −10/+70), bo awaria klimy w serwerowni potrafi godzinami trzymać >70 °C. **Voltage/digital → tylko log, nie wipe** (wpięcie USB / słaby start kwarcu fałszywie je wzbudzają; realny szybki glitch łapie SE 17/18). **Przed wysyłką przejrzyj progi** (`tamper_thresholds` w `tamper_manager.c`).

**Test sprzętowy (dongle do poświęcenia):**
1. Wgraj firmware produkcyjny.
2. Zewrzyj PC5 do GND (próg 1).
3. Dongle znika z USB. Jego flash odczytuje się jako `0xFF`, a `read_tamper_log.py` pokazuje zdarzenia PIN1 (ostatnie z `-> WIPE`) oraz wiersz `USE` z licznikami. Potem dongle flashuje się i provisionuje normalnie.

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

### Plan warstwy OTP / Secure Engine (decyzje 2026-11-12, zaimplementowane 2026-11-13)

> **Decyzja zespołu (2026-11-13): Secure Boot = OFF, świadomie i na stałe.** Nie chcemy secure boota (RTSL) — jest redundantny z zawsze włączonym Secure Debug Lockiem wobec zagrożenia „wgraj złe firmware” (atakujący i tak nie otworzy SWD, żeby je wgrać). `sl_se_init_otp()` zamraża tę decyzję na zawsze w tym samym zapisie co poziomy tamperów, dlatego ustawiamy `enable_secure_boot = false` i mamy tego świadomość. Szczegóły: [compass_security_mechanisms.md §10](compass_security_mechanisms.md).

**Stan: zaimplementowane.** Warstwę SE/OTP uzbraja firmware ([`sec_tamper_otp.c`](../../../KeyFirmware/src/secure/sec_tamper_otp.c)) wołany przez `provision_dongle --lock` (bramka `MSG_TAMPER_OTP_ARM` 0x65, status `MSG_TAMPER_OTP_STATUS` 0x64). Sam wpal OTP na fizycznym urządzeniu pozostaje nieodwracalnym krokiem produkcyjnym (robi się raz, w `--lock`).

**Dwie warstwy.** (a) Software (dół master table) już działa, bez OTP — czyta zwykłe peryferia (GPIO, EMU, HFXO) i robi nasz wipe. (b) Sygnały SE (góra) uzbraja jednorazowy wpis poziomu w OTP (w kodzie gotowe, wypalane w `--lock`).

**Co jest w OTP i co wypala co.** OTP ma osobne „szufladki”, zapisywane różnymi operacjami:
* `sl_se_init_otp_key(...)` — publiczny **Command Key** (Secure Debug). **Już wypalone** na donglach z `--lock`.
* `sl_se_init_otp(...)` — blok **secure boot + poziomy tamperów** (`tamper_levels[]`), oba naraz, **raz i nieodwracalnie**. Nasza konfiguracja: secure boot OFF + poziomy z tabeli niżej. Przy okazji na zawsze zamraża decyzję o secure boot (zapis z secure boot OFF = już nigdy go nie włączysz na tym układzie).

**W OTP idzie tylko liczba (poziom), nie kod.** Poziomy: `0` ignore · `1` interrupt (SE podnosi `SETAMPERHOST`, resztę robi nasz handler, reflashowalny) · `4` reset (autonomiczny, sprzętowy) · `7` erase-OTP (brick — **nigdy**). „Co się wykona” przy poziomie 1 to zwykły firmware (`SETAMPERHOST_IRQHandler` → `tamper_manager_detected`), zmienialny reflashem; w OTP nie ma nazw funkcji ani adresów.

**Szybki glitch (17/18) → poziom 2 (filtr) → licznik filtra (1) → poziom 4 (reset), nie wipe.** Dlaczego filtr, a nie reset wprost: Silicon Labs **wprost odradza** pędzenie poważnej reakcji prosto z surowych detektorów glitcha — „widzą sporadyczne wzbudzenia” (ESD przy dotknięciu/wpięciu, brudne USB, inrush, EM w serwerowni). Kierujemy więc 17/18 na **wspólny licznik filtra** (`SL_SE_TAMPER_SIGNAL_FILTER_COUNTER`, 0x1); dopiero seria glitchy w jednym oknie (~33 s, próg 4) zbija licznik, a on jest ustawiony na **reset**. To nadal reset na realny, podtrzymany atak (Twoja intencja), ale **sprzętowo odbouncowany** — pojedyncza szpilka ESD nie resetuje. Reset jest autonomiczny (SE działa niezależnie od zglitchowanego rdzenia), **niedestrukcyjny** i logowany na reboocie (`SE_TAMPER_RESET`, [`tamper_manager.c`](../../../KeyFirmware/src/core/tamper_manager.c)) plus liczony w DIAG. **Nie brickujemy.** Zamiast tego: **po 50 resetach-tamper (lifetime, licznik `reset_stats.se_tamper` w NVM3) firmware robi odwracalny wipe** na czystym starcie ([`sec_main.c`](../../../KeyFirmware/src/secure/sec_main.c), `TAMPER_SE_RESET_WIPE_THRESHOLD`).

**`tamper_reset_threshold = 0` (SE nigdy sam się nie zatrzymuje).** To pole w OTP to „po ilu resetach-tamper układ wchodzi w tryb diagnostyczny/halt”. Domyślna wartość SDK to **5** — czyli po 5 resetach (np. z szumu) SE **sam zatrzymałby układ = brick**. Ustawiamy **0 = nigdy**, zgodnie z „never auto-brick”: eskalację (wipe po 50) prowadzi firmware, nie sprzęt.

**Przez filtr nie tylko 17/18.** Debounce'ujemy też 10/11 Mailbox/DCI (brute force na debug-unlock / eksport kluczy) — zbijają ten sam wspólny licznik filtra, seria w oknie → reset, pojedyncze zdarzenie nigdy nie resetuje. **DPLL (23/24) celowo pomijamy:** nie używamy DPLL (zegar to HFXO + LFRCO), więc lock-fail nigdy nie odpali — uzbrojenie byłoby martwym wpisem, nie detektorem.

**Logowanie per-zdarzenie (`SETAMPERHOST_IRQHandler`, [`sec_tamper_otp.c`](../../../KeyFirmware/src/secure/sec_tamper_otp.c)):** logujemy zdarzenia **dyskretne** — 10/11 Mailbox/DCI (filtr jest kumulatywny z interruptem, więc i tak podnoszą `SETAMPERHOST`) oraz 15 TRNG (poziom 1). **Nie** logujemy per-szpilkę detektorów 17/18 — pod szumem ESD/USB zużyłoby to log we flashu; ich efektem jest dopiero odbouncowany reset. Każdy logowany wpis to `SE_INTERRUPT` + `tamper_event_count`.

**Uzbrajane poziomy OTP (`sec_tamper_otp.c`, `fill_tamper_levels`):**

| Sygnał SE (nr) | Ustawiany poziom | Efekt |
|---|---|---|
| 17 EMPGD, 18 SUPGD | 2 = Filtr | Detektory glitcha EM/zasilania; zbijają wspólny licznik filtra, nie resetują wprost |
| 10 Mailbox auth, 11 DCI auth | 2 = Filtr | Brute force na debug-unlock / eksport kluczy: seria → reset (rate-limit). Filtr jest kumulatywny z interruptem, więc każde zdarzenie nadal jest logowane |
| 1 Filter counter | 4 = Reset | Seria dowolnych źródeł filtra w oknie (~33 s, próg 4) → reset (odbouncowany); liczone w NVM3, wipe po 50 |
| 15 TRNG | 1 = Interrupt | Tylko log przez `SETAMPERHOST`, **bez** eskalacji do resetu (słaby/starzejący się TRNG nie może zapętlić resetów) |
| 2,4,5,7,8,12,14,16,19 (wewn. SE), 21 BOD | (zostaje 4 = Reset z domyślnego) | Reguła `MAX(domyślny, nasz)` — zostawiamy 0, i tak resetują |
| 22 temp, 23/24 DPLL, 25-31 PRS, 9 user-secure-boot | 0 = Ignore | Temperatura: software (−10/+70); DPLL: **nieużywany** (nie chodzi → lock-fail nigdy nie odpali, uzbrojenie = martwy wpis); PRS: pominięte |
| dowolny | **nigdy 7 (erase-OTP)** | Brick — nie używamy |

Filtr: okno `SL_SE_TAMPER_FILTER_PERIOD_33S`, próg `SL_SE_TAMPER_FILTER_THRESHOLD_4`. Flagi = 0 (glitch-detektor nie „always on”, tamper nie podtrzymywany w uśpieniu — oszczędza baterię w EM2).

**Voltage/digital software (7, 8) → tylko log.** Wpięcie USB (inrush) i słaby start kwarcu fałszywie podnoszą te flagi (do tego `tamper_manager_init()` nie czyści starych flag), więc wipe po 2 = ryzyko skasowania klienta po dwóch wpięciach. Prawdziwy szybki glitch łapie teraz SE 17/18.

**Temperatura — zostaje programowo.** −10/+70 jest celowe (serwerownie/biura). Czujnik SE 22 odpala dopiero ~−35/+120 °C, więc software odpala pierwszy; SE 22 pomijamy. Próg programowy podniesiony do 12 (1 min), bo awaria klimy w serwerowni potrafi godzinami trzymać >70 °C i przy progu 3 (15 s) kasowałaby legalne urządzenia.

**„Martwy firmware” / PRS (25–31) — pominięte.** Przy zawsze włączonym Secure Debug Lock atakujący nie wgra ani nie zatrzyma firmware przez SWD, więc główny powód dla PRS→SE odpada. Ochrona pinów zostaje na software pollu (firmware w produkcji zawsze działa, poll chodzi też w EM2).

**Numeracja sygnałów SE (MG24 = Series 2 Config 4, `sl_se_manager_defines.h`):** 17 EMPGD, 18 SUPGD, 21 BOD, 22 temp, 23/24 DPLL, 10/11 Mailbox/DCI, 15 TRNG. Numery **0, 3, 6, 13 to `RESERVED`** (puste, nie do użycia).

> **Uwaga wdrożeniowa:** uzbrojenie sygnałów SE to **nieodwracalny** `sl_se_init_otp()`, który zamraża też secure boot (OFF). Robimy to **wyłącznie w kroku provisioningu produkcyjnego** (`provision_dongle --lock`), **nigdy** automatycznie przy starcie ani na płytkach deweloperskich. Kod warstwy SE (firmware + host) jest **wdrożony i bramkowany tą ścieżką**; `_arm_tamper_otp` prosi o osobne potwierdzenie `ARM`, a dongle już uzbrojony zgłasza `OTP_INIT:1` i jest pomijany.
>
> **Zweryfikowane na sprzęcie (2026-11-13):** pierwszy dongiel (`...3E32FE`) przeszedł pełny `--lock`; status czyta `OTP_INIT:1;SECURE_BOOT:0;EMPGD:2;SUPGD:2;FILTER_CNT:4;RESET_THRESH:0`, debug lock `LOCK_ACTIVE:1`. Walidacja bez `--lock` najpierw wyłapała błąd mapowania statusu (`sl_se_read_otp` dla nieuzbrojonego OTP **nie** zwraca `COMMAND_IS_INVALID` — teraz każdy wynik `!= OK` = „nieuzbrojony"). `sl_se_read_otp` zwraca poziomy **użytkownika**, nie efektywne.
>
> **Flash a sen EM2:** dongiel śpi w EM2 (zegar debug stoi) → pyOCD „No ACK". `provision_dongle._keep_awake_flash` trzyma go wybudzonym przez heartbeat po COM (osobny interfejs USB od CMSIS-DAP) wokół każdego flasha. `flashbat` nadal nie ma kroku wybudzenia — ręczny `flash.bat` śpiącego dongla wymaga tego samego (scratchpad `flash_awake.py`).

### Funkcje układu poza modułem tamper SE

| Mechanizm | Status | Uwagi |
|---|---|---|
| Secure Debug Lock (SWD zamknięte, odblokowanie tokenem) | **Aktywne**, gdy keyadmin zablokuje dongle (`sec_debug_lock.c`) | Device Erase pozostaje włączony (nigdy nie wywołujemy `sl_se_disable_device_erase()`). |
| Secure boot (RTSL) | **Możliwe**, niewłączone | Trzeba zdecydować razem z OTP tamper SE (jedno wywołanie). |
| Podział TrustZone (Secure / Non-Secure) | **Aktywne** | Logika tamper i sekrety znajdują się w świecie Secure. |
| Device erase SE jako reakcja na tamper | **Aktywne** (jedyna reakcja na osiągnięty próg) | `sl_se_erase_device()`; nietestowane na sprzęcie. |

### Nasze detektory programowe (`tamper_manager.c`)

| Detektor | Status | Uwagi |
|---|---|---|
| Odpytywanie GPIO PC5 / PC6 (przełącznik obudowy, siatka przewodów; pull-up impulsowy co 1 s) | **Aktywne** | `tamper_external_init()` wołane w `app.c`; co 1 s włącza pull-up i próbkuje piny. Wymaga fizycznego przełącznika/siatki od pinów do GND — bez okablowania pull-up trzyma piny wysoko i nic się nie wyzwala. Próg 1. |
| Kontrole VRX (short / invalid / mismatch / no session) | **Aktywne** | Progi 30 / 30 / 50 / 30 (tolerancyjne). Może je też wyzwolić błąd klienta. |
| Flagi brown-out EMU (AVDD / IOVDD0) -> `VOLTAGE_GLITCH` | **Aktywne** | Próg 2. `tamper_manager_init()` nie czyści starych flag, więc flaga pozostała po włączeniu zasilania lub podłączeniu USB może zostać policzona jako zdarzenie (niezweryfikowane na sprzęcie). |
| Flagi błędów HFXO (did-not-start, buffer freeze) -> `DIGITAL_GLITCH` | **Aktywne** | Próg 2. Słaby start kwarcu też ustawia te flagi. |
| `EMU_TemperatureGet()` poza -10..+70 °C -> `TEMP_EXTREME` | **Aktywne** | Próg 3, odpytywanie co 5 s. Dużo ostrzejsze niż specyfikacja układu -40..+125 °C; dongle w nagrzanym samochodzie lub w zimnym aucie kuriera może go wyzwolić. |
| `tamper_manager_report_voltage_glitch()` (monitor baterii) | **Tylko API** | Nic jej nie wywołuje. |
| `tamper_manager_report_emp()` | **Tylko API** | Nic jej nie wywołuje. Prawdziwy czujnik EMP to źródło SE 17 powyżej. |
| Szyfrowany trwały log zdarzeń na stronie User Data | **Aktywne** | Zob. niżej. |

## Trwały log tamper (strona User Data)

Strona User Data (`0x0FE00000`, **1 KB**, jedyny obszar flash poza główną pamięcią flash w Series 2) nie jest kasowana przez device erase SE, mass erase, flashowanie ani odblokowanie debug. Cała strona mieści log zdarzeń: **64 wpisy x 16 B** (`tamper_log_entry_t`), pusty slot to same `0xFF`.

**Jeden wpis logu (16 B):** typ zdarzenia (lub `0xF0` = uruchomienie po resecie tamper Secure Engine, `0xF1` = zrzut liczników użycia), licznik danego typu w tym cyklu zasilania, flagi (`WIPE` = to zdarzenie wyzwoliło kasowanie, `COALESCED` = wchłonął starsze zdarzenia tego samego typu), timestamp RTC (UNIX), uptime 24-bit, setne sekundy, temperatura, CRC-16. Dekoder (`tamper_log_decoder.py`) wypisuje czas w ludzkim formacie `YYMMDD HHMMSS.cc` i typy skrótem 3-literowym (np. `VXM`, `TMP`, `EMP`). Wpis `0xF1` niesie 6 liczników użycia algorytmów (uint16) zamiast pól zdarzenia. Metadane tekstowe nie są zapisywane (zajmowałyby 4-8x więcej miejsca).

* **Szyfrowanie:** każdy wpis to jeden blok AES-128, szyfrowany przez Secure Engine (`sl_se_aes_crypt_ecb`) kluczem **Tamper Log Key** przed zapisem. Klucz jest wkompilowany w obraz Secure (`KeyFirmware/src/core/tamper_log_key.h`), więc kasowanie usuwa kopię w firmware. Kopia fabryczna to `KeySec/keyadmin/keys/tamper_log_key.bin`. Bez niej zrzut skasowanego dongla pokazuje tylko szyfrogram. Każdy wpis jest inny (RTC, uptime, licznik), więc ECB na pojedynczych blokach nie zdradza niczego użytecznego; atakujący widzi tylko, ile slotów jest zajętych. Jeśli SE odmówi szyfrowania, wpis jest pomijany, a nie zapisywany jawnym tekstem.
* **Zarządzanie kluczem:** `python keyadmin/scripts/generate_tamper_log_key.py` tworzy klucz jednorazowo i zapisuje nagłówek; `--header-only` generuje ponownie nagłówek z istniejącego klucza. Nie twórz nowego klucza, gdy dongle są już u klientów: ich logów nie dałoby się wtedy odczytać. Po wygenerowaniu przebuduj firmware.
* **Pojemność:** 64 wpisy. Gdy log jest pełny, **koalescencja** łączy najstarsze zdarzenia *najczęstszego* typu w jeden wpis (sumuje licznik, flaga `COALESCED`), zwalniając sloty; każdy rzadszy typ zachowuje własne wpisy z czasem. Dzięki temu zalew jednego typu (np. 50 niezgodności tokenu VRX) nie wypycha pozostałych zdarzeń z logu.
* **Zużycie:** wpisy są zapisywane do pustych slotów bez kasowania; kasowanie strony następuje tylko przy koalescencji (gdy log się zapełni). Przy typowych 10 000 cyklach kasowania flasha daje to dziesiątki-setki tysięcy zdarzeń na dongle, zależnie od tego, jak często log się przepełnia.
* **Utrata zasilania:** zapis przerwany w połowie nie przechodzi CRC po odszyfrowaniu i jest pokazywany jako `[CORRUPT or wrong key]`. Zanik zasilania podczas przepisywania strony (log pełny) może spowodować utratę logu: okno trwa kilka milisekund.
* **Czego się nie loguje:** własnych zdarzeń tamper Secure Engine, poza resetami, które one powodują (brak jeszcze konfiguracji OTP), oraz niczego sprzed tej wersji firmware'u.

### Jak fabryka go odczytuje

| Stan dongla | Jak odczytać |
|---|---|
| Skasowany po tamperze (device erase SE się powiódł) | Kasowanie usunęło też blokadę debug, a dongle nie ma firmware'u (brak USB). Podłącz sondę SWD i uruchom `python keyadmin/scripts/read_tamper_log.py`. Skrypt zrzuca 1 KB przez pyOCD, odszyfrowuje go kluczem `keyadmin/keys/tamper_log_key.bin` (lub `--key FILE`) i wypisuje log. |
| Zablokowany, ale jeszcze nieskasowany (np. dongle serwisowy) | `secure_debug_lock.py unlock` lub odblokowanie z menu administracyjnego: po odblokowaniu tokenem keyadmin automatycznie zrzuca i dekoduje stronę (`userdata_dump.bin` w folderze dongla). |
| Wcześniejszy plik zrzutu | `python keyadmin/scripts/read_tamper_log.py --file <dump.bin>` |

Po odczycie, zanim dongle wróci do użytku, skasuj stronę, bo ponowne flashowanie ją zachowuje: `commander device pageerase --region @userdata` (jeszcze nie uruchamiane na naszych donglach).

### Blokada debug po kasowaniu

**To jest wybrany projekt (wariant B).** `sl_se_erase_device()` to komenda SE „Erase Device”. W Series 2 zawsze pozostawia układ **odblokowany** po następnym resecie (tak działają standardowa i bezpieczna blokada debug, dopóki Device Erase jest włączony — a u nas jest). Dzięki temu po tamperze log odczytuje się od razu sondą SWD, a dongle **flashuje się i provisionuje normalnie — to nie jest trwały bric**. Fabryka może ponownie zablokować dongle po sflashowaniu (keyadmin `lock`; Command Key w OTP pozostaje).

**Niewybrana alternatywa:** gdyby skasowany dongle miał pozostać zablokowany, trzeba by wyłączyć Device Erase (`sl_se_disable_device_erase()`, nieodwracalne) i polegać na kasowaniu strona po stronie z RAM:

* Blokada pozostaje wtedy włączona.
* Tylko fabryka może otworzyć dongle tokenem secure debug, by odczytać log i ponownie sflashować.
* Koszt: utracony command key oznacza, że dongla nie da się już nigdy otworzyć.
* Nie zweryfikowano, czy kasowanie z RAM potrafi skasować strony świata Secure.

Przed wyborem tej opcji potrzebne są testy sprzętowe.
