import os
import subprocess
import sys
from typing import Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import ec

from keyadmin.api.admin_api import AdminApi
from keyadmin.secure_debug.debug_challenge import DebugChallenge
from keyadmin.secure_debug.debug_lock_status import DebugLockStatus
from keyadmin.secure_debug.secure_debug_store import SecureDebugStore
from keyadmin.secure_debug.unlock_token_builder import UnlockTokenBuilder
from keyadmin.core.constants import (
    RESP_OK_PREFIX_STR,
    SDL_CMD_KEY_MISMATCH,
    SDL_EVENT_STATUS,
    SDL_EVENT_LOCK,
    SDL_EVENT_UNLOCK,
    SDL_JSON_RESPONSE,
    SDL_JSON_CHALLENGE,
    SDL_JSON_SUCCESS,
    SDL_JSON_TIMESTAMP,
    SDL_JSON_SERIAL,
    SDL_MSG_STATUS_FMT,
    SDL_ERR_NO_BUILTIN_KEY,
    SDL_ERR_KEY_MISMATCH,
    SDL_ERR_FIRMWARE_FMT,
    SDL_ERR_LOCK_NOT_VERIFIED_FMT,
    SDL_ERR_SERIAL_MISMATCH_FMT,
    SDL_CERT_SERIAL_OFFSET,
    SDL_SERIAL_SIZE,
    SDL_PACK_RELPATH,
    SDL_BLACKBOX_DUMP_FILENAME,
    SDL_MSG_UNLOCK_HINT_FMT,
    SDL_PROTECTION_ON,
    SDL_PROTECTION_OFF,
    SDL_ERR_DEVICE_PROTECTED_FMT,
    SDL_PYOCD_TARGET,
    SDL_BLACKBOX_ADDR,
    SDL_BLACKBOX_SIZE,
    SDL_BLACKBOX_ERASED_BYTE,
    SDL_PYOCD_SAVEMEM_FMT,
    SDL_PYOCD_TIMEOUT_SEC,
    SDL_MSG_BLACKBOX_SAVED_FMT,
    SDL_BLACKBOX_STATE_EMPTY,
    SDL_BLACKBOX_STATE_DATA,
    SDL_ERR_BLACKBOX_FMT,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SecureDebugService:
    """Secure Debug Lock workflows: status, one-way lock and challenge-response unlock."""

    def __init__(self, admin: AdminApi, store: SecureDebugStore, port: Optional[str] = None):
        self.admin = admin
        self.store = store
        self.port = port
        self.builder = UnlockTokenBuilder()

    def read_status(self) -> DebugLockStatus:
        response = self.admin.get_debug_lock_status()
        status = DebugLockStatus.from_response(response)
        self.store.record_event(status.serial, SDL_EVENT_STATUS, {}, status=status.to_dict(), port=self.port)
        return status

    def describe(self, status: DebugLockStatus) -> str:
        return SDL_MSG_STATUS_FMT.format(
            serial=status.serial, cmd_key=status.command_key, builtin=status.builtin_key_present,
            secure_debug=status.secure_debug_enabled, lock_applied=status.lock_applied,
            lock_active=status.lock_active, device_erase=status.device_erase_enabled,
            protection=SDL_PROTECTION_ON if self.store.is_protected(status.serial) else SDL_PROTECTION_OFF,
            folder=self.store.device_dir(status.serial),
        )

    def _pack_path(self) -> str:
        return os.path.normpath(os.path.join(REPO_ROOT, *SDL_PACK_RELPATH)).replace(os.sep, "/")

    def _blackbox_path(self, serial: str) -> str:
        return os.path.join(self.store.device_dir(serial), SDL_BLACKBOX_DUMP_FILENAME).replace(os.sep, "/")

    def read_memory_hint(self, serial: str) -> str:
        """Instructions for reading memory over SWD while the port is temporarily open."""
        return SDL_MSG_UNLOCK_HINT_FMT.format(pack=self._pack_path(), outfile=self._blackbox_path(serial))

    def dump_black_box(self, serial: str) -> str:
        """Reads the Black Box over SWD in attach mode (no reset, so the port stays open). Requires a prior unlock."""
        outfile = self._blackbox_path(serial)
        if os.path.exists(outfile):
            os.remove(outfile)
        savemem = SDL_PYOCD_SAVEMEM_FMT.format(addr=SDL_BLACKBOX_ADDR, size=SDL_BLACKBOX_SIZE, outfile=outfile)
        cmd = [sys.executable, "-m", "pyocd", "cmd", "-t", SDL_PYOCD_TARGET, "--pack", self._pack_path(),
               "-M", "attach", "-c", savemem]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=SDL_PYOCD_TIMEOUT_SEC)
        if not os.path.isfile(outfile) or os.path.getsize(outfile) != SDL_BLACKBOX_SIZE:
            error = (result.stderr.strip() or result.stdout.strip() or str(result.returncode)).splitlines()[-1]
            raise RuntimeError(SDL_ERR_BLACKBOX_FMT.format(error=error))
        with open(outfile, "rb") as f:
            data = f.read()
        empty = all(b == SDL_BLACKBOX_ERASED_BYTE for b in data)
        return SDL_MSG_BLACKBOX_SAVED_FMT.format(path=os.path.normpath(outfile), size=len(data),
                                                 state=SDL_BLACKBOX_STATE_EMPTY if empty else SDL_BLACKBOX_STATE_DATA)

    def apply_lock(self) -> DebugLockStatus:
        """Writes the command key to OTP (once), enables secure debug and locks SWD. Idempotent."""
        before = self.read_status()
        if self.store.is_protected(before.serial):
            raise RuntimeError(SDL_ERR_DEVICE_PROTECTED_FMT.format(serial=before.serial,
                                                                   path=self.store.protected_list_path))
        if before.is_secure_locked:
            return before
        if not before.builtin_key_present:
            raise RuntimeError(SDL_ERR_NO_BUILTIN_KEY)
        if before.command_key == SDL_CMD_KEY_MISMATCH:
            raise RuntimeError(SDL_ERR_KEY_MISMATCH)

        response = self.admin.apply_debug_lock()
        after = DebugLockStatus.from_response(self.admin.get_debug_lock_status())
        success = response.startswith(RESP_OK_PREFIX_STR) and after.is_secure_locked
        self.store.record_event(after.serial, SDL_EVENT_LOCK, {SDL_JSON_RESPONSE: response, SDL_JSON_SUCCESS: success},
                                status=after.to_dict(), port=self.port)
        if not response.startswith(RESP_OK_PREFIX_STR):
            raise RuntimeError(SDL_ERR_FIRMWARE_FMT.format(response=response))
        if not after.is_secure_locked:
            raise RuntimeError(SDL_ERR_LOCK_NOT_VERIFIED_FMT.format(status=after.to_dict()))
        return after

    def protect_device(self, serial: str) -> bool:
        """Marks a dongle as a development unit that must never be debug-locked."""
        return self.store.add_protected(serial)

    def unlock(self) -> str:
        """Opens the debug port until the next reset. Returns the folder holding this attempt's files."""
        challenge = DebugChallenge.from_response(self.admin.get_debug_challenge())
        certificate, cert_key = self._ensure_access_certificate(challenge.serial)
        token = self.builder.build_unlock_token(certificate, cert_key, challenge.challenge)

        response = self.admin.open_debug_port(token)
        success = response.startswith(RESP_OK_PREFIX_STR)
        result = {
            SDL_JSON_TIMESTAMP: self.store.now_iso(),
            SDL_JSON_SERIAL: challenge.serial,
            SDL_JSON_CHALLENGE: challenge.challenge_hex,
            SDL_JSON_RESPONSE: response,
            SDL_JSON_SUCCESS: success,
        }
        folder = self.store.save_unlock_attempt(challenge.serial, challenge.challenge, token, result)
        self.store.record_event(challenge.serial, SDL_EVENT_UNLOCK,
                                {SDL_JSON_CHALLENGE: challenge.challenge_hex, SDL_JSON_RESPONSE: response,
                                 SDL_JSON_SUCCESS: success}, port=self.port)
        if not success:
            raise RuntimeError(SDL_ERR_FIRMWARE_FMT.format(response=response))
        return folder

    def _ensure_access_certificate(self, serial: str) -> Tuple[bytes, ec.EllipticCurvePrivateKey]:
        """Reuses the per-dongle access certificate, or signs a new one with the Command Key."""
        certificate = self.store.load_access_certificate(serial)
        cert_key = self.store.load_cert_key(serial)
        if certificate is None or cert_key is None:
            command_key = self.store.load_command_key()
            cert_key = ec.generate_private_key(ec.SECP256R1())
            certificate = self.builder.build_access_certificate(bytes.fromhex(serial), cert_key.public_key(),
                                                                command_key)
            self.store.save_cert_key(serial, cert_key)
            self.store.save_access_certificate(serial, certificate)

        cert_serial = certificate[SDL_CERT_SERIAL_OFFSET:SDL_CERT_SERIAL_OFFSET + SDL_SERIAL_SIZE].hex().upper()
        if cert_serial != serial.upper():
            raise RuntimeError(SDL_ERR_SERIAL_MISMATCH_FMT.format(cert=cert_serial, device=serial))
        return certificate, cert_key
