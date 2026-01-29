---
id: FEA-002
type: feature
status: draft
severity: critical
issue: null
validated: null
---

# Multi-Tenancy

## What
- Support multiple users with strong privacy guarantees
- Encrypted storage, per-user sandboxes, device locking

## Why
- Required for paid service offering
- Current state: shared DB, global sandbox, no encryption (score: 1.5/10)

## How

### Architecture
```
Client → API Gateway → Brain → Worker Pool → Claude API
                         ↓
                 PostgreSQL (sessions, settings)
                         ↓
                 Encrypted Storage (memories)
                         ↓
                 Per-User Sandboxes (/sandbox/{user_id}/)
```

### Phases
1. **Security fixes**: Session ownership, sandbox isolation, race conditions
2. **Foundation**: Token tracking, tenant/device tables, device locking
3. **Encryption**: PIN-based key derivation, AES-256-GCM, zero-knowledge
4. **Scale**: PostgreSQL, Redis rate limiting, API key rotation, worker pool

### Key Decisions
- Worker pool: Pre-warmed containers, no cold start
- Session model: One device at a time, force-close on new device
- Encryption: User PIN → key derivation, server can't read data
- API keys: Rotate ~3 Anthropic Max accounts for ~1000 users

### Data Model
- `tenants` - Organization/account
- `devices` - User devices with fingerprint
- `telemetry` - Token usage per session
- `memories` - Encrypted user data

## Test
- User A cannot access User B's sessions/files
- Device takeover closes existing session
- Server restart preserves encrypted data integrity

## Changelog

### 2026-01-29
- Converted from issue draft to spec format
