"""Telegram command handlers."""

import os

from telegram import (
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
    User,
)
from telegram.ext import ContextTypes

from koro.auth import check_claude_auth, load_credentials, save_credentials
from koro.claude import get_claude_client
from koro.config import ALLOWED_CHAT_ID, SANDBOX_DIR
from koro.core.types import SessionStateItem, UserSessionState
from koro.interfaces.telegram.handlers.utils import debug, should_handle_message
from koro.state import get_state_manager
from koro.voice import get_voice_engine


def _format_command_help() -> str:
    sections = [
        (
            "General",
            [
                ("/help", "Show command list"),
            ],
        ),
        (
            "Sessions",
            [
                ("/new [name]", "Start new session"),
                ("/continue", "Resume last session"),
                ("/sessions", "List recent sessions"),
                ("/switch <name|id>", "Switch to session"),
                ("/status", "Current session info"),
            ],
        ),
        (
            "Settings",
            [
                ("/settings", "Configure mode, audio, and voice speed"),
                ("/model [name]", "Show or set Claude model"),
            ],
        ),
        (
            "Credentials",
            [
                ("/setup", "Show credential status"),
                ("/claude_token <token>", "Set Claude token"),
                ("/elevenlabs_key <key>", "Set ElevenLabs key"),
            ],
        ),
        (
            "Diagnostics",
            [
                ("/health", "Run health checks"),
            ],
        ),
    ]

    lines = ["Commands:"]
    for section, items in sections:
        lines.append("")
        lines.append(f"{section}:")
        for command, desc in items:
            lines.append(f"{command} - {desc}")
    return "\n".join(lines)


def _session_label(session: SessionStateItem) -> str:
    """Human-friendly display label for a session."""
    short_id = session.id[:8]
    return session.name if session.name else short_id


def _session_button_label(session: SessionStateItem) -> str:
    """Compact label used in session picker buttons."""
    short_id = session.id[:8]
    if session.name:
        return f"{session.name} ({short_id})"
    return short_id


def _switch_picker_markup(
    sessions: list[SessionStateItem], limit: int = 10
) -> InlineKeyboardMarkup:
    """Build inline keyboard for session selection."""
    rows = [
        [
            InlineKeyboardButton(
                _session_button_label(session), callback_data=f"switch_{session.id}"
            )
        ]
        for session in sessions[:limit]
    ]
    return InlineKeyboardMarkup(rows)


def _format_sessions(state: UserSessionState, limit: int = 10) -> str:
    sessions = state.sessions[:limit]
    if not sessions:
        if state.pending_session_name:
            return (
                f"No sessions yet.\nPending new session: {state.pending_session_name}"
            )
        return "No sessions yet."

    lines = [f"Sessions ({len(sessions)}):"]
    for idx, sess in enumerate(sessions, 1):
        marker = " (👈 current)" if sess.is_current else ""
        if sess.name:
            lines.append(f"{idx}. {sess.id[:8]} [{sess.name}] {marker}")
        else:
            lines.append(f"{idx}. {sess.id[:8]}{marker}")

    if state.pending_session_name:
        lines.append("")
        lines.append(f"Pending new session: {state.pending_session_name}")

    lines.append("")
    lines.append("Use /switch <name|id-prefix> to switch.")
    return "\n".join(lines)


def _resolve_session(
    sessions: list[SessionStateItem], query: str
) -> tuple[SessionStateItem | None, list[SessionStateItem]]:
    """Resolve a session query by exact name, then name prefix, then ID prefix."""
    lower_query = query.lower()
    candidate_lists = [
        [s for s in sessions if s.name and s.name.lower() == lower_query],
        [s for s in sessions if s.name and s.name.lower().startswith(lower_query)],
        [s for s in sessions if s.id.startswith(query)],
    ]
    for matches in candidate_lists:
        if len(matches) == 1:
            return matches[0], []
        if matches:
            return None, matches
    return None, []


def _extract_update_context(update: Update) -> tuple[Message, Chat, User] | None:
    """Return required Telegram entities for command handlers."""
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return None
    return message, chat, user


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command - show command list."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, _user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
        return

    await message.reply_text(_format_command_help())


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new command - start new session."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
        return

    user_id = str(user.id)
    state_manager = get_state_manager()

    session_name = " ".join(context.args).strip() if context.args else None
    session_name = session_name or None
    await state_manager.clear_current_session(user_id)
    await state_manager.set_pending_session_name(user_id, session_name)

    if session_name:
        await message.reply_text(
            f"New session selected: {session_name}\n" "Your next message will start it."
        )
    else:
        await message.reply_text(
            "New session selected. Your next message will start it."
        )


async def cmd_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /continue command - resume last session."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
        return

    user_id = str(user.id)
    state_manager = get_state_manager()
    state = await state_manager.get_session_state(user_id, limit=1)

    if state.current_session_id:
        current = next((s for s in state.sessions if s.is_current), None)
        label = _session_label(current) if current else state.current_session_id[:8]
        await message.reply_text(f"Continuing session: {label}")
    else:
        await message.reply_text("No previous session. Send a voice message to start.")


async def cmd_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sessions command - list all sessions."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
        return

    user_id = str(user.id)
    state_manager = get_state_manager()
    state = await state_manager.get_session_state(user_id, limit=10)
    await message.reply_text(_format_sessions(state))


async def cmd_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /switch command - switch to specific session."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
        return

    user_id = str(user.id)
    state_manager = get_state_manager()
    state = await state_manager.get_session_state(user_id)
    if not context.args:
        if not state.sessions:
            await message.reply_text("No sessions yet.")
        else:
            await message.reply_text(
                "Select a session to switch:",
                reply_markup=_switch_picker_markup(state.sessions),
            )
        return
    query = " ".join(context.args).strip()
    target, matches = _resolve_session(state.sessions, query)

    if target:
        await state_manager.set_current_session(user_id, target.id)
        await state_manager.set_pending_session_name(user_id, None)
        await message.reply_text(f"Switched to session: {_session_label(target)}")
    elif matches:
        options = ", ".join(_session_label(match) for match in matches[:5])
        await message.reply_text(
            f"Multiple matches. Pick one below or be more specific.\nMatches: {options}",
            reply_markup=_switch_picker_markup(matches),
        )
    else:
        await message.reply_text(f"Session not found: {query}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show current session info."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
        return

    user_id = str(user.id)
    state_manager = get_state_manager()
    state = await state_manager.get_session_state(user_id)

    if state.current_session_id:
        current = next((s for s in state.sessions if s.is_current), None)
        current_label = (
            _session_label(current) if current else state.current_session_id[:8]
        )
        await message.reply_text(
            f"Current session: {current_label}\n"
            f"Total sessions: {len(state.sessions)}"
        )
    else:
        msg = "No active session. Send a message or /new to start."
        if state.pending_session_name:
            msg += f"\nPending new session: {state.pending_session_name}"
        await message.reply_text(msg)


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /health command - check all systems."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
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
    user_id = str(user.id)
    state_manager = get_state_manager()
    state = await state_manager.get_session_state(user_id)
    status.append(f"\nSessions: {len(state.sessions)}")
    current = next((s for s in state.sessions if s.is_current), None)
    status.append(f"Current: {_session_label(current) if current else 'None'}")

    # Sandbox info
    status.append(f"\nSandbox: {SANDBOX_DIR}")
    status.append(f"Sandbox exists: {Path(SANDBOX_DIR or '').exists()}")

    # Chat info
    status.append(f"\nChat ID: {chat.id}")
    status.append(f"Topic ID: {message.message_thread_id or 'None'}")
    status.append(f"User ID: {user.id}")

    await message.reply_text("\n".join(status))


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command - show settings menu."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
        return

    user_id = str(user.id)
    state_manager = get_state_manager()
    settings = await state_manager.get_settings(user_id)

    audio_status = "ON" if settings.audio_enabled else "OFF"
    speed = settings.voice_speed
    mode = settings.mode.value
    mode_display = "Go All" if mode == "go_all" else "Approve"
    watch_status = "ON" if settings.watch_enabled else "OFF"
    model_display = settings.model or "default"

    settings_text = (
        f"Settings:\n\n"
        f"Mode: {mode_display}\n"
        f"Watch: {watch_status}\n"
        f"Audio: {audio_status}\n"
        f"Voice Speed: {speed}x\n"
        f"Model: {model_display}"
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

    await message.reply_text(settings_text, reply_markup=reply_markup)


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /model command - show or set model."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
        return

    user_id = str(user.id)
    state_manager = get_state_manager()

    if not context.args:
        settings = await state_manager.get_settings(user_id)
        current = settings.model or "default"
        model_text = (
            f"Current model: {current}\n\n"
            "Usage:\n"
            "/model <name>\n"
            "/model default"
        )
        await message.reply_text(model_text)
        return

    model = " ".join(context.args).strip()
    if model.lower() == "default":
        await state_manager.update_settings(user_id, model="")
        await message.reply_text("Model set to default.")
        return

    await state_manager.update_settings(user_id, model=model)
    await message.reply_text(f"Model set to: {model}")


async def cmd_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setup command - show API credentials status."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, _user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
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

    await message.reply_text("\n".join(message_lines), parse_mode="Markdown")


async def cmd_claude_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /claude_token command - set Claude OAuth token."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, _user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
        return

    thread_id = message.message_thread_id
    try:
        await message.delete()
    except Exception as e:
        debug(f"Failed to delete message in cmd_claude_token: {e}")

    if not context.args:
        await chat.send_message(
            "Usage: `/claude_token <token>`\n\n"
            "Get token by running `claude setup-token` in your terminal.",
            message_thread_id=thread_id,
            parse_mode="Markdown",
        )
        return

    token = " ".join(context.args).strip()

    if not token.startswith("sk-ant-"):
        await chat.send_message(
            "Invalid token format. Token should start with `sk-ant-`",
            message_thread_id=thread_id,
            parse_mode="Markdown",
        )
        return

    creds = load_credentials()
    creds["claude_token"] = token
    save_credentials(creds)

    os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = token

    await chat.send_message(
        "Claude token saved and applied!", message_thread_id=thread_id
    )


async def cmd_elevenlabs_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /elevenlabs_key command - set ElevenLabs API key."""
    update_ctx = _extract_update_context(update)
    if update_ctx is None:
        return
    message, chat, _user = update_ctx

    if not should_handle_message(message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
        return

    thread_id = message.message_thread_id
    try:
        await message.delete()
    except Exception as e:
        debug(f"Failed to delete message in cmd_elevenlabs_key: {e}")

    if not context.args:
        await chat.send_message(
            "Usage: `/elevenlabs_key <key>`\n\n"
            "Get key from elevenlabs.io/app/settings/api-keys",
            message_thread_id=thread_id,
            parse_mode="Markdown",
        )
        return

    key = " ".join(context.args).strip()

    if len(key) < 20:
        await chat.send_message(
            "Invalid key format. Key seems too short.", message_thread_id=thread_id
        )
        return

    creds = load_credentials()
    creds["elevenlabs_key"] = key
    save_credentials(creds)

    # Update voice engine
    voice_engine = get_voice_engine()
    voice_engine.update_api_key(key)

    await chat.send_message(
        "ElevenLabs API key saved and applied!", message_thread_id=thread_id
    )
