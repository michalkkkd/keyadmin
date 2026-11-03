# =============================================================================
# KEYSEC ADMIN CENTRAL CONSTANTS & MESSAGES DICTIONARY
# Single source of truth for all admin command IDs, menu texts, alerts and logs
# =============================================================================

# Admin Command IDs for KeyFirmware hardware dongle
MSG_ADMIN_DATE         = 0x03
MSG_ADMIN_LIC          = 0x04
MSG_ADMIN_WIPE         = 0x05
MSG_DEBUG_TIME         = 0x07
MSG_ADMIN_USERS        = 0x08
MSG_MEM_INFO           = 0x0A
MSG_PROVISION_IDENTITY = 0x0B
MSG_SAVE_CERTIFICATE   = 0x0C
MSG_BATTERY_INFO       = 0x0E
MSG_NVM_DIAG           = 0x0F
MSG_SYS_HEALTH         = 0x10
MSG_GET_LOG_COUNT      = 0x11
MSG_GET_LOG_LINE       = 0x12

# Secure Debug Lock Command IDs (plaintext, both firmware variants)
MSG_DEBUG_LOCK_STATUS    = 0x60
MSG_DEBUG_LOCK_APPLY     = 0x61
MSG_DEBUG_LOCK_CHALLENGE = 0x62
MSG_DEBUG_LOCK_UNLOCK    = 0x63

# Action Item IDs
ACTION_SYS_HEALTH      = 1
ACTION_MEMORY_NVM      = 2
ACTION_RTC_DIAG        = 3
ACTION_LICENSE_USERS   = 4
ACTION_BENCHMARK       = 7
ACTION_EXIT            = 8
ACTION_DEVICE_LOGS     = 9
ACTION_HB_START        = 10
ACTION_HB_DISABLE      = 14
ACTION_BATTERY_STATUS  = 16
ACTION_DONGLE_DIAG     = 17
ACTION_DECIPHER_DIAG   = 18
ACTION_DEBUG_LOCK_STATUS = 20
ACTION_DEBUG_LOCK_APPLY  = 21
ACTION_DEBUG_UNLOCK      = 22
ACTION_PROVISION_DONGLE  = 30

# CLI & Menu Navigation
ADMIN_CONSOLE_BANNER   = "  === KEYSEC DONGLE ADMIN CONSOLE ==="
ADMIN_ERR_ESTABLISH_CONN = "[-] Could not establish admin connection to Dongle."
ADMIN_MENU_TITLE       = "=== KEYSEC DONGLE ADMIN MENU ===\n"
ADMIN_PROMPT_PAUSE     = "\nPress any key to return to the menu..."
ADMIN_PROMPT_NAV       = "\nUse Up/Down arrows to navigate, Enter to select, Esc to exit."

# Menu Section Headers
ADMIN_SEC_DIAGNOSTICS  = "--- DIAGNOSTICS & HEALTH ---"
ADMIN_SEC_TESTING      = "--- TESTING & BENCHMARKING ---"
ADMIN_SEC_HEARTBEAT    = "--- HEARTBEAT BATTERY ---"
ADMIN_SEC_SECURE_DEBUG = "--- SECURE DEBUG LOCK (SWD) ---"
ADMIN_SEC_FACTORY      = "--- FACTORY ---"

# Menu Action Item Labels
ADMIN_ACT_SYS_HEALTH   = "System Health & Anti-Tamper Check"
ADMIN_ACT_BATTERY      = "Battery Status & Capacity (Li-Po)"
ADMIN_ACT_MEMORY       = "Memory & NVM3 Diagnostics"
ADMIN_ACT_RTC          = "Detailed Global RTC Diagnostics"
ADMIN_ACT_LICENSE      = "Check License & User Limits"
ADMIN_ACT_LOGS         = "View Async Device Logs"
ADMIN_ACT_DONGLE_DIAG  = "Dongle Diagnostics (this dongle, works on production firmware)"
ADMIN_ACT_DECIPHER_DIAG = "Decipher Diagnostic Payload (paste what the customer sent)"
ADMIN_ACT_BENCHMARK    = "Run Performance Benchmark (Algorithm Test)"
ADMIN_ACT_HB_START     = "Start sending heartbeat"
ADMIN_ACT_HB_DISABLE   = "Disable heartbeat for 20 seconds"
ADMIN_ACT_EXIT         = "Exit"
ADMIN_ACT_DEBUG_STATUS = "Secure Debug Lock Status"
ADMIN_ACT_DEBUG_LOCK   = "Apply Secure Debug Lock (one-way, OTP)"
ADMIN_ACT_DEBUG_UNLOCK = "Unlock Debug Port until next reset (challenge-response)"
ADMIN_ACT_PROVISION    = "Provision Dongle (full factory pipeline, wipes identity and license)"

# Execution Action Headers
ADMIN_HDR_SYS_HEALTH   = "--- System Health & Anti-Tamper Check ---"
ADMIN_HDR_BATTERY      = "--- Battery Status & Capacity (Li-Po) ---"
ADMIN_HDR_MEMORY       = "--- Memory & NVM3 Diagnostics ---"
ADMIN_HDR_RTC          = "--- Detailed Global RTC Diagnostics ---"
ADMIN_HDR_LICENSE      = "--- License & User Limits ---"
ADMIN_HDR_BENCHMARK    = "--- Performance Benchmark ---"
ADMIN_HDR_DEVICE_LOGS  = "--- Device RAM Logs ---"
ADMIN_HDR_HB_STATUS    = "--- Heartbeat Status ---"
ADMIN_HDR_HB_DISABLE   = "--- Disable Heartbeat Test ---"
ADMIN_HDR_DEBUG_STATUS = "--- Secure Debug Lock Status ---"
ADMIN_HDR_DEBUG_LOCK   = "--- Apply Secure Debug Lock ---"
ADMIN_HDR_DEBUG_UNLOCK = "--- Secure Debug Unlock (until next reset) ---"
ADMIN_HDR_PROVISION    = "--- Provision Dongle (factory pipeline) ---"
ADMIN_HDR_DONGLE_DIAG  = "--- Dongle Diagnostics (DIAG) ---"
ADMIN_HDR_DECIPHER_DIAG = "--- Decipher Diagnostic Payload ---"
ADMIN_PROMPT_DIAG_PASTE = "Paste the payload from -----BEGIN KEY DIAG----- to -----END KEY DIAG----- (or the whole report):"

# Security Alerts & Notifications
ADMIN_ALERT_TAMPER     = (
    "\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
    "!!! CRITICAL SECURITY ALERT: PHYSICAL TAMPER DETECTED !!!\n"
    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
)

# Status & Informational Messages
ADMIN_MSG_LICENSE_PREFIX    = "-> LICENSE:"
ADMIN_MSG_MAX_USERS_PREFIX  = "-> MAX USERS:"
ADMIN_MSG_HB_RESUMING       = "[INFO] Resuming automated heartbeat (every 3s)..."
ADMIN_MSG_HB_RUNNING        = "[INFO] Heartbeat is now running in the background."
ADMIN_MSG_HB_PAUSING        = "[INFO] Pausing automated heartbeat from Python..."
ADMIN_MSG_HB_EXPLANATION    = "[INFO] The MCU requires PING every 3s. Without it, it will timeout (~7.5s) and enter EM3 sleep."
ADMIN_MSG_HB_WAITING        = "[INFO] Waiting 20 seconds..."
ADMIN_MSG_HB_ASLEEP         = "[INFO] MCU should be deeply asleep now."
ADMIN_MSG_HB_VERIFY_WAKE    = "[INFO] Sending a manual command to verify Wake-on-RX works..."
ADMIN_DEFAULT_USER_EMAIL     = "admin_test@compass.com"
ADMIN_BENCHMARK_ITERATIONS   = 5000
ADMIN_BENCHMARK_LOG_STEP     = 100
ADMIN_MSG_BENCH_START_FMT    = "Executing benchmark: {iterations} iterations with random inputs..."
ADMIN_MSG_BENCH_ITER_FMT     = "[{idx:6d}/{total:6d}] Last: {a} + {b} = {res} ({duration_ms:.2f} ms)"
ADMIN_MSG_BENCH_SUMMARY_HDR  = "=== Performance Benchmark Summary ==="
ADMIN_MSG_BENCH_SUCCESS_FMT  = "Success: {success_count}/{total_count} (Errors: {error_count})"
ADMIN_MSG_BENCH_TOTAL_TIME   = "Total time: {total_s:.3f} s ({total_ms:.2f} ms)"
ADMIN_MSG_BENCH_AVG_TIME     = "Average latency: {avg_ms:.2f} ms"
ADMIN_MSG_BENCH_MIN_MAX_FMT  = "Latency min / max: {min_ms:.2f} ms / {max_ms:.2f} ms"
ADMIN_MSG_BENCH_THROUGHPUT   = "Throughput: {ops_per_sec:.2f} calls/sec"
ADMIN_MSG_BENCH_RESULT_FMT  = "Result: {res}"
ADMIN_MSG_BENCH_TIME_FMT    = "Time taken: {duration_ms:.2f} ms"

# Diagnostic Logs Transfer
ADMIN_ERR_LOG_SIZE_FAIL     = "Failed to get log size from device."
ADMIN_MSG_NO_LOGS           = "No logs in device RAM."
ADMIN_MSG_FETCHING_LOGS_FMT = "--- Fetching {total_size} bytes of logs from device RAM (10KB Buffer) ---"
ADMIN_ERR_FETCH_LOGS_FMT    = "Error fetching logs: {e}"
ADMIN_LOG_REQ_PAYLOAD       = b"X"
ADMIN_LOG_LINE_FMT          = "[{idx:03d}/{total:03d}] {line}"

# Application Bootstrap Messages
ADMIN_MSG_STARTING          = "Starting KeySec Admin Tool..."
ADMIN_ERR_INIT_FAIL         = "Could not initialize KeySec Admin connection. Check USB dongle."
ADMIN_ERR_UNHANDLED_FMT     = "An error occurred: {e}"
ADMIN_MSG_CONNECTING_FMT    = "Initializing Admin connection on port {port}..."
ADMIN_ERR_DONGLE_CONN_FAIL  = "Failed to connect to KeySec Dongle."

# General Tokens & Formats
RESP_OK_PREFIX_STR          = "OK:"
RESP_OK_PREFIX_COLON        = f"{RESP_OK_PREFIX_STR} "
CHAR_ENCODING_UTF8          = "utf-8"
LINE_DELIMITER_LF           = "\n"
STRUCT_FMT_UINT32_LE        = "<I"

# System Health & Anti-Tamper Report
RE_TAMPER_EVENTS            = r"TamperEvents:\s*(\d+)"
RE_TEMPERATURE              = r"Temp:\s*(-?[\d.]+)C"
RE_TAMPER_LOG               = r"TamperLog:\s*(\d+)"
TOKEN_ERR                   = "ERR"
TOKEN_FAIL                  = "FAIL"

# Menu Navigation & OS Keys
MENU_KEY_UP                 = "up"
MENU_KEY_DOWN               = "down"
MENU_KEY_ENTER              = "enter"
MENU_KEY_ESC                = "esc"
OPT_TYPE_HEADER             = "header"
OPT_TYPE_ACTION             = "action"
DICT_KEY_TYPE               = "type"
DICT_KEY_TEXT               = "text"
DICT_KEY_ID                 = "id"
OS_NAME_NT                  = "nt"
CMD_CLEAR_WIN               = "cls"
CMD_CLEAR_POSIX             = "clear"
ADMIN_MSG_WAITING_REMAINING_FMT = "Waiting... {remaining}s"
ADMIN_PREFIX_ACTIVE_OPTION  = " > "
ADMIN_PREFIX_INACTIVE_OPTION= "   "
ADMIN_PREFIX_HEADER         = " "


# =============================================================================
# SECURE DEBUG LOCK (SWD lock with challenge-response unlock)
# =============================================================================

# Store layout: Command Key next to the Root CA in keyadmin/keys, per-dongle folders in keyadmin/keys/secure_debug
SDL_KEYS_DIRNAME              = "keys"
SDL_STORE_DIRNAME             = "secure_debug"
SDL_DEVICES_DIRNAME           = "devices"
SDL_PROTECTED_FILENAME        = "protected_devices.json"
SDL_DEVICE_DIR_FMT            = "device_{serial}"
SDL_COMMAND_KEY_FILENAME      = "debug_command_key.pem"
SDL_COMMAND_PUBKEY_FILENAME   = "debug_command_pubkey.pem"
SDL_DEVICE_INFO_FILENAME      = "device.json"
SDL_FIRMWARE_HEADER_RELPATH   = ("..", "KeyFirmware", "src", "secure", "debug_command_pubkey.h")
SDL_PACK_RELPATH              = ("..", "KeyFirmware", "flashbat", "SiliconLabs.GeckoPlatform_EFR32MG24_DFP.2025.6.0.pack")
SDL_TAMPER_LOG_DUMP_FILENAME  = "userdata_dump.bin"
TLOG_KEY_FILENAME             = "tamper_log_key.bin"
HOST_KEY_FILENAME             = "host_key.pem"
TLOG_FIRMWARE_HEADER_RELPATH  = ("..", "KeyFirmware", "src", "core", "tamper_log_key.h")
SDL_PYOCD_TARGET              = "efr32mg24b220f1536im48"
SDL_PYOCD_TIMEOUT_SEC         = 60
SDL_MSG_TAMPER_LOG_READING    = "[*] Reading the tamper log over SWD (pyOCD attach mode, no reset)..."
SDL_MSG_TAMPER_LOG_SAVED_FMT  = "[+] User Data page (tamper log) saved: {path} ({size} bytes)\n{report}"

# Device JSON fields & events
SDL_JSON_SERIAL               = "serial"
SDL_JSON_PORT                 = "usb_port"
SDL_JSON_LAST_STATUS          = "last_status"
SDL_JSON_EVENTS               = "events"
SDL_JSON_EVENT                = "event"
SDL_JSON_TIMESTAMP            = "timestamp"
SDL_JSON_RESPONSE             = "response"
SDL_JSON_CHALLENGE            = "challenge"
SDL_JSON_SUCCESS              = "success"
SDL_JSON_PROTECTED_SERIALS    = "protected_serials"
SDL_JSON_NOTE                 = "note"
SDL_PROTECTED_NOTE            = "Dongles listed here can never be debug-locked by keyadmin tools (development units). Remove a serial only on purpose."
SDL_EVENT_STATUS              = "STATUS"
SDL_EVENT_LOCK                = "LOCK"
SDL_EVENT_UNLOCK              = "UNLOCK"
SDL_JSON_INDENT               = 2

# Silicon Labs Series 2 secure debug token format (se_manager_secure_debug example)
SDL_SERIAL_SIZE               = 16
SDL_CHALLENGE_SIZE            = 16
SDL_ECC_COORD_SIZE            = 32
SDL_CERT_MAGIC                = 0xE5ECCE01
SDL_CERT_AUTH_DEBUG           = 0x003E
SDL_CERT_AUTH_MISC            = 0x00
SDL_CERT_KEY_INDEX            = 0x00
SDL_CERT_AUTH_TAMPER          = 0xFFFFFFB6
SDL_DEBUG_ACCESS_CMD          = 0xFD010001
SDL_DEBUG_UNLOCK_PARAM        = 0x3E      # debug port + NS/S invasive + non-invasive (matches firmware request)
SDL_CERT_BODY_STRUCT          = "<IHBBI16s64s"
SDL_CHALLENGE_RESP_STRUCT     = "<II16s"
SDL_ACCESS_CERT_SIZE          = 156
SDL_UNLOCK_TOKEN_SIZE         = 220

# Firmware response parsing
SDL_FIELD_SEPARATOR           = ";"
SDL_KEY_VALUE_SEPARATOR       = ":"
SDL_FIELD_SERIAL              = "SERIAL"
SDL_FIELD_CHALLENGE           = "CHALLENGE"
SDL_FIELD_CMD_KEY             = "CMD_KEY"
SDL_FIELD_BUILTIN_KEY         = "BUILTIN_KEY"
SDL_FIELD_SECURE_DEBUG        = "SECURE_DEBUG"
SDL_FIELD_LOCK_APPLIED        = "LOCK_APPLIED"
SDL_FIELD_LOCK_ACTIVE         = "LOCK_ACTIVE"
SDL_FIELD_DEVICE_ERASE        = "DEVICE_ERASE"
SDL_FLAG_TRUE                 = "1"
SDL_CMD_KEY_NONE              = "NONE"
SDL_CMD_KEY_MATCH             = "MATCH"
SDL_CMD_KEY_MISMATCH          = "MISMATCH"
SDL_LOCK_TIMEOUT_SEC          = 8.0
SDL_UNLOCK_TIMEOUT_SEC        = 5.0
SDL_LOCK_MAX_RETRIES          = 2
SDL_CONFIRM_WORD              = "LOCK"

# Firmware header generation (public command key compiled into KeyFirmware)
SDL_HEADER_TEMPLATE = """#ifndef DEBUG_COMMAND_PUBKEY_H
#define DEBUG_COMMAND_PUBKEY_H

// =============================================================================
// Secure Debug Public Command Key (ECC P-256, raw X||Y, big-endian)
// GENERATED by KeySec/keyadmin/scripts/generate_debug_command_key.py - DO NOT EDIT.
// Fingerprint (SHA-256 of raw key): {fingerprint}
// =============================================================================

#include <stdint.h>

#define DEBUG_COMMAND_PUBKEY_PROVISIONED 1
#define DEBUG_COMMAND_PUBKEY_SIZE        64

static const uint8_t debug_command_pubkey[DEBUG_COMMAND_PUBKEY_SIZE] = {{
{body}
}};

#endif // DEBUG_COMMAND_PUBKEY_H
"""
SDL_HEADER_BYTES_PER_LINE     = 8
SDL_HEADER_BYTE_FMT           = "0x{:02X}"
SDL_HEADER_LINE_INDENT        = "    "
SDL_HEADER_BYTE_JOIN          = ", "
SDL_HEADER_LINE_JOIN          = ",\n"

# User-facing messages
SDL_MSG_STATUS_FMT = (
    "Serial (SE)      : {serial}\n"
    "                   Unique Secure Engine chip ID; names the per-dongle data folder.\n"
    "Command key (OTP): {cmd_key}  (built into firmware: {builtin})\n"
    "                   NONE = no key burned yet, MATCH = OTP holds our key, MISMATCH = foreign key (lock refused).\n"
    "                   'built into firmware' = this firmware carries the public key needed to lock (False = cannot lock).\n"
    "Secure debug     : {secure_debug}\n"
    "                   True = the port can be reopened with a token signed by debug_command_key.pem.\n"
    "Lock applied     : {lock_applied}\n"
    "                   True = the debug lock is set permanently and comes back on every reset.\n"
    "Port locked now  : {lock_active}\n"
    "                   True = SWD (flash/debug probe) is closed at this moment; False after an unlock until reset.\n"
    "Device erase     : {device_erase}\n"
    "                   True = a full flash erase can still recover the chip (wipes firmware and license).\n"
    "Lock protection  : {protection}\n"
    "                   PROTECTED = this serial is on the dev list, so every lock command is refused on the host.\n"
    "Data folder      : {folder}\n"
    "                   Host folder with this dongle's event log and tamper log dump."
)
SDL_MSG_LOCK_WARNING = (
    "WARNING: This writes the public Command Key to OTP (irreversible) and locks the SWD port.\n"
    "After this, flashing/debugging requires a Secure Debug Unlock signed with debug_command_key.pem.\n"
    "Device erase stays ENABLED (erase still recovers the port, but wipes the whole flash)."
)
SDL_PROMPT_CONFIRM_FMT        = "Type {word} to confirm: "
SDL_PROTECTION_ON             = "PROTECTED (lock refused)"
SDL_PROTECTION_OFF            = "not protected"
SDL_MSG_PROTECTED_ADDED_FMT   = "[+] Dongle {serial} added to {path}. Debug lock will be refused for it."
SDL_MSG_PROTECTED_EXISTS_FMT  = "[=] Dongle {serial} is already protected ({path})."
SDL_MSG_ABORTED               = "[-] Aborted by user."
SDL_MSG_ALREADY_LOCKED        = "[+] Secure debug lock is already active on this dongle."
SDL_MSG_LOCK_OK               = "[+] Secure debug lock applied and verified."
SDL_MSG_UNLOCK_OK             = "[+] Debug port is OPEN until the next reset / power cycle."
SDL_MSG_UNLOCK_HINT_FMT = (
    "Do NOT reset or unplug the dongle. Read more memory in attach mode (use forward slashes, pyOCD drops backslashes):\n"
    "  python -m pyocd cmd -t efr32mg24b220f1536im48 --pack \"{pack}\" -M attach -c \"savemem 0x0FE00000 1024 {outfile}\""
)
SDL_MSG_SAVED_TO_FMT          = "[*] Saved to: {path}"
SDL_MSG_KEY_CREATED_FMT       = "[+] Command key pair created in: {path}"
SDL_MSG_KEY_BACKUP            = "[!] Keep debug_command_key.pem safe. Without it, locked dongles can only be recovered by a full device erase."
SDL_MSG_HEADER_WRITTEN_FMT    = "[+] Firmware header written: {path} (fingerprint {fingerprint}). Rebuild KeyFirmware."
SDL_MSG_SMOKE_TEST            = "[*] Pre-lock smoke test: secure session + license check..."
SDL_MSG_SMOKE_OK_FMT          = "[+] Smoke test passed: {result}"

SDL_ERR_COMMAND_KEY_EXISTS_FMT  = "Command key already exists: {path}. Refusing to overwrite (locked dongles depend on it)."
SDL_ERR_COMMAND_KEY_MISSING_FMT = "Command key not found: {path}. Run generate_debug_command_key.py first."
SDL_ERR_NO_BUILTIN_KEY        = "Firmware has no built-in command key. Generate the key, rebuild and reflash the firmware."
SDL_ERR_KEY_MISMATCH          = "OTP command key differs from the firmware key. This dongle cannot be locked with this firmware."
SDL_ERR_FIRMWARE_FMT          = "Firmware returned an error: {response}"
SDL_ERR_BAD_RESPONSE_FMT      = "Malformed firmware response: {response}"
SDL_ERR_LOCK_NOT_VERIFIED_FMT = "Lock was not confirmed by status readback: {status}"
SDL_ERR_SMOKE_FAILED_FMT      = "Smoke test failed, NOT locking: {result}"
SDL_ERR_NO_CONNECTION         = "Could not connect to the dongle."
SDL_ERR_DEVICE_PROTECTED_FMT  = "Dongle {serial} is on the protected list ({path}). Debug lock refused."

# =============================================================================
# FACTORY PROVISIONING PIPELINE (keyadmin/scripts/provision_dongle.py)
# =============================================================================
PROV_DEFAULT_LICENSE_DAYS     = 365
PROV_DEFAULT_MAX_USERS        = 3
PROV_FLASHBAT_RELPATH         = ("..", "KeyFirmware", "flashbat")
PROV_BAT_COMPILE              = "compile.bat"
PROV_BAT_FACTORY_MODE         = "set_factory_mode.bat"
PROV_BAT_PRODUCTION_MODE      = "set_production_mode.bat"
PROV_ROOT_CA_KEY_FILENAME     = "root_ca_key.pem"
PROV_VERIFY_USER_EMAIL        = "factory_test@compass.com"
PROV_ALG1_INPUT_A             = 15
PROV_ALG1_INPUT_B             = 27
PROV_ALG1_EXPECTED            = "42"
PROV_PORT_WAIT_SEC            = 15.0
PROV_PORT_POLL_SEC            = 0.5
PROV_SETTLE_SEC               = 3.0
PROV_ATTEMPTS                 = 5
PROV_RETRY_DELAY_SEC          = 2.0

PROV_BANNER                   = "=== KEYSEC FACTORY PROVISIONING PIPELINE ==="
PROV_MSG_PLAN_FMT             = "License: {days} days | Max users: {users} | Compile: {compile} | Flash: {flash} | Debug lock: {lock}"
PROV_STEP_FMT                 = ">>> STEP {idx}/{total}: {title}"
PROV_STEP_COMPILE             = "Compile firmware (compile.bat)"
PROV_STEP_FACTORY             = "Flash factory firmware (set_factory_mode.bat)"
PROV_STEP_SECRETS             = "Provision identity, certificate, RTC, license and users"
PROV_STEP_PRODUCTION          = "Seal with production firmware (set_production_mode.bat)"
PROV_STEP_VERIFY              = "Verify sealed dongle (secure session, license, algorithm, admin rejection)"
PROV_STEP_LOCK                = "Secure Debug Lock"
PROV_MSG_RUNNING_FMT          = "[*] Running: {cmd}"
PROV_MSG_WAIT_PORT            = "[*] Waiting for the dongle COM port..."
PROV_MSG_PORT_FMT             = "[+] Dongle on port: {port}"
PROV_MSG_ATTEMPT_FAILED_FMT   = "[*] Attempt {attempt}/{total} failed: {error}"
PROV_MSG_ROOT_CA_LOADED_FMT   = "[*] Root CA private key loaded: {path}"
PROV_MSG_IDENTITY_FMT         = "[+] Dongle identity public key: {pubkey}"
PROV_MSG_CERT_SAVED           = "[+] Identity certificate signed by Root CA and saved to NVM3."
PROV_MSG_RTC_FMT              = "[+] RTC base timestamp: {response}"
PROV_MSG_LICENSE_FMT          = "[+] License days: {response}"
PROV_MSG_USERS_FMT            = "[+] Max users: {response}"
PROV_MSG_SECURE_SESSION       = "[+] Secure ECDHE session established."
PROV_MSG_VERIFY_LICENSE_FMT   = "[+] License check: {result}"
PROV_MSG_VERIFY_ALG1_FMT      = "[+] Algorithm 1 ({a} + {b}): {result}"
PROV_MSG_VERIFY_ADMIN_FMT     = "[+] Admin command rejected by production firmware: {result}"
PROV_MSG_LOCK_SKIPPED         = "[=] Secure Debug Lock skipped (enable with --lock)."
PROV_MSG_SUCCESS              = "[+] SUCCESS: dongle provisioned, sealed and verified."
PROV_MSG_SUCCESS_LOCKED       = "[+] SUCCESS: dongle provisioned, sealed, verified and debug-locked."
PROV_MSG_MENU_WARNING         = (
    "WARNING: This reflashes the connected dongle and generates a NEW identity, certificate and license.\n"
    "Any existing license on this dongle is lost. The admin connection is closed and reopened afterwards."
)
PROV_PROMPT_DAYS_FMT          = "License days [{default}]: "
PROV_PROMPT_USERS_FMT         = "Max users [{default}]: "
PROV_PROMPT_LOCK              = "Apply Secure Debug Lock at the end? [y/N]: "
PROV_PROMPT_CONFIRM_FMT       = "Type {word} to start provisioning: "
PROV_CONFIRM_WORD             = "OK"
PROV_ANSWER_YES               = "y"
PROV_MSG_RECONNECTING         = "[*] Reconnecting admin console to the dongle..."
PROV_ERR_RECONNECT            = "[-] Could not reconnect to the dongle. Restart the admin console."

PROV_ERR_FLASHBAT_MISSING_FMT = "flashbat folder not found: {path}"
PROV_ERR_BAT_FAILED_FMT       = "{bat} failed with exit code {code}."
PROV_ERR_NO_PORT              = "Dongle COM port not found (VID=0x2886, PID=0x0062)."
PROV_ERR_ROOT_CA_MISSING_FMT  = "Root CA private key not found: {path}. Run generate_root_ca.py first."
PROV_ERR_SEALED               = "Dongle runs sealed production firmware and rejects provisioning. Flash factory firmware first."
PROV_ERR_STEP_FMT             = "{step} failed: {response}"
PROV_ERR_STEP_IDENTITY        = "Identity generation"
PROV_ERR_STEP_CERT            = "Certificate save"
PROV_ERR_STEP_RTC             = "RTC sync"
PROV_ERR_STEP_LICENSE         = "License days"
PROV_ERR_STEP_USERS           = "Max users"
PROV_ERR_NO_SESSION           = "No secure ECDHE session with the production firmware."
PROV_ERR_LICENSE_INVALID_FMT  = "License invalid on the sealed dongle: {result}"
PROV_ERR_ALG1_FMT             = "Algorithm 1 returned {result}, expected {expected}."
PROV_ERR_ADMIN_ACCEPTED       = "CRITICAL: production firmware accepted an admin command (wipe)."
PROV_ERR_UNKNOWN_TOKEN        = "Unknown"
PROV_ERR_FAILED_FMT           = "[-] PROVISIONING FAILED: {error}"
PROV_ERR_INVALID_NUMBER_FMT   = "Not a positive number: {value}"
PROV_ERR_LOCK_ABORTED         = "Secure Debug Lock aborted by operator (dongle is provisioned, SWD still open)."

# Preflight (nothing on the dongle is changed until every check passes)
PROV_FLASHBAT_FILES           = ("compile.bat", "set_factory_mode.bat", "set_production_mode.bat", "get_python.bat",
                                 "xiao_mg24_flash.py", "merge_hex.py",
                                 "SiliconLabs.GeckoPlatform_EFR32MG24_DFP.2025.6.0.pack")
PROV_FIRMWARE_RELPATH         = ("..", "KeyFirmware", "cmake_gcc", "build", "base")
PROV_FIRMWARE_IMAGES          = ("keyfirmware_prov.hex", "keyfirmware.hex")
PROV_BAT_GET_PYTHON           = "get_python.bat"
PROV_ENV_PYTHON_PREFIX        = "PYTHON_EXE="
PROV_TOOLCHAIN_PROBE_SCRIPT   = ("import pyocd, intelhex; from pyocd.core.helpers import ConnectHelper; "
                                 "print(len(ConnectHelper.get_all_connected_probes(blocking=False)))")
PROV_TOOLCHAIN_TIMEOUT_SEC    = 60
PROV_STEP_PREFLIGHT           = "Preflight checks (nothing is changed on the dongle)"
PROV_CHECK_OK_FMT             = "  [OK]   {name}: {detail}"
PROV_CHECK_WARN_FMT           = "  [WARN] {name}: {detail}"
PROV_CHECK_FAIL_FMT           = "  [FAIL] {name}: {detail}"
PROV_CHECK_ARGS               = "Arguments"
PROV_CHECK_FLASHBAT           = "flashbat scripts"
PROV_CHECK_IMAGES             = "Firmware images"
PROV_CHECK_ROOT_CA            = "Root CA key pair"
PROV_CHECK_TOOLCHAIN          = "Flash toolchain (pyOCD + probe)"
PROV_CHECK_DONGLE             = "Dongle on USB"
PROV_CHECK_LOCK_KEY           = "Debug Command Key"
PROV_DETAIL_ARGS_FMT          = "{days} days, {users} users"
PROV_DETAIL_FILES_FMT         = "{count} files in {path}"
PROV_DETAIL_IMAGES_REBUILT    = "rebuilt by STEP compile"
PROV_DETAIL_IMAGES_FMT        = "{images} (built {built})"
PROV_DETAIL_ROOT_CA_FMT       = "private key matches the public key used for ECDHE ({path})"
PROV_DETAIL_TOOLCHAIN_FMT     = "python '{python}', 1 debug probe"
PROV_DETAIL_DONGLE_FMT        = "{port}, serial {serial}, SWD locked: {locked}, protected: {protected}"
PROV_DETAIL_DONGLE_NO_STATUS_FMT = "{port}, no debug-lock status ({error}); blank or old firmware, flashing will tell"
PROV_DETAIL_LOCK_KEY_FMT      = "debug_command_pubkey.h matches {path}"
PROV_DETAIL_NOT_NEEDED        = "not needed (no --lock)"
PROV_MSG_CHECK_ONLY           = "[+] Preflight passed. Nothing was changed (--check)."
PROV_HINT_FLASH_FAILED        = ("Hint: unplug and replug the dongle (pyOCD can leave the MCU halted), close any app using the "
                                 "COM port, then run the pipeline again.")
PROV_ERR_PREFLIGHT_FMT        = "{count} preflight check(s) failed, the dongle was not touched."
PROV_ERR_ARGS_FMT             = "days and users must be positive (got {days}, {users})"
PROV_ERR_FILES_MISSING_FMT    = "missing: {files}"
PROV_ERR_IMAGES_MISSING_FMT   = "missing {images}; run without --skip-compile"
PROV_ERR_IMAGES_STALE         = "older than debug_command_pubkey.h; run without --skip-compile"
PROV_ERR_IMAGES_NOT_REBUILT_FMT = "compile.bat did not refresh {images}"
PROV_ERR_ROOT_CA_PUB_MISSING  = "keycomm Root CA public key (root_ca_pub.pem) not found"
PROV_ERR_ROOT_CA_MISMATCH_FMT = "root_ca_key.pem does not match {path}; the sealed dongle would fail the ECDHE check"
PROV_ERR_PYTHON_NOT_FOUND     = "get_python.bat did not return an interpreter"
PROV_ERR_TOOLCHAIN_FMT        = "'{python}' cannot load pyocd/intelhex: {error}"
PROV_ERR_PROBE_COUNT_FMT      = "{count} debug probes connected; connect exactly one dongle"
PROV_ERR_PORT_COUNT_FMT       = "{count} dongle COM ports found; connect exactly one dongle"
PROV_ERR_PORT_NOT_FOUND_FMT   = "port {port} is not a KeySec dongle (connected: {ports})"
PROV_ERR_PORT_BUSY_FMT        = "cannot open {port} ({error}); close the admin console / Compass"
PROV_ERR_DONGLE_LOCKED_FMT    = "dongle {serial} has SWD locked; run 'secure_debug_lock.py unlock' first (flashing would fail)"
PROV_ERR_DONGLE_PROTECTED_FMT = "dongle {serial} is protected; --lock would be refused after provisioning"
PROV_ERR_HEADER_NOT_PROVISIONED = "debug_command_pubkey.h has no key; run generate_debug_command_key.py"
PROV_ERR_HEADER_MISMATCH_FMT  = "debug_command_pubkey.h does not match {path}; unlock would be impossible. Run generate_debug_command_key.py --header-only"

# ==============================================================================
# Dongle diagnostics: keyadmin decrypts and judges the report (Compass carries no meanings,
# thresholds or keys to read it). Envelope format: keycomm/core/constants.py DIAG_ENVELOPE_*.
# ==============================================================================
DIAG_REPORT_KEY_FILENAME    = "diag_report_key.pem"

DIAG_CODE_LICENSE           = "LI_1"
DIAG_CODE_LICENSE_DAYS      = "LI_2"
DIAG_CODE_CLOCK             = "CL_1"
DIAG_CODE_USERS             = "UL_1"
DIAG_CODE_BATTERY           = "BA_1"
DIAG_CODE_TEMPERATURE       = "TE_1"
DIAG_CODE_NVM               = "NV_1"
DIAG_CODE_RESET_CAUSE       = "RS_1"
DIAG_CODE_TAMPER            = "TA_1"
DIAG_CODE_RESET_HISTORY     = "RS_2"
DIAG_CODE_SESSION           = "SE_1"
DIAG_CODE_FRAMES            = "LK_2"
DIAG_CODE_IDENTITY          = "ID_1"
DIAG_CODE_DEBUG_LOCK        = "DB_1"
DIAG_CODE_CMD_ERRORS        = "ER_1"
DIAG_CODE_BATTERY_DIP       = "BA_2"
DIAG_CODE_TEMP_RANGE        = "TE_2"
DIAG_CODE_APP_CRASH         = "AP_1"
DIAG_BATTERY_DIP_MV         = 3610   # 5 % on the LiPo curve (battery_monitor.c)

DIAG_LICENSE_DAYS_WARN      = 30
DIAG_CLOCK_WARN_S           = 3600
DIAG_CLOCK_BAD_S            = 86400
DIAG_BATTERY_LOW_PCT        = 20
DIAG_BATTERY_CRITICAL_PCT   = 10
DIAG_BATTERY_UNKNOWN_PCT    = 255
DIAG_TEMP_OK_MIN_X10        = 0
DIAG_TEMP_OK_MAX_X10        = 500
DIAG_TEMP_LIMIT_MIN_X10     = -100
DIAG_TEMP_LIMIT_MAX_X10     = 700
DIAG_NVM_FREE_WARN_PCT      = 10
RSTCAUSE_WDOG_MASK          = (1 << 3) | (1 << 4)
RSTCAUSE_LOCKUP_MASK        = 1 << 5
RSTCAUSE_BROWNOUT_MASK      = (1 << 7) | (1 << 8) | (1 << 9) | (1 << 10) | (1 << 11)
RSTCAUSE_SE_TAMPER_MASK     = 1 << 13

DIAG_CODE_MEANINGS = {
    "CO_1": "Dongle visible on USB (VID/PID)",
    "CO_2": "COM port can be opened",
    "PI_1": "Dongle answers PING",
    "KY_1": "root_ca_pub.pem found next to the program",
    "HS_1": "Secure handshake (dongle identity + Host Key)",
    "FW_1": "Firmware returns the sealed DIAG record",
    "LK_1": "USB link quality (10 PINGs + retransmissions)",
    "LI_1": "License status",
    "LI_2": "License days left",
    "CL_1": "Dongle clock vs PC clock",
    "UL_1": "Active users limit",
    "BA_1": "Battery level",
    "TE_1": "MCU temperature",
    "NV_1": "NVM3 free space",
    "RS_1": "Cause of the last reset",
    "TA_1": "Tamper events",
    "RS_2": "Abnormal resets since provisioning",
    "SE_1": "Secure session problems since boot",
    "LK_2": "Corrupted USB frames since boot",
    "ID_1": "Dongle identity and certificate",
    "DB_1": "Debug port (SWD) lock",
    "ER_1": "Failed dongle commands (last 4 kept)",
    "BA_2": "Lowest battery voltage since boot",
    "TE_2": "Temperature range since boot",
    "AP_1": "Compass crash report",
}
DIAG_RESULT_MEANINGS = {
    "CO_1 FAIL_1": "no dongle found: not plugged in, charge-only cable, or no USB driver",
    "CO_2 FAIL_1": "port busy: another program holds it (e.g. Compass still running)",
    "CO_2 FAIL_2": "port cannot be opened (driver or USB error)",
    "PI_1 FAIL_1": "no PONG: firmware not running, or dongle wiped",
    "PI_1 FAIL_2": "port lost while connecting",
    "KY_1 FAIL_1": "root_ca_pub.pem missing in keys/ next to the program",
    "HS_1 FAIL_1": "handshake rejected: dongle not provisioned/wiped, wrong certificate or wrong Host Key",
    "HS_1 FAIL_2": "handshake crashed (malformed reply)",
    "FW_1 FAIL_1": "firmware too old: no DIAG command",
    "FW_1 FAIL_2": "DIAG returned an error",
    "FW_1 FAIL_3": "DIAG reply of another size: firmware older or newer than 1.4.0",
    "LK_1 WARN_1": "commands needed retransmissions (poor USB link: hub, extension cable)",
    "LK_1 FAIL_1": "PINGs lost",
    "LI_1 FAIL_1": "license expired",
    "LI_1 FAIL_2": "no license provisioned",
    "LI_1 FAIL_3": "no clock (RTC never set or wiped)",
    "LI_2 WARN_1": "30 days or less left",
    "CL_1 WARN_1": "dongle clock off by more than 1 hour",
    "CL_1 WARN_2": "dongle clock off by more than 1 day",
    "UL_1 FAIL_1": "user limit is 0 (not provisioned)",
    "UL_1 WARN_1": "user limit full right now (users active in the last 10 min)",
    "BA_1 WARN_1": "battery below 20 %",
    "BA_1 FAIL_1": "battery below 10 %",
    "BA_1 FAIL_2": "battery read failed (ADC)",
    "TE_1 WARN_1": "temperature outside 0..50 C",
    "TE_1 FAIL_1": "temperature outside -10..70 C (tamper range)",
    "NV_1 WARN_1": "NVM3 less than 10 % free",
    "NV_1 FAIL_1": "NVM3 stats unavailable",
    "RS_1 FAIL_1": "Secure Engine tamper reset",
    "RS_1 WARN_1": "brown-out reset (supply voltage dropped)",
    "RS_1 WARN_2": "watchdog reset (firmware hung)",
    "RS_1 WARN_3": "CPU lockup reset (hard fault)",
    "TA_1 WARN_1": "tamper events since boot",
    "TA_1 WARN_2": "entries in the persistent tamper log (earlier events or a wipe)",
    "RS_2 WARN_1": "brown-out resets seen (supply drops: cable, hub, battery)",
    "RS_2 WARN_2": "watchdog resets seen (firmware hung)",
    "RS_2 WARN_3": "CPU lockup resets seen (hard faults)",
    "RS_2 FAIL_1": "Secure Engine tamper resets seen",
    "SE_1 WARN_1": "handshakes rejected (wrong Host Key, other program, or attack)",
    "SE_1 WARN_2": "requests that did not decrypt (session out of sync or tampering)",
    "LK_2 WARN_1": "frames dropped for a bad checksum (USB noise)",
    "ID_1 FAIL_1": "no device certificate: not provisioned or wiped",
    "ID_1 FAIL_2": "no identity key: not provisioned or wiped",
    "DB_1 WARN_1": "debug lock not applied (development dongle?)",
    "DB_1 WARN_2": "debug port open right now (lock applied, unlocked until reset)",
    "ER_1 WARN_1": "dongle commands failed recently, see Last errors",
    "BA_2 WARN_1": "battery dropped below ~5 % since boot",
    "TE_2 WARN_1": "temperature left 0..50 C since boot",
    "AP_1 WARN_1": "Compass wrote a crash report (FATAL_CRASH_REPORT.txt)",
}
DIAG_EXPLAIN_FMT            = "  {line:<16} {meaning}{detail}"
DIAG_EXPLAIN_DETAIL_FMT     = "  [{detail}]"

# Sealed record v4 (KeyFirmware src/core/diag_record.h, 256 bytes; field list in sealed_record_decoder.py)
DIAG_SEALED_IV_LEN          = 16
DIAG_SEALED_RECORD_VERSION  = 4
DIAG_SEALED_MAGIC           = 0xD1A6
DIAG_SEALED_FLAG_PROV       = 0x01
DIAG_SEALED_FLAG_LIVE_WIPE  = 0x02
DIAG_SEALED_FLAG_CERT       = 0x04
DIAG_SEALED_NO_TREND        = -32768
# Same order as usage_counter_t in KeyFirmware src/core/usage_counters.h
DIAG_USAGE_NAMES = (
    "Test Add", "Compass Sim PK", "Sim PK & GI table", "Safe Space Estimates",
    "Safe Space Plots A", "Safe Space Plots B", "Safe Space Plots C",
)
DIAG_ERR_SEALED_LEN_FMT     = "Sealed record holds {size} bytes, expected {expected}"
DIAG_ERR_SEALED_INVALID     = "Sealed record does not decrypt (wrong Tamper Log Key or another firmware format)"
DIAG_ERR_NO_PAYLOAD         = "No -----BEGIN KEY DIAG----- / -----END KEY DIAG----- block found"
DIAG_ERR_PAYLOAD_INVALID    = "Payload does not decrypt (wrong Diag Report Key, damaged text, or another format)"
DIAG_ERR_NO_REPORT_KEY_FMT  = "Diag Report Key not found: {path}. Run generate_diag_report_key.py first."
