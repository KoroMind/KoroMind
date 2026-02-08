"""Callback query handlers for inline keyboards."""

from telegram import (
    CallbackQuery,
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    User,
)
from telegram.ext import ContextTypes

from koro.config import ALLOWED_CHAT_ID
from koro.interfaces.telegram.handlers.commands import _session_label
from koro.interfaces.telegram.handlers.messages import pending_approvals
from koro.interfaces.telegram.handlers.utils import debug, should_handle_message
from koro.state import get_state_manager


def _extract_callback_context(
    update: Update,
) -> tuple[CallbackQuery, User, Chat] | None:
    """Return required entities for callback handlers."""
    query = update.callback_query
    user = update.effective_user
    chat = update.effective_chat
    if query is None or user is None or chat is None:
        return None
    return query, user, chat


async def handle_settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle settings button callbacks."""
    callback_ctx = _extract_callback_context(update)
    if callback_ctx is None:
        return
    query, user, _chat = callback_ctx

    if query.data is None:
        await query.answer()
        return

    debug(f"SETTINGS CALLBACK: {query.data}")

    user_id = str(user.id)
    state_manager = get_state_manager()
    settings = await state_manager.get_settings(user_id)
    callback_data = query.data

    if callback_data == "setting_audio_toggle":
        await state_manager.update_settings(
            user_id, audio_enabled=not settings.audio_enabled
        )

    elif callback_data == "setting_mode_toggle":
        new_mode = "approve" if settings.mode.value == "go_all" else "go_all"
        await state_manager.update_settings(user_id, mode=new_mode)

    elif callback_data == "setting_watch_toggle":
        await state_manager.update_settings(
            user_id, watch_enabled=not settings.watch_enabled
        )

    elif callback_data.startswith("setting_speed_"):
        try:
            speed = float(callback_data.replace("setting_speed_", ""))
            if not 0.7 <= speed <= 1.2:
                await query.answer("Invalid speed range")
                return
        except ValueError:
            await query.answer("Invalid speed value")
            return

        await state_manager.update_settings(user_id, voice_speed=speed)

    # Re-fetch updated settings
    settings = await state_manager.get_settings(user_id)

    # Build updated menu
    audio_status = "ON" if settings.audio_enabled else "OFF"
    speed = settings.voice_speed
    mode = settings.mode.value
    mode_display = "Go All" if mode == "go_all" else "Approve"
    watch_status = "ON" if settings.watch_enabled else "OFF"
    model_display = settings.model or "default"

    message = (
        f"Settings:\n\nMode: {mode_display}\nWatch: {watch_status}\n"
        f"Audio: {audio_status}\nVoice Speed: {speed}x\nModel: {model_display}"
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

    try:
        await query.edit_message_text(message, reply_markup=reply_markup)
    except Exception as e:
        debug(f"Error updating settings menu: {e}")

    await query.answer()


async def handle_approval_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle approval/rejection button callbacks."""
    callback_ctx = _extract_callback_context(update)
    if callback_ctx is None:
        return
    query, user, _chat = callback_ctx

    if query.data is None:
        await query.answer()
        return

    callback_data = query.data

    debug(f"APPROVAL CALLBACK: {callback_data}")

    user_id = str(user.id)

    await query.answer()

    if callback_data.startswith("approve_"):
        approval_id = callback_data.replace("approve_", "")
        if approval_id in pending_approvals:
            if user_id != pending_approvals[approval_id].get("user_id"):
                await query.answer("Only the requester can approve this")
                return

            tool_name = pending_approvals[approval_id]["tool_name"]
            pending_approvals[approval_id]["approved"] = True
            pending_approvals[approval_id]["event"].set()
            await query.edit_message_text(f"Approved: {tool_name}")
        else:
            await query.edit_message_text("Approval expired")

    elif callback_data.startswith("reject_"):
        approval_id = callback_data.replace("reject_", "")
        if approval_id in pending_approvals:
            if user_id != pending_approvals[approval_id].get("user_id"):
                await query.answer("Only the requester can reject this")
                return

            tool_name = pending_approvals[approval_id]["tool_name"]
            pending_approvals[approval_id]["approved"] = False
            pending_approvals[approval_id]["event"].set()
            await query.edit_message_text(f"Rejected: {tool_name}")
        else:
            await query.edit_message_text("Approval expired")


async def handle_switch_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle session switch button callbacks."""
    callback_ctx = _extract_callback_context(update)
    if callback_ctx is None:
        return
    query, user, chat = callback_ctx

    callback_data = query.data
    if callback_data is None:
        await query.answer()
        return

    if not should_handle_message(getattr(query.message, "message_thread_id", None)):
        await query.answer()
        return

    if ALLOWED_CHAT_ID != 0 and chat.id != ALLOWED_CHAT_ID:
        await query.answer()
        return

    if not callback_data.startswith("switch_"):
        await query.answer()
        return

    session_id = callback_data.replace("switch_", "", 1)
    user_id = str(user.id)
    state_manager = get_state_manager()
    target = await state_manager.get_session_item(user_id, session_id)

    if target is None:
        await query.edit_message_text("Session not found. Use /sessions to list.")
        await query.answer()
        return

    await state_manager.set_current_session(user_id, session_id)
    await state_manager.set_pending_session_name(user_id, None)
    await query.edit_message_text(f"Switched to session: {_session_label(target)}")
    await query.answer()
