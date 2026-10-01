# Hardware and Environment (Important Information)

* **Main Microcontroller:** EFR32MG24B220F1536IM48 (Silicon Labs) - the pp.c logic runs on this. It features Secure Vault supporting anti-tampering, cryptography, and secure key storage.
* **Development Board:** Seeed Studio XIAO MG24.
* **Bridge / Debugger:** On the bottom of the board, there is a hidden **SAMD11** coprocessor. It serves as a hardware debugger (CMSIS-DAP) and a USB-UART bridge. This means Windows talks to SAMD11, and SAMD11 forwards the information to EFR32.
* **CRITICAL RULE:** **Never hold down the RESET button on the board while connecting it to the USB cable.** This will cause the SAMD11 to enter bootloader mode, completely disabling the CMSIS-DAP debugger interface and making it impossible to flash the board. Plug in the USB cable normally without pressing anything.

## Activated Modules and Components (in Simplicity Studio)

During project configuration (t_soc_empty.slcp), we included the following components into the EFR32 core:

* **IO Stream: USART** (instance: com): 
  * Pin mapping: PA08 (TX) and PA09 (RX).
  * Baud rate: 115200.
  * Purpose: Physical routing of communication from the EFR32 processor to the SAMD11 bridge.
* **Retarget STDIO**: 
  * Purpose: Historically for handling printf(). It allows routing standard input/output streams (C) to the selected interface (in our case, com).
* **Power Manager**: 
  * Purpose: Control of sleep states. We use the command sl_power_manager_add_em_requirement(SL_POWER_MANAGER_EM1); to block the processor from entering Deep Sleep (EM2), which would prevent proper, lossless UART communication.
* **cJSON** (External Library):
  * We included a hardware library from GitHub for professional and secure parsing of JSON objects, bypassing primitive and leaky text scanning methods.


## PRODUCTION NOTE: RTC Battery
While the current development board (Seeed Studio XIAO MG24) does not have a physical RTC battery, the **final production hardware WILL have a dedicated RTC battery**. The software architecture should accommodate this future capability.