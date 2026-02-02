"""Telegram bot initialization and runner."""

import asyncio
import logging
from pathlib import Path

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from koro.auth import apply_saved_credentials, check_claude_auth
from koro.config import (
    ALLOWED_CHAT_ID,
    CLAUDE_WORKING_DIR,
    ELEVENLABS_VOICE_ID,
    PERSONA_NAME,
    SANDBOX_DIR,
    SYSTEM_PROMPT_FILE,
    TELEGRAM_BOT_TOKEN,
    TOPIC_ID,
    setup_logging,
    validate_environment,
)
from koro.interfaces.telegram.handlers import (
    cmd_claude_token,
    cmd_continue,
    cmd_elevenlabs_key,
    cmd_health,
    cmd_new,
    cmd_sessions,
    cmd_settings,
    cmd_setup,
    cmd_start,
    cmd_status,
    cmd_switch,
    handle_approval_callback,
    handle_settings_callback,
    handle_text,
    handle_voice,
)
from koro.interfaces.telegram.handlers.messages import cleanup_stale_approvals
from koro.interfaces.telegram.handlers.utils import debug
from koro.state import get_state_manager
from koro.voice import get_voice_engine

logger = logging.getLogger(__name__)


async def _periodic_approval_cleanup() -> None:
    while True:
        await asyncio.sleep(60)
        cleanup_stale_approvals()


async def error_handler(update, context):
    """
    Handle errors in the telegram bot.

    Args:
        update: Telegram update that caused the error
        context: Telegram context containing error info
    """
    logger.error(f"Exception while handling an update: {context.error}")
    if update and update.effective_chat:
        try:
            await update.effective_chat.send_message(
                "An error occurred while processing your request."
            )
        except Exception as exc:
            logger.warning("Failed to send Telegram error message: %s", exc)


def run_telegram_bot():
    """Run the Telegram bot."""
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
        print(
            "WARNING: Claude authentication not configured - bot will start but Claude won't work"
        )
        print(
            "         Use /setup in Telegram to configure, or set ANTHROPIC_API_KEY in env"
        )
    else:
        print(f"Claude auth: {auth_method}")

    # Initialize state (ensures database is created)
    get_state_manager()

    # Setup logging
    setup_logging()

    # Build application with concurrent updates for approve mode
    app = (
        ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).concurrent_updates(True).build()
    )

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
    app.add_handler(
        CallbackQueryHandler(handle_approval_callback, pattern="^(approve_|reject_)")
    )

    # Register message handlers
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Register error handler
    app.add_error_handler(error_handler)

    # Periodic cleanup for pending approvals
    app.create_task(_periodic_approval_cleanup())

    # Ensure sandbox exists
    Path(SANDBOX_DIR).mkdir(parents=True, exist_ok=True)

    # Startup info
    debug("Bot starting...")
    debug(f"Persona: {PERSONA_NAME}")
    debug(f"Voice ID: {ELEVENLABS_VOICE_ID}")
    debug("TTS: eleven_turbo_v2_5 with expressive settings")
    debug(f"Sandbox: {SANDBOX_DIR}")
    debug(f"Read access: {CLAUDE_WORKING_DIR}")
    debug(f"Chat ID: {ALLOWED_CHAT_ID}")
    debug(f"Topic ID: {TOPIC_ID or 'ALL (no filter)'}")
    debug(f"System prompt: {SYSTEM_PROMPT_FILE or 'default'}")
    print(f"{PERSONA_NAME} is ready. Waiting for messages...")

    # Run bot
    app.run_polling(
        drop_pending_updates=True, allowed_updates=["message", "callback_query"]
    )


if __name__ == "__main__":
    run_telegram_bot()
