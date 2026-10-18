import sys
import time
import abc

class BaseRunner(abc.ABC):
    collect_telemetry: bool = False
    telemetry_history: list = []
    last_kpi: dict = None

    def __init__(self, rpc_client):
        self.rpc = rpc_client
        self.total_bytes_sent = 0
        self.last_kpi = None

    def execute(self, *args, **kwargs) -> str:
        silent = kwargs.pop('silent', False)
        t_start_all = time.time()
        
        self.pre_execute(*args, **kwargs)

        t_start_send = time.time()
        self.execute_send(*args, **kwargs)
        time_send = time.time() - t_start_send

        t_start_work = time.time()
        self.execute_process(*args, **kwargs)
        time_work = time.time() - t_start_work

        t_start_recv = time.time()
        final_result = self.execute_receive(*args, **kwargs)
        time_recv = time.time() - t_start_recv

        time_total = time.time() - t_start_all
        speed_kbs = (self.total_bytes_sent / 1024) / time_send if time_send > 0 else 0
        recv_bytes = len(final_result.encode('utf-8')) if final_result else 0
        recv_speed_kbs = (recv_bytes / 1024) / time_recv if time_recv > 0 else 0

        # Capture standardized KPI telemetry
        kpi = {
            'runner': self.__class__.__name__,
            'send_bytes': self.total_bytes_sent,
            'send_kb': self.total_bytes_sent / 1024.0,
            'send_speed_kbs': speed_kbs,
            'recv_bytes': recv_bytes,
            'recv_kb': recv_bytes / 1024.0,
            'recv_speed_kbs': recv_speed_kbs,
            'time_send': time_send,
            'time_work': time_work,
            'time_recv': time_recv,
            'time_total': time_total,
        }
        self.last_kpi = kpi
        BaseRunner.last_kpi = kpi
        if BaseRunner.collect_telemetry:
            BaseRunner.telemetry_history.append(kpi)

        self.post_execute(final_result)

        if not silent:
            debug_log = (
                f"\n{'='*50}\n"
                f"[DEBUG] TRANSMISSION COMPLETE: {self.__class__.__name__}\n"
                f"[DEBUG] Send Size:          {self.total_bytes_sent/1024:.2f} KB\n"
                f"[DEBUG] Send Speed:         {speed_kbs:.2f} KB/s\n"
                f"[DEBUG] Receive Size:       {recv_bytes/1024:.2f} KB\n"
                f"[DEBUG] Receive Speed:      {recv_speed_kbs:.2f} KB/s\n"
                f"[DEBUG] Time Send:          {time_send:.2f} seconds\n"
                f"[DEBUG] Time Work:          {time_work:.2f} seconds\n"
                f"[DEBUG] Time Receive:       {time_recv:.2f} seconds\n"
                f"[DEBUG] Time:               {time_total:.2f} seconds\n"
                f"{'='*50}\n"
            )
            print(debug_log, end="", flush=True)
            if sys.__stdout__ is not None and sys.__stdout__ is not sys.stdout:
                try:
                    sys.__stdout__.write(debug_log)
                    sys.__stdout__.flush()
                except Exception:
                    pass
        
        self.validate_result(final_result)
        
        return final_result

    def pre_execute(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def execute_send(self, *args, **kwargs):
        """Must set self.total_bytes_sent if data is sent"""
        pass

    @abc.abstractmethod
    def execute_process(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def execute_receive(self, *args, **kwargs) -> str:
        pass

    def post_execute(self, final_result: str):
        pass

    def validate_result(self, final_result: str):
        pass
