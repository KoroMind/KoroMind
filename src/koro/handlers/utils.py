"""Utility functions for handlers.

This module re-exports from koro.interfaces.telegram.handlers.utils for backward compatibility.
New code should import directly from koro.interfaces.telegram.handlers.utils.
"""

# Re-export everything from the new location
from koro.interfaces.telegram.handlers.utils import (
    debug,
    send_long_message,
    should_handle_message,
)

__all__ = [
    "debug",
    "send_long_message",
    "should_handle_message",
]
