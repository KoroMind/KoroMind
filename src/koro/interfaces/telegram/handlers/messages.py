"""Voice and text message handlers."""

import asyncio
import time
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from koro.claude import format_tool_call, get_claude_client
from koro.config import ALLOWED_CHAT_ID
from koro.interfaces.telegram.handlers.utils import (
    debug,
    send_long_message,
    should_handle_message,
)
from koro.rate_limit import get_rate_limiter
from koro.state import get_state_manager
from koro.voice import get_voice_engine

# Pending tool approvals for approve mode
pending_approvals: dict = {}

# Maximum number of pending approvals to prevent memory leaks
MAX_PENDING_APPROVALS = 100


def add_pending_approval(approval_id: str, data: dict) -> None:
    """
    Add a pending approval with automatic cleanup of old entries.

    Args:
        approval_id: Unique approval ID
        data: Approval data (should include created_at)
    """
    # Ensure created_at is present
    if "created_at" not in data:
        data["created_at"] = time.time()

    # Clean up stale approvals before adding new one
    cleanup_stale_approvals()

    # Enforce max size limit (FIFO eviction)
    while len(pending_approvals) >= MAX_PENDING_APPROVALS:
        oldest_id = min(
            pending_approvals.keys(),
            key=lambda k: pending_approvals[k].get("created_at", 0),
        )
        del pending_approvals[oldest_id]

    pending_approvals[approval_id] = data


def cleanup_stale_approvals(max_age_seconds: int = 300) -> None:
    """
    Remove pending approvals that have exceeded the max age.

    Args:
        max_age_seconds: Maximum age in seconds (default 5 minutes)
    """
    current_time = time.time()
    stale_ids = [
        approval_id
        for approval_id, data in pending_approvals.items()
        if current_time - data.get("created_at", 0) > max_age_seconds
    ]
    for approval_id in stale_ids:
        del pending_approvals[approval_id]


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice messages."""
    if update.effective_user.is_bot is True:
        return

    debug(f"VOICE received from user {update.effective_user.id}")

    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    user_id = update.effective_user.id

    # Rate limiting
    rate_limiter = get_rate_limiter()
    allowed, rate_msg = rate_limiter.check(user_id)
    if not allowed:
        await update.message.reply_text(rate_msg)
        return

    state_manager = get_state_manager()
    state = state_manager.get_user_state(user_id)
    settings = state_manager.get_user_settings(user_id)

    processing_msg = await update.message.reply_text("Processing voice message...")

    try:
        # Download voice
        voice = await update.message.voice.get_file()
        voice_bytes = await voice.download_as_bytearray()

        # Transcribe
        await processing_msg.edit_text("Transcribing...")
        voice_engine = get_voice_engine()
        text = await voice_engine.transcribe(bytes(voice_bytes))

        if text.startswith("[Transcription error") or text.startswith("[Error"):
            await processing_msg.edit_text(text)
            return

        # Show what was heard
        preview = text[:100] + "..." if len(text) > 100 else text
        await processing_msg.edit_text(f"Heard: {preview}\n\nAsking Koro...")

        # Call Claude
        response, new_session_id, metadata = await _call_claude_with_settings(
            text, state, settings, update, context
        )

        # Update session
        await state_manager.update_session(str(user_id), new_session_id)

        # Send response
        await send_long_message(update, processing_msg, response)

        # Voice response if enabled
        if settings["audio_enabled"]:
            audio = await voice_engine.text_to_speech(
                response, speed=settings["voice_speed"]
            )
            if audio:
                await update.message.reply_voice(voice=audio)

    except Exception as e:
        debug(f"Error in handle_voice: {e}")
        await processing_msg.edit_text(f"Error: {e}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    if update.effective_user.is_bot is True:
        return

    debug(f"TEXT received: '{update.message.text[:50]}'")

    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    user_id = update.effective_user.id

    # Rate limiting
    rate_limiter = get_rate_limiter()
    allowed, rate_msg = rate_limiter.check(user_id)
    if not allowed:
        await update.message.reply_text(rate_msg)
        return

    state_manager = get_state_manager()
    state = state_manager.get_user_state(user_id)
    settings = state_manager.get_user_settings(user_id)
    text = update.message.text

    processing_msg = await update.message.reply_text("Asking Koro...")

    try:
        response, new_session_id, metadata = await _call_claude_with_settings(
            text, state, settings, update, context
        )

        # Update session
        await state_manager.update_session(str(user_id), new_session_id)

        # Send response
        await send_long_message(update, processing_msg, response)

        # Voice response if enabled
        if settings["audio_enabled"]:
            voice_engine = get_voice_engine()
            audio = await voice_engine.text_to_speech(
                response, speed=settings["voice_speed"]
            )
            if audio:
                await update.message.reply_voice(voice=audio)

    except Exception as e:
        debug(f"Error in handle_text: {e}")
        await processing_msg.edit_text(f"Error: {e}")


async def _call_claude_with_settings(
    text: str,
    state: dict,
    settings: dict,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[str, str, dict]:
    """
    Call Claude with user settings applied.

    Args:
        text: User message
        state: User session state
        settings: User settings
        update: Telegram update
        context: Telegram context

    Returns:
        (response, session_id, metadata)
    """
    from koro.core.types import Mode, UserSettings

    settings_model = UserSettings.from_dict(settings)
    mode = settings_model.mode
    watch_enabled = settings.get("watch_enabled", False)
    continue_last = state["current_session"] is not None

    # Watch mode callback
    async def on_tool_call(tool_name: str, detail: str | None):
        if watch_enabled:
            tool_msg = f"{tool_name}: {detail}" if detail else f"Using: {tool_name}"
            try:
                await update.message.reply_text(tool_msg)
            except Exception as exc:
                debug(f"Failed to send tool call update: {exc}")

    # Approve mode callback
    async def can_use_tool(tool_name: str, tool_input: dict, ctx):
        from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

        if mode != "approve":
            return PermissionResultAllow()

        approval_id = str(uuid.uuid4())[:8]
        approval_event = asyncio.Event()

        add_pending_approval(
            approval_id,
            {
                "created_at": time.time(),
                "user_id": update.effective_user.id,
                "event": approval_event,
                "approved": None,
                "tool_name": tool_name,
                "input": tool_input,
            },
        )

        keyboard = [
            [
                InlineKeyboardButton("Approve", callback_data=f"approve_{approval_id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject_{approval_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = f"Tool Request:\n{format_tool_call(tool_name, tool_input)}"
        await update.message.reply_text(
            message_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

        try:
            await asyncio.wait_for(approval_event.wait(), timeout=300)
        except asyncio.TimeoutError:
            del pending_approvals[approval_id]
            return PermissionResultDeny(message="Approval timed out")

        approval_data = pending_approvals.pop(approval_id, {})
        if approval_data.get("approved"):
            return PermissionResultAllow()
        return PermissionResultDeny(message="User rejected tool")

    from koro.core.types import QueryConfig

    claude_client = get_claude_client()
    config = QueryConfig(
        prompt=text,
        session_id=state["current_session"],
        continue_last=continue_last,
        user_settings=settings_model,
        mode=mode,
        on_tool_call=on_tool_call if watch_enabled else None,
        can_use_tool=can_use_tool if mode == Mode.APPROVE else None,
    )
    return await claude_client.query(config)
