import os
import sys
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization

# Add parent directory to path so we can import core/api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.transport import SerialTransport
from core.protocol import RpcProtocol
from api.admin_api import AdminApi

KEY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'keys')

def provision_dongle(port='COM7'):
    priv_path = os.path.join(KEY_DIR, 'root_ca_key.pem')
    if not os.path.exists(priv_path):
        print("[-] Root CA Private Key not found! Run generate_root_ca.py first.")
        return
        
    print("[*] Loading Root CA Private Key...")
    with open(priv_path, "rb") as f:
        root_ca_priv = serialization.load_pem_private_key(f.read(), password=None)
        
    print(f"[*] Connecting to Dongle on {port}...")
    transport = SerialTransport(port=port)
    try:
        rpc = RpcProtocol(transport)
        admin = AdminApi(rpc, admin_pin='1234')
        
        print("\n--- STEP 1: Requesting Dongle Identity Generation ---")
        # In actual implementation, firmware will generate PUF-backed key, save private to NVM3, and return public
        resp = admin.provision_identity()
        if not resp.startswith("OK:"):
            print(f"[-] Failed to provision identity: {resp}")
            return
            
        pub_key_hex = resp.replace("OK: ", "").strip()
        print(f"[+] Received Dongle Public Key: {pub_key_hex}")
        dongle_pub_bytes = bytes.fromhex(pub_key_hex)
        
        print("\n--- STEP 2: Signing Public Key with Root CA (Creating Cert) ---")
        signature = root_ca_priv.sign(
            dongle_pub_bytes,
            ec.ECDSA(hashes.SHA256())
        )
        print(f"[+] Signature generated. Length: {len(signature)} bytes")
        
        print("\n--- STEP 3: Saving Certificate to Dongle NVM3 ---")
        # Send signature to dongle so it stores it alongside its public key
        # (This acts as a raw certificate)
        resp2 = admin.save_certificate(signature)
        if not resp2.startswith("OK:"):
            print(f"[-] Failed to save certificate on dongle: {resp2}")
            return
            
        print("[+] SUCCESS: Dongle has been successfully provisioned and certificated.")

    finally:
        transport.close()

if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM7'
    provision_dongle(port)
