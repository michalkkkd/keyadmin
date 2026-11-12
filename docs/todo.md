# TODO

Open items to handle before a production release. Newest first.

## KeyFirmware: battery history is also written to NVM3 on USB (2026-11-10)

**Where:** `KeyFirmware/src/core/power_diag.c`, `log_sample()` -> `hist_append_and_save()`, Secure gate `nsc_pwr_hist_save()` (`src/secure/nsc_interface.c`).

**What happens:** the battery history (`PWR HIST` / `PWR H` lines) is meant to be saved only on battery. The firmware decides "on battery" from the PA09 probe: `rx == 0` means nothing drives the UART RX line, so the SAMD11 USB bridge should be unpowered. On hardware, however, the SAMD11 does not drive its TX line while the COM port is closed (checked over SWD on 2026-11-10: with a pull-down, PA09 reads 0 on USB). So on USB with Compass closed the firmware cannot tell USB from battery, and it writes one history entry to NVM3 every 10 minutes.

**Impact:** about 52 000 writes of 252 bytes per year on a dongle that stays plugged in with Compass closed. Acceptable for diagnostics (NVM3 wear stays low, and the Secure gate refuses saves closer than 5 minutes apart), but not something to ship.

**To do before production:** limit it, for example:
- save only while the dongle is asleep and no host byte has been seen since boot or for a long time; or
- save less often (every 30-60 minutes) and only when the battery voltage changed; or
- drop the NVM3 history from the production build (it is a battery-drain diagnostic).
