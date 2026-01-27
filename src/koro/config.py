"""Configuration management for KoroMind.

This module re-exports from koro.core.config for backward compatibility.
New code should import directly from koro.core.config.
"""

# Re-export everything from core config
from koro.core.config import (  # noqa: F401
    CLAUDE_WORKING_DIR,
    ELEVENLABS_VOICE_ID,
    PERSONA_NAME,
    SANDBOX_DIR,
    SYSTEM_PROMPT_FILE,
    get_env,
    get_env_int,
    setup_logging,
)

# Telegram-specific settings (not in core)
TELEGRAM_BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = get_env_int("TELEGRAM_DEFAULT_CHAT_ID", 0)
TOPIC_ID = get_env("TELEGRAM_TOPIC_ID")


def validate_environment() -> tuple[bool, str]:
    """
    Validate required environment variables for Telegram interface.

    Returns:
        (is_valid, message) - If not valid, message explains what's missing.
    """
    required = {
        "TELEGRAM_BOT_TOKEN": "Telegram bot token from @BotFather",
        "ELEVENLABS_API_KEY": "ElevenLabs API key from elevenlabs.io",
    }

    missing = []
    for var, description in required.items():
        if not get_env(var):
            missing.append(f"  - {var}: {description}")

    if missing:
        return False, "Missing required environment variables:\n" + "\n".join(missing)

    # Validate TELEGRAM_DEFAULT_CHAT_ID is set and valid
    chat_id = get_env("TELEGRAM_DEFAULT_CHAT_ID", "")
    if not chat_id:
        return (
            False,
            "Missing required environment variable:\n  - TELEGRAM_DEFAULT_CHAT_ID: Your Telegram chat ID (run /start to get it)",
        )

    try:
        chat_id_int = int(chat_id)
    except ValueError:
        return False, f"TELEGRAM_DEFAULT_CHAT_ID must be a number, got: {chat_id}"

    if chat_id_int == 0:
        return (
            False,
            "TELEGRAM_DEFAULT_CHAT_ID cannot be 0 (would accept messages from anyone). Set it to your chat ID.",
        )

    return True, ""
