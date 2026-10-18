import io
import time
from typing import Optional

from keycomm.core.constants import (
    RESP_MISSING_PREFIX, RESP_OK_PREFIX, RESP_EOF,
    EMPTY_BYTES, CHAR_ENCODING_UTF8, TOKEN_ERR, TOKEN_TIMEOUT,
    ERR_FMT_CHUNK_FAILED, ERR_FMT_MAX_CHUNKS, ERR_FMT_PROCESS_FAILED,
    ERR_FMT_RESOLVE_MISSING_FAILED, ERR_FMT_FINAL_READ_FAILED, ERR_FMT_READ_STALLED,
    LOG_FMT_MISSING_CHUNKS
)

class ChunkStreamer:
    """
    Abstracts high-speed chunked transmission logic over RPC.
    Handles the fire_and_forget execution + 5ms busy-wait flow control.
    """
    def __init__(self, rpc_client) -> None:
        self.rpc = rpc_client
        self.total_bytes_sent: int = 0

    def send_chunk(self, cmd: int, chunk_bytes: bytes, timeout_sec: float = 2.0, pace_sec: float = 0.0) -> str:
        """
        Sends a single chunk with fire_and_forget=True.
        Since ser.flush() already synchronously drains the UART transmit buffer,
        pacing is only applied between consecutive chunks in a multi-chunk stream
        to allow the MCU DMA ring buffer to settle without redundant line-idle delays.
        """
        res_chunk = self.rpc.execute_command(
            cmd, 
            chunk_bytes, 
            timeout_sec=timeout_sec, 
            fire_and_forget=True
        )
        
        if pace_sec > 0:
            time.sleep(pace_sec)
            
        if isinstance(res_chunk, str) and (TOKEN_ERR in res_chunk or TOKEN_TIMEOUT in res_chunk):
            raise Exception(ERR_FMT_CHUNK_FAILED.format(res=res_chunk))
            
        self.total_bytes_sent += len(chunk_bytes)
        return str(res_chunk)

    def stream_payload(self, cmd: int, payload_bytes: bytes, chunk_size: int = 1500, timeout_sec: float = 2.0) -> int:
        """
        Slices a full payload into chunks of chunk_size and streams them.
        Tags each chunk with a 4-byte header: [uint16_t chunk_idx, uint16_t total_chunks].
        Returns the number of payload bytes sent in this specific stream operation.
        """
        import struct
        self.last_cmd = cmd
        self.last_chunks = []

        if len(payload_bytes) == 0:
            raw_chunks = [EMPTY_BYTES]
        else:
            raw_chunks = [payload_bytes[i:i+chunk_size] for i in range(0, len(payload_bytes), chunk_size)]

        total_chunks = len(raw_chunks)
        self.total_chunks = total_chunks

        if total_chunks > 256:
            raise ValueError(
                ERR_FMT_MAX_CHUNKS.format(
                    payload_size=len(payload_bytes),
                    total_chunks=total_chunks
                )
            )

        bytes_sent_now: int = 0
        for chunk_idx, raw_chunk in enumerate(raw_chunks):
            header = struct.pack('<HH', chunk_idx, total_chunks)
            tagged_chunk = header + raw_chunk
            self.last_chunks.append(tagged_chunk)
            pace = 0.003 if chunk_idx < total_chunks - 1 else 0.0
            self.send_chunk(cmd, tagged_chunk, timeout_sec=timeout_sec, pace_sec=pace)
            bytes_sent_now += len(raw_chunk)
        return bytes_sent_now

    def retransmit_missing(self, missing_indices: list, timeout_sec: float = 2.0) -> None:
        """
        Selectively re-streams only the missing chunks requested by the MCU.
        """
        for i, idx in enumerate(missing_indices):
            if hasattr(self, 'last_chunks') and 0 <= idx < len(self.last_chunks):
                pace = 0.003 if i < len(missing_indices) - 1 else 0.0
                self.send_chunk(self.last_cmd, self.last_chunks[idx], timeout_sec=timeout_sec, pace_sec=pace)

    def execute_process(self, process_cmd: int, payload: bytes = EMPTY_BYTES, timeout_sec: float = 10.0, max_retries: int = 5) -> str:
        """
        Executes the PROCESS / verification command. If MCU reports missing chunks
        (e.g. 'MISSING: 1,3'), selectively re-streams only those chunks and retries.
        """
        for attempt in range(max_retries):
            res = self.rpc.execute_command(process_cmd, payload, timeout_sec=timeout_sec)
            if RESP_MISSING_PREFIX in res:
                missing_str = res.split(RESP_MISSING_PREFIX)[1].strip()
                missing_indices = []
                for x in missing_str.split(","):
                    x_str = x.strip()
                    if x_str.isdigit():
                        missing_indices.append(int(x_str))
                print(LOG_FMT_MISSING_CHUNKS.format(missing_indices=missing_indices, attempt=attempt + 1, max_retries=max_retries))
                self.retransmit_missing(missing_indices, timeout_sec=timeout_sec)
                time.sleep(0.015)
                continue

            if TOKEN_ERR in res or TOKEN_TIMEOUT in res:
                raise Exception(ERR_FMT_PROCESS_FAILED.format(cmd=process_cmd, res=res))
            return res

        raise Exception(ERR_FMT_RESOLVE_MISSING_FAILED.format(cmd=process_cmd, max_retries=max_retries))

    process = execute_process
    verify = execute_process
        
    def reset_counters(self) -> None:
        """
        Resets the internal total bytes sent counter.
        """
        self.total_bytes_sent = 0

    def receive_payload(self, cmd: int, expected_len: Optional[int] = None, timeout_sec: float = 2.0, max_chunk_retries: int = 3) -> str:
        """
        Receives chunks in a loop until EOF is hit (if expected_len is None) or 
        until the exact expected_len bytes are received.
        Uses io.BytesIO buffer to prevent quadratic string concatenation overhead.
        Features per-chunk retransmission to prevent frame drop crashes on serial bus jitter.
        """
        buffer = io.BytesIO()
        offset = 0
        while True:
            if expected_len is not None and offset >= expected_len:
                break
                
            offset_str = str(offset).encode(CHAR_ENCODING_UTF8)
            chunk_bytes = None
            
            for attempt in range(max_chunk_retries):
                chunk_res = self.rpc.execute_command(cmd, offset_str, timeout_sec=timeout_sec)
                
                if chunk_res.startswith(RESP_OK_PREFIX):
                    chunk_res = chunk_res[len(RESP_OK_PREFIX):]
                
                if chunk_res == RESP_EOF:
                    return buffer.getvalue().decode(CHAR_ENCODING_UTF8, errors='replace').rstrip('\x00').strip()
                    
                if TOKEN_ERR not in chunk_res and TOKEN_TIMEOUT not in chunk_res:
                    chunk_bytes = chunk_res.encode(CHAR_ENCODING_UTF8)
                    break
                    
                if attempt == max_chunk_retries - 1:
                    raise Exception(ERR_FMT_FINAL_READ_FAILED.format(offset=offset, chunk_res=chunk_res))
                time.sleep(0.015)
                
            if chunk_bytes is not None:
                if len(chunk_bytes) == 0:
                    raise Exception(ERR_FMT_READ_STALLED.format(offset=offset))
                buffer.write(chunk_bytes)
                offset += len(chunk_bytes)
            
        return buffer.getvalue().decode(CHAR_ENCODING_UTF8, errors='replace').rstrip('\x00').strip()

