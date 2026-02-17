"""Callback query handlers for inline keyboards."""

import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from koro.interfaces.telegram.handlers.commands import (
    STT_LANGUAGE_OPTIONS,
    _session_label,
    _settings_markup,
    _settings_text,
)
from koro.interfaces.telegram.handlers.messages import pending_approvals
from koro.interfaces.telegram.handlers.utils import authorized_handler
from koro.state import get_state_manager

logger = logging.getLogger(__name__)


@authorized_handler
async def handle_settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle settings button callbacks."""
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return
    if query.data is None:
        await query.answer()
        return
    logger.debug("SETTINGS CALLBACK: %s", query.data)

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
    elif callback_data.startswith("setting_lang_"):
        language_code = callback_data.replace("setting_lang_", "", 1)
        if language_code not in STT_LANGUAGE_OPTIONS:
            await query.answer("Unsupported language")
            return
        await state_manager.update_settings(user_id, stt_language=language_code)

    # Re-fetch updated settings
    settings = await state_manager.get_settings(user_id)
    reply_markup = _settings_markup(settings)

    try:
        await query.edit_message_text(
            _settings_text(settings), reply_markup=reply_markup
        )
    except TelegramError as e:
        logger.debug("Error updating settings menu: %s", e)

    await query.answer()


@authorized_handler
async def handle_approval_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle approval/rejection button callbacks."""
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return
    if query.data is None:
        await query.answer()
        return
    callback_data = query.data

    logger.debug("APPROVAL CALLBACK: %s", callback_data)

    user_id = str(user.id)

    await query.answer()

    if callback_data.startswith("approve_"):
        approval_id = callback_data.replace("approve_", "")
        if approval_id in pending_approvals:
            approval = pending_approvals[approval_id]
            if user_id != approval.user_id:
                await query.answer("Only the requester can approve this")
                return

            approval.approved = True
            approval.event.set()
            await query.edit_message_text(f"Approved: {approval.tool_name}")
        else:
            await query.edit_message_text("Approval expired")

    elif callback_data.startswith("reject_"):
        approval_id = callback_data.replace("reject_", "")
        if approval_id in pending_approvals:
            approval = pending_approvals[approval_id]
            if user_id != approval.user_id:
                await query.answer("Only the requester can reject this")
                return

            approval.approved = False
            approval.event.set()
            await query.edit_message_text(f"Rejected: {approval.tool_name}")
        else:
            await query.edit_message_text("Approval expired")


@authorized_handler
async def handle_switch_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle session switch button callbacks."""
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return
    if query.data is None:
        await query.answer()
        return
    callback_data = query.data

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
