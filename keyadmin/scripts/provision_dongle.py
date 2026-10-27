"""
KeySec factory provisioning pipeline (single entry point).

    python provision_dongle.py [days] [users] [--port COMx] [--lock] [--yes] [--skip-compile] [--secrets-only] [--check]

Steps (flashing always goes through KeyFirmware/flashbat, which owns the firmware/TrustZone images):
    1. compile.bat                 build keyfirmware.hex + keyfirmware_prov.hex
    2. set_factory_mode.bat        flash the unsealed factory firmware
    3. secrets                     identity (PUF) -> Root CA certificate -> RTC -> license -> max users
    4. set_production_mode.bat     seal with the production firmware
    5. verify                      ECDHE session, license valid, alg1(15,27)=42, admin wipe rejected
    6. --lock                      Secure Debug Lock (protected dongles are refused)

A read-only preflight runs first and stops before the dongle is touched if anything is missing or inconsistent:
scripts and images, Root CA pair, pyOCD with exactly one probe, exactly one free dongle port, SWD not locked,
Command Key vs firmware header. --check runs only the preflight.
--secrets-only runs step 3 alone on a dongle that already runs the factory firmware.
Also callable from the admin console menu (FACTORY section).
"""
import argparse
import os
import shlex
import subprocess
import sys
import time
from typing import Any, Callable, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(ADMIN_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import serial.tools.list_ports

from keycomm.api.device_discovery import find_dongle_port, find_root_ca_key_path
from keycomm.core.constants import TARGET_VID, TARGET_PID
from keycomm.core.protocol import RpcProtocol
from keycomm.core.transport import SerialTransport
from keycomm.core.constants import TOKEN_OK

from keyadmin.admin_factory import init_admin_device
from keyadmin.api.admin_api import AdminApi
from keyadmin.secure_debug.secure_debug_service import SecureDebugService
from keyadmin.secure_debug.secure_debug_store import SecureDebugStore
from keyadmin.secure_debug.debug_lock_status import DebugLockStatus
from keyadmin.secure_debug.unlock_token_builder import UnlockTokenBuilder
from keyadmin.scripts.generate_debug_command_key import render_header
from keyadmin.core.constants import (
    RESP_OK_PREFIX_STR,
    RESP_OK_PREFIX_COLON,
    PROV_DEFAULT_LICENSE_DAYS,
    PROV_DEFAULT_MAX_USERS,
    PROV_FLASHBAT_RELPATH,
    PROV_BAT_COMPILE,
    PROV_BAT_FACTORY_MODE,
    PROV_BAT_PRODUCTION_MODE,
    PROV_ROOT_CA_KEY_FILENAME,
    PROV_VERIFY_USER_EMAIL,
    PROV_ALG1_INPUT_A,
    PROV_ALG1_INPUT_B,
    PROV_ALG1_EXPECTED,
    PROV_PORT_WAIT_SEC,
    PROV_PORT_POLL_SEC,
    PROV_SETTLE_SEC,
    PROV_ATTEMPTS,
    PROV_RETRY_DELAY_SEC,
    PROV_BANNER,
    PROV_MSG_PLAN_FMT,
    PROV_STEP_FMT,
    PROV_STEP_COMPILE,
    PROV_STEP_FACTORY,
    PROV_STEP_SECRETS,
    PROV_STEP_PRODUCTION,
    PROV_STEP_VERIFY,
    PROV_STEP_LOCK,
    PROV_MSG_RUNNING_FMT,
    PROV_MSG_WAIT_PORT,
    PROV_MSG_PORT_FMT,
    PROV_MSG_ATTEMPT_FAILED_FMT,
    PROV_MSG_ROOT_CA_LOADED_FMT,
    PROV_MSG_IDENTITY_FMT,
    PROV_MSG_CERT_SAVED,
    PROV_MSG_RTC_FMT,
    PROV_MSG_LICENSE_FMT,
    PROV_MSG_USERS_FMT,
    PROV_MSG_SECURE_SESSION,
    PROV_MSG_VERIFY_LICENSE_FMT,
    PROV_MSG_VERIFY_ALG1_FMT,
    PROV_MSG_VERIFY_ADMIN_FMT,
    PROV_MSG_LOCK_SKIPPED,
    PROV_MSG_SUCCESS,
    PROV_MSG_SUCCESS_LOCKED,
    PROV_ERR_FLASHBAT_MISSING_FMT,
    PROV_ERR_BAT_FAILED_FMT,
    PROV_ERR_NO_PORT,
    PROV_ERR_ROOT_CA_MISSING_FMT,
    PROV_ERR_SEALED,
    PROV_ERR_STEP_FMT,
    PROV_ERR_STEP_IDENTITY,
    PROV_ERR_STEP_CERT,
    PROV_ERR_STEP_RTC,
    PROV_ERR_STEP_LICENSE,
    PROV_ERR_STEP_USERS,
    PROV_ERR_NO_SESSION,
    PROV_ERR_LICENSE_INVALID_FMT,
    PROV_ERR_ALG1_FMT,
    PROV_ERR_ADMIN_ACCEPTED,
    PROV_ERR_UNKNOWN_TOKEN,
    PROV_ERR_FAILED_FMT,
    SDL_CONFIRM_WORD,
    SDL_PROMPT_CONFIRM_FMT,
    SDL_MSG_LOCK_WARNING,
    SDL_MSG_ALREADY_LOCKED,
    SDL_MSG_LOCK_OK,
    SDL_ERR_DEVICE_PROTECTED_FMT,
    PROV_ERR_LOCK_ABORTED,
    PROV_FLASHBAT_FILES,
    PROV_FIRMWARE_RELPATH,
    PROV_FIRMWARE_IMAGES,
    PROV_BAT_GET_PYTHON,
    PROV_ENV_PYTHON_PREFIX,
    PROV_TOOLCHAIN_PROBE_SCRIPT,
    PROV_TOOLCHAIN_TIMEOUT_SEC,
    PROV_STEP_PREFLIGHT,
    PROV_CHECK_OK_FMT,
    PROV_CHECK_WARN_FMT,
    PROV_CHECK_FAIL_FMT,
    PROV_CHECK_ARGS,
    PROV_CHECK_FLASHBAT,
    PROV_CHECK_IMAGES,
    PROV_CHECK_ROOT_CA,
    PROV_CHECK_TOOLCHAIN,
    PROV_CHECK_DONGLE,
    PROV_CHECK_LOCK_KEY,
    PROV_DETAIL_ARGS_FMT,
    PROV_DETAIL_FILES_FMT,
    PROV_DETAIL_IMAGES_REBUILT,
    PROV_DETAIL_IMAGES_FMT,
    PROV_DETAIL_ROOT_CA_FMT,
    PROV_DETAIL_TOOLCHAIN_FMT,
    PROV_DETAIL_DONGLE_FMT,
    PROV_DETAIL_DONGLE_NO_STATUS_FMT,
    PROV_DETAIL_LOCK_KEY_FMT,
    PROV_DETAIL_NOT_NEEDED,
    PROV_MSG_CHECK_ONLY,
    PROV_HINT_FLASH_FAILED,
    PROV_ERR_PREFLIGHT_FMT,
    PROV_ERR_ARGS_FMT,
    PROV_ERR_FILES_MISSING_FMT,
    PROV_ERR_IMAGES_MISSING_FMT,
    PROV_ERR_IMAGES_STALE,
    PROV_ERR_IMAGES_NOT_REBUILT_FMT,
    PROV_ERR_ROOT_CA_PUB_MISSING,
    PROV_ERR_ROOT_CA_MISMATCH_FMT,
    PROV_ERR_PYTHON_NOT_FOUND,
    PROV_ERR_TOOLCHAIN_FMT,
    PROV_ERR_PROBE_COUNT_FMT,
    PROV_ERR_PORT_COUNT_FMT,
    PROV_ERR_PORT_NOT_FOUND_FMT,
    PROV_ERR_PORT_BUSY_FMT,
    PROV_ERR_DONGLE_LOCKED_FMT,
    PROV_ERR_DONGLE_PROTECTED_FMT,
    PROV_ERR_HEADER_MISMATCH_FMT,
    SDL_FIRMWARE_HEADER_RELPATH,
)

KEY_DIR = os.path.join(ADMIN_DIR, "keys")
FLASHBAT_DIR = os.path.normpath(os.path.join(REPO_ROOT, *PROV_FLASHBAT_RELPATH))
FIRMWARE_DIR = os.path.normpath(os.path.join(REPO_ROOT, *PROV_FIRMWARE_RELPATH))
FIRMWARE_HEADER = os.path.normpath(os.path.join(REPO_ROOT, *SDL_FIRMWARE_HEADER_RELPATH))


def confirm_debug_lock() -> bool:
    print(SDL_MSG_LOCK_WARNING)
    return input(SDL_PROMPT_CONFIRM_FMT.format(word=SDL_CONFIRM_WORD)).strip() == SDL_CONFIRM_WORD


class DongleProvisioner:
    """Runs the factory pipeline: compile -> factory firmware -> secrets -> production firmware -> verify -> lock."""

    def __init__(self, license_days: int = PROV_DEFAULT_LICENSE_DAYS, max_users: int = PROV_DEFAULT_MAX_USERS,
                 port: Optional[str] = None, compile_firmware: bool = True, flash_firmware: bool = True,
                 debug_lock: bool = False, confirm_lock: Callable[[], bool] = confirm_debug_lock,
                 check_only: bool = False):
        self.license_days = license_days
        self.max_users = max_users
        self.port = port
        self.compile_firmware = compile_firmware
        self.flash_firmware = flash_firmware
        self.debug_lock = debug_lock
        self.confirm_lock = confirm_lock
        self.check_only = check_only
        self.started_at = time.time()

    def run(self) -> bool:
        """Returns True when every requested step passed. Never raises; failures are printed."""
        print(PROV_BANNER)
        print(PROV_MSG_PLAN_FMT.format(days=self.license_days, users=self.max_users, compile=self.compile_firmware,
                                       flash=self.flash_firmware, lock=self.debug_lock))
        try:
            print()
            print(PROV_STEP_PREFLIGHT)
            self._preflight()
            if self.check_only:
                print(PROV_MSG_CHECK_ONLY)
                return True
            steps = self._steps()
            for idx, (title, step) in enumerate(steps, start=1):
                print()
                print(PROV_STEP_FMT.format(idx=idx, total=len(steps), title=title))
                step()
        except Exception as e:
            print(PROV_ERR_FAILED_FMT.format(error=e))
            return False
        print()
        print(PROV_MSG_SUCCESS_LOCKED if self.debug_lock else PROV_MSG_SUCCESS)
        return True

    def _steps(self) -> list:
        steps = []
        if self.compile_firmware:
            steps.append((PROV_STEP_COMPILE, self._compile))
        if self.flash_firmware:
            steps.append((PROV_STEP_FACTORY, lambda: self._run_bat(PROV_BAT_FACTORY_MODE)))
        steps.append((PROV_STEP_SECRETS, lambda: self._retry(self._provision_secrets)))
        if self.flash_firmware:
            steps.append((PROV_STEP_PRODUCTION, lambda: self._run_bat(PROV_BAT_PRODUCTION_MODE)))
            steps.append((PROV_STEP_VERIFY, self._verify_and_lock))
        return steps

    # ---- flashbat ---------------------------------------------------------

    def _run_bat(self, bat_name: str) -> None:
        if not os.path.isdir(FLASHBAT_DIR):
            raise RuntimeError(PROV_ERR_FLASHBAT_MISSING_FMT.format(path=FLASHBAT_DIR))
        bat_path = os.path.join(FLASHBAT_DIR, bat_name)
        print(PROV_MSG_RUNNING_FMT.format(cmd=bat_path))
        code = subprocess.run(["cmd", "/c", bat_path], cwd=FLASHBAT_DIR).returncode
        if code != 0:
            error = PROV_ERR_BAT_FAILED_FMT.format(bat=bat_name, code=code)
            if bat_name != PROV_BAT_COMPILE:
                error = f"{error} {PROV_HINT_FLASH_FAILED}"
            raise RuntimeError(error)

    def _compile(self) -> None:
        self._run_bat(PROV_BAT_COMPILE)
        stale = [name for name, mtime in self._image_mtimes().items() if mtime is None or mtime < self.started_at]
        if stale:
            raise RuntimeError(PROV_ERR_IMAGES_NOT_REBUILT_FMT.format(images=", ".join(stale)))

    @staticmethod
    def _image_mtimes() -> dict:
        mtimes = {}
        for name in PROV_FIRMWARE_IMAGES:
            path = os.path.join(FIRMWARE_DIR, name)
            mtimes[name] = os.path.getmtime(path) if os.path.isfile(path) else None
        return mtimes

    # ---- preflight (read-only) ---------------------------------------------

    def _preflight(self) -> None:
        """Runs every check, prints all results, and fails before anything is flashed or written."""
        checks = [
            (PROV_CHECK_ARGS, self._check_arguments),
            (PROV_CHECK_FLASHBAT, self._check_flashbat_files),
            (PROV_CHECK_IMAGES, self._check_firmware_images),
            (PROV_CHECK_ROOT_CA, self._check_root_ca_pair),
            (PROV_CHECK_TOOLCHAIN, self._check_flash_toolchain),
            (PROV_CHECK_DONGLE, self._check_dongle),
            (PROV_CHECK_LOCK_KEY, self._check_debug_command_key),
        ]
        failed = 0
        for name, check in checks:
            try:
                detail, warning = check()
                print((PROV_CHECK_WARN_FMT if warning else PROV_CHECK_OK_FMT).format(name=name, detail=detail))
            except Exception as e:
                failed += 1
                print(PROV_CHECK_FAIL_FMT.format(name=name, detail=e))
        if failed:
            raise RuntimeError(PROV_ERR_PREFLIGHT_FMT.format(count=failed))

    def _check_arguments(self) -> tuple:
        if self.license_days <= 0 or self.max_users <= 0:
            raise ValueError(PROV_ERR_ARGS_FMT.format(days=self.license_days, users=self.max_users))
        return PROV_DETAIL_ARGS_FMT.format(days=self.license_days, users=self.max_users), False

    def _check_flashbat_files(self) -> tuple:
        if not self.flash_firmware:
            return PROV_DETAIL_NOT_NEEDED, False
        missing = [f for f in PROV_FLASHBAT_FILES if not os.path.isfile(os.path.join(FLASHBAT_DIR, f))]
        if missing:
            raise FileNotFoundError(PROV_ERR_FILES_MISSING_FMT.format(files=", ".join(missing)))
        return PROV_DETAIL_FILES_FMT.format(count=len(PROV_FLASHBAT_FILES), path=FLASHBAT_DIR), False

    def _check_firmware_images(self) -> tuple:
        if not self.flash_firmware:
            return PROV_DETAIL_NOT_NEEDED, False
        if self.compile_firmware:
            return PROV_DETAIL_IMAGES_REBUILT, False
        mtimes = self._image_mtimes()
        missing = [name for name, mtime in mtimes.items() if mtime is None]
        if missing:
            raise FileNotFoundError(PROV_ERR_IMAGES_MISSING_FMT.format(images=", ".join(missing)))
        if self.debug_lock and min(mtimes.values()) < os.path.getmtime(FIRMWARE_HEADER):
            raise RuntimeError(PROV_ERR_IMAGES_STALE)
        built = time.strftime("%Y-%m-%d %H:%M", time.localtime(min(mtimes.values())))
        return PROV_DETAIL_IMAGES_FMT.format(images=", ".join(mtimes), built=built), False

    def _check_root_ca_pair(self) -> tuple:
        """The dongle certificate is signed with keyadmin's private key but verified with keycomm's public key."""
        private_key = self._load_root_ca()
        pub_path = find_root_ca_key_path(verbose=False)
        if not pub_path:
            raise FileNotFoundError(PROV_ERR_ROOT_CA_PUB_MISSING)
        with open(pub_path, "rb") as f:
            verify_key = serialization.load_pem_public_key(f.read())
        if UnlockTokenBuilder.raw_public_key(verify_key) != UnlockTokenBuilder.raw_public_key(private_key.public_key()):
            raise RuntimeError(PROV_ERR_ROOT_CA_MISMATCH_FMT.format(path=pub_path))
        return PROV_DETAIL_ROOT_CA_FMT.format(path=pub_path), False

    def _check_flash_toolchain(self) -> tuple:
        """Uses the same interpreter the flashbat scripts will use (get_python.bat)."""
        if not self.flash_firmware:
            return PROV_DETAIL_NOT_NEEDED, False
        get_python = os.path.join(FLASHBAT_DIR, PROV_BAT_GET_PYTHON)
        env = subprocess.run(["cmd", "/c", "call", get_python, "&", "set", "PYTHON_EXE"],
                             cwd=FLASHBAT_DIR, capture_output=True, text=True).stdout
        python = next((line[len(PROV_ENV_PYTHON_PREFIX):].strip() for line in env.splitlines()
                       if line.startswith(PROV_ENV_PYTHON_PREFIX)), "")
        if not python:
            raise RuntimeError(PROV_ERR_PYTHON_NOT_FOUND)
        cmd = [python] if os.path.isfile(python) else shlex.split(python, posix=False)
        result = subprocess.run(cmd + ["-c", PROV_TOOLCHAIN_PROBE_SCRIPT], capture_output=True, text=True,
                                timeout=PROV_TOOLCHAIN_TIMEOUT_SEC)
        if result.returncode != 0:
            error = (result.stderr.strip().splitlines() or ["?"])[-1]
            raise RuntimeError(PROV_ERR_TOOLCHAIN_FMT.format(python=python, error=error))
        probes = int(result.stdout.strip().splitlines()[-1])
        if probes != 1:
            raise RuntimeError(PROV_ERR_PROBE_COUNT_FMT.format(count=probes))
        return PROV_DETAIL_TOOLCHAIN_FMT.format(python=python), False

    def _check_dongle(self) -> tuple:
        """Exactly one dongle, port free, SWD not locked (a locked dongle cannot be flashed)."""
        ports = [p.device for p in serial.tools.list_ports.comports() if p.vid == TARGET_VID and p.pid == TARGET_PID]
        if self.port:
            if self.port not in ports:
                raise RuntimeError(PROV_ERR_PORT_NOT_FOUND_FMT.format(port=self.port, ports=ports))
        elif len(ports) != 1:
            raise RuntimeError(PROV_ERR_PORT_COUNT_FMT.format(count=len(ports)))
        port = self.port or ports[0]
        try:
            transport = SerialTransport(port=port)
        except Exception as e:
            raise RuntimeError(PROV_ERR_PORT_BUSY_FMT.format(port=port, error=e)) from e
        try:
            status = DebugLockStatus.from_response(AdminApi(RpcProtocol(transport)).get_debug_lock_status())
        except Exception as e:
            return PROV_DETAIL_DONGLE_NO_STATUS_FMT.format(port=port, error=e), True
        finally:
            transport.close()
        protected = SecureDebugStore().is_protected(status.serial)
        if status.lock_active and self.flash_firmware:
            raise RuntimeError(PROV_ERR_DONGLE_LOCKED_FMT.format(serial=status.serial))
        if self.debug_lock and protected:
            raise RuntimeError(PROV_ERR_DONGLE_PROTECTED_FMT.format(serial=status.serial))
        return PROV_DETAIL_DONGLE_FMT.format(port=port, serial=status.serial, locked=status.lock_active,
                                             protected=protected), False

    def _check_debug_command_key(self) -> tuple:
        """The firmware must embed the public half of the key that signs unlocks, or a lock cannot be opened."""
        if not self.debug_lock:
            return PROV_DETAIL_NOT_NEEDED, False
        store = SecureDebugStore()
        raw_pubkey = UnlockTokenBuilder.raw_public_key(store.load_command_key().public_key())
        with open(FIRMWARE_HEADER, encoding="utf-8") as f:
            header = f.read()
        if header.strip() != render_header(raw_pubkey).strip():
            raise RuntimeError(PROV_ERR_HEADER_MISMATCH_FMT.format(path=store.command_key_path))
        return PROV_DETAIL_LOCK_KEY_FMT.format(path=store.command_key_path), False

    # ---- helpers ----------------------------------------------------------

    def _retry(self, action: Callable[[], Any]) -> Any:
        """Retries a USB action; the COM port re-enumerates after every flash."""
        for attempt in range(1, PROV_ATTEMPTS + 1):
            try:
                return action()
            except Exception as e:
                if attempt == PROV_ATTEMPTS:
                    raise
                print(PROV_MSG_ATTEMPT_FAILED_FMT.format(attempt=attempt, total=PROV_ATTEMPTS, error=e))
                time.sleep(PROV_RETRY_DELAY_SEC)

    def _wait_for_port(self) -> str:
        if self.flash_firmware:
            time.sleep(PROV_SETTLE_SEC)
        if self.port:
            return self.port
        print(PROV_MSG_WAIT_PORT)
        deadline = time.monotonic() + PROV_PORT_WAIT_SEC
        while time.monotonic() < deadline:
            port = find_dongle_port(verbose=False)
            if port:
                print(PROV_MSG_PORT_FMT.format(port=port))
                return port
            time.sleep(PROV_PORT_POLL_SEC)
        raise RuntimeError(PROV_ERR_NO_PORT)

    @staticmethod
    def _expect_ok(step: str, response: str) -> str:
        if not response.startswith(RESP_OK_PREFIX_STR):
            if PROV_ERR_UNKNOWN_TOKEN in response:
                raise RuntimeError(PROV_ERR_SEALED)
            raise RuntimeError(PROV_ERR_STEP_FMT.format(step=step, response=response))
        return response

    @staticmethod
    def _load_root_ca():
        path = os.path.join(KEY_DIR, PROV_ROOT_CA_KEY_FILENAME)
        if not os.path.exists(path):
            raise RuntimeError(PROV_ERR_ROOT_CA_MISSING_FMT.format(path=path))
        with open(path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
        print(PROV_MSG_ROOT_CA_LOADED_FMT.format(path=path))
        return key

    # ---- step 3: secrets (factory firmware, plaintext admin RPC) ----------

    def _provision_secrets(self) -> None:
        root_ca = self._load_root_ca()
        transport = SerialTransport(port=self._wait_for_port())
        try:
            admin = AdminApi(RpcProtocol(transport))

            resp = self._expect_ok(PROV_ERR_STEP_IDENTITY, admin.provision_identity())
            pubkey_hex = resp.replace(RESP_OK_PREFIX_COLON, "").strip()
            print(PROV_MSG_IDENTITY_FMT.format(pubkey=pubkey_hex))

            signature = root_ca.sign(bytes.fromhex(pubkey_hex), ec.ECDSA(hashes.SHA256()))
            self._expect_ok(PROV_ERR_STEP_CERT, admin.save_certificate(signature))
            print(PROV_MSG_CERT_SAVED)

            print(PROV_MSG_RTC_FMT.format(
                response=self._expect_ok(PROV_ERR_STEP_RTC, admin.update_current_date(int(time.time())))))
            print(PROV_MSG_LICENSE_FMT.format(
                response=self._expect_ok(PROV_ERR_STEP_LICENSE, admin.set_license_days(self.license_days))))
            print(PROV_MSG_USERS_FMT.format(
                response=self._expect_ok(PROV_ERR_STEP_USERS, admin.set_max_users(self.max_users))))
        finally:
            transport.close()

    # ---- steps 5-6: verify sealed dongle, optional debug lock -------------

    def _connect_production(self) -> tuple:
        compass, admin, transport = init_admin_device(port=self._wait_for_port(),
                                                      user_email=PROV_VERIFY_USER_EMAIL, verbose=False)
        if admin is None:
            raise RuntimeError(PROV_ERR_NO_SESSION)
        return compass, admin, transport

    def _verify_and_lock(self) -> None:
        """Connection is retried; verification and the lock are not (a lock prompt must never repeat)."""
        compass, admin, transport = self._retry(self._connect_production)
        try:
            self._verify_sealed(compass, admin)
            if self.debug_lock:
                print()
                print(PROV_STEP_LOCK)
                self._apply_debug_lock(admin, getattr(transport, "port", self.port))
            else:
                print(PROV_MSG_LOCK_SKIPPED)
        finally:
            transport.close()

    @staticmethod
    def _verify_sealed(compass, admin: AdminApi) -> None:
        secure_channel = getattr(compass.rpc, "secure_channel", None)
        if secure_channel is None or not secure_channel.is_active:
            raise RuntimeError(PROV_ERR_NO_SESSION)
        print(PROV_MSG_SECURE_SESSION)

        license_result = compass.check_license()
        if not license_result:
            raise RuntimeError(PROV_ERR_LICENSE_INVALID_FMT.format(result=license_result))
        print(PROV_MSG_VERIFY_LICENSE_FMT.format(result=license_result))

        alg_result = compass.execute_alg1(PROV_ALG1_INPUT_A, PROV_ALG1_INPUT_B)
        if PROV_ALG1_EXPECTED not in alg_result:
            raise RuntimeError(PROV_ERR_ALG1_FMT.format(result=alg_result, expected=PROV_ALG1_EXPECTED))
        print(PROV_MSG_VERIFY_ALG1_FMT.format(a=PROV_ALG1_INPUT_A, b=PROV_ALG1_INPUT_B, result=alg_result))

        wipe_result = admin.wipe_device()
        if TOKEN_OK in wipe_result:
            raise RuntimeError(PROV_ERR_ADMIN_ACCEPTED)
        print(PROV_MSG_VERIFY_ADMIN_FMT.format(result=wipe_result))

    def _apply_debug_lock(self, admin: AdminApi, port: Optional[str]) -> None:
        service = SecureDebugService(admin, SecureDebugStore(), port=port)
        status = service.read_status()
        print(service.describe(status))
        if service.store.is_protected(status.serial):
            raise RuntimeError(SDL_ERR_DEVICE_PROTECTED_FMT.format(serial=status.serial,
                                                                   path=service.store.protected_list_path))
        if status.is_secure_locked:
            print(SDL_MSG_ALREADY_LOCKED)
            return
        if not self.confirm_lock():
            raise RuntimeError(PROV_ERR_LOCK_ABORTED)
        print(service.describe(service.apply_lock()))
        print(SDL_MSG_LOCK_OK)


def main() -> int:
    parser = argparse.ArgumentParser(description="KeySec factory provisioning pipeline")
    parser.add_argument("days", nargs="?", type=int, default=PROV_DEFAULT_LICENSE_DAYS, help="license duration in days")
    parser.add_argument("users", nargs="?", type=int, default=PROV_DEFAULT_MAX_USERS, help="max concurrent users")
    parser.add_argument("--port", help="COM port (auto-detected when omitted)")
    parser.add_argument("--lock", action="store_true", help="apply the Secure Debug Lock after verification")
    parser.add_argument("--yes", action="store_true", help="lock without the interactive LOCK confirmation")
    parser.add_argument("--skip-compile", action="store_true", help="use the existing .hex files")
    parser.add_argument("--secrets-only", action="store_true",
                        help="only provision secrets on a dongle already running factory firmware (no compile/flash/verify)")
    parser.add_argument("--check", action="store_true", help="only run the preflight checks, change nothing")
    args = parser.parse_args()

    provisioner = DongleProvisioner(
        license_days=args.days,
        max_users=args.users,
        port=args.port,
        compile_firmware=not (args.skip_compile or args.secrets_only),
        flash_firmware=not args.secrets_only,
        debug_lock=args.lock and not args.secrets_only,
        confirm_lock=(lambda: True) if args.yes else confirm_debug_lock,
        check_only=args.check,
    )
    return 0 if provisioner.run() else 1


if __name__ == "__main__":
    sys.exit(main())
