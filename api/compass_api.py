from core.protocol import RpcProtocol

class CompassApi:
    """Warstwa biznesowa dla obliczen"""
    def __init__(self, rpc: RpcProtocol):
        self.rpc = rpc

    def check_license(self) -> str:
        """Sprawdza stan licencji (wymaga aktywnej licencji na kluczu)"""
        return self.rpc.execute_command('CHECK_LIC')
        
    def calculate_algorithm_1(self, param1: int, param2: int) -> str:
        """Przyklad wywolania jednego z 5 ukrytych algorytmow"""
        return self.rpc.execute_command(f'COMPASS_ALG1 {param1} {param2}')
