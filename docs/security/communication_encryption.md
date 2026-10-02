# Communication Encryption Mechanism

## 1. Overview
The communication channel between the Windows Python application (host) and the USB dongle operates over a virtual serial port (VCOM/UART). Since this bus can be monitored using software USB sniffers (like Wireshark or Device Monitoring Studio), the TinyFrame RPC payloads must be heavily encrypted.

## 2. Design and Implementation (Phase 2/3)
* **Underlying Protocol:** TinyFrame acts as the binary transport layer, ensuring frame integrity (CRC16/CRC32) and routing.
* **Cryptographic Payload:** Inside the TinyFrame data payload, all parameters and responses will be encrypted.
* **Proposed Algorithms:**
  - **Key Exchange:** ECDH (Elliptic-Curve Diffie-Hellman) performed upon initial handshake to establish a shared session key, preventing replay and eavesdropping attacks.
  - **Symmetric Encryption:** AES-256-GCM or ChaCha20-Poly1305. These algorithms provide Authenticated Encryption with Associated Data (AEAD), ensuring both confidentiality and integrity.
* **Hardware Acceleration:** The EFR32MG24 features an integrated crypto engine (Secure Vault) that will be utilized to perform AES operations with zero CPU overhead and extreme security against side-channel attacks.

## 3. Threat Mitigation
* **Replay Attacks:** Handshakes will include a nonce or a monotonic counter to ensure a captured "Calculate Algorithm" command cannot be sent repeatedly.
* **Man-in-the-Middle (MitM):** The initial public keys will be pre-provisioned or signed to ensure the host is talking to a genuine dongle, and the dongle is talking to a genuine host application.
