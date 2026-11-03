from keycomm.core.constants import (
    MSG_DIAG_BEGIN, MSG_DIAG_DATA, MSG_DIAG_NEXT, RESP_OK_PREFIX, BYTEORDER_LITTLE,
    DIAG_STREAM_CHUNK, DIAG_STREAM_MAX_STEPS, DIAG_STREAM_ATTEMPTS, DIAG_FLAG_FINAL, DIAG_ERR_STREAM_FMT,
)
from keycomm.core.protocol import RpcProtocol


class DiagStream:
    """
    Hands the PC facts to the dongle and collects what it returns: the dongle encrypts them together with its own
    data (Secure world, AES-GCM). The PC only moves bytes; it has no key and cannot read the result.
    """

    def __init__(self, rpc: RpcProtocol):
        self.rpc = rpc

    def _command(self, cmd: int, payload: bytes) -> str:
        # One try only: a resent chunk would be encrypted twice, so a lost reply restarts the stream instead
        reply = self.rpc.execute_command(cmd, payload, max_retries=1)
        if not reply.startswith(RESP_OK_PREFIX):
            raise RuntimeError(DIAG_ERR_STREAM_FMT.format(reply=reply))
        return reply[len(RESP_OK_PREFIX):].strip()

    def _seal_once(self, pc_data: bytes, pc_time: int) -> bytes:
        begin = pc_time.to_bytes(4, byteorder=BYTEORDER_LITTLE) + len(pc_data).to_bytes(4, byteorder=BYTEORDER_LITTLE)
        sealed = bytes.fromhex(self._command(MSG_DIAG_BEGIN, begin))
        for i in range(0, len(pc_data), DIAG_STREAM_CHUNK):
            sealed += bytes.fromhex(self._command(MSG_DIAG_DATA, pc_data[i:i + DIAG_STREAM_CHUNK]))
        for _ in range(DIAG_STREAM_MAX_STEPS):
            reply = self._command(MSG_DIAG_NEXT, b"")
            sealed += bytes.fromhex(reply[2:])
            if reply[:2] == DIAG_FLAG_FINAL:
                return sealed
        raise RuntimeError(DIAG_ERR_STREAM_FMT.format(reply=MSG_DIAG_NEXT))

    def seal(self, pc_data: bytes, pc_time: int) -> bytes:
        """Stream header + ciphertext + GCM tag, as produced by the dongle."""
        for attempt in range(DIAG_STREAM_ATTEMPTS):
            try:
                return self._seal_once(pc_data, pc_time)
            except RuntimeError:
                if attempt == DIAG_STREAM_ATTEMPTS - 1:
                    raise
        raise RuntimeError(DIAG_ERR_STREAM_FMT.format(reply=MSG_DIAG_BEGIN))
