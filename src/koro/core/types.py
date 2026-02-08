"""Shared types and data structures for KoroMind."""

from __future__ import annotations

from collections.abc import Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any, Literal, Protocol

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
from pydantic import BaseModel, Field, field_validator
from typing_extensions import TypedDict


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

    def __call__(self, tool_name: str, detail: str | None) -> Awaitable[None]:
        pass


class OnProgress(Protocol):
    """Callback signature for progress notifications."""

    def __call__(self, message: str) -> None:
        pass


@dataclass(frozen=True)
class BrainCallbacks:
    """Callbacks for Brain operations (Decision 4 from architecture).

    Structured callbacks for interface integration. None = feature disabled.
    Legacy on_tool_call/can_use_tool params still work but prefer this.
    """

    on_tool_use: OnToolCall | None = None
    """Called when a tool is used (watch mode). Async."""

    on_tool_approval: CanUseTool | None = None
    """Called to approve tool use (approve mode). SDK-compatible signature."""

    on_progress: OnProgress | None = None
    """Called with progress updates during processing. Sync."""


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
    "BrainCallbacks",
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
    "OnProgress",
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
    "SessionStateItem",
    "StreamEvent",
    "ThinkingBlock",
    "ToolCall",
    "ToolPermissionContext",
    "QueryConfig",
    "UserSessionState",
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


class UserSettings(BaseModel, frozen=True):
    """User preferences and settings."""

    mode: Mode = Mode.GO_ALL
    audio_enabled: bool = True
    voice_speed: float = 1.1
    watch_enabled: bool = False
    model: str = ""


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

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Session":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_active=datetime.fromisoformat(data["last_active"]),
        )


class SessionStateItem(BaseModel, frozen=True):
    """Typed session summary for interface state views."""

    id: str
    name: str | None = None
    is_current: bool = False


class UserSessionState(BaseModel, frozen=True):
    """Typed session state for a user."""

    current_session_id: str | None = None
    sessions: list[SessionStateItem] = Field(default_factory=list)
    pending_session_name: str | None = None


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
    user_settings: UserSettings = Field(default_factory=UserSettings)
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

    @field_validator("max_turns")
    @classmethod
    def _validate_max_turns(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"max_turns must be int, got {type(value)}")
        return value

    @field_validator("max_budget_usd")
    @classmethod
    def _validate_max_budget_usd(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"max_budget_usd must be float, got {type(value)}")
        return float(value)

    @field_validator("include_partial_messages", "enable_file_checkpointing")
    @classmethod
    def _validate_bool_flags(cls, value: bool) -> bool:
        if not isinstance(value, bool):
            raise TypeError(f"Value must be bool, got {type(value)}")
        return value
