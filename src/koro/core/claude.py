"""Claude SDK wrapper for agent interactions."""

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    HookMatcher,
    McpStdioServerConfig,
    McpSSEServerConfig,
    McpHttpServerConfig,
    PostToolUseHookInput,
    PreToolUseHookInput,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from koro.core.config import CLAUDE_WORKING_DIR, SANDBOX_DIR
from koro.core.prompt import get_prompt_manager
from koro.core.types import BrainCallbacks, SDKConfig, ToolCall


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

    def _build_mcp_servers(self, servers: list[dict]) -> dict[str, Any]:
        """
        Build MCP server configs from Vault config.

        Args:
            servers: List of server config dicts from Vault

        Returns:
            Dict mapping server names to config objects for ClaudeAgentOptions
        """
        result = {}
        for server in servers:
            name = server.get("name")
            if not name:
                continue

            server_type = server.get("type", "stdio")

            if server_type == "stdio":
                result[name] = McpStdioServerConfig(
                    type="stdio",
                    command=server.get("command", ""),
                    args=server.get("args", []),
                    env=server.get("env", {}),
                )
            elif server_type == "sse":
                result[name] = McpSSEServerConfig(
                    type="sse",
                    url=server.get("url", ""),
                    headers=server.get("headers", {}),
                )
            elif server_type == "http":
                result[name] = McpHttpServerConfig(
                    type="http",
                    url=server.get("url", ""),
                    headers=server.get("headers", {}),
                )

        return result

    def _build_agents(self, agents: dict[str, dict]) -> dict[str, AgentDefinition]:
        """
        Build agent definitions from Vault config.

        Args:
            agents: Dict mapping agent names to definition dicts

        Returns:
            Dict mapping agent names to AgentDefinition objects
        """
        result = {}
        for name, definition in agents.items():
            result[name] = AgentDefinition(
                description=definition.get("description", ""),
                prompt=definition.get("prompt", ""),
                tools=definition.get("tools"),
                model=definition.get("model"),
            )
        return result

    def _build_sdk_options(
        self,
        sdk_config: SDKConfig,
        system_prompt: str,
        mode: str,
        can_use_tool: Callable[[str, dict, Any], Any] | None = None,
    ) -> ClaudeAgentOptions:
        """
        Build ClaudeAgentOptions from SDK config.

        Args:
            sdk_config: SDKConfig from Vault
            system_prompt: System prompt to use
            mode: Execution mode ("go_all" or "approve")
            can_use_tool: Callback for tool approval

        Returns:
            Fully configured ClaudeAgentOptions
        """
        # Determine working directories
        sandbox = sdk_config.sandbox_dir or self.sandbox_dir
        working = sdk_config.working_dir or self.working_dir
        add_dirs = sdk_config.add_dirs or [working]

        # Build MCP servers and agents
        mcp_servers = self._build_mcp_servers(sdk_config.mcp_servers)
        agents = self._build_agents(sdk_config.agents)

        # Base options
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            cwd=sandbox,
            add_dirs=add_dirs,
            model=sdk_config.model,
            fallback_model=sdk_config.fallback_model,
            disallowed_tools=sdk_config.disallowed_tools,
        )

        # Add MCP servers if any
        if mcp_servers:
            options.mcp_servers = mcp_servers

        # Add custom agents if any
        if agents:
            options.agents = agents

        # Add sandbox settings if configured
        if sdk_config.sandbox_settings:
            options.sandbox = sdk_config.sandbox_settings

        # Handle permission mode
        if mode == "approve" and can_use_tool:
            options.can_use_tool = can_use_tool
            options.permission_mode = sdk_config.permission_mode
        else:
            options.allowed_tools = sdk_config.allowed_tools

        return options

    def _build_hooks(
        self,
        callbacks: BrainCallbacks | None,
        tool_calls_list: list[ToolCall] | None = None,
    ) -> dict[str, list[HookMatcher]] | None:
        """
        Build SDK hooks from BrainCallbacks.

        This maps the Brain's callback interface to the SDK's hook system,
        providing pre and post tool execution notifications.

        Args:
            callbacks: BrainCallbacks from the Brain
            tool_calls_list: List to append ToolCall records to

        Returns:
            Dict of hook matchers for ClaudeAgentOptions, or None
        """
        if not callbacks and tool_calls_list is None:
            return None

        hooks: dict[str, list[HookMatcher]] = {}

        # Always track tool calls if list provided
        # PreToolUse: Called BEFORE tool execution
        if callbacks and (callbacks.on_tool_start or callbacks.on_permission_request):

            async def pre_tool_hook(
                input_data: PreToolUseHookInput,
                tool_use_id: str | None,
                ctx: Any,
            ) -> dict[str, Any]:
                """Handle pre-tool execution."""
                tool_name = input_data["tool_name"]
                tool_input = input_data.get("tool_input", {})

                # Notify watcher of tool start
                if callbacks.on_tool_start:
                    callbacks.on_tool_start(tool_name, tool_input)

                # Handle permission request if in approve mode
                if callbacks.on_permission_request:
                    result = await callbacks.on_permission_request(tool_name, tool_input)
                    return {
                        "continue_": result.decision != "deny",
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": result.decision,
                            "permissionDecisionReason": result.reason,
                            "updatedInput": result.updated_input,
                        },
                    }

                return {"continue_": True}

            hooks["PreToolUse"] = [HookMatcher(hooks=[pre_tool_hook])]

        # PostToolUse: Called AFTER tool execution
        if (callbacks and callbacks.on_tool_end) or tool_calls_list is not None:

            async def post_tool_hook(
                input_data: PostToolUseHookInput,
                tool_use_id: str | None,
                ctx: Any,
            ) -> dict[str, Any]:
                """Handle post-tool execution."""
                tool_name = input_data["tool_name"]
                tool_input = input_data.get("tool_input", {})
                tool_response = input_data.get("tool_response")

                # Track tool call with full data
                if tool_calls_list is not None:
                    detail = get_tool_detail(tool_name, tool_input)
                    tool_calls_list.append(
                        ToolCall(
                            name=tool_name,
                            detail=detail,
                            tool_input=tool_input,
                            tool_response=tool_response,
                            tool_use_id=tool_use_id,
                        )
                    )

                # Notify watcher of tool completion
                if callbacks and callbacks.on_tool_end:
                    callbacks.on_tool_end(tool_name, tool_input, tool_response)

                return {"continue_": True}

            hooks["PostToolUse"] = [HookMatcher(hooks=[post_tool_hook])]

        return hooks if hooks else None

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
        sdk_config: SDKConfig | None = None,
        callbacks: BrainCallbacks | None = None,
    ) -> tuple[str, str, dict, list[ToolCall]]:
        """
        Query Claude and return response.

        Args:
            prompt: User prompt
            session_id: Session ID to resume
            continue_last: Whether to continue last session
            include_megg: Whether to include megg context
            user_settings: User settings dict
            mode: "go_all" or "approve"
            on_tool_call: Legacy callback when tool is called (for watch mode)
            can_use_tool: Callback for tool approval (for approve mode)
            sdk_config: SDK configuration from Vault (optional, uses defaults if None)
            callbacks: BrainCallbacks for hook-based tool notifications (preferred)

        Returns:
            (response_text, session_id, metadata, tool_calls)
        """
        # Use default config if none provided
        if sdk_config is None:
            sdk_config = SDKConfig()

        # Determine sandbox directory
        sandbox = sdk_config.sandbox_dir or self.sandbox_dir
        working = sdk_config.working_dir or self.working_dir

        # Ensure sandbox exists
        Path(sandbox).mkdir(parents=True, exist_ok=True)

        # Build prompt with megg context for new sessions
        full_prompt = prompt
        if include_megg and not continue_last and not session_id:
            megg_ctx = load_megg_context(working)
            if megg_ctx:
                full_prompt = f"<context>\n{megg_ctx}\n</context>\n\n{prompt}"

        # Get dynamic system prompt
        system_prompt = self.prompt_manager.get_prompt(user_settings)

        # Build SDK options from config
        options = self._build_sdk_options(sdk_config, system_prompt, mode, can_use_tool)

        # Handle session continuation
        if continue_last:
            options.continue_conversation = True
        elif session_id:
            options.resume = session_id

        # Track tool calls using hooks
        tool_calls: list[ToolCall] = []

        # Build hooks from callbacks
        hooks = self._build_hooks(callbacks, tool_calls)
        if hooks:
            options.hooks = hooks

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
                                # Legacy callback support (deprecated)
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
            return result_text, new_session_id, metadata, tool_calls

        except Exception as e:
            return f"Error calling Claude: {e}", session_id, {}, tool_calls

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
                cwd=self.working_dir,
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
