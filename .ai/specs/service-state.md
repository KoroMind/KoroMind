---
id: SVC-003
type: service
status: active
severity: high
issue: 55
validated: 2026-02-16
---

# State Management Service

## What
- SQLite-backed persistence for sessions, settings, and memory
- Single source of truth for user data across all interfaces
- Auto-migrates legacy JSON files on first run

## Why
- Sessions carry Claude conversation context
- Settings persist user preferences (mode, audio, speed)
- Memory enables long-term recall (future feature)

## How
- Core: `src/koro/core/state.py` - `StateManager` class
- Database: `~/.koromind/koromind.db` (configurable via `KOROMIND_DATA_DIR`)

### Schema
```sql
sessions (id, user_id, created_at, last_active, is_current, name)
settings (user_id, mode, audio_enabled, voice_speed, watch_enabled, model, stt_language, pending_session_name)
memory   (user_id, key, value, created_at, updated_at)
```

### Key Operations
| Operation | Method | Notes |
|-----------|--------|-------|
| Get current session | `get_current_session()` | Returns current or None |
| Switch session | `set_current_session()` | Updates is_current flag |
| List sessions | `get_sessions()` | Max 100 per user (FIFO eviction) |
| Typed session state | `get_session_state()` | Returns `UserSessionState` (Pydantic) |
| Stage next session name | `set_pending_session_name()` | Consumed on next created session |
| Get/update settings | `get_settings()`, `update_settings()` | Returns defaults if unset |

### Session Model
- Each user has multiple sessions (max 100, oldest evicted)
- One session is `is_current=True` at a time
- Session ID = Claude conversation ID (context continuity)
- Optional `name` field for user-facing labels
- `pending_session_name` tracks `/new [name]` intent before Claude issues next session ID

### Typed Session State
- `UserSessionState` includes:
  - `current_session_id: str | None`
  - `sessions: list[SessionStateItem]` where each item has `id`, optional `name`, and `is_current`
  - `pending_session_name: str | None`
- Legacy `get_user_state()` remains as a compatibility shim and is still deprecated

### Settings Model
- `mode`: "go_all" (auto-execute) or "approve" (human confirmation)
- `audio_enabled`: TTS on/off
- `voice_speed`: 0.7-1.2 range
- `watch_enabled`: Stream tool calls to UI
- `stt_language`: STT language code (`auto` default, configurable per user)

## Test
- New user gets default settings
- Session switch updates is_current correctly
- 101st session evicts oldest
- Settings persist across restarts

## Changelog

### 2026-02-16
- Added `stt_language` column to `settings` table with schema migration
- Added JSON migration support for `stt_language` with safe fallback to default
- Added validation/normalization for STT language updates in `update_settings()`

### 2026-02-06
- Linked spec to issue #55
- Added typed session state API (`UserSessionState`) for interface consumers
- Added persisted session names and pending-session-name staging support

### 2026-01-29
- Initial spec from codebase exploration
