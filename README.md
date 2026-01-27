<p align="center">
  <strong>KoroMind</strong><br>
  <em>Your personal AI assistant - multi-interface access to Claude's agentic capabilities</em>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> |
  <a href="#architecture">Architecture</a> |
  <a href="#interfaces">Interfaces</a> |
  <a href="#api">API</a> |
  <a href="#deployment">Deployment</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Claude-Agent%20SDK-7c3aed?style=flat-square" alt="Claude Agent SDK">
  <img src="https://img.shields.io/badge/FastAPI-REST-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Telegram-Bot-26a5e4?style=flat-square&logo=telegram&logoColor=white" alt="Telegram Bot">
  <img src="https://img.shields.io/badge/ElevenLabs-TTS%20%2B%20STT-000000?style=flat-square" alt="ElevenLabs">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License">
</p>

---

## Your Second Brain

KoroMind is a multi-interface personal AI assistant ("second brain") built on Claude's agentic capabilities. Access it via Telegram, REST API, or CLI.

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
┌─────────────────────────────────────────────────────────────────┐
│                        INTERFACES                                │
│   ┌──────────┐     ┌─────────┐     ┌───────────────────────┐   │
│   │ Telegram │     │   CLI   │     │  Future: SMS, Mobile  │   │
│   └────┬─────┘     └────┬────┘     └───────────┬───────────┘   │
└────────┼────────────────┼──────────────────────┼────────────────┘
         │                │                      │
         └────────────────┴──────────────────────┘
                          │
                   ┌──────┴──────┐
                   │  REST API   │  ← FastAPI service
                   │ (koro.api)  │
                   └──────┬──────┘
                          │
                   ┌──────┴──────┐
                   │ Brain Engine│  ← Core library
                   │ (koro.core) │
                   └──────┬──────┘
                          │
      ┌───────────────────┼───────────────────┐
      │                   │                   │
┌─────┴─────┐     ┌───────┴───────┐    ┌─────┴─────┐
│  Claude   │     │    Voice      │    │   State   │
│  Agent    │     │   (STT/TTS)   │    │  (SQLite) │
└───────────┘     └───────────────┘    └───────────┘
```

### Package Structure

```
src/koro/
├── core/                    # Brain engine (library)
│   ├── brain.py             # Main orchestrator
│   ├── claude.py            # Claude SDK wrapper
│   ├── voice.py             # STT/TTS engine
│   ├── state.py             # SQLite state manager
│   ├── types.py             # Shared types
│   └── config.py            # Configuration
│
├── api/                     # REST API service
│   ├── app.py               # FastAPI application
│   └── routes/              # API endpoints
│
└── interfaces/
    ├── telegram/            # Telegram bot
    │   ├── bot.py
    │   └── handlers/
    │
    └── cli/                 # Command-line interface
        └── app.py
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- [Claude Code](https://claude.ai/code) installed
- Telegram bot token from [@BotFather](https://t.me/botfather) (for Telegram interface)
- ElevenLabs API key from [elevenlabs.io](https://elevenlabs.io) (for voice)

### Installation

```bash
# Clone and setup
git clone https://github.com/yourusername/koromind.git
cd koromind

# Install with uv (recommended)
pip install uv
uv venv -p python3.11
source .venv/bin/activate
uv sync

# Or with pip
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your credentials
```

### Running

```bash
# Telegram Bot (default)
python -m koro
# or
koromind telegram

# REST API Server
python -m koro api
# or
koromind api --port 8420

# CLI Interface
python -m koro cli
# or
koro-cli
```

### Docker

```bash
docker-compose up --build -d
```

---

## Interfaces

### Telegram Bot

Send voice or text messages to your bot. Full agentic capabilities with voice responses.

**Commands:**
| Command | Description |
|---------|-------------|
| `/start` | Show help |
| `/new [name]` | Start new session |
| `/continue` | Resume last session |
| `/sessions` | List all sessions |
| `/settings` | Configure mode, audio, voice speed |
| `/health` | System health check |

**Settings Menu:**
- **Mode**: "Go All" (auto-approve) or "Approve" (confirm each action)
- **Watch**: Stream tool calls in real-time
- **Audio**: Enable/disable voice responses
- **Speed**: Voice playback speed (0.8x - 1.2x)

### CLI

Interactive terminal interface with Rich formatting.

```bash
koro-cli
# or
python -m koro cli
```

**Commands:**
- `/new` - Start new session
- `/sessions` - List sessions
- `/settings` - View settings
- `/health` - Check system health
- `/quit` - Exit

### REST API

Full API access for building custom integrations.

---

## API

### Endpoints

```
POST /api/v1/messages          # Process text or voice message
POST /api/v1/messages/text     # Simplified text endpoint

GET  /api/v1/sessions          # List sessions
POST /api/v1/sessions          # Create new session
GET  /api/v1/sessions/current  # Get current session
PUT  /api/v1/sessions/current  # Switch session

GET  /api/v1/settings          # Get user settings
PUT  /api/v1/settings          # Update settings

GET  /api/v1/health            # Health check
```

### Authentication

Set `KOROMIND_API_KEY` in environment. Include in requests as `X-API-Key` header.

### Example

```bash
# Process a message
curl -X POST http://localhost:8420/api/v1/messages/text \
  -H "X-API-Key: your-key" \
  -H "X-User-ID: user123" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the weather like?", "include_audio": false}'
```

---

## Configuration

### Environment Variables

**Required:**
| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `ELEVENLABS_API_KEY` | ElevenLabs API key |

**Telegram Interface:**
| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `TELEGRAM_DEFAULT_CHAT_ID` | Your chat ID (security) |

**API Server:**
| Variable | Default | Description |
|----------|---------|-------------|
| `KOROMIND_API_KEY` | - | API authentication key |
| `KOROMIND_HOST` | `127.0.0.1` | Bind address |
| `KOROMIND_PORT` | `8420` | API port |

**Optional:**
| Variable | Default | Description |
|----------|---------|-------------|
| `KOROMIND_DATA_DIR` | `~/.koromind` | Data directory |
| `PERSONA_NAME` | `Assistant` | Display name |
| `SYSTEM_PROMPT_FILE` | - | Custom persona prompt |
| `ELEVENLABS_VOICE_ID` | `JBFqnCBsd6RMkjVDRZzb` | Voice ID |
| `CLAUDE_WORKING_DIR` | `~` | Read access directory |
| `CLAUDE_SANDBOX_DIR` | `~/claude-voice-sandbox` | Write/execute directory |

---

## Data Storage

KoroMind stores data in `~/.koromind/` (configurable via `KOROMIND_DATA_DIR`):

```
~/.koromind/
└── koromind.db     # SQLite database (sessions, settings, memory)
```

Legacy JSON files are automatically migrated on first run.

---

## Security

| Protection | Description |
|------------|-------------|
| Chat ID restriction | Only configured chat ID can use Telegram bot |
| Sandbox isolation | Claude can only write/execute in sandbox directory |
| Rate limiting | 2s cooldown, 10 messages/minute per user |
| API authentication | API key required for REST endpoints |
| Approval mode | Optional manual authorization for each tool call |

---

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
pytest -v                        # All tests
pytest src/tests/unit -v         # Unit tests only
pytest -m "not live" -v          # Skip live API tests

# Linting
pre-commit run --all-files

# Coverage
pytest --cov=koro --cov-report=term-missing
```

---

## Architecture Decisions

- **Core Library Pattern**: `koro.core` is interface-agnostic, enabling multiple frontends
- **SQLite for State**: Replaces JSON files for better concurrency and querying
- **FastAPI for API**: Modern async framework with automatic OpenAPI docs
- **ElevenLabs Scribe** for STT: Handles accents and ambient noise well
- **ElevenLabs Turbo v2.5** for TTS: Low latency with expressive voice
- **Claude Agent SDK**: Official SDK for agentic capabilities
- **Sandboxed by default**: Never trust an AI with full filesystem access

---

<p align="center">
  <strong>KoroMind</strong> | MIT License | 2026
</p>
