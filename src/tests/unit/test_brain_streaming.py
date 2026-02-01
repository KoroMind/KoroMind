"""Unit tests for Brain streaming functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from koro.core.brain import Brain
from koro.core.types import BrainCallbacks, MessageType


@pytest.fixture
def mock_state_manager():
    """Mock state manager."""
    mgr = MagicMock()
    mgr.get_current_session = AsyncMock(return_value=None)
    mgr.update_session = AsyncMock()
    return mgr


@pytest.fixture
def mock_claude_client():
    """Mock Claude client."""
    client = MagicMock()
    client.query = AsyncMock(return_value=("Response", "session-1", {}))
    return client


@pytest.fixture
def mock_voice_engine():
    """Mock voice engine."""
    engine = MagicMock()
    engine.transcribe = AsyncMock(return_value="transcribed")
    return engine


@pytest.fixture
def brain(mock_state_manager, mock_claude_client, mock_voice_engine):
    """Brain instance with mocked dependencies."""
    return Brain(
        state_manager=mock_state_manager,
        claude_client=mock_claude_client,
        voice_engine=mock_voice_engine,
    )


class TestBrainStreaming:
    """Tests for Brain streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_yields_assistant_message_events(self, brain, mock_claude_client):
        """Stream yields events from Claude client."""
        events = [
            MagicMock(type="assistant_message", text="Hello"),
            MagicMock(type="assistant_message", text=" world"),
        ]

        async def mock_stream(*args, **kwargs):
            for event in events:
                yield event

        mock_claude_client.query_stream = mock_stream

        received = []
        async for event in brain.process_message_stream(
            user_id="user1",
            content="hi",
            content_type=MessageType.TEXT,
        ):
            received.append(event)

        assert len(received) == 2
        assert received[0].text == "Hello"
        assert received[1].text == " world"

    @pytest.mark.asyncio
    async def test_stream_yields_result_message_at_end(self, brain, mock_claude_client):
        """Stream includes result message with metadata."""
        result_event = MagicMock(type="result", session_id="new-session", metadata={"cost": 0.01})

        async def mock_stream(*args, **kwargs):
            yield MagicMock(type="text", text="response")
            yield result_event

        mock_claude_client.query_stream = mock_stream

        received = []
        async for event in brain.process_message_stream(
            user_id="user1",
            content="hi",
            content_type=MessageType.TEXT,
        ):
            received.append(event)

        assert len(received) == 2
        assert received[-1].type == "result"

    @pytest.mark.asyncio
    async def test_stream_captures_session_id(self, brain, mock_claude_client, mock_state_manager):
        """Session ID from stream updates state manager."""
        async def mock_stream(*args, **kwargs):
            yield MagicMock(type="text", text="hi")
            yield MagicMock(session_id="stream-session-123")

        mock_claude_client.query_stream = mock_stream

        async for _ in brain.process_message_stream(
            user_id="user1",
            content="hi",
            content_type=MessageType.TEXT,
        ):
            pass

        # State manager should be updated with new session
        mock_state_manager.update_session.assert_called()

    @pytest.mark.asyncio
    async def test_stream_callbacks_fire_during_execution(self, brain, mock_claude_client):
        """Callbacks fire during streaming."""
        progress_msgs = []

        async def mock_stream(*args, **kwargs):
            yield MagicMock(type="text", text="response")

        mock_claude_client.query_stream = mock_stream

        callbacks = BrainCallbacks(
            on_progress=lambda msg: progress_msgs.append(msg),
        )

        async for _ in brain.process_message_stream(
            user_id="user1",
            content="hi",
            content_type=MessageType.TEXT,
            callbacks=callbacks,
        ):
            pass

        # Should have progress updates
        assert len(progress_msgs) >= 1
