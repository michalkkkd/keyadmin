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


def find_dongle_port(vid: int = TARGET_VID, pid: int = TARGET_PID, verbose: bool = True) -> Optional[str]:
    """
    Scans USB COM ports to find the KeySec Dongle (Seeed XIAO MG24).
    """
    all_ports = list(serial.tools.list_ports.comports())
    if verbose:
        print(f"[DEVICE_DISCOVERY] Scanning COM ports for target VID: 0x{vid:04X} ({vid}), PID: 0x{pid:04X} ({pid})...")
        print(f"[DEVICE_DISCOVERY] Total COM ports found: {len(all_ports)}")
        for idx, p in enumerate(all_ports):
            p_vid = f"0x{p.vid:04X}" if p.vid is not None else "None"
            p_pid = f"0x{p.pid:04X}" if p.pid is not None else "None"
            print(f"[DEVICE_DISCOVERY]   Port #{idx+1}: {p.device} | Description: '{p.description}' | VID: {p_vid} | PID: {p_pid} | HWID: '{p.hwid}' | Manufacturer: '{getattr(p, 'manufacturer', 'N/A')}'")

    for port in all_ports:
        if port.vid == vid and port.pid == pid:
            if verbose:
                print(f"[DEVICE_DISCOVERY] => MATCH FOUND! Target dongle on port: {port.device}")
            return port.device

    if verbose:
        print(f"[DEVICE_DISCOVERY] => NO MATCH FOUND for VID: 0x{vid:04X}, PID: 0x{pid:04X}")
    return None


DEFAULT_ROOT_CA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'keys', ROOT_CA_FILENAME
)


def find_root_ca_key_path(custom_keys_dir: Optional[str] = None, verbose: bool = True) -> Optional[str]:
    """
    Returns the path to root_ca_pub.pem.
    Searches custom_keys_dir, exe directory, current directory, and DEFAULT_ROOT_CA_PATH.
    """
    candidates = []
    if custom_keys_dir:
        candidates.append(os.path.join(custom_keys_dir, ROOT_CA_FILENAME))
        candidates.append(os.path.join(custom_keys_dir, 'keys', ROOT_CA_FILENAME))

    import sys
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    candidates.append(os.path.join(exe_dir, 'keys', ROOT_CA_FILENAME))
    candidates.append(os.path.join(exe_dir, 'keycomm', 'keys', ROOT_CA_FILENAME))
    candidates.append(os.path.join(exe_dir, ROOT_CA_FILENAME))

    cwd = os.getcwd()
    candidates.append(os.path.join(cwd, 'keys', ROOT_CA_FILENAME))
    candidates.append(os.path.join(cwd, 'keycomm', 'keys', ROOT_CA_FILENAME))

    if DEFAULT_ROOT_CA_PATH not in candidates:
        candidates.append(DEFAULT_ROOT_CA_PATH)

    if verbose:
        print(f"[DEVICE_DISCOVERY] Searching for Root CA key '{ROOT_CA_FILENAME}' across {len(candidates)} candidate locations:")

    for idx, c_path in enumerate(candidates):
        is_found = os.path.isfile(c_path)
        if verbose:
            print(f"[DEVICE_DISCOVERY]   Candidate #{idx+1}: [{ 'FOUND' if is_found else 'NOT FOUND' }] {c_path}")
        if is_found:
            return c_path

    if verbose:
        print(f"[DEVICE_DISCOVERY] ERROR: Root CA key '{ROOT_CA_FILENAME}' not found in any candidate location!")
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
        port = find_dongle_port(verbose=verbose)
        if port is None:
            if verbose:
                print(LOG_DONGLE_NOT_FOUND)
            return None, None, False
        if verbose:
            print(LOG_FMT_FOUND_DONGLE.format(port=port))

    root_ca_path = find_root_ca_key_path(keys_dir, verbose=verbose)
    if not root_ca_path or not os.path.isfile(root_ca_path):
        if verbose:
            print(LOG_ROOT_CA_NOT_FOUND)
        return None, None, False

    transport = None
    success = False
    try:
        if verbose:
            print(f"[DEVICE_DISCOVERY] Opening SerialTransport on port '{port}' (baudrate 115200)...")
        transport = SerialTransport(port=port)
        rpc = RpcProtocol(transport)
        sec_chan = SecureChannel(rpc, root_ca_path)

        if verbose:
            print(f"[DEVICE_DISCOVERY] Initiating ECDHE Handshake with dongle...")
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
        import traceback
        tb = traceback.format_exc()
        if verbose:
            print(LOG_FMT_CONNECT_ERROR.format(port=port, e=e))
            print(f"[DEVICE_DISCOVERY] Handshake exception stacktrace:\n{tb}")
        return None, None, False
    finally:
        if not success and transport is not None:
            try:
                transport.close()
            except Exception as close_err:
                if verbose:
                    print(LOG_FMT_TRANSPORT_CLOSE_ERROR.format(err=close_err))


