"""
Dummy stub for SimPkGiRunner.
Empty implementation for public distribution or interface mock.
"""

from keycomm.core.base_runner import BaseRunner


class SimPkGiRunner(BaseRunner):
    """
    Dummy SimPkGiRunner. Does not execute computations.
    """
    def __init__(self, rpc_client=None, user_hash: int = 0, vrx_token: int = 0):
        super().__init__(rpc_client)
        self.user_hash = user_hash
        self.vrx_token = int(vrx_token)

    def pre_execute(self, *args, **kwargs):
        pass

    def execute_send(self, *args, **kwargs):
        pass

    def execute_process(self, *args, **kwargs):
        pass

    def execute_receive(self, *args, **kwargs) -> str:
        return ""
