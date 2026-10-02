from core.protocol import RpcProtocol
from core.transport import MSG_ADMIN_DATE, MSG_ADMIN_LIC, MSG_ADMIN_WIPE, MSG_DEBUG_TIME, MSG_ADMIN_USERS

class AdminApi:
    """Business layer for administrative commands"""
    def __init__(self, rpc: RpcProtocol, admin_pin: str = '1234'):
        self.rpc = rpc
        self.pin = admin_pin

    def update_current_date(self, unix_timestamp: int) -> str:
        payload = f"{unix_timestamp} {self.pin}".encode('utf-8')
        return self.rpc.execute_command(MSG_ADMIN_DATE, payload)
        
    def set_license_days(self, days: int) -> str:
        payload = f"{days} {self.pin}".encode('utf-8')
        return self.rpc.execute_command(MSG_ADMIN_LIC, payload)
        
    def wipe_device(self) -> str:
        payload = self.pin.encode('utf-8')
        return self.rpc.execute_command(MSG_ADMIN_WIPE, payload)

    def debug_time(self) -> str:
        import time
        import struct
        payload = struct.pack('<I', int(time.time()))
        return self.rpc.execute_command(MSG_DEBUG_TIME, payload)

    def set_max_users(self, users: int) -> str:
        payload = f"{users} {self.pin}".encode('utf-8')
        return self.rpc.execute_command(MSG_ADMIN_USERS, payload)

    def get_memory_info(self) -> str:
        from core.transport import MSG_MEM_INFO
        return self.rpc.execute_command(MSG_MEM_INFO)

    def provision_identity(self) -> str:
        from core.transport import MSG_PROVISION_IDENTITY
        payload = self.pin.encode('utf-8')
        return self.rpc.execute_command(MSG_PROVISION_IDENTITY, payload, timeout_sec=5.0)

    def save_certificate(self, cert_bytes: bytes) -> str:
        from core.transport import MSG_SAVE_CERTIFICATE
        payload = self.pin.encode('utf-8') + b" " + cert_bytes
        return self.rpc.execute_command(MSG_SAVE_CERTIFICATE, payload, timeout_sec=3.0)
    def get_nvm_diagnostics(self) -> str:
        from core.transport import MSG_NVM_DIAG
        return self.rpc.execute_command(MSG_NVM_DIAG)
    def get_system_health(self) -> str:
        from core.transport import MSG_SYS_HEALTH
        return self.rpc.execute_command(MSG_SYS_HEALTH)
