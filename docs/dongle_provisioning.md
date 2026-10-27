# Dongle Provisioning, Build & Flash Scripts

Building, flashing and factory provisioning of the KeySec dongle (Seeed Studio XIAO MG24, Silicon Labs EFR32MG24).
The build and flash scripts live in `KeyFirmware/flashbat/`; the provisioning pipeline lives in `KeySec/keyadmin/scripts/provision_dongle.py`.

---

## Primary Workflow Scripts (`KeyFirmware/flashbat/`)

### `compile.bat`
Compiles both TrustZone firmware targets (`keyfirmware.hex` and `keyfirmware_prov.hex`) using CMake and Ninja.
Automatically merges the secure and non-secure binaries into unified flashable HEX files.

### `flash.bat`
Low-level hardware flasher that writes an arbitrary `.hex` image to the target MCU via pyOCD over SWD.
When invoked without arguments, it defaults to flashing the production image (`keyfirmware.hex`).

### `set_factory_mode.bat`
Flashes the factory provisioning firmware (`keyfirmware_prov.hex`) to put the dongle into unsealed admin mode.
In this mode, the device accepts serial administrative commands to inject cryptographic keys, timestamps, and licenses.

### `set_production_mode.bat`
Flashes the final production firmware (`keyfirmware.hex`) to seal the dongle for client distribution.
In this mode, administrative provisioning is permanently locked and only encrypted application queries are accepted.

### Factory provisioning (not here)
The full manufacturing pipeline lives in KeySec: `python KeySec/keyadmin/scripts/provision_dongle.py 365 3 [--lock]` (also in the admin console menu, section *FACTORY*). Run it with `--check` first: a read-only preflight (scripts, images, Root CA pair, pyOCD probe, free COM port, SWD not locked, Command Key vs header) that changes nothing.
It does not flash by itself: it calls `compile.bat`, `set_factory_mode.bat` and `set_production_mode.bat` from this folder, so these scripts remain the single source for building and flashing the firmware images.

---

## Secure Debug Lock (SWD)

Full description: [security/secure_debug_lock.md](security/secure_debug_lock.md).

The production firmware locks its own SWD port through the Secure Engine (no J-Link needed), over plaintext RPC `0x60-0x63`.
Host side: `KeySec/keyadmin/scripts/secure_debug_lock.py` and the admin console menu section *SECURE DEBUG LOCK*.

1. **Once per product (factory-wide key):** `python KeySec/keyadmin/scripts/generate_debug_command_key.py` creates `KeySec/keyadmin/keys/debug_command_key.pem` (next to the Root CA) and writes the public key into `src/secure/debug_command_pubkey.h`. Rebuild with `compile.bat`. The current key is a development key; generate new keys before real production.
2. **Protect development dongles:** `python KeySec/keyadmin/scripts/secure_debug_lock.py protect` adds the connected dongle to `KeySec/keyadmin/keys/secure_debug/protected_devices.json`. Every lock path (CLI, admin menu, `provision_dongle.py ... --lock`) refuses protected serials before sending anything to the dongle.
3. **Lock:** `python KeySec/keyadmin/scripts/provision_dongle.py 365 3 --lock` or `python KeySec/keyadmin/scripts/secure_debug_lock.py lock`. Writes the public Command Key to OTP (irreversible), enables secure debug, applies the lock. Device erase stays enabled.
4. **Unlock (until next reset):** `python KeySec/keyadmin/scripts/secure_debug_lock.py unlock`, then read memory with pyOCD in attach mode (`-M attach`) without resetting the dongle.

After locking, `flash.bat`, `set_factory_mode.bat` and `set_production_mode.bat` only work right after an unlock (the reset at the end of flashing locks the port again).
Per-dongle data lives in `KeySec/keyadmin/keys/secure_debug/devices/device_<SE serial>/` (`device.json`, access certificate, `challenge_<hex>/` folders).

---

## Internal Helpers & Engines (`KeyFirmware/flashbat/`)

### `get_python.bat`
Shared utility that discovers a valid Python 3 installation in the system and exports `PYTHON_EXE`.
Bypasses empty Windows Store stubs and verifies the interpreter so all batch scripts run reliably on any developer machine.

### `xiao_mg24_flash.py`
Cross-platform Python engine that manages pyOCD execution, automatic package dependency checks, and SWD flashing.
Invoked under the hood by `flash.bat`, `set_factory_mode.bat`, and `set_production_mode.bat`.

### `merge_hex.py`
Post-build Python script that merges ARM TrustZone Secure and Non-Secure HEX files using the `intelhex` library.
Generates the monolithic hex files stored in `cmake_gcc/build/base/`.

### `SiliconLabs.GeckoPlatform_EFR32MG24_DFP.2025.6.0.pack`
CMSIS Device Family Pack providing flash programming algorithms and register definitions for EFR32MG24.
Enables pyOCD to program the chip without needing a full Simplicity Studio installation.


