import os
import sys
import time
import random
import msvcrt

from keycomm.api.compass_api import CompassApi
from keycomm.core.constants import RESP_OK_PREFIX
from keyadmin.api.admin_api import AdminApi
from keyadmin.core.constants import (
    ADMIN_MENU_TITLE,
    ADMIN_PROMPT_PAUSE,
    ADMIN_PROMPT_NAV,
    ADMIN_SEC_DIAGNOSTICS,
    ADMIN_SEC_TESTING,
    ADMIN_SEC_HEARTBEAT,
    ADMIN_ACT_SYS_HEALTH,
    ADMIN_ACT_BATTERY,
    ADMIN_ACT_MEMORY,
    ADMIN_ACT_RTC,
    ADMIN_ACT_LICENSE,
    ADMIN_ACT_LOGS,
    ADMIN_ACT_BENCHMARK,
    ADMIN_ACT_HB_START,
    ADMIN_ACT_HB_DISABLE,
    ADMIN_ACT_EXIT,
    ACTION_SYS_HEALTH,
    ACTION_BATTERY_STATUS,
    ACTION_MEMORY_NVM,
    ACTION_RTC_DIAG,
    ACTION_LICENSE_USERS,
    ACTION_BENCHMARK,
    ACTION_DEVICE_LOGS,
    ACTION_HB_START,
    ACTION_HB_DISABLE,
    ACTION_EXIT,
    ADMIN_HDR_SYS_HEALTH,
    ADMIN_HDR_BATTERY,
    ADMIN_HDR_MEMORY,
    ADMIN_HDR_RTC,
    ADMIN_HDR_LICENSE,
    ADMIN_HDR_BENCHMARK,
    ADMIN_HDR_DEVICE_LOGS,
    ADMIN_HDR_HB_STATUS,
    ADMIN_HDR_HB_DISABLE,
    ADMIN_ALERT_TAMPER,
    ADMIN_MSG_LICENSE_PREFIX,
    ADMIN_MSG_MAX_USERS_PREFIX,
    ADMIN_MSG_HB_RESUMING,
    ADMIN_MSG_HB_RUNNING,
    ADMIN_MSG_HB_PAUSING,
    ADMIN_MSG_HB_EXPLANATION,
    ADMIN_MSG_HB_WAITING,
    ADMIN_MSG_HB_ASLEEP,
    ADMIN_MSG_HB_VERIFY_WAKE,
    ADMIN_DEFAULT_USER_EMAIL,
    ADMIN_BENCHMARK_ITERATIONS,
    ADMIN_BENCHMARK_LOG_STEP,
    ADMIN_MSG_BENCH_START_FMT,
    ADMIN_MSG_BENCH_ITER_FMT,
    ADMIN_MSG_BENCH_SUMMARY_HDR,
    ADMIN_MSG_BENCH_SUCCESS_FMT,
    ADMIN_MSG_BENCH_TOTAL_TIME,
    ADMIN_MSG_BENCH_AVG_TIME,
    ADMIN_MSG_BENCH_MIN_MAX_FMT,
    ADMIN_MSG_BENCH_THROUGHPUT,
    ADMIN_MSG_BENCH_RESULT_FMT,
    ADMIN_MSG_BENCH_TIME_FMT,
    MENU_KEY_UP,
    MENU_KEY_DOWN,
    MENU_KEY_ENTER,
    MENU_KEY_ESC,
    OPT_TYPE_HEADER,
    OPT_TYPE_ACTION,
    DICT_KEY_TYPE,
    DICT_KEY_TEXT,
    DICT_KEY_ID,
    OS_NAME_NT,
    CMD_CLEAR_WIN,
    CMD_CLEAR_POSIX,
    ADMIN_MSG_WAITING_REMAINING_FMT,
    ADMIN_PREFIX_ACTIVE_OPTION,
    ADMIN_PREFIX_INACTIVE_OPTION,
    ADMIN_PREFIX_HEADER,
)


class KeySecMenu:
    """Interactive Admin CLI Menu for managing the KeySec hardware dongle."""
    def __init__(self, transport, rpc, admin: AdminApi, compass: CompassApi):
        self.transport = transport
        self.rpc = rpc
        self.admin = admin
        self.compass = compass

    def _clear(self):
        os.system(CMD_CLEAR_WIN if os.name == OS_NAME_NT else CMD_CLEAR_POSIX)

    def _pause(self):
        print(ADMIN_PROMPT_PAUSE)
        msvcrt.getch()

    def run(self):
        options = [
            {DICT_KEY_TYPE: OPT_TYPE_HEADER, DICT_KEY_TEXT: ADMIN_SEC_DIAGNOSTICS},
            {DICT_KEY_TYPE: OPT_TYPE_ACTION, DICT_KEY_TEXT: ADMIN_ACT_SYS_HEALTH, DICT_KEY_ID: ACTION_SYS_HEALTH},
            {DICT_KEY_TYPE: OPT_TYPE_ACTION, DICT_KEY_TEXT: ADMIN_ACT_BATTERY, DICT_KEY_ID: ACTION_BATTERY_STATUS},
            {DICT_KEY_TYPE: OPT_TYPE_ACTION, DICT_KEY_TEXT: ADMIN_ACT_MEMORY, DICT_KEY_ID: ACTION_MEMORY_NVM},
            {DICT_KEY_TYPE: OPT_TYPE_ACTION, DICT_KEY_TEXT: ADMIN_ACT_RTC, DICT_KEY_ID: ACTION_RTC_DIAG},
            {DICT_KEY_TYPE: OPT_TYPE_ACTION, DICT_KEY_TEXT: ADMIN_ACT_LICENSE, DICT_KEY_ID: ACTION_LICENSE_USERS},
            {DICT_KEY_TYPE: OPT_TYPE_ACTION, DICT_KEY_TEXT: ADMIN_ACT_LOGS, DICT_KEY_ID: ACTION_DEVICE_LOGS},
            {DICT_KEY_TYPE: OPT_TYPE_HEADER, DICT_KEY_TEXT: ""},
            {DICT_KEY_TYPE: OPT_TYPE_HEADER, DICT_KEY_TEXT: ADMIN_SEC_TESTING},
            {DICT_KEY_TYPE: OPT_TYPE_ACTION, DICT_KEY_TEXT: ADMIN_ACT_BENCHMARK, DICT_KEY_ID: ACTION_BENCHMARK},
            {DICT_KEY_TYPE: OPT_TYPE_HEADER, DICT_KEY_TEXT: ""},
            {DICT_KEY_TYPE: OPT_TYPE_HEADER, DICT_KEY_TEXT: ADMIN_SEC_HEARTBEAT},
            {DICT_KEY_TYPE: OPT_TYPE_ACTION, DICT_KEY_TEXT: ADMIN_ACT_HB_START, DICT_KEY_ID: ACTION_HB_START},
            {DICT_KEY_TYPE: OPT_TYPE_ACTION, DICT_KEY_TEXT: ADMIN_ACT_HB_DISABLE, DICT_KEY_ID: ACTION_HB_DISABLE},
            {DICT_KEY_TYPE: OPT_TYPE_HEADER, DICT_KEY_TEXT: ""},
            {DICT_KEY_TYPE: OPT_TYPE_ACTION, DICT_KEY_TEXT: ADMIN_ACT_EXIT, DICT_KEY_ID: ACTION_EXIT}
        ]

        current_idx = 1

        def get_next_idx(idx, step):
            next_idx = (idx + step) % len(options)
            while options[next_idx][DICT_KEY_TYPE] != OPT_TYPE_ACTION:
                next_idx = (next_idx + step) % len(options)
            return next_idx

        while True:
            self._clear()
            print(ADMIN_MENU_TITLE)

            for i, opt in enumerate(options):
                if opt[DICT_KEY_TYPE] == OPT_TYPE_HEADER:
                    print(f"{ADMIN_PREFIX_HEADER}{opt[DICT_KEY_TEXT]}")
                else:
                    if i == current_idx:
                        print(f"{ADMIN_PREFIX_ACTIVE_OPTION}{opt[DICT_KEY_TEXT]}")
                    else:
                        print(f"{ADMIN_PREFIX_INACTIVE_OPTION}{opt[DICT_KEY_TEXT]}")

            print(ADMIN_PROMPT_NAV)

            key = self._get_key_with_esc()
            if key == MENU_KEY_UP:
                current_idx = get_next_idx(current_idx, -1)
            elif key == MENU_KEY_DOWN:
                current_idx = get_next_idx(current_idx, 1)
            elif key == MENU_KEY_ENTER:
                action_id = options[current_idx][DICT_KEY_ID]
                self._clear()
                self._execute_action(action_id)
            elif key == MENU_KEY_ESC:
                self._clear()
                break

    def _execute_action(self, action_id):
        if action_id == ACTION_SYS_HEALTH:
            print(ADMIN_HDR_SYS_HEALTH)
            health_str = self.admin.get_system_health()
            print(health_str)
            if getattr(health_str, 'is_tampered', False):
                print(ADMIN_ALERT_TAMPER)
            self._pause()

        elif action_id == ACTION_BATTERY_STATUS:
            print(ADMIN_HDR_BATTERY)
            print(self.admin.get_battery_info())
            self._pause()

        elif action_id == ACTION_MEMORY_NVM:
            print(ADMIN_HDR_MEMORY)
            print(self.admin.get_memory_info())
            print(self.admin.get_nvm_diagnostics())
            self._pause()

        elif action_id == ACTION_RTC_DIAG:
            print(ADMIN_HDR_RTC)
            print(self.admin.debug_time())
            self._pause()

        elif action_id == ACTION_LICENSE_USERS:
            print(ADMIN_HDR_LICENSE)
            print(ADMIN_MSG_LICENSE_PREFIX)
            if not getattr(self.compass, 'user_email', None):
                self.compass.set_user_email("admin_test@compass.com")
            print(self.compass.check_license())
            print()
            print(ADMIN_MSG_MAX_USERS_PREFIX)
            print(self.compass.get_max_users())
            self._pause()

        elif action_id == ACTION_BENCHMARK:
            print(ADMIN_HDR_BENCHMARK)
            if not getattr(self.compass, 'user_email', None):
                self.compass.set_user_email(ADMIN_DEFAULT_USER_EMAIL)

            # Ensure user activity and license are verified on the hardware dongle
            try:
                self.compass.check_license()
            except Exception as e:
                print(f"[!] License check: {e}")

            total_iterations = ADMIN_BENCHMARK_ITERATIONS
            print(ADMIN_MSG_BENCH_START_FMT.format(iterations=total_iterations))

            success_count = 0
            error_count = 0
            latencies_ms = []

            # Progress reporting: every ADMIN_BENCHMARK_LOG_STEP iterations (default 100)
            log_step = ADMIN_BENCHMARK_LOG_STEP if total_iterations > ADMIN_BENCHMARK_LOG_STEP else max(1, total_iterations // 10)

            t_start_all = time.perf_counter()

            try:
                for i in range(1, total_iterations + 1):
                    a = random.randint(1, 1000)
                    b = random.randint(1, 1000)
                    expected = a + b

                    t0 = time.perf_counter()
                    try:
                        res = self.compass.execute_test_add(
                            a, b, vrx_token=self.compass.last_vrx_token, silent=True
                        )
                        t1 = time.perf_counter()
                        duration_ms = (t1 - t0) * 1000
                        latencies_ms.append(duration_ms)

                        clean_res = res[len(RESP_OK_PREFIX):].strip() if res.startswith(RESP_OK_PREFIX) else res.replace("OK:", "").strip()
                        if clean_res.lstrip('-').isdigit() and int(clean_res) == expected:
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        error_count += 1
                        res = f"ERR: {e}"
                        duration_ms = 0.0

                    if i % log_step == 0 or i == total_iterations:
                        print(ADMIN_MSG_BENCH_ITER_FMT.format(
                            idx=i, total=total_iterations, a=a, b=b, res=res, duration_ms=duration_ms
                        ))
            except KeyboardInterrupt:
                print("\n[!] Benchmark interrupted by user (Ctrl+C). Generating summary for completed iterations...")

            t_end_all = time.perf_counter()
            total_duration_s = t_end_all - t_start_all
            total_duration_ms = total_duration_s * 1000
            completed_iterations = len(latencies_ms)
            avg_ms = (sum(latencies_ms) / completed_iterations) if completed_iterations else 0.0
            min_ms = min(latencies_ms) if latencies_ms else 0.0
            max_ms = max(latencies_ms) if latencies_ms else 0.0
            ops_per_sec = (completed_iterations / total_duration_s) if total_duration_s > 0 else 0.0

            print()
            print(ADMIN_MSG_BENCH_SUMMARY_HDR)
            print(ADMIN_MSG_BENCH_SUCCESS_FMT.format(
                success_count=success_count, total_count=completed_iterations, error_count=error_count
            ))
            print(ADMIN_MSG_BENCH_TOTAL_TIME.format(total_s=total_duration_s, total_ms=total_duration_ms))
            print(ADMIN_MSG_BENCH_AVG_TIME.format(avg_ms=avg_ms))
            print(ADMIN_MSG_BENCH_MIN_MAX_FMT.format(min_ms=min_ms, max_ms=max_ms))
            print(ADMIN_MSG_BENCH_THROUGHPUT.format(ops_per_sec=ops_per_sec))
            print("=" * len(ADMIN_MSG_BENCH_SUMMARY_HDR))
            self._pause()

        elif action_id == ACTION_DEVICE_LOGS:
            print(ADMIN_HDR_DEVICE_LOGS)
            self.admin.print_all_logs()
            self._pause()

        elif action_id == ACTION_HB_START:
            print(ADMIN_HDR_HB_STATUS)
            print(ADMIN_MSG_HB_RESUMING)
            self.transport.resume_heartbeat()
            print(ADMIN_MSG_HB_RUNNING)
            self._pause()

        elif action_id == ACTION_HB_DISABLE:
            print(ADMIN_HDR_HB_DISABLE)
            print(ADMIN_MSG_HB_PAUSING)
            self.transport.pause_heartbeat()
            print(ADMIN_MSG_HB_EXPLANATION)
            print(ADMIN_MSG_HB_WAITING)
            for i in range(20):
                print(ADMIN_MSG_WAITING_REMAINING_FMT.format(remaining=20-i), end='\r')
                time.sleep(1)
            print()
            print(ADMIN_MSG_HB_ASLEEP)
            print(ADMIN_MSG_HB_VERIFY_WAKE)
            self.transport.sync()
            print(ADMIN_MSG_HB_RESUMING)
            self.transport.resume_heartbeat()
            self._pause()

        elif action_id == ACTION_EXIT:
            pass

    def _get_key_with_esc(self):
        while True:
            char = msvcrt.getch()
            if char in (b'\x00', b'\xe0'):
                char2 = msvcrt.getch()
                if char2 == b'H':
                    return MENU_KEY_UP
                elif char2 == b'P':
                    return MENU_KEY_DOWN
            elif char in (b'\r', b'\n'):
                return MENU_KEY_ENTER
            elif char == b'\x1b':
                return MENU_KEY_ESC
            elif char == b'\x03':
                sys.exit(0)


