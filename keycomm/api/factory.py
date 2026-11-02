from typing import Optional, Tuple

from keycomm.api.compass_api import CompassApi
from keycomm.api.device_discovery import (
    find_dongle_port,
    find_root_ca_key_path,
    establish_dongle_connection,
)

__all__ = [
    "find_dongle_port",
    "find_root_ca_key_path",
    "establish_dongle_connection",
    "init_comm_device",
    "init_device",
]


def init_comm_device(
    port: Optional[str] = None,
    keys_dir: Optional[str] = None,
    user_email: str = "",
    verbose: bool = True,
    enable_heartbeat: bool = True,
    *,
    host_key: bytes
) -> Tuple[Optional[CompassApi], Optional[object]]:
    """
    Initializes communication connection to the Dongle, performs ECDHE handshake,
    and returns (compass_api, transport). host_key signs the handshake (the dongle rejects other hosts).
    """
    if verbose:
        print(f"[KEYCOMM FACTORY] init_comm_device invoked: port={port}, keys_dir={keys_dir}, verbose={verbose}")
    rpc, transport, is_secure = establish_dongle_connection(
        port=port,
        keys_dir=keys_dir,
        verbose=verbose,
        allow_unencrypted_admin=False,
        host_key=host_key
    )
    if rpc is None or transport is None:
        if verbose:
            print("[KEYCOMM FACTORY] establish_dongle_connection returned (None, None). Handshake or device detection failed.")
        return None, None

    if enable_heartbeat and hasattr(transport, 'resume_heartbeat'):
        if verbose:
            print("[KEYCOMM FACTORY] Resuming heartbeat on transport.")
        transport.resume_heartbeat()

    compass = CompassApi(rpc, user_email=user_email)
    if verbose:
        print(f"[KEYCOMM FACTORY] Successfully created CompassApi instance ({compass}).")
    return compass, transport


def init_device(
    port: Optional[str] = None,
    keys_dir: Optional[str] = None,
    user_email: str = "",
    verbose: bool = True,
    enable_heartbeat: bool = True,
    *,
    host_key: bytes
) -> Tuple[Optional[CompassApi], Optional[object], Optional[object]]:
    """
    Backward-compatible factory returning (compass, admin=None, transport).
    Permits legacy unpacking `compass, admin, transport = init_device(...)` in client code.
    """
    compass, transport = init_comm_device(
        port=port,
        keys_dir=keys_dir,
        user_email=user_email,
        verbose=verbose,
        enable_heartbeat=enable_heartbeat,
        host_key=host_key
    )
    if compass is None:
        return None, None, None
    return compass, None, transport
