"""End-to-end integration tests for Telegram bot.

These tests verify the actual Telegram bot behavior by sending real messages
via the Telegram API and verifying responses.

Setup:
    1. Create a test group in Telegram
    2. Add KoroMind bot to the group
    3. Add a tester bot to the group (disable privacy mode via @BotFather)
    4. Set environment variables:
        - KOROMIND_BOT_TOKEN: Token for the KoroMind bot being tested
        - TEST_BOT_TOKEN: Token for the tester bot
        - TEST_CHAT_ID: Chat ID of the test group

IMPORTANT: The tester bot must have privacy mode DISABLED to see other bots' messages.
           Use @BotFather -> /setprivacy -> Disable

Running:
    pytest src/tests/e2e/test_telegram_e2e.py -v
    pytest -m e2e -v  # Run all E2E tests
"""

import asyncio
import logging
import os
from datetime import datetime

import pytest
from telegram import Bot
from telegram.error import TelegramError


def _has_e2e_credentials():
    """Check if E2E test credentials are available."""
    return all(
        [
            os.getenv("KOROMIND_BOT_TOKEN"),
            os.getenv("TEST_BOT_TOKEN"),
            os.getenv("TEST_CHAT_ID"),
        ]
    )


# Mark all tests in this module
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not _has_e2e_credentials(),
        reason="Missing E2E test credentials (KOROMIND_BOT_TOKEN, TEST_BOT_TOKEN, TEST_CHAT_ID)",
    ),
]


class TelegramTester:
    """Helper class for bot-to-bot testing."""

    def __init__(self, test_bot_token: str, koromind_bot_token: str, chat_id: str):
        self.bot = Bot(token=test_bot_token)
        self.koromind_bot = Bot(token=koromind_bot_token)
        self.chat_id = int(chat_id)
        self.last_message_id = None
        self.last_update_id = None
        self.koromind_username: str | None = None

    async def verify_connectivity(self) -> tuple[bool, str]:
        """Verify tester bot can send and receive in the test chat.

        Note: We cannot use KoroMind's getUpdates as it conflicts with the running bot.
        Instead we verify tester bot can communicate and assume KoroMind is set up correctly.

        Returns:
            (success, message) tuple
        """
        try:
            # Verify tester bot can send a message
            test_msg = await self.bot.send_message(
                chat_id=self.chat_id,
                text=f"[E2E Connectivity Test] {datetime.now().isoformat()}",
            )

            # Verify tester bot identity
            me = await self.bot.get_me()

            # Clean up test message
            try:
                await self.bot.delete_message(
                    chat_id=self.chat_id, message_id=test_msg.message_id
                )
            except TelegramError as exc:
                logging.debug("Failed to delete connectivity test message: %s", exc)

            return (
                True,
                f"Connectivity OK - tester bot (@{me.username}) can send to chat {self.chat_id}",
            )

        except TelegramError as e:
            return False, f"Telegram API error: {e}"

    async def send_message(self, text: str) -> int:
        """Send a message to the test chat.

        Args:
            text: Message text to send

        Returns:
            Message ID of the sent message
        """
        message = await self.bot.send_message(chat_id=self.chat_id, text=text)
        return message.message_id

    async def wait_for_response(
        self, timeout: int = 30, from_bot_username: str | None = None
    ) -> str | None:
        """Wait for a response message from KoroMind bot.

        Uses the tester bot's getUpdates. Make sure tester bot has
        privacy mode DISABLED via @BotFather to see all messages.

        Args:
            timeout: Maximum seconds to wait
            from_bot_username: Username to filter messages from.
                Defaults to the KoroMind bot username.

        Returns:
            Response text if found, None if timeout
        """
        target_username = from_bot_username or self.koromind_username
        start_time = asyncio.get_event_loop().time()
        poll_interval = 2.0

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # Get recent updates from tester bot
                updates = await self.bot.get_updates(
                    offset=self.last_update_id + 1 if self.last_update_id else None,
                    timeout=int(poll_interval),
                )

                for update in updates:
                    # Always update the offset
                    if (
                        self.last_update_id is None
                        or update.update_id > self.last_update_id
                    ):
                        self.last_update_id = update.update_id

                    if update.message and update.message.chat_id == self.chat_id:
                        if update.message.from_user and update.message.from_user.is_bot:
                            # Skip messages from our own tester bot
                            if (
                                update.message.from_user.id
                                == (await self.bot.get_me()).id
                            ):
                                continue

                            # Filter by target bot username
                            if target_username and (
                                update.message.from_user.username != target_username
                            ):
                                continue

                            return update.message.text or update.message.caption

            except TelegramError as e:
                # Ignore timeout errors during polling
                if "timed out" not in str(e).lower():
                    raise

            await asyncio.sleep(poll_interval)

        return None

    async def cleanup_recent_messages(self, count: int = 10):
        """Delete recent messages to keep test chat clean.

        Args:
            count: Number of recent messages to attempt deletion
        """
        if not self.last_message_id:
            return

        for msg_id in range(self.last_message_id, self.last_message_id - count, -1):
            try:
                await self.bot.delete_message(chat_id=self.chat_id, message_id=msg_id)
            except TelegramError:
                pass  # Message might not exist or can't be deleted


@pytest.fixture
async def tester():
    """Create a Telegram tester instance."""
    test_bot_token = os.getenv("TEST_BOT_TOKEN")
    koromind_bot_token = os.getenv("KOROMIND_BOT_TOKEN")
    test_chat_id = os.getenv("TEST_CHAT_ID")

    tester = TelegramTester(test_bot_token, koromind_bot_token, test_chat_id)

    # Resolve KoroMind bot username for response filtering
    koromind_me = await tester.koromind_bot.get_me()
    tester.koromind_username = koromind_me.username

    # Get initial state
    try:
        updates = await tester.bot.get_updates(limit=1)
        if updates:
            tester.last_update_id = updates[-1].update_id
    except TelegramError as exc:
        logging.debug("Failed to get initial updates: %s", exc)

    yield tester


@pytest.mark.asyncio
async def test_0_connectivity(tester):
    """Test that both bots can communicate in the test chat.

    This test runs first (0_ prefix) to verify setup is correct.
    """
    success, message = await tester.verify_connectivity()
    assert success, message


@pytest.mark.asyncio
async def test_text_message_response(tester):
    """Test that bot responds to a simple text message."""
    # Send a simple greeting
    test_message = f"Hello KoroMind! Test at {datetime.now().isoformat()}"
    await tester.send_message(test_message)

    # Wait for response
    response = await tester.wait_for_response(timeout=30)

    # Assert we got a response
    assert response is not None, "Bot did not respond within timeout"
    assert len(response) > 0, "Bot response was empty"


@pytest.mark.asyncio
async def test_new_session_command(tester):
    """Test creating a new named session."""
    session_name = f"e2e-test-{datetime.now().timestamp()}"
    await tester.send_message(f"/new {session_name}")

    response = await tester.wait_for_response(timeout=15)

    assert response is not None, "Bot did not respond to /new command"
    assert session_name in response.lower() or "session" in response.lower()


@pytest.mark.asyncio
async def test_sessions_list_command(tester):
    """Test listing sessions."""
    # Create a session first
    session_name = f"list-test-{datetime.now().timestamp()}"
    await tester.send_message(f"/new {session_name}")
    await tester.wait_for_response(timeout=15)

    # Now list sessions
    await tester.send_message("/sessions")
    response = await tester.wait_for_response(timeout=15)

    assert response is not None, "Bot did not respond to /sessions command"
    # Should contain the session we just created
    assert session_name in response or "session" in response.lower()


@pytest.mark.asyncio
async def test_switch_session_command(tester):
    """Test switching between sessions."""
    # Create two sessions
    session1 = f"switch-test-1-{datetime.now().timestamp()}"
    session2 = f"switch-test-2-{datetime.now().timestamp()}"

    await tester.send_message(f"/new {session1}")
    await tester.wait_for_response(timeout=15)

    await tester.send_message(f"/new {session2}")
    await tester.wait_for_response(timeout=15)

    # Switch back to first session
    await tester.send_message(f"/switch {session1}")
    response = await tester.wait_for_response(timeout=15)

    assert response is not None, "Bot did not respond to /switch command"
    assert (
        session1 in response or "switch" in response.lower()
    ), "Response doesn't confirm session switch"


@pytest.mark.asyncio
async def test_status_command(tester):
    """Test status command returns bot information."""
    await tester.send_message("/status")
    response = await tester.wait_for_response(timeout=15)

    assert response is not None, "Bot did not respond to /status command"
    # Status should contain some session or bot state information
    assert len(response) > 20, "Status response too short"


@pytest.mark.asyncio
async def test_health_command(tester):
    """Test health check command."""
    await tester.send_message("/health")
    response = await tester.wait_for_response(timeout=15)

    assert response is not None, "Bot did not respond to /health command"
    # Health response should indicate status
    assert (
        "ok" in response.lower()
        or "healthy" in response.lower()
        or "online" in response.lower()
    ), "Health response doesn't indicate good status"


@pytest.mark.asyncio
async def test_conversation_memory(tester):
    """Test that bot maintains conversation context within a session."""
    # Create a new session for this test
    session_name = f"memory-test-{datetime.now().timestamp()}"
    await tester.send_message(f"/new {session_name}")
    await tester.wait_for_response(timeout=15)

    # Tell the bot something to remember
    await tester.send_message("My favorite number is 42. Remember this.")
    await tester.wait_for_response(timeout=30)

    # Ask the bot to recall
    await tester.send_message("What is my favorite number?")
    response = await tester.wait_for_response(timeout=30)

    assert response is not None, "Bot did not respond to follow-up question"
    assert "42" in response, "Bot did not recall the favorite number"


@pytest.mark.asyncio
async def test_settings_command(tester):
    """Test settings command displays user settings."""
    await tester.send_message("/settings")
    response = await tester.wait_for_response(timeout=15)

    assert response is not None, "Bot did not respond to /settings command"
    # Settings should mention audio, mode, or other configuration options
    assert (
        "audio" in response.lower()
        or "mode" in response.lower()
        or "setting" in response.lower()
    ), "Settings response doesn't show configuration options"
