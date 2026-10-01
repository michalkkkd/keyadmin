# Active Users Limit Mechanism (10-Minute Window)

## 1. Overview
The Compass application operates as a Tornado-based web server. Because multiple users can connect via browser sessions, the system must restrict usage to a hard maximum of *concurrently active users*. A user is considered "active" only if they have interacted with the application within the last **10 minutes** (600 seconds).

## 2. Data Collection (Compass Application)
To enforce this rule, the Compass backend (via its SessionManager and session_store.json) must track specific telemetry for every connected user:
* **Session Token / User ID:** A unique identifier for the user (e.g., a SHA-256 hash of their email or browser fingerprint).
* **Last Activity Timestamp (last_seen_at):** A Unix timestamp updated upon every API call or UI interaction made by that specific session.

## 3. Enforcement Variants (Security Levels)

### Variant 1: Software Enforcement (Weakest)
* **Mechanism:** Compass reads MAX_USERS from the KeySec dongle at boot. Compass internally filters its session_store.json to count sessions where (current_time - last_seen_at) <= 600. If the count exceeds the limit, Compass UI rejects new logins.
* **Vulnerability:** An attacker who unpacks the Nuitka executable could patch out the if active_count > MAX_USERS check. The hardware dongle has no idea how many users are actually calculating data.

### Variant 2: Hardware Enforcement via Algorithm Blocking (Strong)
* **Mechanism:** The dongle itself is responsible for counting active users.
  - The Compass app must attach the user_id_hash to every algorithm calculation request (e.g., MSG_COMPASS_ALG1).
  - The EFR32 firmware maintains an internal RAM array: struct ActiveUser { uint32_t user_hash; uint32_t last_seen; };
  - Upon receiving a calculation request, the dongle updates last_seen for that hash.
  - The dongle then sweeps the array, clearing any hashes older than 10 minutes (using its synchronized Global RTC).
  - If a new hash arrives and the array already contains MAX_USERS active slots, the dongle returns a strict ERR_USER_LIMIT and refuses to calculate the math.
* **Advantage:** Even if the Python app is completely decompiled and patched, the hardware will physically refuse to process requests for excess users.

### Variant 3: Hardware Enforcement with Session Tokens (Strongest)
* **Mechanism:** Instead of just sending a hash, Compass must explicitly request a "Hardware Session Slot" from the dongle.
  - Compass sends MSG_REQUEST_SESSION (user_id_hash).
  - The dongle verifies the 10-minute sliding window limit. If a slot is available, it generates a temporary 16-byte session_key (via Secure Vault TRNG) and returns it.
  - For the next 10 minutes, all algorithm requests for that user MUST be encrypted with that specific session_key.
  - The dongle silently drops the key from its RAM after 10 minutes of inactivity.
* **Advantage:** Completely prevents Replay Attacks and Man-in-the-Middle multiplexing (where a hacked host app tries to funnel multiple users through a single hardware session slot).

## 4. Recommended Implementation
We strongly recommend **Variant 2** as the baseline, with a future upgrade path to **Variant 3**. 
* **Data to send to KeySec:** user_id_hash (4 bytes) appended to the payload of MSG_COMPASS_ALG1.
* **Hardware RAM overhead:** Minimal. Tracking 50 users requires just 50 * 8 bytes = 400 bytes of RAM inside the EFR32.
