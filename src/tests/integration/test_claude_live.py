"""Live integration tests for Claude SDK."""

import os

import pytest
from claude_agent_sdk.types import ResultMessage
from dotenv import load_dotenv

from koro.core.claude import ClaudeClient
from koro.core.types import QueryConfig

# Load environment variables
load_dotenv()


# Check for Claude auth - also check credentials file
def _has_claude_auth():
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    # Check credentials file
    from pathlib import Path

    creds_path = Path.home() / ".claude" / ".credentials.json"
    return creds_path.exists()


# Skip if no Claude auth
pytestmark = pytest.mark.skipif(
    not _has_claude_auth(), reason="No Claude authentication configured"
)


@pytest.fixture
def claude_client(tmp_path):
    """Create Claude client with temp sandbox."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    return ClaudeClient(sandbox_dir=str(sandbox), working_dir=str(tmp_path))


def _query_config(prompt: str, **kwargs) -> QueryConfig:
    """Build query config with MEGG disabled for deterministic live tests."""
    return QueryConfig(prompt=prompt, include_megg=False, **kwargs)


@pytest.mark.live
class TestClaudeHealthCheck:
    """Live tests for Claude health check."""

    def test_health_check_passes(self, claude_client):
        """Health check passes with valid auth."""
        success, message = claude_client.health_check()

        assert success is True
        assert "OK" in message


@pytest.mark.live
class TestClaudeQuery:
    """Live tests for Claude queries."""

    @pytest.mark.asyncio
    async def test_simple_query(self, claude_client):
        """Simple query returns response."""
        response, session_id, metadata = await claude_client.query(
            _query_config("Say exactly: 'Hello test'")
        )

        assert response
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_query_returns_session_id(self, claude_client):
        """Query returns session ID for continuation."""
        response, session_id, metadata = await claude_client.query(
            _query_config("Remember this number: 42")
        )

        assert session_id is not None
        assert len(session_id) > 0

    @pytest.mark.asyncio
    async def test_session_continuation(self, claude_client):
        """Session continuation preserves context."""
        # First message
        _, session_id, _ = await claude_client.query(
            _query_config("Remember this secret word: banana")
        )

        # Continue session
        response, _, _ = await claude_client.query(
            _query_config(
                "What was the secret word I told you?",
                session_id=session_id,
            )
        )

        assert "banana" in response.lower()


@pytest.mark.live
class TestClaudeToolUse:
    """Live tests for Claude tool usage."""

    @pytest.mark.asyncio
    async def test_read_tool(self, claude_client, tmp_path):
        """Claude can read files."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is test content 12345")

        response, _, metadata = await claude_client.query(
            _query_config(f"Read the file at {test_file} and tell me what number is in it.")
        )

        assert "12345" in response

    @pytest.mark.asyncio
    async def test_tool_callback(self, claude_client, tmp_path):
        """Tool callback is invoked."""
        test_file = tmp_path / "callback_test.txt"
        test_file.write_text("Callback test content")

        tools_called = []

        async def on_tool(name, detail):
            tools_called.append(name)

        await claude_client.query(_query_config(f"Read {test_file}", on_tool_call=on_tool))

        assert "Read" in tools_called


@pytest.mark.live
class TestClaudeStreaming:
    """Live tests for Claude streaming."""

    @pytest.mark.asyncio
    async def test_stream_yields_events(self, claude_client):
        """Streaming yields multiple events."""
        events = []
        async for event in claude_client.query_stream(_query_config("Say hello")):
            events.append(type(event).__name__)

        # Should have at least AssistantMessage and ResultMessage
        assert len(events) >= 2
        assert "ResultMessage" in events

    @pytest.mark.asyncio
    async def test_stream_result_contains_text(self, claude_client):
        """Streaming result contains response text."""
        result_text = None
        async for event in claude_client.query_stream(
            _query_config("Say exactly: 'streaming works'")
        ):
            if isinstance(event, ResultMessage):
                result_text = event.result

        assert result_text is not None
        assert "streaming" in result_text.lower() or "works" in result_text.lower()


@pytest.mark.live
class TestClaudeMetadata:
    """Live tests for Claude response metadata."""

    @pytest.mark.asyncio
    async def test_metadata_includes_cost(self, claude_client):
        """Response metadata includes cost."""
        _, _, metadata = await claude_client.query(_query_config("Say OK"))

        assert "cost" in metadata
        assert metadata["cost"] > 0

    @pytest.mark.asyncio
    async def test_metadata_includes_turns(self, claude_client):
        """Response metadata includes turn count."""
        _, _, metadata = await claude_client.query(_query_config("Say OK"))

        assert "num_turns" in metadata
        assert metadata["num_turns"] >= 1

    @pytest.mark.asyncio
    async def test_metadata_includes_tool_count(self, claude_client, tmp_path):
        """Response metadata tracks tool usage."""
        test_file = tmp_path / "tool_count.txt"
        test_file.write_text("test")

        _, _, metadata = await claude_client.query(_query_config(f"Read {test_file}"))

        assert "tool_count" in metadata
        assert metadata["tool_count"] >= 1
