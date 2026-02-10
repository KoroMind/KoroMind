---
id: BUG-002
type: bug
status: open
severity: high
location: src/koro/core/brain.py:71-171
issue: null
validated: 2026-01-28
---

# Race Condition in Concurrent Messages

## Problem
- No locking on `process_message()` per session
- Two messages to same session: both read stale history
- Last write wins, first message lost

## Solution
- Per-session `asyncio.Lock()` in Brain
- `WeakValueDictionary` for auto-cleanup
- Lock acquired before processing, released after

## Test
- Send "Hello" and "How are you?" simultaneously to same session
- Expected: Both messages in history, none lost
