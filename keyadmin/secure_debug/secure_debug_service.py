import os
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import ec

from keyadmin.api.admin_api import AdminApi
from keyadmin.secure_debug.debug_challenge import DebugChallenge
from keyadmin.secure_debug.debug_lock_status import DebugLockStatus
from keyadmin.secure_debug.secure_debug_store import SecureDebugStore
from keyadmin.secure_debug.unlock_token_builder import UnlockTokenBuilder
from keyadmin.secure_debug.tamper_log_decoder import parse, format_report, read_user_data_over_swd, load_key
from keyadmin.core.constants import (
    RESP_OK_PREFIX_STR,
    SDL_CMD_KEY_MISMATCH,
    SDL_EVENT_STATUS,
    SDL_EVENT_LOCK,
    SDL_EVENT_UNLOCK,
    SDL_JSON_RESPONSE,
    SDL_JSON_CHALLENGE,
    SDL_JSON_SUCCESS,
    SDL_MSG_STATUS_FMT,
    SDL_ERR_NO_BUILTIN_KEY,
    SDL_ERR_KEY_MISMATCH,
    SDL_ERR_FIRMWARE_FMT,
    SDL_ERR_LOCK_NOT_VERIFIED_FMT,
    SDL_PACK_RELPATH,
    SDL_TAMPER_LOG_DUMP_FILENAME,
    SDL_MSG_UNLOCK_HINT_FMT,
    SDL_PROTECTION_ON,
    SDL_PROTECTION_OFF,
    SDL_ERR_DEVICE_PROTECTED_FMT,
    SDL_PYOCD_TARGET,
    SDL_PYOCD_TIMEOUT_SEC,
    SDL_MSG_TAMPER_LOG_SAVED_FMT,
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

    def _tamper_log_path(self, serial: str) -> str:
        return os.path.join(self.store.device_dir(serial), SDL_TAMPER_LOG_DUMP_FILENAME).replace(os.sep, "/")

    def read_memory_hint(self, serial: str) -> str:
        """Instructions for reading memory over SWD while the port is temporarily open."""
        return SDL_MSG_UNLOCK_HINT_FMT.format(pack=self._pack_path(), outfile=self._tamper_log_path(serial))

    def dump_tamper_log(self, serial: str) -> str:
        """Reads the User Data page (encrypted tamper event log) over SWD in attach mode and decodes it.
        Requires an open debug port: a prior unlock, or a dongle already wiped by a device erase."""
        outfile = self._tamper_log_path(serial)
        data = read_user_data_over_swd(outfile, self._pack_path(), SDL_PYOCD_TARGET, SDL_PYOCD_TIMEOUT_SEC)
        return SDL_MSG_TAMPER_LOG_SAVED_FMT.format(path=os.path.normpath(outfile), size=len(data),
                                                 report=format_report(parse(data, load_key())))

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
        """Opens the debug port until the next reset. Returns the dongle's folder (event history).
        The access certificate, its key and the unlock token are built in memory from the Command Key and
        never saved: the Command Key is the only secret."""
        challenge = DebugChallenge.from_response(self.admin.get_debug_challenge())
        cert_key = ec.generate_private_key(ec.SECP256R1())
        certificate = self.builder.build_access_certificate(bytes.fromhex(challenge.serial), cert_key.public_key(),
                                                            self.store.load_command_key())
        token = self.builder.build_unlock_token(certificate, cert_key, challenge.challenge)

        response = self.admin.open_debug_port(token)
        success = response.startswith(RESP_OK_PREFIX_STR)
        self.store.record_event(challenge.serial, SDL_EVENT_UNLOCK,
                                {SDL_JSON_CHALLENGE: challenge.challenge_hex, SDL_JSON_RESPONSE: response,
                                 SDL_JSON_SUCCESS: success}, port=self.port)
        if not success:
            raise RuntimeError(SDL_ERR_FIRMWARE_FMT.format(response=response))
        return self.store.device_dir(challenge.serial)
