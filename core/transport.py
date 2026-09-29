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

# Responses
MSG_OK           = 0x80
MSG_ERR          = 0x81

class SerialTransport:
    def __init__(self, port='COM7', baudrate=115200):
        self.port = port
        self.ser = serial.Serial(port, baudrate, timeout=0.1)
        print(f'[Transport] Port otwarty: {port}')
        

        self.tf = TinyFrame()
        self.tf.ID_BYTES = 1
        self.tf.CKSUM_TYPE = 'crc16'
        self.tf.write = self._tf_write
        
        self.running = True
        self.thread = threading.Thread(target=self._rx_thread, daemon=True)
        self.thread.start()
        
        self.sync()

    def _tf_write(self, buf):
        # HACK SPRZĘTOWY: Procek EFR32 wchodzi w głębokie uśpienie (EM2).
        # Pierwszy bajt odebrany przez UART służy mu tylko do wybudzenia i
        # często jest gubiony przez sprzęt. Dodajemy pusty bajt nowej linii (0x0A)
        # przed każdą ramką TinyFrame. Procek się wybudza, a TinyFrame
        # bezpiecznie ignoruje 0x0A, czekając na prawidłowy Start Of Frame (0x01).
        self.ser.write(b'\n' + buf)
        self.ser.flush()

    def _rx_thread(self):
        while self.running:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                print(f'> RAW: {data.hex()}')
                self.tf.accept(data)
            else:
                time.sleep(0.01)

    def sync(self):
        print(f'[Transport] Synchronizacja z mikrokontrolerem...')
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
                    print('[Transport] Zsynchronizowano z MCU (TinyFrame)!')
                    return
            print(f'[Transport] Brak PONG. Retransmisja PING {attempt+1}/3...')
            
        raise TimeoutError('[Transport] Brak odpowiedzi na PING (MCU spi lub nie odpowiada!)')

    def query(self, cmd_id: int, payload: bytes = b'', timeout: float = 5.0):
        event = threading.Event()
        result = [None]
        
        def listener(tf, resp_msg):
            result[0] = resp_msg
            event.set()
            return True # remove listener
            
        self.tf.query(cmd_id, listener, payload)
        event.wait(timeout)
        return result[0]

    def close(self):
        self.running = False
        self.thread.join(timeout=1.0)
        self.ser.close()
