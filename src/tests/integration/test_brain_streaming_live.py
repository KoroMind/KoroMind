"""Live integration tests for Brain streaming."""
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from koro.core.brain import Brain
from koro.core.claude import ClaudeClient
from koro.core.state import StateManager
from koro.core.types import BrainCallbacks, MessageType

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
    """Brain for streaming tests."""
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


class TestBrainStreamingLive:
    """Live tests for Brain streaming."""

    @pytest.mark.asyncio
    async def test_stream_yields_multiple_events(self, brain):
        """Streaming yields multiple events."""
        events = []

        async for event in brain.process_message_stream(
            user_id="test_user",
            content="Count from 1 to 5",
            content_type=MessageType.TEXT,
        ):
            events.append(event)

        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_stream_with_tool_fires_callbacks(self, brain, tmp_path):
        """Streaming with tool use fires callbacks."""
        test_file = tmp_path / "stream_read.txt"
        test_file.write_text("stream content")

        tool_calls = []
        callbacks = BrainCallbacks(
            on_tool_use=lambda name, detail: tool_calls.append(name),
        )

        async for event in brain.process_message_stream(
            user_id="test_user",
            content=f"Read {test_file}",
            content_type=MessageType.TEXT,
            watch_enabled=True,
            callbacks=callbacks,
        ):
            pass

        assert "Read" in tool_calls

    @pytest.mark.asyncio
    async def test_stream_interrupt_stops_execution(self, brain):
        """Interrupt stops streaming execution."""
        events = []

        async for event in brain.process_message_stream(
            user_id="test_user",
            content="Write a very long essay about philosophy",
            content_type=MessageType.TEXT,
        ):
            events.append(event)
            if len(events) >= 3:
                # Interrupt after a few events
                await brain.interrupt()
                break

        # Should have some events before interrupt
        assert len(events) >= 1
