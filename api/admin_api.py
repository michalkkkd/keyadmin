from core.protocol import RpcProtocol
from core.transport import MSG_ADMIN_DATE, MSG_ADMIN_LIC, MSG_ADMIN_WIPE, MSG_DEBUG_TIME

class AdminApi:
    """Warstwa biznesowa dla komend administracyjnych"""
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
