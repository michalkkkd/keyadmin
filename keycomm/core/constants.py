"""
Centralized constants for KeySec keycomm module.
Defines message IDs, response prefixes, cryptographic labels,
transport parameters, and protocol strings as a Single Source of Truth.
"""

# ==============================================================================
# Communication & Business Algorithm Command IDs
# ==============================================================================
MSG_LOG                 = 0x00
MSG_PING                = 0x01
MSG_CHECK_LIC           = 0x02
MSG_TEST_ADD            = 0x06
MSG_COMPASS_USERS       = 0x09
MSG_HANDSHAKE_INIT      = 0x0D
MSG_SYS_HEALTH          = 0x10
MSG_DIAG_BEGIN          = 0x13   # DIAG stream: plaintext commands, the dongle returns ciphertext only
MSG_DIAG_DATA           = 0x14
MSG_DIAG_NEXT           = 0x17
MSG_GET_LOG_SIZE        = 0x11
MSG_GET_LOG_CHUNK       = 0x12
MSG_VRX                 = 0x16

MSG_SIM_PK_GI_INIT      = 0x30
MSG_SIM_PK_GI_CHUNK     = 0x31
MSG_SIM_PK_GI_PROCESS   = 0x32
MSG_SIM_PK_GI_READ      = 0x33

MSG_SAFE_SPACE_INIT     = 0x40
MSG_SAFE_SPACE_CHUNK    = 0x41
MSG_SAFE_SPACE_PROCESS  = 0x42
MSG_SAFE_SPACE_READ     = 0x43
MSG_SAFE_SPACE_RESET    = 0x44
MSG_SAFE_SPACE_FINISH   = 0x45

MSG_SSP_A_INIT          = 0x50
MSG_SSP_A_CHUNK         = 0x51
MSG_SSP_A_PROCESS       = 0x52
MSG_SSP_A_READ          = 0x53
MSG_SSP_B_REQ           = 0x54
MSG_SSP_C_INIT          = 0x55
MSG_SSP_C_CHUNK         = 0x56
MSG_SSP_C_PROCESS       = 0x57
MSG_SSP_C_READ          = 0x58

# Responses
MSG_OK                  = 0x80
MSG_ERR                 = 0x81

# Command IDs that require end-to-end encryption via SecureChannel
SECURE_CMD_IDS = (
    MSG_CHECK_LIC, MSG_TEST_ADD, MSG_COMPASS_USERS,
    MSG_GET_LOG_SIZE, MSG_GET_LOG_CHUNK, 0x15, MSG_VRX,
    0x20, 0x21, 0x22,
    MSG_SIM_PK_GI_INIT, MSG_SIM_PK_GI_CHUNK, MSG_SIM_PK_GI_PROCESS, MSG_SIM_PK_GI_READ,
    MSG_SAFE_SPACE_INIT, MSG_SAFE_SPACE_CHUNK, MSG_SAFE_SPACE_PROCESS, MSG_SAFE_SPACE_READ,
    MSG_SAFE_SPACE_RESET, MSG_SAFE_SPACE_FINISH,
    MSG_SSP_A_INIT, MSG_SSP_A_CHUNK, MSG_SSP_A_PROCESS, MSG_SSP_A_READ,
    MSG_SSP_B_REQ,
    MSG_SSP_C_INIT, MSG_SSP_C_CHUNK, MSG_SSP_C_PROCESS, MSG_SSP_C_READ
)

# ==============================================================================
# General Encoding, Enums, and Delimiters
# ==============================================================================
CHAR_ENCODING_UTF8          = "utf-8"
ERRORS_IGNORE               = "ignore"
BYTEORDER_LITTLE            = "little"
BYTEORDER_BIG               = "big"
EMPTY_BYTES                 = b""
TOKEN_OK                    = "OK"
TOKEN_ERR                   = "ERR"
TOKEN_TIMEOUT               = "Timeout"

ATTR_IS_OPEN                = "is_open"
ATTR_THREAD                 = "thread"
ATTR_HEARTBEAT_THREAD       = "heartbeat_thread"
ATTR_SER                    = "ser"

# ==============================================================================
# Protocol Response Strings and Tokens
# ==============================================================================
RESP_OK_PREFIX              = f"{TOKEN_OK}: "
RESP_ERR_PREFIX             = f"{TOKEN_ERR}: "
RESP_UNKNOWN_PREFIX         = "UNKNOWN: "
RESP_FIRE_AND_FORGET        = f"{TOKEN_OK}: FIRE_AND_FORGET"
RESP_EOF                    = "EOF"
RESP_MISSING_PREFIX         = "MISSING:"
RESP_PONG_BYTES             = b"PONG"
RESP_SYNC_BYTES             = b"SYNC"
RESP_REQ_BYTES              = b"REQ"
DUMMY_PAYLOAD_BYTE          = b"X"

# Diagnostic / Handshake Error Signatures from MCU
MCU_ERR_DECRYPT_FAILED      = f"{TOKEN_ERR}: Decrypt Failed"
MCU_ERR_LIC_EXPIRED         = "License expired"
MCU_ERR_SESSION_INACTIVE    = "Secure Session Not Active"
MCU_ERR_DECRYPTION_FAILED   = "Decryption Failed"

# ==============================================================================
# Cryptographic Labels & Flags
# ==============================================================================
HKDF_CLIENT_INFO            = b"KEYSEC_CLIENT_WRITE_KEY_V1"
HKDF_SERVER_INFO            = b"KEYSEC_SERVER_WRITE_KEY_V1"
HOST_AUTH_LABEL             = b"KEYSEC_HOST_AUTH_V1"

NONCE_DIR_HOST_TO_DEVICE    = 0x01
NONCE_DIR_DEVICE_TO_HOST    = 0x02

ROOT_CA_FILENAME            = "root_ca_pub.pem"

# ==============================================================================
# Hardware / USB / Serial Defaults
# ==============================================================================
TARGET_VID                  = 0x2886  # Seeed Studio
TARGET_PID                  = 0x0062  # Seeed XIAO MG24
DEFAULT_BAUDRATE            = 921600
TF_ID_BYTES                 = 1
TF_CKSUM_TYPE               = "crc32"

# ==============================================================================
# Error Messages
# ==============================================================================
ERR_DONGLE_NOT_FOUND    = "KeySec Dongle (VID=0x2886, PID=0x0062) not found on any USB port! Check USB connection."
ERR_ROOT_CA_NOT_FOUND   = "Root CA public key (root_ca_pub.pem) not found!"
ERR_SECURE_NOT_ESTABLISHED = "Secure session not established"
ERR_COUNTER_EXHAUSTED   = "Nonce counter exhausted: re-handshake required"
ERR_PAYLOAD_TOO_SHORT   = "Encrypted payload too short"
ERR_NO_EMAIL            = f"{TOKEN_ERR}: User email address not provided - operation blocked."
ERR_NO_PONG             = "[Transport] No response to PING (MCU is asleep or unresponsive!)"
ERR_RX_TOO_MANY_ERRORS  = "[Transport] Too many RX errors, closing worker thread."
ERR_DEVICE_DISCONNECTED = "Device is disconnected"
ERR_FMT_WRITE_FAILED    = "Write failed: {e}"

# ==============================================================================
# CompassApi Logging & Protocols
# ==============================================================================
LOGGER_NAME_KEYCOMM_API     = "keycomm.api"
LOG_FMT_CHECK_LICENSE       = "[CompassApi] check_license | user_email='{email}' | user_hash={user_hash} | valid={valid} | received_vrx_token={token}"
LOG_FMT_VRX                 = "[CompassApi] vrx | user_email='{email}' | user_hash={user_hash} | sent_vrx_token={token} | status={status}"
LOG_FMT_VRX_REJECTED        = "[CompassApi] VRX token verification rejected by MCU: {res}"
STATUS_OK                   = "OK"
STATUS_FAILED_FMT           = "FAILED ({res})"
PAYLOAD_ALG1_FMT            = "{user_hash} {a} {b}"
PAYLOAD_TEST_ADD_FMT        = PAYLOAD_ALG1_FMT

# ==============================================================================
# License Result Regex & Tokens
# ==============================================================================
RE_DAYS_PASSED              = r"Days passed:\s*(\d+)"
RE_REMAINING_DAYS           = r"Remaining:\s*(\d+)"
RE_VRX_TOKEN                = r"VRX:([0-9a-zA-Z]+)"
TOKEN_VALID                 = "VALID"
TOKEN_EXPIRED               = "EXPIRED"
TOKEN_RTC_NOT_SYNCHRONIZED  = "RTC NOT SYNCHRONIZED"
TOKEN_NO_RTC                = "NO_RTC"
TOKEN_NO_LICENSE            = "NO LICENSE"
TOKEN_NO_LICENSE_UNDERSCORE = "NO_LICENSE"
TOKEN_FAIL                  = "FAIL"

# ==============================================================================
# Logic & Domain Names
# ==============================================================================
MEDIUM_FASSGF               = "FaSSGF"
MEDIUM_FASSIF               = "FaSSIF"
COL_MEDIUM                  = "Medium"
COL_TIME                    = "Time"
COL_AMOUNT                  = "Amount_%"
COL_TLAG                    = "tlag"
COL_CS_FACT                 = "Cs_fact"
COL_Z_FACT                  = "z_fact"
COL_FORMULATION             = "Formulation"
COL_TLAG_CHANGE             = "tlag_change"
COL_MIN                     = "min"
COL_MAX                     = "max"
VAL_TLAG_CHANGE_NO          = "NO"
VAL_NAN                     = "nan"
CONF_APP_CONF               = "app_conf"
CONF_PLOT_CONF              = "plot_conf"
CONF_SAFE_SPACE_DATA        = "safe_space_data"
CONF_DISSO_MODE             = "disso_mode"
DISSO_MODE_FULL             = "full"
CONF_SFSP_FASSGF            = "sfsp_FaSSGF"
CONF_SFSP_FASSIF            = "sfsp_FaSSIF"
CONF_SSD_CSS                = "ssd_CsS"
CONF_SSD_CSI                = "ssd_CsI"
CONF_SSD_ZS                 = "ssd_zS"
CONF_SSD_ZI                 = "ssd_zI"
CONF_SSD_TLAG               = "ssd_tlag"
CONF_SSD_TLAGI              = "ssd_tlagI"
COL_COLUMNS                 = "columns"
COL_DATA                    = "data"
STAGE_A                     = "A"
STAGE_C                     = "C"
JSON_KEY_EDGE_ALL           = "edge_all"
JSON_KEY_EDGE_IN            = "edge_in"

# Logic Error & Information Messages
ERR_DATA_DICT_REQUIRED      = "data_dict must be provided to SimPkGiRunner"
ERR_FMT_INIT_FAILED         = "Init failed: {res}"
ERR_FMT_PROCESS_INVALID_LEN = "Process returned invalid length: {res}"
ERR_FMT_DEVICE_RESET_FAILED = "Device reset failed: {res}"
ERR_FMT_DATA_CORRUPTION     = "Data corruption! MCU received {mcu_rows} rows, but we sent {total_rows}."
ERR_FINAL_JSON_EMPTY        = "final_json is completely empty! C code returned EOF on offset 0!"
ERR_FMT_INIT_A_FAILED       = "Init A failed: {res}"
ERR_FMT_INIT_C_FAILED       = "Init C failed: {res}"
ERR_FMT_REQ_B_FAILED        = "Req B failed: {res}"
ERR_EMPTY_RESULT_A          = "Empty result from MCU in safe_space_plots_A"
ERR_EMPTY_RESULT_C          = "Empty result C in safe_space_plots_C"

# ==============================================================================
# ChunkStreamer Messages & Formats
# ==============================================================================
ERR_FMT_CHUNK_FAILED        = "Chunk failed: {res}"
ERR_FMT_MAX_CHUNKS          = (
    "[ChunkStreamer] Payload size ({payload_size} bytes) requires {total_chunks} chunks, "
    "which exceeds the maximum device limit of 256 chunks (~384 KB). "
    "Please reduce payload size or increase chunk_size."
)
ERR_FMT_PROCESS_FAILED      = "Process failed (cmd 0x{cmd:02X}): {res}"
ERR_FMT_RESOLVE_MISSING_FAILED = "Failed to resolve missing chunks for command 0x{cmd:02X} after {max_retries} retries"
ERR_FMT_FINAL_READ_FAILED   = "Final read failed at offset {offset}: {chunk_res}"
ERR_FMT_READ_STALLED        = "Read stalled at offset {offset}: received empty chunk without EOF"
LOG_FMT_MISSING_CHUNKS      = "[ChunkStreamer] Missing chunks reported by MCU ({missing_indices}). Re-streaming attempt {attempt}/{max_retries}..."

# ==============================================================================
# Transport, Protocol & SecureChannel Logs & Formats
# ==============================================================================
LOG_FMT_PORT_OPENED         = "[Transport] Port opened: {port}"
LOG_FMT_ASYNC_MCU           = "[!] ASYNC MCU LOG: {log_str}"
LOG_FMT_RX_ERROR            = "[Transport] RX Error: {e}"
LOG_SYNCING                 = "[Transport] Synchronizing with microcontroller..."
LOG_SYNCED                  = "[Transport] Synchronized with MCU (TinyFrame)!"
LOG_FMT_NO_PONG             = "[Transport] No PONG. Retransmitting PING {attempt}/3..."
LOG_FMT_TIMEOUT_CLEANUP     = "[Transport] Timeout! Cleaned up stale listener for ID {frame_id}: {popped}"
LOG_FMT_FLUSH_ERROR         = "[Transport] Non-fatal error flushing buffer: {e}"
LOG_FMT_CLOSE_ERROR         = "[Transport] Non-fatal error closing serial port: {e}"
LOG_FMT_SENDING             = "[Protocol] Sending ID: 0x{cmd:02X}, Length: {len}"
LOG_FMT_MCU                 = "   [MCU] {text}"
LOG_FMT_CORRUPTED_CRC       = "[Protocol] Packet corrupted (CRC). Retransmission {attempt}/{max_retries}..."
LOG_FMT_SESSION_ERROR       = "[Protocol] Session error detected ({data_str}), triggering auto re-handshake..."
LOG_FMT_DECRYPT_FAIL        = "[Protocol] Response decryption failed ({e}), triggering auto re-handshake..."
ERR_FMT_DECRYPT_FAILED      = "Decryption Failed - {err}"
ERR_FMT_TIMEOUT_RETRIES     = "Timeout after {retries} retries"
ERR_SECURE_SESSION_UNAVAILABLE = "Secure session unavailable (handshake failed), command not sent"
ERR_FMT_UNEXPECTED_RESP_TYPE   = "Unexpected response type 0x{type:02X} for a secure command"
TIMESTAMP_FMT               = "%Y-%m-%d %H:%M:%S"
RE_SYNC_ELAPSED             = r'Elapsed since sync:\s*(\d+)'
SYNC_ELAPSED_FMT            = 'Elapsed since sync: {h} h {m} m'

LOG_FMT_ROOT_CA_NOT_FOUND   = "[-] Root CA key not found at {path}"
LOG_HANDSHAKE_INIT          = "[SecureChannel] Sending Handshake Init..."
LOG_HANDSHAKE_NO_RESP       = "[-] Handshake Failed: No response from MCU"
LOG_FMT_HANDSHAKE_MCU_ERR   = "[-] Handshake Failed on MCU side. Error: {err}"
LOG_HANDSHAKE_INVALID_LEN   = "[-] Invalid handshake response length"
LOG_HANDSHAKE_SIG_MISMATCH  = "[-] Signature length mismatch"
LOG_FMT_MCU_EPH_KEY         = "[SecureChannel] MCU Eph Key: {key_hex}..."
LOG_FMT_MCU_ID_KEY          = "[SecureChannel] MCU ID Key: {key_hex}..."
LOG_FMT_CERT_SIZE           = "[SecureChannel] Cert Size: {size} bytes"
LOG_CERT_VERIFIED           = "[+] Device Certificate VERIFIED. Authentic Dongle detected."
LOG_CERT_INVALID            = "[-] Device Certificate INVALID. Counterfeit Dongle!"
LOG_SIG_VERIFIED            = "[+] Handshake Signature VERIFIED. MitM protection active."
LOG_SIG_INVALID             = "[-] Handshake Signature INVALID. Possible Man-in-the-Middle Attack!"
LOG_SESSION_ESTABLISHED     = "[+] Secure Session Established! (AES-256-GCM Dual-Key HKDF)"
ERR_FMT_REPLAY_ATTACK       = "Replay attack detected: counter {incoming} <= last seen {last_seen}"

LOG_AUTODETECTING           = "[*] Auto-detecting Dongle COM port..."
LOG_DONGLE_NOT_FOUND        = "[-] FATAL: Could not find KeySec Dongle plugged into USB!"
LOG_FMT_FOUND_DONGLE        = "[+] Found Dongle on port: {port}"
LOG_ROOT_CA_NOT_FOUND       = "[-] FATAL: Root CA public key (root_ca_pub.pem) not found!"
LOG_FMT_SESSION_ESTABLISHED = "[+] Secure Session Established! Handshake took: {ms:.2f} ms"
LOG_ADMIN_UNENCRYPTED_NOTICE = "[*] Notice: Secure ECDHE session not active (unprovisioned device or provisioning firmware). Admin API available."
LOG_HANDSHAKE_FATAL         = "[-] FATAL: Failed to establish secure ECDHE channel."
LOG_FMT_CONNECT_ERROR       = "[-] FATAL: Could not connect to Dongle on {port}: {e}"
LOG_FMT_TRANSPORT_CLOSE_ERROR = "[-] Warning: Failed to close transport cleanly on error: {err}"

# ==============================================================================
# Dongle diagnostics (keycomm.diag): the PC collects its facts and sends them to the dongle, which encrypts
# them together with its own data (KeyFirmware src/core/diag_record.h). The PC encrypts and judges nothing.
# ==============================================================================
DIAG_TOOL_VERSION           = 4
KEYCOMM_VERSION             = "1.2.0"
DIAG_STREAM_CHUNK           = 640              # max PC bytes per MSG_DIAG_DATA (firmware DIAG_STREAM_CHUNK)
DIAG_STREAM_MAX_STEPS       = 64               # safety stop for MSG_DIAG_NEXT
DIAG_STREAM_ATTEMPTS        = 3                # a lost reply restarts the whole stream
DIAG_FLAG_FINAL             = "01"
DIAG_ERR_STREAM_FMT         = "DIAG stream failed: {reply}"
DIAG_HANDSHAKE_REJECTED     = "rejected"
DIAG_ERROR_FMT              = "{type}: {error}"
DIAG_ARMOR_BEGIN            = "-----BEGIN KEY DIAG-----"
DIAG_ARMOR_END              = "-----END KEY DIAG-----"
DIAG_ARMOR_LINE_LEN         = 64

# PC facts (JSON keys); the dongle stores them as received
DIAG_KEY_TOOL               = "tool"
DIAG_KEY_TIME               = "time"
DIAG_KEY_UTC                = "utc"
DIAG_KEY_PC                 = "pc"
DIAG_KEY_PORTS              = "ports"
DIAG_KEY_PROCESSES          = "processes"
DIAG_KEY_USB                = "usb"
DIAG_KEY_ROOT_CA            = "root_ca"        # found next to the program
DIAG_KEY_HANDSHAKE          = "handshake"      # "" = session open, else what went wrong
DIAG_KEY_LINK               = "link"           # RpcProtocol counters after the run
DIAG_KEY_APP                = "app"

# PC facts (pc_info_collector.py)
DIAG_PORT_FMT               = "{device} {vid}:{pid} {description} | {manufacturer} | SER={serial} LOC={location} | {hwid}"
# Process names worth reporting (may hold the COM port): image names matched case-insensitively
DIAG_PROCESS_PATTERN        = r"compass|python|keyadmin|putty|tera|realterm|arduino|simplicity|commander|serial|coolterm|hterm|termite|pyocd|jlink"
DIAG_TASKLIST_CMD           = ["tasklist", "/FO", "CSV", "/NH"]
DIAG_USB_DRIVER_PS          = ("Get-CimInstance Win32_PnPSignedDriver -Filter \"DeviceID like 'USB\\\\VID_{vid:04X}&PID_{pid:04X}%'\" | "
                               "Select-Object DeviceID,DeviceName,DriverProviderName,DriverVersion,DriverDate,InfName | ConvertTo-Json -Compress")
DIAG_SUBPROCESS_TIMEOUT_S   = 15
DIAG_EXE_HASH_CHUNK         = 1 << 20
DIAG_FP_HEX_LEN             = 16

# What the customer sees (the three messages without a payload carry nothing the customer cannot see)
DIAG_HEADER_FMT             = "KEY DIAG {version} | {timestamp}"
DIAG_SEND_HINT              = "Send the text below (or the report file) to support:"
DIAG_MSG_NO_DONGLE          = "The key was not found. Plug it in (data cable, no hub if possible) and run again."
DIAG_MSG_PORT_FMT           = "The key cannot be opened ({error}). Close Compass and any program using it, then run again."
DIAG_MSG_NO_REPLY_FMT       = "The key does not answer ({error}). Unplug it, plug it in again and run again."
DIAG_REPORT_SAVED_FMT       = "REPORT: {path}"
DIAG_REPORT_FILE_FMT        = "key_diag_{stamp}.txt"
DIAG_TIMESTAMP_FMT          = "%Y-%m-%d %H:%M:%S"
DIAG_FILE_STAMP_FMT         = "%Y%m%d_%H%M%S"
