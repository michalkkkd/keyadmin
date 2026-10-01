from core.protocol import RpcProtocol
from core.transport import MSG_CHECK_LIC, MSG_COMPASS_ALG1

class CompassApi:
    def __init__(self, rpc: RpcProtocol):
        self.rpc = rpc

    def check_license(self) -> str:
        return self.rpc.execute_command(MSG_CHECK_LIC)

    def calculate_algorithm_1(self, user_hash: int, a: int, b: int) -> str:
        payload = f"{user_hash} {a} {b}".encode('utf-8')
        return self.rpc.execute_command(MSG_COMPASS_ALG1, payload, timeout_sec=0.5)

    def get_max_users(self) -> str:
        from core.transport import MSG_COMPASS_USERS
        return self.rpc.execute_command(MSG_COMPASS_USERS)


