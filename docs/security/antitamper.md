# Anti-Tamper Protection (EFR32MG24 / Secure Vault High)

The EFR32MG24 microcontroller with Secure Vault High features a comprehensive hardware Anti-Tamper module designed to prevent both reverse engineering and logical attacks. It allows the system to rapidly detect tampering attempts and respond by triggering an interrupt, resetting the device, or completely erasing the One-Time-Programmable (OTP) memory, rendering the device inoperable (bricking).

## What is Detected?

The Anti-Tamper module monitors several hardware and software signals. It provides fast detection of both external physical tampering and internal logical or environmental attacks:

### Internal Protections:
1. **Voltage Glitching:** Detects sudden spikes or drops in the supply voltage (`VGLITCHFALLING`, `VGLITCHRISING`), commonly used to skip instructions or bypass security checks.
2. **Digital Glitching (`DGLITCH`):** Detects logic-level glitches within the chip.
3. **Temperature Extremes:** Detects forced heating or freezing of the chip used to induce faults or read SRAM contents.
4. **Electromagnetic Pulses (EMP):** Detects intense magnetic fields or radiation often used in fault injection attacks.
5. **Security Sub-System Tampering:** Detects logical attacks like failed authentication attempts, Secure Boot (RTSL) failures, and unauthorized debug access.

### External Protections (Hardware Switches & Wire Loops):
The device features up to 8 external configurable tamper sources (or handled via GPIO external interrupts with glitch filters). These are typically used to detect:
- **Case Opening / Enclosure Tamper:** Physical opening of the device casing.
- **Mesh/Wire Cut:** Cutting a security wire loop or breaking a microswitch circuit around the PCB.

> **Hardware Note (EFR32MG24 vs ETAMPDET):** The hardware peripheral `ETAMPDET` (External Tamper Detect with PRBS LFSR pseudo-random bit sequence generation) is available only on EFR32xG25, EFR32xG27, EFR32xG29, and Series 3 devices. The EFR32MG24 (Seeed XIAO MG24) does NOT feature the ETAMPDET peripheral; external physical protection is implemented via GPIO external interrupts with pull-up resistors and digital glitch filtering, routed directly to `TamperManager` (`tamper_manager_detected()`).

## Physical Implementation Requirements

To utilize external tamper detection on EFR32MG24:
1. **Tamper Switch or Wire Loop:** A physical microswitch (for case opening) or a wire loop must be connected between the designated tamper GPIO pins (PC5 / PC6 on XIAO MG24) and Ground (GND).
2. **Pull-Up & Glitch Filter:** The pins are configured in `SL_GPIO_MODE_INPUT_PULL_FILTER` mode. When the casing is closed, the circuit pulls the pin to GND (logic 0).
3. If the loop is cut, the wire detached, or the casing opened, the internal pull-up resistor immediately raises the line to VCC (logic 1), firing an interrupt on the rising edge and notifying `TamperManager`.

## Code Examples

There are two main configurations for anti-tamper: configuring the Secure Engine (SE) OTP to handle autonomous hardware responses, and configuring GPIO external interrupt inputs with TamperManager to detect physical casing and wire breaches.

### 1. Configuring the Secure Engine (Internal Protections)

The tamper responses are permanently programmed into the Secure Engine's OTP memory using `sl_se_init_otp()`. 
**WARNING:** This action is irreversible. It configures the hardware to automatically erase its secrets when under attack.

```c
#include "sl_se_manager.h"

void configure_secure_engine_tamper(void)
{
    sl_se_otp_init_t otp_settings_init = SL_SE_OTP_INIT_DEFAULT;

    // Glitches can have spurious activations. Instead of erasing OTP immediately,
    // we route them to a filter. If too many glitches occur in a time window,
    // the filter triggers the main response.
    otp_settings_init.tamper_levels[SL_SE_TAMPER_SIGNAL_FILTER] = SL_SE_TAMPER_LEVEL_PERMANENTLY_ERASE_OTP;
    
    // Route glitch detectors to the filter
    otp_settings_init.tamper_levels[SL_SE_TAMPER_SIGNAL_VGLITCHFALLING] = SL_SE_TAMPER_LEVEL_FILTER;
    otp_settings_init.tamper_levels[SL_SE_TAMPER_SIGNAL_VGLITCHRISING]  = SL_SE_TAMPER_LEVEL_FILTER;
    otp_settings_init.tamper_levels[SL_SE_TAMPER_SIGNAL_DGLITCH]        = SL_SE_TAMPER_LEVEL_FILTER;

    // Configure the filter: Trigger if 4 incidents occur within 1 minute
    otp_settings_init.tamper_filter_period = SL_SE_TAMPER_FILTER_PERIOD_1MIN;
    otp_settings_init.tamper_filter_threshold = SL_SE_TAMPER_FILTER_THRESHOLD_4;

    // Commit the settings to OTP (ONE TIME OPERATION!)
    sl_se_init_otp(&otp_settings_init);
}
```

#### 2. Configuring External Tamper Pins (EFR32MG24 GPIO & TamperManager)

The following code (implemented in [`tamper_simulation.c`](../../../KeyFirmware/src/core/tamper_simulation.c)) demonstrates how external physical tamper events (such as case opening or wire loop cuts on PC5 / PC6) are configured and handled on the EFR32MG24 using digital glitch filtering and interrupts:

```c
#include "sl_gpio.h"
#include "tamper_manager.h"

// Define physical pins on Seeed XIAO MG24
#define TAMPER1_PORT  SL_GPIO_PORT_C
#define TAMPER1_PIN   5

static sl_gpio_t tamper_gpio = { .port = TAMPER1_PORT, .pin = TAMPER1_PIN };
static int32_t int_no = -1;

// Hardware GPIO Interrupt Callback (runs when circuit is broken / casing opened)
static void tamper1_callback(uint8_t pin, void *ctx)
{
    (void)pin;
    (void)ctx;
    // Notify central TamperManager
    tamper_manager_detected(TAMPER_TYPE_PHYSICAL_PIN1, "Casing opened / Wire 1 severed");
}

void configure_external_tamper_pin(void)
{
    // Configure pin as input with pull-up and digital glitch filter enabled
    sl_gpio_set_pin_mode(&tamper_gpio, SL_GPIO_MODE_INPUT_PULL_FILTER, 1);

    // Allocate and configure rising edge interrupt
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
* Gdy tylko puścisz przycisk (otwarcie obudowy), wewnętrzny licznik 	amper_event_count rośnie o 1. Wbudowana dioda na płytce XIAO **zamiga szybko jeden raz**.
* Jeśli znów wciśniesz i po chwili puścisz przycisk, układ zanotuje to jako drugi atak. Dioda zamiga **dwa razy pod rząd**. Liczba błysków LED zawsze obrazuje całkowitą sumę zarejestrowanych naruszeń.

**Krok 2: Test Telemetrii (Komunikacja z Windows)**
* Włącz Dongle'a i uruchom w systemie Windows nasz skrypt backendowy: python main.py.
* Jeśli wcześniej klikałeś przyciskiem, Dongle ciągle przechowuje to w pamięci RAM.
* W trakcie autoryzacji (krok 1.7), Python odpyta dongle'a o kondycję sprzętową (MSG_SYS_HEALTH).
* Ponieważ dongle zanotował atak, wyśle raport do Windowsa.
* W konsoli Windowsa natychmiast po połączeniu zobaczysz ogromny alert bezpieczeństwa:
`	ext
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!! CRITICAL SECURITY ALERT: PHYSICAL TAMPER DETECTED !!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
`
Oraz bieżący odczyt parametrów środowiskowych wyciągnięty ze sprzętu, np.:
TamperEvents: 2, Temp: 24.5C

> **Ważna uwaga fizyczna:** Obecna konfiguracja "wersji testowej" przechowuje wynik w szybkiej pamięci RAM, by uchronić żywotność Flasha i nie uszkodzić Secure Engine (OTP). To oznacza, że jeżeli **całkowicie odłączysz zasilanie** (np. wyjmiesz układ z USB w celu przeniesienia na inne biurko), to log w RAM zniknie i po podłączeniu licznik znowu będzie wynosił zero. Do testowania samej mechaniki obudowy wystarczy zasilanie z powerbanka i obserwacja diody LED!
