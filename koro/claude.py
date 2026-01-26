"""Claude SDK wrapper for agent interactions."""

import json
import asyncio
import subprocess
from pathlib import Path
from typing import Callable, Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    PermissionResultAllow,
    PermissionResultDeny,
)

from .config import SANDBOX_DIR, CLAUDE_WORKING_DIR
from .prompt import get_prompt_manager


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
            ["megg", "context"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd
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

    async def query(
        self,
        prompt: str,
        session_id: str = None,
        continue_last: bool = False,
        include_megg: bool = True,
        user_settings: dict = None,
        mode: str = "go_all",
        on_tool_call: Callable[[str, dict], None] = None,
        can_use_tool: Callable[[str, dict, Any], Any] = None,
    ) -> tuple[str, str, dict]:
        """
        Query Claude and return response.

        Args:
            prompt: User prompt
            session_id: Session ID to resume
            continue_last: Whether to continue last session
            include_megg: Whether to include megg context
            user_settings: User settings dict
            mode: "go_all" or "approve"
            on_tool_call: Callback when tool is called (for watch mode)
            can_use_tool: Callback for tool approval (for approve mode)

        Returns:
            (response_text, session_id, metadata)
        """
        # Ensure sandbox exists
        Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True)

        # Build prompt with megg context for new sessions
        full_prompt = prompt
        if include_megg and not continue_last and not session_id:
            megg_ctx = load_megg_context(self.working_dir)
            if megg_ctx:
                full_prompt = f"<context>\n{megg_ctx}\n</context>\n\n{prompt}"

        # Get dynamic system prompt
        system_prompt = self.prompt_manager.get_prompt(user_settings)

        # Build SDK options
        if mode == "approve" and can_use_tool:
            options = ClaudeAgentOptions(
                system_prompt=system_prompt,
                cwd=self.sandbox_dir,
                can_use_tool=can_use_tool,
                permission_mode="default",
                add_dirs=[self.working_dir],
            )
        else:
            options = ClaudeAgentOptions(
                system_prompt=system_prompt,
                allowed_tools=[
                    "Read", "Grep", "Glob", "WebSearch", "WebFetch",
                    "Task", "Bash", "Edit", "Write", "Skill"
                ],
                cwd=self.sandbox_dir,
                add_dirs=[self.working_dir],
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

        try:
            async with ClaudeSDKClient(options=options) as client:
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

            metadata["tool_count"] = tool_count
            return result_text, new_session_id, metadata

        except Exception as e:
            return f"Error calling Claude: {e}", session_id, {}

    def health_check(self) -> tuple[bool, str]:
        """
        Check Claude connectivity.

        Returns:
            (success, message)
        """
        try:
            result = subprocess.run(
                ["claude", "-p", "Say OK", "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.working_dir
            )
            if result.returncode == 0:
                return True, "OK"
            return False, f"FAILED - {result.stderr[:50]}"
        except Exception as e:
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
