"""Callback query handlers for inline keyboards."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..state import get_state_manager
from .messages import pending_approvals
from .utils import debug


async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings button callbacks."""
    query = update.callback_query
    debug(f"SETTINGS CALLBACK: {query.data}")

    user_id = update.effective_user.id
    state_manager = get_state_manager()
    settings = state_manager.get_user_settings(user_id)
    callback_data = query.data

    if callback_data == "setting_audio_toggle":
        settings["audio_enabled"] = not settings["audio_enabled"]
        state_manager.save_settings()

    elif callback_data == "setting_mode_toggle":
        current_mode = settings.get("mode", "go_all")
        settings["mode"] = "approve" if current_mode == "go_all" else "go_all"
        state_manager.save_settings()

    elif callback_data == "setting_watch_toggle":
        settings["watch_enabled"] = not settings.get("watch_enabled", False)
        state_manager.save_settings()

    elif callback_data.startswith("setting_speed_"):
        try:
            speed = float(callback_data.replace("setting_speed_", ""))
            if not 0.7 <= speed <= 1.2:
                await query.answer("Invalid speed range")
                return
        except ValueError:
            await query.answer("Invalid speed value")
            return

        settings["voice_speed"] = speed
        state_manager.save_settings()

    # Build updated menu
    audio_status = "ON" if settings["audio_enabled"] else "OFF"
    speed = settings["voice_speed"]
    mode = settings.get("mode", "go_all")
    mode_display = "Go All" if mode == "go_all" else "Approve"
    watch_status = "ON" if settings.get("watch_enabled", False) else "OFF"

    message = f"Settings:\n\nMode: {mode_display}\nWatch: {watch_status}\nAudio: {audio_status}\nVoice Speed: {speed}x"

    keyboard = [
        [
            InlineKeyboardButton(f"Mode: {mode_display}", callback_data="setting_mode_toggle"),
            InlineKeyboardButton(f"Watch: {watch_status}", callback_data="setting_watch_toggle"),
        ],
        [InlineKeyboardButton(f"Audio: {audio_status}", callback_data="setting_audio_toggle")],
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


async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle approval/rejection button callbacks."""
    query = update.callback_query
    callback_data = query.data

    debug(f"APPROVAL CALLBACK: {callback_data}")

    await query.answer()

    if callback_data.startswith("approve_"):
        approval_id = callback_data.replace("approve_", "")
        if approval_id in pending_approvals:
            if update.effective_user.id != pending_approvals[approval_id].get("user_id"):
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
            if update.effective_user.id != pending_approvals[approval_id].get("user_id"):
                await query.answer("Only the requester can reject this")
                return

            tool_name = pending_approvals[approval_id]["tool_name"]
            pending_approvals[approval_id]["approved"] = False
            pending_approvals[approval_id]["event"].set()
            await query.edit_message_text(f"Rejected: {tool_name}")
        else:
            await query.edit_message_text("Approval expired")
