# Time-Based License Mechanism

## 1. Overview
The time-based licensing system ensures that the application and its critical functions can only be executed if a valid license is present on the USB dongle and has not expired.

## 2. Components
* **Hardware Clock (RTC):** The EFR32MG24 lacks a battery-backed RTC. To simulate continuous time, the dongle saves an initial oot_time (Unix timestamp) in the secure NVM3 storage. The current time is calculated by adding the processor's uptime (ticks) to this oot_time.
* **Admin API:** The dmin_set_date and dmin_set_license commands allow the administrator to synchronize the current time and define the license duration (in days) using a secure PIN.
* **Compass API:** The Python application calls check_license on startup or before critical calculations. The dongle responds with the validity status.

## 3. Security Measures (Anti-Tampering)
* **Time Rollback Protection:** The firmware actively prevents time rollback attacks. If the host PC attempts to push a time synchronization that is older than the dongle's currently calculated time, the firmware rejects it and logs an attack attempt.
* **Storage Security:** The lic_start_time and lic_days are stored in NVM3, leveraging the ARM TrustZone and Secure Vault capabilities to prevent unauthorized reading or writing via physical flash dumping.
* **Fail-Secure State:** If the dongle loses power, its internal clock halts. Upon reconnection, the time must be explicitly synchronized by the host (forward-sync). If synchronization is missing, all algorithm requests are denied.
