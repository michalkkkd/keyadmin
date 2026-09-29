from core.protocol import RpcProtocol

class AdminApi:
    """Warstwa biznesowa dla komend administracyjnych"""
    def __init__(self, rpc: RpcProtocol, admin_pin: str = '1234'):
        self.rpc = rpc
        self.pin = admin_pin

    def update_current_date(self, unix_timestamp: int) -> str:
        return self.rpc.execute_command(f'ADMIN_DATE {unix_timestamp} {self.pin}')
        
    def set_license_days(self, days: int) -> str:
        return self.rpc.execute_command(f'ADMIN_LIC {days} {self.pin}')
        
    def wipe_device(self) -> str:
        return self.rpc.execute_command(f'ADMIN_WIPE {self.pin}')
