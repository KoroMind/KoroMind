---
id: SVC-005
type: service
status: active
severity: high
issue: 39
validated: 2026-02-11
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
- Telegram is a **thin connector**: translates Telegram events into `Brain.process_message()` calls

### Message Handling
- Handlers call `get_brain().process_message()` — same pattern as REST API and CLI
- **Text**: rate limit → `brain.process_message(content=text, content_type=TEXT)` → send `response.text` + optional `response.audio`
- **Voice**: rate limit → download bytes → `brain.process_message(content=bytes, content_type=VOICE)` → same response handling
- Brain handles all orchestration internally (STT, Claude SDK, session update, TTS)
- Handlers read settings from `brain.state_manager.get_settings()` to pass mode/audio/speed params
- Errors show generic "Something went wrong" to user; full error logged server-side via `_send_safe_error()`

### Brain Callbacks
- `_build_brain_callbacks()` creates a `BrainCallbacks` with Telegram-specific closures:
  - `on_tool_use` — sends tool usage as reply messages (watch mode only)
  - `on_tool_approval` — shows approve/reject inline buttons, blocks on `asyncio.Event` (approve mode only)
- `handle_approval_callback()` in `callbacks.py` resolves button presses → sets event
- Pending approvals (`PendingApproval` dataclass) stored in-memory with 5min timeout, FIFO eviction at 100 max
- `on_tool_approval` wrapped in try/except — Telegram errors return `PermissionResultDeny`, never abort Brain

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

### Access Control
- `ALLOWED_CHAT_ID` - Restrict to specific chat
- `TOPIC_ID` - Filter to specific forum topic (optional)

### Config
- `TELEGRAM_BOT_TOKEN` - Required
- `PERSONA_NAME` - Display name in logs
- `SYSTEM_PROMPT_FILE` - Custom system prompt path

## Test
- Text message routes through Brain with correct content + content_type
- Voice message passes raw bytes to Brain (Brain handles transcription)
- Brain returning audio triggers `reply_voice`
- Brain exception shows safe error message, not raw traceback
- Approval buttons trigger tool execution/rejection
- Unknown chat ID rejected
- Commands work in correct topic only

## Changelog

### 2026-02-11 (Review fixes)
- Callback isolation: `on_tool_approval` wrapped in try/except
- `Session` migrated to frozen Pydantic BaseModel, `PendingApproval` to dataclass
- `debug()` wrapper removed entirely — all callers use `logger.debug()` directly
- `get_session_by_name` made deterministic with `ORDER BY last_active DESC LIMIT 1`
- `.env.test` removed from git history, `.env.*` added to `.gitignore`
- E2E tests filter by KoroMind bot username

### 2026-02-10 (Issue #39)
- Handlers now route through `Brain.process_message()` instead of calling `ClaudeClient.query()` directly
- Deleted `_call_claude_with_settings()` — logic split between Brain and `_build_brain_callbacks()`
- Added `_send_safe_error()` — generic error messages to user, full traceback logged
- Typing indicator loop hardened against `TelegramError`

### 2026-02-06
- Updated session command semantics and matching rules (`/new`, `/sessions`, `/switch`)
- Session listings now include explicit current marker and pending new-session visibility

### 2026-02-05
- Expand command list, add /model, delete /start, improve UX

### 2026-01-29
- Initial spec from codebase exploration
