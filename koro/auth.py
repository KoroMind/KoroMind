"""Authentication management for Claude and credentials."""

import json
import os
import time
from pathlib import Path

from .config import CREDENTIALS_FILE


def check_claude_auth() -> tuple[bool, str]:
    """
    Check if Claude authentication is configured.

    Returns:
        (is_authenticated, auth_method) - auth_method is 'api_key', 'oauth', 'saved_token', or 'none'
    """
    # Method 1: API Key
    if os.getenv("ANTHROPIC_API_KEY"):
        return True, "api_key"

    # Method 2: Saved OAuth token (from /setup)
    if os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        return True, "saved_token"

    # Method 3: OAuth credentials file
    credentials_path = Path.home() / ".claude" / ".credentials.json"
    if credentials_path.exists():
        try:
            creds = json.loads(credentials_path.read_text())
            oauth = creds.get("claudeAiOauth", {})
            if oauth.get("accessToken"):
                # Check if not expired (with 5 min buffer)
                expires_at = oauth.get("expiresAt", 0)
                if expires_at > (time.time() * 1000 + 300000):
                    return True, "oauth"
                # Expired but has refresh token - Claude SDK will handle refresh
                if oauth.get("refreshToken"):
                    return True, "oauth"
        except (json.JSONDecodeError, KeyError):
            pass

    return False, "none"


def load_credentials() -> dict:
    """Load saved credentials from file."""
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_credentials(creds: dict) -> None:
    """Save credentials to file with secure permissions from creation."""
    # Use os.open to create file with correct permissions atomically
    fd = os.open(CREDENTIALS_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(creds, f, indent=2)
    except Exception:
        os.close(fd)
        raise


def apply_saved_credentials() -> tuple[str | None, str | None]:
    """
    Apply saved credentials on startup.

    Returns:
        (claude_token, elevenlabs_key) - The applied credentials or None
    """
    creds = load_credentials()
    claude_token = None
    elevenlabs_key = None

    if creds.get("claude_token"):
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = creds["claude_token"]
        claude_token = creds["claude_token"]

    if creds.get("elevenlabs_key"):
        elevenlabs_key = creds["elevenlabs_key"]

    return claude_token, elevenlabs_key
