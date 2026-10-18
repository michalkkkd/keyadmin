# Cryptography Flow & Keys Architecture (Variant B+ ECDHE with Root CA)

This document specifies the information flow, role, and storage location of every element used in the cryptographic process protecting the Compass application and the KeyFirmware hardware dongle.

## 1. List of All Used Keys

The following table gathers all cryptographic keys used in the system:

| Key Name | Where is it generated? | Where and how is it stored? | What is it used for? | Confidentiality |
|---|---|---|---|---|
| **Root CA Private Key** | Utility script on an isolated company PC in the factory. | Secured file (e.g., .pem with a password) offline. **Never** goes to the client. | Signing public identity certificates for newly manufactured Dongles. (Provisioning). | **CRITICAL** |
| **Root CA Public Key** | Derived from Root CA Private Key. | Hardcoded directly into the Compass client application code. | Authenticity verification (signature checking) of the connected Dongle. The PC checks if the Dongle's certificate came from your factory. | Public |
| **PUF Root Key (RK)** | EFR32MG24 Silicon (Automatically at boot, SRAM physics). | Exists only in volatile hardware cells and is hidden from the main Cortex-M33 processor. Disappears after power off. | Used by the built-in Hardware Security Engine (HSE) to wrap (encrypt) other keys stored in Flash. | **CRITICAL** |
| **Identity Private Key (Device)** | Inside the EFR32 crypto processor (during provisioning). | Stored in Flash (NVM3), but wrapped (encrypted) by the PUF key. No one (not even your C code) has plaintext access to it. | Device identity. Used EXCLUSIVELY to sign the ephemeral key during USB plug-in, proving it's an authentic dongle. | **CRITICAL** |
| **Identity Public Key (Device)** | Derived from the Identity Private Key above during provisioning. | Part of the Device Certificate stored in plaintext in the Dongle's NVM3 Flash memory. Sent to the PC at startup. | Verified by the PC, attests the binding of the physical device to the factory. | Public |
| **PC Ephemeral Key (ECDHE)** | Python process (Compass) on the client PC, at every connection. | Application RAM. Destroyed after deriving the session key. | One half of the Diffie-Hellman puzzle to derive the session key. Changes after disconnect/forced rotation. | Protected (PFS) |
| **Device Ephemeral Key (ECDHE)** | EFR32MG24 Microcontroller, at every connection. | Crypto engine RAM. Destroyed after deriving the session key. | Second half of the Diffie-Hellman puzzle. | Protected (PFS) |
| **Session Key (AES-256-GCM)** | Result of HKDF on both devices (PC and Dongle) based on the Ephemeral exchange. | PC RAM and volatile coprocessor slots in EFR32. Completely destroyed after key rotation (e.g., every minute) or USB disconnect. | The main "meat". We encrypt physical data flowing through the COM port with this key. Rotation protects against PC RAM dumps. | **HIGH** |

---

## 2. Flow Diagrams

### Process A: Provisioning (Factory Production)
You execute this process at your desk after soldering the board, using KeySec scripts.

`mermaid
sequenceDiagram
    participant Factory (KeySec)
    participant EFR32 (KeyFirmware)
    participant HSE (Hardware Security Engine)

    Note over Factory (KeySec): Holds "Root CA Private Key" in an offline safe
    Factory (KeySec)->>EFR32 (KeyFirmware): CMD_PROVISION_IDENTITY
    EFR32 (KeyFirmware)->>HSE (Hardware Security Engine): Generate Key Pair (Identity)
    HSE (Hardware Security Engine)-->>EFR32 (KeyFirmware): Return Public Key, hide Private (PUF)
    EFR32 (KeyFirmware)-->>Factory (KeySec): Identity Public Key
    Note over Factory (KeySec): Creating Certificate:<br>1. Creates payload: "EFR32 Public Key"<br>2. Signs payload using Root CA Priv Key
    Factory (KeySec)->>EFR32 (KeyFirmware): CMD_SAVE_CERTIFICATE (Device Cert)
    EFR32 (KeyFirmware)->>EFR32 (KeyFirmware): Save Certificate in NVM3
    Note over EFR32 (KeyFirmware), Factory (KeySec): PROCESS COMPLETED - DEVICE READY FOR SHIPPING
`

### Process B: Handshake and Protection (At Client Site)
This process triggers immediately every time the client software (Compass) attempts to communicate with the Dongle.

`mermaid
sequenceDiagram
    participant Compass (PC Client)
    participant EFR32 (PUF Dongle)

    Note over Compass (PC Client): Holds hardcoded Root CA Public Key
    Compass (PC Client)->>EFR32 (PUF Dongle): CMD_HELLO
    EFR32 (PUF Dongle)-->>Compass (PC Client): Sends its Device Certificate (from NVM3)
    Note over Compass (PC Client): Verifies Certificate using Root CA Pub Key.<br>Checks if the Dongle is counterfeit.
    
    Note over Compass (PC Client), EFR32 (PUF Dongle): --- START ECDHE EXCHANGE ---
    Compass (PC Client)->>Compass (PC Client): Generates PC_Ephemeral_Key
    EFR32 (PUF Dongle)->>EFR32 (PUF Dongle): Generates Device_Ephemeral_Key
    
    Compass (PC Client)->>EFR32 (PUF Dongle): PC_Ephemeral_Pub_Key
    Note over EFR32 (PUF Dongle): Hardware signs (ECDSA)<br>its ephemeral using Identity Private Key (from PUF)
    EFR32 (PUF Dongle)-->>Compass (PC Client): Device_Ephemeral_Pub_Key + SIGNATURE
    
    Note over Compass (PC Client): Verifies SIGNATURE using Pub Key from Dongle's Certificate.<br>Secures against Man-in-the-Middle!
    
    Note over Compass (PC Client), EFR32 (PUF Dongle): Both parties calculate Shared Secret = f(My_Priv, Their_Pub)<br>From it, they derive the target Session_Key (HKDF)
    
    Note over Compass (PC Client), EFR32 (PUF Dongle): --- ENCRYPTED COMMUNICATION ---
    Compass (PC Client)->>EFR32 (PUF Dongle): GCM_ENCRYPT(AES_Session_Key, Counter=1, Data="Check status")
    EFR32 (PUF Dongle)-->>Compass (PC Client): GCM_ENCRYPT(AES_Session_Key, Counter=2, Data="OK")
    
    Note over Compass (PC Client), EFR32 (PUF Dongle): (After 1 minute) - REKEYING
    Compass (PC Client)->>EFR32 (PUF Dongle): CMD_REKEY (Without dropping session)
    Note over Compass (PC Client), EFR32 (PUF Dongle): Destruction of AES_Session_Key, generation of new one.
`
