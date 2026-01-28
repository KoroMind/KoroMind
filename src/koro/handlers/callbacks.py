"""Callback query handlers for inline keyboards.

This module re-exports from koro.interfaces.telegram.handlers.callbacks for backward compatibility.
New code should import directly from koro.interfaces.telegram.handlers.callbacks.
"""

# Re-export everything from the new location
from koro.interfaces.telegram.handlers.callbacks import (
    handle_approval_callback,
    handle_settings_callback,
)

__all__ = [
    "handle_settings_callback",
    "handle_approval_callback",
]
