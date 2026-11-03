import csv
import hashlib
import io
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List

import serial.tools.list_ports

from keycomm.core.constants import (
    TARGET_VID, TARGET_PID, KEYCOMM_VERSION, DIAG_PORT_FMT, DIAG_PROCESS_PATTERN, DIAG_TASKLIST_CMD,
    DIAG_USB_DRIVER_PS, DIAG_SUBPROCESS_TIMEOUT_S, DIAG_EXE_HASH_CHUNK, DIAG_FP_HEX_LEN, DIAG_TIMESTAMP_FMT,
)

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class PcInfoCollector:
    """
    PC facts for the diagnostic payload. Read-only; nothing here touches the dongle.
    Personal data stays out: no computer or user name, and the user profile in paths is replaced by %USERPROFILE%.
    Each probe catches its own failure and reports the error text instead, so one broken probe never stops the run.
    """

    @staticmethod
    def mask_profile(path: str) -> str:
        profile = os.path.expanduser("~")
        return path.replace(profile, "%USERPROFILE%") if profile and profile != "~" else path

    def pc(self) -> Dict[str, object]:
        exe = os.path.abspath(sys.argv[0])
        info: Dict[str, object] = {
            "keycomm": KEYCOMM_VERSION,
            "os": platform.platform(),
            "python": platform.python_version(),
            "timezone": time.strftime("%Z"),
            "utc_offset_s": int(datetime.now().astimezone().utcoffset().total_seconds()),
            "exe": self.mask_profile(exe),
        }
        try:
            info["exe_size"] = os.path.getsize(exe)
            info["exe_mtime"] = datetime.fromtimestamp(os.path.getmtime(exe)).strftime(DIAG_TIMESTAMP_FMT)
            info["exe_sha256"] = self._sha256_prefix(exe)
        except OSError as e:
            info["exe_error"] = str(e)
        return info

    @staticmethod
    def _sha256_prefix(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(DIAG_EXE_HASH_CHUNK), b""):
                digest.update(block)
        return digest.hexdigest()[:DIAG_FP_HEX_LEN].upper()

    @staticmethod
    def ports() -> List[str]:
        return [DIAG_PORT_FMT.format(device=p.device, vid=f"{p.vid or 0:04X}", pid=f"{p.pid or 0:04X}",
                                     description=p.description, manufacturer=p.manufacturer,
                                     serial=p.serial_number, location=p.location, hwid=p.hwid)
                for p in serial.tools.list_ports.comports()]

    @staticmethod
    def processes() -> Dict[str, object]:
        """Image names that may hold the COM port (Compass, terminals, flashing tools), with their count."""
        try:
            out = subprocess.run(DIAG_TASKLIST_CMD, capture_output=True, text=True,
                                 timeout=DIAG_SUBPROCESS_TIMEOUT_S, creationflags=NO_WINDOW).stdout
        except (OSError, subprocess.SubprocessError) as e:
            return {"error": str(e)}
        pattern = re.compile(DIAG_PROCESS_PATTERN, re.IGNORECASE)
        counts: Dict[str, int] = {}
        for row in csv.reader(io.StringIO(out)):
            if row and pattern.search(row[0]):
                counts[row[0]] = counts.get(row[0], 0) + 1
        return counts

    @staticmethod
    def usb_driver() -> object:
        """Windows driver of every USB interface of the dongle (VID/PID), via WMI."""
        command = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                   DIAG_USB_DRIVER_PS.format(vid=TARGET_VID, pid=TARGET_PID)]
        try:
            out = subprocess.run(command, capture_output=True, text=True,
                                 timeout=DIAG_SUBPROCESS_TIMEOUT_S, creationflags=NO_WINDOW).stdout.strip()
            return json.loads(out) if out else []
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            return {"error": str(e)}
