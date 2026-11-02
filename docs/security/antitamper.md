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

// Signal names below are the EFR32MG24 (Series 2 config 4) names from sl_se_manager_defines.h.
// Names such as VGLITCHFALLING / DGLITCH exist only on EFR32xG21 and do not compile for MG24.
void configure_secure_engine_tamper(sl_se_command_context_t *cmd_ctx)
{
    sl_se_otp_init_t otp_settings_init = SL_SE_OTP_INIT_DEFAULT;  // also carries the secure boot settings!

    // Glitches can have spurious activations. Instead of erasing OTP immediately,
    // we route them to a filter. If too many glitches occur in a time window,
    // the filter triggers the main response.
    otp_settings_init.tamper_levels[SL_SE_TAMPER_SIGNAL_FILTER_COUNTER] = SL_SE_TAMPER_LEVEL_PERMANENTLY_ERASE_OTP;

    // Route glitch detectors to the filter
    otp_settings_init.tamper_levels[SL_SE_TAMPER_ATAMPDET_SUPGD] = SL_SE_TAMPER_LEVEL_FILTER;  // 18: supply glitch
    otp_settings_init.tamper_levels[SL_SE_TAMPER_ATAMPDET_EMPGD] = SL_SE_TAMPER_LEVEL_FILTER;  // 17: digital / EMP glitch

    // Configure the filter: Trigger if 4 incidents occur within 1 minute
    otp_settings_init.tamper_filter_period = SL_SE_TAMPER_FILTER_PERIOD_1MIN;
    otp_settings_init.tamper_filter_threshold = SL_SE_TAMPER_FILTER_THRESHOLD_4;

    // Commit the settings to OTP (ONE TIME OPERATION, secure boot settings included!)
    sl_se_init_otp(cmd_ctx, &otp_settings_init);
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

## TamperManager in KeyFirmware: detection, logging and wipe (as implemented)

Code: `KeyFirmware/src/core/tamper_manager.c` (Secure world), entry points through NSC gates in `src/secure/nsc_interface.c`.

### Central mechanism

Every detector ends in one function, `tamper_manager_detected(type, metadata)`, which runs in the **Secure world**. It increments a per-type counter and, when the counter reaches the type's threshold, calls `tamper_manager_trigger_wipe()` once per boot.

| Type | Source (who calls it) | Threshold |
|---|---|---|
| `PHYSICAL_PIN1` / `PIN2` | PC5 / PC6 GPIO interrupts, `tamper_simulation.c` (Non-Secure) → `nsc_tamper_manager_detected` | 3 / 3 |
| `LOGICAL_VRX_SHORT` | Truncated VRX packet, `prod_router.c` (Non-Secure) | 5 |
| `LOGICAL_VRX_INVALID` / `MISMATCH` / `NO_SESSION` | `security_users.c` (Secure) | 5 / 3 / 5 |
| `VOLTAGE_GLITCH` | AVDD / IOVDD0 brown-out flags in `EMU->IF`, polled by `tamper_manager_process()` | 2 |
| `DIGITAL_GLITCH` | HFXO error flags in `HFXO0->IF`, same poll | 2 |
| `TEMP_EXTREME` | `EMU_TemperatureGet()` every 5 s, outside -10..+70 °C | 3 |
| `EMP` | `tamper_manager_report_emp()` exists but **nothing calls it** (no EMP sensor) | 1 |

`tamper_manager_process()` is called from the Non-Secure main loop (`app.c`) through `nsc_tamper_manager_process()`. The Secure Engine's own hardware tamper responses (`sl_se_otp_init_t.tamper_levels`) are **not** configured; they are only described in comments.

Counters are kept in Secure RAM only. A reset or power cycle sets them back to zero, so every threshold means "N events within one power cycle".

### Logging

* **Nothing the Secure world logs reaches USB.** In the Secure image `send_log()` is a stub (`sec_main.c`) and `tamper_manager_init(NULL)` leaves `active_tf` empty. The per-event `SECURITY ALERT` line and the final `CRITICAL: SELF-DESTRUCT` line are built but dropped.
* What the host does see:
  * PC5 / PC6 events: the Non-Secure `tamper_simulation.c` sends its own `SECURITY ALERT` log, and the LED blinks.
  * VRX events: only the error reply to the failed call (`ERR: Tamper attempt detected`).
  * `MSG_SYS_HEALTH` (`0x10`): `TamperEvents:<total>, Temp:<t>, TamperLog:<entries in the persistent log>`.
* **Persistent event log**: every tamper event is written, AES-encrypted, to the **User Data page `0x0FE00000`**, which survives the wipe. The entry of the event that reached its threshold carries the WIPE flag. See [Persistent tamper log](#persistent-tamper-log-user-data-page). The old Black Box record (192 B, written once at the threshold) was removed: the log already holds the trigger, its time and temperature.

### Response when a threshold is reached

1. The triggering event is already in the persistent log with the WIPE flag.
2. The response depends on the build switch `TAMPER_ENABLE_CODE_FLASH_SELF_DESTRUCT`:

| | Dev mode (default, `0`) | Live wipe (`1`) |
|---|---|---|
| NVM3 (license, certificate, max users, identity key) | Deleted (`security_nvm_wipe_all`) | Erased with the rest of the flash |
| Secure + Non-Secure code | Kept: the dongle keeps running | **Erased**: `sl_se_erase_device()`, a Secure Engine mass erase that clears and verifies all main flash **and RAM** |
| Debug lock | Unchanged | Reset to unlocked by the SE: the empty chip can be reflashed and the User Data page read without an unlock token (the log is encrypted) |
| If the SE refuses (device erase disabled) | n/a | Fallback: NVM3 objects are deleted, then `tamper_manager_self_destruct_ram()` erases main flash page by page from RAM, then halts |

> **Even dev mode is destructive for the customer's data:** 3 VRX token mismatches within one power cycle already delete the license and the identity key from NVM3.

The device erase stays available because `sec_debug_lock.c` never calls `sl_se_disable_device_erase()`. If that is ever called, only the RAM fallback is left. Whether the Non-Secure MSC can erase Secure-world flash pages has not been verified, so the fallback may leave the Secure code in place.

### Enabling the live wipe

```bat
set TAMPER_LIVE_WIPE=ON
flashbat\compile.bat
```

`compile.bat` passes `-D KEYFIRMWARE_TAMPER_LIVE_WIPE=ON|OFF` on every configure, so the setting never sticks in the CMake cache. CMake prints a warning when it is ON. Any build without the variable is a safe dev-mode build.

**Before shipping with live wipe ON, review the thresholds.** Software-reachable events (the VRX types) and environmental ones (brown-out, HFXO, temperature) can then destroy a customer's dongle. A client bug that sends 3 bad VRX tokens in one session would do it.

**Hardware test (sacrificial dongle):**
1. Flash a live-wipe build.
2. Toggle PC5 to GND three times.
3. The dongle disappears from USB. Its flash reads back as `0xFF` and `read_tamper_log.py` shows the PIN1 events, the last one with `-> WIPE`.

This path has not been run on hardware yet.

## Anti-tamper mechanisms: status on the dongle

Checked against the Simplicity SDK 2026.6.1 headers (`sl_se_manager_defines.h`, `efr32mg24b220f1536im48.h`) and the Silicon Labs Secure Vault tamper documentation (AN1247, Appendix C "Other Series 2 HSE-SVH devices"). The XIAO MG24 chip is an **EFR32MG24B220F1536IM48**, Secure Vault **High** (`_SILICON_LABS_SECURITY_FEATURE_VAULT`), Series 2 config 4, so the full SE tamper module is present. The XIAO board itself has **no** tamper hardware: switches, meshes and potting are ours to add.

**Key constraint:** all Secure Engine responses are written by `sl_se_init_otp()` into SE OTP **once, together with the secure boot settings**, and can never be changed. If we burn a tamper configuration with secure boot off, secure boot can never be turned on for that chip. Both have to be decided and provisioned in one factory step.

Legend: **Active** = works on dongles today. **Code only** = implemented, depends on build flags or wiring. **Possible** = the hardware supports it, nothing done yet. **N/A** = not available on this chip.

### Secure Engine hardware tamper sources (EFR32MG24, numbering from the SDK)

| SE source | What it detects | Default response (no OTP config) | Status | What enabling takes |
|---|---|---|---|---|
| 2, 4, 5, 7, 8, 12, 14, 16, 19 (SE watchdog, SE RAM ECC2, SE hard fault, SE assertion, SE firmware secure boot, OTP read, self test, secure lock, SE ICACHE) | Faults inside the Secure Engine itself | 4 = Reset | **Active** (built in, cannot be lowered) | Nothing. Since this change a reset caused by any SE tamper source is written to the persistent log at the next boot (`EMU_RSTCAUSE_SETAMPER`). |
| 21 BOD | Brown-out of the supply | 4 = Reset | **Active** (reset only) | Nothing. Same reset-cause logging as above. |
| 17 Digital glitch (`SL_SE_TAMPER_ATAMPDET_EMPGD`, "EMP glitch detector") | Fault injection by EM pulse / clock / logic glitch. **This is the only real EMP sensor on the chip.** | 0 = Ignore | **Possible**, not configured. Our `TAMPER_TYPE_EMP` has no source. | OTP level 1 (interrupt) to log it through `SETAMPERHOST_IRQHandler`, or 2 (filter) / 4 (reset). By default it runs only while the SE executes a command; staying armed needs the "digital glitch always on" OTP flag or `sl_se_enter_active_mode()` (higher current). |
| 18 Voltage glitch (`SL_SE_TAMPER_ATAMPDET_SUPGD`) | Fast supply glitches (fault injection) | 0 = Ignore | **Possible**, not configured | OTP level 1 / 2 / 4. |
| 22 Temperature sensor | Die temperature within 5 °C of the device limits (MG24: -40..+125 °C) | 0 = Ignore | **Possible**, not configured | OTP level 1 / 2 / 4. Much saner limits than our software -10..+70 °C. |
| 23 / 24 DPLL lock fail low / high | Clock manipulation through the DPLL | 0 = Ignore | **Possible**, little value (our firmware does not rely on the DPLL) | OTP level. |
| 25-31 PRS0-PRS6 | Any on-chip signal routed through PRS, e.g. the **PC5 / PC6 tamper pins** | 0 = Ignore | **Possible**, not configured | Route the GPIO through PRS to the SE tamper consumer + OTP level 4 (reset) or 7. The SE then reacts even if the CPU firmware is compromised. |
| ETAMPDET (external tamper detect with LFSR mesh) | Active mesh with pseudo-random pattern | n/a | **N/A**: only on Series 2 config 5 / 9 (xG25, xG29...) and Series 3 | Use PC5 / PC6 (+ PRS) instead. |
| 10 / 11 Mailbox / DCI authorization | Wrong debug-unlock tokens, attempts to export non-exportable keys | 0 = Ignore | **Possible**, not configured | OTP level 2 (filter) would slow down brute force against the Secure Debug unlock. |
| 15 TRNG monitor | Lack of entropy (TRNG attacked or broken) | 0 = Ignore | **Possible**, not configured | OTP level 1 or 4. |
| 9 User secure boot | Our firmware signature failed | 0 = Ignore | **N/A until secure boot is on** | Secure boot (RTSL) is not enabled (`compass_security_mechanisms.md` §10). |
| Response level 7 "Erase OTP" | Bricks the chip permanently (OTP keys gone, part never boots again) | n/a | Not used | Only for sources with zero false positives. Not recommended for us. |

### Chip features outside the SE tamper module

| Mechanism | Status | Notes |
|---|---|---|
| Secure Debug Lock (SWD closed, token-based unlock) | **Active** when keyadmin locks the dongle (`sec_debug_lock.c`) | Device Erase stays enabled (we never call `sl_se_disable_device_erase()`). |
| Secure boot (RTSL) | **Possible**, not enabled | Must be decided together with the SE tamper OTP (one call). |
| TrustZone split (Secure / Non-Secure) | **Active** | Tamper logic and secrets live in the Secure world. |
| SE device erase as the wipe | **Code only** (`TAMPER_LIVE_WIPE=ON`), default OFF | Untested on hardware. |

### Our software detectors (`tamper_manager.c`)

| Detector | Status | Notes |
|---|---|---|
| PC5 / PC6 GPIO interrupts (enclosure switch, wire mesh) | **Code only** | Needs a switch or mesh wired from PC5 / PC6 to GND. Without it the pull-up keeps the pins high and nothing fires. Threshold 3. |
| VRX checks (short / invalid / mismatch / no session) | **Active** | Thresholds 5 / 5 / 3 / 5. Can also be triggered by a client bug. |
| EMU brown-out flags (AVDD / IOVDD0) -> `VOLTAGE_GLITCH` | **Active** | Threshold 2. `tamper_manager_init()` does not clear stale flags, so a flag left from power-up or a USB plug-in may count as an event (not verified on hardware). |
| HFXO error flags (did-not-start, buffer freeze) -> `DIGITAL_GLITCH` | **Active** | Threshold 2. A weak crystal start-up also sets these flags. |
| `EMU_TemperatureGet()` outside -10..+70 °C -> `TEMP_EXTREME` | **Active** | Threshold 3, polled every 5 s. Much stricter than the chip's -40..+125 °C rating; a dongle in a hot car or a cold courier van can trip it. |
| `tamper_manager_report_voltage_glitch()` (battery monitor) | **API only** | Nothing calls it. |
| `tamper_manager_report_emp()` | **API only** | Nothing calls it. The real EMP sensor is SE source 17 above. |
| Encrypted persistent event log in the User Data page | **Active** | See below. |

## Persistent tamper log (User Data page)

The User Data page (`0x0FE00000`, **1 KB**, the only flash outside main flash on Series 2) is not erased by the SE device erase, a mass erase, flashing, or a debug unlock. The whole page holds the event log: **64 entries x 16 B** (`tamper_log_entry_t`), a blank slot is all `0xFF`.

**One log entry (16 B):** event type (or `0xF0` = boot after a Secure Engine tamper reset), the per-type count in this power cycle, a "this event triggered the wipe" flag, RTC timestamp, uptime in seconds, temperature, CRC-16. The free-text metadata is not stored (it would cost 4-8x the space).

* **Encryption:** each entry is one AES-128 block, encrypted with the **Tamper Log Key** by the Secure Engine (`sl_se_aes_crypt_ecb`) before it is written. The key is compiled into the Secure image (`KeyFirmware/src/core/tamper_log_key.h`), so the wipe erases the firmware copy. The factory copy is `KeySec/keyadmin/keys/tamper_log_key.bin`. Without it a dump of a wiped dongle shows only ciphertext. Every entry differs (RTC, uptime, count), so ECB on single blocks leaks nothing useful; an attacker sees only how many slots are used. If the SE refuses to encrypt, the entry is skipped rather than written in plaintext.
* **Key management:** `python keyadmin/scripts/generate_tamper_log_key.py` creates the key once and writes the header; `--header-only` regenerates the header from the existing key. Do not create a new key once dongles are in the field: their logs could no longer be read. Rebuild the firmware after generating.
* **Capacity:** 64 events. When the log is full, the oldest 32 entries are dropped and the newest 32 kept (one page erase). The newest events are therefore always there.
* **Wear:** entries are written into blank slots without erasing; an erase happens only once per 32 events. With the usual 10,000 flash erase cycles that is about 320,000 events per dongle.
* **Power loss:** a write cut halfway fails the CRC after decryption and is shown as `[CORRUPT or wrong key]`. A power cut during the page rewrite (log full) can lose the log: a window of a few milliseconds.
* **What is not logged:** the Secure Engine's own tamper events, except the resets they cause (no OTP configuration yet), and anything before this firmware version.

### How the factory reads it

| Dongle state | How to read |
|---|---|
| Wiped by the live wipe (SE device erase succeeded) | The erase also removed the debug lock and the dongle has no firmware (no USB). Connect SWD and run `python keyadmin/scripts/read_tamper_log.py`. It dumps 1 KB with pyOCD, decrypts it with `keyadmin/keys/tamper_log_key.bin` (or `--key FILE`) and prints the log. |
| Still running (dev mode, or locked but not wiped) | `secure_debug_lock.py unlock` or admin menu unlock: after the token unlock keyadmin dumps and decodes the page automatically (`userdata_dump.bin` in the dongle's folder). |
| An earlier dump file | `python keyadmin/scripts/read_tamper_log.py --file <dump.bin>` |

After reading, before the dongle goes back into service, erase the page, because reflashing keeps it: `commander device pageerase --region @userdata` (not yet run on our dongles).

### Debug lock after a wipe

`sl_se_erase_device()` is the SE "Erase Device" command. On Series 2 it always leaves the chip **unlocked** after the next reset. This is how standard and secure debug lock work while Device Erase is enabled, and we cannot change it. The factory can lock the dongle again after reflashing (keyadmin `lock`; the command key in OTP stays).

If a wiped dongle must stay locked, the alternative is to disable Device Erase (`sl_se_disable_device_erase()`, irreversible) and rely on the page-by-page RAM wipe:

* The lock then stays on.
* Only the factory can open the dongle, with the secure debug token, to read the log and reflash.
* The cost: a lost command key means the dongle can never be opened again.
* It is not verified that the RAM wipe can erase the Secure-world pages.

Hardware tests are needed before choosing this.
