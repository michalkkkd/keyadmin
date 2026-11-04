"""
Readable support view of a decrypted DIAG stream: every check with its internal meaning, the PC and Compass
facts, the dongle record, tamper log and RAM log. KeySec admin only.
"""
import json
from typing import List

from keycomm.core.constants import (
    DIAG_KEY_TOOL, DIAG_KEY_TIME, DIAG_KEY_PC, DIAG_KEY_PORTS, DIAG_KEY_PROCESSES, DIAG_KEY_USB,
    DIAG_KEY_ROOT_CA, DIAG_KEY_HANDSHAKE, DIAG_KEY_LINK, DIAG_KEY_APP,
)
from keyadmin.core.constants import (
    DIAG_CODE_MEANINGS, DIAG_RESULT_MEANINGS, DIAG_EXPLAIN_FMT, DIAG_EXPLAIN_DETAIL_FMT, DIAG_CODE_APP_CRASH,
    DIAG_PASS, DIAG_WARN_FMT, DIAG_LINE_FMT,
)
from keyadmin.secure_debug.diag_evaluator import DiagEvaluator
from keyadmin.secure_debug.diag_host_evaluator import DiagHostEvaluator
from keyadmin.secure_debug.diag_stream_decoder import DiagContent
from keyadmin.secure_debug.sealed_record_decoder import format_sealed_record
from keyadmin.secure_debug.rtc_report import format_rtc_report
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


def _pc_lines(pc: dict) -> List[str]:
    lines = _key_values(pc.get(DIAG_KEY_PC, {}))
    for key in (DIAG_KEY_ROOT_CA, DIAG_KEY_HANDSHAKE, DIAG_KEY_LINK, DIAG_KEY_PROCESSES):
        lines.append(f"  {key:<15} : {pc.get(key)!r}")
    lines += _section("[COM PORTS]", [f"  {p}" for p in pc.get(DIAG_KEY_PORTS, [])])
    usb = pc.get(DIAG_KEY_USB, [])
    usb_lines = [f"  {json.dumps(d, ensure_ascii=False)}" for d in (usb if isinstance(usb, list) else [usb])]
    return lines + _section("[USB DRIVERS]", usb_lines)


def _app_lines(app: dict) -> List[str]:
    lines = _key_values({k: v for k, v in app.items() if not isinstance(v, list)})
    for key in (k for k, v in app.items() if isinstance(v, list)):
        lines += _section(f"[COMPASS {key.upper()}]", [f"  {line}" for line in app[key]])
    return lines


def format_support_report(content: DiagContent) -> str:
    pc, rec = content.pc, content.record
    lines: List[str] = [f"[PC]  report time {pc.get(DIAG_KEY_TIME, '?')}, tool v{pc.get(DIAG_KEY_TOOL, '?')}"]
    lines += _pc_lines(pc)

    checks = [explain(code, result) for code, result in DiagHostEvaluator().evaluate(pc, rec)]
    checks += [explain(code, result) for code, result in DiagEvaluator().evaluate(rec)]
    app = pc.get(DIAG_KEY_APP, {})
    if app:
        checks.append(explain(DIAG_CODE_APP_CRASH, DIAG_WARN_FMT.format(n=1) if app.get("crash_report") else DIAG_PASS))
    lines += _section("[CHECKS]", checks)

    lines += ["", format_sealed_record(rec)]
    lines.append(format_rtc_report(rec))
    lines += ["", "[TAMPER LOG]  (persistent, User Data page)", format_tamper_log(content.tamper_log)]
    lines += _section("[DONGLE RAM LOG]  (oldest first)", [f"  {l}" for l in content.ramlog.splitlines() if l.strip()])
    if app:
        lines += _section("[COMPASS]", _app_lines(app))
    return "\n".join(lines)
