"""Session and settings state management.

This module re-exports from koro.core.state for backward compatibility.
New code should import directly from koro.core.state.
"""

# Re-export everything from core state
from koro.core.state import (
    MAX_SESSIONS,
    StateManager,
    get_state_manager,
    set_state_manager,
)

__all__ = [
    "MAX_SESSIONS",
    "StateManager",
    "get_state_manager",
    "set_state_manager",
]
