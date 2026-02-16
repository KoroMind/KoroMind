---
id: SVC-002
type: service
status: active
severity: medium
issue: null
validated: 2026-02-16
---

# Voice Processing Service

## What
- Bidirectional voice conversion: speech-to-text and text-to-speech
- Uses ElevenLabs APIs (Scribe v1 for STT, Turbo v2.5 for TTS)
- Optional - all functionality works without voice configured

## Why
- Enable voice interaction via Telegram voice messages
- Natural conversational interface beyond text

## How
- Core: `src/koro/core/voice.py` - `VoiceEngine` class
- Config: `src/koro/core/config.py` - voice settings

### Key Methods
| Method | Input | Output |
|--------|-------|--------|
| `transcribe(audio_bytes, language_code)` | Voice audio (ogg/wav) + STT language (`auto`/code) | Text string |
| `text_to_speech(text, speed)` | Text + speed (0.7-1.2) | Audio bytes |

### Config
- `ELEVENLABS_API_KEY` - Required for voice features
- `ELEVENLABS_VOICE_ID` - Voice model (default: George)
- `VOICE_STT_LANGUAGE_DEFAULT` - Default STT language (`auto` by default)
- Voice settings: stability, similarity_boost, style, speed

### Async Design
- ElevenLabs SDK is sync; wrapped with `asyncio.to_thread()`
- Non-blocking in async context (Brain, API handlers)

### Integration
- Brain calls `VoiceEngine.transcribe()` for voice input
- Brain calls `VoiceEngine.text_to_speech()` when `include_audio=True`
- Graceful degradation: missing API key = voice features disabled

## Test
- Transcribe returns text for valid audio
- TTS returns audio bytes for valid text
- Missing API key raises clear error
- Speed parameter respected (0.7-1.2 range)

## Changelog

### 2026-02-16
- Added `language_code` support to `VoiceEngine.transcribe()` and pass-through to ElevenLabs Scribe
- Added STT language normalization/validation (`auto`, `en`, `pl`, etc.)

### 2026-01-29
- Initial spec from codebase exploration
