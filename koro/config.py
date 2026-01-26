"""Configuration management for KoroMind."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_env(key: str, default: str = None) -> str | None:
    """Get environment variable with optional default."""
    return os.getenv(key, default)


def get_env_int(key: str, default: int) -> int:
    """Get environment variable as integer."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes"):
        return True
    if value in ("false", "0", "no"):
        return False
    return default


# Core settings
TELEGRAM_BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN")
ELEVENLABS_API_KEY = get_env("ELEVENLABS_API_KEY")
ALLOWED_CHAT_ID = get_env_int("TELEGRAM_DEFAULT_CHAT_ID", 0)
TOPIC_ID = get_env("TELEGRAM_TOPIC_ID")

# Directories
CLAUDE_WORKING_DIR = get_env("CLAUDE_WORKING_DIR", os.path.expanduser("~"))
SANDBOX_DIR = get_env(
    "CLAUDE_SANDBOX_DIR",
    os.path.join(os.path.expanduser("~"), "claude-voice-sandbox")
)

# Voice settings
MAX_VOICE_CHARS = get_env_int("MAX_VOICE_RESPONSE_CHARS", 500)
ELEVENLABS_VOICE_ID = get_env("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")

# Persona settings
PERSONA_NAME = get_env("PERSONA_NAME", "Assistant")
SYSTEM_PROMPT_FILE = get_env("SYSTEM_PROMPT_FILE", "")
CLAUDE_SETTINGS_FILE = get_env("CLAUDE_SETTINGS_FILE", "")

# Logging
LOG_LEVEL = get_env("LOG_LEVEL", "INFO")

# Voice settings for expressive delivery
VOICE_SETTINGS = {
    "stability": 0.3,
    "similarity_boost": 0.75,
    "style": 0.4,
    "speed": 1.1,
}

# Rate limiting
RATE_LIMIT_SECONDS = 2
RATE_LIMIT_PER_MINUTE = 10

# Paths
BASE_DIR = Path(__file__).parent.parent
STATE_FILE = BASE_DIR / "sessions_state.json"
SETTINGS_FILE = BASE_DIR / "user_settings.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"


def setup_logging() -> logging.Logger:
    """Configure and return logger."""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    )
    return logging.getLogger(__name__)


def validate_environment() -> tuple[bool, str]:
    """
    Validate required environment variables.

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
        return False, "Missing required environment variable:\n  - TELEGRAM_DEFAULT_CHAT_ID: Your Telegram chat ID (run /start to get it)"

    try:
        chat_id_int = int(chat_id)
    except ValueError:
        return False, f"TELEGRAM_DEFAULT_CHAT_ID must be a number, got: {chat_id}"

    if chat_id_int == 0:
        return False, "TELEGRAM_DEFAULT_CHAT_ID cannot be 0 (would accept messages from anyone). Set it to your chat ID."

    return True, ""
