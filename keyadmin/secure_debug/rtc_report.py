"""
The clock and license report of the factory firmware (MSG_DEBUG_TIME, security_rtc_get_time_report()), rebuilt
line for line from the DIAG record. Production firmware answers no plaintext diagnostics; the record carries every
value of the report (v6), measured at MSG_DIAG_BEGIN together with the PC time.
"""
from keyadmin.core.constants import (
    RTC_REPORT_HEADER, RTC_REPORT_LINES, RTC_MATCH_WINDOW_S, RTC_VERDICT_MATCH, RTC_VERDICT_AHEAD,
    RTC_VERDICT_BEHIND, RTC_LICENSE_STATUS,
)
from keyadmin.secure_debug.sealed_record_decoder import SealedRecord, SECONDS_PER_DAY, utc


def _diff_s(dongle_time: int, pc_time: int) -> int:
    """(int32_t)(mcu_time - win_time), as the firmware computes it."""
    diff = (dongle_time - pc_time) & 0xFFFFFFFF
    return diff - (1 << 32) if diff >= (1 << 31) else diff


def format_rtc_report(rec: SealedRecord) -> str:
    diff = _diff_s(rec.dongle_time, rec.pc_time)
    if abs(diff) <= RTC_MATCH_WINDOW_S:
        verdict = RTC_VERDICT_MATCH
    else:
        verdict = RTC_VERDICT_AHEAD if diff > 0 else RTC_VERDICT_BEHIND
    lic_end = rec.lic_start + rec.lic_days * SECONDS_PER_DAY
    if rec.lic_start == 0 or lic_end > 0xFFFFFFFF:
        lic_end = 0
    status = RTC_LICENSE_STATUS[rec.lic_status] if rec.lic_status < len(RTC_LICENSE_STATUS) else RTC_LICENSE_STATUS[-1]
    values = dict(
        now=rec.dongle_time, now_str=utc(rec.dongle_time), pc=rec.pc_time, pc_str=utc(rec.pc_time),
        diff=diff, verdict=verdict,
        start=rec.lic_start, start_str=utc(rec.lic_start), end=lic_end, end_str=utc(lic_end), days=rec.lic_days,
        status=status, used=rec.lic_elapsed_days, left=rec.lic_remaining_days,
        boot=rec.boot_base_time, boot_str=utc(rec.boot_base_time), penalty=rec.rtc_reset_penalty_s,
        uptime=rec.uptime_s, uptime_min=rec.uptime_s // 60, tick_hz=rec.rtc_tick_hz,
        saved=rec.persisted_time, saved_str=utc(rec.persisted_time), checkpoint=rec.rtc_checkpoint_s,
    )
    return "\n".join([RTC_REPORT_HEADER] + [line.format(**values) for line in RTC_REPORT_LINES])
