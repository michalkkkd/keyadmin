"""Dongle diagnostics: the PC sends its facts to the dongle, which encrypts them with its own data for KeySec support."""
from keycomm.diag.diag_tool import run_diagnostics

__all__ = ["run_diagnostics"]
