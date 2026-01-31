---
id: SVC-006
type: service
status: active
severity: low
issue: 35
validated: 2026-02-01
---

# CLI Interface

## What
- Terminal REPL for KoroMind using Rich and Typer
- Text-only interface for local development/testing
- Supports vault configuration and debug logging

## Why
- Quick testing without Telegram setup
- Debugging and development workflows
- Headless server access

## How
- Core: `src/koro/interfaces/cli/app.py`
- Framework: Typer (CLI) + Rich (TUI)

### Entry Points
```bash
koro-cli chat                          # Start REPL (default vault)
koro-cli chat --vault ~/.koromind      # Explicit vault
koro-cli chat --debug                  # Enable debug logging
koro-cli health --vault ./my-vault     # Health check with vault
koro-cli sessions --user <id>
```

### CLI Options
| Option | Purpose |
|--------|---------|
| `--vault, -v` | Path to vault directory |
| `--debug, -d` | Enable debug logging |
| `--user, -u` | User ID (default: cli-user) |

### Vault Resolution Order
1. `--vault PATH` (explicit)
2. `$KOROMIND_VAULT` (env var)
3. `~/.koromind` (default)

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

### 2026-02-01
- Added --vault option for vault configuration
- Added --debug option for debug logging
- Health check now shows vault status
- Welcome message shows vault path and model

### 2026-01-29
- Initial spec from codebase exploration
