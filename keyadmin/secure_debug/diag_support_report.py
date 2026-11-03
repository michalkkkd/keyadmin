"""
Readable support view of a decrypted diagnostic payload: every check with its internal meaning,
the raw errors, the PC and Compass details, the decoded dongle record, tamper log and logs. KeySec admin only.
"""
import json
from typing import List

from keycomm.core.constants import (
    DIAG_KEY_TOOL, DIAG_KEY_TIME, DIAG_KEY_PC, DIAG_KEY_PORTS, DIAG_KEY_PROCESSES, DIAG_KEY_USB, DIAG_KEY_CHECKS,
    DIAG_KEY_ERRORS, DIAG_KEY_LINK, DIAG_KEY_SEALED, DIAG_KEY_TLOG, DIAG_KEY_RAMLOG, DIAG_KEY_APP, DIAG_LINE_FMT,
)
from keyadmin.core.constants import (
    DIAG_CODE_MEANINGS, DIAG_RESULT_MEANINGS, DIAG_EXPLAIN_FMT, DIAG_EXPLAIN_DETAIL_FMT, DIAG_CODE_APP_CRASH,
)
from keyadmin.secure_debug.diag_evaluator import DiagEvaluator
from keyadmin.secure_debug.sealed_record_decoder import (
    decode_sealed, decode_sealed_tamper_log, format_sealed_record,
)
from keyadmin.secure_debug.tamper_log_decoder import format_report as format_tamper_log


def explain(code: str, result: str) -> str:
    detail = DIAG_RESULT_MEANINGS.get(f"{code} {result}", "")
    return DIAG_EXPLAIN_FMT.format(line=DIAG_LINE_FMT.format(code=code, result=result),
                                   meaning=DIAG_CODE_MEANINGS.get(code, "?"),
                                   detail=DIAG_EXPLAIN_DETAIL_FMT.format(detail=detail) if detail else "")


def _section(title: str, lines: List[str]) -> List[str]:
    return ["", title] + (lines or ["  (none)"])


def _key_values(data: dict) -> List[str]:
    return [f"  {k:<15} : {v}" for k, v in data.items()]


def _pc_lines(payload: dict) -> List[str]:
    lines = _key_values(payload.get(DIAG_KEY_PC, {}))
    lines.append(f"  {'link':<15} : {payload.get(DIAG_KEY_LINK) or 'not measured'}")
    lines.append(f"  {'processes':<15} : {payload.get(DIAG_KEY_PROCESSES) or 'none of interest'}")
    lines += _section("[COM PORTS]", [f"  {p}" for p in payload.get(DIAG_KEY_PORTS, [])])
    usb = payload.get(DIAG_KEY_USB, [])
    usb_lines = [f"  {json.dumps(d, ensure_ascii=False)}" for d in (usb if isinstance(usb, list) else [usb])]
    return lines + _section("[USB DRIVERS]", usb_lines)


def _app_lines(app: dict) -> List[str]:
    scalars = {k: v for k, v in app.items() if not isinstance(v, list)}
    lines = _key_values(scalars)
    for key in (k for k, v in app.items() if isinstance(v, list)):
        lines += _section(f"[COMPASS {key.upper()}]", [f"  {line}" for line in app[key]])
    return lines


def format_support_report(payload: dict, tamper_log_key: bytes) -> str:
    lines: List[str] = [f"[PC]  report time {payload.get(DIAG_KEY_TIME, '?')}, tool v{payload.get(DIAG_KEY_TOOL, '?')}"]
    lines += _pc_lines(payload)

    checks = [explain(code, result) for code, result in payload.get(DIAG_KEY_CHECKS, [])]
    record = None
    sealed_hex = payload.get(DIAG_KEY_SEALED, "")
    if sealed_hex:
        record = decode_sealed(bytes.fromhex(sealed_hex), tamper_log_key)
        checks += [explain(code, result) for code, result in DiagEvaluator().evaluate(record)]
    app = payload.get(DIAG_KEY_APP, {})
    if app:
        checks.append(explain(DIAG_CODE_APP_CRASH, "WARN_1" if app.get("crash_report") else "PASS"))
    lines += _section("[CHECKS]", checks)
    lines += _section("[ERRORS]", [f"  {code}: {text}" for code, text in payload.get(DIAG_KEY_ERRORS, {}).items()])

    if record is not None:
        lines += ["", format_sealed_record(record)]
    tlog_hex = payload.get(DIAG_KEY_TLOG, "")
    if tlog_hex:
        lines += ["", "[TAMPER LOG]  (persistent, User Data page)",
                  format_tamper_log(decode_sealed_tamper_log(bytes.fromhex(tlog_hex), tamper_log_key))]
    ramlog = [f"  {l}" for l in payload.get(DIAG_KEY_RAMLOG, "").splitlines() if l.strip()]
    lines += _section("[DONGLE RAM LOG]  (oldest first)", ramlog)
    if app:
        lines += _section("[COMPASS]", _app_lines(app))
    return "\n".join(lines)
