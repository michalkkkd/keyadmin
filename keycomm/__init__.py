"""
keycomm - Secure communication library for KeyFirmware hardware dongle.
Contains all client and non-admin functionalities.
"""

from keycomm.core.transport import SerialTransport
from keycomm.core.protocol import RpcProtocol
from keycomm.core.secure_channel import SecureChannel
from keycomm.api.compass_api import CompassApi
from keycomm.api.factory import init_device, init_comm_device, find_dongle_port

__all__ = [
    "SerialTransport",
    "RpcProtocol",
    "SecureChannel",
    "CompassApi",
    "init_device",
    "init_comm_device",
    "find_dongle_port",
]
