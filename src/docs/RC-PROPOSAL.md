# KoroMind RC - Componentize + Full Test Coverage

## Branch
```
feat/componentize-with-tests
```

---

## Current State

| Metric | Value |
|--------|-------|
| `src/bot.py` | 1389 lines, monolithic |
| Test coverage | 0% (no pytest tests) |
| Existing tests | 2 manual scripts |

---

## Target Architecture

```
KoroMind/
├── src/koro/
│   ├── __init__.py
│   ├── config.py           # Env vars, validation, constants
│   ├── auth.py             # Claude auth, credentials management
│   ├── voice.py            # ElevenLabs TTS + STT
│   ├── claude.py           # Claude SDK wrapper
│   ├── state.py            # Sessions + settings persistence
│   ├── rate_limit.py       # Rate limiting logic
│   ├── prompt.py           # System prompt loading/building
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── commands.py     # /start, /new, /status, /health, etc.
│   │   ├── messages.py     # Voice and text message handlers
│   │   └── callbacks.py    # Inline keyboard callbacks
│   └── main.py             # Entry point, wires everything
│
├── src/tests/
│   ├── conftest.py         # Shared fixtures, mocks
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_auth.py
│   │   ├── test_voice.py
│   │   ├── test_claude.py
│   │   ├── test_state.py
│   │   ├── test_rate_limit.py
│   │   ├── test_prompt.py
│   │   └── test_handlers.py
│   └── integration/
│       ├── test_elevenlabs_live.py
│       ├── test_claude_live.py
│       └── test_e2e.py
│
├── src/bot.py                  # Kept as thin wrapper → imports koro.main
├── pyproject.toml          # Add pytest config
└── uv.lock                 # Locked dependencies
```

---

## Component Breakdown

| Component | Lines (est.) | Responsibility |
|-----------|--------------|----------------|
| `config.py` | ~80 | Load env, validate, expose constants |
| `auth.py` | ~100 | Check Claude auth, load/save credentials |
| `voice.py` | ~60 | `transcribe()`, `text_to_speech()` |
| `claude.py` | ~150 | `query()` wrapper, message parsing |
| `state.py` | ~80 | Session/settings JSON persistence |
| `rate_limit.py` | ~50 | Rate check logic |
| `prompt.py` | ~50 | Load file, build dynamic prompt |
| `handlers/commands.py` | ~200 | All /command handlers |
| `handlers/messages.py` | ~150 | Voice + text handlers |
| `handlers/callbacks.py` | ~100 | Settings + approval callbacks |
| `main.py` | ~50 | App builder, handler registration |

---

## Test Coverage Plan

### Tier 1: Unit Tests (Mocked, Fast)

| Test File | What's Tested |
|-----------|---------------|
| `test_config.py` | Env parsing, defaults, validation errors |
| `test_auth.py` | Credential file parsing, token expiry logic |
| `test_voice.py` | Buffer handling, error paths (mocked API) |
| `test_claude.py` | Options building, message type handling |
| `test_state.py` | JSON save/load, default creation |
| `test_rate_limit.py` | Timing logic, cooldown, per-minute limits |
| `test_prompt.py` | File loading, placeholder replacement |
| `test_handlers.py` | Auth checks, routing, response formatting |

**Run:** `pytest src/tests/unit/ -v`
**Target:** 70%+ line coverage

### Tier 2: Integration Tests (Live APIs)

| Test File | What's Tested |
|-----------|---------------|
| `test_elevenlabs_live.py` | Real TTS → STT round-trip |
| `test_claude_live.py` | Real query, session creation/resume |
| `test_e2e.py` | Full: audio → transcribe → Claude → TTS |

**Run:** `pytest src/tests/integration/ -v --live`
**Requires:** Real API keys in `.env`

---

## Exit Criteria (Machine-Verifiable)

| Check | Command | Pass |
|-------|---------|------|
| Unit tests | `pytest src/tests/unit/ -v` | 0 failures |
| Coverage | `pytest src/tests/unit/ --cov=koro --cov-fail-under=70` | ≥70% |
| Live ElevenLabs | `pytest src/tests/integration/test_elevenlabs_live.py -v` | Pass |
| Live Claude | `pytest src/tests/integration/test_claude_live.py -v` | Pass |
| Full E2E | `pytest src/tests/integration/test_e2e.py -v` | Pass |
| Bot starts | `python src/bot.py` (ctrl+c after startup) | No crash |
| Imports clean | `python -c "import koro"` | No errors |

---

## What Changes for Users

**Nothing.** Same `python src/bot.py`, same commands, same behavior.

The `src/bot.py` file becomes:
```python
#!/usr/bin/env python3
"""KoroMind - Voice-first interface to Claude's agentic capabilities"""
from koro.main import main

if __name__ == "__main__":
    main()
```

---

## What Will NOT Change

- No new features
- No behavior changes
- No new runtime dependencies
- Docker setup unchanged
- src/prompts/ and docker/ configs untouched

---

## Dev Dependencies Added

```
pytest>=9.0.2
```

---

## Deliverables

1. `src/koro/` package with all components
2. `src/tests/unit/` with 70%+ coverage
3. `src/tests/integration/` with live API tests
4. Updated `pyproject.toml` dev extras
5. `pyproject.toml` with pytest config
6. Thin `src/bot.py` wrapper (backwards compatible)
7. All commits on `feat/componentize-with-tests` branch

---

## Validation Commands

```bash
# 1. Fast validation (no keys needed)
pytest src/tests/unit/ -v --cov=koro --cov-fail-under=70

# 2. Live validation (needs real keys)
pytest src/tests/integration/ -v

# 3. Manual smoke test
python src/bot.py
# Send voice message, verify response
```
