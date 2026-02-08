"""Voice processing with ElevenLabs TTS and STT.

This module re-exports from koro.core.voice for backward compatibility.
New code should import directly from koro.core.voice.
"""

# Re-export config constants that tests monkeypatch on koro.voice
from koro.core.config import ELEVENLABS_API_KEY  # noqa: F401

# Re-export everything from core voice
from koro.core.voice import (
    VoiceEngine,
    VoiceError,
    VoiceNotConfiguredError,
    VoiceTranscriptionError,
    get_voice_engine,
    set_voice_engine,
)

__all__ = [
    "ELEVENLABS_API_KEY",
    "VoiceError",
    "VoiceEngine",
    "VoiceNotConfiguredError",
    "VoiceTranscriptionError",
    "get_voice_engine",
    "set_voice_engine",
]
