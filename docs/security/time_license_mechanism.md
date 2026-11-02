# Time-Based License Mechanism

## 1. Overview
The time-based licensing system ensures that the application and its critical functions can only be executed if a valid license is present on the USB dongle and has not expired.

## 2. Components
* **Hardware Clock (RTC):** The EFR32MG24 lacks a battery-backed RTC. To simulate continuous time, the dongle saves an initial `boot_time` (Unix timestamp) in the secure NVM3 storage. The current time is calculated by adding the processor's uptime (ticks) to this `boot_time`.
* **Admin API:** `AdminApi.update_current_date()` and `AdminApi.set_license_days()` (`MSG_ADMIN_DATE`, `MSG_ADMIN_LIC`) set the current time and the license duration (in days). They exist only in the factory firmware (`keyfirmware_prov.hex`); the production firmware does not contain them.
* **Compass API:** The Python application calls check_license on startup or before critical calculations. The dongle responds with the validity status.

## 3. Security Measures (Anti-Tampering)
* **Time Rollback Protection:** The firmware actively prevents time rollback attacks. If the host PC attempts to push a time synchronization that is older than the dongle's currently calculated time, the firmware rejects it and logs an attack attempt.
* **Storage Security:** The lic_start_time and lic_days are stored in NVM3, in the Secure world (ARM TrustZone), unencrypted; the Secure Debug Lock is what prevents reading or writing them over SWD.
* **Fail-Secure State:** If the dongle loses power, its internal clock halts. Upon reconnection, the time must be explicitly synchronized by the host (forward-sync). If synchronization is missing, all algorithm requests are denied.
