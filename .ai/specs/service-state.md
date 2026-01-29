---
id: SVC-003
type: service
status: active
severity: high
issue: null
validated: 2026-01-29
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
sessions (id, user_id, created_at, last_active, is_current)
settings (user_id, mode, audio_enabled, voice_speed, watch_enabled)
memory   (user_id, key, value, created_at, updated_at)
```

### Key Operations
| Operation | Method | Notes |
|-----------|--------|-------|
| Get/create session | `get_current_session()` | Creates if none exists |
| Switch session | `set_current_session()` | Updates is_current flag |
| List sessions | `get_user_sessions()` | Max 100 per user (FIFO eviction) |
| Get/update settings | `get_settings()`, `update_settings()` | Returns defaults if unset |

### Session Model
- Each user has multiple sessions (max 100, oldest evicted)
- One session is `is_current=True` at a time
- Session ID = Claude conversation ID (context continuity)

### Settings Model
- `mode`: "go_all" (auto-execute) or "approve" (human confirmation)
- `audio_enabled`: TTS on/off
- `voice_speed`: 0.7-1.2 range
- `watch_enabled`: Stream tool calls to UI

## Test
- New user gets default settings
- Session switch updates is_current correctly
- 101st session evicts oldest
- Settings persist across restarts

## Changelog

### 2026-01-29
- Initial spec from codebase exploration
