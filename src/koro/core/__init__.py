"""KoroMind core library - the brain engine."""

from typing import TYPE_CHECKING

from koro.core.types import (
    BrainResponse,
    MessageType,
    Mode,
    Session,
    ToolCall,
    UserSettings,
)

if TYPE_CHECKING:
    from koro.core.brain import Brain
    from koro.core.factory import build_brain
    from koro.core.policy import PolicyConfig, PolicyEngine
    from koro.core.sessions import SessionManager

__all__ = [
    # Core classes
    "Brain",
    "build_brain",
    # Types
    "BrainResponse",
    "MessageType",
    "Mode",
    "Session",
    "ToolCall",
    "UserSettings",
    # Policy
    "PolicyConfig",
    "PolicyEngine",
    # Sessions
    "SessionManager",
]


def __getattr__(name: str):
    if name == "Brain":
        from koro.core.brain import Brain

        return Brain
    if name == "build_brain":
        from koro.core.factory import build_brain

        return build_brain
    if name == "PolicyConfig":
        from koro.core.policy import PolicyConfig

        return PolicyConfig
    if name == "PolicyEngine":
        from koro.core.policy import PolicyEngine

        return PolicyEngine
    if name == "SessionManager":
        from koro.core.sessions import SessionManager

        return SessionManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
