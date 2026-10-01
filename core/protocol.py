import time
import re
from datetime import datetime
from .transport import SerialTransport, MSG_LOG, MSG_OK, MSG_ERR

class RpcProtocol:
    def __init__(self, transport: SerialTransport):
        self.transport = transport
        
        # Register listener for background logs from MCU
        self.transport.tf.add_type_listener(MSG_LOG, self._on_log)

    def _on_log(self, tf, msg):
        log_str = msg.data.decode('utf-8', errors='ignore')
        print(f'   [MCU] {self._format_timestamps(log_str)}')
        return True # stay active

    def _format_timestamps(self, text: str) -> str:
        def replace_ts(m):
            ts = int(m.group(0))
            if 1577836800 <= ts <= 2524608000:
                return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            return m.group(0)
        text = re.sub(r'\b\d{10}\b', replace_ts, text)
        return self._format_elapsed(text)

    def _format_elapsed(self, text: str) -> str:
        def replace_elapsed(m):
            mins = int(m.group(1))
            if mins >= 60:
                h = mins // 60
                m_rem = mins % 60
                return f'Od sync minelo: {h} h {m_rem} m'
            return m.group(0)
        return re.sub(r'Od sync minelo: (\d+) minut', replace_elapsed, text)

    def execute_command(self, cmd_id: int, payload: bytes = b'', timeout_sec: float = 2.0, max_retries: int = 3) -> str:
        # Check if we should encrypt
        is_secure = hasattr(self, 'secure_channel') and self.secure_channel and self.secure_channel.is_active
        if is_secure and cmd_id in (0x06, 0x09): # MSG_COMPASS_ALG1, MSG_COMPASS_USERS
            payload = self.secure_channel.encrypt_payload(payload)
            print(f'[Protocol] Sending ENCRYPTED ID: 0x{cmd_id:02X}, CipherLen: {len(payload)}')
        else:
            print(f'[Protocol] Sending ID: 0x{cmd_id:02X}, Length: {len(payload)}')
        
        for attempt in range(max_retries):
            resp = self.transport.query(cmd_id, payload, timeout=timeout_sec)
            if resp is not None:
                resp_data = resp.data
                
                # If it was a secure command, decrypt the response (whether OK or ERR)
                if is_secure and cmd_id in (0x06, 0x09) and resp.type in (MSG_OK, MSG_ERR):
                    try:
                        resp_data = self.secure_channel.decrypt_payload(resp_data)
                    except Exception as e:
                        return f"ERR: Decryption Failed - {str(e)}"
                
                data_str = resp_data.decode('utf-8', errors='ignore')
                if resp.type == MSG_OK:
                    return f"OK: {data_str}"
                elif resp.type == MSG_ERR:
                    return f"ERR: {data_str}"
                else:
                    return f"UNKNOWN: {data_str}"
            
            # If we caught a dropped packet, retry after a short delay
            if attempt < max_retries - 1:
                print(f'[Protocol] Packet corrupted (CRC). Retransmission {attempt + 1}/{max_retries}...')
                time.sleep(0.1)

        raise TimeoutError(f'Critical hardware error: No response for command 0x{cmd_id:02X} (Failed retransmissions)!')
