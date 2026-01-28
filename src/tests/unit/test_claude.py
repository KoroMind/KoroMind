"""Tests for koro.claude module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

import koro.core.claude as claude


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Stub subprocess.run used by the Claude module."""
    mock_run = MagicMock()
    monkeypatch.setattr(claude.subprocess, "run", mock_run)
    return mock_run


@pytest.fixture
def mock_sdk_client():
    """Provide a basic Claude SDK client stub."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.query = AsyncMock()

    async def empty_receive():
        if False:
            yield

    client.receive_response = empty_receive
    return client


@pytest.fixture
def patch_sdk_client(monkeypatch, mock_sdk_client):
    """Patch ClaudeSDKClient constructor to return the stub client."""
    monkeypatch.setattr(claude, "ClaudeSDKClient", lambda **_: mock_sdk_client)
    return mock_sdk_client


@pytest.fixture
def reset_default_client(monkeypatch):
    """Reset the default client between tests."""
    monkeypatch.setattr(claude, "_claude_client", None)


class TestLoadMeggContext:
    """Tests for load_megg_context function."""

    def test_returns_output_on_success(self, mock_subprocess_run):
        """load_megg_context returns stdout on success."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=0, stdout="megg context content"
        )

        result = claude.load_megg_context("/test/dir")

        assert result == "megg context content"
        mock_subprocess_run.assert_called_once()

    def test_returns_empty_on_failure(self, mock_subprocess_run):
        """load_megg_context returns empty string on failure."""
        mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="error")

        result = claude.load_megg_context()

        assert result == ""

    def test_returns_empty_on_exception(self, mock_subprocess_run):
        """load_megg_context returns empty string on exception."""
        mock_subprocess_run.side_effect = Exception("command not found")

        result = claude.load_megg_context()

        assert result == ""

    def test_load_megg_context_uses_default_dir(self, monkeypatch, mock_subprocess_run):
        """load_megg_context uses CLAUDE_WORKING_DIR when no dir given."""
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/default/working")
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="context")

        claude.load_megg_context()

        call_kwargs = mock_subprocess_run.call_args.kwargs
        assert call_kwargs["cwd"] == "/default/working"


class TestFormatToolCall:
    """Tests for format_tool_call function."""

    def test_formats_simple_input(self):
        """format_tool_call formats simple tool input."""
        result = claude.format_tool_call("Read", {"file_path": "/test.txt"})

        assert "Tool: Read" in result
        assert "/test.txt" in result

    def test_truncates_long_input(self):
        """format_tool_call truncates long input."""
        long_content = "x" * 1000
        result = claude.format_tool_call("Write", {"content": long_content})

        assert len(result) < 600
        assert "..." in result


class TestGetToolDetail:
    """Tests for get_tool_detail function."""

    @pytest.mark.parametrize(
        "tool_name,tool_input,expected",
        [
            ("Bash", {"command": "ls -la"}, "ls -la"),
            ("Read", {"file_path": "/home/user/file.txt"}, "/home/user/file.txt"),
            ("Edit", {"file_path": "/test.py"}, "/test.py"),
            ("Write", {"file_path": "/output.txt"}, "/output.txt"),
            ("Grep", {"pattern": "TODO"}, "/TODO/"),
            ("Glob", {"pattern": "*.py"}, "*.py"),
            ("UnknownTool", {"data": "value"}, None),
        ],
    )
    def test_tool_detail_extraction(self, tool_name, tool_input, expected):
        """get_tool_detail extracts key detail or returns None."""
        result = claude.get_tool_detail(tool_name, tool_input)

        assert result == expected

    def test_bash_long_command_truncated(self):
        """get_tool_detail truncates long Bash command."""
        long_cmd = "echo " + "x" * 100
        result = claude.get_tool_detail("Bash", {"command": long_cmd})

        assert len(result) <= 83
        assert "..." in result


class TestClaudeClient:
    """Tests for ClaudeClient class."""

    def test_init_with_defaults(self, monkeypatch):
        """ClaudeClient uses default directories."""
        monkeypatch.setattr(claude, "SANDBOX_DIR", "/default/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/default/working")

        client = claude.ClaudeClient()

        assert client.sandbox_dir == "/default/sandbox"
        assert client.working_dir == "/default/working"

    def test_init_with_custom_dirs(self):
        """ClaudeClient accepts custom directories."""
        client = claude.ClaudeClient(
            sandbox_dir="/custom/sandbox", working_dir="/custom/working"
        )

        assert client.sandbox_dir == "/custom/sandbox"
        assert client.working_dir == "/custom/working"

    def test_health_check_success(self, mock_subprocess_run):
        """health_check succeeds with working CLI."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        client = claude.ClaudeClient()

        success, message = client.health_check()

        assert success is True
        assert "OK" in message

    def test_health_check_failure(self, mock_subprocess_run):
        """health_check reports CLI failure."""
        mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="auth error")
        client = claude.ClaudeClient()

        success, message = client.health_check()

        assert success is False
        assert "FAILED" in message

    def test_health_check_exception(self, mock_subprocess_run):
        """health_check handles exceptions."""
        mock_subprocess_run.side_effect = Exception("timeout")
        client = claude.ClaudeClient()

        success, message = client.health_check()

        assert success is False
        assert "FAILED" in message


class TestClaudeClientDefaults:
    """Tests for Claude client default instance management."""

    def test_get_claude_client_creates_instance(
        self, monkeypatch, reset_default_client
    ):
        """get_claude_client creates instance on first call."""
        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        client = claude.get_claude_client()

        assert client is not None
        assert isinstance(client, claude.ClaudeClient)

    def test_get_claude_client_returns_same(self, monkeypatch, reset_default_client):
        """get_claude_client returns same instance."""
        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        client1 = claude.get_claude_client()
        client2 = claude.get_claude_client()

        assert client1 is client2

    def test_set_claude_client_replaces(self, reset_default_client):
        """set_claude_client replaces default instance."""
        custom = claude.ClaudeClient(sandbox_dir="/custom", working_dir="/custom")
        claude.set_claude_client(custom)

        assert claude.get_claude_client() is custom


class TestClaudeClientQuery:
    """Tests for ClaudeClient.query method."""

    @pytest.mark.asyncio
    async def test_query_creates_sandbox_dir(self, tmp_path, patch_sdk_client):
        """query creates sandbox directory if missing."""
        sandbox_dir = tmp_path / "sandbox"
        assert not sandbox_dir.exists()

        client = claude.ClaudeClient(
            sandbox_dir=str(sandbox_dir), working_dir=str(tmp_path)
        )
        await client.query("Hello")

        assert sandbox_dir.exists()

    @pytest.mark.asyncio
    async def test_query_includes_megg_context_for_new_session(
        self, tmp_path, monkeypatch, patch_sdk_client
    ):
        """query includes megg context for new sessions."""
        monkeypatch.setattr(claude, "load_megg_context", lambda _: "Megg context here")

        captured_prompt = {}

        async def capture_query(prompt):
            captured_prompt["value"] = prompt

        patch_sdk_client.query = capture_query

        client = claude.ClaudeClient(
            sandbox_dir=str(tmp_path / "sandbox"), working_dir=str(tmp_path)
        )
        await client.query("Hello", include_megg=True)

        assert "Megg context here" in captured_prompt["value"]

    @pytest.mark.asyncio
    async def test_query_skips_megg_for_continued_session(
        self, tmp_path, monkeypatch, patch_sdk_client
    ):
        """query skips megg context when continuing a session."""
        called = {"megg": False}

        def mock_load_megg(_):
            called["megg"] = True
            return "Megg context"

        monkeypatch.setattr(claude, "load_megg_context", mock_load_megg)

        client = claude.ClaudeClient(
            sandbox_dir=str(tmp_path / "sandbox"), working_dir=str(tmp_path)
        )
        await client.query("Hello", continue_last=True)

        assert called["megg"] is False

    @pytest.mark.asyncio
    async def test_query_handles_sdk_exception(self, tmp_path, monkeypatch):
        """query handles SDK exceptions gracefully."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.query = AsyncMock(side_effect=Exception("SDK error"))

        async def empty_receive():
            if False:
                yield

        mock_client.receive_response = empty_receive
        monkeypatch.setattr(claude, "ClaudeSDKClient", lambda **_: mock_client)

        client = claude.ClaudeClient(
            sandbox_dir=str(tmp_path / "sandbox"), working_dir=str(tmp_path)
        )
        result, session_id, metadata = await client.query("Hello")

        assert "Error" in result
        assert "SDK error" in result


class TestSubprocessShellFalse:
    """Tests to verify subprocess calls use shell=False behavior."""

    def test_load_megg_uses_list_command(self, mock_subprocess_run):
        """load_megg_context uses command list (shell=False behavior)."""
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="")

        claude.load_megg_context("/test")

        call_args = mock_subprocess_run.call_args.args[0]
        assert isinstance(call_args, list)
        assert call_args == ["megg", "context"]

    def test_health_check_uses_list_command(self, mock_subprocess_run):
        """health_check uses command list (shell=False behavior)."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        client = claude.ClaudeClient()
        client.health_check()

        call_args = mock_subprocess_run.call_args.args[0]
        assert isinstance(call_args, list)
        assert "claude" in call_args
