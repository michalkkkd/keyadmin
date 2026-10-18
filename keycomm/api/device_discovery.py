import os
import time
from typing import Optional, Tuple
import serial.tools.list_ports

from keycomm.core.transport import SerialTransport
from keycomm.core.protocol import RpcProtocol
from keycomm.core.secure_channel import SecureChannel
from keycomm.core.constants import (
    TARGET_VID, TARGET_PID, ROOT_CA_FILENAME,
    LOG_AUTODETECTING, LOG_DONGLE_NOT_FOUND, LOG_FMT_FOUND_DONGLE,
    LOG_ROOT_CA_NOT_FOUND, LOG_FMT_SESSION_ESTABLISHED,
    LOG_ADMIN_UNENCRYPTED_NOTICE, LOG_HANDSHAKE_FATAL,
    LOG_FMT_CONNECT_ERROR, LOG_FMT_TRANSPORT_CLOSE_ERROR
)


def find_dongle_port(vid: int = TARGET_VID, pid: int = TARGET_PID) -> Optional[str]:
    """
    Scans USB COM ports to find the KeySec Dongle (Seeed XIAO MG24).
    """
    for port in serial.tools.list_ports.comports():
        if port.vid == vid and port.pid == pid:
            return port.device
    return None


DEFAULT_ROOT_CA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'keys', ROOT_CA_FILENAME
)


def find_root_ca_key_path(custom_keys_dir: Optional[str] = None) -> Optional[str]:
    """
    Returns the path to root_ca_pub.pem.
    Uses custom_keys_dir if specified, otherwise the canonical keycomm/keys/root_ca_pub.pem.
    """
    if custom_keys_dir:
        custom_path = os.path.join(custom_keys_dir, ROOT_CA_FILENAME)
        if os.path.isfile(custom_path):
            return custom_path

    if os.path.isfile(DEFAULT_ROOT_CA_PATH):
        return DEFAULT_ROOT_CA_PATH

    return None


def establish_dongle_connection(
    port: Optional[str] = None,
    keys_dir: Optional[str] = None,
    verbose: bool = True,
    allow_unencrypted_admin: bool = False
) -> Tuple[Optional[RpcProtocol], Optional[SerialTransport], bool]:
    """
    Connects to the KeySec Dongle, establishes the secure ECDHE session,
    and returns (rpc, transport, is_secure_active).
    """
    if port is None:
        if verbose:
            print(LOG_AUTODETECTING)
        port = find_dongle_port()
        if port is None:
            if verbose:
                print(LOG_DONGLE_NOT_FOUND)
            return None, None, False
        if verbose:
            print(LOG_FMT_FOUND_DONGLE.format(port=port))

    root_ca_path = find_root_ca_key_path(keys_dir)
    if not root_ca_path or not os.path.isfile(root_ca_path):
        if verbose:
            print(LOG_ROOT_CA_NOT_FOUND)
        return None, None, False

    transport = None
    success = False
    try:
        transport = SerialTransport(port=port)
        rpc = RpcProtocol(transport)
        sec_chan = SecureChannel(rpc, root_ca_path)

        t0 = time.perf_counter()
        hs_result = sec_chan.init_handshake()
        t1 = time.perf_counter()

        if hs_result:
            if verbose:
                print(LOG_FMT_SESSION_ESTABLISHED.format(ms=(t1 - t0) * 1000))
            rpc.secure_channel = sec_chan
            success = True
            return rpc, transport, True
        else:
            if allow_unencrypted_admin:
                if verbose:
                    print(LOG_ADMIN_UNENCRYPTED_NOTICE)
                success = True
                return rpc, transport, False
            else:
                if verbose:
                    print(LOG_HANDSHAKE_FATAL)
                return None, None, False

    except Exception as e:
        if verbose:
            print(LOG_FMT_CONNECT_ERROR.format(port=port, e=e))
        return None, None, False
    finally:
        if not success and transport is not None:
            try:
                transport.close()
            except Exception as close_err:
                if verbose:
                    print(LOG_FMT_TRANSPORT_CLOSE_ERROR.format(err=close_err))


