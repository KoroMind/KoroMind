# KoroMind project overview
- Purpose: Voice-first Telegram bot that connects ElevenLabs STT/TTS with the Claude Agent SDK for agentic tool execution.
- Primary entrypoint: bot.py (Telegram bot + agent loop + voice pipeline).
- Key concepts: sessions state, user settings, approve/go-all modes, watch mode, sandboxed tool execution.
- Platform: macOS (Darwin) dev, Python-based app with optional Docker deployment.
