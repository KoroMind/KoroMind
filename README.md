# Claude Voice Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

**A voice-first interface to Claude's full agentic capabilities.** Not another chatbot wrapper.

<!-- Demo GIF here -->

Send a voice message, and Claude can search the web, read your files, write code, execute scripts, and respond with natural speech. All from Telegram.

## What Makes This Different

Most "voice AI" projects are thin wrappers around chat completions. This is different:

- **Agentic execution** - Claude can use tools: read files, search the web, write and execute code
- **Sandboxed safety** - All writes and execution happen in an isolated sandbox directory
- **Voice-native** - Built for voice input/output from the ground up, not text with TTS bolted on
- **Multi-persona** - Run different AI personalities from the same codebase, each with their own voice and sandbox
- **Session persistence** - Conversations continue across messages, even after restarts
- **Real-time control** - Watch mode streams tool calls, approve mode lets you authorize each action

## Features

| Feature | Description |
|---------|-------------|
| Voice transcription | ElevenLabs Scribe for accurate speech-to-text |
| Voice synthesis | ElevenLabs TTS with expressive voice settings |
| Claude Agent SDK | Official SDK with full tool access |
| Tool capabilities | Read, Grep, Glob, WebSearch, Bash, Edit, Write |
| Sandbox isolation | Claude can only write/execute in designated directory |
| Session management | Resume conversations, switch between sessions |
| Per-user settings | Audio on/off, voice speed, approval modes |
| Topic filtering | Multiple personas in one Telegram group |
| Rate limiting | Protect against abuse |

## Architecture

```
Telegram Voice Message
        |
        v
+-------------------+
|   Telegram Bot    |  <-- python-telegram-bot
+-------------------+
        |
        v
+-------------------+
| ElevenLabs Scribe |  <-- Speech-to-text
+-------------------+
        |
        v
+-------------------+
| Claude Agent SDK  |  <-- Full agentic capabilities
|   - WebSearch     |      (reads, writes, executes)
|   - Bash          |
|   - Read/Write    |
+-------------------+
        |
        v
+-------------------+
|  ElevenLabs TTS   |  <-- Text-to-speech
+-------------------+
        |
        v
   Voice Response
```

## Prerequisites

- **Python 3.12+**
- **Telegram Bot** - Create one via [@BotFather](https://t.me/botfather)
- **ElevenLabs account** - API key from [elevenlabs.io](https://elevenlabs.io)
- **Claude Code** - Install via `npm install -g @anthropic-ai/claude-code`

## Quick Start

1. Clone and setup:
```bash
git clone https://github.com/toruai/claude-voice-assistant.git
cd claude-voice-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure:
```bash
cp .env.example .env
# Edit .env with your values
```

3. Run:
```bash
python bot.py
```

4. Send a voice message to your Telegram bot.

## Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_DEFAULT_CHAT_ID` | Your Telegram chat ID (security: only this chat can use the bot) |
| `ELEVENLABS_API_KEY` | API key from elevenlabs.io |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PERSONA_NAME` | `Assistant` | Display name in logs |
| `SYSTEM_PROMPT_FILE` | - | Path to persona prompt file |
| `ELEVENLABS_VOICE_ID` | `JBFqnCBsd6RMkjVDRZzb` | ElevenLabs voice (George) |
| `TELEGRAM_TOPIC_ID` | - | Filter to specific forum topic |
| `CLAUDE_WORKING_DIR` | `/home/dev` | Directory Claude can read from |
| `CLAUDE_SANDBOX_DIR` | `/home/dev/claude-voice-sandbox` | Directory Claude can write to |
| `MAX_VOICE_RESPONSE_CHARS` | `500` | Max characters for TTS |

## User Settings

Use `/settings` in Telegram to configure:

- **Mode**: "Go All" (auto-approve tools) or "Approve" (confirm each action)
- **Watch**: Stream tool calls to chat in real-time
- **Audio**: Enable/disable voice responses
- **Speed**: Voice playback speed (0.8x - 1.2x)

## Multi-Persona Setup

Run multiple AI personalities from the same codebase. Each gets its own:
- Telegram bot
- Voice and personality
- Sandbox directory
- Topic filter (for group chats)

### Directory Structure

```
/home/dev/voice-agents/
├── v.env              # V persona config
├── tc.env             # TC persona config
└── sandboxes/
    ├── v/             # V's isolated sandbox
    └── tc/            # TC's isolated sandbox
```

### Example Persona Prompt

See `prompts/v.md` for a full example. Key elements:

```markdown
You are V, a brilliant and slightly cynical voice assistant.

## Your capabilities:
- You can READ files from anywhere in {read_dir}
- You can WRITE and EXECUTE only in {sandbox_dir}
- You have WebSearch for current information

## CRITICAL - Voice output rules:
- NO markdown formatting
- Speak in natural flowing sentences
```

### Systemd Service

```ini
[Unit]
Description=Claude Voice Assistant - V
After=network.target

[Service]
Type=simple
User=dev
WorkingDirectory=/path/to/claude-voice-assistant
EnvironmentFile=/home/dev/voice-agents/v.env
ExecStart=/path/to/claude-voice-assistant/.venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Show help |
| `/new [name]` | Start new session |
| `/continue` | Resume last session |
| `/sessions` | List all sessions |
| `/switch <id>` | Switch to specific session |
| `/status` | Current session info |
| `/settings` | Configure audio, speed, mode |
| `/health` | System health check |

## Security Considerations

- **Chat ID restriction** - Only configured chat ID can interact with the bot
- **Sandbox isolation** - Claude can only write/execute in the sandbox directory
- **Rate limiting** - Built-in protection against abuse (2s cooldown, 10/minute limit)
- **No secrets in prompts** - Keep API keys in `.env`, not in persona files

## Development

```bash
# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest test_bot.py -v

# Run with coverage
pytest test_bot.py --cov=bot --cov-report=term-missing
```

## How It Works

1. **Voice input**: Telegram receives voice message, bot downloads it
2. **Transcription**: ElevenLabs Scribe converts speech to text
3. **Processing**: Claude Agent SDK processes with full tool access
4. **Tool execution**: Claude can search web, read files, execute code in sandbox
5. **Response**: Text response sent to chat
6. **Voice output**: ElevenLabs TTS converts response to speech (if enabled)

The Claude Agent SDK provides real agentic capabilities - Claude can autonomously use multiple tools to accomplish tasks, not just respond to prompts.

## License

[MIT](LICENSE) - ToruAI 2026
