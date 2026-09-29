import serial
import time

class SerialTransport:
    """Warstwa fizyczna komunikacji (UART)"""
    def __init__(self, port='COM7', baudrate=115200):
        self.port = port
        self.ser = serial.Serial(port, baudrate, timeout=1.0)
        print(f'[Transport] Port otwarty: {port}')
        print(f'[Transport] Czekam 2s na inicjalizacje SAMD11...')
        time.sleep(2)
        print(f'[Transport] Gotowy. Bajty w buforze RX: {self.ser.in_waiting}')
        if self.ser.in_waiting:
            stale = self.ser.read(self.ser.in_waiting)
            print(f'[Transport] Wyczyścilem stare dane: {stale!r}')
        print(f'[Transport] Zestawiono fizyczne polaczenie na {port}')

    def write_line(self, text: str):
        encoded = f"{text}\n".encode('utf-8')
        print(f'[Transport] TX >>> {text!r}')
        self.ser.write(encoded)
        self.ser.flush()

    def read_line(self) -> str:
        raw = self.ser.readline()
        if raw:
            print(f'[Transport] RX <<< {raw!r}')
        return raw.decode('utf-8', errors='ignore').strip()

    def close(self):
        self.ser.close()
