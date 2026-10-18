import json
import logging
import zlib

from keycomm.core.protocol import RpcProtocol
from keycomm.core.constants import (
    MSG_CHECK_LIC, MSG_TEST_ADD, MSG_COMPASS_USERS, MSG_VRX,
    RESP_REQ_BYTES, ERR_NO_EMAIL,
    CHAR_ENCODING_UTF8, BYTEORDER_LITTLE, TOKEN_OK, STATUS_OK,
    STATUS_FAILED_FMT, LOGGER_NAME_KEYCOMM_API,
    LOG_FMT_CHECK_LICENSE, LOG_FMT_VRX, LOG_FMT_VRX_REJECTED,
    PAYLOAD_ALG1_FMT
)
from keycomm.api.license_result import LicenseResult
from keycomm.logic.safe_space_estimates import SafeSpaceEstimatesRunner
from keycomm.logic.safe_space_plots import (
    execute_safe_space_plots_A,
    execute_safe_space_plots_B,
    execute_safe_space_plots_C,
)
from keycomm.logic.sim_pk_gi import SimPkGiRunner
from keycomm.logic.test_add import TestAddRunner

logger = logging.getLogger(LOGGER_NAME_KEYCOMM_API)


class CompassApi:
    def __init__(self, rpc: RpcProtocol, user_email: str = ""):
        self.rpc = rpc
        self.last_vrx_token = 0
        self.set_user_email(user_email)

    def set_user_email(self, user_email: str = "") -> None:
        self.user_email = (user_email or "").strip()
        if self.user_email:
            computed_hash = zlib.crc32(self.user_email.encode(CHAR_ENCODING_UTF8)) & 0xFFFFFFFF
            self.user_hash = computed_hash if computed_hash != 0 else 1
        else:
            self.user_hash = 0

    def check_license(self) -> LicenseResult:
        payload = self.user_hash.to_bytes(4, byteorder=BYTEORDER_LITTLE)
        res = self.rpc.execute_command(MSG_CHECK_LIC, payload)
        result = LicenseResult(res)
        self.last_vrx_token = result.vrx_token
        logger.info(
            LOG_FMT_CHECK_LICENSE.format(
                email=self.user_email,
                user_hash=self.user_hash,
                valid=bool(result),
                token=self.last_vrx_token
            )
        )
        return result

    def get_license_status(self) -> LicenseResult:
        return self.check_license()

    def vrx(self, vrx_token: int) -> bool:
        token = int(vrx_token)
        self.last_vrx_token = 0
        payload = self.user_hash.to_bytes(4, byteorder=BYTEORDER_LITTLE) + token.to_bytes(4, byteorder=BYTEORDER_LITTLE)
        res = self.rpc.execute_command(MSG_VRX, payload)
        ok = TOKEN_OK in res
        status_str = STATUS_OK if ok else STATUS_FAILED_FMT.format(res=res)
        logger.info(
            LOG_FMT_VRX.format(
                email=self.user_email,
                user_hash=self.user_hash,
                token=token,
                status=status_str
            )
        )
        if not ok:
            logger.warning(LOG_FMT_VRX_REJECTED.format(res=res))
        return ok

    def get_max_users(self) -> str:
        res = self.rpc.execute_command(MSG_COMPASS_USERS, RESP_REQ_BYTES)
        return res

    def execute_test_add(self, a: float, b: float, vrx_token: int = 0, silent: bool = False) -> str:
        return TestAddRunner(self.rpc, self.user_hash, int(vrx_token)).execute(a, b, silent=silent)

    def execute_alg1(self, a: float, b: float, vrx_token: int = 0) -> str:
        return self.execute_test_add(a, b, vrx_token)

    def calculate_algorithm_1(self, a: float, b: float, vrx_token: int = 0) -> str:
        return self.execute_test_add(a, b, vrx_token)

    def execute_safe_space_estimates(self, data_dict: dict, vrx_token: int) -> str:
        if not self.user_hash:
            raise PermissionError(ERR_NO_EMAIL)
        return SafeSpaceEstimatesRunner(self.rpc, self.user_hash, int(vrx_token)).execute(data_dict)

    def execute_safe_space_plots_A(self, plot_data, min_tlag_variability, vrx_token: int):
        if not self.user_hash:
            raise PermissionError(ERR_NO_EMAIL)
        return execute_safe_space_plots_A(self.rpc, plot_data, min_tlag_variability, user_hash=self.user_hash, vrx_token=int(vrx_token))

    def execute_safe_space_plots_B(self, m, disso_mode, tlag_check, min_tlag_variability, vrx_token: int):
        if not self.user_hash:
            raise PermissionError(ERR_NO_EMAIL)
        return execute_safe_space_plots_B(self.rpc, m, disso_mode, tlag_check, min_tlag_variability, user_hash=self.user_hash, vrx_token=int(vrx_token))

    def execute_safe_space_plots_C(self, disso_data, m, f, t_obs_last, vrx_token: int):
        if not self.user_hash:
            raise PermissionError(ERR_NO_EMAIL)
        return execute_safe_space_plots_C(self.rpc, disso_data, m, f, t_obs_last, user_hash=self.user_hash, vrx_token=int(vrx_token))

    def execute_sim_pk_gi(self, data_dict: dict, vrx_token: int) -> str:
        if not self.user_hash:
            raise PermissionError(ERR_NO_EMAIL)
        return SimPkGiRunner(self.rpc, self.user_hash, int(vrx_token)).execute(data_dict)
