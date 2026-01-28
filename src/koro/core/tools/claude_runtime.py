"""Claude Agent SDK execution runtime.

This module wraps the Claude SDK execution loop with KoroMind-specific
handling for tool calls, streaming, and result processing.
"""

from pathlib import Path
from typing import Any, Callable

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from koro.core.types import ToolCall


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


async def run_claude_agent(
    prompt: str,
    system_prompt: str,
    sandbox_dir: str | Path,
    working_dir: str | Path,
    session_id: str | None = None,
    continue_conversation: bool = False,
    allowed_tools: list[str] | None = None,
    can_use_tool: Callable[[str, dict, Any], Any] | None = None,
    on_tool_call: Callable[[str, str | None], None] | None = None,
) -> tuple[str, str | None, list[ToolCall], dict]:
    """
    Run Claude agent and collect results.

    Args:
        prompt: User prompt to send
        system_prompt: System prompt for Claude
        sandbox_dir: Directory for Claude to write/execute
        working_dir: Directory Claude can read from
        session_id: Session ID to resume
        continue_conversation: Whether to continue last session
        allowed_tools: List of allowed tools (for go_all mode)
        can_use_tool: Approval callback (for approve mode)
        on_tool_call: Callback for each tool call (for watch mode)

    Returns:
        (response_text, session_id, tool_calls, metadata)
    """
    # Ensure sandbox exists
    Path(sandbox_dir).mkdir(parents=True, exist_ok=True)

    # Build SDK options
    if can_use_tool:
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            cwd=str(sandbox_dir),
            can_use_tool=can_use_tool,
            permission_mode="default",
            add_dirs=[str(working_dir)],
        )
    else:
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=allowed_tools
            or [
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
            ],
            cwd=str(sandbox_dir),
            add_dirs=[str(working_dir)],
        )

    # Handle session continuation
    if continue_conversation:
        options.continue_conversation = True
    elif session_id:
        options.resume = session_id

    result_text = ""
    new_session_id = session_id
    tool_calls: list[ToolCall] = []
    metadata: dict[str, Any] = {}

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            result_text += block.text
                        elif isinstance(block, ToolUseBlock):
                            tool_input = block.input or {}
                            detail = get_tool_detail(block.name, tool_input)
                            tool_calls.append(ToolCall(name=block.name, detail=detail))
                            if on_tool_call:
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

        metadata["tool_count"] = len(tool_calls)
        return result_text, new_session_id, tool_calls, metadata

    except Exception as e:
        return f"Error calling Claude: {e}", session_id, [], {}
