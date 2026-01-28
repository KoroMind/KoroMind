"""Auth repository - credential persistence only.

This module handles reading/writing credentials to file.
Token validation and policies live in core/auth.py.
"""

import json
import logging
import os
from pathlib import Path

from koro.core.config import CREDENTIALS_FILE

logger = logging.getLogger(__name__)


class AuthRepo:
    """Repository for credential persistence."""

    def __init__(self, credentials_path: Path | str | None = None):
        """
        Initialize auth repository.

        Args:
            credentials_path: Path to credentials file (defaults to CREDENTIALS_FILE)
        """
        self.credentials_path = (
            Path(credentials_path) if credentials_path else CREDENTIALS_FILE
        )

    def load(self) -> dict:
        """Load saved credentials from file."""
        if self.credentials_path.exists():
            try:
                with open(self.credentials_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Failed to load credentials file: %s", exc)
        return {}

    def save(self, creds: dict) -> None:
        """Save credentials to file with secure permissions from creation."""
        # Ensure parent directory exists
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)

        # Use os.open to create file with correct permissions atomically
        fd = os.open(
            self.credentials_path,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(creds, f, indent=2)
        except Exception:
            os.close(fd)
            raise

    def get_claude_token(self) -> str | None:
        """Get saved Claude OAuth token."""
        creds = self.load()
        return creds.get("claude_token")

    def set_claude_token(self, token: str) -> None:
        """Save Claude OAuth token."""
        creds = self.load()
        creds["claude_token"] = token
        self.save(creds)

    def get_elevenlabs_key(self) -> str | None:
        """Get saved ElevenLabs API key."""
        creds = self.load()
        return creds.get("elevenlabs_key")

    def set_elevenlabs_key(self, key: str) -> None:
        """Save ElevenLabs API key."""
        creds = self.load()
        creds["elevenlabs_key"] = key
        self.save(creds)

    def clear(self) -> None:
        """Clear all saved credentials."""
        if self.credentials_path.exists():
            self.credentials_path.unlink()

    def exists(self) -> bool:
        """Check if credentials file exists."""
        return self.credentials_path.exists()


# Default instance for singleton pattern
_auth_repo: AuthRepo | None = None


def get_auth_repo() -> AuthRepo:
    """Get or create the default auth repository instance."""
    global _auth_repo
    if _auth_repo is None:
        _auth_repo = AuthRepo()
    return _auth_repo


def set_auth_repo(repo: AuthRepo) -> None:
    """Set the default auth repository instance (for testing)."""
    global _auth_repo
    _auth_repo = repo
