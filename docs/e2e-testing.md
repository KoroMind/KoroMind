# End-to-End Testing Guide

This guide explains how to set up and run end-to-end (E2E) integration tests for the KoroMind Telegram bot.

## Overview

The E2E tests verify the complete Telegram bot functionality by sending real messages via the Telegram API and verifying responses. This uses a "bot-to-bot" testing approach where a tester bot sends messages and monitors responses from the KoroMind bot.

## Setup

### 1. Create a Test Environment

You'll need:
- A Telegram test group
- The KoroMind bot (being tested)
- A separate tester bot (to send test messages)

### 2. Create the Test Group

1. Open Telegram and create a new group (e.g., "KoroMind E2E Tests")
2. Add both bots to the group:
   - Your KoroMind bot instance
   - The tester bot

### 3. Create a Tester Bot

If you don't have a tester bot yet:

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Follow prompts to name your bot (e.g., "KoroMind Tester")
4. Save the bot token provided

### 4. Get the Test Chat ID

Option A - Using the tester bot:
```bash
# Send a message to the test group, then run:
curl "https://api.telegram.org/bot<TEST_BOT_TOKEN>/getUpdates"
```

Look for `"chat":{"id":-1234567890}` in the response.

Option B - Using a bot like [@userinfobot](https://t.me/userinfobot):
1. Add the bot to your test group
2. It will display the chat ID

### 5. Configure Environment Variables

Create or update your `.env.test` file:

```bash
# KoroMind bot being tested
KOROMIND_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Tester bot (sends test messages)
TEST_BOT_TOKEN=987654321:ZYXwvuTSRqponMLKjihGFEdcba

# Test group chat ID (negative for groups)
TEST_CHAT_ID=-1001234567890
```

### 6. Start KoroMind Bot

The bot must be running for E2E tests to work:

```bash
# In a separate terminal
source .venv/bin/activate
python -m koro telegram
```

Or using Docker:
```bash
docker compose up -d koro
```

## Running Tests

### Run All E2E Tests

```bash
# Load test environment and run
export $(cat .env.test | xargs)
pytest src/tests/e2e/test_telegram_e2e.py -v
```

### Run Specific Test

```bash
export $(cat .env.test | xargs)
pytest src/tests/e2e/test_telegram_e2e.py::test_text_message_response -v
```

### Skip E2E Tests

E2E tests are marked with `@pytest.mark.e2e`, so you can exclude them:

```bash
# Run all tests except E2E
pytest -m "not e2e" -v

# Run unit and integration but skip E2E
pytest src/tests/unit src/tests/integration -v
```

### Run Only E2E Tests

```bash
pytest -m e2e -v
```

## Test Coverage

The E2E test suite covers:

1. **Text Message Response** - Bot responds to simple text messages
2. **New Session** - `/new <session_name>` creates named sessions
3. **List Sessions** - `/sessions` shows active sessions
4. **Switch Session** - `/switch <session_name>` changes active session
5. **Status Check** - `/status` returns bot state
6. **Health Check** - `/health` confirms bot is operational
7. **Conversation Memory** - Bot maintains context within session
8. **Settings Display** - `/settings` shows user configuration

## How It Works

### Bot-to-Bot Architecture

```
Test Suite (pytest)
    ↓
Tester Bot (sends messages)
    ↓
Telegram API
    ↓
KoroMind Bot (responds)
    ↓
Telegram API
    ↓
Tester Bot (polls for response)
    ↓
Test Suite (verifies response)
```

### Test Flow

Each test follows this pattern:

1. **Send message** - Tester bot sends command/message to test group
2. **Wait for response** - Polls Telegram API for bot's reply (30s timeout)
3. **Verify response** - Asserts response content is correct

### TelegramTester Helper Class

The `TelegramTester` class provides:
- `send_message(text)` - Send message to test chat
- `wait_for_response(timeout, from_bot_username)` - Poll for bot response
- `cleanup_recent_messages(count)` - Clean up test messages

## CI/CD Integration

### GitHub Actions

Skip E2E tests in CI unless credentials are available:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest -m "not e2e" -v  # Skip E2E in CI
```

To enable E2E tests in CI:

1. Add secrets to GitHub repository:
   - `KOROMIND_BOT_TOKEN`
   - `TEST_BOT_TOKEN`
   - `TEST_CHAT_ID`

2. Update workflow:
```yaml
- name: Run E2E tests
  if: ${{ secrets.TEST_BOT_TOKEN != '' }}
  env:
    KOROMIND_BOT_TOKEN: ${{ secrets.KOROMIND_BOT_TOKEN }}
    TEST_BOT_TOKEN: ${{ secrets.TEST_BOT_TOKEN }}
    TEST_CHAT_ID: ${{ secrets.TEST_CHAT_ID }}
  run: |
    # Start bot in background
    python -m koro telegram &
    BOT_PID=$!
    sleep 5

    # Run tests
    pytest -m e2e -v

    # Cleanup
    kill $BOT_PID
```

## Troubleshooting

### Tests Timeout

**Problem:** Tests fail with "Bot did not respond within timeout"

**Solutions:**
- Verify bot is running: `docker compose logs -f koro`
- Check bot has access to test group
- Verify bot token is correct
- Increase timeout in test if bot is slow

### Bot Not Receiving Messages

**Problem:** Bot doesn't respond to any messages

**Solutions:**
- Ensure both bots are in the test group
- Check `ALLOWED_CHAT_ID` in KoroMind `.env` includes test group ID
- Verify no `TOPIC_ID` filter is blocking messages
- Check bot has necessary permissions in group

### Wrong Bot Responds

**Problem:** Tester bot receives messages from wrong bot

**Solutions:**
- Use `from_bot_username` parameter in `wait_for_response()`
- Ensure bot usernames are unique
- Check that only test bots are in the group

### Permission Errors

**Problem:** Tests fail with "not enough rights to send text messages"

**Solutions:**
- Ensure tester bot is not restricted in the group
- Remove any message restrictions
- Make tester bot an admin (optional)

### Stale Messages

**Problem:** Tests receive old messages from previous test runs

**Solutions:**
- The tester tracks `last_message_id` to ignore old messages
- Manually clear chat history before test runs
- Use unique timestamps in test messages

## Best Practices

1. **Use dedicated test group** - Don't use production bot/group for testing
2. **Unique session names** - Include timestamp to avoid conflicts
3. **Independent tests** - Each test should work in isolation
4. **Cleanup** - Consider uncommenting cleanup in fixture
5. **Timeouts** - Adjust based on your bot's response time
6. **Rate limits** - Add delays between tests if hitting Telegram limits

## Extending Tests

### Adding New Test Cases

```python
@pytest.mark.asyncio
async def test_new_feature(tester):
    """Test description."""
    # Send message
    await tester.send_message("/command or text")

    # Wait for response
    response = await tester.wait_for_response(timeout=30)

    # Verify
    assert response is not None, "Bot did not respond"
    assert "expected" in response.lower()
```

### Testing Voice Messages

To test voice message handling:

1. Upload a test audio file via tester bot
2. Monitor for voice response or text transcription
3. Requires extending TelegramTester with voice support

### Testing Photos

Similar to voice, extend TelegramTester to send photos and monitor for analysis responses.

## Limitations

Current limitations of the E2E test suite:

1. **No voice testing** - Voice messages not yet supported
2. **No photo testing** - Image uploads not yet supported
3. **No callback buttons** - Interactive button testing not implemented
4. **Single-threaded** - Tests run sequentially, not in parallel
5. **Manual bot startup** - Bot must be started separately

Future improvements could address these limitations.

## Security Notes

- **Never commit** `.env.test` with real tokens
- Use separate test bots, not production bots
- Restrict test group membership
- Regularly rotate test bot tokens
- Monitor test group for unexpected activity

## References

- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [pytest-asyncio Guide](https://pytest-asyncio.readthedocs.io/)
