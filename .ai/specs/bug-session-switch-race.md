---
id: BUG-001
type: bug
status: open
severity: high
location: src/koro/core/brain.py:253-255
issue: null
validated: 2026-01-28
---

# Race Condition in Session Switching

## Problem
- No locking on `switch_session()`
- Concurrent switch requests corrupt state
- Grep confirms: no `Lock()` or mutex in codebase

## Solution
- Option A: Optimistic concurrency (version column)
- Option B: Database-level `SELECT FOR UPDATE`
- MVP: Add `version` column, reject stale updates

## Test
- Concurrent `switch_session(A)` and `switch_session(B)`
- Expected: One succeeds, state is consistent (A or B, not corrupted)
