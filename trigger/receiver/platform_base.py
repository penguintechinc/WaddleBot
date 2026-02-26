"""Backward-compatibility shim — import from libs/platform_receiver instead.

    from platform_receiver import PlatformReceiverBase
"""
# The canonical location is libs/platform_receiver/base.py
# This file exists so existing imports within trigger/receiver/ still work.
try:
    from platform_receiver.base import PlatformReceiverBase  # noqa: F401
except ImportError:
    # Direct relative import fallback if libs/ is not on sys.path
    import sys
    import os
    _libs = os.path.join(os.path.dirname(__file__), '..', '..', 'libs')
    if _libs not in sys.path:
        sys.path.insert(0, _libs)
    from platform_receiver.base import PlatformReceiverBase  # noqa: F401

__all__ = ["PlatformReceiverBase"]
