import time
import re
from datetime import datetime
from .transport import SerialTransport

class RpcProtocol:
    """Warstwa logiczna (protokol Ping-Pong, odbieranie logow)"""
    def __init__(self, transport: SerialTransport):
        self.transport = transport
        self._first_command = True

    def _format_timestamps(self, text: str) -> str:
        """Zamienia surowe Unix timestampy na czytelny format Y-m-d H:M:S"""
        def replace_ts(m):
            ts = int(m.group(0))
            if 1577836800 <= ts <= 2524608000:
                return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            return m.group(0)
        text = re.sub(r'\b\d{10}\b', replace_ts, text)
        return self._format_elapsed(text)

    def _format_elapsed(self, text: str) -> str:
        """Zamienia 'Od sync minelo: X minut' na 'X h Y m' gdy > 60 minut"""
        def replace_elapsed(m):
            mins = int(m.group(1))
            if mins >= 60:
                h = mins // 60
                m_rem = mins % 60
                return f'Od sync minelo: {h} h {m_rem} m'
            return m.group(0)
        return re.sub(r'Od sync minelo: (\d+) minut', replace_elapsed, text)

    def execute_command(self, cmd: str, timeout_sec: float = 5.0) -> str:
        """
        Wysyla komende i blokuje wykonanie az do otrzymania OK: lub ERR:
        W miedzyczasie printuje sprzetowe LOG: na biezaco.
        """
        if self._first_command:
            self._first_command = False
        else:
            # Daj MCU czas na opuszczenie petli while w app_process_action
            # zanim wyslemy kolejna komende (inaczej MCU przetworzy ja podwojnie)
            time.sleep(0.5)

        print(f'[Protocol] Wysylam: {cmd!r}')
        self.transport.write_line(cmd)

        start = time.time()
        while time.time() - start < timeout_sec:
            line = self.transport.read_line()
            if not line:
                continue

            if line.startswith('LOG:'):
                print(f'   [MCU] {self._format_timestamps(line[4:].strip())}')
            elif line.startswith('OK:') or line.startswith('ERR:'):
                return line

        raise TimeoutError(f'Krytyczny blad sprzetu: Brak odpowiedzi na {cmd} przez {timeout_sec} sekund!')
