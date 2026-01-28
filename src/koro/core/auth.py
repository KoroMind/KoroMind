"""Authentication logic and policies for Claude and credentials.

This module contains pure authentication logic. Persistence is handled
by storage.repos.auth_repo.
"""

import json
import logging
import os
import time
from pathlib import Path

from koro.core.config import CREDENTIALS_FILE
from koro.storage.repos.auth_repo import AuthRepo

logger = logging.getLogger(__name__)


def _get_repo(auth_repo: AuthRepo | None = None) -> AuthRepo:
    """Get auth repo, creating one with current CREDENTIALS_FILE if needed."""
    if auth_repo is not None:
        return auth_repo
    # Create new repo with current CREDENTIALS_FILE value (supports monkeypatching)
    return AuthRepo(credentials_path=CREDENTIALS_FILE)


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
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            logger.debug("Failed to read Claude OAuth credentials: %s", exc)

    return False, "none"


def is_token_expired(expires_at: int, buffer_ms: int = 300000) -> bool:
    """
    Check if a token is expired.

    Args:
        expires_at: Expiration timestamp in milliseconds
        buffer_ms: Buffer time in milliseconds (default: 5 minutes)

    Returns:
        True if token is expired or will expire within buffer time
    """
    current_time_ms = time.time() * 1000
    return expires_at < (current_time_ms + buffer_ms)


def validate_api_key(api_key: str) -> bool:
    """
    Validate an API key format.

    Args:
        api_key: API key to validate

    Returns:
        True if key appears to be valid format
    """
    if not api_key:
        return False
    # Anthropic API keys start with "sk-ant-"
    return api_key.startswith("sk-ant-") and len(api_key) > 20


def load_credentials(auth_repo: AuthRepo | None = None) -> dict:
    """
    Load saved credentials from file.

    Args:
        auth_repo: Optional AuthRepo instance (defaults to new repo with CREDENTIALS_FILE)

    Returns:
        Credentials dictionary
    """
    return _get_repo(auth_repo).load()


def save_credentials(creds: dict, auth_repo: AuthRepo | None = None) -> None:
    """
    Save credentials to file.

    Args:
        creds: Credentials dictionary
        auth_repo: Optional AuthRepo instance (defaults to new repo with CREDENTIALS_FILE)
    """
    _get_repo(auth_repo).save(creds)


def apply_saved_credentials(
    auth_repo: AuthRepo | None = None,
) -> tuple[str | None, str | None]:
    """
    Apply saved credentials on startup.

    Args:
        auth_repo: Optional AuthRepo instance (defaults to new repo with CREDENTIALS_FILE)

    Returns:
        (claude_token, elevenlabs_key) - The applied credentials or None
    """
    repo = _get_repo(auth_repo)
    creds = repo.load()
    claude_token = None
    elevenlabs_key = None

    if creds.get("claude_token"):
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = creds["claude_token"]
        claude_token = creds["claude_token"]

    if creds.get("elevenlabs_key"):
        elevenlabs_key = creds["elevenlabs_key"]

    return claude_token, elevenlabs_key


def save_claude_token(token: str, auth_repo: AuthRepo | None = None) -> None:
    """
    Save Claude OAuth token.

    Args:
        token: OAuth token
        auth_repo: Optional AuthRepo instance (defaults to new repo with CREDENTIALS_FILE)
    """
    _get_repo(auth_repo).set_claude_token(token)


def save_elevenlabs_key(key: str, auth_repo: AuthRepo | None = None) -> None:
    """
    Save ElevenLabs API key.

    Args:
        key: API key
        auth_repo: Optional AuthRepo instance (defaults to new repo with CREDENTIALS_FILE)
    """
    _get_repo(auth_repo).set_elevenlabs_key(key)


def get_saved_claude_token(auth_repo: AuthRepo | None = None) -> str | None:
    """
    Get saved Claude OAuth token.

    Args:
        auth_repo: Optional AuthRepo instance (defaults to new repo with CREDENTIALS_FILE)

    Returns:
        Saved token or None
    """
    return _get_repo(auth_repo).get_claude_token()


def get_saved_elevenlabs_key(auth_repo: AuthRepo | None = None) -> str | None:
    """
    Get saved ElevenLabs API key.

    Args:
        auth_repo: Optional AuthRepo instance (defaults to new repo with CREDENTIALS_FILE)

    Returns:
        Saved key or None
    """
    return _get_repo(auth_repo).get_elevenlabs_key()


def clear_saved_credentials(auth_repo: AuthRepo | None = None) -> None:
    """
    Clear all saved credentials.

    Args:
        auth_repo: Optional AuthRepo instance (defaults to new repo with CREDENTIALS_FILE)
    """
    _get_repo(auth_repo).clear()
