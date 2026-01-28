"""Shared test fixtures and configuration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    env_vars = {
        "TELEGRAM_BOT_TOKEN": "test_token_12345",
        "ELEVENLABS_API_KEY": "test_elevenlabs_key",
        "TELEGRAM_DEFAULT_CHAT_ID": "12345",
        "CLAUDE_WORKING_DIR": "/tmp/test_working",
        "CLAUDE_SANDBOX_DIR": "/tmp/test_sandbox",
        "PERSONA_NAME": "TestBot",
        "LOG_LEVEL": "DEBUG",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def state_file(tmp_path):
    """Create a temporary state file."""
    path = tmp_path / "sessions_state.json"
    return path


@pytest.fixture
def settings_file(tmp_path):
    """Create a temporary settings file."""
    path = tmp_path / "user_settings.json"
    return path


@pytest.fixture
def credentials_file(tmp_path):
    """Create a temporary credentials file."""
    path = tmp_path / "credentials.json"
    return path


@pytest.fixture
def sample_state():
    """Sample session state data."""
    return {
        "12345": {
            "current_session": "session_abc123",
            "sessions": ["session_abc123", "session_def456"],
        }
    }


@pytest.fixture
def sample_settings():
    """Sample user settings data."""
    return {
        "12345": {
            "audio_enabled": True,
            "voice_speed": 1.1,
            "mode": "go_all",
            "watch_enabled": False,
        }
    }


@pytest.fixture
def mock_telegram_update():
    """Create a mock Telegram Update object."""
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.is_bot = False
    update.effective_chat.id = 12345
    update.effective_chat.send_message = AsyncMock()
    update.message.message_thread_id = None
    update.message.text = "Hello test"
    update.message.reply_text = AsyncMock()
    update.message.reply_voice = AsyncMock()
    update.message.delete = AsyncMock()
    update.message.voice.get_file = AsyncMock()
    return update


@pytest.fixture
def mock_telegram_context():
    """Create a mock Telegram context."""
    context = MagicMock()
    context.args = []
    return context


@pytest.fixture
def make_processing_message():
    """Factory for a processing message with edit_text."""

    def _make_processing_message():
        message = MagicMock()
        message.edit_text = AsyncMock()
        return message

    return _make_processing_message


@pytest.fixture
def make_update():
    """Factory for Telegram Update objects used in handlers tests."""

    def _make_update(
        *,
        user_id: int = 12345,
        chat_id: int = 12345,
        is_bot: bool = False,
        thread_id: int | None = None,
        text: str | None = "Hello test",
        voice: MagicMock | None = None,
    ):
        update = MagicMock()
        update.effective_user.id = user_id
        update.effective_user.is_bot = is_bot
        update.effective_chat.id = chat_id
        update.effective_chat.send_message = AsyncMock()

        update.message.message_thread_id = thread_id
        update.message.text = text
        update.message.reply_text = AsyncMock()
        update.message.reply_voice = AsyncMock()
        update.message.delete = AsyncMock()
        if voice is not None:
            update.message.voice = voice

        return update

    return _make_update


@pytest.fixture
def make_callback_query():
    """Factory for callback queries."""

    def _make_callback_query(data: str):
        query = MagicMock()
        query.data = data
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        return query

    return _make_callback_query


@pytest.fixture
def make_voice_message():
    """Factory for Telegram voice message objects."""

    def _make_voice_message(audio_bytes: bytes = b"voice_data"):
        voice_file = MagicMock()
        voice_file.download_as_bytearray = AsyncMock(
            return_value=bytearray(audio_bytes)
        )

        voice_obj = MagicMock()
        voice_obj.get_file = AsyncMock(return_value=voice_file)
        return voice_obj

    return _make_voice_message


@pytest.fixture
def mock_elevenlabs_client():
    """Create a mock ElevenLabs client."""
    client = MagicMock()

    # Mock TTS
    client.text_to_speech.convert.return_value = [b"fake_audio_data" * 100]

    # Mock STT
    transcription = MagicMock()
    transcription.text = "This is a test transcription"
    client.speech_to_text.convert.return_value = transcription

    return client


@pytest.fixture
def sample_audio_bytes():
    """Sample audio bytes for testing."""
    return b"RIFF" + b"\x00" * 100  # Fake WAV header


@pytest.fixture
def mock_claude_response():
    """Mock Claude SDK response data."""
    return {
        "result": "This is Claude's response",
        "session_id": "new_session_xyz789",
        "total_cost_usd": 0.001,
        "num_turns": 1,
        "duration_ms": 500,
    }
