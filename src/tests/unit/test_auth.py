"""Tests for koro.auth module."""

import json
import os
import time
from pathlib import Path
from unittest.mock import patch


class TestCheckClaudeAuth:
    """Tests for Claude authentication checking."""

    def test_auth_with_api_key(self, monkeypatch):
        """Auth succeeds with ANTHROPIC_API_KEY."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        from koro.auth import check_claude_auth

        is_auth, method = check_claude_auth()

        assert is_auth is True
        assert method == "api_key"

    def test_auth_with_saved_token(self, monkeypatch):
        """Auth succeeds with saved OAuth token."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "saved_token_123")

        from koro.auth import check_claude_auth

        is_auth, method = check_claude_auth()

        assert is_auth is True
        assert method == "saved_token"

    def test_auth_with_oauth_file(self, monkeypatch, tmp_path):
        """Auth succeeds with valid OAuth credentials file."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        # Create mock credentials file
        creds_dir = tmp_path / ".claude"
        creds_dir.mkdir()
        creds_file = creds_dir / ".credentials.json"

        # Token expires in 1 hour
        expires_at = (time.time() + 3600) * 1000
        creds_file.write_text(
            json.dumps(
                {
                    "claudeAiOauth": {
                        "accessToken": "access_token_123",
                        "refreshToken": "refresh_token_456",
                        "expiresAt": expires_at,
                    }
                }
            )
        )

        with patch.object(Path, "home", return_value=tmp_path):
            from koro.auth import check_claude_auth

            is_auth, method = check_claude_auth()

        assert is_auth is True
        assert method == "oauth"

    def test_auth_with_expired_but_refreshable_token(self, monkeypatch, tmp_path):
        """Auth succeeds with expired token that has refresh token."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        creds_dir = tmp_path / ".claude"
        creds_dir.mkdir()
        creds_file = creds_dir / ".credentials.json"

        # Token expired 1 hour ago
        expires_at = (time.time() - 3600) * 1000
        creds_file.write_text(
            json.dumps(
                {
                    "claudeAiOauth": {
                        "accessToken": "access_token_123",
                        "refreshToken": "refresh_token_456",
                        "expiresAt": expires_at,
                    }
                }
            )
        )

        with patch.object(Path, "home", return_value=tmp_path):
            from koro.auth import check_claude_auth

            is_auth, method = check_claude_auth()

        assert is_auth is True
        assert method == "oauth"

    def test_auth_fails_with_nothing(self, monkeypatch, tmp_path):
        """Auth fails when nothing is configured."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        with patch.object(Path, "home", return_value=tmp_path):
            from koro.auth import check_claude_auth

            is_auth, method = check_claude_auth()

        assert is_auth is False
        assert method == "none"


class TestCredentials:
    """Tests for credentials loading and saving."""

    def test_load_credentials_empty_when_missing(self, tmp_path, monkeypatch):
        """load_credentials returns empty dict when file missing."""
        import koro.core.auth

        monkeypatch.setattr(
            koro.core.auth, "CREDENTIALS_FILE", tmp_path / "missing.json"
        )

        from koro.auth import load_credentials

        assert load_credentials() == {}

    def test_load_credentials_from_file(self, tmp_path, monkeypatch):
        """load_credentials reads existing file."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(
            json.dumps({"claude_token": "token123", "elevenlabs_key": "key456"})
        )

        import koro.core.auth

        monkeypatch.setattr(koro.core.auth, "CREDENTIALS_FILE", creds_file)

        from koro.auth import load_credentials

        creds = load_credentials()

        assert creds["claude_token"] == "token123"
        assert creds["elevenlabs_key"] == "key456"

    def test_load_credentials_handles_invalid_json(self, tmp_path, monkeypatch):
        """load_credentials returns empty dict on invalid JSON."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text("not valid json {{{")

        import koro.core.auth

        monkeypatch.setattr(koro.core.auth, "CREDENTIALS_FILE", creds_file)

        from koro.auth import load_credentials

        assert load_credentials() == {}

    def test_save_credentials_creates_file(self, tmp_path, monkeypatch):
        """save_credentials creates file with correct permissions."""
        creds_file = tmp_path / "credentials.json"

        import koro.core.auth

        monkeypatch.setattr(koro.core.auth, "CREDENTIALS_FILE", creds_file)

        from koro.auth import save_credentials

        save_credentials({"test": "value"})

        assert creds_file.exists()
        assert json.loads(creds_file.read_text()) == {"test": "value"}
        # Check file permissions (0o600 = owner read/write only)
        assert oct(creds_file.stat().st_mode)[-3:] == "600"

    def test_apply_saved_credentials(self, tmp_path, monkeypatch):
        """apply_saved_credentials sets environment variables."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(
            json.dumps(
                {"claude_token": "applied_token", "elevenlabs_key": "applied_key"}
            )
        )

        import koro.core.auth

        monkeypatch.setattr(koro.core.auth, "CREDENTIALS_FILE", creds_file)

        from koro.auth import apply_saved_credentials

        claude_token, elevenlabs_key = apply_saved_credentials()

        assert claude_token == "applied_token"
        assert elevenlabs_key == "applied_key"
        assert os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") == "applied_token"


class TestCredentialPermissions:
    """Tests for secure credential file permissions."""

    def test_save_credentials_atomic_permissions(self, tmp_path, monkeypatch):
        """Credentials file should never be world-readable, even briefly."""

        creds_file = tmp_path / "credentials.json"

        import koro.core.auth

        monkeypatch.setattr(koro.core.auth, "CREDENTIALS_FILE", creds_file)

        from koro.auth import save_credentials

        save_credentials({"token": "secret"})

        # Check file permissions
        mode = os.stat(creds_file).st_mode
        # Should be owner read/write only (0o600)
        assert mode & 0o077 == 0, f"File has insecure permissions: {oct(mode)}"

    def test_save_credentials_file_created_with_correct_permissions(
        self, tmp_path, monkeypatch
    ):
        """New credentials file should be created with restricted permissions."""

        creds_file = tmp_path / "new_creds.json"

        import koro.core.auth

        monkeypatch.setattr(koro.core.auth, "CREDENTIALS_FILE", creds_file)

        from koro.auth import save_credentials

        # File shouldn't exist yet
        assert not creds_file.exists()

        save_credentials({"token": "secret"})

        # File should exist now with secure permissions
        assert creds_file.exists()
        mode = os.stat(creds_file).st_mode & 0o777
        # File should be created with restricted permissions from the start
        assert mode == 0o600, f"File has insecure permissions: {oct(mode)}"
