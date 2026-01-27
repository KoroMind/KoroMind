"""Voice and text message handlers.

This module re-exports from koro.interfaces.telegram.handlers.messages for backward compatibility.
New code should import directly from koro.interfaces.telegram.handlers.messages.
"""

# Re-export everything from the new location
from koro.interfaces.telegram.handlers.messages import (
    MAX_PENDING_APPROVALS,
    add_pending_approval,
    cleanup_stale_approvals,
    handle_text,
    handle_voice,
    pending_approvals,
)

__all__ = [
    "handle_voice",
    "handle_text",
    "pending_approvals",
    "add_pending_approval",
    "cleanup_stale_approvals",
    "MAX_PENDING_APPROVALS",
]
