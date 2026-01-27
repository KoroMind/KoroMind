"""Voice processing with ElevenLabs TTS and STT.

This module re-exports from koro.core.voice for backward compatibility.
New code should import directly from koro.core.voice.
"""

# Re-export everything from core voice
from koro.core.voice import (
    VoiceEngine,
    get_voice_engine,
    set_voice_engine,
)

__all__ = [
    "VoiceEngine",
    "get_voice_engine",
    "set_voice_engine",
]
