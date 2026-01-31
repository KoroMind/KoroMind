"""Shared types and data structures for KoroMind."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, TypedDict

from claude_agent_sdk import SdkMcpTool
from claude_agent_sdk.types import (
    AgentDefinition,
    HookCallback,
    HookContext,
    HookEvent,
    HookMatcher,
    McpServerConfig,
    PermissionResult,
    PermissionResultAllow,
    PermissionResultDeny,
    SandboxSettings,
    SdkPluginConfig,
    StreamEvent,
    ThinkingBlock,
    ToolPermissionContext,
)


class OutputFormat(TypedDict):
    """Output format configuration."""

    type: Literal["json_schema"]
    schema: dict[str, Any]


# Type alias for tool permission callback (SDK-compatible)
# Signature: (tool_name, tool_input, context) -> PermissionResult
CanUseTool = Callable[
    [str, dict[str, Any], ToolPermissionContext],
    Awaitable[PermissionResult],
]

# Type alias for tool call notification callback
# Signature: (tool_name, detail) -> None
OnToolCall = Callable[[str, str | None], None]

# Re-export SDK types for convenience
__all__ = [
    "AgentDefinition",
    "BrainResponse",
    "CanUseTool",
    "HookCallback",
    "HookContext",
    "HookEvent",
    "HookMatcher",
    "McpServerConfig",
    "MessageType",
    "Mode",
    "OnToolCall",
    "OutputFormat",
    "PermissionResult",
    "PermissionResultAllow",
    "PermissionResultDeny",
    "ProjectConfig",
    "SandboxSettings",
    "SdkMcpTool",
    "SdkPluginConfig",
    "Session",
    "StreamEvent",
    "ThinkingBlock",
    "ToolCall",
    "ToolPermissionContext",
    "UserSettings",
]


class MessageType(Enum):
    """Type of message content."""

    TEXT = "text"
    VOICE = "voice"


class Mode(Enum):
    """Execution mode for tool calls."""

    GO_ALL = "go_all"
    APPROVE = "approve"


@dataclass(frozen=True)
class ToolCall:
    """Record of a tool call during processing."""

    name: str
    detail: str | None = None


@dataclass(frozen=True)
class BrainResponse:
    """Response from the brain engine."""

    text: str
    session_id: str
    audio: bytes | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Session:
    """User session record."""

    id: str
    user_id: str
    created_at: datetime
    last_active: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_active=datetime.fromisoformat(data["last_active"]),
        )


@dataclass
class ProjectConfig:
    """Project-level configuration (hooks, mcp, agents, etc)."""

    hooks: dict[HookEvent, list[HookMatcher]] | None = None
    mcp_servers: dict[str, McpServerConfig] | None = None
    agents: dict[str, AgentDefinition] | None = None
    plugins: list[SdkPluginConfig] | None = None
    sandbox: SandboxSettings | None = None


@dataclass
class UserSettings:
    """User preferences and settings."""

    mode: Mode = Mode.GO_ALL
    audio_enabled: bool = True
    voice_speed: float = 1.1
    watch_enabled: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "mode": self.mode.value,
            "audio_enabled": self.audio_enabled,
            "voice_speed": self.voice_speed,
            "watch_enabled": self.watch_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserSettings":
        """Create from dictionary."""
        mode_value = data.get("mode", "go_all")
        return cls(
            mode=Mode(mode_value) if isinstance(mode_value, str) else mode_value,
            audio_enabled=data.get("audio_enabled", True),
            voice_speed=data.get("voice_speed", 1.1),
            watch_enabled=data.get("watch_enabled", False),
        )
