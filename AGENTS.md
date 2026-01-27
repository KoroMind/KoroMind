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

## Documentation and Specifications

This project follows **spec-driven development**: define the specification first, then implement. Spec files live in `.ai/specs/` and serve as the source of truth for design decisions. See `.ai/specs/AGENTS.md` for full guidelines.

### Workflow

**1. Create a GitHub issue first:**

Before writing code, create an issue that serves as the specification:
- **User story**: Who needs this and why? ("As a user, I want X so that Y")
- **Acceptance criteria**: What conditions must be met for this to be complete?
- **Test cases**: What scenarios should be tested? Include edge cases
- **Technical notes**: Any implementation constraints, dependencies, or considerations

```bash
gh issue create \
  --title "Add rate limiting per user" \
  --body "## User Story
As an admin, I want per-user rate limiting so that no single user can overwhelm the bot.

## Acceptance Criteria
- [ ] Users limited to 10 requests per minute
- [ ] Rate limit state persists across restarts
- [ ] Clear error message when limit exceeded

## Test Cases
- Verify limit triggers after 10 requests
- Verify limit resets after 60 seconds
- Verify state survives bot restart

## Technical Notes
- Store in user_settings.json alongside other preferences
- Use sliding window algorithm" \
  --label enhancement
```

**Then create a linked branch:**

```bash
gh issue develop <ISSUE_NUMBER>
```

This single command creates a branch, checks it out, and links it to the issue—keeping everything connected from spec to implementation.

**2. Before coding:**
- Check if a spec exists for the module you're modifying
- Read the spec to understand design intent and constraints

**3. When adding features:**
- Update the corresponding spec file with new functionality, API changes, and data model updates
- Add a changelog entry with date and summary

**4. When creating new modules:**
- Create a new spec file at `.ai/specs/<module-name>.md`
- Document the initial design before or alongside implementation

**5. After coding:**
- Generate or update specs when implementing significant changes, even if not explicitly asked
- Keep specs synchronized with actual implementation
- Reference the issue number in commits

## Python Best Practices

### Asyncio / Non-Blocking I/O

- Use `aiofiles` for file operations in async contexts
- Use async HTTP clients (`httpx.AsyncClient`) instead of `requests`
- Use `asyncio.sleep()` instead of `time.sleep()` in async functions
- Load static resources (prompts, config files) at app startup, not per-request

### Exception Handling

- Catch specific exceptions (`ValueError`, `KeyError`, `httpx.HTTPError`), never bare `except Exception`
- Keep try blocks small and focused around the specific operation that may fail
- Let exceptions propagate to framework handlers when you can't meaningfully handle them
- Don't wrap entire function bodies in try/except—isolate the risky operation


### Code Organization

- Keep all imports at module top level, not inside functions
- Return new objects instead of mutating parameters as side effects, use immutable structures (frozen=True) if possible
- If mutation is unavoidable, make it explicit in the function name (e.g., `append_to_list()`)

### Defensive Programming

- Validate inputs at system boundaries (user input, external APIs)
- Trust internal code and framework guarantees—don't over-validate
- Make function behavior explicit through clear naming
