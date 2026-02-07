"""Configuration management for KoroMind core."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_env(key: str, default: str | None = None) -> str | None:
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


# API Keys (required for core functionality)
ANTHROPIC_API_KEY = get_env("ANTHROPIC_API_KEY")
ELEVENLABS_API_KEY = get_env("ELEVENLABS_API_KEY")

# KoroMind Data Directory (XDG-style, defaults to ~/.koromind)
KOROMIND_DATA_DIR = Path(
    get_env("KOROMIND_DATA_DIR", os.path.expanduser("~/.koromind"))
    or os.path.expanduser("~/.koromind")
)

# Ensure data directory exists
KOROMIND_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database path
DATABASE_PATH = KOROMIND_DATA_DIR / "koromind.db"

# Directories for Claude operations
CLAUDE_WORKING_DIR = get_env("CLAUDE_WORKING_DIR", os.path.expanduser("~"))
SANDBOX_DIR = get_env(
    "CLAUDE_SANDBOX_DIR", os.path.join(os.path.expanduser("~"), "claude-voice-sandbox")
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
RATE_LIMIT_SECONDS = 0.5
RATE_LIMIT_PER_MINUTE = 50

# API Server settings
KOROMIND_API_KEY = get_env("KOROMIND_API_KEY")
KOROMIND_HOST = get_env("KOROMIND_HOST", "127.0.0.1")
KOROMIND_PORT = get_env_int("KOROMIND_PORT", 8420)
KOROMIND_ALLOW_NO_AUTH = get_env_bool("KOROMIND_ALLOW_NO_AUTH", False)
KOROMIND_CORS_ORIGINS = [
    origin.strip()
    for origin in (
        get_env("KOROMIND_CORS_ORIGINS", "http://localhost:3000")
        or "http://localhost:3000"
    ).split(",")
    if origin.strip()
]

# Legacy paths (for backward compatibility during migration)
# In src layout, repo root is two levels above this file: src/koro/core/config.py
BASE_DIR = Path(__file__).resolve().parents[3]
STATE_FILE = BASE_DIR / "sessions_state.json"
SETTINGS_FILE = BASE_DIR / "user_settings.json"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"


def setup_logging() -> logging.Logger:
    """Configure and return logger."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    )
    return logging.getLogger(__name__)


def validate_core_environment() -> tuple[bool, str]:
    """
    Validate required environment variables for core functionality.

    Returns:
        (is_valid, message) - If not valid, message explains what's missing.
    """
    # ANTHROPIC_API_KEY is required for Claude operations
    if not ANTHROPIC_API_KEY:
        return (
            False,
            "Missing ANTHROPIC_API_KEY - required for Claude operations",
        )

    return True, ""


def validate_voice_environment() -> tuple[bool, str]:
    """
    Validate environment variables for voice functionality.

    Returns:
        (is_valid, message) - If not valid, message explains what's missing.
    """
    if not ELEVENLABS_API_KEY:
        return (
            False,
            "Missing ELEVENLABS_API_KEY - required for voice functionality",
        )

    return True, ""
