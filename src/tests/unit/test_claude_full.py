"""Tests for full Claude SDK integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

from koro.core.claude import ClaudeClient
from koro.core.types import QueryConfig, SandboxSettings


@pytest.fixture
def claude_client():
    return ClaudeClient(sandbox_dir="/tmp/sandbox", working_dir="/tmp/work")


@pytest.mark.asyncio
async def test_build_options_full(claude_client):
    """Test building options with all new parameters."""
    sandbox_settings: SandboxSettings = {"enabled": True}

    # Test complex options
    hooks_mock = {"PreToolUse": []}
    mcp_mock = {"server": {"type": "stdio", "command": "ls"}}
    output_format = {"type": "json_schema", "schema": {}}

    config = QueryConfig(
        prompt="test",
        sandbox=sandbox_settings,
        include_partial_messages=True,
        max_turns=10,
        max_budget_usd=5.0,
        model="claude-3-opus-20240229",
        fallback_model="claude-3-sonnet",
        hooks=hooks_mock,
        mcp_servers=mcp_mock,
        output_format=output_format,
        enable_file_checkpointing=True,
    )
    options = claude_client._build_options(config)

    assert options.sandbox == sandbox_settings
    assert options.include_partial_messages is True
    assert options.max_turns == 10
    assert options.max_budget_usd == 5.0
    assert options.model == "claude-3-opus-20240229"
    assert options.fallback_model == "claude-3-sonnet"
    assert options.hooks == hooks_mock
    assert options.mcp_servers == mcp_mock
    assert options.output_format == output_format
    assert options.enable_file_checkpointing is True
    assert options.allowed_tools  # Should have default tools


@pytest.mark.asyncio
async def test_full_result_metadata(claude_client):
    """Test parsing of all ResultMessage fields."""
    mock_sdk_client = MagicMock()
    mock_sdk_client.query = AsyncMock()
    mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
    mock_sdk_client.__aexit__ = AsyncMock()

    async def mock_receive():
        yield ResultMessage(
            subtype="success",
            result="Done",
            session_id="sess_1",
            duration_ms=100,
            duration_api_ms=50,
            is_error=True,
            num_turns=5,
            total_cost_usd=0.05,
            usage={"input_tokens": 100, "output_tokens": 50},
            structured_output={"key": "value"},
        )

    mock_sdk_client.receive_response = mock_receive

    with patch("koro.core.claude.ClaudeSDKClient", return_value=mock_sdk_client):
        result, session_id, metadata = await claude_client.query(
            QueryConfig(prompt="test")
        )

        assert result == "Done"
        assert metadata["cost"] == 0.05
        assert metadata["num_turns"] == 5
        assert metadata["duration_ms"] == 100
        assert metadata["usage"] == {"input_tokens": 100, "output_tokens": 50}
        assert metadata["structured_output"] == {"key": "value"}
        assert metadata["is_error"] is True


@pytest.mark.asyncio
async def test_stream_event_handling(claude_client):
    """Test handling of StreamEvent in query_stream."""
    mock_sdk_client = MagicMock()
    mock_sdk_client.query = AsyncMock()
    mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
    mock_sdk_client.__aexit__ = AsyncMock()

    stream_event = StreamEvent(
        uuid="evt_1",
        session_id="sess_1",
        event={"type": "content_block_delta", "delta": {"text": "Hello"}},
    )

    async def mock_receive():
        yield stream_event

    mock_sdk_client.receive_response = mock_receive

    with patch("koro.core.claude.ClaudeSDKClient", return_value=mock_sdk_client):
        events = []
        async for event in claude_client.query_stream(
            QueryConfig(prompt="test", include_partial_messages=True)
        ):
            events.append(event)

        assert len(events) == 1
        assert isinstance(events[0], StreamEvent)
        assert events[0].uuid == "evt_1"


@pytest.mark.asyncio
async def test_thinking_block_parsing(claude_client):
    """Test parsing of ThinkingBlock."""
    # Mock client needs to be MagicMock to allow assigning a generator function to a method
    # without it being wrapped in an awaitable by AsyncMock
    mock_sdk_client = MagicMock()
    mock_sdk_client.query = AsyncMock()
    mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
    mock_sdk_client.__aexit__ = AsyncMock()

    # Mock stream response
    async def mock_receive():
        yield AssistantMessage(
            content=[
                ThinkingBlock(thinking="Hmm...", signature="sig"),
                TextBlock(text="Hello"),
            ],
            model="claude-3",
        )
        yield ResultMessage(
            subtype="success",
            result="Hello",
            session_id="sess_1",
            duration_ms=100,
            duration_api_ms=50,
            is_error=False,
            num_turns=1,
            total_cost_usd=0.01,
        )

    # Assign the generator function directly
    mock_sdk_client.receive_response = mock_receive

    with patch("koro.core.claude.ClaudeSDKClient", return_value=mock_sdk_client):
        result, session_id, metadata = await claude_client.query(
            QueryConfig(prompt="test")
        )

        assert result == "Hello"
        assert metadata["thinking"] == "Hmm..."


@pytest.mark.asyncio
async def test_tool_result_tracking(claude_client):
    """Tool result blocks are captured in metadata."""
    mock_sdk_client = MagicMock()
    mock_sdk_client.query = AsyncMock()
    mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
    mock_sdk_client.__aexit__ = AsyncMock()

    async def mock_receive():
        yield AssistantMessage(
            content=[
                ToolUseBlock(id="tool_1", name="Read", input={"path": "README.md"}),
                ToolResultBlock(tool_use_id="tool_1", is_error=False),
            ],
            model="claude-3",
        )
        yield ResultMessage(
            subtype="success",
            duration_ms=10,
            duration_api_ms=5,
            is_error=False,
            num_turns=1,
            session_id="sess_1",
            result="Done",
        )

    mock_sdk_client.receive_response = mock_receive

    with patch("koro.core.claude.ClaudeSDKClient", return_value=mock_sdk_client):
        result, session_id, metadata = await claude_client.query(
            QueryConfig(prompt="test")
        )

        assert result == "Done"
        assert session_id == "sess_1"
        assert metadata["tool_results"] == [
            {"tool_use_id": "tool_1", "name": "Read", "is_error": False}
        ]


@pytest.mark.asyncio
async def test_interrupt(claude_client):
    """Test interrupt method."""
    mock_sdk_client = MagicMock()
    mock_sdk_client.interrupt = AsyncMock()
    mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
    mock_sdk_client.__aexit__ = AsyncMock()

    # Simulate active client
    claude_client._active_client = mock_sdk_client

    success = await claude_client.interrupt()
    assert success is True
    mock_sdk_client.interrupt.assert_called_once()

    # Simulate no active client
    claude_client._active_client = None
    success = await claude_client.interrupt()
    assert success is False


@pytest.mark.asyncio
async def test_query_stream(claude_client):
    """Test query_stream generator."""
    mock_sdk_client = MagicMock()
    mock_sdk_client.query = AsyncMock()
    mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
    mock_sdk_client.__aexit__ = AsyncMock()

    expected_msg = AssistantMessage(
        content=[TextBlock(text="Streamed")], model="claude-3"
    )

    async def mock_receive():
        yield expected_msg

    mock_sdk_client.receive_response = mock_receive

    with patch("koro.core.claude.ClaudeSDKClient", return_value=mock_sdk_client):
        events = []
        async for event in claude_client.query_stream(QueryConfig(prompt="test")):
            events.append(event)

        assert len(events) == 1
        assert events[0] == expected_msg
        # Verify active client was set and cleared
        assert claude_client._active_client is None
