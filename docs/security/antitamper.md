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

### External Protections (ETAMPDET):
The device features up to 8 external configurable tamper pins (External Tamper Detect - ETAMPDET). These are typically used to detect:
- **Case Opening / Enclosure Tamper:** Physical opening of the device casing.
- **Mesh/Wire Cut:** Cutting a security mesh or a wire loop around the PCB.

## Physical Implementation Requirements

To utilize the external tamper detection (ETAMPDET), specific physical hardware setup is required:
1. **Tamper Switch or Wire Loop:** A physical microswitch (for case opening) or a wire loop/security mesh must be connected to the dedicated ETAMPDET pins on the microcontroller.
2. **Pin Connections:** The ETAMPDET module can drive a pseudorandom signal out of an output pin (`ETAMPDET_OUT`) and read it back on an input pin (`ETAMPDET_IN`). 
3. If the loop is cut, shorted to ground, or shorted to VCC, the pseudorandom sequence mismatch is instantly detected. A filter window (e.g., waiting for a few mismatched samples) is usually configured to prevent false positives due to environmental noise.

## Code Examples

There are two main configurations for anti-tamper: configuring the Secure Engine (SE) OTP to handle the responses, and configuring the ETAMPDET peripheral to read the external switches.

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

### 2. Configuring External Tamper Pins (ETAMPDET)

The following example demonstrates how to configure the `ETAMPDET` module to detect an external physical tamper event, such as a case opening, utilizing filtering to prevent false positives.

```c
#include "sl_hal_etampdet.h"
#include "sl_interrupt_manager.h"

// Global flag to handle tamper detection in the main loop
volatile bool tamper_detected = false;

// ETAMPDET Interrupt Handler
void ETAMPDET_IRQHandler(void)
{
    // Disable further interrupts
    sl_interrupt_manager_disable_irq(ETAMPDET_IRQn);
    sl_hal_etampdet_disable_interrupts(ETAMPDET_IEN_TAMPDET0);

    // Clear the interrupt
    sl_hal_etampdet_clear_interrupts(ETAMPDET_IF_TAMPDET0);
    sl_interrupt_manager_clear_irq_pending(ETAMPDET_IRQn);

    // Set flag
    tamper_detected = true;
    
    // (Optional) Take immediate action here, such as wiping RAM variables
}

void etampdet_init_example(void)
{
    // Initialize ETAMPDET with default configuration
    sl_hal_etampdet_init_t etampdet_init = SL_HAL_ETAMPDET_INIT_DEFAULT;
    sl_hal_etampdet_init(&etampdet_init);

    // Configure ETAMPDET channel 0
    sl_hal_etampdet_channel_init_t channel_init = ETAMPDET_CHANNEL_INIT_DEFAULT;
    
    // Select channel 0 and provide a pseudorandom seed
    channel_init.channel = channel_0;
    channel_init.channel_seed_val = 0x13579BDF;

    // Enable filtering to reduce false triggers from noise
    channel_init.channel_tampdet_filt_en = true;
    channel_init.channel_filt_win_size = detect_filt_win_size_4; // window size = 4
    channel_init.channel_cnt_mismatch = detect_filt_threshold_3; // 3 failures in window trigger tamper

    // Initialize the channel
    sl_hal_etampdet_init_channel(&channel_init);

    // Clear any pending interrupts
    sl_hal_etampdet_clear_interrupts(ETAMPDET_IF_TAMPDET0);
    sl_interrupt_manager_clear_irq_pending(ETAMPDET_IRQn);

    // Enable interrupts for channel 0
    sl_hal_etampdet_enable_interrupts(ETAMPDET_IEN_TAMPDET0);
    sl_interrupt_manager_enable_irq(ETAMPDET_IRQn);

    // Enable ETAMPDET module globally
    sl_hal_etampdet_enable();
    sl_hal_etampdet_wait_sync();

    // Load the seed into channel 0 and start it
    sl_hal_etampdet_load(channel_init.channel);
    sl_hal_etampdet_start(channel_init.channel);
    sl_hal_etampdet_wait_sync();
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
