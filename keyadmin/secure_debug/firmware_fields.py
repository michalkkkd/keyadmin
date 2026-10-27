from typing import Dict

from keyadmin.core.constants import (
    RESP_OK_PREFIX_STR,
    TOKEN_ERR,
    SDL_FIELD_SEPARATOR,
    SDL_KEY_VALUE_SEPARATOR,
    SDL_ERR_FIRMWARE_FMT,
)


class FirmwareFields:
    """Parses 'KEY:VALUE;KEY:VALUE' responses returned by the Secure Debug Lock firmware commands."""

    @staticmethod
    def parse(response: str) -> Dict[str, str]:
        text = response.strip()
        if not text.startswith(RESP_OK_PREFIX_STR) or text.startswith(TOKEN_ERR):
            raise RuntimeError(SDL_ERR_FIRMWARE_FMT.format(response=response))
        body = text[len(RESP_OK_PREFIX_STR):].strip()
        fields: Dict[str, str] = {}
        for item in body.split(SDL_FIELD_SEPARATOR):
            key, sep, value = item.partition(SDL_KEY_VALUE_SEPARATOR)
            if sep:
                fields[key.strip()] = value.strip()
        return fields
