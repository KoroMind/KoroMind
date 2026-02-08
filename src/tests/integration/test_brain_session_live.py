"""Live integration tests for Brain session management."""

import asyncio
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from koro.core.brain import Brain
from koro.core.claude import ClaudeClient
from koro.core.state import StateManager
from koro.core.types import Session

load_dotenv()


def _has_claude_auth():
    """Check for Claude authentication."""
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    creds_path = Path.home() / ".claude" / ".credentials.json"
    return creds_path.exists()


pytestmark = [
    pytest.mark.skipif(not _has_claude_auth(), reason="No Claude auth"),
    pytest.mark.live,
]


@pytest.fixture
def brain(tmp_path):
    """Brain with shared state manager."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    state_manager = StateManager(db_path=str(tmp_path / "test.db"))
    claude_client = ClaudeClient(
        sandbox_dir=str(sandbox),
        working_dir=str(tmp_path),
    )

    return Brain(
        state_manager=state_manager,
        claude_client=claude_client,
    )


class TestBrainSessionLive:
    """Live tests for Brain session management."""

    @pytest.mark.asyncio
    async def test_multi_user_sessions_isolated(self, brain):
        """Different users have isolated sessions."""
        # User 1 remembers something
        response1 = await brain.process_text(
            user_id="user_alice",
            text="Remember this code: ALPHA999",
            include_audio=False,
        )

        # User 2 remembers something different
        await brain.process_text(
            user_id="user_bob",
            text="Remember this code: BETA888",
            include_audio=False,
        )

        # User 1 recalls - should get ALPHA999, not BETA888
        recall1 = await brain.process_text(
            user_id="user_alice",
            text="What was my code?",
            session_id=response1.session_id,
            include_audio=False,
        )

        assert "ALPHA" in recall1.text.upper() or "999" in recall1.text

    @pytest.mark.asyncio
    async def test_session_continuity_preserves_context(self, brain):
        """Session ID preserves conversation context."""
        # First message
        response1 = await brain.process_text(
            user_id="test_user",
            text="My favorite color is purple",
            include_audio=False,
        )

        # Follow-up with same session
        response2 = await brain.process_text(
            user_id="test_user",
            text="What is my favorite color?",
            session_id=response1.session_id,
            include_audio=False,
        )

        assert "purple" in response2.text.lower()

    @pytest.mark.asyncio
    async def test_session_switch_changes_context(self, brain):
        """Switching sessions changes conversation context."""
        # Session 1 - use a unique user to avoid cross-contamination
        resp1 = await brain.process_text(
            user_id="switch_user_1",
            text="The secret code for this conversation is FLAMINGO. Just confirm you remember it.",
            include_audio=False,
        )
        session1_id = resp1.session_id

        # Session 2 (new session, different user) - different context
        await brain.process_text(
            user_id="switch_user_2",
            text="The secret code for this conversation is ELEPHANT. Just confirm you remember it.",
            include_audio=False,
        )

        # Query session 1 - should know FLAMINGO, not ELEPHANT
        recall1 = await brain.process_text(
            user_id="switch_user_1",
            text="What was the secret code I told you earlier? Reply with ONLY the single code word, nothing else.",
            session_id=session1_id,
            include_audio=False,
        )

        assert "FLAMINGO" in recall1.text.upper()

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_users(self, brain):
        """Concurrent requests from different users work."""

        async def user_task(user_id: str, message: str):
            return await brain.process_text(
                user_id=user_id,
                text=message,
                include_audio=False,
            )

        # Run concurrent requests
        results = await asyncio.gather(
            user_task("user1", "Say exactly: USER1"),
            user_task("user2", "Say exactly: USER2"),
            user_task("user3", "Say exactly: USER3"),
        )

        # All should complete without error
        assert len(results) == 3
        for result in results:
            assert result.text
            assert result.session_id

    @pytest.mark.asyncio
    async def test_create_session_returns_new_session(self, brain):
        """create_session returns a Session with valid fields."""
        session = await brain.create_session("create_session_test_user")

        assert isinstance(session, Session)
        assert session.id
        assert session.user_id == "create_session_test_user"
        assert session.created_at is not None
        assert session.last_active is not None
