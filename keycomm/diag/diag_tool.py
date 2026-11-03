import base64
import contextlib
import io
import json
import os
import sys
import time
import zlib
from datetime import datetime
from typing import Optional, TextIO

from keycomm.api.device_discovery import find_dongle_port, find_root_ca_key_path
from keycomm.core.constants import (
    CHAR_ENCODING_UTF8, DIAG_TOOL_VERSION, DIAG_HEADER_FMT, DIAG_SEND_HINT, DIAG_REPORT_FILE_FMT,
    DIAG_REPORT_SAVED_FMT, DIAG_TIMESTAMP_FMT, DIAG_FILE_STAMP_FMT, DIAG_ARMOR_BEGIN, DIAG_ARMOR_END,
    DIAG_ARMOR_LINE_LEN, DIAG_MSG_NO_DONGLE, DIAG_MSG_PORT_FMT, DIAG_MSG_NO_REPLY_FMT,
    DIAG_HANDSHAKE_REJECTED, DIAG_ERROR_FMT,
    DIAG_KEY_TOOL, DIAG_KEY_TIME, DIAG_KEY_UTC, DIAG_KEY_PC, DIAG_KEY_PORTS, DIAG_KEY_PROCESSES, DIAG_KEY_USB,
    DIAG_KEY_ROOT_CA, DIAG_KEY_HANDSHAKE, DIAG_KEY_LINK, DIAG_KEY_APP,
)
from keycomm.core.protocol import RpcProtocol
from keycomm.core.secure_channel import SecureChannel
from keycomm.core.transport import SerialTransport
from keycomm.diag.diag_stream import DiagStream
from keycomm.diag.pc_info_collector import PcInfoCollector


def _error(e: Exception) -> str:
    return DIAG_ERROR_FMT.format(type=type(e).__name__, error=e)


def _try_handshake(rpc: RpcProtocol, root_ca: Optional[str], host_key: bytes) -> str:
    """Opens a session like Compass does, so the dongle can record whether that works ("" = it did)."""
    if not root_ca:
        return DIAG_HANDSHAKE_REJECTED
    try:
        channel = SecureChannel(rpc, root_ca, host_key)
        if not channel.init_handshake():
            return DIAG_HANDSHAKE_REJECTED
        rpc.secure_channel = channel
        return ""
    except Exception as e:
        return _error(e)


def pc_facts(rpc: RpcProtocol, started: datetime, root_ca: Optional[str], handshake: str,
             app_info: Optional[dict]) -> dict:
    """Everything the PC knows; it goes to the dongle as is and is only read back in KeySec admin."""
    pc = PcInfoCollector()
    return {
        DIAG_KEY_TOOL: DIAG_TOOL_VERSION,
        DIAG_KEY_TIME: started.strftime(DIAG_TIMESTAMP_FMT),
        DIAG_KEY_UTC: int(time.time()),
        DIAG_KEY_PC: pc.pc(),
        DIAG_KEY_PORTS: pc.ports(),
        DIAG_KEY_PROCESSES: pc.processes(),
        DIAG_KEY_USB: pc.usb_driver(),
        DIAG_KEY_ROOT_CA: bool(root_ca),
        DIAG_KEY_HANDSHAKE: handshake,
        DIAG_KEY_LINK: {"retransmissions": rpc.retransmissions_count, "timeouts": rpc.timeouts_count},
        DIAG_KEY_APP: app_info or {},
    }


def seal_on_dongle(rpc: RpcProtocol, facts: dict) -> bytes:
    """The PC facts, compressed, encrypted by the dongle together with its own data."""
    data = zlib.compress(json.dumps(facts, separators=(",", ":")).encode(CHAR_ENCODING_UTF8))
    return DiagStream(rpc).seal(data, int(time.time()))


def armor(sealed: bytes) -> str:
    text = base64.b64encode(sealed).decode(CHAR_ENCODING_UTF8)
    lines = [text[i:i + DIAG_ARMOR_LINE_LEN] for i in range(0, len(text), DIAG_ARMOR_LINE_LEN)]
    return "\n".join([DIAG_ARMOR_BEGIN] + lines + [DIAG_ARMOR_END])


def run_diagnostics(host_key: bytes, keys_dir: Optional[str] = None, out_dir: Optional[str] = None,
                    stream: Optional[TextIO] = None, app_info: Optional[dict] = None) -> Optional[str]:
    """
    Compass.exe --diag. Prints the payload the dongle produced and saves it in out_dir; returns its path.
    Without a working connection there is nothing the dongle could encrypt: it prints what to do instead.
    """
    out = stream or sys.stdout
    started = datetime.now()
    out.write(DIAG_HEADER_FMT.format(version=DIAG_TOOL_VERSION, timestamp=started.strftime(DIAG_TIMESTAMP_FMT)) + "\n")

    with contextlib.redirect_stdout(io.StringIO()):
        port = find_dongle_port(verbose=False)
        if not port:
            out.write(DIAG_MSG_NO_DONGLE + "\n")
            return None
        try:
            transport = SerialTransport(port=port)
        except TimeoutError as e:
            out.write(DIAG_MSG_NO_REPLY_FMT.format(error=e) + "\n")
            return None
        except Exception as e:
            out.write(DIAG_MSG_PORT_FMT.format(error=e) + "\n")
            return None
        try:
            rpc = RpcProtocol(transport)
            root_ca = find_root_ca_key_path(keys_dir, verbose=False)
            handshake = _try_handshake(rpc, root_ca, host_key)
            payload = armor(seal_on_dongle(rpc, pc_facts(rpc, started, root_ca, handshake, app_info)))
        except Exception as e:
            out.write(DIAG_MSG_NO_REPLY_FMT.format(error=e) + "\n")
            return None
        finally:
            transport.close()

    path = os.path.join(out_dir or os.getcwd(), DIAG_REPORT_FILE_FMT.format(stamp=started.strftime(DIAG_FILE_STAMP_FMT)))
    with open(path, "w", encoding=CHAR_ENCODING_UTF8) as f:
        f.write(DIAG_SEND_HINT + "\n" + payload + "\n")
    out.write("\n".join([DIAG_SEND_HINT, payload, DIAG_REPORT_SAVED_FMT.format(path=path)]) + "\n")
    out.flush()
    return path
