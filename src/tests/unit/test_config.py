"""Tests for koro.config module."""

import logging

import pytest

import koro.config as config


class TestEnvHelpers:
    """Tests for environment variable helpers."""

    def test_get_env_returns_value(self, monkeypatch):
        """get_env returns environment variable value."""
        monkeypatch.setenv("TEST_VAR", "test_value")

        assert config.get_env("TEST_VAR") == "test_value"

    def test_get_env_returns_default(self, monkeypatch):
        """get_env returns default when var not set."""
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)

        assert config.get_env("NONEXISTENT_VAR", "default") == "default"

    def test_get_env_warns_when_using_default(self, monkeypatch, caplog):
        """get_env warns when falling back to default."""
        monkeypatch.delenv("MISSING_WITH_DEFAULT", raising=False)
        caplog.set_level(logging.WARNING, logger="koro.core.config")

        value = config.get_env("MISSING_WITH_DEFAULT", "fallback")

        assert value == "fallback"
        assert "MISSING_WITH_DEFAULT" in caplog.text
        assert "falling back to default value" in caplog.text

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("42", 42),
            ("not_a_number", 99),
            (None, 123),
        ],
    )
    def test_get_env_int(self, monkeypatch, value, expected):
        """get_env_int parses or falls back to default."""
        if value is None:
            monkeypatch.delenv("INT_VAR", raising=False)
        else:
            monkeypatch.setenv("INT_VAR", value)

        assert config.get_env_int("INT_VAR", expected) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
        ],
    )
    def test_get_env_bool_parses_known_values(self, monkeypatch, value, expected):
        """get_env_bool parses known values."""
        monkeypatch.setenv("BOOL_VAR", value)

        assert config.get_env_bool("BOOL_VAR") is expected

    @pytest.mark.parametrize("default", [True, False])
    def test_get_env_bool_default(self, monkeypatch, default):
        """get_env_bool returns default for unknown values."""
        monkeypatch.setenv("BOOL_VAR", "maybe")

        assert config.get_env_bool("BOOL_VAR", default) is default

    def test_get_env_int_warns_for_invalid_value(self, monkeypatch, caplog):
        """get_env_int warns when value cannot be parsed."""
        monkeypatch.setenv("INT_VAR", "invalid")
        caplog.set_level(logging.WARNING, logger="koro.core.config")

        value = config.get_env_int("INT_VAR", 77)

        assert value == 77
        assert "INT_VAR" in caplog.text
        assert "not a valid integer" in caplog.text

    def test_get_env_bool_warns_for_invalid_value(self, monkeypatch, caplog):
        """get_env_bool warns when value cannot be parsed."""
        monkeypatch.setenv("BOOL_VAR", "invalid")
        caplog.set_level(logging.WARNING, logger="koro.core.config")

        value = config.get_env_bool("BOOL_VAR", True)

        assert value is True
        assert "BOOL_VAR" in caplog.text
        assert "not a valid boolean" in caplog.text


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

        monkeypatch.setattr(config, "get_env", mock_get_env)

        is_valid, message = config.validate_environment()
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

        monkeypatch.setattr(config, "get_env", mock_get_env)

        is_valid, message = config.validate_environment()
        assert is_valid is False
        assert "ELEVENLABS_API_KEY" in message

    def test_validate_invalid_chat_id(self, monkeypatch):
        """Validation fails with non-numeric chat ID."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key")
        monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "not_a_number")

        is_valid, message = config.validate_environment()
        assert is_valid is False
        assert "must be a number" in message

    def test_validate_fails_with_zero_chat_id(self, monkeypatch):
        """Validation fails when chat ID is 0 (security risk)."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key")
        monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "0")

        is_valid, message = config.validate_environment()
        assert is_valid is False
        assert "cannot be 0" in message

    def test_validate_fails_with_missing_chat_id(self, monkeypatch):
        """Validation fails when TELEGRAM_DEFAULT_CHAT_ID is not set."""

        # Mock get_env to simulate missing chat ID
        def mock_get_env(key, default=None):
            if key == "TELEGRAM_BOT_TOKEN":
                return "test_token"
            if key == "ELEVENLABS_API_KEY":
                return "test_key"
            if key == "TELEGRAM_DEFAULT_CHAT_ID":
                return default  # Returns None or empty string
            return default

        monkeypatch.setattr(config, "get_env", mock_get_env)

        is_valid, message = config.validate_environment()
        assert is_valid is False
        assert "TELEGRAM_DEFAULT_CHAT_ID" in message

    def test_validate_full_success(self, monkeypatch):
        """Validation succeeds with all required vars."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key")
        monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "12345")

        is_valid, message = config.validate_environment()
        assert is_valid is True
        assert message == ""


class TestVoiceSettings:
    """Tests for voice settings defaults."""

    def test_voice_settings_has_required_keys(self):
        """VOICE_SETTINGS has all required keys."""
        required = ["stability", "similarity_boost", "style", "speed"]
        for key in required:
            assert key in config.VOICE_SETTINGS

    def test_voice_settings_values_in_range(self):
        """VOICE_SETTINGS values are within valid ranges."""
        assert 0 <= config.VOICE_SETTINGS["stability"] <= 1
        assert 0 <= config.VOICE_SETTINGS["similarity_boost"] <= 1
        assert 0 <= config.VOICE_SETTINGS["style"] <= 1
        assert 0.7 <= config.VOICE_SETTINGS["speed"] <= 1.2
