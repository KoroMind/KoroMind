---
id: SEC-001
type: security
status: open
severity: critical
location: src/koro/api/routes/messages.py:52-103
issue: null
validated: 2026-01-28
---

# Session Hijacking in Messages API

## Problem
- `/messages` accepts any `session_id` without ownership validation
- Attacker can guess session IDs and access other users' conversations
- `sessions.py:124-132` validates ownership, but `messages.py` does not

## Solution
- Add ownership check before `brain.process_message()`
- Pattern: `if session_id not in user's sessions → 403`
- Reference implementation: `sessions.py:124-132`

## Test
- User A creates session S1
- User B calls `POST /messages` with `session_id=S1`
- Expected: 403 Forbidden
