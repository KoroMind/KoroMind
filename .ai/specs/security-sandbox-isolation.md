---
id: SEC-002
type: security
status: open
severity: critical
location: src/koro/core/config.py:59-61
issue: null
validated: 2026-01-28
---

# Per-User Sandbox Isolation

## Problem
- `SANDBOX_DIR` is global, shared by all users
- User A's Claude can read/modify User B's files
- Dockerfile:65 sets single `/home/claude/sandbox`

## Solution
- Dynamic per-user paths: `~/.koromind/sandboxes/{user_id}/`
- Pass user-specific sandbox to `ClaudeAgentOptions`
- Auto-create on first request, permissions 0700

## Test
- User A creates `secret.txt` in sandbox
- User B asks Claude to read User A's file
- Expected: Access denied
