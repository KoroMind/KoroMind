"""Claude SDK wrapper for agent interactions."""

import json
import logging
import os
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    CLINotFoundError,
    ProcessError,
)

logger = logging.getLogger(__name__)
from claude_agent_sdk.types import (
    AgentDefinition,
    AssistantMessage,
    HookEvent,
    HookMatcher,
    McpServerConfig,
    ResultMessage,
    SandboxSettings,
    SdkPluginConfig,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
)

from koro.core.config import CLAUDE_WORKING_DIR, SANDBOX_DIR
from koro.core.prompt import get_prompt_manager
from koro.core.types import CanUseTool, OnToolCall, OutputFormat


def load_megg_context(working_dir: str = None) -> str:
    """
    Load megg context for enhanced prompts.

    Args:
        working_dir: Directory to run megg in

    Returns:
        Megg context string or empty string on failure
    """
    cwd = working_dir or CLAUDE_WORKING_DIR
    try:
        result = subprocess.run(
            ["megg", "context"], capture_output=True, text=True, timeout=10, cwd=cwd
        )
        if result.returncode == 0:
            return result.stdout
        return ""
    except Exception:
        return ""


def format_tool_call(tool_name: str, tool_input: dict) -> str:
    """
    Format a tool call for display.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters

    Returns:
        Formatted string for display
    """
    input_str = json.dumps(tool_input, indent=2)
    if len(input_str) > 500:
        input_str = input_str[:500] + "..."
    return f"Tool: {tool_name}\n```\n{input_str}\n```"


def get_tool_detail(tool_name: str, tool_input: dict) -> str | None:
    """
    Extract key detail from tool input for display.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters

    Returns:
        Brief detail string or None
    """
    if tool_name == "Bash" and "command" in tool_input:
        cmd = tool_input["command"]
        return cmd[:80] + "..." if len(cmd) > 80 else cmd
    elif tool_name == "Read" and "file_path" in tool_input:
        return tool_input["file_path"]
    elif tool_name == "Edit" and "file_path" in tool_input:
        return tool_input["file_path"]
    elif tool_name == "Write" and "file_path" in tool_input:
        return tool_input["file_path"]
    elif tool_name == "Grep" and "pattern" in tool_input:
        return f"/{tool_input['pattern']}/"
    elif tool_name == "Glob" and "pattern" in tool_input:
        return tool_input["pattern"]
    return None


class ClaudeClient:
    """Wrapper for Claude SDK interactions."""

    def __init__(
        self,
        sandbox_dir: str = None,
        working_dir: str = None,
    ):
        """
        Initialize Claude client.

        Args:
            sandbox_dir: Directory for Claude to write/execute
            working_dir: Directory Claude can read from
        """
        self.sandbox_dir = sandbox_dir or SANDBOX_DIR
        self.working_dir = working_dir or CLAUDE_WORKING_DIR
        self.prompt_manager = get_prompt_manager()
        self._active_client: ClaudeSDKClient | None = None
        logger.debug(
            f"ClaudeClient initialized: sandbox_dir={self.sandbox_dir}, "
            f"working_dir={self.working_dir}, "
            f"CLAUDE_CODE_OAUTH_TOKEN={'set' if os.environ.get('CLAUDE_CODE_OAUTH_TOKEN') else 'not set'}, "
            f"ANTHROPIC_API_KEY={'set' if os.environ.get('ANTHROPIC_API_KEY') else 'not set'}"
        )

    async def interrupt(self) -> bool:
        """
        Interrupt the currently active query.

        Returns:
            True if interrupt was sent, False if no active client
        """
        if self._active_client:
            await self._active_client.interrupt()
            return True
        return False

    def _build_options(
        self,
        user_settings: dict | None,
        mode: str,
        can_use_tool: CanUseTool | None,
        # Vault config options
        cwd: str | None = None,
        add_dirs: list[str] | None = None,
        system_prompt_file: str | None = None,
        # Full SDK options
        hooks: dict[HookEvent, list[HookMatcher]] | None = None,
        mcp_servers: dict[str, McpServerConfig] | None = None,
        agents: dict[str, AgentDefinition] | None = None,
        plugins: list[SdkPluginConfig] | None = None,
        sandbox: SandboxSettings | None = None,
        output_format: OutputFormat | None = None,
        max_turns: int | None = None,
        max_budget_usd: float | None = None,
        model: str | None = None,
        fallback_model: str | None = None,
        include_partial_messages: bool = False,
        enable_file_checkpointing: bool = False,
    ) -> ClaudeAgentOptions:
        """Build SDK options from parameters."""
        # Determine system prompt: vault file > prompt manager
        if system_prompt_file:
            prompt_path = Path(system_prompt_file)
            if prompt_path.exists():
                system_prompt = prompt_path.read_text()
                logger.debug(f"Loaded system prompt from vault: {system_prompt_file}")
            else:
                logger.warning(f"System prompt file not found: {system_prompt_file}")
                system_prompt = self.prompt_manager.get_prompt(user_settings)
        else:
            system_prompt = self.prompt_manager.get_prompt(user_settings)

        # Determine cwd: vault > sandbox_dir
        effective_cwd = cwd or self.sandbox_dir
        logger.debug(f"Using cwd: {effective_cwd}")

        # Determine add_dirs: vault > working_dir
        effective_add_dirs = add_dirs or [self.working_dir]
        logger.debug(f"Using add_dirs: {effective_add_dirs}")

        # Base options
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            cwd=effective_cwd,
            add_dirs=effective_add_dirs,
            # Pass through new options
            hooks=hooks,
            mcp_servers=mcp_servers,
            agents=agents,
            plugins=plugins,
            sandbox=sandbox,
            output_format=output_format,
            max_turns=max_turns,
            max_budget_usd=max_budget_usd,
            model=model,
            fallback_model=fallback_model,
            include_partial_messages=include_partial_messages,
            enable_file_checkpointing=enable_file_checkpointing,
        )

        logger.debug(f"Built options: model={model}, max_turns={max_turns}")

        # Set permission mode and tools based on mode
        if mode == "approve" and can_use_tool:
            options.can_use_tool = can_use_tool
            options.permission_mode = "default"
        else:
            options.allowed_tools = [
                "Read",
                "Grep",
                "Glob",
                "WebSearch",
                "WebFetch",
                "Task",
                "Bash",
                "Edit",
                "Write",
                "Skill",
            ]

        logger.debug(
            f"Built options: model={model}, max_turns={max_turns}, "
            f"cwd={self.sandbox_dir}, mode={mode}, "
            f"hooks={bool(hooks)}, mcp_servers={bool(mcp_servers)}"
        )
        return options

    async def query(
        self,
        prompt: str,
        session_id: str | None = None,
        continue_last: bool = False,
        include_megg: bool = True,
        user_settings: dict | None = None,
        mode: str = "go_all",
        on_tool_call: OnToolCall | None = None,
        can_use_tool: CanUseTool | None = None,
        # Vault config options
        cwd: str | None = None,
        add_dirs: list[str] | None = None,
        system_prompt_file: str | None = None,
        # Full SDK options
        hooks: dict[HookEvent, list[HookMatcher]] | None = None,
        mcp_servers: dict[str, McpServerConfig] | None = None,
        agents: dict[str, AgentDefinition] | None = None,
        plugins: list[SdkPluginConfig] | None = None,
        sandbox: SandboxSettings | None = None,
        output_format: OutputFormat | None = None,
        max_turns: int | None = None,
        max_budget_usd: float | None = None,
        model: str | None = None,
        fallback_model: str | None = None,
        include_partial_messages: bool = False,
        enable_file_checkpointing: bool = False,
    ) -> tuple[str, str, dict]:
        """
        Query Claude and return response.
        """
        logger.debug(
            f"Query starting: session_id={session_id}, continue_last={continue_last}, "
            f"mode={mode}, model={model}"
        )

        # Ensure sandbox exists
        Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True)

        # Build prompt with megg context
        full_prompt = prompt
        if include_megg and not continue_last and not session_id:
            megg_ctx = load_megg_context(self.working_dir)
            if megg_ctx:
                full_prompt = f"<context>\n{megg_ctx}\n</context>\n\n{prompt}"
                logger.debug("Added megg context to prompt")

        # Build options
        options = self._build_options(
            user_settings=user_settings,
            mode=mode,
            can_use_tool=can_use_tool,
            cwd=cwd,
            add_dirs=add_dirs,
            system_prompt_file=system_prompt_file,
            hooks=hooks,
            mcp_servers=mcp_servers,
            agents=agents,
            plugins=plugins,
            sandbox=sandbox,
            output_format=output_format,
            max_turns=max_turns,
            max_budget_usd=max_budget_usd,
            model=model,
            fallback_model=fallback_model,
            include_partial_messages=include_partial_messages,
            enable_file_checkpointing=enable_file_checkpointing,
        )

        # Handle session continuation
        if continue_last:
            options.continue_conversation = True
        elif session_id:
            options.resume = session_id

        result_text = ""
        new_session_id = session_id
        metadata = {}
        tool_count = 0
        thinking_content = ""

        try:
            async with ClaudeSDKClient(options=options) as client:
                self._active_client = client
                try:
                    await client.query(full_prompt)
                    async for message in client.receive_response():
                        if isinstance(message, AssistantMessage):
                            for block in message.content:
                                if isinstance(block, TextBlock):
                                    result_text += block.text
                                elif isinstance(block, ToolUseBlock):
                                    tool_count += 1
                                    if on_tool_call:
                                        tool_input = block.input or {}
                                        detail = get_tool_detail(block.name, tool_input)
                                        on_tool_call(block.name, detail)
                                elif isinstance(block, ThinkingBlock):
                                    thinking_content += block.thinking

                        elif isinstance(message, ResultMessage):
                            if hasattr(message, "result") and message.result:
                                result_text = message.result
                            if hasattr(message, "session_id") and message.session_id:
                                new_session_id = message.session_id
                            if hasattr(message, "total_cost_usd"):
                                metadata["cost"] = message.total_cost_usd
                            if hasattr(message, "num_turns"):
                                metadata["num_turns"] = message.num_turns
                            if hasattr(message, "duration_ms"):
                                metadata["duration_ms"] = message.duration_ms
                            if hasattr(message, "usage"):
                                metadata["usage"] = message.usage
                            if hasattr(message, "structured_output"):
                                metadata["structured_output"] = (
                                    message.structured_output
                                )
                            if hasattr(message, "is_error"):
                                metadata["is_error"] = message.is_error
                finally:
                    self._active_client = None

            metadata["tool_count"] = tool_count
            if thinking_content:
                metadata["thinking"] = thinking_content

            logger.debug(
                f"Query complete: session_id={new_session_id}, "
                f"tools={tool_count}, cost={metadata.get('cost')}, "
                f"turns={metadata.get('num_turns')}"
            )
            return result_text, new_session_id, metadata

        except CLINotFoundError:
            logger.error("Claude CLI not found")
            return (
                "Error: Claude CLI not found. Please install claude-code.",
                session_id or "",
                {"error": "cli_not_found"},
            )
        except CLIConnectionError as e:
            logger.error(f"Claude CLI connection failed: {e}")
            return (
                f"Error: Failed to connect to Claude CLI: {e}",
                session_id or "",
                {"error": "connection_failed"},
            )
        except ProcessError as e:
            logger.error(f"Claude process failed: exit={e.exit_code}")
            return (
                f"Error: Claude process failed (exit {e.exit_code}): {e}",
                session_id or "",
                {"error": "process_error", "exit_code": e.exit_code},
            )
        except Exception as e:
            logger.exception(f"Unexpected error calling Claude: {e}")
            return f"Error calling Claude: {e}", session_id or "", {"error": str(e)}

    async def query_stream(
        self,
        prompt: str,
        session_id: str | None = None,
        continue_last: bool = False,
        include_megg: bool = True,
        user_settings: dict | None = None,
        mode: str = "go_all",
        on_tool_call: OnToolCall | None = None,
        can_use_tool: CanUseTool | None = None,
        **kwargs,
    ) -> AsyncIterator[Any]:
        """
        Query Claude and yield events (StreamEvent or messages).
        """
        logger.debug(f"Stream query starting: session_id={session_id}, mode={mode}")

        # Ensure partial messages are enabled for streaming
        kwargs["include_partial_messages"] = True

        # Ensure sandbox exists
        Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True)

        full_prompt = prompt
        if include_megg and not continue_last and not session_id:
            megg_ctx = load_megg_context(self.working_dir)
            if megg_ctx:
                full_prompt = f"<context>\n{megg_ctx}\n</context>\n\n{prompt}"

        options = self._build_options(
            user_settings=user_settings,
            mode=mode,
            can_use_tool=can_use_tool,
            **kwargs,
        )

        if continue_last:
            options.continue_conversation = True
        elif session_id:
            options.resume = session_id

        try:
            async with ClaudeSDKClient(options=options) as client:
                self._active_client = client
                try:
                    await client.query(full_prompt)
                    async for message in client.receive_response():
                        # Pass through on_tool_call side effect
                        if isinstance(message, AssistantMessage):
                            for block in message.content:
                                if isinstance(block, ToolUseBlock) and on_tool_call:
                                    tool_input = block.input or {}
                                    detail = get_tool_detail(block.name, tool_input)
                                    on_tool_call(block.name, detail)
                        yield message
                finally:
                    self._active_client = None

        except Exception as e:
            # Yield error as a special event or re-raise
            # For simplicity, we yield an error dict
            yield {"error": str(e)}

    def health_check(self) -> tuple[bool, str]:
        """
        Check Claude connectivity.

        Returns:
            (success, message)
        """
        logger.debug(f"Health check starting: cwd={self.working_dir}")
        logger.debug(
            f"Auth env: CLAUDE_CODE_OAUTH_TOKEN={'set' if os.environ.get('CLAUDE_CODE_OAUTH_TOKEN') else 'not set'}, "
            f"ANTHROPIC_API_KEY={'set' if os.environ.get('ANTHROPIC_API_KEY') else 'not set'}"
        )
        try:
            result = subprocess.run(
                ["claude", "-p", "Say OK", "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.working_dir,
            )
            logger.debug(f"Health check subprocess: returncode={result.returncode}")
            logger.debug(
                f"Health check stdout: {result.stdout[:200] if result.stdout else 'empty'}"
            )
            logger.debug(
                f"Health check stderr: {result.stderr[:200] if result.stderr else 'empty'}"
            )

            if result.returncode == 0:
                logger.debug("Health check passed")
                return True, "OK"
            logger.debug(f"Health check failed: returncode={result.returncode}")
            return False, f"FAILED - {result.stderr[:50]}"
        except Exception as e:
            logger.debug(f"Health check exception: {e}")
            return False, f"FAILED - {e}"


# Default instance
_claude_client: ClaudeClient | None = None


def get_claude_client() -> ClaudeClient:
    """Get or create the default Claude client instance."""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client


def set_claude_client(client: ClaudeClient) -> None:
    """Set the default Claude client instance (for testing)."""
    global _claude_client
    _claude_client = client
