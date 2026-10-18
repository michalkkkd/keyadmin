# Power Management and USB Detection (Battery Sleep)

## Architectural Context
The EFR32MG24 chip does not have a built-in hardware USB controller. On Seeed Studio XIAO MG24 development boards, USB connectivity is provided by an on-board coprocessor (SAMD11 / DAPLink CMSIS-DAP) acting as a USB-to-UART bridge. The EFR32MG24 communicates with it exclusively through pins `PA08` (TX) and `PA09` (RX) at 921,600 baud.

Because the backup battery (for the Real-Time Clock and anti-tamper circuitry) is permanently connected, the chip must automatically transition into ultra-low-power Deep Sleep mode (**EM3**) whenever the USB cable is unplugged, the PC enters sleep, or the host application terminates. Due to the lack of a dedicated hardware VBUS sense line routed to the EFR32 microcontroller, connection detection is handled **100% in software via an active Heartbeat and asynchronous Wake-on-RX protocol**.

---

## Operating Modes (Energy Modes)

The system operates across three distinct Silicon Labs Energy Modes (EM):

| Mode | Name | CPU Core | Perypherals (EUSART0, DMA, Clocks) | Current Draw | Wakeup Latency | Description |
|:---|:---|:---|:---|:---:|:---:|:---|
| **EM0** | **Active** | ARM Cortex-M33 running at 78 MHz | All high-speed clocks (HFXO/DPLL), DMA, EUSART, and Vault hardware crypto active | ~6–8 mA | 0 ns | Actively decrypting, executing secure algorithms (RPCs), and encrypting responses. |
| **EM1** | **Active Idle** | Paused via `WFI` (Wait For Interrupt) | **100% active.** High-frequency oscillator (HFXO), DMA, and EUSART0 listen at 921,600 baud | ~1.5–2.5 mA | ~38 ns (3 CPU cycles) | Micro-sleep between UART bytes/packets. Preserves instantaneous 0-delay response. |
| **EM3** | **Deep Sleep** | Powered down; RAM retained | High-speed clocks and UART disabled. Only ULFRCO (1 kHz) and GPIO interrupt detection active | **~1 µA** | ~10 µs | Ultra-low-power battery retention mode entered when host application heartbeat is absent. |

---

## Software Solution Description (Heartbeat + Asynchronous Wake-on-RX)

The architecture is built upon two coordinated mechanisms:

```
[ PC Application (KeySec) ]
       |
       |  (Sends RPCs & periodic MSG_PING heartbeats every 3.0s)
       v
+-----------------------------------------------------------------------------------+
| 1. ACTIVE STATE (EM0 / EM1)                                                       |
|    - Lock held: sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1)         |
|    - PA09 GPIO falling-edge interrupt is STRICTLY DISABLED to prevent ISR storms  |
|    - EUSART0 and DMA receive bytes at 921,600 baud with zero overhead             |
|    - Heartbeat refreshes inactivity_timer (4.5s countdown)                        |
+-----------------------------------------------------------------------------------+
       |
       |  (Inactivity timeout: 4.5s without Heartbeat / Traffic)
       v
+-----------------------------------------------------------------------------------+
| 2. HEARTBEAT LOST WARNING (3.0s Transition)                                       |
|    - Status LED turns ON solid for 3.0 seconds as a visual warning                |
|    - Device remains in EM1 (can instantaneously recover if heartbeat arrives)     |
+-----------------------------------------------------------------------------------+
       |
       |  (Warning expires without heartbeat resumption: total 7.5s elapsed)
       v
+-----------------------------------------------------------------------------------+
| 3. DEEP SLEEP (EM3 Mode)                                                          |
|    - Lock released: sl_power_manager_remove_em_requirement(SL_POWER_MANAGER_EM1)   |
|    - PA09 GPIO falling-edge interrupt is ARMED (sl_gpio_enable_interrupts)         |
|    - MCU enters EM3 (~1 µA consumption)                                           |
|    - First falling edge on RX triggers rx_wakeup_callback, disarms GPIO ISR,     |
|      restores EM1 requirement, and wakes MCU to EM0                               |
+-----------------------------------------------------------------------------------+
```

### 1. Inactivity & Heartbeat Protocol (Ping-Pong Countdown)
1. **First Heartbeat Gate**: Upon power-on boot, `sleep_feature_enabled` is initialized to `false`. The sleep timer countdown does not activate until the first valid `MSG_PING` is received from the host, preventing the MCU from going to sleep while awaiting initial configuration or immediately after flashing.
2. **Periodic Host Heartbeat**: The host PC application (`KeySec/keycomm/core/transport.py`) maintains a background thread (`_heartbeat_loop`) that transmits `MSG_PING` frames every **3.0 seconds**.
3. **Inactivity Countdown**: On the MCU, `trigger_led_timer()` restarts `inactivity_timer` with a **4.5-second timeout** (`INACTIVITY_TIMEOUT_MS = 4500`).
4. **Heartbeat Lost Warning**: If 4.5 seconds elapse without communication:
   - `inactivity_timer_callback` turns the status LED ON solid for **3.0 seconds** (`HEARTBEAT_LOST_LED_MS = 3000`).
   - If the host resumes communication during these 3 seconds, `trigger_led_timer()` stops the countdown, turns off the warning LED, and restores normal operation.
5. **Entry into EM3 Deep Sleep**: If no heartbeat arrives after the 3-second warning (total **7.5 seconds** of inactivity):
   - `heartbeat_lost_timer_callback` turns off the LED.
   - It removes the EM1 power requirement (`sl_power_manager_remove_em_requirement(SL_POWER_MANAGER_EM1)`).
   - It enables the falling-edge GPIO external interrupt on `PA09`.
   - The Silicon Labs Power Manager transitions the device into **EM3 Deep Sleep** (~1 µA).

### 2. Interrupt Storm Prevention & Wake-on-RX
To guarantee high-throughput UART communication stability at 921,600 baud:
* **The PA09 GPIO Interrupt Storm Trap**: In early implementations, the GPIO falling-edge interrupt on PA09 remained active while communicating. At 921,600 baud, every start bit and zero bit generated hundreds of GPIO interrupts per packet, locking the sleeptimer queue and starving the 16-byte EUSART hardware FIFO.
* **Strict Interrupt Isolation**:
  - In EM0 and EM1, the GPIO external interrupt on PA09 is **strictly disabled** (`sl_gpio_disable_interrupts(1 << rx_wakeup_int_no)`).
  - The GPIO interrupt is enabled **exclusively** when transitioning into EM3.
  - When the PC transmits a wake-up byte (falling edge on RX), `rx_wakeup_callback` fires, **immediately disables the GPIO interrupt**, re-asserts `SL_POWER_MANAGER_EM1`, and returns `SL_POWER_MANAGER_WAKEUP`.
  - All subsequent data bytes are processed purely by the EUSART hardware and DMA without any GPIO interrupt interference.

### 3. PC-side Heartbeat Pause & Resume
During intensive benchmarks or high-throughput batch operations, the host software can prevent thread contention on the serial bus using:
- `transport.pause_heartbeat()`: Suspends automatic 3.0s `MSG_PING` transmissions.
- `transport.resume_heartbeat()`: Restores automatic heartbeat transmissions.

---

## Use Case Scenarios (Edge Cases & Fail-Safes)

### Scenario A: Device Disconnected ➔ Application Starts ➔ Device Plugged In
* **Initial State:** Device is in EM3 Deep Sleep powered by battery. PC application waits for COM port discovery.
* **Flow:** Device is plugged into USB. PC application opens the COM port and initiates the cryptographic handshake.
* **Result:** The initial edge on RX immediately wakes the EFR32MG24 into EM0. The GPIO interrupt is disabled, the EM1 requirement is locked, the handshake completes, and periodic heartbeats keep the device active.

### Scenario B: Device Connected ➔ PC Application Starts
* **Initial State:** Device is plugged into USB but in EM3 Deep Sleep because the PC application was previously closed (>7.5s ago).
* **Flow:** User starts the application. Transport opens COM10 and sends the initial sync ping.
* **Result:** The falling edge wakes the EFR32MG24 into EM0. Normal communication resumes instantly.

### Scenario C: Normal Operation ➔ Application Terminates or Crashes
* **Initial State:** Device is in Active State (EM0/EM1), communicating normally.
* **Flow:** PC application is closed or crashes unexpectedly. Background heartbeat transmissions cease.
* **Result:** 
  1. At $t = 4.5\text{ s}$, the MCU detects missed heartbeat and lights the status LED.
  2. At $t = 7.5\text{ s}$, the warning expires; MCU enables PA09 GPIO interrupt, removes EM1 requirement, and enters EM3 Deep Sleep (~1 µA), fully conserving battery power.

### Scenario D: Normal Operation ➔ USB Cable Physically Disconnected
* **Initial State:** Device is in Active State (EM0/EM1).
* **Flow:** USB cable is unplugged. The on-board USB-UART bridge loses VBUS power.
* **Result:** Identical to Scenario C. After 4.5s warning + 3.0s countdown, the EFR32MG24 safely drops into EM3 Deep Sleep on battery power.

### Scenario E: Spurious Glitches or Foreign Serial Ports (False Wakeup)
* **Initial State:** Device is in EM3 Deep Sleep.
* **Flow:** Electrical noise on the cable or a third-party serial monitor (e.g. PuTTY) opens the port and sends a stray character.
* **Result:** The EFR32MG24 wakes to EM0/EM1 and disarms the GPIO interrupt. However, because the foreign program does not send valid `KeySec` cryptographic heartbeats, the MCU times out after 4.5s + 3.0s and securely returns to EM3 Deep Sleep.
