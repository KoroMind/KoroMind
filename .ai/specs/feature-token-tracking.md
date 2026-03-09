---
id: FEAT-001
type: feature
status: open
severity: high
location: src/koro/core/brain.py:143-151
issue: null
validated: 2026-01-28
---

# Token Usage Tracking

## Goal
- Track Claude token consumption per request
- Track ElevenLabs TTS characters
- Enable billing, quotas, analytics

## Solution
- New `usage` table: user_id, session_id, input_tokens, output_tokens, tts_chars
- Extract tokens from Claude SDK response metadata
- Record after each `process_message()` call

## Data
```sql
CREATE TABLE usage (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    timestamp TEXT DEFAULT (datetime('now')),
    input_tokens INTEGER,
    output_tokens INTEGER,
    tts_characters INTEGER
);
```

## Test
- Send message, query usage table
- Expected: Row with token counts > 0
