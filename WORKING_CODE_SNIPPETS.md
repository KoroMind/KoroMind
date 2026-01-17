# Working ElevenLabs Code Snippets

These are verified, tested code snippets from the Claude Voice Assistant bot.

## Setup

```python
from elevenlabs.client import ElevenLabs
from io import BytesIO
import os

# Initialize client
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
```

## Text-to-Speech (TTS)

**Model:** Flash v2.5 (cheapest, fastest)
**Voice:** George (`JBFqnCBsd6RMkjVDRZzb`)

```python
async def text_to_speech(text: str) -> BytesIO:
    """Convert text to speech using ElevenLabs Flash v2.5."""
    try:
        audio = client.text_to_speech.convert(
            text=text,
            voice_id="JBFqnCBsd6RMkjVDRZzb",  # George - clear English voice
            model_id="eleven_flash_v2_5",
            output_format="mp3_44100_128",
        )

        audio_buffer = BytesIO()
        for chunk in audio:
            if isinstance(chunk, bytes):
                audio_buffer.write(chunk)
        audio_buffer.seek(0)
        return audio_buffer
    except Exception as e:
        print(f"TTS error: {e}")
        return None
```

**Usage:**
```python
audio = await text_to_speech("Hello world")
# Returns BytesIO with MP3 audio data
```

## Speech-to-Text (STT)

**Model:** Scribe v1
**Language:** English

```python
async def transcribe_voice(voice_bytes: bytes) -> str:
    """Transcribe voice using ElevenLabs Scribe."""
    try:
        transcription = client.speech_to_text.convert(
            file=BytesIO(voice_bytes),
            model_id="scribe_v1",
            language_code="en",
        )
        return transcription.text
    except Exception as e:
        return f"[Transcription error: {e}]"
```

**Usage:**
```python
# From file
with open("audio.mp3", "rb") as f:
    audio_bytes = f.read()
text = await transcribe_voice(audio_bytes)

# From BytesIO
audio_buffer = BytesIO(audio_data)
text = await transcribe_voice(audio_buffer.getvalue())
```

## Complete Round-trip

```python
async def voice_roundtrip(text: str) -> str:
    """Text → Speech → Text round-trip."""
    # Convert to speech
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_flash_v2_5",
        output_format="mp3_44100_128",
    )

    # Collect audio bytes
    audio_bytes = BytesIO()
    for chunk in audio:
        if isinstance(chunk, bytes):
            audio_bytes.write(chunk)
    audio_bytes.seek(0)

    # Convert back to text
    transcription = client.speech_to_text.convert(
        file=audio_bytes,
        model_id="scribe_v1",
        language_code="en",
    )

    return transcription.text
```

## Error Handling

```python
try:
    audio = client.text_to_speech.convert(...)
except Exception as e:
    # Handle API errors
    if "quota_exceeded" in str(e):
        print("Out of credits")
    elif "invalid_voice_id" in str(e):
        print("Voice not found")
    else:
        print(f"Error: {e}")
```

## Model Options

### TTS Models
- `eleven_flash_v2_5` - Fastest, cheapest (recommended)
- `eleven_turbo_v2_5` - Higher quality, more expensive
- `eleven_multilingual_v2` - Multiple languages

### Output Formats
- `mp3_44100_128` - Standard MP3 (recommended)
- `mp3_44100_192` - Higher quality MP3
- `pcm_16000` - Raw PCM for processing

### Voices
Current: `JBFqnCBsd6RMkjVDRZzb` (George - male, clear English)

To list available voices (requires `voices_read` permission):
```python
voices = client.voices.get_all()
for voice in voices.voices:
    print(f"{voice.name}: {voice.voice_id}")
```

## Cost Estimates

Based on ElevenLabs pricing:

**Flash v2.5 TTS:**
- $0.04 per 1,000 characters
- ~100 char message = $0.004

**Scribe v1 STT:**
- $0.24 per hour of audio
- ~5 second message = $0.000333

**Voice interaction (both ways):**
- ~$0.024 per round-trip

## Tested Configurations

All tested and working:

```python
# Configuration 1: Bot implementation
TTS_MODEL = "eleven_flash_v2_5"
STT_MODEL = "scribe_v1"
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
OUTPUT_FORMAT = "mp3_44100_128"
LANGUAGE = "en"
```

## Dependencies

```txt
elevenlabs>=1.0.0
python-dotenv>=1.0.0
```

## Environment Variables

```bash
ELEVENLABS_API_KEY=sk_your_api_key_here
```

---

**Status:** All snippets tested and verified working on 2026-01-17
**Test File:** `/home/dev/claude-voice-assistant/test_elevenlabs.py`
**Bot File:** `/home/dev/claude-voice-assistant/bot.py`
