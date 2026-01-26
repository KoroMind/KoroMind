<p align="center">
  <strong>KoroMind</strong><br>
  <em>Voice-first interface to Claude's agentic capabilities</em>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> |
  <a href="#architecture">Architecture</a> |
  <a href="#commands">Commands</a> |
  <a href="#deployment">Deployment</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/Claude-Agent%20SDK-7c3aed?style=flat-square" alt="Claude Agent SDK">
  <img src="https://img.shields.io/badge/Telegram-Bot-26a5e4?style=flat-square&logo=telegram&logoColor=white" alt="Telegram Bot">
  <img src="https://img.shields.io/badge/ElevenLabs-TTS%20%2B%20STT-000000?style=flat-square" alt="ElevenLabs">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License">
</p>

---

## Not Another Chatbot

Most "voice AI" projects wrap chat completions with speech-to-text. This is different.

**Claude can actually do things:**

| You say... | Claude does... |
|------------|----------------|
| "Search for the latest on React Server Components" | Runs WebSearch, synthesizes findings, speaks the summary |
| "Read my project's package.json and tell me what's outdated" | Uses Read tool, analyzes dependencies, responds with insights |
| "Write a Python script that fetches my calendar" | Creates the file in sandbox, executes it, reports results |
| "Find all TODO comments in the codebase" | Uses Grep across your files, summarizes what needs attention |

Full agentic loop. Voice in, action, voice out.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TELEGRAM LAYER                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Commands   │  │  Callbacks  │  │   Voice     │  │       Text          │ │
│  │ /new /start │  │  Approve    │  │  Messages   │  │     Messages        │ │
│  │ /settings   │  │  Settings   │  │             │  │                     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                     │            │
│         └────────────────┴────────┬───────┴─────────────────────┘            │
│                                   │                                          │
│                    ┌──────────────▼──────────────┐                           │
│                    │       SECURITY GATES        │                           │
│                    │  Chat ID → Topic → Rate     │                           │
│                    └──────────────┬──────────────┘                           │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
┌─────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  STATE MANAGER  │     │    VOICE ENGINE     │     │  SETTINGS STORE  │
│                 │     │                     │     │                  │
│ sessions_state  │     │  ┌───────────────┐  │     │  audio: on/off   │
│   .json         │◄────┤  │ ElevenLabs    │  │     │  speed: 0.8-1.2  │
│                 │     │  │ Scribe (STT)  │  │     │  mode: go_all/   │
│ • current_sess  │     │  └───────┬───────┘  │     │        approve   │
│ • session_ids[] │     │          │          │     │  watch: on/off   │
│ • per-user      │     │          ▼          │     │                  │
└────────┬────────┘     │     Transcript      │     └────────┬─────────┘
         │              └──────────┬──────────┘              │
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      CLAUDE AGENT SDK       │
                    │                             │
                    │  ┌───────────────────────┐  │
                    │  │    TOOL EXECUTION     │  │
                    │  │                       │  │
                    │  │  Read   Grep   Bash   │  │
                    │  │  Write  Edit   Glob   │  │
                    │  │  WebSearch  WebFetch  │  │
                    │  └───────────┬───────────┘  │
                    │              │              │
                    │    ┌────────┴────────┐     │
                    │    │                 │     │
                    │    ▼                 ▼     │
                    │ ┌──────┐       ┌────────┐  │
                    │ │GO ALL│       │APPROVE │  │
                    │ │ mode │       │  mode  │  │
                    │ │      │       │        │  │
                    │ │ Auto │       │ Human  │  │
                    │ │      │       │ gate   │  │
                    │ └──────┘       └───┬────┘  │
                    │                    │       │
                    │         ┌──────────▼─────┐ │
                    │         │ Inline Button  │ │
                    │         │ [Approve][Deny]│ │
                    │         └────────────────┘ │
                    │                             │
                    │  ┌───────────────────────┐  │
                    │  │    WATCH MODE         │  │
                    │  │  Stream tool calls    │  │
                    │  │  to Telegram live     │  │
                    │  └───────────────────────┘  │
                    │                             │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      VOICE ENGINE (TTS)     │
                    │                             │
                    │  ElevenLabs Turbo v2.5      │
                    │  • Configurable voice       │
                    │  • Speed: per-user          │
                    │  • Expressive settings      │
                    │                             │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                           Voice Response
```

### Data Flows

**Voice → Response (main path):**
```
Voice msg → Download → STT → Claude SDK → [Tools] → Response → TTS → Voice reply
```

**Tool Approval (approve mode):**
```
Claude wants tool → Send button to Telegram → Wait for click → Allow/Deny → Continue
```

**Session Resume:**
```
/continue → Load session_id from state → Claude SDK continue_conversation=true → Context preserved
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Sandbox** | Claude can only write/execute in isolated directory |
| **Sessions** | Conversation context persists across messages and restarts |
| **Watch Mode** | Real-time streaming of tool calls to Telegram |
| **Approve Mode** | Human-in-the-loop for each tool execution |

### State Persistence

```
sessions_state.json          user_settings.json
┌─────────────────────┐      ┌─────────────────────┐
│ "user_123": {       │      │ "user_123": {       │
│   current: "abc..", │      │   audio: true,      │
│   sessions: [...]   │      │   speed: 1.1,       │
│ }                   │      │   mode: "go_all",   │
│                     │      │   watch: false      │
└─────────────────────┘      └─────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- [Claude Code](https://claude.ai/code) installed (`npm install -g @anthropic-ai/claude-code`)
- Telegram bot token from [@BotFather](https://t.me/botfather)
- ElevenLabs API key from [elevenlabs.io](https://elevenlabs.io)

### Setup

```bash
git clone https://github.com/KoroMind/KoroMind.git
cd KoroMind

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your credentials

python bot.py
```

Send a voice message to your bot. That's it.

---

## Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `TELEGRAM_DEFAULT_CHAT_ID` | Your chat ID (security restriction) |
| `ELEVENLABS_API_KEY` | From elevenlabs.io |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PERSONA_NAME` | `Assistant` | Display name in logs |
| `SYSTEM_PROMPT_FILE` | - | Path to persona prompt (e.g., `prompts/v.md`) |
| `ELEVENLABS_VOICE_ID` | `JBFqnCBsd6RMkjVDRZzb` | ElevenLabs voice ID |
| `TELEGRAM_TOPIC_ID` | - | Filter to specific forum topic |
| `CLAUDE_WORKING_DIR` | `/home/dev` | Directory Claude can read |
| `CLAUDE_SANDBOX_DIR` | `/home/dev/claude-voice-sandbox` | Directory Claude can write/execute |
| `MAX_VOICE_RESPONSE_CHARS` | `500` | Max TTS characters |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show help |
| `/new [name]` | Start new conversation session |
| `/continue` | Resume last session |
| `/sessions` | List all sessions |
| `/switch <id>` | Switch to specific session |
| `/status` | Current session info |
| `/settings` | Configure mode, audio, voice speed |
| `/health` | System health check |

### Settings Menu

Access via `/settings`:

- **Mode**: "Go All" (auto-approve all tools) or "Approve" (confirm each action)
- **Watch**: Stream tool calls to chat in real-time
- **Audio**: Enable/disable voice responses
- **Speed**: Voice playback speed (0.8x - 1.2x)

---

## Deployment

### Production Setup

1. Clone repo on your server
2. Set up Python environment
3. Configure `.env`
4. Run with systemd or supervisor

---

## Security

| Protection | Description |
|------------|-------------|
| Chat ID restriction | Only configured chat ID can interact |
| Sandbox isolation | Claude can only write/execute in sandbox directory |
| Rate limiting | 2s cooldown, 10 messages/minute per user |
| Approval mode | Optional manual authorization for each tool call |

---

## Development

```bash
pip install pytest pytest-asyncio pytest-cov

pytest test_bot.py -v
pytest test_bot.py --cov=bot --cov-report=term-missing
```

---

## Architecture Decisions

- **ElevenLabs Scribe** for STT - handles accents and ambient noise well
- **ElevenLabs Turbo v2.5** for TTS - low latency with expressive voice settings
- **Claude Agent SDK** - official SDK, not subprocess shelling to CLI
- **python-telegram-bot** - mature async library with good typing
- **Sandboxed by default** - never trust an AI with full filesystem access

---

<p align="center">
  <strong>KoroMind</strong> | MIT License | 2026
</p>
