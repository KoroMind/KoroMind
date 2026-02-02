"""Voice processing with ElevenLabs TTS and STT."""

import asyncio
from io import BytesIO

from elevenlabs.client import ElevenLabs
from elevenlabs.core import ApiError

from koro.core.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, VOICE_SETTINGS


class VoiceError(RuntimeError):
    """Base error for voice processing failures."""


class VoiceNotConfiguredError(VoiceError):
    """Raised when ElevenLabs is not configured."""


class VoiceTranscriptionError(VoiceError):
    """Raised when transcription fails."""


class VoiceEngine:
    """Handles text-to-speech and speech-to-text conversion."""

    def __init__(self, api_key: str | None, voice_id: str | None = None):
        """
        Initialize voice engine.

        Args:
            api_key: ElevenLabs API key (required)
            voice_id: Voice ID to use (defaults to env)
        """
        self.api_key = api_key
        self.voice_id = voice_id or ELEVENLABS_VOICE_ID
        self.client = ElevenLabs(api_key=self.api_key) if self.api_key else None

    def update_api_key(self, api_key: str) -> None:
        """Update API key and reinitialize client."""
        self.api_key = api_key
        self.client = ElevenLabs(api_key=api_key)

    async def transcribe(self, voice_bytes: bytes) -> str:
        """
        Transcribe voice using ElevenLabs Scribe.

        Args:
            voice_bytes: Audio data as bytes

        Returns:
            Transcribed text or error message
        """
        if not self.client:
            raise VoiceNotConfiguredError("ElevenLabs not configured")

        def _transcribe_sync():
            return self.client.speech_to_text.convert(
                file=BytesIO(voice_bytes),
                model_id="scribe_v1",
                language_code="en",
            )

        try:
            transcription = await asyncio.to_thread(_transcribe_sync)
            return transcription.text
        except ApiError as exc:
            return f"Error: {exc}"
        except (RuntimeError, ValueError, TypeError) as exc:
            raise VoiceTranscriptionError(str(exc)) from exc

    async def text_to_speech(self, text: str, speed: float = None) -> BytesIO | None:
        """
        Convert text to speech using ElevenLabs Turbo v2.5.

        Args:
            text: Text to convert
            speed: Voice speed (0.7-1.2), defaults to VOICE_SETTINGS

        Returns:
            Audio buffer or None on error
        """
        if not self.client:
            return None

        actual_speed = speed if speed is not None else VOICE_SETTINGS["speed"]

        def _tts_sync():
            return self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id="eleven_turbo_v2_5",
                output_format="mp3_44100_128",
                voice_settings={
                    "stability": VOICE_SETTINGS["stability"],
                    "similarity_boost": VOICE_SETTINGS["similarity_boost"],
                    "style": VOICE_SETTINGS["style"],
                    "speed": actual_speed,
                    "use_speaker_boost": True,
                },
            )

        try:
            audio = await asyncio.to_thread(_tts_sync)

            audio_buffer = BytesIO()
            for chunk in audio:
                if isinstance(chunk, bytes):
                    audio_buffer.write(chunk)
            audio_buffer.seek(0)
            return audio_buffer
        except Exception:
            return None

    def health_check(self) -> tuple[bool, str]:
        """
        Check ElevenLabs connectivity.

        Returns:
            (success, message)
        """
        if not self.client:
            return False, "ElevenLabs not configured"

        try:
            audio = self.client.text_to_speech.convert(
                text="test",
                voice_id=self.voice_id,
                model_id="eleven_turbo_v2_5",
            )
            size = sum(len(c) for c in audio if isinstance(c, bytes))
            return True, f"OK ({size} bytes, turbo_v2_5)"
        except Exception as e:
            return False, f"FAILED - {e}"


# Default instance
_voice_engine: VoiceEngine | None = None


def get_voice_engine() -> VoiceEngine:
    """Get or create the default voice engine instance."""
    global _voice_engine
    if _voice_engine is None:
        _voice_engine = VoiceEngine(api_key=ELEVENLABS_API_KEY)
    return _voice_engine


def set_voice_engine(engine: VoiceEngine) -> None:
    """Set the default voice engine instance (for testing)."""
    global _voice_engine
    _voice_engine = engine
