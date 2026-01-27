"""Telegram message and command handlers.

This module re-exports from koro.interfaces.telegram.handlers for backward compatibility.
New code should import directly from koro.interfaces.telegram.handlers.
"""

# Re-export everything from the new location
from koro.interfaces.telegram.handlers import (
    cmd_claude_token,
    cmd_continue,
    cmd_elevenlabs_key,
    cmd_health,
    cmd_new,
    cmd_sessions,
    cmd_settings,
    cmd_setup,
    cmd_start,
    cmd_status,
    cmd_switch,
    handle_approval_callback,
    handle_settings_callback,
    handle_text,
    handle_voice,
)

__all__ = [
    "cmd_start",
    "cmd_new",
    "cmd_continue",
    "cmd_sessions",
    "cmd_switch",
    "cmd_status",
    "cmd_health",
    "cmd_settings",
    "cmd_setup",
    "cmd_claude_token",
    "cmd_elevenlabs_key",
    "handle_voice",
    "handle_text",
    "handle_settings_callback",
    "handle_approval_callback",
]
