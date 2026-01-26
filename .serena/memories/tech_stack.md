# Tech stack
- Language/runtime: Python 3.12+ (Docker image uses Python 3.11 but compatible per Dockerfile notes).
- Core libs: python-telegram-bot, elevenlabs, python-dotenv, claude-agent-sdk.
- Deployment: Docker / docker-compose; Node.js used in Docker image to install Claude Code CLI.
- External services: Telegram Bot API, ElevenLabs, Anthropic/Claude authentication (API key or OAuth credentials).
