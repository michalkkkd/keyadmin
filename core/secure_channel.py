import os
import struct
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidSignature

class SecureChannel:
    def __init__(self, rpc, root_ca_pub_path):
        self.rpc = rpc
        self.root_ca_pub_path = root_ca_pub_path
        self.aesgcm = None
        self.rx_nonce_counter = 0
        self.tx_nonce_counter = 0
        self.is_active = False

    def init_handshake(self) -> bool:
        # Load Root CA Pub Key
        with open(self.root_ca_pub_path, "rb") as f:
            root_ca_pub = serialization.load_pem_public_key(f.read())

        # Generate PC Ephemeral Key
        pc_priv = ec.generate_private_key(ec.SECP256R1())
        pc_pub = pc_priv.public_key().public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        # Generate Challenge Nonce
        pc_nonce = os.urandom(32)
        
        payload = pc_pub + pc_nonce
        
        print("[SecureChannel] Sending Handshake Init...")
        # 0x0D = MSG_HANDSHAKE_INIT
        resp = self.rpc.transport.query(0x0D, payload, timeout=5.0)
        
        if not resp:
            print("[-] Handshake Failed: No response from MCU")
            return False
            
        if resp.type != 0x80: # MSG_OK = 0x80
            err_msg = resp.data.decode('utf-8', errors='ignore')
            print(f"[-] Handshake Failed on MCU side. Error: {err_msg}")
            return False

        data = resp.data
        if len(data) < 131:
            print("[-] Invalid handshake response length")
            return False

        mcu_eph_pub_bytes = bytes(data[:65])
        dongle_id_pub_bytes = bytes(data[65:130])
        sig_len = data[130]
        
        if len(data) < 131 + sig_len:
            print("[-] Signature length mismatch")
            return False
            
        signature = bytes(data[131:131+sig_len])
        cert_bytes = bytes(data[131+sig_len:])
        
        print(f"[SecureChannel] MCU Eph Key: {mcu_eph_pub_bytes.hex()[:16]}...")
        print(f"[SecureChannel] MCU ID Key: {dongle_id_pub_bytes.hex()[:16]}...")
        print(f"[SecureChannel] Cert Size: {len(cert_bytes)} bytes")

        # 1. Verify Device Certificate against Root CA
        try:
            root_ca_pub.verify(
                cert_bytes,
                dongle_id_pub_bytes,
                ec.ECDSA(hashes.SHA256())
            )
            print("[+] Device Certificate VERIFIED. Authentic Dongle detected.")
        except InvalidSignature:
            print("[-] Device Certificate INVALID. Counterfeit Dongle!")
            return False

        # 2. Verify Handshake Signature
        # MCU signs: SHA256(pc_nonce + mcu_eph_pub_bytes)
        dongle_id_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), dongle_id_pub_bytes)
        
        to_verify = pc_nonce + mcu_eph_pub_bytes
        digest = hashes.Hash(hashes.SHA256())
        digest.update(to_verify)
        hash_val = digest.finalize()
        
        try:
            from cryptography.hazmat.primitives.asymmetric import utils
            
            if len(signature) == 64:
                r = int.from_bytes(signature[:32], 'big')
                s = int.from_bytes(signature[32:], 'big')
                signature = utils.encode_dss_signature(r, s)

            dongle_id_pub.verify(
                signature,
                hash_val,
                ec.ECDSA(utils.Prehashed(hashes.SHA256()))
            )
            print('[+] Handshake Signature VERIFIED. MitM protection active.')
        except InvalidSignature:
            print('[-] Handshake Signature INVALID. Possible Man-in-the-Middle Attack!')
            return False

        # 3. Compute Shared Secret & AES Key
        mcu_eph_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), mcu_eph_pub_bytes)
        shared_secret = pc_priv.exchange(ec.ECDH(), mcu_eph_pub)
        
        digest = hashes.Hash(hashes.SHA256())
        digest.update(shared_secret)
        aes_key = digest.finalize()
        
        self.aesgcm = AESGCM(aes_key)
        self.tx_nonce_counter = 0
        self.rx_nonce_counter = 0
        self.is_active = True
        
        print("[+] Secure Session Established! (AES-256-GCM)")
        return True

    def encrypt_payload(self, plaintext: bytes) -> bytes:
        if not self.is_active:
            raise RuntimeError("Secure session not established")
            
        self.tx_nonce_counter += 1
        # Little endian 4-byte counter for nonce. Padded to 12 bytes with zeroes implicitly by firmware, wait.
        # Firmware uses: `uint8_t nonce[12] = {0}; memcpy(nonce, &tx_nonce_counter, 4);`
        # So nonce is 4 bytes little endian followed by 8 bytes of zeros.
        nonce = struct.pack('<I', self.tx_nonce_counter) + b'\x00' * 8
        
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, associated_data=None)
        
        # We prepend the 4-byte counter (not the full 12 bytes, to save UART bandwidth)
        return struct.pack('<I', self.tx_nonce_counter) + ciphertext

    def decrypt_payload(self, encrypted: bytes) -> bytes:
        if not self.is_active:
            raise RuntimeError("Secure session not established")
            
        if len(encrypted) <= 20: # 4 (nonce) + 16 (tag)
            raise ValueError("Encrypted payload too short")
            
        tx_counter = struct.unpack('<I', encrypted[:4])[0]
        nonce = encrypted[:4] + b'\x00' * 8
        
        ciphertext = encrypted[4:]
        
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, associated_data=None)
        return plaintext

