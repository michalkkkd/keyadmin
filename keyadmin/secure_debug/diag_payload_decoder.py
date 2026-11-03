"""
Opens the encrypted diagnostic payload printed by keycomm.diag (Compass.exe --diag).
Envelope (keycomm/diag/diag_envelope.py): version | ephemeral P-256 point | nonce | AES-256-GCM(zlib(JSON)),
key = HKDF-SHA256(ECDH(ephemeral, Diag Report Key)). Needs keyadmin/keys/diag_report_key.pem.
"""
import base64
import binascii
import json
import os
import zlib

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from keycomm.core.constants import (
    CHAR_ENCODING_UTF8, DIAG_ENVELOPE_VERSION, DIAG_ENVELOPE_POINT_LEN, DIAG_ENVELOPE_NONCE_LEN,
    DIAG_ARMOR_BEGIN, DIAG_ARMOR_END,
)
from keycomm.diag.diag_envelope import DiagEnvelope
from keyadmin.core.constants import (
    SDL_KEYS_DIRNAME, DIAG_REPORT_KEY_FILENAME, DIAG_ERR_NO_PAYLOAD, DIAG_ERR_PAYLOAD_INVALID,
    DIAG_ERR_NO_REPORT_KEY_FMT,
)

HEADER_LEN = 1 + DIAG_ENVELOPE_POINT_LEN


def diag_report_key_path() -> str:
    admin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(admin_dir, SDL_KEYS_DIRNAME, DIAG_REPORT_KEY_FILENAME)


def load_diag_report_key(path: str = "") -> ec.EllipticCurvePrivateKey:
    path = path or diag_report_key_path()
    if not os.path.isfile(path):
        raise FileNotFoundError(DIAG_ERR_NO_REPORT_KEY_FMT.format(path=path))
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def extract_armored(text: str) -> bytes:
    """The base64 between the BEGIN/END lines; tolerates mail quoting, indentation and line breaks."""
    start, end = text.find(DIAG_ARMOR_BEGIN), text.find(DIAG_ARMOR_END)
    if start < 0 or end < start:
        raise ValueError(DIAG_ERR_NO_PAYLOAD)
    body = text[start + len(DIAG_ARMOR_BEGIN):end]
    b64 = "".join(ch for ch in body if ch.isalnum() or ch in "+/=")
    try:
        return base64.b64decode(b64, validate=True)
    except binascii.Error as e:
        raise ValueError(DIAG_ERR_PAYLOAD_INVALID) from e


def open_payload(blob: bytes, key: ec.EllipticCurvePrivateKey) -> dict:
    if len(blob) <= HEADER_LEN + DIAG_ENVELOPE_NONCE_LEN or blob[0] != DIAG_ENVELOPE_VERSION:
        raise ValueError(DIAG_ERR_PAYLOAD_INVALID)
    header, point = blob[:HEADER_LEN], blob[1:HEADER_LEN]
    nonce = blob[HEADER_LEN:HEADER_LEN + DIAG_ENVELOPE_NONCE_LEN]
    try:
        ephemeral = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), point)
        aes_key = DiagEnvelope.derive_key(key.exchange(ec.ECDH(), ephemeral), point)
        plain = AESGCM(aes_key).decrypt(nonce, blob[HEADER_LEN + DIAG_ENVELOPE_NONCE_LEN:], header)
    except (InvalidTag, ValueError) as e:
        raise ValueError(DIAG_ERR_PAYLOAD_INVALID) from e
    return json.loads(zlib.decompress(plain).decode(CHAR_ENCODING_UTF8))
