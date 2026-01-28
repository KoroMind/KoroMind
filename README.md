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
                       EXTERNAL CLIENTS
       ┌────────────┐   ┌────────────┐   ┌────────────┐
       │  Telegram  │   │   Mobile   │   │  Terminal  │
       │    App     │   │    App     │   │            │
       └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
             │                │                │
─────────────┼────────────────┼────────────────┼─────────────
             │                │                │
             ▼                ▼                ▼
┌───────────────────────────────────────────────────────────┐
│                         KOROMIND                          │
│                                                           │
│    ┌────────────┐   ┌────────────┐   ┌────────────┐       │
│    │  Telegram  │   │  REST API  │   │    CLI     │       │
│    │    Bot     │   │   Server   │   │            │       │
│    └─────┬──────┘   └─────┬──────┘   └─────┬──────┘       │
│          └────────────────┼────────────────┘              │
│                           │                               │
│                    ┌──────▼──────┐                        │
│                    │    Brain    │                        │
│                    └──────┬──────┘                        │
│                           │                               │
│          ┌────────────────┼────────────────┐              │
│          │                │                │              │
│    ┌─────▼─────┐   ┌──────▼──────┐   ┌─────▼─────┐        │
│    │ Providers │   │   Storage   │   │   Vault   │        │
│    │Claude/11L │   │   SQLite    │   │  Markdown │        │
│    └───────────┘   └──────┬──────┘   └─────┬─────┘        │
│                           │                │              │
└───────────────────────────┼────────────────┼──────────────┘
                            │                │
                     ┌──────▼────────────────▼──────┐
                     │   ~/.koromind/ (shared data) │
                     └──────────────────────────────┘
```

All services share the same data directory. In Docker, this is a mounted volume.

### Package Structure

```
src/koro/
├── core/                    # Brain engine (interface-agnostic)
│   ├── brain.py             # Main orchestrator
│   ├── factory.py           # build_brain() wires dependencies
│   ├── state.py             # State facade over storage repos
│   ├── sessions.py          # Session business logic
│   ├── policy.py            # Mode/rate limit rules
│   ├── approvals.py         # Approval callback tracking
│   ├── auth.py              # Token logic/policies
│   ├── types.py             # Shared types
│   └── config.py            # Configuration
│
├── storage/                 # SQLite persistence layer
│   ├── db.py                # Connection, WAL mode, migrations
│   ├── migrations/          # SQL migration files
│   └── repos/               # Data access repositories
│       ├── sessions_repo.py
│       ├── settings_repo.py
│       └── auth_repo.py
│
├── vault/                   # Long-term memory (markdown vault)
│   ├── layout.py            # Folder structure + path helpers
│   ├── notes.py             # Create/update/move notes (stub)
│   ├── daily.py             # Daily log (stub)
│   └── attachments.py       # File blobs (stub)
│
├── providers/               # External service wrappers
│   ├── llm/
│   │   └── claude.py        # Claude SDK wrapper
│   └── voice/
│       └── elevenlabs.py    # ElevenLabs STT/TTS
│
├── api/                     # REST API service
│   ├── app.py               # FastAPI application
│   ├── deps.py              # Dependency injection
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
- [Claude Code](https://claude.ai/code) installed (optional, used by health check)
- Telegram bot token from [@BotFather](https://t.me/botfather) (for Telegram interface)
- ElevenLabs API key from [elevenlabs.io](https://elevenlabs.io) (for voice)

### Docker (Recommended)

```bash
cp .env.example .env   # Edit with your credentials
docker-compose up -d --build
```

### Manual Setup

```bash
pip install uv
uv venv -p python3.11 && source .venv/bin/activate
uv sync
cp .env.example .env   # Edit with your credentials

# Run one of:
python -m koro              # Telegram bot
python -m koro api          # REST API
python -m koro cli          # CLI
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
| `/switch <id>` | Switch session |
| `/status` | Bot + environment status |
| `/settings` | Configure mode, watch, audio, voice speed |
| `/setup` | Setup tokens/keys |
| `/claude_token` | Set Claude token |
| `/elevenlabs_key` | Set ElevenLabs key |
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
- `/switch <id>` - Switch session
- `/settings` - View settings
- `/audio on|off` - Toggle audio
- `/mode go_all|approve` - Set mode (approve not supported in CLI)
- `/health` - Check system health
- `/help` - Show help
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
User identity is derived from the API key.

### Example

```bash
# Process a message
curl -X POST http://localhost:8420/api/v1/messages/text \
  -H "X-API-Key: your-key" \
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
| `KOROMIND_ALLOW_NO_AUTH` | `false` | Allow unauthenticated API access (dev only) |
| `KOROMIND_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated CORS allowlist |
| `KOROMIND_HOST` | `127.0.0.1` | Bind address |
| `KOROMIND_PORT` | `8420` | API port |

**Optional:**
| Variable | Default | Description |
|----------|---------|-------------|
| `KOROMIND_DATA_DIR` | `~/.koromind` | Data directory |
| `KOROMIND_VAULT_DIR` | `~/.koromind/vault` | Long-term memory vault |
| `KOROMIND_SANDBOX_DIR` | `~/.koromind/sandbox` | Write/execute directory |
| `CLAUDE_WORKING_DIR` | `~` | Read access directory |
| `PERSONA_NAME` | `Assistant` | Display name |
| `SYSTEM_PROMPT_FILE` | - | Custom persona prompt |
| `ELEVENLABS_VOICE_ID` | `JBFqnCBsd6RMkjVDRZzb` | Voice ID |

---

## Data Storage

KoroMind stores data in `~/.koromind/` (configurable via `KOROMIND_DATA_DIR`):

```
~/.koromind/
├── db/
│   └── koromind.db      # SQLite database (sessions, settings, memory)
├── vault/               # Long-term memory (markdown + attachments)
│   ├── 00_INBOX/        # Uncategorized notes
│   ├── daily/           # Daily logs
│   └── _templates/      # Note templates
└── sandbox/             # Working scratchpad for Claude
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

- **Modular Package Structure**: Separates core engine, storage, providers, and interfaces
- **Core Library Pattern**: `koro.core` is interface-agnostic, enabling multiple frontends
- **Repository Pattern**: Data access isolated in `koro.storage.repos` for testability
- **Factory Pattern**: `build_brain()` wires all dependencies, preventing drift across processes
- **SQLite with WAL**: Replaces JSON files for better concurrency and querying
- **Vault for Long-term Memory**: Human-readable markdown files for durable knowledge
- **FastAPI for API**: Modern async framework with automatic OpenAPI docs
- **ElevenLabs Scribe** for STT: Handles accents and ambient noise well
- **ElevenLabs Turbo v2.5** for TTS: Low latency with expressive voice
- **Claude Agent SDK**: Official SDK for agentic capabilities
- **Sandboxed by default**: Never trust an AI with full filesystem access

---

<p align="center">
  <strong>KoroMind</strong> | MIT License | 2026
</p>
