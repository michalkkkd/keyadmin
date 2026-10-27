from dataclasses import dataclass

from keyadmin.secure_debug.firmware_fields import FirmwareFields
from keyadmin.core.constants import (
    SDL_FIELD_SERIAL,
    SDL_FIELD_CHALLENGE,
    SDL_SERIAL_SIZE,
    SDL_CHALLENGE_SIZE,
    SDL_ERR_BAD_RESPONSE_FMT,
)


@dataclass(frozen=True)
class DebugChallenge:
    """Secure Engine serial number and current unlock challenge (MSG_DEBUG_LOCK_CHALLENGE)."""
    serial: str
    challenge: bytes

    @classmethod
    def from_response(cls, response: str) -> "DebugChallenge":
        fields = FirmwareFields.parse(response)
        try:
            serial = fields[SDL_FIELD_SERIAL].upper()
            challenge = bytes.fromhex(fields[SDL_FIELD_CHALLENGE])
            serial_ok = len(bytes.fromhex(serial)) == SDL_SERIAL_SIZE
        except (KeyError, ValueError) as e:
            raise RuntimeError(SDL_ERR_BAD_RESPONSE_FMT.format(response=response)) from e
        if not serial_ok or len(challenge) != SDL_CHALLENGE_SIZE:
            raise RuntimeError(SDL_ERR_BAD_RESPONSE_FMT.format(response=response))
        return cls(serial=serial, challenge=challenge)

    @property
    def challenge_hex(self) -> str:
        return self.challenge.hex().upper()
