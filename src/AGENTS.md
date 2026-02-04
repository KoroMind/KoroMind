# Source Directory Structure

Overview of what lives where in `src/`.

## Folders

```
src/
├── koro/              # Main package
│   ├── core/          # Brain engine (library) - brain, claude, voice, state, config
│   ├── api/           # REST API service - FastAPI app, routes, middleware
│   ├── interfaces/    # Interface adapters - telegram/, cli/
│   └── handlers/      # Legacy re-exports (backward compatibility)
│
├── prompts/           # System prompt templates
└── tests/             # Test suite (see tests/AGENTS.md)
```

## Key Modules

| Module | Purpose |
|--------|---------|
| `koro/core/brain.py` | Main orchestrator |
| `koro/core/claude.py` | Claude SDK wrapper |
| `koro/core/voice.py` | STT/TTS engine |
| `koro/core/state.py` | SQLite state manager |
| `koro/api/app.py` | FastAPI application |
| `koro/main.py` | Unified entry point |

## Coding Guidelines

For coding standards and review checklists, see `.ai/skills/coding-lessons/SKILL.md`.
