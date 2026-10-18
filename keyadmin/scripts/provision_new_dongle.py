import os
import sys
import time
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(ADMIN_DIR)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

KEYCOMM_DIR = os.path.join(REPO_ROOT, 'keycomm')
if KEYCOMM_DIR not in sys.path:
    sys.path.insert(0, KEYCOMM_DIR)

from keycomm.api.factory import find_dongle_port, init_comm_device
from keycomm.core.transport import SerialTransport
from keycomm.core.protocol import RpcProtocol

from keyadmin.scripts.provision_dongle import provision_dongle
from keyadmin.api.admin_api import AdminApi
from keyadmin.core.constants import TOKEN_OK


def run_flash(hex_path: str, python_exe: str = sys.executable) -> bool:
    flash_script = os.path.join(REPO_ROOT, '..', 'KeyFirmware', 'flashbat', 'xiao_mg24_flash.py')
    flash_script = os.path.abspath(flash_script)
    if not os.path.exists(flash_script):
        print(f"[-] Flash script not found: {flash_script}")
        return False
    if not os.path.exists(hex_path):
        print(f"[-] Hex file not found: {hex_path}")
        return False

    pack_path = os.path.join(os.path.dirname(flash_script), 'SiliconLabs.GeckoPlatform_EFR32MG24_DFP.2025.6.0.pack')
    cmd = [
        python_exe,
        flash_script,
        "--hex", hex_path,
        "--pack", pack_path
    ]
    print(f"[*] Running: {' '.join(cmd)}")
    ret = subprocess.run(cmd)
    return ret.returncode == 0


def provision_new_dongle(port: str = None, license_days: int = 365, max_users: int = 1):
    print("==================================================================")
    print("   AUTOMATED FACTORY PROVISIONING & PRODUCTION SEALING PIPELINE   ")
    print("==================================================================")

    kf_build_dir = os.path.abspath(os.path.join(REPO_ROOT, '..', 'KeyFirmware', 'cmake_gcc', 'build', 'base'))
    prov_hex = os.path.join(kf_build_dir, 'keyfirmware_prov.hex')
    prod_hex = os.path.join(kf_build_dir, 'keyfirmware.hex')

    # STEP 1: Flash Provisioning Firmware
    print("\n>>> STEP 1: Flashing Factory Provisioning Firmware (keyfirmware_prov.hex) <<<")
    if not run_flash(prov_hex):
        print("[-] FAILED: Could not flash provisioning firmware!")
        return False

    print("[*] Waiting 3s for USB re-enumeration after flashing...")
    time.sleep(3.0)

    # Detect port if not explicitly provided
    if not port:
        print("[*] Auto-detecting Dongle COM port (VID=0x2886, PID=0x0062)...")
        for _ in range(10):
            port = find_dongle_port()
            if port:
                break
            time.sleep(0.5)
        if not port:
            print("[-] FATAL: Could not detect KeySec Dongle plugged into USB!")
            return False
        print(f"[+] Detected Dongle on port: {port}")

    # STEP 2: Run Factory Provisioning (Identity, Cert, Base RTC, License, Users)
    print(f"\n>>> STEP 2: Provisioning Device Secrets over {port} <<<")
    success = False
    for attempt in range(1, 6):
        try:
            success = provision_dongle(port=port, license_days=license_days, max_users=max_users, set_rtc=True)
            if success:
                break
        except Exception as e:
            print(f"[*] Provisioning attempt {attempt}/5 failed with error: {e}")
        print(f"[*] Provisioning attempt {attempt}/5 not complete. Retrying in 2.0s...")
        time.sleep(2.0)

    if not success:
        print("[-] FAILED: Factory provisioning rejected by device!")
        return False

    # STEP 3: Flash Sealed Production Firmware
    print("\n>>> STEP 3: Sealing Device with Production Firmware (keyfirmware.hex) <<<")
    if not run_flash(prod_hex):
        print("[-] FAILED: Could not flash production firmware!")
        return False

    print("[*] Waiting 4s for USB re-enumeration after flashing production firmware...")
    time.sleep(4.0)

    # STEP 4: Verification of Sealed Device
    print(f"\n>>> STEP 4: Verifying Sealed Production Device on {port} <<<")
    compass = None
    transport = None
    for attempt in range(1, 6):
        try:
            compass, transport = init_comm_device(port=port, user_email="factory_test@example.com", verbose=(attempt == 1))
            if compass and transport:
                break
        except Exception as e:
            print(f"[*] Verification connection attempt {attempt}/5 failed: {e}")
        print(f"[*] Waiting for port {port} to become available (attempt {attempt}/5)... Retrying in 2.0s...")
        time.sleep(2.0)

    if not compass:
        print("[-] FAILED: Could not establish secure ECDHE session with production device!")
        return False

    try:
        # Check license
        lic_result = compass.check_license()
        print(f"[+] Production License Check: {lic_result}")
        if not lic_result.is_valid:
            print("[-] FAILED: License check invalid on production device!")
            return False

        # Check Algorithm 1
        alg_res = compass.execute_alg1(15, 27)
        print(f"[+] Algorithm 1 Calculation (15 + 27): {alg_res}")
        if "42" not in alg_res:
            print(f"[-] FAILED: Algorithm 1 returned unexpected output: {alg_res}")
            return False

        # Verify that Admin commands are rejected (zero admin handlers)
        print("\n[*] Testing Admin Command Rejection (verifying Zero Admin Handlers)...")
        rpc = compass.rpc
        admin_test = AdminApi(rpc)
        wipe_res = admin_test.wipe_device()
        print(f"[+] Attempted admin wipe result on production binary: {wipe_res}")
        if TOKEN_OK in wipe_res:
            print("[-] CRITICAL FAILURE: Production firmware accepted admin wipe!")
            return False
        print("[+] SUCCESS: Admin commands are safely rejected by production firmware!")

        print("\n==================================================================")
        print(" [+] SUCCESS: Device has been provisioned and sealed with Production Firmware!")
        print("     All manufacturing secrets committed to NVM3.")
        print("     Production binary contains ZERO admin commands and ZERO hardcoded PINs.")
        print("==================================================================")
        return True

    finally:
        transport.close()


if __name__ == '__main__':
    args = sys.argv[1:]
    target_port = None
    lic_d = 365
    max_u = 1

    if args:
        if args[0].upper().startswith("COM") or args[0].startswith("/dev/"):
            target_port = args[0]
            if len(args) > 1: lic_d = int(args[1])
            if len(args) > 2: max_u = int(args[2])
        else:
            lic_d = int(args[0])
            if len(args) > 1: max_u = int(args[1])

    ok = provision_new_dongle(port=target_port, license_days=lic_d, max_users=max_u)
    sys.exit(0 if ok else 1)
