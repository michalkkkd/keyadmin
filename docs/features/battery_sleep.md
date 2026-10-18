# Power Management and USB Detection (Battery Sleep)

## Architectural Context
The EFR32MG24 chip does not have a built-in hardware USB controller. On development boards (e.g., Seeed XIAO MG24), the USB port is handled by a coprocessor (SAMD11), which acts as a USB-UART bridge. The EFR32 communicates with it exclusively through pins `PA08` (TX) and `PA09` (RX).

Because the backup battery (e.g., for the RTC) will be permanently soldered, the chip must be able to flawlessly enter Deep Sleep mode (EM2) when the USB cable is disconnected (or the application is inactive) to minimize battery drain. Due to the lack of a direct hardware connection of the VBUS pin to the processor, connection detection has been implemented **100% in software**, eliminating the need for hardware modifications (soldering additional resistors on the prototype board).

## Software Solution Description (Heartbeat + Wake-on-RX)

The mechanism is based on two pillars combined with the Low-Power SDK environment:

### 1. Sleeping based on Timeout (Heartbeat / Ping-Pong)
According to the *Fail Fast* principle, the device must constantly verify if the PC application (KeySec) is active.
* The PC Application periodically sends a message to the serial port (`MSG_PING`).
* The firmware responds to this message, and simultaneously resets its internal inactivity timer.
* A lack of incoming `MSG_PING` messages within a designated time window (timeout, e.g., 20 seconds) indicates that the cable has been disconnected or the PC application is closed.
* The firmware removes the Deep Sleep block using the command: `sl_power_manager_remove_em_requirement(SL_POWER_MANAGER_EM1);`, and the OS (Silicon Labs Power Manager) automatically puts the processor to sleep in EM2 mode.

### 2. Waking up via RX Line Interrupt (Wake-on-RX)
When the chip is sleeping in EM2 mode, its main oscillator (high-frequency clock) and UART peripherals are turned off to save energy.
* The receive pin `PA09` (RX) is configured at the hardware level as an **asynchronous GPIO interrupt** reacting to a falling edge. The GPIO module is one of the few that listens in EM2 mode.
* To initiate communication with the sleeping device, the PC application (KeySec) must first send a **"Dummy Byte"**, e.g., `0x00`.
* The physical voltage state change on the RX pin hardware-wakes the processor to EM1 mode. The firmware, awakened by the interrupt, immediately blocks returning to sleep (`sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1);`).
* **Note for the Python layer:** The first sent wake-up byte will be destroyed because the EFR32 processor clock needs a fraction of a second to start. For this reason, the PC app always sends `0x00`, waits e.g., 15 milliseconds for the chip to synchronize, and only then sends the actual (cryptographic) command.

---

## Use Case Scenarios (Edge Cases & Fail-Safes)

The system behavior described below relies on a fundamental architectural principle:
> *The system always goes to sleep in the absence of confirmed communication (Timeout), and wakes up exclusively upon a physical electrical impulse (Falling Edge) on the RX line.*

### Scenario A: Device disconnected ➔ App starts ➔ Device connected
* **Initial State:** Device is in Deep Sleep (EM2) running on battery. App waits for the COM port.
* **Flow:** Upon USB connection, the PC app opens the new COM port, sends the *Dummy Byte*, waits a moment, and sends the first operational command.
* **Result:** The hardware interrupt on the RX pin instantly wakes the EFR32. The command is correctly received, and the system resumes normal operation.

### Scenario B: Device connected ➔ App just starts
* **Initial State:** Device is plugged into the PC's USB but is sleeping (EM2) because a timeout occurred due to the PC app not running previously.
* **Flow:** The user launches the KeySec app. The app opens the existing port, sends the *Dummy Byte*, and after ~15 ms sends the initializing command.
* **Result:** EFR32 wakes up identically to Scenario A and instantly gets to work.

### Scenario C: Normal operation ➔ User closes PC app (Crash)
* **Initial State:** Chip is awake (EM1), correct communication ongoing.
* **Flow:** The PC app is unexpectedly closed or crashes (heartbeats stop).
* **Result:** The firmware timeout cycle expires. EFR32 safely removes the EM1 block requirement and immediately returns to Deep Sleep (EM2), radically saving the battery. (Implementation of the *Fail Fast* and *Defensive Programming* principles).

### Scenario D: Normal operation ➔ USB cable physically ripped out
* **Initial State:** Chip is awake (EM1).
* **Flow:** Power to the SAMD11 bridge chip on the board drops, the physical transmission line goes dead. Connection with the PC drops.
* **Result:** Behavior identical to Scenario C – EFR32 waits for messages, hits a timeout, and goes to sleep (EM2).

### Scenario E: Device plugged into USB ➔ No running PC app on target computer
* **Initial State:** Device sleeping (EM2) on battery.
* **Flow:** Device plugged into a computer (or external wall charger). Battery charges via 5V VBUS, but the COM port on the PC remains unopened (no one sends an RX signal).
* **Result:** EFR32 **remains deeply asleep (EM2)**. This is a deliberate and desired behavior – the EFR32 processor ignores the power connection, saving clock cycles, knowing it won't establish effective authorization due to the lack of PC software.

### Scenario F: False Wakeup (Glitches / Foreign terminal)
* **Initial State:** Device sleeping (EM2).
* **Flow:** A glitch mimicking UART transmission occurs on the cable, OR a random user opens the port in an external terminal like PuTTY and presses the spacebar.
* **Result:** EFR32 catches an impulse on the RX pin and wakes up prophylactically to EM1. The processor blocks sleeping, expecting formal data exchange. Since neither the glitch nor the random terminal will continue sending heartbeats, the device quickly reports a timeout. After a few seconds, the firmware irreversibly puts the chip to EM2 sleep.
* **Conclusion:** The device has high tolerance for interference (False Wakeups), protecting the battery against unjustified discharge.
