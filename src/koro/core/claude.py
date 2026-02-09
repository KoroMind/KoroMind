"""Claude SDK wrapper for agent interactions."""

import inspect
import json
import logging
import os
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    CLIConnectionError,
    CLINotFoundError,
    ProcessError,
)
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from koro.core.config import CLAUDE_WORKING_DIR, SANDBOX_DIR
from koro.core.prompt import get_prompt_manager
from koro.core.types import DEFAULT_CLAUDE_TOOLS, Mode, QueryConfig

logger = logging.getLogger(__name__)

StreamedEvent = (
    AssistantMessage | ResultMessage | StreamEvent | UserMessage | SystemMessage
)


def load_megg_context(working_dir: str | None = None) -> str:
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


def format_tool_call(tool_name: str, tool_input: dict[str, Any]) -> str:
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


def get_tool_detail(tool_name: str, tool_input: dict[str, Any]) -> str | None:
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
        if not isinstance(cmd, str):
            return None
        return cmd[:80] + "..." if len(cmd) > 80 else cmd
    elif tool_name == "Read" and "file_path" in tool_input:
        file_path = tool_input["file_path"]
        return file_path if isinstance(file_path, str) else None
    elif tool_name == "Edit" and "file_path" in tool_input:
        file_path = tool_input["file_path"]
        return file_path if isinstance(file_path, str) else None
    elif tool_name == "Write" and "file_path" in tool_input:
        file_path = tool_input["file_path"]
        return file_path if isinstance(file_path, str) else None
    elif tool_name == "Grep" and "pattern" in tool_input:
        pattern = tool_input["pattern"]
        return f"/{pattern}/" if isinstance(pattern, str) else None
    elif tool_name == "Glob" and "pattern" in tool_input:
        pattern = tool_input["pattern"]
        return pattern if isinstance(pattern, str) else None
    return None


class ClaudeClient:
    """Wrapper for Claude SDK interactions."""

    def __init__(
        self,
        sandbox_dir: str | None = None,
        working_dir: str | None = None,
    ):
        """
        Initialize Claude client.

        Args:
            sandbox_dir: Directory for Claude to write/execute
            working_dir: Directory Claude can read from
        """
        self.sandbox_dir = sandbox_dir or SANDBOX_DIR or str(Path.home())
        self.working_dir = working_dir or CLAUDE_WORKING_DIR or str(Path.home())
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

    def _build_options(self, config: QueryConfig) -> ClaudeAgentOptions:
        """Build SDK options from config."""
        # Get dynamic system prompt
        system_prompt = self.prompt_manager.get_prompt(config.user_settings)

        # Base options
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            cwd=self.sandbox_dir,
            add_dirs=[self.working_dir],
            # Pass through new options
            hooks=config.hooks,
            mcp_servers=config.mcp_servers,
            agents=config.agents,
            plugins=config.plugins,
            sandbox=config.sandbox,
            output_format=dict(config.output_format) if config.output_format else None,
            max_turns=config.max_turns,
            max_budget_usd=config.max_budget_usd,
            model=config.model,
            fallback_model=config.fallback_model,
            include_partial_messages=config.include_partial_messages,
            enable_file_checkpointing=config.enable_file_checkpointing,
        )

        # Set permission mode and tools based on mode
        if config.mode == Mode.APPROVE and config.can_use_tool:
            options.can_use_tool = config.can_use_tool
            options.permission_mode = "default"
        else:
            options.allowed_tools = [tool.value for tool in DEFAULT_CLAUDE_TOOLS]

        logger.debug(
            f"Built options: model={config.model}, max_turns={config.max_turns}, "
            f"cwd={self.sandbox_dir}, mode={config.mode.value}, "
            f"hooks={bool(config.hooks)}, mcp_servers={bool(config.mcp_servers)}"
        )
        return options

    def _prepare_query(self, config: QueryConfig) -> tuple[str, ClaudeAgentOptions]:
        full_prompt = config.prompt
        if config.include_megg and not config.continue_last and not config.session_id:
            megg_ctx = load_megg_context(self.working_dir)
            if megg_ctx:
                full_prompt = f"<context>\n{megg_ctx}\n</context>\n\n{config.prompt}"

        options = self._build_options(config)

        if config.continue_last:
            options.continue_conversation = True
        elif config.session_id:
            options.resume = config.session_id

        return full_prompt, options

    async def query(
        self,
        config: QueryConfig,
    ) -> tuple[str, str, dict[str, Any]]:
        """
        Query Claude and return response.
        """
        logger.debug(
            f"Query starting: session_id={config.session_id}, "
            f"continue_last={config.continue_last}, mode={config.mode.value}, "
            f"model={config.model}"
        )
        # Ensure sandbox exists
        Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True)

        full_prompt, options = self._prepare_query(config)

        result_text = ""
        new_session_id = config.session_id or ""
        metadata: dict[str, Any] = {}
        tool_count = 0
        tool_results: list[dict[str, Any]] = []
        tool_use_map: dict[str, dict[str, Any]] = {}
        thinking_content = ""

        try:
            async with ClaudeSDKClient(options=options) as client:
                self._active_client = client
                try:
                    await client.query(full_prompt)
                    async for message in client.receive_response():
                        if isinstance(message, AssistantMessage):
                            for block in message.content:
                                match block:
                                    case TextBlock(text=text):
                                        result_text += text
                                    case ToolUseBlock(
                                        id=tool_id, name=name, input=tool_input
                                    ):
                                        tool_count += 1
                                        tool_use_map[tool_id] = {
                                            "name": name,
                                            "input": tool_input,
                                        }
                                        if config.on_tool_call:
                                            detail = get_tool_detail(
                                                name, tool_input or {}
                                            )
                                            await config.on_tool_call(name, detail)
                                    case ToolResultBlock(
                                        tool_use_id=tool_use_id, is_error=is_error
                                    ):
                                        tool_info = tool_use_map.get(tool_use_id, {})
                                        tool_results.append(
                                            {
                                                "tool_use_id": tool_use_id,
                                                "name": tool_info.get("name"),
                                                "is_error": is_error,
                                            }
                                        )
                                    case ThinkingBlock(thinking=thinking):
                                        thinking_content += thinking

                        elif isinstance(message, ResultMessage):
                            if message.result:
                                result_text = message.result
                            if message.session_id:
                                new_session_id = message.session_id
                            if message.total_cost_usd is not None:
                                metadata["cost"] = message.total_cost_usd
                            if message.num_turns is not None:
                                metadata["num_turns"] = message.num_turns
                            if message.duration_ms is not None:
                                metadata["duration_ms"] = message.duration_ms
                            if message.usage is not None:
                                metadata["usage"] = message.usage
                            if message.structured_output is not None:
                                metadata["structured_output"] = (
                                    message.structured_output
                                )
                            if message.is_error is not None:
                                metadata["is_error"] = message.is_error
                finally:
                    self._active_client = None

            metadata["tool_count"] = tool_count
            if tool_results:
                metadata["tool_results"] = tool_results
            if thinking_content:
                metadata["thinking"] = thinking_content
            logger.debug(
                f"Query complete: session_id={new_session_id}, "
                f"tools={tool_count}, cost={metadata.get('cost')}, "
                f"turns={metadata.get('num_turns')}"
            )
            return result_text, new_session_id, metadata

        except CLINotFoundError:
            logger.debug("Query failed: CLI not found")
            return (
                "Error: Claude CLI not found. Please install claude-code.",
                config.session_id or "",
                {"error": "cli_not_found"},
            )
        except CLIConnectionError as e:
            logger.debug(f"Query failed: CLI connection error: {e}")
            return (
                f"Error: Failed to connect to Claude CLI: {e}",
                config.session_id or "",
                {"error": "connection_failed"},
            )
        except ProcessError as e:
            logger.debug(f"Query failed: Process error (exit {e.exit_code}): {e}")
            return (
                f"Error: Claude process failed (exit {e.exit_code}): {e}",
                config.session_id or "",
                {"error": "process_error", "exit_code": e.exit_code},
            )
        except Exception as e:
            logger.debug(f"Query failed: Exception: {e}")
            return (
                f"Error calling Claude: {e}",
                config.session_id or "",
                {"error": str(e)},
            )

    async def query_stream(
        self,
        config: QueryConfig,
    ) -> AsyncIterator[StreamedEvent]:
        """
        Query Claude and yield events (StreamEvent or messages).
        """
        logger.debug(
            f"Stream query starting: session_id={config.session_id}, mode={config.mode.value}"
        )
        stream_config = config.model_copy(update={"include_partial_messages": True})

        # Ensure sandbox exists
        Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True)

        full_prompt, options = self._prepare_query(stream_config)

        try:
            async with ClaudeSDKClient(options=options) as client:
                self._active_client = client
                try:
                    await client.query(full_prompt)
                    async for message in client.receive_response():
                        # Pass through on_tool_call side effect
                        if isinstance(message, AssistantMessage):
                            for block in message.content:
                                if (
                                    isinstance(block, ToolUseBlock)
                                    and stream_config.on_tool_call
                                ):
                                    try:
                                        tool_input = block.input or {}
                                        detail = get_tool_detail(
                                            block.name, tool_input
                                        )
                                        result = stream_config.on_tool_call(
                                            block.name, detail
                                        )
                                        if inspect.isawaitable(result):
                                            await result
                                    except Exception:
                                        logger.warning(
                                            "on_tool_call callback failed",
                                            exc_info=True,
                                        )
                        yield message
                finally:
                    self._active_client = None

        except Exception as e:
            logger.debug(f"Stream query failed: {e}")
            raise

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
