"""Telegram command handlers.

This module re-exports from koro.interfaces.telegram.handlers.commands for backward compatibility.
New code should import directly from koro.interfaces.telegram.handlers.commands.
"""

# Re-export everything from the new location
from koro.interfaces.telegram.handlers.commands import (
    cmd_claude_token,
    cmd_continue,
    cmd_elevenlabs_key,
    cmd_health,
    cmd_language,
    cmd_new,
    cmd_sessions,
    cmd_settings,
    cmd_setup,
    cmd_status,
    cmd_switch,
)

__all__ = [
    "cmd_new",
    "cmd_language",
    "cmd_continue",
    "cmd_sessions",
    "cmd_switch",
    "cmd_status",
    "cmd_health",
    "cmd_settings",
    "cmd_setup",
    "cmd_claude_token",
    "cmd_elevenlabs_key",
]
