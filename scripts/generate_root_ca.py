import os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

KEY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'keys')

def generate_root_ca():
    if not os.path.exists(KEY_DIR):
        os.makedirs(KEY_DIR)
        
    priv_path = os.path.join(KEY_DIR, 'root_ca_key.pem')
    pub_path = os.path.join(KEY_DIR, 'root_ca_pub.pem')
    
    if os.path.exists(priv_path):
        print(f"[!] Root CA already exists at {priv_path}. Aborting to prevent overwriting.")
        return

    print("Generating NIST P-256 (SECP256R1) Root CA key pair...")
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    
    # Save private key
    with open(priv_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption() # Can be encrypted with BestAvailableEncryption(b'password')
        ))
    
    # Save public key
    with open(pub_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
        
    print(f"[*] Root CA generated successfully.\nPrivate: {priv_path}\nPublic: {pub_path}")
    print("\nWARNING: Keep the private key safe and offline. The public key must be embedded in compass.exe.")

if __name__ == '__main__':
    generate_root_ca()
