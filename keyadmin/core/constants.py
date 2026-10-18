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

# Menu Action Item Labels
ADMIN_ACT_SYS_HEALTH   = "System Health & Anti-Tamper Check"
ADMIN_ACT_BATTERY      = "Battery Status & Capacity (Li-Po)"
ADMIN_ACT_MEMORY       = "Memory & NVM3 Diagnostics"
ADMIN_ACT_RTC          = "Detailed Global RTC Diagnostics"
ADMIN_ACT_LICENSE      = "Check License & User Limits"
ADMIN_ACT_LOGS         = "View Async Device Logs"
ADMIN_ACT_BENCHMARK    = "Run Performance Benchmark (Algorithm Test)"
ADMIN_ACT_HB_START     = "Start sending heartbeat"
ADMIN_ACT_HB_DISABLE   = "Disable heartbeat for 20 seconds"
ADMIN_ACT_EXIT         = "Exit"

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
ADMIN_MSG_HB_EXPLANATION    = "[INFO] The MCU requires PING every 3s. Without it, it will timeout (~5s) and enter EM2 sleep."
ADMIN_MSG_HB_WAITING        = "[INFO] Waiting 20 seconds..."
ADMIN_MSG_HB_ASLEEP         = "[INFO] MCU should be deeply asleep now."
ADMIN_MSG_HB_VERIFY_WAKE    = "[INFO] Sending a manual command to verify Wake-on-RX works..."
ADMIN_DEFAULT_USER_EMAIL     = "admin_test@compass.com"
ADMIN_BENCHMARK_ITERATIONS   = 100000
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
RE_BLACKBOX                 = r"BlackBox:\s*([A-Za-z0-9_-]+)"
BLACKBOX_STATE_NONE         = "NONE"
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

