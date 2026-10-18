from enum import Enum


class LicenseState(Enum):
    """Enumeration of possible firmware license states."""
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    NO_RTC = "NO_RTC"
    NO_LICENSE = "NO_LICENSE"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"
