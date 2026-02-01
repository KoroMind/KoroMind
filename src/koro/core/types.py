"""Shared types and data structures for KoroMind."""

from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any, Literal, Protocol

from typing_extensions import TypedDict

from pydantic import BaseModel

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


class CanUseTool(Protocol):
    """Callback signature for SDK tool permission checks."""

    def __call__(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: ToolPermissionContext,
    ) -> Awaitable[PermissionResult]:
        pass


class OnToolCall(Protocol):
    """Callback signature for tool call notifications."""

    def __call__(self, tool_name: str, detail: str | None) -> None:
        pass


class ClaudeTools(StrEnum):
    """Claude tool names for allowed tool lists."""

    READ = "Read"
    GREP = "Grep"
    GLOB = "Glob"
    WEBSEARCH = "WebSearch"
    WEBFETCH = "WebFetch"
    TASK = "Task"
    BASH = "Bash"
    EDIT = "Edit"
    WRITE = "Write"
    SKILL = "Skill"


DEFAULT_CLAUDE_TOOLS = [
    ClaudeTools.READ,
    ClaudeTools.GREP,
    ClaudeTools.GLOB,
    ClaudeTools.WEBSEARCH,
    ClaudeTools.WEBFETCH,
    ClaudeTools.TASK,
    ClaudeTools.BASH,
    ClaudeTools.EDIT,
    ClaudeTools.WRITE,
    ClaudeTools.SKILL,
]

# Re-export SDK types for convenience
__all__ = [
    "AgentDefinition",
    "BrainResponse",
    "CanUseTool",
    "ClaudeTools",
    "DEFAULT_CLAUDE_TOOLS",
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
    "QueryConfig",
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


class ProjectConfig(BaseModel, frozen=True, arbitrary_types_allowed=True):
    """Project-level configuration (hooks, mcp, agents, etc)."""

    hooks: dict[HookEvent, list[HookMatcher]] = {}
    mcp_servers: dict[str, McpServerConfig] = {}
    agents: dict[str, AgentDefinition] = {}
    plugins: list[SdkPluginConfig] = []
    sandbox: SandboxSettings | None = None


class QueryConfig(BaseModel, frozen=True, arbitrary_types_allowed=True):
    """Configuration for Claude SDK queries."""

    prompt: str
    session_id: str | None = None
    continue_last: bool = False
    include_megg: bool = True
    user_settings: UserSettings | None = None
    mode: Mode = Mode.GO_ALL
    # Protocol types can't be validated by Pydantic, use Any
    on_tool_call: Any | None = None  # OnToolCall
    can_use_tool: Any | None = None  # CanUseTool
    hooks: dict[HookEvent, list[HookMatcher]] = {}
    mcp_servers: dict[str, McpServerConfig] = {}
    agents: dict[str, AgentDefinition] = {}
    plugins: list[SdkPluginConfig] = []
    sandbox: SandboxSettings | None = None
    output_format: OutputFormat | None = None
    max_turns: int | None = None
    max_budget_usd: float | None = None
    model: str | None = None
    fallback_model: str | None = None
    include_partial_messages: bool = False
    enable_file_checkpointing: bool = False
