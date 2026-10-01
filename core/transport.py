import serial
import time
import threading
from .TinyFrame import TinyFrame

# CMD IDs
MSG_LOG          = 0x00
MSG_PING         = 0x01
MSG_CHECK_LIC    = 0x02
MSG_ADMIN_DATE   = 0x03
MSG_ADMIN_LIC    = 0x04
MSG_ADMIN_WIPE   = 0x05
MSG_COMPASS_ALG1 = 0x06
MSG_DEBUG_TIME   = 0x07
MSG_ADMIN_USERS  = 0x08
MSG_COMPASS_USERS= 0x09
MSG_MEM_INFO     = 0x0A
MSG_PROVISION_IDENTITY = 0x0B
MSG_SAVE_CERTIFICATE   = 0x0C

# Responses
MSG_OK           = 0x80
MSG_ERR          = 0x81

class SerialTransport:
    def __init__(self, port='COM7', baudrate=115200):
        self.port = port
        import time
        for attempt in range(5):
            try:
                self.ser = serial.Serial(port, baudrate, timeout=0.01)
                break
            except Exception as e:
                if attempt == 4:
                    raise
                time.sleep(0.1)
        print(f'[Transport] Port opened: {port}')
        

        self.tf = TinyFrame()
        self.tf.ID_BYTES = 1
        self.tf.CKSUM_TYPE = 'crc16'
        self.tf.write = self._tf_write
        
        self.running = True
        self.thread = threading.Thread(target=self._rx_thread, daemon=True)
        self.thread.start()
        
        self.sync()

    def _tf_write(self, buf):
        # HARDWARE HACK: The EFR32 processor goes into deep sleep (EM2).
        # The first byte received over UART is only used for waking it up and
        # is often lost by the hardware. We add an empty newline byte (0x0A)
        # before every TinyFrame frame. The processor wakes up, and TinyFrame
        # safely ignores 0x0A, waiting for a valid Start Of Frame (0x01).
        self.ser.write(b'\n' + buf)
        self.ser.flush()

    def _rx_thread(self):
        import time
        error_count = 0
        while self.running:
            try:
                data = self.ser.read(1024)
                if data:
                    print(f'> RAW: {data.hex()}')
                    self.tf.accept(data)
                error_count = 0 # reset on success
            except Exception as e:
                print(f'[Transport] RX Error: {e}')
                error_count += 1
                if error_count > 5:
                    print('[Transport] Zbyt duzo bledow RX, zamykam watek.')
                    break
                time.sleep(0.1)

    def sync(self):
        print(f'[Transport] Synchronizing with microcontroller...')
        self.ser.reset_input_buffer()
        
        for attempt in range(3):
            event = threading.Event()
            result = [None]
            
            def ping_listener(tf, resp_msg):
                result[0] = resp_msg
                event.set()
                return True
                
            self.tf.query(MSG_PING, ping_listener, b"")
            
            if event.wait(2.0):
                if result[0] and result[0].type == MSG_OK and result[0].data == b"PONG":
                    print('[Transport] Synchronized with MCU (TinyFrame)!')
                    return
            print(f'[Transport] No PONG. Retransmitting PING {attempt+1}/3...')
            
        raise TimeoutError('[Transport] Brak odpowiedzi na PING (MCU spi lub nie odpowiada!)')

    def query(self, cmd_id: int, payload: bytes = b'', timeout: float = 5.0):
        event = threading.Event()
        result = [None]
        
        def listener(tf, resp_msg):
            result[0] = resp_msg
            event.set()
            return True # remove listener
            
        print(f'[Transport] query cmd_id={cmd_id:02X}, next_frame_id={self.tf.next_frame_id}')
        self.tf.query(cmd_id, listener, payload)
        import time
        t0 = time.time()
        event.wait(timeout)
        print(f'[Transport] wait took {time.time()-t0:.2f}s')
        return result[0]

    def close(self):
        self.running = False
        self.thread.join(timeout=1.0)
        self.ser.close()







