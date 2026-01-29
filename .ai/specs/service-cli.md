---
id: SVC-006
type: service
status: active
severity: low
issue: null
validated: 2026-01-29
---

# CLI Interface

## What
- Terminal REPL for KoroMind using Rich and Typer
- Text-only interface for local development/testing
- No approval mode support (GO_ALL only)

## Why
- Quick testing without Telegram setup
- Debugging and development workflows
- Headless server access

## How
- Core: `src/koro/interfaces/cli/app.py`
- Framework: Typer (CLI) + Rich (TUI)

### Entry Points
```bash
python -m koro cli        # Start REPL
python -m koro cli health # Health check only
python -m koro cli sessions --user <id>
```

### REPL Commands
| Command | Purpose |
|---------|---------|
| `/new` | Create new session |
| `/sessions` | List sessions |
| `/switch <id>` | Switch session |
| `/settings` | View settings |
| `/audio on\|off` | Toggle audio |
| `/mode go_all\|approve` | Set mode (approve warns) |
| `/health` | System health |
| `/help` | Show commands |
| `/quit` | Exit |

### Limitations
- No voice input (text only)
- No audio output (disabled)
- Approve mode not supported (shows warning)
- User ID defaults to `cli-user`

### Display
- Rich panels for responses
- Tables for sessions/settings
- Markdown rendering for Claude output
- Metadata: cost, turns, tool count

## Test
- REPL starts and accepts input
- Commands execute correctly
- Health check returns proper exit code
- Graceful handling of Ctrl+C

## Changelog

### 2026-01-29
- Initial spec from codebase exploration
