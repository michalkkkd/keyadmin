"""
Reads and decrypts the tamper event log from a dongle's User Data page (0x0FE00000).
Needs the Tamper Log Key (keyadmin/keys/tamper_log_key.bin, or --key FILE).

Works without USB firmware, e.g. on a dongle wiped by the tamper live wipe (the device erase also
opened its debug port). A secure-locked dongle with working firmware is read via `secure_debug_lock.py unlock`.

    python read_tamper_log.py [--out FILE]      # read over SWD (pyOCD, attach mode) and decode
    python read_tamper_log.py --file FILE       # decode an earlier dump

Clearing the page afterwards (flashing does not erase it): commander device pageerase --region @userdata
"""
import argparse
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from keyadmin.secure_debug.tamper_log_decoder import parse, format_report, read_user_data_over_swd, load_key
from keyadmin.core.constants import SDL_PACK_RELPATH, SDL_PYOCD_TARGET, SDL_PYOCD_TIMEOUT_SEC


def main() -> int:
    parser = argparse.ArgumentParser(description="Read and decode the dongle tamper log (User Data page)")
    parser.add_argument("--file", help="decode this dump instead of reading the dongle")
    parser.add_argument("--out", help="where to save the dump (default: userdata_<time>.bin in the current folder)")
    parser.add_argument("--key", default="", help="Tamper Log Key file (default: keyadmin/keys/tamper_log_key.bin)")
    args = parser.parse_args()

    try:
        key = load_key(args.key)
        if args.file:
            with open(args.file, "rb") as f:
                data = f.read()
        else:
            out = args.out or f"userdata_{time.strftime('%Y%m%d_%H%M%S')}.bin"
            pack = os.path.normpath(os.path.join(REPO_ROOT, *SDL_PACK_RELPATH)).replace(os.sep, "/")
            data = read_user_data_over_swd(out.replace(os.sep, "/"), pack, SDL_PYOCD_TARGET, SDL_PYOCD_TIMEOUT_SEC)
            print(f"[+] Saved: {os.path.abspath(out)}")
        print(format_report(parse(data, key)))
        return 0
    except Exception as e:
        print(f"[-] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
