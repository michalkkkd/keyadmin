# Dongle Diagnostics (`Compass.exe --diag`, DIAG command)

A customer calls with "the dongle does not work". **The customer runs the diagnostics themselves**: they close Compass (it holds the COM port) and run `Compass.exe --diag` from a console in the Compass folder. They need nothing else: no KeySec, no key files, no Python. The Host Key is built into Compass. The program prints one encrypted payload and saves the same text next to the exe as `key_diag_YYYYMMDD_HHMMSS.txt`:

```
KEY DIAG 1 | 2026-11-03 17:47:30
Collecting diagnostics ....... done
Send the text below (or the report file) to support:
-----BEGIN KEY DIAG-----
AQRQZlxnl7YL3XX1RAJIfmUoa4Fv9xPc3EHOc9wtM6WbZ2fp3rAgepzJVoBuhjOt
...
-----END KEY DIAG-----
REPORT: C:\Compass\key_diag_20261103_174730.txt
```

**100 % of the diagnostic information is encrypted.** The customer (or anyone holding Compass) sees no codes, values or results. Support deciphers it in KeySec admin, which needs no dongle:

* keyadmin menu: **Decipher Diagnostic Payload (paste what the customer sent)**. Paste the text from `BEGIN` to `END`; mail quoting (`> `) and line breaks are tolerated.
* or `python keyadmin/scripts/decode_diag_payload.py key_diag_20261103_174730.txt` (or without an argument, to paste the text).

The deciphered view shows:
* the PC: OS, COM ports with VID/PID, USB link stats;
* every check with its internal meaning;
* the raw error texts of failed steps;
* the dongle record: firmware, clock, license, reset cause, users, NVM3, tamper counters, battery, temperature, algorithm run counters.

**Dongle Diagnostics** in the keyadmin menu shows the same view live for the connected dongle.

Developers can run the customer tool without Compass: `python -m keycomm.diag --host-key keyadmin/keys/host_key.pem [--out-dir temp]`.

## Two layers of encryption

1. **The dongle seals its values** (`MSG_DIAG`, 0x13). The reply is nothing but `IV + AES-128-CBC(record)`, encrypted in the Secure world with the **Tamper Log Key**. That key is only in the Secure image and in `keyadmin/keys/tamper_log_key.bin`. On top of that, `MSG_DIAG` is a secure route: it needs a session opened with the Host Key, and the reply also travels inside the AES-256-GCM session. There is no license check, so it still works on an expired dongle. It reads only: it never registers a user, changes the clock or counts as a tamper event.
2. **The PC encrypts the whole report** to the **Diag Report Key** (ECIES):
   * an ephemeral P-256 ECDH, HKDF-SHA256 (`info` = label + ephemeral point) and AES-256-GCM over `zlib(JSON)`;
   * the version byte and the point are the AAD;
   * only the public half is in keycomm (`keycomm/diag/diag_report_pubkey.py`, generated). The private half is `keyadmin/keys/diag_report_key.pem` (`keyadmin/scripts/generate_diag_report_key.py`). The PC that made the payload cannot read it back.

## What the payload contains

All of it is inside the encrypted envelope (JSON, zlib). A full payload is about 170 lines of base64, roughly 10 KB.

| Key | Content | Source |
| :--- | :--- | :--- |
| `tool`, `time`, `utc` | Tool version, local and UTC time of the run | keycomm |
| `pc` | keycomm version, Windows version, Python version, time zone and UTC offset, program path (user profile masked as `%USERPROFILE%`), exe size, modification time and SHA-256 prefix (identifies the exact Compass build) | `pc_info_collector.py` |
| `ports` | Every COM port: VID/PID, description, manufacturer, USB serial, USB location (shows hubs), HWID | pyserial |
| `processes` | Running programs that may hold the port (Compass, Python, terminals, flashing tools) and how many of each | `tasklist` |
| `usb` | Windows driver of every USB interface of the dongle (name, provider, version, date, INF) | WMI |
| `checks`, `errors`, `link` | Host check results, raw error text of each failed step, 10 PINGs / lost / retransmissions | `DiagnosticsRunner` |
| `sealed` | Dongle record (below), sealed by the dongle | `MSG_DIAG` |
| `tlog` | The whole persistent tamper log page (1 KB), sealed by the dongle | `MSG_DIAG_TLOG` |
| `ramlog` | Dongle RAM log (last ~4 KB of events: heartbeat, sleep, wake-up) | `MSG_GET_LOG_*` |
| `app` | Compass: compiled or not, USE_DEVICE, keys folder found; size and time of `log.json`, the last 300 dongle-related lines of it (XRouter / keycomm / license / VRX / gate / heartbeat; per-model timing stats left out); the end of the newest `run-*.log`; the end of `FATAL_CRASH_REPORT.txt` if present | `app/level_x/key_diag.py` |

**Privacy:**
* E-mail addresses in the Compass logs are replaced by `<user1>`, `<user2>` and so on, consistently within one report, so support can follow one user without knowing who it is.
* The computer name and the Windows user name are not collected.

The tamper log page is sealed as a whole, with a fresh IV, for one reason: on its own, the number of non-blank (still ECB-encrypted) slots would reveal how many tamper events were logged.

## Threat model

Even with Compass fully reverse-engineered (Host Key extracted), an attacker gets nothing that helps:
* **Nothing readable in Compass.** The check meanings, the thresholds and the evaluation of the dongle values live only in KeySec admin (`keyadmin/core/constants.py`, `keyadmin/secure_debug/diag_evaluator.py`).
* **The dongle answers `MSG_DIAG` with the sealed record only.** An attacker who calls it directly gets ciphertext. They cannot use it as feedback, for example by watching tamper counters or the reset cause after a glitch attempt.
* **The production firmware answers no plaintext diagnostics.** `MSG_BATTERY_INFO`, `MSG_SYS_HEALTH`, `MSG_DEBUG_TIME`, `MSG_MEM_INFO` and `MSG_NVM_DIAG` exist only in the factory provisioning firmware (`src/admin/admin_diag_router.c`).
* **PC5/PC6 tamper events send no `SECURITY ALERT` log over USB in production** (`tamper_simulation.c`, factory build only). The event is still written to the encrypted tamper log. The LED still lights for 1 s.

What the sealed record would tell an attacker, and why each part stays encrypted:
* **Tamper counters per type and the log size** are a detection oracle: they show whether an attempt was seen and by which detector.
* **The live-wipe flag** tells whether crossing a threshold destroys the device.
* **The clock internals** reveal the 60 s checkpoint and the 150 s reset penalty.
* **The reset cause** is feedback for glitch tuning.

## Check codes (internal, shown only after deciphering)

Checks made on the PC. When a step fails, the later ones are `SKIP`. `LK_1` runs whenever a session exists.

| Code | Checks | Results |
| :--- | :--- | :--- |
| `CO_1` | Dongle visible on USB (VID/PID) | `FAIL_1` not found: not plugged in, charge-only cable, no driver |
| `CO_2` | COM port can be opened | `FAIL_1` port busy (Compass still running), `FAIL_2` other open error |
| `PI_1` | Dongle answers PING | `FAIL_1` no PONG (firmware not running / wiped), `FAIL_2` port lost |
| `KY_1` | `root_ca_pub.pem` found | `FAIL_1` missing in `keys/` next to the program |
| `HS_1` | Secure handshake | `FAIL_1` rejected (not provisioned / wiped, wrong certificate or Host Key), `FAIL_2` malformed reply |
| `FW_1` | Firmware returns the sealed record | `FAIL_1` firmware without DIAG, `FAIL_2` DIAG error, `FAIL_3` reply of another size (firmware other than 1.4.0) |
| `LK_1` | USB link: 10 PINGs + retransmissions | `WARN_1` retransmissions needed (hub, extension cable), `FAIL_1` PINGs lost |

Checks judged by keyadmin from the decrypted dongle record (and `AP_1` from the Compass part):

| Code | Checks | Results |
| :--- | :--- | :--- |
| `LI_1` | License status | `FAIL_1` expired, `FAIL_2` no license, `FAIL_3` no clock (RTC never set or wiped) |
| `LI_2` | License days left | `WARN_1` 30 days or less (`SKIP` if `LI_1` failed) |
| `CL_1` | Dongle clock minus PC clock | `WARN_1` more than 1 hour, `WARN_2` more than 1 day |
| `UL_1` | Active users limit | `FAIL_1` limit is 0, `WARN_1` limit full right now (users active in the last 10 min) |
| `BA_1` | Battery (filtered charge level) | `WARN_1` below 20 %, `FAIL_1` below 10 %, `FAIL_2` ADC read failed |
| `TE_1` | MCU temperature | `WARN_1` outside 0..50 C, `FAIL_1` outside -10..70 C |
| `NV_1` | NVM3 free space | `WARN_1` less than 10 % free, `FAIL_1` stats unavailable |
| `RS_1` | Cause of the last reset | `FAIL_1` Secure Engine tamper reset, `WARN_1` brown-out, `WARN_2` watchdog, `WARN_3` CPU lockup |
| `TA_1` | Tamper events | `WARN_1` events since boot, `WARN_2` entries in the persistent tamper log |
| `RS_2` | Abnormal resets since provisioning | `FAIL_1` SE tamper, `WARN_1` brown-out, `WARN_2` watchdog, `WARN_3` lockup |
| `SE_1` | Secure session problems since boot | `WARN_1` handshakes rejected, `WARN_2` requests that did not decrypt |
| `LK_2` | Corrupted USB frames since boot | `WARN_1` frames dropped for a bad TinyFrame checksum |
| `ID_1` | Identity and certificate | `FAIL_1` no certificate, `FAIL_2` no identity key (not provisioned / wiped) |
| `DB_1` | Debug port (SWD) lock | `WARN_1` lock not applied, `WARN_2` lock applied but unlocked until the next reset |
| `ER_1` | Failed dongle commands | `WARN_1` at least one of the last 4 secure commands failed (listed with time and error) |
| `BA_2` | Lowest battery voltage since boot | `WARN_1` below ~5 % (3610 mV) |
| `TE_2` | Temperature range since boot | `WARN_1` left 0..50 C |
| `AP_1` | Compass crash report | `WARN_1` `FATAL_CRASH_REPORT.txt` exists |

## Reset cause

The Secure world captures `EMU->RSTCAUSE` once at boot (`sec_diag_init()`, after `tamper_manager_init()` has checked `SETAMPER`) and then clears it with `EMU_CMD_RSTCAUSECLR`. Before firmware 1.1.0 nothing cleared it and the bits added up since power-on. The first boot after updating from such firmware can therefore show old causes.

## Algorithm run counters

The Secure world counts how many times each algorithm of `src/prod/logic` ran (`src/core/usage_counters.c`). A run is counted once its license, user and VRX checks have passed and its input data is complete. A resent Sim PK PROCESS answered from the cached result is not counted again. Runs that then fail on a data limit (OOM, too many subjects) are counted.

| # | Counter | Firmware function |
| :--- | :--- | :--- |
| 0 | Test Add | `cmd_test_add` |
| 1 | Compass Sim PK | `cmd_compass_sim_pk` |
| 2 | Sim PK & GI table | `cmd_sim_pk_gi_process` |
| 3 | Safe Space Estimates | `cmd_safe_space_finish` |
| 4 | Safe Space Plots A | `cmd_ssp_a_process` |
| 5 | Safe Space Plots B | `cmd_ssp_b_req` |
| 6 | Safe Space Plots C | `cmd_ssp_c_process` (once per formulation and medium) |

* The counters are kept in RAM and written to Secure NVM3 (key `0x40030`) at most once per 60 s, from the same housekeeping call as the license clock. This bounds flash wear whatever the usage; a reset loses at most the runs of the last 60 s.
* Non-Secure code has no NSC entry to change them. They leave the dongle only inside the sealed record.
* A wipe (provisioning, admin wipe, tamper wipe) clears NVM3 and starts them from zero.

## Lifetime and session counters

* **Boots and reset causes since provisioning:** POR, pin, software (also flashing / debugger), watchdog, brown-out, lockup, SE tamper. They are counted once per boot by `sec_diag_init()` in Secure NVM3 (key `0x40031`), one NVM3 write per boot.
* **Since boot, in RAM:** handshakes rejected and requests that did not decrypt (counted in the NSC gates); TinyFrame frames with a bad checksum (`tf_rx_cksum_errors` in the Non-Secure `TinyFrame.c`); minimum battery voltage and min / max temperature (60 s samples).
* **Last 4 failed secure commands**, newest first: dongle time, command, the first 11 characters of the error with the `ERR: ` prefix removed. They are recorded by the Non-Secure router (`diag_stats.c`) for every secure route that answers with an error, including chunk errors.

## `MSG_DIAG` wire format

Request: PC UNIX time, `uint32` little-endian (4 bytes). Reply: hex of `IV (16 B) + AES-128-CBC(record, 256 B)`, nothing else.

`MSG_DIAG_TLOG` (0x14, secure route): request = byte offset (`uint16` LE) into the sealed tamper log (`IV + AES-128-CBC(1 KB page)`, 1040 B). The reply is up to 700 bytes as hex, and is empty past the end. Offset 0 seals a fresh copy with a new IV.

Sealed record v4 (`src/core/diag_record.h`, `_Static_assert` size 256, little-endian, packed; the field list is mirrored in `RECORD_FIELDS` in the decoder):
* `magic 0xD1A6`, version 4, flags (provisioning build, tamper live wipe, certificate present);
* firmware version, PC time, dongle time, license start / days, clock at boot, last NVM3 checkpoint, uptime, raw reset cause, NVM3 free / total / erase count;
* chip EUI64, identity key and certificate fingerprints (SHA-256, first 8 bytes);
* license days left / status, active users, user limit, tamper events since boot, tamper log entries, battery %, debug lock flags, 10 tamper type counters;
* battery now / average / minimum / trend, temperature now / minimum / maximum;
* 7 algorithm run counters, lifetime boots and 7 reset-cause counters, handshakes rejected, decrypt failures, bad-checksum frames;
* 4 error entries (16 B: time, command, 11 characters), 24 reserved bytes, CRC-32 (zlib).

Decoder: `keyadmin/secure_debug/sealed_record_decoder.py`.

## Files

* Firmware: `src/core/diag_router.c` (NS, `cmd_diag`, `cmd_diag_tlog`), `src/core/diag_stats.c` (NS: error ring, min / max), `src/secure/sec_diag.c` (reset cause and lifetime counters, record, sealing of record and tamper log), `src/core/usage_counters.c` (Secure, run counters), `src/core/diag_record.h`, `src/core/fw_version.h`, `src/admin/admin_diag_router.c` (plaintext reports, factory build only). Routes `MSG_DIAG` / `MSG_DIAG_TLOG` in `prod_router.c` and `admin_router.c`.
* keycomm (ships with Compass): `keycomm/diag/` (`run_diagnostics`, `DiagnosticsRunner`, `PcInfoCollector`, `DiagReport`, `DiagEnvelope`, `diag_report_pubkey.py`), `CompassApi.get_diagnostics()`.
* keyadmin: `scripts/decode_diag_payload.py`, `scripts/generate_diag_report_key.py`, `secure_debug/diag_payload_decoder.py`, `sealed_record_decoder.py`, `diag_evaluator.py`, `diag_support_report.py`, menu actions **Dongle Diagnostics** and **Decipher Diagnostic Payload**.
* Compass: `run_compass.py --diag` and `app/level_x/key_diag.py` (app part of the payload); `SafeFileManager.read_text_tail()` reads the end of the large `log.json`.
