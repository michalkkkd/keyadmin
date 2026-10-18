"""
Test algorithm runner module.
Implements reference computation (adding two numbers) under full dongle security
(user hash check, VRX token, and license expiration).
"""

from keycomm.core.base_runner import BaseRunner
from keycomm.core.transport import MSG_TEST_ADD
from keycomm.core.constants import (
    CHAR_ENCODING_UTF8,
    PAYLOAD_TEST_ADD_FMT,
)


class TestAddRunner(BaseRunner):
    """
    Runner for test addition computations on the secure hardware dongle.
    Inherits from BaseRunner to unify timing, throughput measurement, and logging.
    """
    def __init__(self, rpc, user_hash: int, vrx_token: int = 0):
        super().__init__(rpc)
        self.user_hash = int(user_hash)
        self.vrx_token = int(vrx_token)
        self._result_str = ""

    def pre_execute(self, a: float, b: float, *args, **kwargs):
        pass

    def execute_send(self, a: float, b: float, *args, **kwargs):
        payload = PAYLOAD_TEST_ADD_FMT.format(
            user_hash=self.user_hash,
            a=int(a),
            b=int(b)
        ).encode(CHAR_ENCODING_UTF8)
        self.total_bytes_sent = len(payload)
        self._result_str = self.rpc.execute_command(MSG_TEST_ADD, payload, timeout_sec=5.0)

    def execute_process(self, a: float, b: float, *args, **kwargs):
        pass

    def execute_receive(self, a: float, b: float, *args, **kwargs) -> str:
        return self._result_str

    def post_execute(self, final_result: str):
        pass

    def validate_result(self, final_result: str):
        pass
