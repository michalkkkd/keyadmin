"""
Runs the customer diagnostics tool (what Compass.exe --diag does) with the factory Host Key, for testing
without Compass. Prints and saves the encrypted payload; decipher it with decode_diag_payload.py.

    python run_customer_diag.py [--keys-dir DIR] [--out-dir DIR]
"""
import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from keycomm.diag import run_diagnostics
from keyadmin.admin_factory import load_host_key
from keyadmin.core.constants import DIAG_HELP_KEYS_DIR, DIAG_HELP_OUT_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the customer diagnostics tool with the factory Host Key")
    parser.add_argument("--keys-dir", default=None, help=DIAG_HELP_KEYS_DIR)
    parser.add_argument("--out-dir", default=None, help=DIAG_HELP_OUT_DIR)
    args = parser.parse_args()
    run_diagnostics(load_host_key(), keys_dir=args.keys_dir, out_dir=args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
