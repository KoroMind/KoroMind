# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KoroMind is a voice-first Telegram bot that connects ElevenLabs STT/TTS with the Claude Agent SDK for agentic tool execution. Users send voice messages, Claude executes tools (Read, Write, Bash, WebSearch, etc.), and responses come back as voice.

## Commands

### Setup
```bash
pip install uv
uv venv -p python3.11
source .venv/bin/activate
uv sync --extra dev
cp .env.example .env  # Then fill in credentials
```

### Running
```bash
python src/bot.py                # Run the bot
docker compose up -d --build     # Docker deployment
docker compose logs -f koro      # View Docker logs
```

### Testing
```bash
pytest -v                        # Run all tests
pytest src/tests/unit -v         # Unit tests only
pytest src/tests/integration -v  # Integration tests (need API keys)
pytest -m "not live" -v          # Skip tests requiring live APIs
pytest src/tests/unit/test_voice.py::test_name -v  # Single test
pytest --cov=koro --cov-report=term-missing    # Coverage
```

### Linting (via pre-commit)
```bash
pre-commit run --all-files       # Run all checks
pre-commit run black --all-files # Just black
pre-commit run ruff-check --all-files
```

## Architecture

### Package Structure
- `src/bot.py` - Entry point, imports from `koro.main`
- `src/koro/` - Main package
  - `main.py` - Application setup and Telegram bot initialization
  - `config.py` - Environment configuration loading
  - `claude.py` - Claude Agent SDK integration
  - `voice.py` - ElevenLabs STT/TTS handling
  - `state.py` - Session and user settings persistence
  - `auth.py` - Chat ID and topic authorization
  - `rate_limit.py` - Per-user rate limiting
  - `prompt.py` - System prompt loading
  - `handlers/` - Telegram handlers
    - `commands.py` - /start, /new, /settings, etc.
    - `messages.py` - Voice and text message processing
    - `callbacks.py` - Inline button callbacks (approve/deny, settings)
    - `utils.py` - Shared handler utilities

### Key Concepts
- **Sessions**: Conversation context persists via session IDs stored in `sessions_state.json`
- **Approve Mode**: Human-in-the-loop requiring inline button confirmation for each tool call
- **Go All Mode**: Auto-approve all tool executions
- **Watch Mode**: Stream tool calls to Telegram in real-time
- **Sandbox**: Claude can only write/execute in configured sandbox directory

### Data Flow
```
Voice → Download → ElevenLabs STT → Claude Agent SDK → [Tools] → Response → ElevenLabs TTS → Voice reply
```

### State Files
- `sessions_state.json` - Per-user session IDs and current session
- `user_settings.json` - Per-user preferences (mode, audio, speed, watch)

## Code Style
- Python 3.11+, PEP 8
- Type hints for function signatures
- Black for formatting (line-length 88)
- isort with black profile
- ruff for linting

## Testing Notes
- Tests use pytest-asyncio with `asyncio_mode = "auto"`
- Integration tests marked with `@pytest.mark.live` require real API keys
- Fixtures in `src/tests/conftest.py` provide mocked Telegram updates, contexts, and ElevenLabs clients
