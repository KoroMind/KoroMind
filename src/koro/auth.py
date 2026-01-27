"""Authentication management for Claude and credentials.

This module re-exports from koro.core.auth for backward compatibility.
New code should import directly from koro.core.auth.
"""

# Re-export everything from core auth
from koro.core.auth import (
    apply_saved_credentials,
    check_claude_auth,
    load_credentials,
    save_credentials,
)

__all__ = [
    "apply_saved_credentials",
    "check_claude_auth",
    "load_credentials",
    "save_credentials",
]
