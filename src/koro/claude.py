"""Claude SDK wrapper for agent interactions.

This module re-exports from koro.core.claude for backward compatibility.
New code should import directly from koro.core.claude.
"""

# Re-export everything from core claude
from koro.core.claude import (
    ClaudeClient,
    format_tool_call,
    get_claude_client,
    get_tool_detail,
    load_megg_context,
    set_claude_client,
)

__all__ = [
    "ClaudeClient",
    "format_tool_call",
    "get_claude_client",
    "get_tool_detail",
    "load_megg_context",
    "set_claude_client",
]
