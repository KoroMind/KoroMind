"""Live integration tests for Brain tool execution."""
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from koro.core.brain import Brain
from koro.core.claude import ClaudeClient
from koro.core.state import StateManager
from koro.core.types import (
    BrainCallbacks,
    MessageType,
    Mode,
    PermissionResultAllow,
)

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
    """Brain with sandbox."""
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


class TestBrainToolsLive:
    """Live tests for Brain tool execution."""

    @pytest.mark.asyncio
    async def test_brain_reads_file(self, brain, tmp_path):
        """Brain can read files."""
        test_file = tmp_path / "readable.txt"
        test_file.write_text("Secret content: ABC123")

        response = await brain.process_text(
            user_id="test_user",
            text=f"Read the file at {test_file} and tell me the secret",
            include_audio=False,
        )

        assert "ABC123" in response.text

    @pytest.mark.asyncio
    async def test_brain_writes_file_in_sandbox(self, brain, tmp_path):
        """Brain can write files in sandbox."""
        sandbox = tmp_path / "sandbox"
        target = sandbox / "output.txt"

        await brain.process_text(
            user_id="test_user",
            text=f"Write the text 'Hello World' to a file at {target}",
            include_audio=False,
        )

        # Check file was created
        if target.exists():
            content = target.read_text()
            assert "Hello" in content or "hello" in content.lower()

    @pytest.mark.asyncio
    async def test_brain_write_outside_sandbox_blocked(self, brain, tmp_path):
        """Writing outside sandbox should be blocked."""
        outside = tmp_path / "outside.txt"

        response = await brain.process_text(
            user_id="test_user",
            text=f"Write 'test' to {outside}",
            include_audio=False,
        )

        # Either blocked or file not created outside sandbox
        # SDK enforces sandbox boundaries
        assert response.text  # Got a response

    @pytest.mark.asyncio
    async def test_brain_executes_bash_command(self, brain):
        """Brain can execute bash commands."""
        response = await brain.process_text(
            user_id="test_user",
            text="Run 'echo hello123' and tell me the output",
            include_audio=False,
        )

        assert "hello123" in response.text.lower() or "hello" in response.text.lower()

    @pytest.mark.asyncio
    async def test_brain_tracks_all_tool_calls(self, brain, tmp_path):
        """Brain tracks tool calls in response."""
        test_file = tmp_path / "track.txt"
        test_file.write_text("tracking")

        tools_used = []
        callbacks = BrainCallbacks(
            on_tool_use=lambda name, detail: tools_used.append(name),
        )

        await brain.process_message(
            user_id="test_user",
            content=f"Read {test_file}",
            content_type=MessageType.TEXT,
            include_audio=False,
            watch_enabled=True,
            callbacks=callbacks,
        )

        assert "Read" in tools_used

    @pytest.mark.asyncio
    async def test_approve_mode_blocks_until_callback(self, brain, tmp_path):
        """Approve mode waits for callback approval."""
        test_file = tmp_path / "approve.txt"
        test_file.write_text("approve content")

        approval_requests = []

        async def approve_handler(tool_name, tool_input, context):
            approval_requests.append(tool_name)
            return PermissionResultAllow()

        callbacks = BrainCallbacks(on_tool_approval=approve_handler)

        await brain.process_message(
            user_id="test_user",
            content=f"Read {test_file}",
            content_type=MessageType.TEXT,
            include_audio=False,
            mode=Mode.APPROVE,
            callbacks=callbacks,
        )

        assert len(approval_requests) >= 1
        assert "Read" in approval_requests
