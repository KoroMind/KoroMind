"""Claude SDK wrapper - re-exports from providers.llm.claude.

This module exists for backward compatibility. Import from koro.providers.llm
for new code.
"""

# Re-export subprocess and config constants for tests that monkeypatch them
import subprocess  # noqa: F401

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient  # noqa: F401

from koro.core.config import CLAUDE_WORKING_DIR, SANDBOX_DIR  # noqa: F401
from koro.providers.llm.claude import (
    ClaudeClient,
    _claude_client,
    format_tool_call,
    get_claude_client,
    get_tool_detail,
    load_megg_context,
    set_claude_client,
)

__all__ = [
    "CLAUDE_WORKING_DIR",
    "ClaudeAgentOptions",
    "ClaudeClient",
    "ClaudeSDKClient",
    "SANDBOX_DIR",
    "_claude_client",
    "format_tool_call",
    "get_claude_client",
    "get_tool_detail",
    "load_megg_context",
    "set_claude_client",
    "subprocess",
]
