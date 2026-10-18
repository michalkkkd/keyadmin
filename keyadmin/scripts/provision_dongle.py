import os
import sys
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(ADMIN_DIR)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

KEYCOMM_DIR = os.path.join(REPO_ROOT, 'keycomm')
if KEYCOMM_DIR not in sys.path:
    sys.path.insert(0, KEYCOMM_DIR)

from keycomm.core.transport import SerialTransport
from keycomm.core.protocol import RpcProtocol
from keycomm.api.factory import find_dongle_port

from keyadmin.api.admin_api import AdminApi
from keyadmin.core.constants import RESP_OK_PREFIX_STR, RESP_OK_PREFIX_COLON

KEY_DIR = os.path.join(ADMIN_DIR, 'keys')


import time


def provision_dongle(port=None, license_days=365, max_users=1, set_rtc=True) -> bool:
    if port is None:
        port = find_dongle_port()
        if not port:
            print("[-] FATAL: Could not find KeySec Dongle (VID=0x2886, PID=0x0062) plugged into USB!")
            return False
        print(f"[+] Auto-detected Dongle on port: {port}")

    priv_path = os.path.join(KEY_DIR, 'root_ca_key.pem')
    if not os.path.exists(priv_path):
        print("[-] Root CA Private Key not found! Run generate_root_ca.py first.")
        return False

    print("[*] Loading Root CA Private Key from keyadmin/keys...")
    with open(priv_path, "rb") as f:
        root_ca_priv = serialization.load_pem_private_key(f.read(), password=None)

    print(f"[*] Connecting to Dongle on {port}...")
    transport = SerialTransport(port=port)
    try:
        rpc = RpcProtocol(transport)
        admin = AdminApi(rpc)

        print("\n--- STEP 1: Requesting Dongle Identity Generation ---")
        resp = admin.provision_identity()
        if not resp.startswith(RESP_OK_PREFIX_STR):
            print(f"[-] Failed to provision identity: {resp}")
            if "Unknown" in resp:
                print("\n" + "="*68)
                print(" [!] SEALED")
                print("="*68 + "\n")
            return False

        pub_key_hex = resp.replace(RESP_OK_PREFIX_COLON, "").strip()
        print(f"[+] Received Dongle Public Key: {pub_key_hex}")
        dongle_pub_bytes = bytes.fromhex(pub_key_hex)

        print("\n--- STEP 2: Signing Public Key with Root CA (Creating Cert) ---")
        signature = root_ca_priv.sign(
            dongle_pub_bytes,
            ec.ECDSA(hashes.SHA256())
        )
        print(f"[+] Signature generated. Length: {len(signature)} bytes")

        print("\n--- STEP 3: Saving Certificate to Dongle NVM3 ---")
        resp2 = admin.save_certificate(signature)
        if not resp2.startswith(RESP_OK_PREFIX_STR):
            print(f"[-] Failed to save certificate on dongle: {resp2}")
            return False

        print("[+] Identity & Certificate committed to NVM3.")

        if set_rtc:
            print("\n--- STEP 4: Synchronizing Device Base Timestamp (RTC) ---")
            now_ts = int(time.time())
            resp_date = admin.update_current_date(now_ts)
            print(f"[+] Date sync response: {resp_date}")
            if not resp_date.startswith(RESP_OK_PREFIX_STR):
                print(f"[-] Failed to set RTC date: {resp_date}")
                return False

            print("\n--- STEP 5: Setting License Duration & Max Users Limit ---")
            resp_lic = admin.set_license_days(license_days)
            print(f"[+] License response: {resp_lic}")
            if not resp_lic.startswith(RESP_OK_PREFIX_STR):
                print(f"[-] Failed to set license days: {resp_lic}")
                return False

            resp_users = admin.set_max_users(max_users)
            print(f"[+] Users limit response: {resp_users}")
            if not resp_users.startswith(RESP_OK_PREFIX_STR):
                print(f"[-] Failed to set max users: {resp_users}")
                return False

        print("\n[+] SUCCESS: Dongle has been successfully provisioned and configured!")
        return True

    finally:
        transport.close()


if __name__ == '__main__':
    args = sys.argv[1:]
    port = None
    days = 365
    users = 1

    if args:
        if args[0].upper().startswith("COM") or args[0].startswith("/dev/"):
            port = args[0]
            if len(args) > 1: days = int(args[1])
            if len(args) > 2: users = int(args[2])
        else:
            days = int(args[0])
            if len(args) > 1: users = int(args[1])

    provision_dongle(port, license_days=days, max_users=users)
