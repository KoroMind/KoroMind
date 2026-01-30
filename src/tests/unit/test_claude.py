"""Tests for koro.claude module."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

import koro.core.claude as claude
from koro.core.types import SDKConfig


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
        result, session_id, metadata, tool_calls = await client.query("Hello")

        assert "Error" in result
        assert "SDK error" in result
        assert tool_calls == []  # No tool calls on error


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


class TestClaudeClientSDKConfig:
    """Tests for ClaudeClient SDK config integration."""

    def test_build_mcp_servers_stdio(self):
        """_build_mcp_servers creates stdio server configs."""
        client = claude.ClaudeClient(sandbox_dir="/sandbox", working_dir="/working")
        servers = [
            {"name": "test-server", "type": "stdio", "command": "test-cmd", "args": ["--flag"]}
        ]

        result = client._build_mcp_servers(servers)

        assert "test-server" in result
        # MCP configs are TypedDicts (dicts with type hints)
        assert result["test-server"]["type"] == "stdio"
        assert result["test-server"]["command"] == "test-cmd"
        assert result["test-server"]["args"] == ["--flag"]

    def test_build_mcp_servers_sse(self):
        """_build_mcp_servers creates SSE server configs."""
        client = claude.ClaudeClient(sandbox_dir="/sandbox", working_dir="/working")
        servers = [
            {"name": "sse-server", "type": "sse", "url": "http://localhost:8080", "headers": {"Auth": "token"}}
        ]

        result = client._build_mcp_servers(servers)

        assert "sse-server" in result
        # MCP configs are TypedDicts (dicts with type hints)
        assert result["sse-server"]["type"] == "sse"
        assert result["sse-server"]["url"] == "http://localhost:8080"

    def test_build_mcp_servers_skips_unnamed(self):
        """_build_mcp_servers skips servers without name."""
        client = claude.ClaudeClient(sandbox_dir="/sandbox", working_dir="/working")
        servers = [
            {"type": "stdio", "command": "test-cmd"},  # No name
            {"name": "valid", "type": "stdio", "command": "cmd"},
        ]

        result = client._build_mcp_servers(servers)

        assert len(result) == 1
        assert "valid" in result

    def test_build_agents(self):
        """_build_agents creates agent definitions."""
        client = claude.ClaudeClient(sandbox_dir="/sandbox", working_dir="/working")
        agents = {
            "test-agent": {
                "description": "Test agent description",
                "prompt": "You are a test agent",
                "tools": ["Read", "Write"],
                "model": "test-model",
            }
        }

        result = client._build_agents(agents)

        assert "test-agent" in result
        assert result["test-agent"].description == "Test agent description"
        assert result["test-agent"].prompt == "You are a test agent"
        assert result["test-agent"].tools == ["Read", "Write"]
        assert result["test-agent"].model == "test-model"

    def test_build_sdk_options_basic(self):
        """_build_sdk_options creates basic options."""
        client = claude.ClaudeClient(sandbox_dir="/sandbox", working_dir="/working")
        config = SDKConfig()

        options = client._build_sdk_options(config, "System prompt", "go_all")

        assert options.system_prompt == "System prompt"
        assert options.cwd == "/sandbox"
        assert "/working" in options.add_dirs
        assert "Read" in options.allowed_tools

    def test_build_sdk_options_with_custom_dirs(self):
        """_build_sdk_options uses custom dirs from config."""
        client = claude.ClaudeClient(sandbox_dir="/sandbox", working_dir="/working")
        config = SDKConfig(sandbox_dir="/custom/sandbox", working_dir="/custom/working")

        options = client._build_sdk_options(config, "System prompt", "go_all")

        assert options.cwd == "/custom/sandbox"
        assert "/custom/working" in options.add_dirs

    def test_build_sdk_options_with_model(self):
        """_build_sdk_options sets model from config."""
        client = claude.ClaudeClient(sandbox_dir="/sandbox", working_dir="/working")
        config = SDKConfig(model="claude-sonnet", fallback_model="claude-haiku")

        options = client._build_sdk_options(config, "System prompt", "go_all")

        assert options.model == "claude-sonnet"
        assert options.fallback_model == "claude-haiku"

    def test_build_sdk_options_approve_mode(self):
        """_build_sdk_options sets can_use_tool callback in approve mode."""
        client = claude.ClaudeClient(sandbox_dir="/sandbox", working_dir="/working")
        config = SDKConfig(permission_mode="acceptEdits")

        def my_callback(tool, input, ctx):
            return True

        options = client._build_sdk_options(config, "System prompt", "approve", my_callback)

        assert options.can_use_tool == my_callback
        assert options.permission_mode == "acceptEdits"

    def test_build_sdk_options_with_disallowed_tools(self):
        """_build_sdk_options sets disallowed tools."""
        client = claude.ClaudeClient(sandbox_dir="/sandbox", working_dir="/working")
        config = SDKConfig(disallowed_tools=["Bash", "Write"])

        options = client._build_sdk_options(config, "System prompt", "go_all")

        assert "Bash" in options.disallowed_tools
        assert "Write" in options.disallowed_tools

    @pytest.mark.asyncio
    async def test_query_with_sdk_config(self, tmp_path, patch_sdk_client):
        """query uses provided SDK config."""
        client = claude.ClaudeClient(
            sandbox_dir=str(tmp_path / "sandbox"), working_dir=str(tmp_path)
        )
        config = SDKConfig(
            model="test-model",
            allowed_tools=["Read", "Write"],
        )

        await client.query("Hello", sdk_config=config)

        # Query should complete without error using the config
        patch_sdk_client.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_without_sdk_config_uses_defaults(self, tmp_path, patch_sdk_client):
        """query uses default SDKConfig when none provided."""
        client = claude.ClaudeClient(
            sandbox_dir=str(tmp_path / "sandbox"), working_dir=str(tmp_path)
        )

        # Call without sdk_config
        await client.query("Hello")

        # Should complete without error using defaults
        patch_sdk_client.query.assert_called_once()


class TestClaudeClientHooks:
    """Tests for ClaudeClient hooks integration."""

    def test_build_hooks_returns_none_without_callbacks(self, monkeypatch):
        """_build_hooks returns None when no callbacks provided."""
        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        client = claude.ClaudeClient()
        result = client._build_hooks(None, None)

        assert result is None

    def test_build_hooks_with_tool_calls_list(self, monkeypatch):
        """_build_hooks creates PostToolUse hook to track calls."""
        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        client = claude.ClaudeClient()
        tool_calls = []
        result = client._build_hooks(None, tool_calls)

        assert result is not None
        assert "PostToolUse" in result
        assert len(result["PostToolUse"]) == 1

    def test_build_hooks_with_on_tool_start(self, monkeypatch):
        """_build_hooks creates PreToolUse hook for on_tool_start callback."""
        from koro.core.types import BrainCallbacks

        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        received = {}

        def on_start(name: str, input: dict):
            received["name"] = name
            received["input"] = input

        callbacks = BrainCallbacks(on_tool_start=on_start)
        client = claude.ClaudeClient()
        result = client._build_hooks(callbacks, None)

        assert result is not None
        assert "PreToolUse" in result

    def test_build_hooks_with_on_tool_end(self, monkeypatch):
        """_build_hooks creates PostToolUse hook for on_tool_end callback."""
        from koro.core.types import BrainCallbacks

        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        received = {}

        def on_end(name: str, input: dict, response: Any):
            received["name"] = name
            received["response"] = response

        callbacks = BrainCallbacks(on_tool_end=on_end)
        client = claude.ClaudeClient()
        result = client._build_hooks(callbacks, None)

        assert result is not None
        assert "PostToolUse" in result

    @pytest.mark.asyncio
    async def test_pre_tool_hook_calls_on_tool_start(self, monkeypatch):
        """PreToolUse hook invokes on_tool_start callback."""
        from koro.core.types import BrainCallbacks

        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        received = {}

        def on_start(name: str, input: dict):
            received["name"] = name
            received["input"] = input

        callbacks = BrainCallbacks(on_tool_start=on_start)
        client = claude.ClaudeClient()
        hooks = client._build_hooks(callbacks, None)

        # Get the hook callback
        pre_hook = hooks["PreToolUse"][0].hooks[0]

        # Simulate calling the hook
        result = await pre_hook(
            {"tool_name": "Read", "tool_input": {"file_path": "/test.txt"}},
            "tool_123",
            {},
        )

        assert received["name"] == "Read"
        assert received["input"]["file_path"] == "/test.txt"
        assert result["continue_"] is True

    @pytest.mark.asyncio
    async def test_post_tool_hook_calls_on_tool_end(self, monkeypatch):
        """PostToolUse hook invokes on_tool_end callback."""
        from koro.core.types import BrainCallbacks

        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        received = {}

        def on_end(name: str, input: dict, response: Any):
            received["name"] = name
            received["input"] = input
            received["response"] = response

        callbacks = BrainCallbacks(on_tool_end=on_end)
        client = claude.ClaudeClient()
        hooks = client._build_hooks(callbacks, None)

        # Get the hook callback
        post_hook = hooks["PostToolUse"][0].hooks[0]

        # Simulate calling the hook
        result = await post_hook(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
                "tool_response": "file1.txt\nfile2.txt",
            },
            "tool_456",
            {},
        )

        assert received["name"] == "Bash"
        assert received["input"]["command"] == "ls"
        assert received["response"] == "file1.txt\nfile2.txt"
        assert result["continue_"] is True

    @pytest.mark.asyncio
    async def test_post_tool_hook_tracks_tool_calls(self, monkeypatch):
        """PostToolUse hook appends to tool_calls list."""
        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        tool_calls = []
        client = claude.ClaudeClient()
        hooks = client._build_hooks(None, tool_calls)

        # Get the hook callback
        post_hook = hooks["PostToolUse"][0].hooks[0]

        # Simulate calling the hook
        await post_hook(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "/out.txt", "content": "hello"},
                "tool_response": "Success",
            },
            "tool_789",
            {},
        )

        assert len(tool_calls) == 1
        assert tool_calls[0].name == "Write"
        assert tool_calls[0].detail == "/out.txt"
        assert tool_calls[0].tool_input["content"] == "hello"
        assert tool_calls[0].tool_response == "Success"
        assert tool_calls[0].tool_use_id == "tool_789"

    @pytest.mark.asyncio
    async def test_permission_request_hook(self, monkeypatch):
        """PreToolUse hook handles permission requests."""
        from koro.core.types import BrainCallbacks, PermissionResult

        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        async def on_permission(name: str, input: dict) -> PermissionResult:
            if name == "Bash":
                return PermissionResult(decision="deny", reason="Bash not allowed")
            return PermissionResult(decision="allow")

        callbacks = BrainCallbacks(on_permission_request=on_permission)
        client = claude.ClaudeClient()
        hooks = client._build_hooks(callbacks, None)

        # Get the hook callback
        pre_hook = hooks["PreToolUse"][0].hooks[0]

        # Test deny case
        result = await pre_hook(
            {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}},
            "tool_danger",
            {},
        )

        assert result["continue_"] is False
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "not allowed" in result["hookSpecificOutput"]["permissionDecisionReason"]

        # Test allow case
        result = await pre_hook(
            {"tool_name": "Read", "tool_input": {"file_path": "/safe.txt"}},
            "tool_safe",
            {},
        )

        assert result["continue_"] is True
        assert result["hookSpecificOutput"]["permissionDecision"] == "allow"

    @pytest.mark.asyncio
    async def test_hook_handles_callback_exception(self, monkeypatch):
        """Hooks gracefully handle callback exceptions."""
        from koro.core.types import BrainCallbacks

        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        def on_start_raises(name: str, input: dict):
            raise ValueError("Callback error!")

        callbacks = BrainCallbacks(on_tool_start=on_start_raises)
        client = claude.ClaudeClient()
        hooks = client._build_hooks(callbacks, None)

        # Get the hook callback
        pre_hook = hooks["PreToolUse"][0].hooks[0]

        # Should not raise, should return continue=True
        result = await pre_hook(
            {"tool_name": "Bash", "tool_input": {"command": "ls"}},
            "tool_err",
            {},
        )

        assert result["continue_"] is True

    @pytest.mark.asyncio
    async def test_post_hook_handles_callback_exception(self, monkeypatch):
        """PostToolUse hook handles callback exceptions gracefully."""
        from koro.core.types import BrainCallbacks

        monkeypatch.setattr(claude, "SANDBOX_DIR", "/test/sandbox")
        monkeypatch.setattr(claude, "CLAUDE_WORKING_DIR", "/test/working")

        def on_end_raises(name: str, input: dict, response: Any):
            raise RuntimeError("Post callback error!")

        callbacks = BrainCallbacks(on_tool_end=on_end_raises)
        tool_calls = []
        client = claude.ClaudeClient()
        hooks = client._build_hooks(callbacks, tool_calls)

        # Get the hook callback
        post_hook = hooks["PostToolUse"][0].hooks[0]

        # Should not raise, should return continue=True
        result = await post_hook(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "/test.txt"},
                "tool_response": "ok",
            },
            "tool_post_err",
            {},
        )

        assert result["continue_"] is True
        # Tool call should still be tracked before callback
        assert len(tool_calls) == 1
