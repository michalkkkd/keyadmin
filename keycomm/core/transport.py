import serial
import time
import threading

from keycomm.core.TinyFrame import TinyFrame
from keycomm.core.constants import (
    MSG_LOG, MSG_PING, MSG_CHECK_LIC, MSG_TEST_ADD, MSG_COMPASS_USERS,
    MSG_SYS_HEALTH, MSG_VRX,
    MSG_SIM_PK_GI_INIT, MSG_SIM_PK_GI_CHUNK, MSG_SIM_PK_GI_PROCESS, MSG_SIM_PK_GI_READ,
    MSG_SAFE_SPACE_INIT, MSG_SAFE_SPACE_CHUNK, MSG_SAFE_SPACE_PROCESS, MSG_SAFE_SPACE_READ,
    MSG_SAFE_SPACE_RESET, MSG_SAFE_SPACE_FINISH,
    MSG_SSP_A_INIT, MSG_SSP_A_CHUNK, MSG_SSP_A_PROCESS, MSG_SSP_A_READ,
    MSG_SSP_B_REQ,
    MSG_SSP_C_INIT, MSG_SSP_C_CHUNK, MSG_SSP_C_PROCESS, MSG_SSP_C_READ,
    MSG_OK, MSG_ERR,
    DEFAULT_BAUDRATE, TF_ID_BYTES, TF_CKSUM_TYPE,
    RESP_SYNC_BYTES, RESP_PONG_BYTES, EMPTY_BYTES, CHAR_ENCODING_UTF8, ERRORS_IGNORE,
    ATTR_IS_OPEN, ATTR_THREAD, ATTR_HEARTBEAT_THREAD, ATTR_SER,
    ERR_DONGLE_NOT_FOUND, ERR_NO_PONG, ERR_RX_TOO_MANY_ERRORS,
    ERR_DEVICE_DISCONNECTED, ERR_FMT_WRITE_FAILED,
    LOG_FMT_PORT_OPENED, LOG_FMT_ASYNC_MCU, LOG_FMT_RX_ERROR,
    LOG_SYNCING, LOG_SYNCED, LOG_FMT_NO_PONG, LOG_FMT_TIMEOUT_CLEANUP,
    LOG_FMT_FLUSH_ERROR, LOG_FMT_CLOSE_ERROR
)


class SerialTransport:
    def __init__(self, port=None, baudrate=DEFAULT_BAUDRATE):
        self.port = None
        self.ser = None
        self.running = False
        self.thread = None
        self.heartbeat_thread = None

        if port is None:
            from keycomm.api.device_discovery import find_dongle_port
            port = find_dongle_port()
            if port is None:
                raise serial.SerialException(ERR_DONGLE_NOT_FOUND)

        self.port = port
        try:
            for attempt in range(20):
                try:
                    self.ser = serial.Serial(port, baudrate, timeout=0.01)
                    break
                except Exception as e:
                    if attempt == 19:
                        raise
                    time.sleep(0.15)
            print(LOG_FMT_PORT_OPENED.format(port=port))

            self.tf = TinyFrame()
            self.tf.ID_BYTES = TF_ID_BYTES
            self.tf.CKSUM_TYPE = TF_CKSUM_TYPE
            self.tf.write = self._tf_write

            def _log_listener(tf, msg):
                if msg.data:
                    log_str = msg.data.decode(CHAR_ENCODING_UTF8, errors=ERRORS_IGNORE)
                    print(LOG_FMT_ASYNC_MCU.format(log_str=log_str))
                return True

            self.tf.add_type_listener(MSG_LOG, _log_listener)

            self.tx_lock = threading.Lock()
            self.running = True
            self._pause_heartbeat = True
            self.last_tx_time = 0.0  # Force dummy byte on first TX to wake up MCU

            self.thread = threading.Thread(target=self._rx_thread, daemon=True)
            self.thread.start()

            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()

            self.sync()
        except Exception:
            self.close()
            raise

    @property
    def is_connected(self) -> bool:
        """Returns True if transport is running and serial port is open."""
        return self.running and self.ser is not None and getattr(self.ser, ATTR_IS_OPEN, False)

    def _tf_write(self, buf):
        if not self.running or not getattr(self.ser, ATTR_IS_OPEN, False):
            raise serial.SerialException(ERR_DEVICE_DISCONNECTED)
        with self.tx_lock:
            try:
                self.ser.write(buf)
                self.ser.flush()
                self.last_tx_time = time.time()
            except (serial.SerialException, OSError, PermissionError) as e:
                self.running = False
                try:
                    if self.ser and getattr(self.ser, ATTR_IS_OPEN, False):
                        self.ser.close()
                except Exception:
                    pass
                raise serial.SerialException(ERR_FMT_WRITE_FAILED.format(e=e)) from e

    def _heartbeat_loop(self):
        while self.running:
            time.sleep(3.0)
            if not self.running:
                break
            if not self._pause_heartbeat:
                try:
                    self.tf.send(MSG_PING, EMPTY_BYTES)
                except Exception:
                    self.running = False
                    try:
                        if self.ser and getattr(self.ser, ATTR_IS_OPEN, False):
                            self.ser.close()
                    except Exception:
                        pass
                    break

    def resume_heartbeat(self) -> None:
        """Resumes automated background heartbeat transmission (every 3.0s)."""
        self._pause_heartbeat = False

    def pause_heartbeat(self) -> None:
        """Pauses background heartbeat transmission to allow MCU deep sleep."""
        self._pause_heartbeat = True

    @property
    def is_heartbeat_active(self) -> bool:
        """Returns True if the background heartbeat transmission is active."""
        return not self._pause_heartbeat

    def _rx_thread(self):
        error_count = 0
        while self.running:
            try:
                to_read = max(1, self.ser.in_waiting)
                data = self.ser.read(to_read)
                if data:
                    self.tf.accept(data)
                error_count = 0  # reset on success
            except Exception as e:
                print(LOG_FMT_RX_ERROR.format(e=e))
                error_count += 1
                if error_count > 5:
                    print(ERR_RX_TOO_MANY_ERRORS)
                    self.running = False
                    try:
                        if self.ser and getattr(self.ser, ATTR_IS_OPEN, False):
                            self.ser.close()
                    except Exception:
                        pass
                    break
                time.sleep(0.1)

    def sync(self):
        if not self.is_connected:
            raise serial.SerialException(ERR_DEVICE_DISCONNECTED)
        print(LOG_SYNCING)
        self.ser.reset_input_buffer()

        for attempt in range(3):
            event = threading.Event()
            result = [None]

            def ping_listener(tf, resp_msg):
                result[0] = resp_msg
                event.set()
                return True

            frame_id = self.tf.query(MSG_PING, ping_listener, RESP_SYNC_BYTES)

            try:
                if event.wait(2.0):
                    if result[0] and result[0].type == MSG_OK and result[0].data == RESP_PONG_BYTES:
                        print(LOG_SYNCED)
                        return
            finally:
                if result[0] is None:
                    self.tf.remove_id_listener(frame_id)

            print(LOG_FMT_NO_PONG.format(attempt=attempt + 1))

        raise TimeoutError(ERR_NO_PONG)

    def query(self, cmd_id: int, payload: bytes = EMPTY_BYTES, timeout: float = 5.0):
        if not self.is_connected:
            raise serial.SerialException(ERR_DEVICE_DISCONNECTED)
        event = threading.Event()
        result = [None]

        def listener(tf, resp_msg):
            result[0] = resp_msg
            event.set()
            return True  # remove listener

        frame_id = self.tf.query(cmd_id, listener, payload)

        try:
            event.wait(timeout)
        finally:
            if result[0] is None:
                popped = self.tf.remove_id_listener(frame_id)
                print(LOG_FMT_TIMEOUT_CLEANUP.format(frame_id=frame_id, popped=(popped is not None)))

                try:
                    self.ser.reset_input_buffer()
                    time.sleep(0.05)
                    self.ser.reset_input_buffer()
                except Exception as e:
                    print(LOG_FMT_FLUSH_ERROR.format(e=e))

        return result[0]

    def close(self):
        self.running = False
        if getattr(self, ATTR_THREAD, None) is not None and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if getattr(self, ATTR_HEARTBEAT_THREAD, None) is not None and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1.0)
        if hasattr(self, ATTR_SER) and self.ser is not None:
            try:
                if getattr(self.ser, ATTR_IS_OPEN, False):
                    self.ser.close()
            except Exception as e:
                print(LOG_FMT_CLOSE_ERROR.format(e=e))


