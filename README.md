# Claude Voice Assistant

Telegram voice bot powered by Claude and ElevenLabs TTS. Supports multiple personas with isolated sandboxes.

## Features

- Voice input via Telegram voice messages
- Voice output via ElevenLabs TTS
- Session persistence across messages
- Multi-persona support (different bots, different voices)
- Sandbox isolation for file writes
- MEGG integration for context

## Quick Start

1. Copy `.env.example` to your deployment location
2. Fill in required values (Telegram token, ElevenLabs key)
3. Run with: `python bot.py`

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token |
| `TELEGRAM_DEFAULT_CHAT_ID` | Yes | Allowed chat ID |
| `ELEVENLABS_API_KEY` | Yes | ElevenLabs API key |
| `PERSONA_NAME` | No | Display name for logs |
| `SYSTEM_PROMPT_FILE` | No | Path to persona prompt |
| `ELEVENLABS_VOICE_ID` | No | ElevenLabs voice ID |
| `TELEGRAM_TOPIC_ID` | No | Filter to specific topic |
| `CLAUDE_WORKING_DIR` | No | Read access directory (default: `/home/dev`) |
| `CLAUDE_SANDBOX_DIR` | No | Write/execute directory |
| `CLAUDE_SETTINGS_FILE` | No | Claude Code settings for permissions |
| `MAX_VOICE_RESPONSE_CHARS` | No | TTS character limit (default: 500) |

### Sandbox Permissions

To restrict Claude to only write within the sandbox directory, create a settings file:

```json
{
  "permissions": {
    "allow": [
      "Edit(//path/to/sandbox/**)",
      "Write(//path/to/sandbox/**)"
    ]
  }
}
```

Then set `CLAUDE_SETTINGS_FILE` to point to it. See `settings.example.json`.

**How it works:**
- `allow` rules auto-approve writes to specified paths
- Writes elsewhere require permission (denied in headless mode)
- Uses `//` prefix for absolute paths (Claude Code convention)
- Read access controlled by `--add-dir` flag (set via `CLAUDE_WORKING_DIR`)

## Multi-Persona Setup

Run multiple bots from the same codebase with different configs:

```
/home/dev/voice-agents/
├── v.env              # V persona config
├── tc.env             # TC persona config
├── v-settings.json    # V sandbox permissions
├── tc-settings.json   # TC sandbox permissions
└── sandboxes/
    ├── v/             # V's sandbox
    └── tc/            # TC's sandbox
```

Each persona gets:
- Own Telegram bot token
- Own topic filter
- Own ElevenLabs voice
- Own sandbox directory
- Own permission settings

## Systemd Services

```bash
# /etc/systemd/system/claude-voice-v.service
[Unit]
Description=Claude Voice Assistant - V
After=network.target

[Service]
Type=simple
User=dev
WorkingDirectory=/home/dev/GitRepos/claude-voice-assistant
EnvironmentFile=/home/dev/voice-agents/v.env
ExecStart=/home/dev/GitRepos/claude-voice-assistant/.venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Testing

```bash
.venv/bin/pytest test_bot.py -v
```

## Files

- `bot.py` - Main bot code
- `prompts/` - Persona prompt files
- `.env.example` - Environment template
- `settings.example.json` - Permissions template
