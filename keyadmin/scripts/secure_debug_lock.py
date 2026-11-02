"""
Secure Debug Lock CLI (production pipeline + service use).

    python secure_debug_lock.py status [--port COMx] [--store DIR]
    python secure_debug_lock.py lock   [--port COMx] [--store DIR] [--yes] [--skip-smoke-test]
    python secure_debug_lock.py unlock [--port COMx] [--store DIR]
    python secure_debug_lock.py protect [--port COMx] [--store DIR]   # dev unit: lock is refused forever

Data for every dongle is kept in <store>/devices/device_<SE serial>/ (default store: keyadmin/keys/secure_debug).

"""
import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(ADMIN_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from keyadmin.admin_factory import init_admin_device
from keyadmin.secure_debug.secure_debug_service import SecureDebugService
from keyadmin.secure_debug.secure_debug_store import SecureDebugStore
from keyadmin.core.constants import (
    ADMIN_DEFAULT_USER_EMAIL,
    SDL_CONFIRM_WORD,
    SDL_PROMPT_CONFIRM_FMT,
    SDL_MSG_LOCK_WARNING,
    SDL_MSG_ABORTED,
    SDL_MSG_ALREADY_LOCKED,
    SDL_MSG_LOCK_OK,
    SDL_MSG_UNLOCK_OK,
    SDL_MSG_SAVED_TO_FMT,
    SDL_MSG_TAMPER_LOG_READING,
    SDL_MSG_SMOKE_TEST,
    SDL_MSG_SMOKE_OK_FMT,
    SDL_ERR_SMOKE_FAILED_FMT,
    SDL_ERR_NO_CONNECTION,
    SDL_ERR_DEVICE_PROTECTED_FMT,
    SDL_MSG_PROTECTED_ADDED_FMT,
    SDL_MSG_PROTECTED_EXISTS_FMT,
)

CMD_STATUS = "status"
CMD_LOCK = "lock"
CMD_UNLOCK = "unlock"
CMD_PROTECT = "protect"
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_ABORTED = 2


def run_smoke_test(compass, rpc) -> None:
    """Fails fast unless the dongle runs sealed production firmware with a valid identity and license."""
    print(SDL_MSG_SMOKE_TEST)
    secure_channel = getattr(rpc, "secure_channel", None)
    if secure_channel is None or not secure_channel.is_active:
        raise RuntimeError(SDL_ERR_SMOKE_FAILED_FMT.format(result="no secure ECDHE session"))
    compass.set_user_email(ADMIN_DEFAULT_USER_EMAIL)
    result = compass.check_license()
    if not result:
        raise RuntimeError(SDL_ERR_SMOKE_FAILED_FMT.format(result=result))
    print(SDL_MSG_SMOKE_OK_FMT.format(result=result))


def confirm_lock() -> bool:
    print(SDL_MSG_LOCK_WARNING)
    return input(SDL_PROMPT_CONFIRM_FMT.format(word=SDL_CONFIRM_WORD)).strip() == SDL_CONFIRM_WORD


def main() -> int:
    parser = argparse.ArgumentParser(description="KeySec Secure Debug Lock tool")
    parser.add_argument("command", choices=[CMD_STATUS, CMD_LOCK, CMD_UNLOCK, CMD_PROTECT])
    parser.add_argument("--port", help="COM port (auto-detected when omitted)")
    parser.add_argument("--store", help="secure_debug store folder (default: keyadmin/keys/secure_debug)")
    parser.add_argument("--keys", help="folder holding debug_command_key.pem (default: keyadmin/keys)")
    parser.add_argument("--yes", action="store_true", help="lock without the interactive confirmation")
    parser.add_argument("--skip-smoke-test", action="store_true", help="lock without the pre-lock license test")
    args = parser.parse_args()

    compass, admin, transport = init_admin_device(port=args.port, user_email=ADMIN_DEFAULT_USER_EMAIL, verbose=False)
    if admin is None:
        print(f"[-] {SDL_ERR_NO_CONNECTION}")
        return EXIT_FAIL

    try:
        service = SecureDebugService(admin, SecureDebugStore(args.store, keys_dir=args.keys), port=getattr(transport, "port", args.port))
        status = service.read_status()
        print(service.describe(status))

        if args.command == CMD_PROTECT:
            added = service.protect_device(status.serial)
            fmt = SDL_MSG_PROTECTED_ADDED_FMT if added else SDL_MSG_PROTECTED_EXISTS_FMT
            print(fmt.format(serial=status.serial, path=service.store.protected_list_path))

        elif args.command == CMD_LOCK:
            if service.store.is_protected(status.serial):
                raise RuntimeError(SDL_ERR_DEVICE_PROTECTED_FMT.format(serial=status.serial,
                                                                       path=service.store.protected_list_path))
            if status.is_secure_locked:
                print(SDL_MSG_ALREADY_LOCKED)
                return EXIT_OK
            if not args.skip_smoke_test:
                run_smoke_test(compass, compass.rpc)
            if not args.yes and not confirm_lock():
                print(SDL_MSG_ABORTED)
                return EXIT_ABORTED
            print(service.describe(service.apply_lock()))
            print(SDL_MSG_LOCK_OK)

        elif args.command == CMD_UNLOCK:
            folder = service.unlock()
            print(SDL_MSG_UNLOCK_OK)
            print(SDL_MSG_SAVED_TO_FMT.format(path=folder))
            print(SDL_MSG_TAMPER_LOG_READING)
            try:
                print(service.dump_tamper_log(status.serial))
            except Exception as e:
                print(f"[-] {e}")
            print(service.read_memory_hint(status.serial))
        return EXIT_OK

    except Exception as e:
        print(f"[-] {e}")
        return EXIT_FAIL
    finally:
        transport.close()


if __name__ == "__main__":
    sys.exit(main())
