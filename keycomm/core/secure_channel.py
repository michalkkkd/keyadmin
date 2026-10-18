import os
import struct
import threading
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.exceptions import InvalidSignature

from keycomm.core.constants import (
    MSG_HANDSHAKE_INIT, MSG_OK,
    HKDF_CLIENT_INFO, HKDF_SERVER_INFO,
    NONCE_DIR_HOST_TO_DEVICE, NONCE_DIR_DEVICE_TO_HOST,
    CHAR_ENCODING_UTF8, BYTEORDER_BIG,
    ERR_SECURE_NOT_ESTABLISHED, ERR_COUNTER_EXHAUSTED, ERR_PAYLOAD_TOO_SHORT,
    LOG_FMT_ROOT_CA_NOT_FOUND, LOG_HANDSHAKE_INIT, LOG_HANDSHAKE_NO_RESP,
    LOG_FMT_HANDSHAKE_MCU_ERR, LOG_HANDSHAKE_INVALID_LEN, LOG_HANDSHAKE_SIG_MISMATCH,
    LOG_FMT_MCU_EPH_KEY, LOG_FMT_MCU_ID_KEY, LOG_FMT_CERT_SIZE,
    LOG_CERT_VERIFIED, LOG_CERT_INVALID, LOG_SIG_VERIFIED, LOG_SIG_INVALID,
    LOG_SESSION_ESTABLISHED, ERR_FMT_REPLAY_ATTACK
)

class SecureChannel:
    def __init__(self, rpc, root_ca_pub_path):
        self.rpc = rpc
        self.root_ca_pub_path = root_ca_pub_path
        self._lock = threading.RLock()
        self.client_aesgcm = None
        self.server_aesgcm = None
        self.rx_nonce_counter = 0
        self.tx_nonce_counter = 0
        self.is_active = False
        self.root_ca_pub = None
        self._load_root_ca()

    def _load_root_ca(self):
        if self.root_ca_pub_path and os.path.isfile(self.root_ca_pub_path):
            with open(self.root_ca_pub_path, "rb") as f:
                self.root_ca_pub = serialization.load_pem_public_key(f.read())

    def init_handshake(self) -> bool:
        with self._lock:
            self.is_active = False
            self.client_aesgcm = None
            self.server_aesgcm = None
            self.tx_nonce_counter = 0
            self.rx_nonce_counter = 0

            # Ensure Root CA Pub Key is loaded
            if self.root_ca_pub is None:
                self._load_root_ca()
            if self.root_ca_pub is None:
                print(LOG_FMT_ROOT_CA_NOT_FOUND.format(path=self.root_ca_pub_path))
                return False
            root_ca_pub = self.root_ca_pub

        # Generate PC Ephemeral Key
        pc_priv = ec.generate_private_key(ec.SECP256R1())
        pc_pub = pc_priv.public_key().public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        # Generate Challenge Nonce
        pc_nonce = os.urandom(32)
        
        payload = pc_pub + pc_nonce
        
        print(LOG_HANDSHAKE_INIT)
        resp = self.rpc.transport.query(MSG_HANDSHAKE_INIT, payload, timeout=5.0)
        
        if not resp:
            print(LOG_HANDSHAKE_NO_RESP)
            return False
            
        if resp.type != MSG_OK:
            err_msg = resp.data.decode(CHAR_ENCODING_UTF8, errors='ignore')
            print(LOG_FMT_HANDSHAKE_MCU_ERR.format(err=err_msg))
            return False

        data = resp.data
        if len(data) < 131:
            print(LOG_HANDSHAKE_INVALID_LEN)
            return False

        mcu_eph_pub_bytes = bytes(data[:65])
        dongle_id_pub_bytes = bytes(data[65:130])
        sig_len = data[130]
        
        if len(data) < 131 + sig_len:
            print(LOG_HANDSHAKE_SIG_MISMATCH)
            return False
            
        signature = bytes(data[131:131+sig_len])
        cert_bytes = bytes(data[131+sig_len:])
        
        print(LOG_FMT_MCU_EPH_KEY.format(key_hex=mcu_eph_pub_bytes.hex()[:16]))
        print(LOG_FMT_MCU_ID_KEY.format(key_hex=dongle_id_pub_bytes.hex()[:16]))
        print(LOG_FMT_CERT_SIZE.format(size=len(cert_bytes)))

        # 1. Verify Device Certificate against Root CA
        try:
            root_ca_pub.verify(
                cert_bytes,
                dongle_id_pub_bytes,
                ec.ECDSA(hashes.SHA256())
            )
            print(LOG_CERT_VERIFIED)
        except InvalidSignature:
            print(LOG_CERT_INVALID)
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
                r = int.from_bytes(signature[:32], BYTEORDER_BIG)
                s = int.from_bytes(signature[32:], BYTEORDER_BIG)
                signature = utils.encode_dss_signature(r, s)

            dongle_id_pub.verify(
                signature,
                hash_val,
                ec.ECDSA(utils.Prehashed(hashes.SHA256()))
            )
            print(LOG_SIG_VERIFIED)
        except InvalidSignature:
            print(LOG_SIG_INVALID)
            return False

        # 3. Compute Shared Secret & Derive Dual Directional AES Keys (HKDF-SHA256)
        mcu_eph_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), mcu_eph_pub_bytes)
        shared_secret = pc_priv.exchange(ec.ECDH(), mcu_eph_pub)
        
        # Derive client_write_key (Host -> Device, PC encrypts)
        hkdf_client = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=pc_nonce,
            info=HKDF_CLIENT_INFO,
        )
        client_write_key = hkdf_client.derive(shared_secret)

        # Derive server_write_key (Device -> Host, PC decrypts)
        hkdf_server = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=pc_nonce,
            info=HKDF_SERVER_INFO,
        )
        server_write_key = hkdf_server.derive(shared_secret)

        self.client_aesgcm = AESGCM(client_write_key)
        self.server_aesgcm = AESGCM(server_write_key)
        self.tx_nonce_counter = 0
        self.rx_nonce_counter = 0
        self.is_active = True
        
        print(LOG_SESSION_ESTABLISHED)
        return True

    def encrypt_payload(self, plaintext: bytes) -> bytes:
        with self._lock:
            if not self.is_active or self.client_aesgcm is None:
                raise RuntimeError(ERR_SECURE_NOT_ESTABLISHED)
                
            if self.tx_nonce_counter >= 0xFFFFFFFF:
                raise OverflowError(ERR_COUNTER_EXHAUSTED)

            self.tx_nonce_counter += 1
            # 12-byte Nonce: [4 bytes uint32_le counter] [NONCE_DIR_HOST_TO_DEVICE] [7 zero bytes]
            nonce = struct.pack('<IB7x', self.tx_nonce_counter, NONCE_DIR_HOST_TO_DEVICE)
            
            ciphertext = self.client_aesgcm.encrypt(nonce, plaintext, associated_data=None)
            
            # We prepend only the 4-byte counter to ciphertext + tag (saves UART bandwidth)
            return struct.pack('<I', self.tx_nonce_counter) + ciphertext

    def decrypt_payload(self, encrypted: bytes) -> bytes:
        with self._lock:
            if not self.is_active or self.server_aesgcm is None:
                raise RuntimeError(ERR_SECURE_NOT_ESTABLISHED)
                
            if len(encrypted) < 20: # 4 (counter) + 16 (tag)
                raise ValueError(ERR_PAYLOAD_TOO_SHORT)
                
            incoming_counter = struct.unpack('<I', encrypted[:4])[0]

            # Enforce strict monotonic nonce check
            if incoming_counter <= self.rx_nonce_counter:
                raise ValueError(ERR_FMT_REPLAY_ATTACK.format(incoming=incoming_counter, last_seen=self.rx_nonce_counter))

            # 12-byte Nonce: [4 bytes uint32_le counter] [NONCE_DIR_DEVICE_TO_HOST] [7 zero bytes]
            nonce = struct.pack('<IB7x', incoming_counter, NONCE_DIR_DEVICE_TO_HOST)
            ciphertext = encrypted[4:]
            
            plaintext = self.server_aesgcm.decrypt(nonce, ciphertext, associated_data=None)

            # Commit new counter strictly after successful authenticated decryption
            self.rx_nonce_counter = incoming_counter
            return plaintext


