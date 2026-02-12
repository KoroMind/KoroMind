"""Utility functions for Telegram handlers."""

import asyncio
import functools
import inspect
import logging
from typing import Any, Callable, Concatenate, Coroutine, ParamSpec, TypeVar

from telegram import Message, Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from koro.config import ALLOWED_CHAT_ID, TOPIC_ID

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def should_handle_message(message_thread_id: int | None) -> bool:
    """
    Check if this bot instance should handle a message based on topic filtering.

    Args:
        message_thread_id: The message's thread/topic ID

    Returns:
        True if message should be handled
    """
    if not TOPIC_ID:
        return True

    try:
        allowed_topic = int(TOPIC_ID)
    except (ValueError, TypeError):
        logger.debug(f"WARNING: Invalid TOPIC_ID '{TOPIC_ID}', handling all messages")
        return True

    if message_thread_id is None:
        logger.debug(f"Message not in a topic, but we're filtering for topic {allowed_topic}")
        return False

    return message_thread_id == allowed_topic


def authorized_handler(
    handler: Callable[
        Concatenate[Update, ContextTypes.DEFAULT_TYPE, P], Coroutine[Any, Any, R]
    ],
) -> Callable[
    Concatenate[Update, ContextTypes.DEFAULT_TYPE, P], Coroutine[Any, Any, R | None]
]:
    """
    Decorator that checks topic filtering and chat authorization.

    Extracts the duplicated pattern:
        if not should_handle_message(update.message.message_thread_id): return
        if ALLOWED_CHAT_ID != 0 and update.effective_chat.id != ALLOWED_CHAT_ID: return
    """

    @functools.wraps(handler)
    async def wrapper(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R | None:
        callback_query = update.callback_query
        raw_answer_cb = callback_query.answer if callback_query is not None else None

        async def answer_callback_query() -> None:
            if not callable(raw_answer_cb):
                return
            result = raw_answer_cb()
            if inspect.isawaitable(result):
                await result

        if callback_query is not None and isinstance(callback_query.message, Message):
            thread_id = callback_query.message.message_thread_id
        else:
            message_obj = update.message
            thread_id = (
                message_obj.message_thread_id if message_obj is not None else None
            )
        chat = update.effective_chat
        chat_id = chat.id if chat is not None else None

        if not should_handle_message(thread_id):
            await answer_callback_query()
            return None
        if ALLOWED_CHAT_ID != 0 and chat_id != ALLOWED_CHAT_ID:
            await answer_callback_query()
            return None
        return await handler(update, context, *args, **kwargs)

    return wrapper


async def _chat_action_loop(
    update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, interval: float
) -> None:
    """Continuously send a chat action until cancelled."""
    chat = update.effective_chat
    if chat is None:
        return
    chat_id = chat.id
    while True:
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=action)
        except TelegramError as exc:
            logger.debug("Failed to send chat action: %s", exc)
        await asyncio.sleep(interval)


def start_chat_action(
    update: Update, context: ContextTypes.DEFAULT_TYPE, interval: float = 4.0
) -> asyncio.Task[None]:
    """Start sending 'typing' chat actions periodically."""
    return asyncio.create_task(
        _chat_action_loop(update, context, ChatAction.TYPING, interval)
    )


async def stop_chat_action(task: asyncio.Task[None] | None) -> None:
    """Stop a running chat action task."""
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        # Task cancellation is expected here; we intentionally ignore the exception.
        pass


async def send_long_message(
    update: Update, first_msg: Message, text: str, chunk_size: int = 4000
) -> None:
    """
    Split long text into multiple Telegram messages.

    Args:
        update: Telegram update object
        first_msg: First message to edit
        text: Full text to send
        chunk_size: Maximum characters per message
    """
    if len(text) <= chunk_size:
        await first_msg.edit_text(text)
        return

    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break
        break_point = remaining.rfind("\n", 0, chunk_size)
        if break_point == -1:
            break_point = remaining.rfind(" ", 0, chunk_size)
        if break_point == -1:
            break_point = chunk_size
        chunks.append(remaining[:break_point])
        remaining = remaining[break_point:].lstrip()

    await first_msg.edit_text(chunks[0] + f"\n\n[1/{len(chunks)}]")
    message = update.message
    if message is None:
        return
    for i, chunk in enumerate(chunks[1:], 2):
        await message.reply_text(chunk + f"\n\n[{i}/{len(chunks)}]")
