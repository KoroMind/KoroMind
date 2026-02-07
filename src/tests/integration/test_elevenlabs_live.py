"""Live integration tests for ElevenLabs API."""

import os
from io import BytesIO

import pytest
from dotenv import load_dotenv

from koro.voice import VoiceEngine

# Load environment variables
load_dotenv()


def _has_elevenlabs_access() -> bool:
    """Return True when ElevenLabs credentials are usable for live tests."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return False
    voice = VoiceEngine(api_key=api_key)
    success, _ = voice.health_check()
    return success


# Skip all tests in this module if live access is unavailable
pytestmark = pytest.mark.skipif(
    not _has_elevenlabs_access(),
    reason="ElevenLabs live access unavailable (missing key or account/API issue)",
)


@pytest.fixture
def voice_engine():
    """Create voice engine with real API key."""
    return VoiceEngine(api_key=os.getenv("ELEVENLABS_API_KEY"))


@pytest.mark.live
class TestElevenLabsTTS:
    """Live tests for Text-to-Speech."""

    @pytest.mark.asyncio
    async def test_tts_produces_audio(self, voice_engine):
        """TTS produces valid audio bytes."""
        result = await voice_engine.text_to_speech("Hello, this is a test.")

        assert result is not None
        assert isinstance(result, BytesIO)
        assert len(result.getvalue()) > 1000  # Should be more than 1KB

    @pytest.mark.asyncio
    async def test_tts_with_different_speeds(self, voice_engine):
        """TTS works with different speed settings."""
        for speed in [0.8, 1.0, 1.2]:
            result = await voice_engine.text_to_speech("Test", speed=speed)
            assert result is not None
            assert len(result.getvalue()) > 0


@pytest.mark.live
class TestElevenLabsSTT:
    """Live tests for Speech-to-Text."""

    @pytest.mark.asyncio
    async def test_stt_transcribes_audio(self, voice_engine):
        """STT transcribes TTS output correctly."""
        # Generate audio
        test_text = "The quick brown fox"
        audio = await voice_engine.text_to_speech(test_text)
        assert audio is not None

        # Transcribe it back
        transcription = await voice_engine.transcribe(audio.getvalue())

        # Should contain key words
        assert "quick" in transcription.lower() or "fox" in transcription.lower()


@pytest.mark.live
class TestElevenLabsRoundTrip:
    """Live tests for full TTS->STT round trip."""

    @pytest.mark.asyncio
    async def test_round_trip_preserves_content(self, voice_engine):
        """Round trip preserves essential content."""
        original = "Hello world, testing one two three."

        # TTS
        audio = await voice_engine.text_to_speech(original)
        assert audio is not None

        # STT
        transcription = await voice_engine.transcribe(audio.getvalue())

        # Should preserve key words
        words_found = sum(
            1
            for word in ["hello", "world", "testing", "one", "two", "three"]
            if word in transcription.lower()
        )
        assert words_found >= 3  # At least half the words


@pytest.mark.live
class TestElevenLabsHealthCheck:
    """Live tests for health check."""

    def test_health_check_passes(self, voice_engine):
        """Health check passes with valid API key."""
        success, message = voice_engine.health_check()

        assert success is True
        assert "OK" in message
