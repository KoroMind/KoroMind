"""Utility functions for handlers.

This module re-exports from koro.interfaces.telegram.handlers.utils for backward compatibility.
New code should import directly from koro.interfaces.telegram.handlers.utils.
"""

# Re-export TOPIC_ID for test monkeypatching
from koro.config import TOPIC_ID  # noqa: F401

# Re-export everything from the new location
from koro.interfaces.telegram.handlers.utils import (
    send_long_message,
    should_handle_message,
)

__all__ = [
    "TOPIC_ID",
    "send_long_message",
    "should_handle_message",
]
