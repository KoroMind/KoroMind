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

__all__ = [
    "Brain",
    "BrainResponse",
    "MessageType",
    "Mode",
    "Session",
    "ToolCall",
    "UserSettings",
]


def __getattr__(name: str):
    if name == "Brain":
        from koro.core.brain import Brain

        return Brain
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
