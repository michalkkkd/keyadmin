import logging
import os
import sys
import time

logger = logging.getLogger("keyadmin")


def setup_admin_logging(verbose: bool = True) -> None:
    """Configures structured console logging for the admin console without monkeypatching builtins."""
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter("[%(asctime)s.%(msecs)03d] %(message)s", datefmt="%H:%M:%S")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    log = logging.getLogger("keyadmin")
    log.setLevel(level)
    log.handlers = [handler]
    log.propagate = False

# Ensure keycomm and keyadmin packages can be found if running directly
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

KEYCOMM_DIR = os.path.join(REPO_ROOT, 'keycomm')
if KEYCOMM_DIR not in sys.path:
    sys.path.insert(0, KEYCOMM_DIR)

from keyadmin.admin_factory import init_admin_device
from keyadmin.admin_menu import KeySecMenu
from keyadmin.core.constants import ADMIN_CONSOLE_BANNER, ADMIN_ERR_ESTABLISH_CONN


def main():
    setup_admin_logging(verbose=True)
    print('=' * 60)
    print(ADMIN_CONSOLE_BANNER)
    print('=' * 60)

    compass, admin, transport = init_admin_device(
        port=None,
        keys_dir=None,
        user_email="admin_test@compass.com",
        verbose=True
    )

    if not compass or not admin:
        print(ADMIN_ERR_ESTABLISH_CONN)
        return

    time.sleep(1)

    menu = KeySecMenu(transport, compass.rpc, admin, compass)
    try:
        menu.run()
    finally:
        transport.close()


if __name__ == '__main__':
    main()
