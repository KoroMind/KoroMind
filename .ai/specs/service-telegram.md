---
id: SVC-005
type: service
status: active
severity: high
issue: 39
validated: 2026-02-06
---

# Telegram Interface

## What
- Telegram bot providing voice and text access to KoroMind
- Commands, inline keyboards for settings/approvals, voice messages
- Primary user interface for the assistant

## Why
- Natural mobile-first experience
- Voice messages enable hands-free interaction
- Approval mode UI with inline buttons

## How
- Core: `src/koro/interfaces/telegram/bot.py` - initialization
- Handlers: `src/koro/interfaces/telegram/handlers/` - commands, messages, callbacks

### Commands
| Command | Purpose |
|---------|---------|
| `/new [name]` | Stage a new session (optional name) |
| `/sessions` | List sessions |
| `/switch <name|id>` | Switch session by name or id prefix |
| `/model [name]` | Show or set model |
| `/settings` | Settings menu (inline keyboard) |
| `/status` | Current session info |
| `/health` | System health check |
| `/setup` | Configure credentials |

### Session UX Semantics
- `/new [name]` clears current session and stages optional name for the next Claude session ID
- `/sessions` shows recent sessions with `(current)` marker and optional pending new-session label
- `/switch` resolves in this order:
  - exact name match
  - unique name prefix
  - unique id prefix
- Ambiguous matches return a disambiguation message

### Message Handling
- **Voice**: Transcribe via VoiceEngine → Brain → TTS response
- **Text**: Direct to Brain → text response (+ audio if enabled)

### Approval Mode
- `handle_approval_callback()` shows inline keyboard per tool call
- Pending approvals stored in-memory (5min timeout)
- Pattern: `approve_<id>` / `reject_<id>`

### Access Control
- `ALLOWED_CHAT_ID` - Restrict to specific chat
- `TOPIC_ID` - Filter to specific forum topic (optional)

### Config
- `TELEGRAM_BOT_TOKEN` - Required
- `PERSONA_NAME` - Display name in logs
- `SYSTEM_PROMPT_FILE` - Custom system prompt path

## Test
- Voice message returns audio response
- Approval buttons trigger tool execution/rejection
- Unknown chat ID rejected
- Commands work in correct topic only

## Changelog

### 2026-02-06
- Updated session command semantics and matching rules (`/new`, `/sessions`, `/switch`)
- Session listings now include explicit current marker and pending new-session visibility

### 2026-01-29
- Initial spec from codebase exploration
### 2026-02-05
- Expand command list, add /model, delete /start, improve UX
