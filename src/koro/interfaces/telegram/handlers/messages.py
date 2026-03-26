"""Voice and text message handlers."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from koro.claude import format_tool_call
from koro.core.brain import get_brain
from koro.core.types import (
    BrainCallbacks,
    CanUseTool,
    MessageType,
    Mode,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
    UserSettings,
)
from koro.interfaces.telegram.handlers.utils import (
    authorized_handler,
    send_long_message,
    start_chat_action,
    stop_chat_action,
)
from koro.rate_limit import get_rate_limiter

logger = logging.getLogger(__name__)


@dataclass
class PendingApproval:
    """Runtime state for an approve/reject tool request."""

    user_id: str
    tool_name: str
    event: asyncio.Event
    created_at: float = field(default_factory=time.time)
    approved: bool | None = None
    input: dict[str, Any] = field(default_factory=dict)


# Pending tool approvals for approve mode
pending_approvals: dict[str, PendingApproval] = {}

# Maximum number of pending approvals to prevent memory leaks
MAX_PENDING_APPROVALS = 100


def add_pending_approval(approval_id: str, data: PendingApproval) -> None:
    """Add a pending approval with automatic cleanup of old entries."""
    # Clean up stale approvals before adding new one
    cleanup_stale_approvals()

    # Enforce max size limit (FIFO eviction)
    while len(pending_approvals) >= MAX_PENDING_APPROVALS:
        oldest_id = min(
            pending_approvals.keys(),
            key=lambda k: pending_approvals[k].created_at,
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
        if current_time - data.created_at > max_age_seconds
    ]
    for approval_id in stale_ids:
        del pending_approvals[approval_id]


_USER_ERROR = "Something went wrong. Please try again."


async def _send_safe_error(msg: Message, error: Exception) -> None:
    """Log the error and show a generic message to the user."""
    logger.error("Handler error: %s", error, exc_info=True)
    try:
        await msg.edit_text(_USER_ERROR)
    except Exception as exc:
        logger.debug("Failed to send error message: %s", exc)


def _build_brain_callbacks(
    settings: UserSettings,
    user_id: str,
    update: Update,
) -> BrainCallbacks:
    """Build BrainCallbacks with Telegram-specific closures."""

    # Watch mode: send tool usage updates as Telegram messages
    async def on_tool_use(tool_name: str, detail: str | None) -> None:
        tool_msg = f"{tool_name}: {detail}" if detail else f"Using: {tool_name}"
        try:
            message = update.message
            if message is not None:
                await message.reply_text(tool_msg)
        except Exception as exc:
            logger.debug("Failed to send tool call update: %s", exc)

    # Approve mode: show inline approve/reject buttons, block until user responds
    async def on_tool_approval(
        tool_name: str,
        tool_input: dict[str, Any],
        ctx: ToolPermissionContext,
    ) -> PermissionResultAllow | PermissionResultDeny:
        message = update.message
        if message is None:
            return PermissionResultDeny(message="Missing message context")

        approval_id = str(uuid.uuid4())[:8]
        approval_event = asyncio.Event()

        add_pending_approval(
            approval_id,
            PendingApproval(
                user_id=user_id,
                tool_name=tool_name,
                event=approval_event,
                input=tool_input,
            ),
        )

        keyboard = [
            [
                InlineKeyboardButton("Approve", callback_data=f"approve_{approval_id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject_{approval_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = f"Tool Request:\n{format_tool_call(tool_name, tool_input)}"
        try:
            await message.reply_text(
                message_text, reply_markup=reply_markup, parse_mode="Markdown"
            )
        except Exception as exc:
            logger.warning("Failed to send approval prompt: %s", exc)
            pending_approvals.pop(approval_id, None)
            return PermissionResultDeny(message="Failed to send approval prompt")

        try:
            await asyncio.wait_for(approval_event.wait(), timeout=300)
        except asyncio.TimeoutError:
            pending_approvals.pop(approval_id, None)
            return PermissionResultDeny(message="Approval timed out")
        except asyncio.CancelledError:
            pending_approvals.pop(approval_id, None)
            raise

        approval_data: PendingApproval | None = pending_approvals.pop(approval_id, None)
        if approval_data is not None and approval_data.approved:
            return PermissionResultAllow()
        return PermissionResultDeny(message="User rejected tool")

    return BrainCallbacks(
        on_tool_use=on_tool_use if settings.watch_enabled else None,
        on_tool_approval=(
            cast(CanUseTool, on_tool_approval)
            if settings.mode == Mode.APPROVE
            else None
        ),
    )


@authorized_handler
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages."""
    user = update.effective_user
    message = update.message
    if user is None or message is None or user.is_bot is True:
        return

    logger.debug("VOICE received from user %s", user.id)

    user_id = str(user.id)

    # Rate limiting
    rate_limiter = get_rate_limiter()
    allowed, rate_msg = rate_limiter.check(user_id)
    if not allowed:
        await message.reply_text(rate_msg)
        return

    brain = get_brain()
    settings = await brain.state_manager.get_settings(user_id)

    processing_msg = await message.reply_text("Processing voice message...")
    typing_task = start_chat_action(update, context)

    try:
        # Download voice
        if message.voice is None:
            await processing_msg.edit_text("No voice attachment found.")
            return
        voice = await message.voice.get_file()
        voice_bytes = bytes(await voice.download_as_bytearray())

        callbacks = _build_brain_callbacks(settings, user_id, update)

        response = await brain.process_message(
            user_id=user_id,
            content=voice_bytes,
            content_type=MessageType.VOICE,
            mode=settings.mode,
            include_audio=settings.audio_enabled,
            voice_speed=settings.voice_speed,
            watch_enabled=settings.watch_enabled,
            callbacks=callbacks,
            model=settings.model or None,
        )

        await send_long_message(update, processing_msg, response.text)

        if response.audio:
            await message.reply_voice(voice=response.audio)

    except Exception as e:
        await _send_safe_error(processing_msg, e)
    finally:
        await stop_chat_action(typing_task)


@authorized_handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages."""
    user = update.effective_user
    message = update.message
    if user is None or message is None or user.is_bot is True:
        return

    text = message.text
    if not text:
        return
    logger.debug("TEXT received: '%s'", text[:50])

    user_id = str(user.id)

    # Rate limiting
    rate_limiter = get_rate_limiter()
    allowed, rate_msg = rate_limiter.check(user_id)
    if not allowed:
        await message.reply_text(rate_msg)
        return

    brain = get_brain()
    settings = await brain.state_manager.get_settings(user_id)

    processing_msg = await message.reply_text("Asking Koro...")
    typing_task = start_chat_action(update, context)

    try:
        callbacks = _build_brain_callbacks(settings, user_id, update)

        response = await brain.process_message(
            user_id=user_id,
            content=text,
            content_type=MessageType.TEXT,
            mode=settings.mode,
            include_audio=settings.audio_enabled,
            voice_speed=settings.voice_speed,
            watch_enabled=settings.watch_enabled,
            callbacks=callbacks,
            model=settings.model or None,
        )

        await send_long_message(update, processing_msg, response.text)

        if response.audio:
            await message.reply_voice(voice=response.audio)

    except Exception as e:
        await _send_safe_error(processing_msg, e)
    finally:
        await stop_chat_action(typing_task)
