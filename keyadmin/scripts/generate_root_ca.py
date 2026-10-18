import os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(ADMIN_DIR)

KEYADMIN_KEYS_DIR = os.path.join(ADMIN_DIR, 'keys')
KEYCOMM_KEYS_DIR = os.path.join(REPO_ROOT, 'keycomm', 'keys')


def generate_root_ca():
    os.makedirs(KEYADMIN_KEYS_DIR, exist_ok=True)
    os.makedirs(KEYCOMM_KEYS_DIR, exist_ok=True)

    priv_path = os.path.join(KEYADMIN_KEYS_DIR, 'root_ca_key.pem')
    pub_admin_path = os.path.join(KEYADMIN_KEYS_DIR, 'root_ca_pub.pem')
    pub_comm_path = os.path.join(KEYCOMM_KEYS_DIR, 'root_ca_pub.pem')

    if os.path.exists(priv_path):
        print(f"[!] Root CA already exists at {priv_path}. Aborting to prevent overwriting.")
        return

    print("Generating NIST P-256 (SECP256R1) Root CA key pair...")
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Save private key strictly in keyadmin/keys
    with open(priv_path, "wb") as f:
        f.write(priv_bytes)

    # Save public key in keyadmin/keys and keycomm/keys
    with open(pub_admin_path, "wb") as f:
        f.write(pub_bytes)

    with open(pub_comm_path, "wb") as f:
        f.write(pub_bytes)

    print(f"[*] Root CA generated successfully.")
    print(f"    Private (CRITICAL SECRECY): {priv_path}")
    print(f"    Public (Admin):            {pub_admin_path}")
    print(f"    Public (Client / keycomm): {pub_comm_path}")
    print("\nWARNING: Keep the private key safe and offline. Only the public key goes to keycomm/client.")


if __name__ == '__main__':
    generate_root_ca()
