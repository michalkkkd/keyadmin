import os
from typing import Optional, Tuple

from cryptography.hazmat.primitives import serialization

from keycomm.api.compass_api import CompassApi
from keycomm.api.device_discovery import (
    find_dongle_port,
    find_root_ca_key_path,
    establish_dongle_connection,
)
from keyadmin.api.admin_api import AdminApi
from keyadmin.core.constants import HOST_KEY_FILENAME

__all__ = ["init_admin_device", "find_dongle_port", "host_key_path", "load_host_key"]


def host_key_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys", HOST_KEY_FILENAME)


def load_host_key() -> bytes:
    """Factory copy of the Host Key (same key as XRouter._HOST_KEY in Compass), as a raw 32-byte scalar."""
    with open(host_key_path(), "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    return key.private_numbers().private_value.to_bytes(32, "big")


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
        allow_unencrypted_admin=True,
        host_key=load_host_key()
    )
    if rpc is None or transport is None:
        return None, None, None

    admin = AdminApi(rpc)
    compass = CompassApi(rpc, user_email=user_email)
    return compass, admin, transport
