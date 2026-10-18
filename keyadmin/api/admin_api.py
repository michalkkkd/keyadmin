from keycomm.core.protocol import RpcProtocol
from keycomm.core.chunk_streamer import ChunkStreamer
from keycomm.api.license_result import LicenseResult
from keycomm.api.license_state import LicenseState

from keyadmin.api.system_health_report import SystemHealthReport
from keyadmin.core.constants import (
    MSG_ADMIN_DATE,
    MSG_ADMIN_LIC,
    MSG_ADMIN_WIPE,
    MSG_DEBUG_TIME,
    MSG_ADMIN_USERS,
    MSG_MEM_INFO,
    MSG_PROVISION_IDENTITY,
    MSG_SAVE_CERTIFICATE,
    MSG_BATTERY_INFO,
    MSG_NVM_DIAG,
    MSG_SYS_HEALTH,
    MSG_GET_LOG_COUNT,
    MSG_GET_LOG_LINE,
    ADMIN_ERR_LOG_SIZE_FAIL,
    ADMIN_MSG_NO_LOGS,
    ADMIN_MSG_FETCHING_LOGS_FMT,
    ADMIN_ERR_FETCH_LOGS_FMT,
    ADMIN_LOG_REQ_PAYLOAD,
    ADMIN_LOG_LINE_FMT,
    RESP_OK_PREFIX_STR,
    CHAR_ENCODING_UTF8,
    LINE_DELIMITER_LF,
    STRUCT_FMT_UINT32_LE,
)


class AdminApi:
    """Business layer for administrative commands on the KeyFirmware dongle."""
    def __init__(self, rpc: RpcProtocol):
        self.rpc = rpc

    def update_current_date(self, unix_timestamp: int) -> str:
        payload = f"{unix_timestamp}".encode(CHAR_ENCODING_UTF8)
        return self.rpc.execute_command(MSG_ADMIN_DATE, payload)

    def set_license_days(self, days: int) -> str:
        payload = f"{days}".encode(CHAR_ENCODING_UTF8)
        return self.rpc.execute_command(MSG_ADMIN_LIC, payload)

    def wipe_device(self) -> str:
        return self.rpc.execute_command(MSG_ADMIN_WIPE)

    def debug_time(self) -> str:
        import time
        import struct
        payload = struct.pack(STRUCT_FMT_UINT32_LE, int(time.time()))
        return self.rpc.execute_command(MSG_DEBUG_TIME, payload)

    def set_max_users(self, users: int) -> str:
        payload = f"{users}".encode(CHAR_ENCODING_UTF8)
        return self.rpc.execute_command(MSG_ADMIN_USERS, payload)

    def get_memory_info(self) -> str:
        return self.rpc.execute_command(MSG_MEM_INFO)

    def provision_identity(self) -> str:
        return self.rpc.execute_command(MSG_PROVISION_IDENTITY, timeout_sec=5.0)

    def save_certificate(self, cert_bytes: bytes) -> str:
        return self.rpc.execute_command(MSG_SAVE_CERTIFICATE, cert_bytes, timeout_sec=3.0)

    def get_nvm_diagnostics(self) -> str:
        return self.rpc.execute_command(MSG_NVM_DIAG)

    def get_system_health(self) -> SystemHealthReport:
        res = self.rpc.execute_command(MSG_SYS_HEALTH)
        return SystemHealthReport(res)

    def get_battery_info(self) -> str:
        return self.rpc.execute_command(MSG_BATTERY_INFO)

    def print_all_logs(self):
        try:
            res = self.rpc.execute_command(MSG_GET_LOG_COUNT, ADMIN_LOG_REQ_PAYLOAD)
            total_size = int(res.replace(RESP_OK_PREFIX_STR, '').strip())
        except Exception:
            print(ADMIN_ERR_LOG_SIZE_FAIL)
            return

        if total_size == 0:
            print(ADMIN_MSG_NO_LOGS)
            return

        print(ADMIN_MSG_FETCHING_LOGS_FMT.format(total_size=total_size))

        streamer = ChunkStreamer(self.rpc)
        try:
            full_text = streamer.receive_payload(MSG_GET_LOG_LINE, expected_len=total_size, timeout_sec=2.0)
        except Exception as e:
            print(ADMIN_ERR_FETCH_LOGS_FMT.format(e=e))
            return

        lines = [l for l in full_text.split(LINE_DELIMITER_LF) if l.strip()]
        for i, line in enumerate(lines):
            print(ADMIN_LOG_LINE_FMT.format(idx=i+1, total=len(lines), line=line))

