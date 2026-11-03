from typing import List, Tuple

from keycomm.core.constants import DIAG_KEY_ROOT_CA, DIAG_KEY_HANDSHAKE, DIAG_KEY_LINK, DIAG_HANDSHAKE_REJECTED
from keyadmin.core.constants import (
    DIAG_PASS, DIAG_WARN_FMT, DIAG_FAIL_FMT, DIAG_CODE_ROOT_CA, DIAG_CODE_HANDSHAKE, DIAG_CODE_LINK,
    DIAG_SESSION_ACTIVE,
)
from keyadmin.secure_debug.sealed_record_decoder import SealedRecord

Check = Tuple[str, str]


class DiagHostEvaluator:
    """Judges the PC facts (a payload exists, so the PC found, opened and reached the dongle)."""

    def evaluate(self, pc: dict, rec: SealedRecord) -> List[Check]:
        return [
            (DIAG_CODE_ROOT_CA, DIAG_PASS if pc.get(DIAG_KEY_ROOT_CA) else DIAG_FAIL_FMT.format(n=1)),
            (DIAG_CODE_HANDSHAKE, self.handshake(pc, rec)),
            (DIAG_CODE_LINK, self.link(pc)),
        ]

    @staticmethod
    def handshake(pc: dict, rec: SealedRecord) -> str:
        if rec.session & DIAG_SESSION_ACTIVE:
            return DIAG_PASS
        return DIAG_FAIL_FMT.format(n=1 if pc.get(DIAG_KEY_HANDSHAKE) == DIAG_HANDSHAKE_REJECTED else 2)

    @staticmethod
    def link(pc: dict) -> str:
        link = pc.get(DIAG_KEY_LINK) or {}
        return DIAG_WARN_FMT.format(n=1) if any(link.values()) else DIAG_PASS
