# TORIS Claude Voice Assistant

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

- **Telegram Bot** - Create one via [@BotFather](https://t.me/botfather)
- **ElevenLabs account** - API key from [elevenlabs.io](https://elevenlabs.io)
- **Claude Access** - Choose one authentication method (see below)

For Docker deployment:
- **Docker** and **Docker Compose**

For non-Docker deployment:
- **Python 3.12+**
- **Node.js 20+** (for Claude Code CLI)

### Claude Authentication

Choose ONE of these methods:

| Method | Best For | Setup |
|--------|----------|-------|
| **API Key** | Docker, CI/CD, teams | Set `ANTHROPIC_API_KEY` from [console.anthropic.com](https://console.anthropic.com) |
| **Subscription** | Personal use, Pro/Max/Teams plans | Run `claude /login` once, mount credentials |

**API Key Method:**
- Uses pre-paid API credits
- Set `ANTHROPIC_API_KEY` in your env file
- Works immediately in Docker

**Subscription Method (Pro/Max/Teams):**
- Uses your Claude subscription
- No API key needed
- For Docker: login on host first, then mount credentials

## Deployment Options

This project supports two deployment modes:

### Option 1: Docker (Recommended for Production)

Best for production deployment with automatic restarts and isolation.

**Quick Start:**
```bash
# Clone the repository
git clone --recurse-submodules https://github.com/toruai/toris-claude-voice-assistant.git
cd toris-claude-voice-assistant

# Configure
cp docker/toris.env.example docker/toris.env
# Edit docker/toris.env with your settings

# Choose authentication method:
# Option A: Add ANTHROPIC_API_KEY to docker/toris.env
# Option B: Login with subscription, then uncomment credentials mount in docker-compose.yml
#           claude /login  # Run on host first

# Start
docker-compose up -d

# View logs
docker-compose logs -f toris

# Stop
docker-compose down
```

**Benefits:**
- Isolated sandbox for file operations
- Automatic restarts on failure
- No Python/Node installation needed
- Persistent state across restarts
- Toru agents and skills pre-installed (Garry, Bob, Sentinel, Scout, etc.)

**Directory Structure:**
```
toris-claude-voice-assistant/
├── Dockerfile
├── docker-compose.yml
├── docker/
│   └── toris.env  # Your config (from example.env)
└── prompts/           # Persona prompts
```

See [Docker Deployment Guide](#docker-deployment-guide) for details.

### Option 2: Non-Docker (Systemd)

Best for development or single-persona deployments on Linux.

**Quick Start:**
```bash
# Clone and setup
git clone --recurse-submodules https://github.com/toruai/toris-claude-voice-assistant.git
cd toris-claude-voice-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Install Toru agents and skills (optional but recommended)
cd .claude-settings && ./install.sh && cd ..

# Configure
cp .env.example .env
# Edit .env with your values

# Run
python bot.py
```

The agents install adds 7 specialized AI agents (Garry, Bob, Sentinel, Scout, etc.) and 14 skills like `/dev-cycle` and `/scout`. See [toru-claude-agents](https://github.com/ToruAI/toru-claude-agents) for details.

See [Systemd Deployment Guide](#systemd-deployment-guide) for production setup.

---

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
| `CLAUDE_WORKING_DIR` | `/home/youruser` | Directory Claude can read from |
| `CLAUDE_SANDBOX_DIR` | `/home/youruser/claude-voice-sandbox` | Directory Claude can write to |
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

### Docker Multi-Persona

Duplicate the service in `docker-compose.yml` with different env files:

```yaml
services:
  toris:
    env_file: docker/toris.env
    volumes:
      - toris-state:/home/claude/state
      - toris-sandbox:/home/claude/sandbox

  assistant2:
    env_file: docker/assistant2.env
    volumes:
      - assistant2-state:/home/claude/state
      - assistant2-sandbox:/home/claude/sandbox
```

### Persona Prompt

See `prompts/toris.md` for the default TORIS persona. Key elements:

```markdown
# TORIS - Your Second Brain

You are TORIS, a voice-powered thinking partner built on Claude.

## Your Capabilities
- READ files from {read_dir}
- WRITE and EXECUTE in {sandbox_dir}
- Web search, research, note-taking via MEGG

## CRITICAL - Voice Output Rules
- NO markdown formatting
- Speak in natural flowing sentences
```

---

## Docker Deployment Guide

### Building and Running

```bash
# Build the image
docker-compose build

# Start
docker-compose up -d

# View logs
docker-compose logs -f toris

# Restart
docker-compose restart toris

# Stop
docker-compose down

# Stop and remove volumes (WARNING: deletes session history)
docker-compose down -v
```

### Configuration

Copy and edit the example environment file:

```bash
cp docker/toris.env.example docker/toris.env
```

**Key environment variables:**
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `TELEGRAM_DEFAULT_CHAT_ID` - Your Telegram chat ID (security)
- `ELEVENLABS_API_KEY` - ElevenLabs API key
- `ANTHROPIC_API_KEY` - Anthropic API key (optional if using subscription)
- `ELEVENLABS_VOICE_ID` - Voice selection
- `PERSONA_NAME` - Display name in logs
- `SYSTEM_PROMPT_FILE` - Path to persona prompt
- `MAX_VOICE_RESPONSE_CHARS` - Max TTS characters (default: 2000)

### Authentication

**Option 1: API Key** (recommended)
```bash
# Add to docker/toris.env
ANTHROPIC_API_KEY=sk-ant-...
```

**Option 2: Claude Subscription**
```bash
# 1. Login on host machine
claude /login

# 2. Uncomment in docker-compose.yml volumes:
- ~/.claude/.credentials.json:/home/claude/.claude/.credentials.json:ro
```

### Data Persistence

Docker volumes store persistent data:

| Volume | Contents | Location |
|--------|----------|----------|
| `toris-state` | Session history & settings | `/home/claude/state` |
| `toris-sandbox` | File operations sandbox | `/home/claude/sandbox` |
| `toris-claude-config` | Claude credentials & settings | `/home/claude/.claude` |

**Backup state:**
```bash
# Export session data
docker cp toris-claude-voice-assistant:/home/claude/state ./backup-state

# Import session data
docker cp ./backup-state/. toris-claude-voice-assistant:/home/claude/state
docker-compose restart toris
```

### Health Checks

Docker monitors bot health automatically. Check status:

```bash
# Container health
docker-compose ps

# If unhealthy, check logs
docker-compose logs v
```

---

## Systemd Deployment Guide

For non-Docker production deployments on Linux.

### Setup

```bash
# Create deployment directory
mkdir -p /opt/toris-claude-voice-assistant
cd /opt/toris-claude-voice-assistant

# Clone and install
git clone --recurse-submodules https://github.com/toruai/toris-claude-voice-assistant.git .
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Install Claude Code globally
npm install -g @anthropic-ai/claude-code

# Create config directory
mkdir -p /etc/claude-voice
cp .env.example /etc/claude-voice/v.env
# Edit /etc/claude-voice/v.env with your values
```

### Service File

Create `/etc/systemd/system/claude-voice-v.service`:

```ini
[Unit]
Description=Claude Voice Assistant - V
After=network.target

[Service]
Type=simple
User=claude
Group=claude
WorkingDirectory=/opt/toris-claude-voice-assistant
EnvironmentFile=/etc/claude-voice/v.env
ExecStart=/opt/toris-claude-voice-assistant/.venv/bin/python bot.py
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/var/lib/claude-voice/v-sandbox /var/lib/claude-voice/v-state

[Install]
WantedBy=multi-user.target
```

### Create User and Directories

```bash
# Create service user
useradd -r -s /bin/false claude

# Create state and sandbox directories
mkdir -p /var/lib/claude-voice/{v-state,v-sandbox}
chown -R claude:claude /var/lib/claude-voice

# Set sandbox path in env file
echo "CLAUDE_SANDBOX_DIR=/var/lib/claude-voice/v-sandbox" >> /etc/claude-voice/v.env
```

### Manage Service

```bash
# Enable and start
systemctl daemon-reload
systemctl enable claude-voice-v
systemctl start claude-voice-v

# Check status
systemctl status claude-voice-v

# View logs
journalctl -u claude-voice-v -f

# Restart
systemctl restart claude-voice-v
```

### Multiple Personas with Systemd

Create separate service files and env files:
- `/etc/systemd/system/claude-voice-v.service` + `/etc/claude-voice/v.env`
- `/etc/systemd/system/claude-voice-tc.service` + `/etc/claude-voice/tc.env`

Each persona needs its own sandbox and state directories.

---

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
