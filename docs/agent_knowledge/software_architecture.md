# Software Architecture

## A. KeySec (Python on PC)
**Main file:** compass_rpc.py (and newer 	ransport.py)
A control application from Windows sending commands. It maintains a serial connection. We resolved buffer desynchronization issues in it using eset_input_buffer() and intentionally disabled reliance on the hardware DTR reset, ensuring a stable, smooth connection (reading in chunks via ead_all).

## B. KeyFirmware (C on silicon)
**Main file:** pp.c in the IDE (Simplicity Studio).
Firmware that constantly listens to the VCOM port (without blocking the core) using the native SDK (sl_iostream_getchar). It parses full lines and invokes RPC procedures. It sends the response back using the lightning-fast sl_iostream_write(), adding a microsecond blocking delay (sl_sleeptimer_delay_millisecond) to give data physical time to leave the port before the next Bluetooth stack tick.

### COMPILATION INSTRUCTIONS FOR THE AGENT
1. To compile: cd cmake_gcc && cmake --build --preset default_config
2. To flash: .\xiao_mg24_flash.bat (or Python script) located in cmake_gcc\build\base.

## TrustZone Strategy and Target Architecture (Phase 3+)
Ultimately, the code will be split into two physical projects enforced by the Cortex-M33 processor (ARM TrustZone):
1. **Non-Secure World (Project B):** Handles open code, USB and UART operations, the event loop (pp.c, pc_router.c, dmin_cli.c), and raw NVM3 disk (security_nvm.c).
2. **Secure World (Project A):** A fortified environment. This will house the logic verifying license validity (security_rtc.c) and the main, secret logic of the algorithms (compass_core.cpp). This code uses NSC (Non-Secure Callables) gateways to allow the Non-Secure side to query the secure zone.
