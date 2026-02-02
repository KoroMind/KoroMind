"""Unit tests for Brain streaming behavior."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest
from claude_agent_sdk.types import ResultMessage

from koro.core.brain import Brain
from koro.core.types import MessageType, Mode


@dataclass(frozen=True)
class DummyEvent:
    """Event without session_id to ensure safe handling."""

    name: str = "dummy"


@pytest.mark.asyncio
async def test_process_message_stream_updates_session_on_result_only():
    """Ensure streaming handles events without session_id and updates on ResultMessage."""
    state_manager = MagicMock()
    state_manager.update_session = AsyncMock()

    async def mock_stream(_config):
        yield DummyEvent()
        yield ResultMessage(
            subtype="success",
            duration_ms=10,
            duration_api_ms=5,
            is_error=False,
            num_turns=1,
            session_id="sess_new",
            result="ok",
        )

    claude_client = MagicMock()
    claude_client.query_stream = mock_stream

    brain = Brain(
        state_manager=state_manager,
        claude_client=claude_client,
        voice_engine=MagicMock(),
        rate_limiter=MagicMock(),
    )

    events = []
    async for event in brain.process_message_stream(
        user_id="user_1",
        content="hello",
        content_type=MessageType.TEXT,
        session_id="sess_old",
        mode=Mode.GO_ALL,
    ):
        events.append(event)

    assert [type(event) for event in events] == [DummyEvent, ResultMessage]
    state_manager.update_session.assert_awaited_once_with("user_1", "sess_new")
