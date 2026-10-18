"""
keyadmin - Administrative suite for KeyFirmware hardware dongle.
Internal and factory provisioning utilities, diagnostic tools, and Admin API.
"""

from keyadmin.api.admin_api import AdminApi
from keyadmin.admin_factory import init_admin_device

__all__ = [
    "AdminApi",
    "init_admin_device",
]
