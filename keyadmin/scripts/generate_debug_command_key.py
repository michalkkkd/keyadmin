"""
Generates the Secure Debug Command Key pair (ECC P-256) and writes its public part
into KeyFirmware/src/secure/debug_command_pubkey.h so the firmware can install it into OTP.

Usage:
    python generate_debug_command_key.py               # create key (refuses to overwrite) + header
    python generate_debug_command_key.py --header-only # regenerate header from the existing key
    python generate_debug_command_key.py --keys DIR    # custom keys folder (default: keyadmin/keys)
"""
import argparse
import hashlib
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(ADMIN_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from keyadmin.secure_debug.secure_debug_store import SecureDebugStore
from keyadmin.secure_debug.unlock_token_builder import UnlockTokenBuilder
from keyadmin.core.constants import (
    SDL_FIRMWARE_HEADER_RELPATH,
    SDL_HEADER_TEMPLATE,
    SDL_HEADER_BYTES_PER_LINE,
    SDL_HEADER_BYTE_FMT,
    SDL_HEADER_LINE_INDENT,
    SDL_HEADER_BYTE_JOIN,
    SDL_HEADER_LINE_JOIN,
    SDL_MSG_KEY_CREATED_FMT,
    SDL_MSG_KEY_BACKUP,
    SDL_MSG_HEADER_WRITTEN_FMT,
    CHAR_ENCODING_UTF8,
)


def render_header(raw_pubkey: bytes) -> str:
    lines = []
    for i in range(0, len(raw_pubkey), SDL_HEADER_BYTES_PER_LINE):
        chunk = raw_pubkey[i:i + SDL_HEADER_BYTES_PER_LINE]
        lines.append(SDL_HEADER_LINE_INDENT + SDL_HEADER_BYTE_JOIN.join(SDL_HEADER_BYTE_FMT.format(b) for b in chunk))
    fingerprint = hashlib.sha256(raw_pubkey).hexdigest().upper()
    return SDL_HEADER_TEMPLATE.format(fingerprint=fingerprint, body=SDL_HEADER_LINE_JOIN.join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Secure Debug Command Key and firmware header")
    parser.add_argument("--keys", help="keys folder (default: keyadmin/keys, next to the Root CA)")
    parser.add_argument("--header-only", action="store_true", help="only regenerate the firmware header")
    args = parser.parse_args()

    store = SecureDebugStore(keys_dir=args.keys)
    if args.header_only:
        command_key = store.load_command_key()
    else:
        command_key = store.create_command_key()
        print(SDL_MSG_KEY_CREATED_FMT.format(path=store.command_key_dir))
        print(SDL_MSG_KEY_BACKUP)

    raw_pubkey = UnlockTokenBuilder.raw_public_key(command_key.public_key())
    header_path = os.path.normpath(os.path.join(REPO_ROOT, *SDL_FIRMWARE_HEADER_RELPATH))
    with open(header_path, "w", encoding=CHAR_ENCODING_UTF8) as f:
        f.write(render_header(raw_pubkey))
    print(SDL_MSG_HEADER_WRITTEN_FMT.format(path=header_path,
                                            fingerprint=hashlib.sha256(raw_pubkey).hexdigest().upper()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
