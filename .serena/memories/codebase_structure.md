# Rough codebase structure
- bot.py: main Telegram bot + Claude Agent SDK orchestration.
- prompts/: persona/system prompts (e.g., prompts/koro.md).
- tests/: test suite (test_elevenlabs.py, test_integration.py).
- docker/: docker env example (koro.env.example).
- docker-compose.yml, Dockerfile: container deployment.
- .env.example, settings.example.json: local env + permissions template.
- requirements.txt: Python deps.
