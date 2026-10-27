import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from keyadmin.core.constants import (
    SDL_KEYS_DIRNAME,
    SDL_STORE_DIRNAME,
    SDL_DEVICES_DIRNAME,
    SDL_PROTECTED_FILENAME,
    SDL_JSON_PROTECTED_SERIALS,
    SDL_JSON_NOTE,
    SDL_PROTECTED_NOTE,
    SDL_DEVICE_DIR_FMT,
    SDL_CHALLENGE_DIR_FMT,
    SDL_COMMAND_KEY_FILENAME,
    SDL_COMMAND_PUBKEY_FILENAME,
    SDL_CERT_KEY_FILENAME,
    SDL_CERT_PUBKEY_FILENAME,
    SDL_ACCESS_CERT_FILENAME,
    SDL_DEVICE_INFO_FILENAME,
    SDL_CHALLENGE_FILENAME,
    SDL_UNLOCK_TOKEN_FILENAME,
    SDL_RESULT_FILENAME,
    SDL_JSON_SERIAL,
    SDL_JSON_PORT,
    SDL_JSON_LAST_STATUS,
    SDL_JSON_EVENTS,
    SDL_JSON_EVENT,
    SDL_JSON_TIMESTAMP,
    SDL_JSON_INDENT,
    SDL_ERR_COMMAND_KEY_EXISTS_FMT,
    SDL_ERR_COMMAND_KEY_MISSING_FMT,
    CHAR_ENCODING_UTF8,
)

ADMIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_KEYS_DIR = os.path.join(ADMIN_DIR, SDL_KEYS_DIRNAME)
DEFAULT_STORE_DIR = os.path.join(DEFAULT_KEYS_DIR, SDL_STORE_DIRNAME)


class SecureDebugStore:
    """
    File store for Secure Debug Lock material.

    <keys>/debug_command_key.pem                    private Command Key (one per product / factory)
    <keys>/debug_command_pubkey.pem
    <root>/protected_devices.json                   serials that must never be debug-locked (dev units)
    <root>/devices/device_<SE serial>/device.json   status snapshots + event history
    <root>/devices/device_<SE serial>/cert_key.pem, cert_pubkey.pem, access_certificate.bin
    <root>/devices/device_<SE serial>/challenge_<challenge>/challenge.bin, unlock_token.bin, result.json
    """

    def __init__(self, root_dir: Optional[str] = None, keys_dir: Optional[str] = None):
        self.root_dir = os.path.abspath(root_dir or DEFAULT_STORE_DIR)
        self.keys_dir = os.path.abspath(keys_dir or DEFAULT_KEYS_DIR)

    # ---- Command key -------------------------------------------------------
    @property
    def command_key_dir(self) -> str:
        return self.keys_dir

    @property
    def command_key_path(self) -> str:
        return os.path.join(self.command_key_dir, SDL_COMMAND_KEY_FILENAME)

    def create_command_key(self) -> ec.EllipticCurvePrivateKey:
        if os.path.exists(self.command_key_path):
            raise FileExistsError(SDL_ERR_COMMAND_KEY_EXISTS_FMT.format(path=self.command_key_path))
        key = ec.generate_private_key(ec.SECP256R1())
        os.makedirs(self.command_key_dir, exist_ok=True)
        self._write_private_key(self.command_key_path, key)
        self._write_public_key(os.path.join(self.command_key_dir, SDL_COMMAND_PUBKEY_FILENAME), key.public_key())
        return key

    def load_command_key(self) -> ec.EllipticCurvePrivateKey:
        if not os.path.isfile(self.command_key_path):
            raise FileNotFoundError(SDL_ERR_COMMAND_KEY_MISSING_FMT.format(path=self.command_key_path))
        return self._read_private_key(self.command_key_path)

    # ---- Lock protection (development dongles) ------------------------------
    @property
    def protected_list_path(self) -> str:
        return os.path.join(self.root_dir, SDL_PROTECTED_FILENAME)

    def protected_serials(self) -> List[str]:
        if not os.path.isfile(self.protected_list_path):
            return []
        return [str(x).upper() for x in self._read_json(self.protected_list_path).get(SDL_JSON_PROTECTED_SERIALS, [])]

    def is_protected(self, serial: str) -> bool:
        return serial.upper() in self.protected_serials()

    def add_protected(self, serial: str) -> bool:
        """Adds a dongle to the protected list. Returns False if it was already there."""
        serials = self.protected_serials()
        if serial.upper() in serials:
            return False
        os.makedirs(self.root_dir, exist_ok=True)
        self._write_json(self.protected_list_path,
                         {SDL_JSON_NOTE: SDL_PROTECTED_NOTE, SDL_JSON_PROTECTED_SERIALS: serials + [serial.upper()]})
        return True

    # ---- Per-device folder -------------------------------------------------
    def device_dir(self, serial: str) -> str:
        path = os.path.join(self.root_dir, SDL_DEVICES_DIRNAME, SDL_DEVICE_DIR_FMT.format(serial=serial.upper()))
        os.makedirs(path, exist_ok=True)
        return path

    def challenge_dir(self, serial: str, challenge_hex: str) -> str:
        path = os.path.join(self.device_dir(serial), SDL_CHALLENGE_DIR_FMT.format(challenge=challenge_hex.upper()))
        os.makedirs(path, exist_ok=True)
        return path

    def load_cert_key(self, serial: str) -> Optional[ec.EllipticCurvePrivateKey]:
        path = os.path.join(self.device_dir(serial), SDL_CERT_KEY_FILENAME)
        return self._read_private_key(path) if os.path.isfile(path) else None

    def save_cert_key(self, serial: str, key: ec.EllipticCurvePrivateKey) -> None:
        folder = self.device_dir(serial)
        self._write_private_key(os.path.join(folder, SDL_CERT_KEY_FILENAME), key)
        self._write_public_key(os.path.join(folder, SDL_CERT_PUBKEY_FILENAME), key.public_key())

    def load_access_certificate(self, serial: str) -> Optional[bytes]:
        path = os.path.join(self.device_dir(serial), SDL_ACCESS_CERT_FILENAME)
        return self._read_bytes(path) if os.path.isfile(path) else None

    def save_access_certificate(self, serial: str, certificate: bytes) -> None:
        self._write_bytes(os.path.join(self.device_dir(serial), SDL_ACCESS_CERT_FILENAME), certificate)

    def save_unlock_attempt(self, serial: str, challenge: bytes, token: bytes, result: Dict[str, object]) -> str:
        folder = self.challenge_dir(serial, challenge.hex())
        self._write_bytes(os.path.join(folder, SDL_CHALLENGE_FILENAME), challenge)
        self._write_bytes(os.path.join(folder, SDL_UNLOCK_TOKEN_FILENAME), token)
        self._write_json(os.path.join(folder, SDL_RESULT_FILENAME), result)
        return folder

    def record_event(self, serial: str, event: str, details: Dict[str, object],
                     status: Optional[Dict[str, object]] = None, port: Optional[str] = None) -> str:
        path = os.path.join(self.device_dir(serial), SDL_DEVICE_INFO_FILENAME)
        info = self._read_json(path) if os.path.isfile(path) else {SDL_JSON_SERIAL: serial.upper(), SDL_JSON_EVENTS: []}
        if port:
            info[SDL_JSON_PORT] = port
        if status is not None:
            info[SDL_JSON_LAST_STATUS] = status
        info[SDL_JSON_EVENTS].append({SDL_JSON_TIMESTAMP: self.now_iso(), SDL_JSON_EVENT: event, **details})
        self._write_json(path, info)
        return path

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    # ---- File helpers ------------------------------------------------------
    @staticmethod
    def _write_private_key(path: str, key: ec.EllipticCurvePrivateKey) -> None:
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
        SecureDebugStore._write_bytes(path, pem)

    @staticmethod
    def _write_public_key(path: str, key: ec.EllipticCurvePublicKey) -> None:
        pem = key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        SecureDebugStore._write_bytes(path, pem)

    @staticmethod
    def _read_private_key(path: str) -> ec.EllipticCurvePrivateKey:
        return serialization.load_pem_private_key(SecureDebugStore._read_bytes(path), password=None)

    @staticmethod
    def _read_bytes(path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    @staticmethod
    def _write_bytes(path: str, data: bytes) -> None:
        with open(path, "wb") as f:
            f.write(data)

    @staticmethod
    def _read_json(path: str) -> Dict[str, object]:
        with open(path, "r", encoding=CHAR_ENCODING_UTF8) as f:
            return json.load(f)

    @staticmethod
    def _write_json(path: str, data: Dict[str, object]) -> None:
        with open(path, "w", encoding=CHAR_ENCODING_UTF8) as f:
            json.dump(data, f, indent=SDL_JSON_INDENT)
