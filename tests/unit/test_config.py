"""Tests for koro.config module."""

import os
import pytest


class TestEnvHelpers:
    """Tests for environment variable helpers."""

    def test_get_env_returns_value(self, monkeypatch):
        """get_env returns environment variable value."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        from koro.config import get_env
        assert get_env("TEST_VAR") == "test_value"

    def test_get_env_returns_default(self, monkeypatch):
        """get_env returns default when var not set."""
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        from koro.config import get_env
        assert get_env("NONEXISTENT_VAR", "default") == "default"

    def test_get_env_int_parses_integer(self, monkeypatch):
        """get_env_int parses integer values."""
        monkeypatch.setenv("INT_VAR", "42")
        from koro.config import get_env_int
        assert get_env_int("INT_VAR", 0) == 42

    def test_get_env_int_returns_default_on_invalid(self, monkeypatch):
        """get_env_int returns default for non-integer."""
        monkeypatch.setenv("INT_VAR", "not_a_number")
        from koro.config import get_env_int
        assert get_env_int("INT_VAR", 99) == 99

    def test_get_env_int_returns_default_when_missing(self, monkeypatch):
        """get_env_int returns default when var not set."""
        monkeypatch.delenv("MISSING_INT", raising=False)
        from koro.config import get_env_int
        assert get_env_int("MISSING_INT", 123) == 123

    def test_get_env_bool_true_values(self, monkeypatch):
        """get_env_bool parses true values."""
        from koro.config import get_env_bool
        for value in ["true", "True", "TRUE", "1", "yes", "YES"]:
            monkeypatch.setenv("BOOL_VAR", value)
            assert get_env_bool("BOOL_VAR") is True

    def test_get_env_bool_false_values(self, monkeypatch):
        """get_env_bool parses false values."""
        from koro.config import get_env_bool
        for value in ["false", "False", "FALSE", "0", "no", "NO"]:
            monkeypatch.setenv("BOOL_VAR", value)
            assert get_env_bool("BOOL_VAR") is False

    def test_get_env_bool_default(self, monkeypatch):
        """get_env_bool returns default for unknown values."""
        monkeypatch.setenv("BOOL_VAR", "maybe")
        from koro.config import get_env_bool
        assert get_env_bool("BOOL_VAR", True) is True
        assert get_env_bool("BOOL_VAR", False) is False


class TestValidateEnvironment:
    """Tests for environment validation."""

    def test_validate_missing_telegram_token(self, monkeypatch):
        """Validation fails without Telegram token."""
        # Mock get_env to simulate missing token
        def mock_get_env(key, default=None):
            if key == "TELEGRAM_BOT_TOKEN":
                return None
            if key == "ELEVENLABS_API_KEY":
                return "test_key"
            if key == "TELEGRAM_DEFAULT_CHAT_ID":
                return "12345"
            return default

        import koro.config
        monkeypatch.setattr(koro.config, "get_env", mock_get_env)

        is_valid, message = koro.config.validate_environment()
        assert is_valid is False
        assert "TELEGRAM_BOT_TOKEN" in message

    def test_validate_missing_elevenlabs_key(self, monkeypatch):
        """Validation fails without ElevenLabs key."""
        # Mock get_env to simulate missing key
        def mock_get_env(key, default=None):
            if key == "TELEGRAM_BOT_TOKEN":
                return "test_token"
            if key == "ELEVENLABS_API_KEY":
                return None
            if key == "TELEGRAM_DEFAULT_CHAT_ID":
                return "12345"
            return default

        import koro.config
        monkeypatch.setattr(koro.config, "get_env", mock_get_env)

        is_valid, message = koro.config.validate_environment()
        assert is_valid is False
        assert "ELEVENLABS_API_KEY" in message

    def test_validate_invalid_chat_id(self, monkeypatch):
        """Validation fails with non-numeric chat ID."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key")
        monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "not_a_number")

        import importlib
        import koro.config
        importlib.reload(koro.config)

        is_valid, message = koro.config.validate_environment()
        assert is_valid is False
        assert "must be a number" in message

    def test_validate_success_with_warning(self, monkeypatch):
        """Validation succeeds but warns when chat ID is 0."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key")
        monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "0")

        import importlib
        import koro.config
        importlib.reload(koro.config)

        is_valid, message = koro.config.validate_environment()
        assert is_valid is True
        assert "accept all messages" in message

    def test_validate_full_success(self, monkeypatch):
        """Validation succeeds with all required vars."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key")
        monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "12345")

        import importlib
        import koro.config
        importlib.reload(koro.config)

        is_valid, message = koro.config.validate_environment()
        assert is_valid is True
        assert message == ""


class TestVoiceSettings:
    """Tests for voice settings defaults."""

    def test_voice_settings_has_required_keys(self):
        """VOICE_SETTINGS has all required keys."""
        from koro.config import VOICE_SETTINGS
        required = ["stability", "similarity_boost", "style", "speed"]
        for key in required:
            assert key in VOICE_SETTINGS

    def test_voice_settings_values_in_range(self):
        """VOICE_SETTINGS values are within valid ranges."""
        from koro.config import VOICE_SETTINGS
        assert 0 <= VOICE_SETTINGS["stability"] <= 1
        assert 0 <= VOICE_SETTINGS["similarity_boost"] <= 1
        assert 0 <= VOICE_SETTINGS["style"] <= 1
        assert 0.7 <= VOICE_SETTINGS["speed"] <= 1.2
