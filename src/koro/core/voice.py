"""Voice processing - re-exports from providers.voice.elevenlabs.

This module exists for backward compatibility. Import from koro.providers.voice
for new code.
"""

from koro.core.config import ELEVENLABS_API_KEY
from koro.providers.voice.elevenlabs import (
    VoiceEngine,
    get_voice_engine,
    set_voice_engine,
)

__all__ = [
    "ELEVENLABS_API_KEY",
    "VoiceEngine",
    "get_voice_engine",
    "set_voice_engine",
]
