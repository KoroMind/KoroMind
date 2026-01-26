"""Main entry point for KoroMind bot."""

from pathlib import Path
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from .config import (
    TELEGRAM_BOT_TOKEN,
    SANDBOX_DIR,
    PERSONA_NAME,
    ELEVENLABS_VOICE_ID,
    SYSTEM_PROMPT_FILE,
    ALLOWED_CHAT_ID,
    TOPIC_ID,
    CLAUDE_WORKING_DIR,
    validate_environment,
    setup_logging,
)
from .auth import check_claude_auth, apply_saved_credentials
from .state import get_state_manager
from .voice import get_voice_engine
from .handlers import (
    cmd_start,
    cmd_new,
    cmd_continue,
    cmd_sessions,
    cmd_switch,
    cmd_status,
    cmd_health,
    cmd_settings,
    cmd_setup,
    cmd_claude_token,
    cmd_elevenlabs_key,
    handle_voice,
    handle_text,
    handle_settings_callback,
    handle_approval_callback,
)
from .handlers.utils import debug


def main():
    """Main entry point."""
    # Apply any saved credentials first
    claude_token, elevenlabs_key = apply_saved_credentials()
    if claude_token:
        debug("Applied saved Claude token")
    if elevenlabs_key:
        voice_engine = get_voice_engine()
        voice_engine.update_api_key(elevenlabs_key)
        debug("Applied saved ElevenLabs key")

    # Validate environment
    is_valid, message = validate_environment()
    if not is_valid:
        print(f"ERROR: {message}")
        print("\nCopy .env.example to .env and fill in the values.")
        exit(1)
    if message:
        print(f"WARNING: {message}")

    # Check Claude auth
    is_auth, auth_method = check_claude_auth()
    if not is_auth:
        print("WARNING: Claude authentication not configured - bot will start but Claude won't work")
        print("         Use /setup in Telegram to configure, or set ANTHROPIC_API_KEY in env")
    else:
        print(f"Claude auth: {auth_method}")

    # Initialize state
    state_manager = get_state_manager()
    state_manager.load()

    # Setup logging
    setup_logging()

    # Build application with concurrent updates for approve mode
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).concurrent_updates(True).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("continue", cmd_continue))
    app.add_handler(CommandHandler("sessions", cmd_sessions))
    app.add_handler(CommandHandler("switch", cmd_switch))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("setup", cmd_setup))
    app.add_handler(CommandHandler("claude_token", cmd_claude_token))
    app.add_handler(CommandHandler("elevenlabs_key", cmd_elevenlabs_key))

    # Register callback handlers
    app.add_handler(CallbackQueryHandler(handle_settings_callback, pattern="^setting_"))
    app.add_handler(CallbackQueryHandler(handle_approval_callback, pattern="^(approve_|reject_)"))

    # Register message handlers
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Ensure sandbox exists
    Path(SANDBOX_DIR).mkdir(parents=True, exist_ok=True)

    # Startup info
    debug("Bot starting...")
    debug(f"Persona: {PERSONA_NAME}")
    debug(f"Voice ID: {ELEVENLABS_VOICE_ID}")
    debug(f"TTS: eleven_turbo_v2_5 with expressive settings")
    debug(f"Sandbox: {SANDBOX_DIR}")
    debug(f"Read access: {CLAUDE_WORKING_DIR}")
    debug(f"Chat ID: {ALLOWED_CHAT_ID}")
    debug(f"Topic ID: {TOPIC_ID or 'ALL (no filter)'}")
    debug(f"System prompt: {SYSTEM_PROMPT_FILE or 'default'}")
    print(f"{PERSONA_NAME} is ready. Waiting for messages...")

    # Run bot
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"]
    )


if __name__ == "__main__":
    main()
