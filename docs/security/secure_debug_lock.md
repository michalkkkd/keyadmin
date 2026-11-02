# Secure Debug Lock (SWD Lock with Challenge-Response Unlock)

> **Scope:** KeyFirmware (Seeed XIAO MG24 / EFR32MG24, Secure Engine "Secure Vault High") + KeySec `keyadmin` tooling.
> **Status:** Implemented. Applied **only on request** (`provision_dongle.py <days> <users> --lock`, CLI or admin menu).
> **Verified on hardware:** status, challenge, rejection of invalid tokens, protected-device refusal.
> **Not yet verified on hardware:** a real lock followed by a successful unlock (writes OTP; to be done on a spare board).

---

## 1. What changes when the lock is enabled

Without the lock, anyone with a 2-wire SWD probe (or the XIAO's on-board CMSIS-DAP) can halt the CPU, dump the whole flash and RAM, single-step the secure world and reflash arbitrary firmware.

Enabling Secure Debug Lock performs three Secure Engine (SE) operations, in this order:

| Step | SE operation | Persistence | Effect |
|---|---|---|---|
| 1 | `sl_se_init_otp_key(SL_SE_KEY_TYPE_IMMUTABLE_AUTH)` | **OTP, permanent** | Installs our **public Command Key**. From now on this chip trusts only unlock tokens signed by the matching private key. |
| 2 | `sl_se_enable_secure_debug()` | SE config (reset by device erase) | Allows a temporary, cryptographically authorized unlock. Must happen **before** step 3. |
| 3 | `sl_se_apply_debug_lock()` | SE config (reset by device erase) | Closes the debug access port on every boot. |

What is deliberately **not** done: `disabledeviceerase`. Device erase stays available as a last-resort recovery.

### What it protects against
* **Firmware / IP extraction over SWD:** the proprietary Compass algorithms in the secure world, the license logic and the tamper log can no longer be read with a debugger.
* **Live debugging attacks:** halting the CPU, patching the license check in RAM, reading session keys from RAM, single-stepping TrustZone code.
* **Reflashing the dongle** with modified firmware while keeping its NVM3 state (license, identity key, certificate).

### What it does NOT change
* Normal operation: Compass, VCOM/USB RPC, encrypted sessions, license and user limits work exactly as before.
* The RAM logs over USB (`MSG_GET_LOG_*`) still work without any unlock.
* **Device erase** is still possible: it re-opens the port but wipes the **entire** main flash (firmware, NVM3 license, identity key, certificate). Only the User Data page with the encrypted tamper log survives. An attacker gains an empty chip, never our data.
* The identity key in NVM3 is PUF-wrapped (dongles provisioned with firmware from 2026-10-30 on); the lock adds protection for code, RAM and the license data, which wrapping does not cover.

### How the firmware implements it
* **Secure world** ([`KeyFirmware/src/secure/sec_debug_lock.c`](../../../KeyFirmware/src/secure/sec_debug_lock.c)): all SE calls; the public Command Key is **compiled in** from [`debug_command_pubkey.h`](../../../KeyFirmware/src/secure/debug_command_pubkey.h) and is never accepted from the host, so nobody can install their own key through the RPC.
* **NSC gates** (`nsc_debug_lock_*` in `nsc_interface.c`): pointer validation; the unlock token is copied into secure memory before use.
* **Non-secure router** ([`KeyFirmware/src/core/debug_lock_router.c`](../../../KeyFirmware/src/core/debug_lock_router.c)): plaintext RPC commands, present in **both** production and provisioning firmware:

| ID | Command | Payload | Response |
|---|---|---|---|
| `0x60` | STATUS | – | `SERIAL:<32 hex>;CMD_KEY:NONE/MATCH/MISMATCH;BUILTIN_KEY;SECURE_DEBUG;LOCK_APPLIED;LOCK_ACTIVE;DEVICE_ERASE` |
| `0x61` | LOCK | – | One-way and idempotent. Refused if the firmware has no built-in key or the OTP holds a different key. |
| `0x62` | CHALLENGE | – | `SERIAL:<32 hex>;CHALLENGE:<32 hex>` |
| `0x63` | UNLOCK | 220-byte token | Opens the debug port **until the next reset / power cycle**. |

Plaintext is intentional: the SE itself verifies the token (serial number + current challenge + Command Key signature), and UNLOCK must keep working on a dongle whose identity certificate or session layer is broken.

---

## 2. A dongle comes back from a customer: what can we do?

**Without unlocking (USB only):** read system health, tamper counters, battery, RTC, license, and the RAM log buffer through the admin console.

**After `secure_debug_lock.py unlock`** (port open until the next reset):

| Action | How | Notes |
|---|---|---|
| Read the encrypted tamper event log (User Data page `0x0FE00000`, 1 KB) | Done and decoded automatically after `unlock`; manually: `python -m pyocd cmd ... -M attach -c "savemem 0x0FE00000 1024 <file>"`, decode with `keyadmin/scripts/read_tamper_log.py --file <file>` (the exact command is printed by the tool) | Use **attach** mode: a reset re-locks the port. |
| Dump any flash / RAM region, inspect the secure world | pyOCD / GDB in attach mode | Full access: non-secure + secure, invasive + non-invasive. |
| Debug a fault live | GDB attach | Port stays open until reset. |
| Reflash firmware (update / fix) | `unlock`, then `flash.bat` or `set_production_mode.bat` | The reset at the end of flashing re-locks the port, so a separate re-lock is not needed. The OTP key and the lock stay. |
| Re-provision (new license, new customer) | `unlock` → `set_factory_mode.bat` → provisioning over USB → `unlock` again (provisioning firmware also has `0x63`) → `set_production_mode.bat` | NVM3 is preserved by flashing; use `MSG_ADMIN_WIPE` in factory mode for a clean slate. |

**Limitations:**
* The VCOM unlock needs **running firmware**. After a tamper live wipe no unlock is needed: the Secure Engine device erase also resets the debug lock, so the tamper log (User Data page, kept by the erase) can be read directly over SWD and decrypted with `tamper_log_key.bin` (see [antitamper.md](antitamper.md)). If the firmware is broken for another reason, the unlock must go through the debug interface instead: Simplicity Commander with a J-Link and the same key (`commander security unlock --command-key debug_command_key.pem`). This path has not been tested on the XIAO yet.
* The **OTP key can never be removed**. A unit locked with a given Command Key is tied to it for life.
* Last resort: a full **device erase** through the SE debug interface (e.g. `commander device recover`). It re-opens the port permanently but destroys everything except OTP. Whether the XIAO's on-board CMSIS-DAP can issue it via pyOCD is unverified; a J-Link on the SWD pads is the known-good path.

---

## 3. Keys and files

### 3.1 Where each key lives

| Key | Where | Purpose |
|---|---|---|
| **Root CA private key** | `keyadmin/keys/root_ca_key.pem` (host) | Signs each dongle's identity public key during provisioning (`provision_dongle.py`). |
| **Root CA public key** | `keyadmin/keys/root_ca_pub.pem`, `keycomm/keys/root_ca_pub.pem`, shipped with Compass | Compass checks that a dongle's identity certificate was signed by us (genuine dongle). |
| **Device identity key** | Inside each dongle (NVM3 of the Secure world, PUF-wrapped `SL_PSA_KEY_LOCATION_WRAPPED`; older dongles plain until re-provisioned; never sent out) | Signs the ECDHE handshake, which proves the dongle's identity and prevents MitM. |
| **Device certificate** | Inside each dongle (NVM3) | Root CA signature over the identity public key. |
| **Command Key, private** | `keyadmin/keys/debug_command_key.pem` (host) | **One per product/factory, not per device, and the only unlock secret.** keyadmin signs every unlock token with it, in memory. |
| **Command Key, public** | `keyadmin/keys/debug_command_pubkey.pem` + compiled into firmware (`debug_command_pubkey.h`) + OTP of each locked dongle | The trust anchor the SE uses to verify unlock tokens. |
| **Session keys** | RAM only (ECDHE + HKDF, AES-256-GCM) | Per-connection encryption; unrelated to the debug lock. |

The Root CA chain and the Command Key chain are **independent**. The Root CA proves "this dongle is genuine" to Compass. The Command Key proves "this host is the manufacturer" to the dongle's Secure Engine.

### 3.2 Unlock chain of trust

```
debug_command_key.pem (private, factory-wide)
        │ at every unlock, in memory: new throwaway certificate key, certificate signed by the Command Key
        ▼
access certificate      = magic | auth bits | SE serial[16] | cert_pubkey[64] | signature[64]   (156 B)
        │ throwaway certificate key signs
        ▼
challenge response      = DEBUG_ACCESS_CMD | unlock params | challenge[16]                     (24 B)

unlock token            = access certificate + challenge signature                             (220 B)
```

The SE format needs the two-step chain (certificate + challenge signature), but keyadmin builds both in memory from the Command Key at every unlock and saves neither: **the Command Key is the only unlock secret.**

The SE accepts the token only if:
1. the certificate was signed by the Command Key stored in **its** OTP;
2. the serial number in the certificate is **its own**, so a token cannot be reused on another dongle;
3. the challenge signature matches its **current** challenge. The challenge stays the same until rolled; we do not roll it, because tokens are made only in the factory and never stored.

### 3.3 `keyadmin/keys/` folder layout

```
keyadmin/keys/
├── root_ca_key.pem                 Root CA private key (identity chain)
├── root_ca_pub.pem                 Root CA public key
├── debug_command_key.pem           Command Key private (CURRENT KEY IS A DEVELOPMENT KEY)
├── debug_command_pubkey.pem        Command Key public (same bytes as debug_command_pubkey.h)
└── secure_debug/
    ├── protected_devices.json      Serials that keyadmin tools will NEVER lock (development boards)
    └── devices/
        └── device_<SE serial>/     One folder per dongle, named after the 16-byte Secure Engine serial
            ├── device.json         Last status + history of STATUS / LOCK / UNLOCK events (timestamp, port, response)
            └── userdata_dump.bin   User Data page dump (tamper log, written by pyOCD)
```

No unlock material (certificate, its key, token) is ever written here.

**Serial number:** each EFR32MG24 has a factory-unique 16-byte SE serial number (for example `0000000000000000880F62FFFE3E183B`; the last 8 bytes are the chip's EUI-64). It differs from the USB serial of the XIAO's on-board USB bridge, so do not use the COM port identity to name devices.


---

## 4. How enabling the lock works now

| Entry point | Locks? | Details |
|---|---|---|
| `compile.bat` | No | Builds both firmwares; embeds the public Command Key from `debug_command_pubkey.h`. |
| `flash.bat`, `set_factory_mode.bat`, `set_production_mode.bat` | No | Only flash via pyOCD. On a locked dongle they work only right after an `unlock`. |
| `python keyadmin/scripts/provision_dongle.py <days> <users>` | **No** | compile → factory firmware → secrets → production firmware → verify. The lock step is skipped. |
| `python keyadmin/scripts/provision_dongle.py <days> <users> --lock` | **Yes** | After verification: protected check → already-locked check → typed `LOCK` confirmation (`--yes` skips it) → `0x61` → readback. |
| Admin console, section *FACTORY* → *Provision Dongle* | Only if answered `y` | Same pipeline; asks for days, users, lock, and a typed `PROVISION` confirmation. |
| `python keyadmin/scripts/secure_debug_lock.py lock` | Yes | Same flow, standalone. |
| Admin console (`python keyadmin/main.py`), section *SECURE DEBUG LOCK (SWD)* | Yes | Status / Apply lock (asks to type `LOCK`) / Unlock until next reset. |

`secure_debug_lock.py lock` flow:
1. Connects and reads STATUS (serial, OTP key state, lock flags) and records it in `device.json`.
2. **Refuses** if the serial is in `protected_devices.json`; nothing is sent to the dongle.
3. Exits OK if the dongle is already secure-locked.
4. **Smoke test:** requires an established encrypted ECDHE session (genuine, provisioned dongle running production firmware) and a valid license check.
5. Shows the warning and asks the operator to type `LOCK` (skipped with `--yes`).
6. Sends `0x61`, re-reads STATUS and verifies `LOCK_APPLIED=1`, `SECURE_DEBUG=1`, `CMD_KEY=MATCH`; records the result.

Safety layers against accidental locking of development boards:
1. `protected_devices.json` (add the connected board with `secure_debug_lock.py protect`; remove a serial only by editing the file);
2. `--lock` must be passed explicitly to `provision_dongle.py` (or `y` answered in the menu) and confirmed by typing `LOCK`;
3. firmware built before a Command Key existed (`BUILTIN_KEY:0`) cannot lock at all.

Other CLI commands: `status`, `unlock` (builds the token in memory, records the event in `device.json`, dumps the tamper log and prints the pyOCD command), `protect`. Options: `--port COMx`, `--store DIR` (device data), `--keys DIR` (Command Key folder).

---

## 5. Regenerating (rotating) the Command Key

`generate_debug_command_key.py`:
* creates `debug_command_key.pem` + `debug_command_pubkey.pem` in `keyadmin/keys/` (or `--keys DIR`);
* **refuses to overwrite** an existing key;
* writes the public key into `KeyFirmware/src/secure/debug_command_pubkey.h` (with a SHA-256 fingerprint);
* `--header-only` regenerates the header from an existing key without creating a new one.

### Consequences of a new key
The OTP key of a dongle never changes, so after a rotation two populations exist:

| Dongle state | With new firmware (new key built in) | How to unlock it |
|---|---|---|
| Never locked (OTP empty) | LOCK installs the **new** key | New key |
| Locked with the **old** key | STATUS shows `CMD_KEY:MISMATCH`; LOCK is refused (it is already locked anyway) | Needs the **old** Command Key: `secure_debug_lock.py unlock --keys <old keys dir>` |

### Procedure for the move to real production
1. Generate the production key into a separate folder: `python keyadmin/scripts/generate_debug_command_key.py --keys <production keys dir>`. This also rewrites the firmware header.
2. Rebuild with `compile.bat` and confirm the fingerprint in `debug_command_pubkey.h`.
3. Lock production dongles. The lock itself does not read the private key (the firmware installs its built-in public key), but unlocks do. `provision_dongle.py ... --lock` therefore works unchanged. For unlocks, use `secure_debug_lock.py unlock --keys <production keys dir>`. The admin console always uses the default `keyadmin/keys`.
4. **Keep the development key**: dongles already locked with it depend on it forever.
5. Store the production private key **offline / outside git** with a backup. The current development key, and the Root CA private key, are tracked in git, which is acceptable for development only.

**Losing a Command Key** means every dongle locked with it can only be recovered by a full device erase (license and identity lost; the tamper log in the User Data page survives).

---

## 6. The three modes: never locked, locked, unlocked until reset

### 6.1 What SWD is, and why the XIAO makes it a shortcut

**SWD (Serial Wire Debug)** is ARM's two-wire debug interface (`SWDIO` data + `SWCLK` clock) built into every Cortex-M core, including the EFR32MG24's Cortex-M33. It is not a normal communication port. It is a direct door into the chip's internals:

* SWD talks to the **Debug Access Port (DAP)**. Behind it sits the **AHB-AP**, a bus master on the chip's internal memory bus, just like the CPU.
* Through the AHB-AP a debugger can **read and write any address**: the whole flash (firmware and NVM3 with license data), RAM (runtime state, session keys, intermediate results), and all peripheral registers.
* It can also **halt the CPU**, single-step instructions, set breakpoints, and change registers. The firmware cannot notice or prevent any of this. A halted CPU runs no anti-tamper code.
* It is how firmware is programmed in the first place: `flash.bat`, `set_factory_mode.bat` and `set_production_mode.bat` all write flash over SWD (via pyOCD).

On a normal board, using SWD needs physical effort: open the case, find the debug pads, solder or clip wires, and own a debug probe (J-Link, ST-Link, ...). **The Seeed XIAO MG24 removes all of that.** It has a small USB bridge MCU on the board that runs **CMSIS-DAP** firmware, so the debug probe is part of the dongle itself. Over the **same USB cable** the PC sees two things:

| USB interface | What it is | Who uses it |
|---|---|---|
| Serial port (VCOM, e.g. `COM10`) | UART bridge to the EFR32 firmware | Compass, keycomm and keyadmin: RPC commands the firmware chooses to answer |
| CMSIS-DAP debug probe (HID) | **SWD bridge** to the EFR32 debug port | pyOCD, flash scripts; and anyone else with free tools |

So anyone holding the dongle can plug it into a laptop, install pyOCD (`pip install pyocd`) and dump the whole chip with one command. No case opening, no soldering, no special hardware. That is the "SWD shortcut", and it is why an unlocked dongle must never leave the factory.

The **Secure Engine (SE)** is the only thing that can close this door. The debug lock tells the SE to keep the AHB-AP (the memory/CPU access path) disabled on every boot. What remains reachable over SWD while locked is the SE's **Debug Challenge Interface (DCI)**: a narrow mailbox that accepts only SE commands (read lock status, get challenge, device erase, signed unlock). It gives no memory access.

> In this project the unlock does **not** go through DCI. The firmware fetches the challenge and passes the signed token to the SE over the USB serial RPC (`0x62` / `0x63`). The effect is the same: the SE verifies the token and reopens the AHB-AP until the next reset.

### 6.2 Reading the dongle's memory

| | (a) never locked | (b) secure-debug locked | (c) locked, then unlocked until reset |
|---|---|---|---|
| **USB serial (RPC)** | Only what the firmware allows: status, logs, license check. No raw memory reads. | **Same** | **Same** |
| **SWD: flash, RAM, NVM3, registers** | **Everything**, for anyone with the USB cable | **Nothing**: the SE keeps the port closed | **Everything**, until the next reset |
| **Keys inside the SE** (dongle identity key) | Not readable in plaintext (stored wrapped by the chip-unique PUF key) | Not readable | Not readable |

The lock does not change the USB serial channel at all. It only closes SWD.

### 6.3 Flashing

| | (a) never locked | (b) secure-debug locked | (c) unlocked until reset |
|---|---|---|---|
| **Normal flash** (`flash.bat`, `set_*_mode.bat`) | Anyone; NVM3 (license, identity) is preserved | **Impossible** | Possible; works like (a) until reset |
| **Re-provision** (`provision_dongle.py`) | Yes | Run `secure_debug_lock.py unlock` first (the preflight refuses a locked SWD port) | Yes |
| **Device erase** | Yes | Yes, but it **wipes flash and RAM**: firmware, license, identity (the User Data page with the encrypted tamper log survives) | Yes |
| **What survives an erase** | — | The Command Key in OTP: the chip stays bound to that key forever | Same |

### 6.4 Attack surface for reverse engineering

**(a) Never locked: wide open to anyone with a USB cable.**
* **Dump the whole firmware**, including the secret Compass calculations, and disassemble it offline.
* **Live debugging:** halt the CPU while Compass is talking to the dongle and read session keys and results from RAM; step through the license and RTC checks.
* **Patch and reflash while keeping NVM3.** For example, flash firmware with the license check removed. It still holds the genuine Root CA-signed certificate, so Compass accepts it as authentic. This is the worst case.
* Use the dongle as an algorithm oracle through the debugger.

**(b) Secure-debug locked: SWD is gone.** What is left:
* **USB serial protocol:** fuzzing, logic bugs in RPC handlers, attacks on the ECDHE session. This is identical in all three modes and becomes the main attack surface.
* **Device erase:** gives the attacker a blank chip. No firmware, no license, no certificate; firmware they write themselves is rejected by Compass because it has no Root CA-signed identity. Nothing useful is gained.
* **Physical attacks:** voltage or clock glitching to skip the SE lock check (the chip has glitch and tamper detectors, and the firmware's anti-tamper logic reacts), or decapping the chip. These need expensive equipment and expertise.
* **Stealing `debug_command_key.pem`.** This is the real weakness today: the development key is in git, so anyone with repository access can unlock every dongle locked with it. Production therefore gets a new key kept offline (section 5).

**(c) Locked, then unlocked until reset:** the same as (a), but only until the next power-on reset or device reset. Getting there requires a valid unlock token:
* Each token is bound to **this chip's serial number** and to its **current SE challenge**, so it is useless on another dongle. The challenge is not rolled, so a token would keep working on the same chip; keyadmin never stores it, and it exists only in the factory, in memory, during an unlock.
* The window exists only while the dongle is in the lab. Once it resets, it is back in mode (b).

**Bottom line:** (a) is never acceptable for a customer, because the dongle carries its own debugger. (b) is the shipping state. (c) is a service window that only the holder of the keys can open, and it closes on reset.

> **Hardware verification status (2026-10-27, dongle `0000000000000000880F62FFFE3E183B`):** lock applied and verified (`CMD_KEY:MATCH`, `SECURE_DEBUG:1`, `LOCK_APPLIED:1`); challenge-response unlock accepted by the SE; SWD reads confirmed while unlocked (vector table at `0x08000000`, Black Box at its old location `0x0817E000`, now moved to the User Data page `0x0FE00000`). A pyOCD software reset did **not** close the port again; re-locking after a pin reset (RESET button) or a power-on reset with the battery disconnected is still to be confirmed.
