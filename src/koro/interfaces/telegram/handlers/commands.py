"""Telegram command handlers."""

import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from koro.auth import check_claude_auth, load_credentials, save_credentials
from koro.claude import get_claude_client
from koro.config import ALLOWED_CHAT_ID, SANDBOX_DIR
from koro.interfaces.telegram.handlers.utils import debug, should_handle_message
from koro.state import get_state_manager
from koro.voice import get_voice_engine


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    await update.message.reply_text(
        "KoroMind\n\n"
        "Send me a voice message and I'll think with you.\n\n"
        "Commands:\n"
        "/setup - Configure API credentials\n"
        "/new [name] - Start new session\n"
        "/continue - Resume last session\n"
        "/sessions - List all sessions\n"
        "/switch <name> - Switch to session\n"
        "/status - Current session info\n"
        "/settings - Configure audio and voice speed"
    )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new command - start new session."""
    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    user_id = update.effective_user.id
    state_manager = get_state_manager()

    session_name = " ".join(context.args) if context.args else None
    await state_manager.clear_current_session(str(user_id))

    if session_name:
        await update.message.reply_text(f"New session started: {session_name}")
    else:
        await update.message.reply_text(
            "New session started. Send a voice message to begin."
        )


async def cmd_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /continue command - resume last session."""
    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    user_id = update.effective_user.id
    state_manager = get_state_manager()
    state = state_manager.get_user_state(user_id)

    if state["current_session"]:
        await update.message.reply_text(
            f"Continuing session: {state['current_session'][:8]}..."
        )
    else:
        await update.message.reply_text(
            "No previous session. Send a voice message to start."
        )


async def cmd_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sessions command - list all sessions."""
    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    user_id = update.effective_user.id
    state_manager = get_state_manager()
    state = state_manager.get_user_state(user_id)

    if not state["sessions"]:
        await update.message.reply_text("No sessions yet.")
        return

    msg = "Sessions:\n"
    for i, sess in enumerate(state["sessions"][-10:], 1):
        current = " (current)" if sess == state["current_session"] else ""
        msg += f"{i}. {sess[:9]}...{current}\n"

    await update.message.reply_text(msg)


async def cmd_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /switch command - switch to specific session."""
    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    if not context.args:
        await update.message.reply_text("Usage: /switch <session_id>")
        return

    user_id = update.effective_user.id
    state_manager = get_state_manager()
    state = state_manager.get_user_state(user_id)
    session_id = context.args[0]

    matches = [s for s in state["sessions"] if s.startswith(session_id)]

    if len(matches) == 1:
        await state_manager.update_session(str(user_id), matches[0])
        await update.message.reply_text(f"Switched to session: {matches[0][:8]}...")
    elif len(matches) > 1:
        await update.message.reply_text("Multiple matches. Be more specific.")
    else:
        await update.message.reply_text(f"Session not found: {session_id}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show current session info."""
    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    user_id = update.effective_user.id
    state_manager = get_state_manager()
    state = state_manager.get_user_state(user_id)

    if state["current_session"]:
        await update.message.reply_text(
            f"Current session: {state['current_session'][:8]}...\n"
            f"Total sessions: {len(state['sessions'])}"
        )
    else:
        await update.message.reply_text(
            "No active session. Send a voice message or /new to start."
        )


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /health command - check all systems."""
    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    from pathlib import Path

    status = []
    status.append("=== Health Check ===\n")

    # Check ElevenLabs
    voice_engine = get_voice_engine()
    el_ok, el_msg = voice_engine.health_check()
    status.append(f"ElevenLabs TTS: {el_msg}")

    # Check Claude
    claude_client = get_claude_client()
    cl_ok, cl_msg = claude_client.health_check()
    status.append(f"Claude Code: {cl_msg}")

    # Session info
    user_id = update.effective_user.id
    state_manager = get_state_manager()
    state = state_manager.get_user_state(user_id)
    status.append(f"\nSessions: {len(state['sessions'])}")
    status.append(
        f"Current: {state['current_session'][:8] if state['current_session'] else 'None'}..."
    )

    # Sandbox info
    status.append(f"\nSandbox: {SANDBOX_DIR}")
    status.append(f"Sandbox exists: {Path(SANDBOX_DIR).exists()}")

    # Chat info
    status.append(f"\nChat ID: {update.effective_chat.id}")
    status.append(f"Topic ID: {update.message.message_thread_id or 'None'}")
    status.append(f"User ID: {update.effective_user.id}")

    await update.message.reply_text("\n".join(status))


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command - show settings menu."""
    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    user_id = update.effective_user.id
    state_manager = get_state_manager()
    settings = state_manager.get_user_settings(user_id)

    audio_status = "ON" if settings["audio_enabled"] else "OFF"
    speed = settings["voice_speed"]
    mode = settings.get("mode", "go_all")
    mode_display = "Go All" if mode == "go_all" else "Approve"
    watch_status = "ON" if settings.get("watch_enabled", False) else "OFF"

    message = (
        f"Settings:\n\n"
        f"Mode: {mode_display}\n"
        f"Watch: {watch_status}\n"
        f"Audio: {audio_status}\n"
        f"Voice Speed: {speed}x"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                f"Mode: {mode_display}", callback_data="setting_mode_toggle"
            ),
            InlineKeyboardButton(
                f"Watch: {watch_status}", callback_data="setting_watch_toggle"
            ),
        ],
        [
            InlineKeyboardButton(
                f"Audio: {audio_status}", callback_data="setting_audio_toggle"
            )
        ],
        [
            InlineKeyboardButton("0.8x", callback_data="setting_speed_0.8"),
            InlineKeyboardButton("0.9x", callback_data="setting_speed_0.9"),
            InlineKeyboardButton("1.0x", callback_data="setting_speed_1.0"),
            InlineKeyboardButton("1.1x", callback_data="setting_speed_1.1"),
            InlineKeyboardButton("1.2x", callback_data="setting_speed_1.2"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(message, reply_markup=reply_markup)


async def cmd_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setup command - show API credentials status."""
    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    creds = load_credentials()
    claude_configured, claude_method = check_claude_auth()

    if claude_configured:
        if claude_method == "api_key":
            claude_status = "Set (env)"
        elif claude_method == "saved_token":
            claude_status = "Set (saved)" if creds.get("claude_token") else "Set (env)"
        elif claude_method == "oauth":
            claude_status = "Set (oauth)"
        else:
            claude_status = "Set"
    else:
        claude_status = "Not set"

    elevenlabs_env = os.getenv("ELEVENLABS_API_KEY")
    if elevenlabs_env:
        elevenlabs_status = "Set (env)"
    elif creds.get("elevenlabs_key"):
        elevenlabs_status = "Set (saved)"
    else:
        elevenlabs_status = "Not set"

    missing_claude = not claude_configured
    missing_elevenlabs = not (elevenlabs_env or creds.get("elevenlabs_key"))

    message_lines = [
        "**API Credentials Status**",
        "",
        f"Claude Token: {claude_status}",
        f"ElevenLabs Key: {elevenlabs_status}",
    ]

    if missing_claude or missing_elevenlabs:
        message_lines.extend(["", "**To configure:**"])
        if missing_claude:
            message_lines.append("`/claude_token <token>` - Set Claude token")
        if missing_elevenlabs:
            message_lines.append("`/elevenlabs_key <key>` - Set ElevenLabs key")
        if missing_claude:
            message_lines.extend(
                ["", "_Get Claude token by running `claude setup-token` in terminal._"]
            )
        message_lines.append("_Credential messages are deleted for security._")
    else:
        message_lines.extend(["", "Everything is ready to go."])

    await update.message.reply_text("\n".join(message_lines), parse_mode="Markdown")


async def cmd_claude_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claude_token command - set Claude OAuth token."""
    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    thread_id = update.message.message_thread_id
    try:
        await update.message.delete()
    except Exception as e:
        debug(f"Failed to delete message in cmd_claude_token: {e}")

    if not context.args:
        await update.effective_chat.send_message(
            "Usage: `/claude_token <token>`\n\n"
            "Get token by running `claude setup-token` in your terminal.",
            message_thread_id=thread_id,
            parse_mode="Markdown",
        )
        return

    token = " ".join(context.args).strip()

    if not token.startswith("sk-ant-"):
        await update.effective_chat.send_message(
            "Invalid token format. Token should start with `sk-ant-`",
            message_thread_id=thread_id,
            parse_mode="Markdown",
        )
        return

    creds = load_credentials()
    creds["claude_token"] = token
    save_credentials(creds)

    os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = token

    await update.effective_chat.send_message(
        "Claude token saved and applied!", message_thread_id=thread_id
    )


async def cmd_elevenlabs_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /elevenlabs_key command - set ElevenLabs API key."""
    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    thread_id = update.message.message_thread_id
    try:
        await update.message.delete()
    except Exception as e:
        debug(f"Failed to delete message in cmd_elevenlabs_key: {e}")

    if not context.args:
        await update.effective_chat.send_message(
            "Usage: `/elevenlabs_key <key>`\n\n"
            "Get key from elevenlabs.io/app/settings/api-keys",
            message_thread_id=thread_id,
            parse_mode="Markdown",
        )
        return

    key = " ".join(context.args).strip()

    if len(key) < 20:
        await update.effective_chat.send_message(
            "Invalid key format. Key seems too short.", message_thread_id=thread_id
        )
        return

    creds = load_credentials()
    creds["elevenlabs_key"] = key
    save_credentials(creds)

    # Update voice engine
    voice_engine = get_voice_engine()
    voice_engine.update_api_key(key)

    await update.effective_chat.send_message(
        "ElevenLabs API key saved and applied!", message_thread_id=thread_id
    )
