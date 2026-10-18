import re

from keyadmin.core.constants import (
    RE_TAMPER_EVENTS,
    RE_TEMPERATURE,
    RE_BLACKBOX,
    BLACKBOX_STATE_NONE,
    TOKEN_ERR,
    TOKEN_FAIL,
)


class SystemHealthReport(str):
    """
    Strongly-typed report for device system health and anti-tamper status.
    Inherits from str for seamless backward compatibility.
    """
    tamper_events: int
    temperature_c: float
    blackbox_state: str
    is_tampered: bool
    is_error: bool
    raw: str

    def __new__(cls, content: str = ""):
        obj = super().__new__(cls, content)
        obj.raw = str(content)
        obj._parse()
        return obj

    def _parse(self) -> None:
        s = self.raw
        self.is_error = s.startswith(TOKEN_ERR) or TOKEN_FAIL in s.upper()

        self.tamper_events = 0
        m_tamper = re.search(RE_TAMPER_EVENTS, s)
        if m_tamper:
            self.tamper_events = int(m_tamper.group(1))

        self.temperature_c = 0.0
        m_temp = re.search(RE_TEMPERATURE, s)
        if m_temp:
            try:
                self.temperature_c = float(m_temp.group(1))
            except ValueError:
                self.temperature_c = 0.0

        self.blackbox_state = BLACKBOX_STATE_NONE
        m_bb = re.search(RE_BLACKBOX, s)
        if m_bb:
            self.blackbox_state = m_bb.group(1)

        self.is_tampered = not self.is_error and (self.tamper_events > 0)

