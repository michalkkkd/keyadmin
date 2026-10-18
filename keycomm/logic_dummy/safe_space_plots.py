"""
Dummy stub for Safe Space Plots.
Empty implementation for public distribution or interface mock.
"""

from typing import Tuple, Optional
import pandas as pd
from keycomm.core.base_runner import BaseRunner


class SafeSpacePlotsRunner(BaseRunner):
    """
    Dummy SafeSpacePlotsRunner. Does not execute computations.
    """
    def __init__(self, rpc_client=None, user_hash: int = 0, vrx_token: int = 0, stage: str = "A"):
        super().__init__(rpc_client)
        self.user_hash = user_hash
        self.vrx_token = int(vrx_token)
        self.stage = stage

    def pre_execute(self, *args, **kwargs):
        pass

    def execute_send(self, *args, **kwargs):
        pass

    def execute_process(self, *args, **kwargs):
        pass

    def execute_receive(self, *args, **kwargs) -> str:
        return ""


def execute_safe_space_plots_A(rpc, plot_data, min_tlag_variability, user_hash: int = 0, vrx_token: int = 0) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    return pd.DataFrame(), None


def execute_safe_space_plots_B(rpc, m, disso_mode, tlag_check, min_tlag_variability, user_hash: int = 0, vrx_token: int = 0) -> bool:
    return True


def execute_safe_space_plots_C(rpc, disso_data, m, f, t_obs_last, user_hash: int = 0, vrx_token: int = 0) -> pd.DataFrame:
    return pd.DataFrame()
