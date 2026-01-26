"""Tests for koro.claude module."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from koro.claude import (
    load_megg_context,
    format_tool_call,
    get_tool_detail,
    ClaudeClient,
)


class TestLoadMeggContext:
    """Tests for load_megg_context function."""

    def test_returns_output_on_success(self):
        """load_megg_context returns stdout on success."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="megg context content"
            )

            result = load_megg_context("/test/dir")

            assert result == "megg context content"
            mock_run.assert_called_once()

    def test_returns_empty_on_failure(self):
        """load_megg_context returns empty string on failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="error"
            )

            result = load_megg_context()

            assert result == ""

    def test_returns_empty_on_exception(self):
        """load_megg_context returns empty string on exception."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("command not found")

            result = load_megg_context()

            assert result == ""


class TestFormatToolCall:
    """Tests for format_tool_call function."""

    def test_formats_simple_input(self):
        """format_tool_call formats simple tool input."""
        result = format_tool_call("Read", {"file_path": "/test.txt"})

        assert "Tool: Read" in result
        assert "file_path" in result
        assert "/test.txt" in result

    def test_truncates_long_input(self):
        """format_tool_call truncates long input."""
        long_content = "x" * 1000
        result = format_tool_call("Write", {"content": long_content})

        assert len(result) < 600
        assert "..." in result


class TestGetToolDetail:
    """Tests for get_tool_detail function."""

    def test_bash_command(self):
        """get_tool_detail extracts Bash command."""
        result = get_tool_detail("Bash", {"command": "ls -la"})
        assert result == "ls -la"

    def test_bash_long_command_truncated(self):
        """get_tool_detail truncates long Bash command."""
        long_cmd = "echo " + "x" * 100
        result = get_tool_detail("Bash", {"command": long_cmd})
        assert len(result) <= 83
        assert "..." in result

    def test_read_file_path(self):
        """get_tool_detail extracts Read file path."""
        result = get_tool_detail("Read", {"file_path": "/home/user/file.txt"})
        assert result == "/home/user/file.txt"

    def test_edit_file_path(self):
        """get_tool_detail extracts Edit file path."""
        result = get_tool_detail("Edit", {"file_path": "/test.py"})
        assert result == "/test.py"

    def test_write_file_path(self):
        """get_tool_detail extracts Write file path."""
        result = get_tool_detail("Write", {"file_path": "/output.txt"})
        assert result == "/output.txt"

    def test_grep_pattern(self):
        """get_tool_detail extracts Grep pattern."""
        result = get_tool_detail("Grep", {"pattern": "TODO"})
        assert result == "/TODO/"

    def test_glob_pattern(self):
        """get_tool_detail extracts Glob pattern."""
        result = get_tool_detail("Glob", {"pattern": "*.py"})
        assert result == "*.py"

    def test_unknown_tool_returns_none(self):
        """get_tool_detail returns None for unknown tools."""
        result = get_tool_detail("UnknownTool", {"data": "value"})
        assert result is None


class TestClaudeClient:
    """Tests for ClaudeClient class."""

    def test_init_with_defaults(self, monkeypatch):
        """ClaudeClient uses default directories."""
        monkeypatch.setattr("koro.claude.SANDBOX_DIR", "/default/sandbox")
        monkeypatch.setattr("koro.claude.CLAUDE_WORKING_DIR", "/default/working")

        client = ClaudeClient()

        assert client.sandbox_dir == "/default/sandbox"
        assert client.working_dir == "/default/working"

    def test_init_with_custom_dirs(self):
        """ClaudeClient accepts custom directories."""
        client = ClaudeClient(
            sandbox_dir="/custom/sandbox",
            working_dir="/custom/working"
        )

        assert client.sandbox_dir == "/custom/sandbox"
        assert client.working_dir == "/custom/working"

    def test_health_check_success(self):
        """health_check succeeds with working CLI."""
        client = ClaudeClient()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            success, message = client.health_check()

            assert success is True
            assert "OK" in message

    def test_health_check_failure(self):
        """health_check reports CLI failure."""
        client = ClaudeClient()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="auth error"
            )

            success, message = client.health_check()

            assert success is False
            assert "FAILED" in message

    def test_health_check_exception(self):
        """health_check handles exceptions."""
        client = ClaudeClient()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("timeout")

            success, message = client.health_check()

            assert success is False
            assert "FAILED" in message


class TestClaudeClientDefaults:
    """Tests for Claude client default instance management."""

    def test_get_claude_client_creates_instance(self, monkeypatch):
        """get_claude_client creates instance on first call."""
        monkeypatch.setattr("koro.claude.SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr("koro.claude.CLAUDE_WORKING_DIR", "/test/working")

        import koro.claude
        koro.claude._claude_client = None

        client = koro.claude.get_claude_client()

        assert client is not None
        assert isinstance(client, ClaudeClient)

    def test_get_claude_client_returns_same(self, monkeypatch):
        """get_claude_client returns same instance."""
        monkeypatch.setattr("koro.claude.SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr("koro.claude.CLAUDE_WORKING_DIR", "/test/working")

        import koro.claude
        koro.claude._claude_client = None

        client1 = koro.claude.get_claude_client()
        client2 = koro.claude.get_claude_client()

        assert client1 is client2

    def test_set_claude_client_replaces(self, monkeypatch):
        """set_claude_client replaces default instance."""
        import koro.claude

        custom = ClaudeClient(sandbox_dir="/custom", working_dir="/custom")
        koro.claude.set_claude_client(custom)

        assert koro.claude.get_claude_client() is custom


class TestClaudeClientQuery:
    """Tests for ClaudeClient.query method."""

    @pytest.mark.asyncio
    async def test_query_creates_sandbox_dir(self, tmp_path, monkeypatch):
        """query creates sandbox directory if missing."""
        sandbox_dir = tmp_path / "sandbox"
        assert not sandbox_dir.exists()

        # Mock the SDK client
        mock_sdk_client = MagicMock()
        mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
        mock_sdk_client.__aexit__ = AsyncMock(return_value=None)
        mock_sdk_client.query = AsyncMock()

        async def mock_receive():
            return
            yield  # Empty async generator

        mock_sdk_client.receive_response = mock_receive

        with patch("koro.claude.ClaudeSDKClient", return_value=mock_sdk_client):
            client = ClaudeClient(
                sandbox_dir=str(sandbox_dir),
                working_dir=str(tmp_path)
            )
            await client.query("Hello")

        assert sandbox_dir.exists()

    @pytest.mark.asyncio
    async def test_query_includes_megg_context_for_new_session(self, tmp_path, monkeypatch):
        """query includes megg context for new sessions."""
        monkeypatch.setattr("koro.claude.load_megg_context", lambda x: "Megg context here")

        mock_sdk_client = MagicMock()
        mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
        mock_sdk_client.__aexit__ = AsyncMock(return_value=None)
        captured_prompt = None

        async def capture_query(prompt):
            nonlocal captured_prompt
            captured_prompt = prompt

        mock_sdk_client.query = capture_query

        async def mock_receive():
            return
            yield

        mock_sdk_client.receive_response = mock_receive

        with patch("koro.claude.ClaudeSDKClient", return_value=mock_sdk_client):
            client = ClaudeClient(
                sandbox_dir=str(tmp_path / "sandbox"),
                working_dir=str(tmp_path)
            )
            await client.query("Hello", include_megg=True)

        assert captured_prompt is not None
        assert "Megg context here" in captured_prompt

    @pytest.mark.asyncio
    async def test_query_skips_megg_for_continued_session(self, tmp_path, monkeypatch):
        """query skips megg context when continuing a session."""
        megg_called = False

        def mock_load_megg(x):
            nonlocal megg_called
            megg_called = True
            return "Megg context"

        monkeypatch.setattr("koro.claude.load_megg_context", mock_load_megg)

        mock_sdk_client = MagicMock()
        mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
        mock_sdk_client.__aexit__ = AsyncMock(return_value=None)
        mock_sdk_client.query = AsyncMock()

        async def mock_receive():
            return
            yield

        mock_sdk_client.receive_response = mock_receive

        with patch("koro.claude.ClaudeSDKClient", return_value=mock_sdk_client):
            client = ClaudeClient(
                sandbox_dir=str(tmp_path / "sandbox"),
                working_dir=str(tmp_path)
            )
            await client.query("Hello", continue_last=True)

        # Megg should not be called for continued sessions
        assert not megg_called

    @pytest.mark.asyncio
    async def test_query_handles_sdk_exception(self, tmp_path, monkeypatch):
        """query handles SDK exceptions gracefully."""
        mock_sdk_client = MagicMock()
        mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
        mock_sdk_client.__aexit__ = AsyncMock(return_value=None)
        mock_sdk_client.query = AsyncMock(side_effect=Exception("SDK error"))

        with patch("koro.claude.ClaudeSDKClient", return_value=mock_sdk_client):
            client = ClaudeClient(
                sandbox_dir=str(tmp_path / "sandbox"),
                working_dir=str(tmp_path)
            )
            result, session_id, metadata = await client.query("Hello")

        assert "Error" in result
        assert "SDK error" in result

    def test_load_megg_context_uses_default_dir(self, monkeypatch):
        """load_megg_context uses CLAUDE_WORKING_DIR when no dir given."""
        monkeypatch.setattr("koro.claude.CLAUDE_WORKING_DIR", "/default/working")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="context")

            from koro.claude import load_megg_context
            load_megg_context()

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["cwd"] == "/default/working"


class TestSubprocessShellFalse:
    """Tests to verify subprocess calls use shell=False behavior."""

    def test_load_megg_uses_list_command(self):
        """load_megg_context uses command list (shell=False behavior)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")

            from koro.claude import load_megg_context
            load_megg_context("/test")

            call_args = mock_run.call_args[0][0]
            # Should be a list, not a string
            assert isinstance(call_args, list)
            assert call_args == ["megg", "context"]

    def test_health_check_uses_list_command(self):
        """health_check uses command list (shell=False behavior)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            client = ClaudeClient()
            client.health_check()

            call_args = mock_run.call_args[0][0]
            # Should be a list, not a string
            assert isinstance(call_args, list)
            assert "claude" in call_args
