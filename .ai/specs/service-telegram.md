---
id: SVC-005
type: service
status: active
severity: high
issue: null
validated: 2026-01-29
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
| `/start` | Welcome message |
| `/new` | Create new session |
| `/sessions` | List sessions |
| `/switch <id>` | Switch session |
| `/model [name]` | Show or set model |
| `/settings` | Settings menu (inline keyboard) |
| `/status` | Current session info |
| `/health` | System health check |
| `/setup` | Configure credentials |

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

### 2026-01-29
- Initial spec from codebase exploration
### 2026-02-05
- Expand command list, add /help and /model, improve session switching UX
