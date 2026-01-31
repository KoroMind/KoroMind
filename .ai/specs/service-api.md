---
id: SVC-001
type: service
status: active
severity: high
issue: null
validated: 2026-01-29
---

# REST API Service

## What
- Programmatic access to KoroMind for messages, sessions, settings
- Single-tenant by default, API key authentication

## Why
- Enable integrations beyond Telegram (web apps, other bots)
- Headless access for automation

## How
- FastAPI app: `src/koro/api/app.py`
- Auth middleware: `src/koro/api/middleware.py`
- Routes delegate to `koro.core.brain`

### Endpoints
| Route | Method | Purpose |
|-------|--------|---------|
| `/messages` | POST | Process text/voice, return response + audio |
| `/sessions` | GET/POST | List or create sessions |
| `/sessions/current` | GET/PUT | Get or switch current session |
| `/settings` | GET/PUT | User preferences |
| `/health` | GET | Health check (public) |

### Config
- `KOROMIND_API_KEY` - Required for auth
- `KOROMIND_ALLOW_NO_AUTH` - Dev bypass
- `KOROMIND_CORS_ORIGINS` - Allowlist

### Security
- User ID derived from API key (SHA-256), not header
- Rate limiting on all non-public endpoints
- CORS allowlist, no wildcard with credentials

## Test
- Auth rejects invalid/missing key
- Rate limit triggers after threshold
- User ID stable across requests with same key

## Changelog

### 2026-01-29
- Refactored to new spec format

### 2026-01-28
- Added API key auth, CORS, rate limiting
