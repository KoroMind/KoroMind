#!/usr/bin/env python3
"""
Debug script to show Telegram topic/chat information.
Run this, then send messages in different topics to see their IDs.
"""

import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def debug_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log all message details."""
    msg = update.message
    chat = update.effective_chat
    user = update.effective_user

    print("\n" + "="*60)
    print("MESSAGE RECEIVED")
    print("="*60)
    print(f"Chat ID:          {chat.id}")
    print(f"Chat Type:        {chat.type}")
    print(f"Chat Title:       {chat.title or 'N/A'}")
    print(f"Topic ID:         {msg.message_thread_id or 'None (General)'}")
    print(f"Is Topic Message: {msg.is_topic_message}")
    print(f"User ID:          {user.id}")
    print(f"User Name:        {user.full_name}")
    print(f"Message Text:     {msg.text[:50] if msg.text else '[no text]'}...")
    print("="*60)

    # Reply with the info
    reply = (
        f"📊 **Debug Info**\n\n"
        f"Chat ID: `{chat.id}`\n"
        f"Topic ID: `{msg.message_thread_id or 'None'}`\n"
        f"User ID: `{user.id}`\n"
    )
    await msg.reply_text(reply, parse_mode='Markdown')

def main():
    print("Starting topic debug bot...")
    print(f"Bot token: {TELEGRAM_BOT_TOKEN[:20]}...")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, debug_handler))

    print("\nSend messages in different topics to see their IDs.")
    print("Press Ctrl+C to stop.\n")

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
