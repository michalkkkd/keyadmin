# Dongle Diagnostics (`Compass.exe --diag`, DIAG stream)

A customer calls with "the dongle does not work". **The customer runs the diagnostics themselves**: they close Compass (it holds the COM port) and run `Compass.exe --diag` from a console in the Compass folder. They need nothing else: no KeySec, no key files, no Python. The program prints one encrypted payload and saves the same text next to the exe as `key_diag_YYYYMMDD_HHMMSS.txt`:

```
KEY DIAG 4 | 2026-11-03 19:34:17
Send the text below (or the report file) to support:
-----BEGIN KEY DIAG-----
ATpqGoYt8cnk+/M3sk+WmJUQBXlxRHNBhcrlZXtuEwMMTbZpUdc7rHvPG+71rH27
...
-----END KEY DIAG-----
REPORT: C:\Compass\key_diag_20261103_193417.txt
```

If the PC cannot talk to the dongle at all, there is nothing the dongle could encrypt. The program then prints one plain sentence and no payload. Those sentences say only what the customer can see anyway:
* **The key was not found:** plug it in.
* **The key cannot be opened:** close Compass or any other program using it.
* **The key does not answer:** unplug it and plug it in again.

Support deciphers the payload in KeySec admin, which needs no dongle:
* keyadmin menu: **Decipher Diagnostic Payload (paste what the customer sent)**. Paste the text from `BEGIN` to `END`; mail quoting (`> `) and line breaks are tolerated.
* or `python keyadmin/scripts/decode_diag_payload.py key_diag_20261103_193417.txt` (or without an argument, to paste the text).

**Dongle Diagnostics** in the keyadmin menu runs the same stream over the console's connection and shows the result right away. `python keyadmin/scripts/run_customer_diag.py [--out-dir temp]` runs the customer tool without Compass (factory Host Key).

## The dongle encrypts everything

1. The PC (`keycomm/diag`) finds the port, connects and tries the Host Key handshake like Compass does. It then collects its own facts (below) and compresses them (zlib JSON).
2. It sends them to the dongle: `MSG_DIAG_BEGIN` (PC time, length), then `MSG_DIAG_DATA` chunks of up to 640 bytes. The Secure world (`sec_diag.c`) encrypts them as they arrive, in one **AES-128-GCM stream** with the **Tamper Log Key** and a fresh IV from the SE TRNG.
3. `MSG_DIAG_NEXT` makes the dongle append its own data to the same stream: the record, the whole tamper log page and its RAM log. These are fixed sizes (256 + 1024 + 4096 bytes), so the length of the payload says nothing either. The last reply ends with the GCM tag, which authenticates everything (PC part included).
4. The PC only moves bytes. It has no key, encrypts nothing, judges nothing and cannot read the result. The Tamper Log Key is only in the dongle's Secure image and in `keyadmin/keys/tamper_log_key.bin`.

The DIAG commands need no session: every byte they return is ciphertext. Diagnostics therefore also work when the handshake fails (wiped or unprovisioned dongle, wrong Host Key), which is exactly when they are needed. The record then shows that no session was open.

Stream layout (`src/core/diag_record.h`): header = version (1) | IV (12), then the ciphertext, then the tag (16). The AAD is the version byte. Plaintext sections are type (1) | length (`uint32` LE) | data:
* `0x01`: PC facts;
* `0x10`: dongle record;
* `0x11`: tamper log page, its entries still ECB-encrypted as stored;
* `0x12`: RAM log, zero-padded.

Decoder: `keyadmin/secure_debug/diag_stream_decoder.py`.

## What the payload contains

| Section | Content |
| :--- | :--- |
| PC facts | keycomm and tool version, local and UTC time, Windows and Python version, time zone, program path (user profile masked as `%USERPROFILE%`), exe size, time and SHA-256 prefix (identifies the Compass build), COM ports (VID/PID, USB serial, USB location showing hubs, HWID), programs that may hold the port, Windows drivers of the dongle's USB interfaces, `root_ca_pub.pem` found, handshake result text, retransmissions / timeouts of the run |
| PC facts / `app` | Compass: compiled or not, USE_DEVICE, keys folder found; size and time of `log.json` and its last 300 dongle-related lines (per-model timing stats left out); the end of the newest `run-*.log`; the end of `FATAL_CRASH_REPORT.txt` if present (`compass/app/level_x/key_diag.py`) |
| Dongle record | see [record](#dongle-record-v5) |
| Tamper log | the persistent User Data page (64 entries) |
| RAM log | the dongle's last ~4 KB of events (heartbeat, sleep, wake-up) |

**Privacy:**
* E-mail addresses in the Compass logs are replaced by `<user1>`, `<user2>` and so on, consistently within one report.
* The computer name and the Windows user name are not collected.

## What ships to the customer

`keycomm/diag` holds only three modules:
* `diag_tool.py`: `run_diagnostics()`, `pc_facts()`, `seal_on_dongle()`, armor and report file;
* `diag_stream.py`: moves the PC facts to the dongle and the ciphertext back;
* `pc_info_collector.py`: the PC facts.

There is no key, cipher, check code, threshold or meaning in it. Everything that reads or judges is in keyadmin:
* `secure_debug/diag_stream_decoder.py`, `sealed_record_decoder.py`, `diag_host_evaluator.py`, `diag_evaluator.py`, `diag_support_report.py`;
* the meanings in `keyadmin/core/constants.py`.

Production firmware answers no plaintext diagnostics. `MSG_BATTERY_INFO`, `MSG_SYS_HEALTH`, `MSG_DEBUG_TIME`, `MSG_MEM_INFO` and `MSG_NVM_DIAG` exist only in the factory provisioning firmware (`src/admin/admin_diag_router.c`). PC5/PC6 tamper events send no `SECURITY ALERT` log over USB in production (`tamper_simulation.c`). The event is still written to the encrypted tamper log, and the LED still lights for 1 s.

## Check codes (internal, shown only after deciphering)

A payload exists, so the PC found the dongle, opened the port and the dongle answered. These checks are judged from the PC facts:

| Code | Checks | Results |
| :--- | :--- | :--- |
| `KY_1` | `root_ca_pub.pem` found | `FAIL_1` missing in `keys/` next to the program |
| `HS_1` | Secure handshake (record: session open) | `FAIL_1` rejected (not provisioned / wiped, wrong certificate or Host Key), `FAIL_2` handshake crashed (see the PC handshake text) |
| `LK_1` | USB link during the run | `WARN_1` retransmissions or timeouts (hub, extension cable) |

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
| `LK_2` | Corrupted USB frames since boot | `WARN_1` frames dropped for a bad TinyFrame checksum. Fast chunk bursts (large Safe Space transfers, retried by the host) can cause a few; wake-ups from EM3 do not |
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
* Non-Secure code has no NSC entry to change them. They leave the dongle only inside the encrypted DIAG stream.
* A wipe (provisioning, admin wipe, tamper wipe) clears NVM3 and starts them from zero.

## Lifetime and session counters

* **Boots and reset causes since provisioning:** POR, pin, software (also flashing / debugger), watchdog, brown-out, lockup, SE tamper. They are counted once per boot by `sec_diag_init()` in Secure NVM3 (key `0x40031`), one NVM3 write per boot.
* **Since boot, in RAM:** handshakes rejected and requests that did not decrypt (counted in the NSC gates); TinyFrame frames with a bad checksum (`tf_rx_cksum_errors` in the Non-Secure `TinyFrame.c`); minimum battery voltage and min / max temperature (60 s samples).
* **Last 4 failed secure commands**, newest first: dongle time, command, the first 11 characters of the error with the `ERR: ` prefix removed. They are recorded by the Non-Secure router (`diag_stats.c`) for every secure route that answers with an error, including chunk errors.

## Dongle record v5

`src/core/diag_record.h`, `_Static_assert` size 256, little-endian, packed; the field list is mirrored in `RECORD_FIELDS` in `sealed_record_decoder.py`:
* `magic 0xD1A6`, version 5, flags (provisioning build, tamper live wipe, certificate present);
* firmware version, PC time, dongle time, license start / days, clock at boot, last NVM3 checkpoint, uptime, raw reset cause, NVM3 free / total / erase count;
* chip EUI64, identity key and certificate fingerprints (SHA-256, first 8 bytes);
* license days left / status, active users, user limit, tamper events since boot, tamper log entries, battery %, debug lock flags, session flags (session open during DIAG), 10 tamper type counters;
* battery now / average / minimum / trend, temperature now / minimum / maximum;
* 7 algorithm run counters, lifetime boots and 7 reset-cause counters, handshakes rejected, decrypt failures, bad-checksum frames;
* 4 error entries (16 B: time, command, 11 characters), 24 reserved bytes, CRC-32 (zlib).

## Wire format

| Command | Request | Reply (hex) |
| :--- | :--- | :--- |
| `MSG_DIAG_BEGIN` (0x13) | PC time (`uint32` LE), PC data length (`uint32` LE, max 64 KB) | stream header (version, IV) |
| `MSG_DIAG_DATA` (0x14) | next PC data chunk, 1..640 bytes, in order | ciphertext released so far (may be empty) |
| `MSG_DIAG_NEXT` (0x17) | none | `00` + ciphertext, or `01` + last ciphertext + GCM tag |

Any error answers `ERR: DIAG stream failed (start again)` and aborts the stream. The host sends each command once, with no retry, because a resent chunk would be encrypted twice. It restarts the whole stream instead, up to 3 times.

## Files

* Firmware:
  * `src/core/diag_router.c` (NS: the three commands, snapshot of the record inputs and RAM log at begin);
  * `src/core/diag_stats.c` (NS: error ring, min / max);
  * `src/secure/sec_diag.c` (reset cause and lifetime counters, record, GCM stream);
  * `src/core/usage_counters.c` (Secure, run counters);
  * `src/core/diag_record.h`, `src/core/fw_version.h` (1.5.0);
  * `src/admin/admin_diag_router.c` (plaintext reports, factory build only).
* keycomm (ships with Compass): `keycomm/diag/` (`diag_tool.py`, `diag_stream.py`, `pc_info_collector.py`).
* keyadmin:
  * `scripts/decode_diag_payload.py`, `scripts/run_customer_diag.py`;
  * `secure_debug/diag_stream_decoder.py`, `sealed_record_decoder.py`, `diag_host_evaluator.py`, `diag_evaluator.py`, `diag_support_report.py`;
  * menu actions **Dongle Diagnostics** and **Decipher Diagnostic Payload**.
* Compass:
  * `run_compass.py --diag`;
  * `app/level_x/key_diag.py` (Compass part of the PC facts);
  * `SafeFileManager.read_text_tail()`, which reads the end of the large `log.json`.
