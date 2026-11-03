"""
Opens the DIAG stream the customer sends (Compass.exe --diag). The dongle's Secure world encrypted it with the
Tamper Log Key (AES-128-GCM): header = version | IV, then ciphertext, then the 16-byte tag; AAD = version byte.
Plaintext: sections type (1) | length (uint32 LE) | data. Layout: KeyFirmware src/core/diag_record.h.
"""
import base64
import binascii
import json
import struct
import zlib
from dataclasses import dataclass
from typing import Dict

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from keycomm.core.constants import CHAR_ENCODING_UTF8, DIAG_ARMOR_BEGIN, DIAG_ARMOR_END
from keyadmin.core.constants import (
    DIAG_STREAM_VERSION, DIAG_STREAM_IV_LEN, DIAG_STREAM_TAG_LEN, DIAG_SECTION_HDR_FORMAT,
    DIAG_SECTION_PC, DIAG_SECTION_RECORD, DIAG_SECTION_TLOG, DIAG_SECTION_RAMLOG,
    DIAG_ERR_NO_PAYLOAD, DIAG_ERR_PAYLOAD_INVALID, DIAG_ERR_STREAM_FORMAT,
)
from keyadmin.secure_debug.sealed_record_decoder import SealedRecord, decode_record
from keyadmin.secure_debug.tamper_log_decoder import TamperRecord, parse as parse_tamper_log

HEADER_LEN = 1 + DIAG_STREAM_IV_LEN
SECTION_HDR_LEN = struct.calcsize(DIAG_SECTION_HDR_FORMAT)


@dataclass
class DiagContent:
    pc: dict                # PC facts as the customer PC sent them
    record: SealedRecord    # dongle record
    tamper_log: TamperRecord
    ramlog: str


def extract_armored(text: str) -> bytes:
    """The base64 between the BEGIN/END lines; tolerates mail quoting, indentation and line breaks."""
    start, end = text.find(DIAG_ARMOR_BEGIN), text.find(DIAG_ARMOR_END)
    if start < 0 or end < start:
        raise ValueError(DIAG_ERR_NO_PAYLOAD)
    body = text[start + len(DIAG_ARMOR_BEGIN):end]
    try:
        return base64.b64decode("".join(ch for ch in body if ch.isalnum() or ch in "+/="), validate=True)
    except binascii.Error as e:
        raise ValueError(DIAG_ERR_PAYLOAD_INVALID) from e


def _sections(plain: bytes) -> Dict[int, bytes]:
    sections, pos = {}, 0
    while pos < len(plain):
        if pos + SECTION_HDR_LEN > len(plain):
            raise ValueError(DIAG_ERR_STREAM_FORMAT)
        kind, length = struct.unpack_from(DIAG_SECTION_HDR_FORMAT, plain, pos)
        pos += SECTION_HDR_LEN
        if pos + length > len(plain):
            raise ValueError(DIAG_ERR_STREAM_FORMAT)
        sections[kind] = plain[pos:pos + length]
        pos += length
    return sections


def open_stream(blob: bytes, tamper_log_key: bytes) -> DiagContent:
    if len(blob) < HEADER_LEN + DIAG_STREAM_TAG_LEN or blob[0] != DIAG_STREAM_VERSION:
        raise ValueError(DIAG_ERR_PAYLOAD_INVALID)
    try:
        plain = AESGCM(tamper_log_key).decrypt(blob[1:HEADER_LEN], blob[HEADER_LEN:], blob[:1])
    except InvalidTag as e:
        raise ValueError(DIAG_ERR_PAYLOAD_INVALID) from e
    sections = _sections(plain)
    if not {DIAG_SECTION_PC, DIAG_SECTION_RECORD, DIAG_SECTION_TLOG, DIAG_SECTION_RAMLOG} <= sections.keys():
        raise ValueError(DIAG_ERR_STREAM_FORMAT)
    pc_raw = sections[DIAG_SECTION_PC]
    return DiagContent(
        pc=json.loads(zlib.decompress(pc_raw).decode(CHAR_ENCODING_UTF8)) if pc_raw else {},
        record=decode_record(sections[DIAG_SECTION_RECORD]),
        tamper_log=parse_tamper_log(sections[DIAG_SECTION_TLOG], tamper_log_key),
        ramlog=sections[DIAG_SECTION_RAMLOG].split(b"\0", 1)[0].decode(CHAR_ENCODING_UTF8, errors="replace"),
    )
