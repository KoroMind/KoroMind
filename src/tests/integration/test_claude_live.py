"""Live integration tests for Claude SDK."""

import os

import pytest
from dotenv import load_dotenv

from koro.claude import ClaudeClient

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
        response, session_id, metadata, tool_calls = await claude_client.query(
            "Say exactly: 'Hello test'", include_megg=False
        )

        assert response
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_query_returns_session_id(self, claude_client):
        """Query returns session ID for continuation."""
        response, session_id, metadata, tool_calls = await claude_client.query(
            "Remember this number: 42", include_megg=False
        )

        assert session_id is not None
        assert len(session_id) > 0

    @pytest.mark.asyncio
    async def test_session_continuation(self, claude_client):
        """Session continuation preserves context."""
        # First message
        _, session_id, _, _ = await claude_client.query(
            "Remember this secret word: banana", include_megg=False
        )

        # Continue session
        response, _, _, _ = await claude_client.query(
            "What was the secret word I told you?",
            session_id=session_id,
            include_megg=False,
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

        response, _, metadata, tool_calls = await claude_client.query(
            f"Read the file at {test_file} and tell me what number is in it.",
            include_megg=False,
        )

        assert "12345" in response

    @pytest.mark.asyncio
    async def test_tool_callback(self, claude_client, tmp_path):
        """Tool callback is invoked."""
        test_file = tmp_path / "callback_test.txt"
        test_file.write_text("Callback test content")

        tools_called = []

        def on_tool(name, detail):
            tools_called.append(name)

        await claude_client.query(
            f"Read {test_file}", include_megg=False, on_tool_call=on_tool
        )

        assert "Read" in tools_called
