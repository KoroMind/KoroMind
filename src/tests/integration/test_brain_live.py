"""Live integration tests for Brain orchestrator."""

import os

import pytest
from dotenv import load_dotenv

from koro.core.brain import Brain
from koro.core.types import BrainCallbacks, MessageType, Mode, UserSettings

# Load environment variables
load_dotenv()


def _has_claude_auth():
    """Check for Claude authentication."""
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    from pathlib import Path

    creds_path = Path.home() / ".claude" / ".credentials.json"
    return creds_path.exists()


# Skip if no Claude auth
pytestmark = pytest.mark.skipif(
    not _has_claude_auth(), reason="No Claude authentication configured"
)


@pytest.fixture
def brain(tmp_path):
    """Create Brain with temp sandbox."""
    from koro.core.claude import ClaudeClient
    from koro.core.state import StateManager

    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    # Create minimal mocks for state and voice (no real APIs needed)
    state_manager = StateManager(db_path=str(tmp_path / "test.db"))
    claude_client = ClaudeClient(sandbox_dir=str(sandbox), working_dir=str(tmp_path))

    return Brain(
        state_manager=state_manager,
        claude_client=claude_client,
    )


@pytest.mark.live
class TestBrainBasicProcessing:
    """Live tests for Brain message processing."""

    @pytest.mark.asyncio
    async def test_process_text_returns_response(self, brain):
        """Brain processes text and returns response."""
        response = await brain.process_text(
            user_id="test_user",
            text="Say exactly: 'Brain works'",
            include_audio=False,
        )

        assert response.text
        assert len(response.text) > 0
        assert response.session_id

    @pytest.mark.asyncio
    async def test_process_message_with_session(self, brain):
        """Brain maintains session across messages."""
        # First message
        response1 = await brain.process_text(
            user_id="test_user",
            text="Remember this code: ALPHA123",
            include_audio=False,
        )

        # Second message in same session
        response2 = await brain.process_text(
            user_id="test_user",
            text="What code did I tell you?",
            session_id=response1.session_id,
            include_audio=False,
        )

        assert "ALPHA123" in response2.text.upper()


@pytest.mark.live
class TestBrainCallbacksLive:
    """Live tests for Brain callbacks."""

    @pytest.mark.asyncio
    async def test_on_progress_fires_during_processing(self, brain):
        """Progress callback fires during real processing."""
        progress_messages = []

        callbacks = BrainCallbacks(
            on_progress=lambda msg: progress_messages.append(msg),
        )

        await brain.process_text(
            user_id="test_user",
            text="Say hello",
            include_audio=False,
            callbacks=callbacks,
        )

        # Should fire at least once for Claude processing
        assert len(progress_messages) >= 1
        assert any(
            "claude" in msg.lower() or "processing" in msg.lower()
            for msg in progress_messages
        )

    @pytest.mark.asyncio
    async def test_on_tool_use_fires_with_real_tool(self, brain, tmp_path):
        """Tool use callback fires when Claude uses a tool."""
        tools_used = []

        callbacks = BrainCallbacks(
            on_tool_use=lambda name, detail: tools_used.append(name),
        )

        # Create file for Claude to read
        test_file = tmp_path / "test.txt"
        test_file.write_text("Secret: XYZ789")

        await brain.process_message(
            user_id="test_user",
            content=f"Read the file at {test_file} and tell me the secret.",
            content_type=MessageType.TEXT,
            include_audio=False,
            watch_enabled=True,
            callbacks=callbacks,
        )

        assert "Read" in tools_used


@pytest.mark.live
class TestBrainToolExecution:
    """Live tests for Brain tool execution."""

    @pytest.mark.asyncio
    async def test_brain_executes_file_operations(self, brain, tmp_path):
        """Brain can execute file read operations."""
        test_file = tmp_path / "data.txt"
        test_file.write_text("The answer is 42")

        response = await brain.process_text(
            user_id="test_user",
            text=f"What number is in the file {test_file}?",
            include_audio=False,
        )

        assert "42" in response.text

    @pytest.mark.asyncio
    async def test_brain_tracks_tool_calls(self, brain, tmp_path):
        """Brain tracks tool calls in response."""
        test_file = tmp_path / "track.txt"
        test_file.write_text("tracking test")

        response = await brain.process_message(
            user_id="test_user",
            content=f"Read {test_file}",
            content_type=MessageType.TEXT,
            include_audio=False,
            watch_enabled=True,  # Required to track tool calls
        )

        assert len(response.tool_calls) >= 1
        tool_names = [tc.name for tc in response.tool_calls]
        assert "Read" in tool_names


@pytest.mark.live
class TestBrainStreaming:
    """Live tests for Brain streaming."""

    @pytest.mark.asyncio
    async def test_stream_yields_events(self, brain):
        """Brain streaming yields events."""
        events = []

        async for event in brain.process_message_stream(
            user_id="test_user",
            content="Say hello",
            content_type=MessageType.TEXT,
        ):
            events.append(event)

        assert len(events) >= 1


@pytest.mark.live
class TestBrainMetadata:
    """Live tests for Brain response metadata."""

    @pytest.mark.asyncio
    async def test_response_includes_cost(self, brain):
        """Brain response includes cost metadata."""
        response = await brain.process_text(
            user_id="test_user",
            text="Say OK",
            include_audio=False,
        )

        assert "cost" in response.metadata
        assert response.metadata["cost"] > 0

    @pytest.mark.asyncio
    async def test_response_includes_session(self, brain):
        """Brain response includes valid session ID."""
        response = await brain.process_text(
            user_id="test_user",
            text="Hello",
            include_audio=False,
        )

        assert response.session_id
        assert len(response.session_id) > 0


@pytest.mark.live
class TestBrainSettings:
    """Live tests for Brain settings management."""

    @pytest.mark.asyncio
    async def test_get_settings_returns_defaults(self, brain):
        """New user gets default UserSettings."""
        settings = await brain.get_settings("new_user_settings_test")

        assert isinstance(settings, UserSettings)
        assert settings.mode == Mode.GO_ALL
        assert settings.audio_enabled is True

    @pytest.mark.asyncio
    async def test_update_settings_persists(self, brain):
        """Updated settings persist across calls."""
        user_id = "settings_persist_test"

        updated = await brain.update_settings(user_id, mode=Mode.APPROVE)
        assert updated.mode == Mode.APPROVE

        retrieved = await brain.get_settings(user_id)
        assert retrieved.mode == Mode.APPROVE


@pytest.mark.live
class TestBrainRateLimit:
    """Live tests for Brain rate limiting."""

    def test_rate_limit_allows_normal_usage(self, brain):
        """Rate limit allows normal usage."""
        allowed, message = brain.check_rate_limit("rate_limit_test_user")

        assert allowed is True
        assert isinstance(message, str)


@pytest.mark.live
class TestBrainHealthCheck:
    """Live tests for Brain health check."""

    def test_health_check_reports_status(self, brain):
        """Health check returns dict with component statuses."""
        health = brain.health_check()

        assert "claude" in health
        assert isinstance(health["claude"], tuple)
        assert len(health["claude"]) == 2
