"""Unit tests for Brain callbacks functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from koro.core.brain import Brain
from koro.core.types import (
    BrainCallbacks,
    MessageType,
    Mode,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
    UserSettings,
)


@pytest.fixture
def mock_state_manager():
    """Mock state manager."""
    mgr = MagicMock()
    mgr.get_current_session = AsyncMock(return_value=None)
    mgr.update_session = AsyncMock()
    mgr.get_settings = AsyncMock(return_value=UserSettings())
    return mgr


@pytest.fixture
def mock_claude_client():
    """Mock Claude client."""
    client = MagicMock()
    client.query = AsyncMock(return_value=("Test response", "session-123", {}))
    return client


@pytest.fixture
def mock_voice_engine():
    """Mock voice engine."""
    engine = MagicMock()
    engine.transcribe = AsyncMock(return_value="Test transcription")
    engine.text_to_speech = AsyncMock(return_value=None)
    return engine


@pytest.fixture
def brain(mock_state_manager, mock_claude_client, mock_voice_engine):
    """Brain instance with mocked dependencies."""
    return Brain(
        state_manager=mock_state_manager,
        claude_client=mock_claude_client,
        voice_engine=mock_voice_engine,
    )


@pytest.mark.asyncio
async def test_callbacks_on_progress_fires(brain, mock_claude_client):
    """Verify on_progress callback is called during processing."""
    progress_calls = []

    callbacks = BrainCallbacks(
        on_progress=lambda msg: progress_calls.append(msg)
    )

    await brain.process_message(
        user_id="user-1",
        content="Hello",
        content_type=MessageType.TEXT,
        callbacks=callbacks,
        include_audio=False,
    )

    # Should have progress updates
    assert len(progress_calls) > 0
    assert any("claude" in msg.lower() for msg in progress_calls)


@pytest.mark.asyncio
async def test_callbacks_on_progress_fires_with_audio(brain, mock_voice_engine):
    """Verify on_progress includes TTS step when audio enabled."""
    progress_calls = []

    # Setup voice engine to return audio
    mock_buffer = MagicMock()
    mock_buffer.read = MagicMock(return_value=b"audio-data")
    mock_voice_engine.text_to_speech = AsyncMock(return_value=mock_buffer)

    callbacks = BrainCallbacks(
        on_progress=lambda msg: progress_calls.append(msg)
    )

    await brain.process_message(
        user_id="user-1",
        content="Hello",
        content_type=MessageType.TEXT,
        callbacks=callbacks,
        include_audio=True,
    )

    # Should include voice response step
    assert any("voice" in msg.lower() for msg in progress_calls)


@pytest.mark.asyncio
async def test_callbacks_on_progress_fires_with_voice_input(brain, mock_voice_engine):
    """Verify on_progress includes transcription step for voice input."""
    progress_calls = []

    callbacks = BrainCallbacks(
        on_progress=lambda msg: progress_calls.append(msg)
    )

    await brain.process_message(
        user_id="user-1",
        content=b"audio-bytes",
        content_type=MessageType.VOICE,
        callbacks=callbacks,
        include_audio=False,
    )

    # Should include transcription step
    assert any("transcrib" in msg.lower() for msg in progress_calls)


@pytest.mark.asyncio
async def test_callbacks_on_tool_use_fires(brain, mock_claude_client):
    """Verify on_tool_use callback is called during watch mode."""
    tool_calls = []

    async def track_tool(tool_name: str, detail: str | None) -> None:
        tool_calls.append((tool_name, detail))

    callbacks = BrainCallbacks(on_tool_use=track_tool)

    # Setup Claude to call tool via on_tool_call in QueryConfig
    async def mock_query(config):
        if config.on_tool_call:
            await config.on_tool_call("test_tool", "test detail")
        return ("Response", "session-1", {})

    mock_claude_client.query = mock_query

    await brain.process_message(
        user_id="user-1",
        content="Use a tool",
        content_type=MessageType.TEXT,
        watch_enabled=True,
        callbacks=callbacks,
        include_audio=False,
    )

    # Callback should have been called
    assert len(tool_calls) == 1
    assert tool_calls[0] == ("test_tool", "test detail")


@pytest.mark.asyncio
async def test_callbacks_on_tool_approval_fires(brain, mock_claude_client):
    """Verify on_tool_approval callback is called in approve mode."""
    approval_calls = []

    async def track_approval(
        tool_name: str,
        tool_input: dict,
        context: ToolPermissionContext,
    ):
        approval_calls.append((tool_name, tool_input))
        return PermissionResultAllow()

    callbacks = BrainCallbacks(on_tool_approval=track_approval)

    # Setup Claude to request approval via QueryConfig
    async def mock_query(config):
        if config.can_use_tool:
            ctx = ToolPermissionContext()
            result = await config.can_use_tool("bash", {"command": "ls"}, ctx)
            assert isinstance(result, PermissionResultAllow)
        return ("Response", "session-1", {})

    mock_claude_client.query = mock_query

    await brain.process_message(
        user_id="user-1",
        content="Run a command",
        content_type=MessageType.TEXT,
        mode=Mode.APPROVE,
        callbacks=callbacks,
        include_audio=False,
    )

    # Approval callback should have been called
    assert len(approval_calls) == 1
    assert approval_calls[0][0] == "bash"
    assert approval_calls[0][1] == {"command": "ls"}


@pytest.mark.asyncio
async def test_callbacks_none_disables_feature(brain, mock_claude_client):
    """Verify None callbacks disable features correctly."""
    # No callbacks = no errors, no tracking
    callbacks = BrainCallbacks(
        on_tool_use=None,
        on_tool_approval=None,
        on_progress=None,
    )

    # Should complete without errors
    result = await brain.process_message(
        user_id="user-1",
        content="Hello",
        content_type=MessageType.TEXT,
        callbacks=callbacks,
        include_audio=False,
    )

    assert result.text == "Test response"
    assert result.session_id == "session-123"


@pytest.mark.asyncio
async def test_callbacks_backward_compat_on_tool_call(brain, mock_claude_client):
    """Verify old on_tool_call parameter still works."""
    tool_calls = []

    async def track_tool(tool_name: str, detail: str | None) -> None:
        tool_calls.append((tool_name, detail))

    # Setup Claude to call tool
    async def mock_query(config):
        if config.on_tool_call:
            await config.on_tool_call("legacy_tool", "legacy detail")
        return ("Response", "session-1", {})

    mock_claude_client.query = mock_query

    # Use old API (no callbacks object)
    await brain.process_message(
        user_id="user-1",
        content="Use a tool",
        content_type=MessageType.TEXT,
        watch_enabled=True,
        on_tool_call=track_tool,
        include_audio=False,
    )

    # Should work with old API
    assert len(tool_calls) == 1
    assert tool_calls[0] == ("legacy_tool", "legacy detail")


@pytest.mark.asyncio
async def test_callbacks_backward_compat_can_use_tool(brain, mock_claude_client):
    """Verify old can_use_tool parameter still works."""
    approval_calls = []

    async def track_approval(tool_name: str, tool_input: dict, context):
        approval_calls.append(tool_name)
        return PermissionResultDeny(message="Test deny")

    # Setup Claude to request approval
    async def mock_query(config):
        if config.can_use_tool:
            ctx = ToolPermissionContext()
            result = await config.can_use_tool("bash", {"command": "ls"}, ctx)
            assert isinstance(result, PermissionResultDeny)
        return ("Response", "session-1", {})

    mock_claude_client.query = mock_query

    # Use old API
    await brain.process_message(
        user_id="user-1",
        content="Run a command",
        content_type=MessageType.TEXT,
        mode=Mode.APPROVE,
        can_use_tool=track_approval,
        include_audio=False,
    )

    # Should work with old API
    assert len(approval_calls) == 1
    assert approval_calls[0] == "bash"


@pytest.mark.asyncio
async def test_callbacks_override_legacy_params(brain, mock_claude_client):
    """Verify callbacks object takes precedence over legacy params."""
    new_calls = []
    old_calls = []

    async def new_callback(tool_name: str, detail: str | None) -> None:
        new_calls.append(tool_name)

    async def old_callback(tool_name: str, detail: str | None) -> None:
        old_calls.append(tool_name)

    # Setup Claude to call tool
    async def mock_query(config):
        if config.on_tool_call:
            await config.on_tool_call("test_tool", None)
        return ("Response", "session-1", {})

    mock_claude_client.query = mock_query

    callbacks = BrainCallbacks(on_tool_use=new_callback)

    # Pass both new and old - new should win
    await brain.process_message(
        user_id="user-1",
        content="Use a tool",
        content_type=MessageType.TEXT,
        watch_enabled=True,
        on_tool_call=old_callback,  # Should be ignored
        callbacks=callbacks,
        include_audio=False,
    )

    # Only new callback should have been called
    assert len(new_calls) == 1
    assert len(old_calls) == 0
