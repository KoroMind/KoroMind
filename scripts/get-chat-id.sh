#!/bin/bash
# Get Telegram chat IDs for test setup

set -e

# Load .env if exists
if [ -f .env ]; then
    set -a; source .env; set +a
fi

TOKEN="${TELEGRAM_BOT_TOKEN:-$KOROMIND_BOT_TOKEN}"

if [ -z "$TOKEN" ]; then
    echo "Error: No bot token found. Set TELEGRAM_BOT_TOKEN in .env"
    exit 1
fi

echo "Fetching recent chats from Telegram API..."
echo ""

curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates" | \
    jq -r '
    .result[] |
    select(.message.chat or .my_chat_member.chat) |
    (.message.chat // .my_chat_member.chat) |
    "\(.id) | \(.type) | \(.title // "Private Chat")"
    ' | sort -u

echo ""
echo "Copy the chat ID (negative number for groups) to .env.test as TEST_CHAT_ID"
