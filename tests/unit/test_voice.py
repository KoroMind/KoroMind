"""Tests for koro.voice module."""

import pytest
from io import BytesIO
from unittest.mock import MagicMock

from koro.voice import VoiceEngine


class TestVoiceEngine:
    """Tests for VoiceEngine class."""

    def test_init_with_api_key(self):
        """VoiceEngine initializes with API key."""
        engine = VoiceEngine(api_key="test_key", voice_id="test_voice")

        assert engine.api_key == "test_key"
        assert engine.voice_id == "test_voice"
        assert engine.client is not None

    def test_init_without_api_key(self, monkeypatch):
        """VoiceEngine handles missing API key."""
        monkeypatch.setattr("koro.voice.ELEVENLABS_API_KEY", None)

        engine = VoiceEngine(api_key=None)

        assert engine.client is None

    def test_update_api_key(self):
        """update_api_key reinitializes client."""
        engine = VoiceEngine(api_key="old_key")
        old_client = engine.client

        engine.update_api_key("new_key")

        assert engine.api_key == "new_key"
        assert engine.client is not old_client

    @pytest.mark.asyncio
    async def test_transcribe_without_client(self, monkeypatch):
        """transcribe returns error without client."""
        monkeypatch.setattr("koro.voice.ELEVENLABS_API_KEY", None)
        engine = VoiceEngine(api_key=None)

        result = await engine.transcribe(b"audio_data")

        assert "not configured" in result.lower()

    @pytest.mark.asyncio
    async def test_transcribe_success(self, mock_elevenlabs_client):
        """transcribe returns transcription text."""
        engine = VoiceEngine(api_key="test_key")
        engine.client = mock_elevenlabs_client

        result = await engine.transcribe(b"audio_data")

        assert result == "This is a test transcription"
        mock_elevenlabs_client.speech_to_text.convert.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_handles_error(self):
        """transcribe returns error message on exception."""
        engine = VoiceEngine(api_key="test_key")
        engine.client = MagicMock()
        engine.client.speech_to_text.convert.side_effect = Exception("API error")

        result = await engine.transcribe(b"audio_data")

        assert "Transcription error" in result
        assert "API error" in result

    @pytest.mark.asyncio
    async def test_text_to_speech_without_client(self, monkeypatch):
        """text_to_speech returns None without client."""
        monkeypatch.setattr("koro.voice.ELEVENLABS_API_KEY", None)
        engine = VoiceEngine(api_key=None)

        result = await engine.text_to_speech("Hello")

        assert result is None

    @pytest.mark.asyncio
    async def test_text_to_speech_success(self, mock_elevenlabs_client):
        """text_to_speech returns audio buffer."""
        engine = VoiceEngine(api_key="test_key")
        engine.client = mock_elevenlabs_client

        result = await engine.text_to_speech("Hello test")

        assert isinstance(result, BytesIO)
        assert len(result.getvalue()) > 0

    @pytest.mark.asyncio
    async def test_text_to_speech_with_custom_speed(self, mock_elevenlabs_client):
        """text_to_speech uses custom speed."""
        engine = VoiceEngine(api_key="test_key")
        engine.client = mock_elevenlabs_client

        await engine.text_to_speech("Hello", speed=0.8)

        call_args = mock_elevenlabs_client.text_to_speech.convert.call_args
        assert call_args.kwargs["voice_settings"]["speed"] == 0.8

    @pytest.mark.asyncio
    async def test_text_to_speech_handles_error(self):
        """text_to_speech returns None on exception."""
        engine = VoiceEngine(api_key="test_key")
        engine.client = MagicMock()
        engine.client.text_to_speech.convert.side_effect = Exception("API error")

        result = await engine.text_to_speech("Hello")

        assert result is None

    def test_health_check_without_client(self, monkeypatch):
        """health_check fails without client."""
        monkeypatch.setattr("koro.voice.ELEVENLABS_API_KEY", None)
        engine = VoiceEngine(api_key=None)

        success, message = engine.health_check()

        assert success is False
        assert "not configured" in message.lower()

    def test_health_check_success(self, mock_elevenlabs_client):
        """health_check succeeds with working client."""
        engine = VoiceEngine(api_key="test_key")
        engine.client = mock_elevenlabs_client

        success, message = engine.health_check()

        assert success is True
        assert "OK" in message

    def test_health_check_failure(self):
        """health_check reports failure on exception."""
        engine = VoiceEngine(api_key="test_key")
        engine.client = MagicMock()
        engine.client.text_to_speech.convert.side_effect = Exception("API error")

        success, message = engine.health_check()

        assert success is False
        assert "FAILED" in message


class TestVoiceEngineDefaults:
    """Tests for voice engine default instance management."""

    def test_get_voice_engine_creates_instance(self, monkeypatch):
        """get_voice_engine creates instance on first call."""
        monkeypatch.setattr("koro.voice.ELEVENLABS_API_KEY", "test_key")

        import koro.voice
        koro.voice._voice_engine = None

        engine = koro.voice.get_voice_engine()

        assert engine is not None
        assert isinstance(engine, VoiceEngine)

    def test_get_voice_engine_returns_same(self, monkeypatch):
        """get_voice_engine returns same instance."""
        monkeypatch.setattr("koro.voice.ELEVENLABS_API_KEY", "test_key")

        import koro.voice
        koro.voice._voice_engine = None

        engine1 = koro.voice.get_voice_engine()
        engine2 = koro.voice.get_voice_engine()

        assert engine1 is engine2

    def test_set_voice_engine_replaces(self, monkeypatch):
        """set_voice_engine replaces default instance."""
        import koro.voice

        custom = VoiceEngine(api_key="custom_key")
        koro.voice.set_voice_engine(custom)

        assert koro.voice.get_voice_engine() is custom
