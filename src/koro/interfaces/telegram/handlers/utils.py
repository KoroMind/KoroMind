"""Utility functions for Telegram handlers."""

import asyncio
from datetime import datetime

from telegram.constants import ChatAction

from koro.config import TOPIC_ID


def debug(msg: str) -> None:
    """Print debug message with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


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
        debug(f"WARNING: Invalid TOPIC_ID '{TOPIC_ID}', handling all messages")
        return True

    if message_thread_id is None:
        debug(f"Message not in a topic, but we're filtering for topic {allowed_topic}")
        return False

    return message_thread_id == allowed_topic


async def _chat_action_loop(update, context, action: str, interval: float) -> None:
    """Continuously send a chat action until cancelled."""
    chat_id = update.effective_chat.id
    while True:
        await context.bot.send_chat_action(chat_id=chat_id, action=action)
        await asyncio.sleep(interval)


def start_chat_action(update, context, interval: float = 4.0) -> asyncio.Task:
    """Start sending 'typing' chat actions periodically."""
    return asyncio.create_task(
        _chat_action_loop(update, context, ChatAction.TYPING, interval)
    )


async def stop_chat_action(task: asyncio.Task | None) -> None:
    """Stop a running chat action task."""
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        # Task cancellation is expected here; we intentionally ignore the exception.
        pass


async def send_long_message(update, first_msg, text: str, chunk_size: int = 4000):
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
    for i, chunk in enumerate(chunks[1:], 2):
        await update.message.reply_text(chunk + f"\n\n[{i}/{len(chunks)}]")
