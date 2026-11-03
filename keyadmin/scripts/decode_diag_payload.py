"""
Deciphers a customer's diagnostic payload (Compass.exe --diag / run_customer_diag.py).
Needs keyadmin/keys/tamper_log_key.bin (the dongle encrypted the payload with it). No dongle needed.

    python decode_diag_payload.py key_diag_20261103_171037.txt   # the report file
    python decode_diag_payload.py                                # paste the text, end with the END line
"""
import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from keycomm.core.constants import DIAG_ARMOR_END
from keyadmin.core.constants import ADMIN_PROMPT_DIAG_PASTE
from keyadmin.secure_debug.tamper_log_decoder import load_key as load_tamper_log_key
from keyadmin.secure_debug.diag_stream_decoder import extract_armored, open_stream
from keyadmin.secure_debug.diag_support_report import format_support_report


def read_pasted_payload() -> str:
    """Reads console lines until the END marker (or end of input)."""
    print(ADMIN_PROMPT_DIAG_PASTE)
    lines = []
    for line in sys.stdin:
        lines.append(line)
        if DIAG_ARMOR_END in line:
            break
    return "".join(lines)


def decipher(text: str) -> str:
    return format_support_report(open_stream(extract_armored(text), load_tamper_log_key()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Decipher a customer's diagnostic payload")
    parser.add_argument("file", nargs="?", help="report file (key_diag_*.txt); omit to paste the text")
    args = parser.parse_args()
    try:
        if args.file:
            with open(args.file, encoding="utf-8") as f:
                text = f.read()
        else:
            text = read_pasted_payload()
        print(decipher(text))
        return 0
    except Exception as e:
        print(f"[-] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
