from dataclasses import dataclass, asdict
from typing import Dict

from keyadmin.secure_debug.firmware_fields import FirmwareFields
from keyadmin.core.constants import (
    SDL_FIELD_SERIAL,
    SDL_FIELD_CMD_KEY,
    SDL_FIELD_BUILTIN_KEY,
    SDL_FIELD_SECURE_DEBUG,
    SDL_FIELD_LOCK_APPLIED,
    SDL_FIELD_LOCK_ACTIVE,
    SDL_FIELD_DEVICE_ERASE,
    SDL_FLAG_TRUE,
    SDL_CMD_KEY_MATCH,
    SDL_SERIAL_SIZE,
    SDL_ERR_BAD_RESPONSE_FMT,
)


@dataclass(frozen=True)
class DebugLockStatus:
    """Secure Engine debug lock state reported by MSG_DEBUG_LOCK_STATUS."""
    serial: str
    command_key: str
    builtin_key_present: bool
    secure_debug_enabled: bool
    lock_applied: bool
    lock_active: bool
    device_erase_enabled: bool

    @classmethod
    def from_response(cls, response: str) -> "DebugLockStatus":
        fields = FirmwareFields.parse(response)
        try:
            status = cls(
                serial=fields[SDL_FIELD_SERIAL].upper(),
                command_key=fields[SDL_FIELD_CMD_KEY],
                builtin_key_present=fields[SDL_FIELD_BUILTIN_KEY] == SDL_FLAG_TRUE,
                secure_debug_enabled=fields[SDL_FIELD_SECURE_DEBUG] == SDL_FLAG_TRUE,
                lock_applied=fields[SDL_FIELD_LOCK_APPLIED] == SDL_FLAG_TRUE,
                lock_active=fields[SDL_FIELD_LOCK_ACTIVE] == SDL_FLAG_TRUE,
                device_erase_enabled=fields[SDL_FIELD_DEVICE_ERASE] == SDL_FLAG_TRUE,
            )
        except KeyError as e:
            raise RuntimeError(SDL_ERR_BAD_RESPONSE_FMT.format(response=response)) from e
        if len(bytes.fromhex(status.serial)) != SDL_SERIAL_SIZE:
            raise RuntimeError(SDL_ERR_BAD_RESPONSE_FMT.format(response=response))
        return status

    @property
    def is_secure_locked(self) -> bool:
        return self.lock_applied and self.secure_debug_enabled and self.command_key == SDL_CMD_KEY_MATCH

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
