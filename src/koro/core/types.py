"""Shared types and data structures for KoroMind."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


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


# Default tools for Claude Code SDK
DEFAULT_ALLOWED_TOOLS = [
    "Read",
    "Grep",
    "Glob",
    "WebSearch",
    "WebFetch",
    "Task",
    "Bash",
    "Edit",
    "Write",
    "Skill",
]


@dataclass
class SDKConfig:
    """Configuration for Claude Code SDK.

    This holds all the settings that get passed to ClaudeAgentOptions.
    Stored in Vault (SQLite) per user.
    """

    # MCP Servers - list of server configs
    # Format: [{"name": "server1", "type": "stdio", "command": "...", "args": [...]}]
    mcp_servers: list[dict[str, Any]] = field(default_factory=list)

    # Custom agents - dict of agent definitions
    # Format: {"agent_name": {"description": "...", "prompt": "...", "tools": [...]}}
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Permission mode: "default", "acceptEdits", "plan", "bypassPermissions"
    permission_mode: str = "default"

    # Tool permissions
    allowed_tools: list[str] = field(default_factory=lambda: DEFAULT_ALLOWED_TOOLS.copy())
    disallowed_tools: list[str] = field(default_factory=list)

    # Sandbox settings (optional)
    sandbox_settings: dict[str, Any] | None = None

    # Model preferences
    model: str | None = None
    fallback_model: str | None = None

    # Working directories
    working_dir: str | None = None
    sandbox_dir: str | None = None
    add_dirs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mcp_servers": self.mcp_servers,
            "agents": self.agents,
            "permission_mode": self.permission_mode,
            "allowed_tools": self.allowed_tools,
            "disallowed_tools": self.disallowed_tools,
            "sandbox_settings": self.sandbox_settings,
            "model": self.model,
            "fallback_model": self.fallback_model,
            "working_dir": self.working_dir,
            "sandbox_dir": self.sandbox_dir,
            "add_dirs": self.add_dirs,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SDKConfig":
        """Create from dictionary."""
        return cls(
            mcp_servers=data.get("mcp_servers", []),
            agents=data.get("agents", {}),
            permission_mode=data.get("permission_mode", "default"),
            allowed_tools=data.get("allowed_tools", DEFAULT_ALLOWED_TOOLS.copy()),
            disallowed_tools=data.get("disallowed_tools", []),
            sandbox_settings=data.get("sandbox_settings"),
            model=data.get("model"),
            fallback_model=data.get("fallback_model"),
            working_dir=data.get("working_dir"),
            sandbox_dir=data.get("sandbox_dir"),
            add_dirs=data.get("add_dirs", []),
        )
