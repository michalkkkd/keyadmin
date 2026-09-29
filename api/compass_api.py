from core.protocol import RpcProtocol
from core.transport import MSG_CHECK_LIC, MSG_ADMIN_DATE, MSG_ADMIN_LIC, MSG_ADMIN_WIPE, MSG_COMPASS_ALG1

class CompassApi:
    def __init__(self, rpc: RpcProtocol):
        self.rpc = rpc

    def check_license(self) -> str:
        return self.rpc.execute_command(MSG_CHECK_LIC)

    def admin_set_date(self, timestamp: int, pin: str) -> str:
        # Przesylamy payload binarno/tekstowy - np. "1790709332 1234" tak samo jak uzywal sscanf
        payload = f"{timestamp} {pin}".encode('utf-8')
        return self.rpc.execute_command(MSG_ADMIN_DATE, payload)

    def admin_set_license(self, days: int, pin: str) -> str:
        payload = f"{days} {pin}".encode('utf-8')
        return self.rpc.execute_command(MSG_ADMIN_LIC, payload)

    def admin_wipe(self, pin: str) -> str:
        payload = pin.encode('utf-8')
        return self.rpc.execute_command(MSG_ADMIN_WIPE, payload)

    def calculate_algorithm_1(self, a: int, b: int) -> str:
        payload = f"{a} {b}".encode('utf-8')
        return self.rpc.execute_command(MSG_COMPASS_ALG1, payload)
