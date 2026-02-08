---
id: INF-001
type: service
status: active
severity: medium
issue: null
validated: 2026-01-29
---

# Docker Deployment

## What
- Containerized deployment of KoroMind Telegram bot
- Persistent volumes for state, sandbox, and credentials
- Health checks and auto-restart

## Why
- Reproducible deployment
- Isolated environment
- Easy hosting on any Docker-capable server

## How
- `Dockerfile` - Python 3.12 image, uv for deps
- `docker-compose.yml` - Service definition

### Volumes
| Volume | Path in Container | Purpose |
|--------|-------------------|---------|
| `koro-state` | `/home/claude/state` | SQLite DB (sessions, settings) |
| `koro-sandbox` | `/home/claude/sandbox` | Claude write access |
| `koro-claude-config` | `/home/claude/.claude` | Claude credentials |
| `./src/prompts` | `/home/claude/app/src/prompts` | System prompts (read-only) |

### Quick Start
```bash
cp .env.example .env  # Fill in API keys
docker compose up -d --build
docker compose logs -f koro
```

### Health Check
- Command: `pgrep -f "python.*bot.py"`
- Interval: 30s, timeout: 10s, 3 retries
- Start period: 40s (allow initialization)

### Auth Options
1. **API Key**: Set `ANTHROPIC_API_KEY` in `.env`
2. **Subscription**: Mount `~/.claude/.credentials.json` (after `claude /login` on host)

### Config
All config via `.env` file (see `.env.example`):
- `TELEGRAM_BOT_TOKEN`, `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`
- `ALLOWED_CHAT_ID`, `TOPIC_ID`, `PERSONA_NAME`

## Test
- Container starts and stays healthy
- State persists across restarts
- Sandbox isolated from host
- Logs accessible via `docker compose logs`

## Changelog

### 2026-01-29
- Initial spec from codebase exploration
