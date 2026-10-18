import time
import re
import threading
from datetime import datetime

from keycomm.core.transport import SerialTransport
from keycomm.core.constants import (
    MSG_LOG, MSG_OK, MSG_ERR, SECURE_CMD_IDS,
    RESP_OK_PREFIX, RESP_ERR_PREFIX, RESP_UNKNOWN_PREFIX, RESP_FIRE_AND_FORGET,
    DUMMY_PAYLOAD_BYTE, EMPTY_BYTES, CHAR_ENCODING_UTF8,
    MCU_ERR_SESSION_INACTIVE, MCU_ERR_DECRYPT_FAILED, MCU_ERR_DECRYPTION_FAILED,
    MCU_ERR_LIC_EXPIRED,
    LOG_FMT_SENDING, LOG_FMT_MCU, LOG_FMT_CORRUPTED_CRC, LOG_FMT_SESSION_ERROR,
    LOG_FMT_DECRYPT_FAIL, ERR_FMT_DECRYPT_FAILED, ERR_FMT_TIMEOUT_RETRIES,
    TIMESTAMP_FMT, RE_SYNC_ELAPSED, SYNC_ELAPSED_FMT
)


class RpcProtocol:
    SECURE_CMD_IDS = SECURE_CMD_IDS

    def __init__(self, transport: SerialTransport):
        self.transport = transport
        self._lock = threading.RLock()

        # Telemetry counters for diagnostics and stress testing
        self.retransmissions_count = 0
        self.timeouts_count = 0
        self.session_resets_count = 0

        # Register listener for background logs from MCU
        self.transport.tf.add_type_listener(MSG_LOG, self._on_log)

    def _on_log(self, tf, msg):
        log_str = msg.data.decode(CHAR_ENCODING_UTF8, errors='ignore')
        print(LOG_FMT_MCU.format(text=self._format_timestamps(log_str)))
        return True  # stay active

    def _format_timestamps(self, text: str) -> str:
        def replace_ts(m):
            ts = int(m.group(0))
            if 1577836800 <= ts <= 2524608000:
                return datetime.fromtimestamp(ts).strftime(TIMESTAMP_FMT)
            return m.group(0)
        text = re.sub(r'\b\d{10}\b', replace_ts, text)
        return self._format_elapsed(text)

    def _format_elapsed(self, text: str) -> str:
        def replace_elapsed(m):
            mins = int(m.group(1))
            if mins >= 60:
                h = mins // 60
                m_rem = mins % 60
                return SYNC_ELAPSED_FMT.format(h=h, m=m_rem)
            return m.group(0)
        return re.sub(RE_SYNC_ELAPSED, replace_elapsed, text)

    def execute_command(self, cmd_id: int, payload: bytes = EMPTY_BYTES, timeout_sec: float = 2.0, max_retries: int = 5, fire_and_forget: bool = False) -> str:
        with self._lock:
            # Check if command requires encryption
            is_secure = hasattr(self, 'secure_channel') and self.secure_channel and self.secure_channel.is_active

            raw_payload = payload
            if is_secure and cmd_id in self.SECURE_CMD_IDS:
                if not raw_payload:
                    raw_payload = DUMMY_PAYLOAD_BYTE
            else:
                if not fire_and_forget:
                    print(LOG_FMT_SENDING.format(cmd=cmd_id, len=len(raw_payload)))

            for attempt in range(max_retries):
                # Re-encrypt for each attempt to guarantee fresh monotonic nonce counter on retries
                if is_secure and cmd_id in self.SECURE_CMD_IDS:
                    tx_payload = self.secure_channel.encrypt_payload(raw_payload)
                else:
                    tx_payload = raw_payload

                if fire_and_forget:
                    self.transport.tf.send(cmd_id, tx_payload)
                    return RESP_FIRE_AND_FORGET

                resp = self.transport.query(cmd_id, tx_payload, timeout=timeout_sec)
                if resp is not None:
                    resp_data = resp.data

                    # If it was a secure command, decrypt the response (whether OK or ERR)
                    if is_secure and cmd_id in self.SECURE_CMD_IDS and resp.type in (MSG_OK, MSG_ERR):
                        # If MCU responded with an unencrypted error (e.g. ERR: Decrypt Failed, License expired, Secure Session Not Active),
                        # preserve the diagnostic string instead of failing with "Encrypted payload too short"
                        if resp.type == MSG_ERR and (len(resp_data) < 20 or resp_data.startswith(b"ERR:") or resp_data.startswith(MCU_ERR_LIC_EXPIRED.encode())):
                            data_str = resp_data.decode(CHAR_ENCODING_UTF8, errors='ignore')
                            if (MCU_ERR_SESSION_INACTIVE in data_str or MCU_ERR_DECRYPT_FAILED in data_str or MCU_ERR_DECRYPTION_FAILED in data_str) and attempt < max_retries - 1 and hasattr(self, 'secure_channel') and self.secure_channel:
                                self.session_resets_count += 1
                                self.retransmissions_count += 1
                                print(LOG_FMT_SESSION_ERROR.format(data_str=data_str))
                                if self.secure_channel.init_handshake():
                                    is_secure = self.secure_channel.is_active
                                    time.sleep(0.05)
                                    continue
                            return f"{RESP_ERR_PREFIX}{data_str}"
                        try:
                            resp_data = self.secure_channel.decrypt_payload(resp_data)
                        except Exception as e:
                            if attempt < max_retries - 1 and hasattr(self, 'secure_channel') and self.secure_channel:
                                self.session_resets_count += 1
                                self.retransmissions_count += 1
                                print(LOG_FMT_DECRYPT_FAIL.format(e=e))
                                if self.secure_channel.init_handshake():
                                    is_secure = self.secure_channel.is_active
                                    time.sleep(0.05)
                                    continue
                            return f"{RESP_ERR_PREFIX}{ERR_FMT_DECRYPT_FAILED.format(err=str(e))}"

                    data_str = resp_data.decode(CHAR_ENCODING_UTF8, errors='ignore')
                    if resp.type == MSG_OK:
                        return f"{RESP_OK_PREFIX}{data_str}"
                    elif resp.type == MSG_ERR:
                        return f"{RESP_ERR_PREFIX}{data_str}"
                    else:
                        return f"{RESP_UNKNOWN_PREFIX}{data_str}"

                # Flush stale responses from serial buffer before retransmitting.
                self.timeouts_count += 1
                if attempt < max_retries - 1:
                    self.retransmissions_count += 1
                    print(LOG_FMT_CORRUPTED_CRC.format(attempt=attempt + 1, max_retries=max_retries))
                    try:
                        self.transport.ser.reset_input_buffer()
                    except Exception:
                        pass
                    time.sleep(0.3)

            return f"{RESP_ERR_PREFIX}{ERR_FMT_TIMEOUT_RETRIES.format(retries=max_retries)}"

