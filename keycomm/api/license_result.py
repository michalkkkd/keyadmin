import re
from typing import Optional

from keycomm.api.license_state import LicenseState
from keycomm.core.constants import (
    RE_DAYS_PASSED,
    RE_REMAINING_DAYS,
    RE_VRX_TOKEN,
    TOKEN_VALID,
    TOKEN_EXPIRED,
    TOKEN_RTC_NOT_SYNCHRONIZED,
    TOKEN_NO_RTC,
    TOKEN_NO_LICENSE,
    TOKEN_NO_LICENSE_UNDERSCORE,
    TOKEN_ERR,
    TOKEN_FAIL,
)


class LicenseResult(str):
    """
    Strongly-typed license verification result.
    Inherits from str for complete backward compatibility with string operations
    while providing structured fields and an Enum state.
    """
    state: LicenseState
    days_passed: Optional[int]
    remaining_days: Optional[int]
    vrx_token: int
    raw: str

    def __new__(cls, content: str = ""):
        obj = super().__new__(cls, content)
        obj.raw = str(content)
        obj._parse()
        return obj

    def _parse(self) -> None:
        s = self.raw
        upper = s.upper()

        if TOKEN_VALID in upper and TOKEN_ERR not in upper:
            self.state = LicenseState.VALID
        elif TOKEN_EXPIRED in upper:
            self.state = LicenseState.EXPIRED
        elif TOKEN_RTC_NOT_SYNCHRONIZED in upper or TOKEN_NO_RTC in upper:
            self.state = LicenseState.NO_RTC
        elif TOKEN_NO_LICENSE in upper or TOKEN_NO_LICENSE_UNDERSCORE in upper:
            self.state = LicenseState.NO_LICENSE
        elif TOKEN_ERR in upper or TOKEN_FAIL in upper:
            self.state = LicenseState.ERROR
        else:
            self.state = LicenseState.UNKNOWN

        self.days_passed = None
        m_days = re.search(RE_DAYS_PASSED, s, re.IGNORECASE)
        if m_days:
            self.days_passed = int(m_days.group(1))

        self.remaining_days = None
        m_rem = re.search(RE_REMAINING_DAYS, s, re.IGNORECASE)
        if m_rem:
            self.remaining_days = int(m_rem.group(1))

        self.vrx_token = 0
        m_vrx = re.search(RE_VRX_TOKEN, s)
        if m_vrx:
            tok_str = m_vrx.group(1)
            try:
                self.vrx_token = int(tok_str, 10)
            except ValueError:
                try:
                    self.vrx_token = int(tok_str, 16)
                except ValueError:
                    self.vrx_token = 0


    @property
    def is_valid(self) -> bool:
        return self.state == LicenseState.VALID

    def __bool__(self) -> bool:
        return self.is_valid
