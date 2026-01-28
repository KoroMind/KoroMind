"""Policy module for mode rules, rate limiting, and access control.

This module centralizes policy decisions that were previously scattered
across brain.py and rate_limit.py.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from koro.core.config import RATE_LIMIT_PER_MINUTE, RATE_LIMIT_SECONDS
from koro.core.types import Mode


class ToolPermission(Enum):
    """Permission level for tool execution."""

    ALLOW = "allow"  # Tool can execute without approval
    REQUIRE_APPROVAL = "require_approval"  # User must approve
    DENY = "deny"  # Tool is blocked


@dataclass
class PolicyConfig:
    """Configuration for policy rules."""

    # Rate limiting
    cooldown_seconds: float = RATE_LIMIT_SECONDS
    per_minute_limit: int = RATE_LIMIT_PER_MINUTE

    # Tool execution
    default_mode: Mode = Mode.GO_ALL
    dangerous_tools: set[str] | None = None

    def __post_init__(self):
        if self.dangerous_tools is None:
            # Tools that should always require approval in APPROVE mode
            self.dangerous_tools = {
                "Bash",
                "Write",
                "Edit",
                "NotebookEdit",
            }


class PolicyEngine:
    """Evaluates policies for tool execution and rate limiting."""

    def __init__(self, config: PolicyConfig | None = None):
        """
        Initialize policy engine.

        Args:
            config: Policy configuration (defaults to PolicyConfig())
        """
        self.config = config or PolicyConfig()

    def should_approve_tool(
        self,
        tool_name: str,
        tool_input: dict,
        mode: Mode,
    ) -> ToolPermission:
        """
        Determine if a tool call should be approved.

        Args:
            tool_name: Name of the tool
            tool_input: Tool input parameters
            mode: Current execution mode

        Returns:
            ToolPermission indicating how to handle the tool call
        """
        if mode == Mode.GO_ALL:
            return ToolPermission.ALLOW

        # APPROVE mode - check if tool is dangerous
        if tool_name in self.config.dangerous_tools:
            return ToolPermission.REQUIRE_APPROVAL

        # Read-only tools are safe
        if tool_name in {"Read", "Grep", "Glob", "WebSearch", "WebFetch"}:
            return ToolPermission.ALLOW

        # Default to requiring approval for unknown tools
        return ToolPermission.REQUIRE_APPROVAL

    def get_allowed_tools(self, mode: Mode) -> list[str]:
        """
        Get list of allowed tools for a mode.

        Args:
            mode: Execution mode

        Returns:
            List of tool names
        """
        # Base tools always allowed
        base_tools = [
            "Read",
            "Grep",
            "Glob",
            "WebSearch",
            "WebFetch",
            "Task",
        ]

        if mode == Mode.GO_ALL:
            # All tools allowed in go_all mode
            return base_tools + ["Bash", "Edit", "Write", "Skill"]

        # APPROVE mode - Claude SDK will use can_use_tool callback
        return base_tools + ["Bash", "Edit", "Write", "Skill"]


def create_approval_callback(
    policy_engine: PolicyEngine,
    mode: Mode,
    user_callback: Callable[[str, dict, Any], Any] | None = None,
) -> Callable[[str, dict, Any], Any] | None:
    """
    Create a can_use_tool callback for Claude SDK.

    Args:
        policy_engine: PolicyEngine instance
        mode: Current execution mode
        user_callback: Optional user-provided callback

    Returns:
        Callback function for Claude SDK or None if not needed
    """
    if mode == Mode.GO_ALL:
        return None

    def can_use_tool(tool_name: str, tool_input: dict, context: Any) -> Any:
        permission = policy_engine.should_approve_tool(tool_name, tool_input, mode)

        if permission == ToolPermission.ALLOW:
            return True

        if permission == ToolPermission.DENY:
            return False

        # REQUIRE_APPROVAL - delegate to user callback
        if user_callback:
            return user_callback(tool_name, tool_input, context)

        # Default to allowing if no callback provided
        return True

    return can_use_tool
