class TF_Msg:
    """A TinyFrame message object representing a framed packet."""
    def __init__(self):
        self.data = bytearray()
        self.len = 0
        self.type = 0
        self.id = 0

    def __str__(self):
        return f"ID {self.id:X}h, type {self.type:X}h, len {self.len:d}, body: {self.data}"
