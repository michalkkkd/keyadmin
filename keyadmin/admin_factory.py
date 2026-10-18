from typing import Optional, Tuple

from keycomm.api.compass_api import CompassApi
from keycomm.api.device_discovery import (
    find_dongle_port,
    find_root_ca_key_path,
    establish_dongle_connection,
)
from keyadmin.api.admin_api import AdminApi

__all__ = ["init_admin_device", "find_dongle_port"]


def init_admin_device(
    port: Optional[str] = None,
    keys_dir: Optional[str] = None,
    user_email: str = "",
    verbose: bool = True
) -> Tuple[Optional[CompassApi], Optional[AdminApi], Optional[object]]:
    """
    Initializes Dongle connection with both CompassApi and AdminApi capabilities.
    Returns (compass, admin, transport).
    """
    rpc, transport, is_secure = establish_dongle_connection(
        port=port,
        keys_dir=keys_dir,
        verbose=verbose,
        allow_unencrypted_admin=True
    )
    if rpc is None or transport is None:
        return None, None, None

    admin = AdminApi(rpc)
    compass = CompassApi(rpc, user_email=user_email)
    return compass, admin, transport
