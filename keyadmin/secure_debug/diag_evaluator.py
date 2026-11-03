from typing import List, Tuple

from keyadmin.core.constants import (
    DIAG_CODE_LICENSE, DIAG_CODE_LICENSE_DAYS, DIAG_CODE_CLOCK, DIAG_CODE_USERS, DIAG_CODE_BATTERY,
    DIAG_CODE_TEMPERATURE, DIAG_CODE_NVM, DIAG_CODE_RESET_CAUSE, DIAG_CODE_TAMPER,
    DIAG_CODE_RESET_HISTORY, DIAG_CODE_SESSION, DIAG_CODE_FRAMES, DIAG_CODE_IDENTITY, DIAG_CODE_DEBUG_LOCK,
    DIAG_CODE_CMD_ERRORS, DIAG_CODE_BATTERY_DIP, DIAG_CODE_TEMP_RANGE, DIAG_BATTERY_DIP_MV,
    DIAG_SEALED_FLAG_CERT,
    DIAG_LICENSE_DAYS_WARN, DIAG_CLOCK_WARN_S, DIAG_CLOCK_BAD_S,
    DIAG_BATTERY_LOW_PCT, DIAG_BATTERY_CRITICAL_PCT, DIAG_BATTERY_UNKNOWN_PCT,
    DIAG_TEMP_OK_MIN_X10, DIAG_TEMP_OK_MAX_X10, DIAG_TEMP_LIMIT_MIN_X10, DIAG_TEMP_LIMIT_MAX_X10,
    DIAG_NVM_FREE_WARN_PCT,
    RSTCAUSE_WDOG_MASK, RSTCAUSE_LOCKUP_MASK, RSTCAUSE_BROWNOUT_MASK, RSTCAUSE_SE_TAMPER_MASK,
)
from keyadmin.secure_debug.sealed_record_decoder import SealedRecord

PASS = "PASS"
LICENSE_VALID, LICENSE_EXPIRED, LICENSE_NO_LICENSE, LICENSE_NO_RTC = 0, 1, 2, 3  # license_status_code_t

Check = Tuple[str, str]


def warn(n: int) -> str:
    return f"WARN_{n}"


def fail(n: int) -> str:
    return f"FAIL_{n}"


class DiagEvaluator:
    """Judges the decrypted dongle record (KeySec admin only: Compass carries no thresholds)."""

    def evaluate(self, rec: SealedRecord) -> List[Check]:
        license_valid = rec.lic_status == LICENSE_VALID
        return [
            (DIAG_CODE_LICENSE, self.license(rec)),
            (DIAG_CODE_LICENSE_DAYS, self.license_days(rec) if license_valid else "SKIP"),
            (DIAG_CODE_CLOCK, self.clock(rec)),
            (DIAG_CODE_USERS, self.users(rec)),
            (DIAG_CODE_BATTERY, self.battery(rec)),
            (DIAG_CODE_TEMPERATURE, self.temperature(rec)),
            (DIAG_CODE_NVM, self.nvm(rec)),
            (DIAG_CODE_RESET_CAUSE, self.reset_cause(rec)),
            (DIAG_CODE_TAMPER, self.tamper(rec)),
            (DIAG_CODE_RESET_HISTORY, self.reset_history(rec)),
            (DIAG_CODE_SESSION, self.session(rec)),
            (DIAG_CODE_FRAMES, warn(1) if rec.tf_cksum_errors else PASS),
            (DIAG_CODE_IDENTITY, self.identity(rec)),
            (DIAG_CODE_DEBUG_LOCK, self.debug_lock(rec)),
            (DIAG_CODE_CMD_ERRORS, warn(1) if rec.errors else PASS),
            (DIAG_CODE_BATTERY_DIP, self.battery_dip(rec)),
            (DIAG_CODE_TEMP_RANGE, self.temp_range(rec)),
        ]

    @staticmethod
    def license(rec: SealedRecord) -> str:
        failures = {LICENSE_EXPIRED: fail(1), LICENSE_NO_LICENSE: fail(2), LICENSE_NO_RTC: fail(3)}
        return PASS if rec.lic_status == LICENSE_VALID else failures.get(rec.lic_status, fail(4))

    @staticmethod
    def license_days(rec: SealedRecord) -> str:
        return warn(1) if rec.lic_remaining_days <= DIAG_LICENSE_DAYS_WARN else PASS

    @staticmethod
    def clock(rec: SealedRecord) -> str:
        drift = abs(rec.clock_diff_s)
        if drift > DIAG_CLOCK_BAD_S:
            return warn(2)
        return warn(1) if drift > DIAG_CLOCK_WARN_S else PASS

    @staticmethod
    def users(rec: SealedRecord) -> str:
        if rec.user_limit == 0:
            return fail(1)
        return warn(1) if rec.active_users >= rec.user_limit else PASS

    @staticmethod
    def battery(rec: SealedRecord) -> str:
        if rec.battery_pct == DIAG_BATTERY_UNKNOWN_PCT:
            return fail(2)
        if rec.battery_pct < DIAG_BATTERY_CRITICAL_PCT:
            return fail(1)
        return warn(1) if rec.battery_pct < DIAG_BATTERY_LOW_PCT else PASS

    @staticmethod
    def temperature(rec: SealedRecord) -> str:
        if not DIAG_TEMP_LIMIT_MIN_X10 <= rec.temp_x10 <= DIAG_TEMP_LIMIT_MAX_X10:
            return fail(1)
        return PASS if DIAG_TEMP_OK_MIN_X10 <= rec.temp_x10 <= DIAG_TEMP_OK_MAX_X10 else warn(1)

    @staticmethod
    def nvm(rec: SealedRecord) -> str:
        if rec.nvm_total == 0:
            return fail(1)
        return warn(1) if rec.nvm_free * 100 < rec.nvm_total * DIAG_NVM_FREE_WARN_PCT else PASS

    @staticmethod
    def reset_cause(rec: SealedRecord) -> str:
        cause = rec.reset_cause
        if cause & RSTCAUSE_SE_TAMPER_MASK:
            return fail(1)
        if cause & RSTCAUSE_BROWNOUT_MASK:
            return warn(1)
        if cause & RSTCAUSE_WDOG_MASK:
            return warn(2)
        return warn(3) if cause & RSTCAUSE_LOCKUP_MASK else PASS

    @staticmethod
    def reset_history(rec: SealedRecord) -> str:
        if rec.resets_se_tamper:
            return fail(1)
        if rec.resets_brownout:
            return warn(1)
        if rec.resets_wdog:
            return warn(2)
        return warn(3) if rec.resets_lockup else PASS

    @staticmethod
    def session(rec: SealedRecord) -> str:
        if rec.handshakes_rejected:
            return warn(1)
        return warn(2) if rec.decrypt_failures else PASS

    @staticmethod
    def identity(rec: SealedRecord) -> str:
        if not rec.flags & DIAG_SEALED_FLAG_CERT:
            return fail(1)
        return fail(2) if not any(rec.identity_fp) else PASS

    @staticmethod
    def debug_lock(rec: SealedRecord) -> str:
        applied, active = rec.debug_lock & 0x02, rec.debug_lock & 0x04
        if not applied:
            return warn(1)
        return PASS if active else warn(2)

    @staticmethod
    def battery_dip(rec: SealedRecord) -> str:
        return warn(1) if 0 < rec.vbat_min_mv < DIAG_BATTERY_DIP_MV else PASS

    @staticmethod
    def temp_range(rec: SealedRecord) -> str:
        in_range = DIAG_TEMP_OK_MIN_X10 <= rec.temp_min_x10 and rec.temp_max_x10 <= DIAG_TEMP_OK_MAX_X10
        return PASS if in_range else warn(1)

    @staticmethod
    def tamper(rec: SealedRecord) -> str:
        if rec.tamper_events:
            return warn(1)
        return warn(2) if rec.tamper_log_count else PASS
