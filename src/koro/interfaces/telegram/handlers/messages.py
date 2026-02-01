"""Voice and text message handlers."""

import asyncio
import time
import uuid
from io import BytesIO

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from koro.claude import format_tool_call
from koro.config import ALLOWED_CHAT_ID
from koro.core.brain import get_brain
from koro.core.types import (
    BrainCallbacks,
    MessageType,
    Mode,
    PermissionResultAllow,
    PermissionResultDeny,
)
from koro.interfaces.telegram.handlers.utils import (
    debug,
    send_long_message,
    should_handle_message,
)

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

    user_id = str(update.effective_user.id)
    brain = get_brain()

    # Rate limiting
    allowed, rate_msg = brain.check_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(rate_msg)
        return

    # Get settings
    settings = await brain.get_settings(user_id)

    processing_msg = await update.message.reply_text("Processing voice message...")

    try:
        # Download voice
        voice = await update.message.voice.get_file()
        voice_bytes = bytes(await voice.download_as_bytearray())

        # Create callbacks for Brain
        callbacks = _create_brain_callbacks(
            update, context, processing_msg, settings.watch_enabled, settings.mode
        )

        # Start typing indicator
        await update.effective_chat.send_chat_action(ChatAction.TYPING)

        # Process through Brain (handles transcription, Claude, TTS)
        response = await brain.process_message(
            user_id=user_id,
            content=voice_bytes,
            content_type=MessageType.VOICE,
            mode=settings.mode,
            include_audio=settings.audio_enabled,
            voice_speed=settings.voice_speed,
            watch_enabled=settings.watch_enabled,
            callbacks=callbacks,
        )

        # Send text response
        await send_long_message(update, processing_msg, response.text)

        # Send voice response if available
        if response.audio:
            await update.message.reply_voice(voice=BytesIO(response.audio))

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

    user_id = str(update.effective_user.id)
    brain = get_brain()

    # Rate limiting
    allowed, rate_msg = brain.check_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(rate_msg)
        return

    # Get settings
    settings = await brain.get_settings(user_id)
    text = update.message.text

    processing_msg = await update.message.reply_text("Thinking...")

    try:
        # Create callbacks for Brain
        callbacks = _create_brain_callbacks(
            update, context, processing_msg, settings.watch_enabled, settings.mode
        )

        # Start typing indicator
        await update.effective_chat.send_chat_action(ChatAction.TYPING)

        # Process through Brain
        response = await brain.process_message(
            user_id=user_id,
            content=text,
            content_type=MessageType.TEXT,
            mode=settings.mode,
            include_audio=settings.audio_enabled,
            voice_speed=settings.voice_speed,
            watch_enabled=settings.watch_enabled,
            callbacks=callbacks,
        )

        # Send text response
        await send_long_message(update, processing_msg, response.text)

        # Send voice response if available
        if response.audio:
            await update.message.reply_voice(voice=BytesIO(response.audio))

    except Exception as e:
        debug(f"Error in handle_text: {e}")
        await processing_msg.edit_text(f"Error: {e}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages."""
    if update.effective_user.is_bot is True:
        return

    debug(f"PHOTO received from user {update.effective_user.id}")

    if not should_handle_message(update.message.message_thread_id):
        return

    if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID:
        return

    user_id = str(update.effective_user.id)
    brain = get_brain()

    # Rate limiting
    allowed, rate_msg = brain.check_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(rate_msg)
        return

    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_bytes = bytes(await photo_file.download_as_bytearray())

        # Process through Brain (will return placeholder for now)
        response = await brain.process_message(
            user_id=user_id,
            content=photo_bytes,
            content_type=MessageType.IMAGE,
        )

        await update.message.reply_text(response.text)

    except Exception as e:
        debug(f"Error in handle_photo: {e}")
        await update.message.reply_text(f"Error processing image: {e}")


def _create_brain_callbacks(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    processing_msg,
    watch_enabled: bool,
    mode: Mode,
) -> BrainCallbacks:
    """
    Create BrainCallbacks for Telegram interface.

    Args:
        update: Telegram update
        context: Telegram context
        processing_msg: Processing message to update with progress
        watch_enabled: Whether watch mode is enabled
        mode: Execution mode (GO_ALL or APPROVE)

    Returns:
        BrainCallbacks instance
    """

    def on_progress(status: str) -> None:
        """Update processing message with progress status."""
        try:
            asyncio.create_task(processing_msg.edit_text(status))
        except Exception as exc:
            debug(f"Failed to update progress: {exc}")

    def on_tool_use(tool_name: str, detail: str | None) -> None:
        """Send tool call notification in watch mode."""
        if watch_enabled:
            tool_msg = f"{tool_name}: {detail}" if detail else f"Using: {tool_name}"
            try:
                asyncio.create_task(update.message.reply_text(tool_msg))
            except Exception as exc:
                debug(f"Failed to send tool call update: {exc}")

    async def on_tool_approval(tool_name: str, tool_input: dict, ctx):
        """Handle tool approval in approve mode."""
        if mode != Mode.APPROVE:
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

    return BrainCallbacks(
        on_tool_use=on_tool_use,
        on_tool_approval=on_tool_approval,
        on_progress=on_progress,
    )
