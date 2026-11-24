"""
busybar_kit - Shared office-context kit and multi-device connection layer for BUSY Bar.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("busybar-kit")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0"
