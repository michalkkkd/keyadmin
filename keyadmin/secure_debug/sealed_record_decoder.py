"""
Decoder for the dongle record of the DIAG stream (section DIAG_SECTION_RECORD, already decrypted by
diag_stream_decoder.py). Layout: KeyFirmware src/core/diag_record.h (_Static_assert on the size).
"""
import struct
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Tuple

from keyadmin.core.constants import (
    DIAG_SEALED_RECORD_VERSION, DIAG_SEALED_RECORD_MIN_VERSION, DIAG_SEALED_MAGIC, DIAG_SEALED_FLAG_PROV, DIAG_SEALED_FLAG_LIVE_WIPE,
    DIAG_SEALED_FLAG_CERT, DIAG_SEALED_NO_TREND, DIAG_SESSION_ACTIVE, DIAG_USAGE_NAMES,
    DIAG_ERR_SEALED_LEN_FMT, DIAG_ERR_SEALED_INVALID,
)
from keyadmin.secure_debug.tamper_log_decoder import type_name

# diag_sealed_record_t, field by field (packed, little-endian)
RECORD_FIELDS = (
    ("magic", "H"), ("version", "B"), ("flags", "B"),
    ("fw_version", "I"), ("pc_time", "I"), ("dongle_time", "I"), ("lic_start", "I"), ("lic_days", "I"),
    ("boot_base_time", "I"), ("persisted_time", "I"), ("uptime_s", "I"), ("reset_cause", "I"),
    ("nvm_free", "I"), ("nvm_total", "I"), ("nvm_erase_count", "I"),
    ("eui64", "Q"), ("identity_fp", "8s"), ("cert_fp", "8s"),
    ("lic_remaining_days", "H"), ("lic_status", "B"), ("active_users", "B"), ("user_limit", "H"),
    ("tamper_events", "H"), ("tamper_log_count", "B"), ("battery_pct", "B"), ("debug_lock", "B"), ("session", "B"),
    ("tamper_counts", "10s"),
    ("vbat_now_mv", "H"), ("vbat_avg_mv", "H"), ("vbat_min_mv", "H"),
    ("vbat_trend_mv_10min", "h"), ("temp_x10", "h"), ("temp_min_x10", "h"), ("temp_max_x10", "h"),
    ("usage_counts", "7I"),
    ("boots", "I"), ("resets_por", "H"), ("resets_pin", "H"), ("resets_sysreq", "H"), ("resets_wdog", "H"),
    ("resets_brownout", "H"), ("resets_lockup", "H"), ("resets_se_tamper", "H"),
    ("handshakes_rejected", "H"), ("decrypt_failures", "H"), ("tf_cksum_errors", "H"),
    ("errors", "64s"),
    ("lic_elapsed_days", "H"), ("rtc_reset_penalty_s", "H"), ("rtc_checkpoint_s", "H"), ("rtc_tick_hz", "I"),
    ("em0_s", "I"), ("em1_s", "I"), ("em2_s", "I"), ("em2_entries", "H"), ("crc32", "I"),
)
RECORD_FORMAT = "<" + "".join(f for _, f in RECORD_FIELDS)
RECORD_SIZE = struct.calcsize(RECORD_FORMAT)  # 256 = sixteen AES blocks
ERROR_ENTRY_FORMAT = "<IB11s"                 # diag_error_entry_t
ERROR_ENTRY_SIZE = struct.calcsize(ERROR_ENTRY_FORMAT)
SECONDS_PER_DAY = 86400
LICENSE_STATUS_NAMES = ("valid", "expired", "no license", "no clock (RTC)")  # license_status_code_t
DEBUG_KEY_STATES = ("no key in OTP", "OTP key matches firmware", "OTP key MISMATCH")

# EMU->RSTCAUSE bits (efr32mg24_emu.h)
RESET_CAUSE_NAMES = (
    (0, "POR"), (1, "PIN"), (2, "EM4"), (3, "WDOG0"), (4, "WDOG1"), (5, "LOCKUP"), (6, "SYSREQ"),
    (7, "DVDDBOD"), (8, "DVDDLEBOD"), (9, "DECBOD"), (10, "AVDDBOD"), (11, "IOVDD0BOD"), (13, "SETAMPER"),
    (31, "VREGIN"),
)
# Secure command types (router_common.h, prod_router.h) for the error ring
COMMAND_NAMES = {
    0x02: "CHECK_LIC", 0x06: "TEST_ADD", 0x09: "COMPASS_USERS", 0x11: "GET_LOG_SIZE", 0x12: "GET_LOG_CHUNK",
    0x13: "DIAG", 0x14: "DIAG_TLOG", 0x15: "COMPASS_SIM_PK", 0x16: "VRX",
    0x30: "SIM_PK_GI_INIT", 0x31: "SIM_PK_GI_CHUNK", 0x32: "SIM_PK_GI_PROCESS", 0x33: "SIM_PK_GI_READ",
    0x40: "SAFE_SPACE_INIT", 0x41: "SAFE_SPACE_CHUNK", 0x42: "SAFE_SPACE_PROCESS", 0x43: "SAFE_SPACE_READ",
    0x44: "SAFE_SPACE_RESET", 0x45: "SAFE_SPACE_FINISH",
    0x50: "SSP_A_INIT", 0x51: "SSP_A_CHUNK", 0x52: "SSP_A_PROCESS", 0x53: "SSP_A_READ", 0x54: "SSP_B_REQ",
    0x55: "SSP_C_INIT", 0x56: "SSP_C_CHUNK", 0x57: "SSP_C_PROCESS", 0x58: "SSP_C_READ",
}


@dataclass
class CommandError:
    dongle_time: int
    cmd: int
    text: str


@dataclass
class SealedRecord:
    version: int
    flags: int
    fw_version: int
    pc_time: int
    dongle_time: int
    lic_start: int
    lic_days: int
    boot_base_time: int
    persisted_time: int
    uptime_s: int
    reset_cause: int
    nvm_free: int
    nvm_total: int
    nvm_erase_count: int
    eui64: int
    identity_fp: bytes
    cert_fp: bytes
    lic_remaining_days: int
    lic_status: int
    active_users: int
    user_limit: int
    tamper_events: int
    tamper_log_count: int
    battery_pct: int
    debug_lock: int
    session: int
    tamper_counts: Tuple[int, ...]
    vbat_now_mv: int
    vbat_avg_mv: int
    vbat_min_mv: int
    vbat_trend_mv_10min: int
    temp_x10: int
    temp_min_x10: int
    temp_max_x10: int
    usage_counts: Tuple[int, ...]
    boots: int
    resets_por: int
    resets_pin: int
    resets_sysreq: int
    resets_wdog: int
    resets_brownout: int
    resets_lockup: int
    resets_se_tamper: int
    handshakes_rejected: int
    decrypt_failures: int
    tf_cksum_errors: int
    errors: List[CommandError]
    lic_elapsed_days: int
    rtc_reset_penalty_s: int
    rtc_checkpoint_s: int
    rtc_tick_hz: int
    em0_s: int
    em1_s: int
    em2_s: int
    em2_entries: int

    @property
    def clock_diff_s(self) -> int:
        return self.dongle_time - self.pc_time


def _parse_errors(raw: bytes) -> List[CommandError]:
    errors = []
    for i in range(0, len(raw), ERROR_ENTRY_SIZE):
        ts, cmd, text = struct.unpack(ERROR_ENTRY_FORMAT, raw[i:i + ERROR_ENTRY_SIZE])
        if ts or cmd:
            errors.append(CommandError(ts, cmd, text.split(b"\0", 1)[0].decode("ascii", errors="replace")))
    return errors


def decode_record(plain: bytes) -> SealedRecord:
    if len(plain) != RECORD_SIZE:
        raise ValueError(DIAG_ERR_SEALED_LEN_FMT.format(size=len(plain), expected=RECORD_SIZE))
    values = struct.unpack(RECORD_FORMAT, plain)
    fields = {}
    i = 0
    for name, fmt in RECORD_FIELDS:
        if fmt == "7I":
            fields[name] = tuple(values[i:i + 7])
            i += 7
        else:
            fields[name] = values[i]
            i += 1
    if (fields["magic"] != DIAG_SEALED_MAGIC
            or not DIAG_SEALED_RECORD_MIN_VERSION <= fields["version"] <= DIAG_SEALED_RECORD_VERSION
            or zlib.crc32(plain[:-4]) != fields["crc32"]):
        raise ValueError(DIAG_ERR_SEALED_INVALID)
    fields["tamper_counts"] = tuple(fields["tamper_counts"])
    fields["errors"] = _parse_errors(fields["errors"])
    for name in ("magic", "crc32"):
        del fields[name]
    return SealedRecord(**fields)


def utc(ts: int) -> str:
    if ts == 0:
        return "not set"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def reset_cause_names(raw: int) -> str:
    names = [name for bit, name in RESET_CAUSE_NAMES if raw & (1 << bit)]
    return ", ".join(names) if names else "none"


def _energy_modes(rec: SealedRecord) -> str:
    """Time per energy mode since boot: shows whether the dongle really sleeps (EM2) on battery."""
    if rec.version < 7:
        return f"not in record v{rec.version}"
    total = rec.em0_s + rec.em1_s + rec.em2_s
    if total == 0:
        return "no data"
    share = ", ".join(f"{name} {sec} s ({100.0 * sec / total:.1f} %)"
                      for name, sec in (("EM0 run", rec.em0_s), ("EM1 idle", rec.em1_s), ("EM2 sleep", rec.em2_s)))
    return f"{share}; {rec.em2_entries} EM2 entries"


def _debug_lock(flags: int) -> str:
    parts = [name for bit, name in ((0x01, "secure debug on"), (0x02, "lock applied"), (0x04, "lock ACTIVE"),
                                    (0x08, "device erase allowed")) if flags & bit]
    key_state = (flags >> 4) & 0x3
    parts.append(DEBUG_KEY_STATES[key_state] if key_state < len(DEBUG_KEY_STATES) else f"key state {key_state}")
    return ", ".join(parts)


def format_sealed_record(rec: SealedRecord) -> str:
    fw = f"{rec.fw_version >> 16}.{(rec.fw_version >> 8) & 0xFF}.{rec.fw_version & 0xFF}"
    build = "provisioning" if rec.flags & DIAG_SEALED_FLAG_PROV else "production"
    wipe = "live (device erase)" if rec.flags & DIAG_SEALED_FLAG_LIVE_WIPE else "dev (NVM3 only)"
    lic_end = rec.lic_start + rec.lic_days * SECONDS_PER_DAY if rec.lic_start else 0
    status = LICENSE_STATUS_NAMES[rec.lic_status] if rec.lic_status < len(LICENSE_STATUS_NAMES) else rec.lic_status
    trend = "not enough samples yet" if rec.vbat_trend_mv_10min == DIAG_SEALED_NO_TREND \
        else f"{rec.vbat_trend_mv_10min:+d} mV / 10 min"
    battery = "read failed" if rec.vbat_now_mv == 0 else \
        f"{rec.battery_pct} %, now {rec.vbat_now_mv} mV, avg {rec.vbat_avg_mv} mV, min {rec.vbat_min_mv} mV, {trend}"
    cert = rec.cert_fp.hex().upper() if rec.flags & DIAG_SEALED_FLAG_CERT else "MISSING"
    lines = [
        "[DONGLE]  (times UTC)",
        f"  Chip ID (EUI64) : {rec.eui64:016X}",
        f"  Identity / cert : key {rec.identity_fp.hex().upper()}, certificate {cert}",
        f"  Firmware        : {fw} {build}, tamper wipe {wipe}, record v{rec.version}",
        f"  Debug lock      : {_debug_lock(rec.debug_lock)}",
        f"  Session         : {'open (Host Key handshake worked)' if rec.session & DIAG_SESSION_ACTIVE else 'NONE'}",
        f"  Dongle time     : {utc(rec.dongle_time)}  (PC {utc(rec.pc_time)}, dongle {rec.clock_diff_s:+d} s)",
        f"  License         : {status}, {rec.lic_remaining_days} days left; start {utc(rec.lic_start)}, "
        f"{rec.lic_days} days, end {utc(lic_end)}",
        f"  Clock at boot   : {utc(rec.boot_base_time)}  (last NVM3 save + reset penalty)",
        f"  Last NVM3 save  : {utc(rec.persisted_time)}",
        f"  Uptime          : {rec.uptime_s} s ({rec.uptime_s // 3600} h {rec.uptime_s % 3600 // 60} min)",
        f"  Reset cause     : 0x{rec.reset_cause:08X} ({reset_cause_names(rec.reset_cause)})",
        f"  Boots (lifetime): {rec.boots} total; POR {rec.resets_por}, pin {rec.resets_pin}, "
        f"software {rec.resets_sysreq}, watchdog {rec.resets_wdog}, brown-out {rec.resets_brownout}, "
        f"lockup {rec.resets_lockup}, SE tamper {rec.resets_se_tamper}",
        f"  Session (boot)  : {rec.handshakes_rejected} handshakes rejected, {rec.decrypt_failures} decrypt failures, "
        f"{rec.tf_cksum_errors} frames with bad checksum",
        f"  Users           : {rec.active_users} active of {rec.user_limit}",
        f"  NVM3            : {rec.nvm_free} B free of {rec.nvm_total} B, {rec.nvm_erase_count} page erases",
        f"  Tamper          : {rec.tamper_events} events since boot, {rec.tamper_log_count} entries in the log",
    ]
    lines += [f"      {type_name(i)}: {n}" for i, n in enumerate(rec.tamper_counts) if n]
    lines += [
        f"  Battery         : {battery}",
        f"  Energy modes    : {_energy_modes(rec)}",
        f"  Temperature     : {rec.temp_x10 / 10.0:.1f} C (since boot {rec.temp_min_x10 / 10.0:.1f} .. "
        f"{rec.temp_max_x10 / 10.0:.1f} C)",
        "  Algorithm runs  : (since provisioning, saved every 60 s)",
    ]
    lines += [f"      {name}: {n}" for name, n in zip(DIAG_USAGE_NAMES, rec.usage_counts)]
    lines.append(f"  Last errors     : {len(rec.errors) or 'none'} (newest first)")
    lines += [f"      {utc(e.dongle_time)}  {COMMAND_NAMES.get(e.cmd, f'0x{e.cmd:02X}')}: {e.text}" for e in rec.errors]
    return "\n".join(lines)
