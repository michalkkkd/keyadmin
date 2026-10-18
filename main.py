"""
KeySec root launcher.
Delegates to the keyadmin console when the keyadmin suite is installed.
"""
import sys
import os

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

KEYCOMM_DIR = os.path.join(REPO_ROOT, 'keycomm')
if KEYCOMM_DIR not in sys.path:
    sys.path.insert(0, KEYCOMM_DIR)


def main():
    try:
        from keyadmin.main import main as admin_main
        admin_main()
    except ImportError as e:
        print("[!] keyadmin package is not available in this environment.")
        print(f"    Details: {e}")
        print("    This installation contains only keycomm (client communication library).")
        sys.exit(1)


if __name__ == '__main__':
    main()
