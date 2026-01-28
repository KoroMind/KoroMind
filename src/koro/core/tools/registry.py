"""Tool registry for routing tool calls."""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolDefinition:
    """Definition of a tool."""

    name: str
    description: str
    handler: Callable[..., Any] | None = None
    requires_approval: bool = False
    category: str = "general"


class ToolRegistry:
    """Registry for available tools."""

    def __init__(self):
        """Initialize tool registry."""
        self.tools: dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register the default Claude SDK tools."""
        # Read-only tools
        self.register(
            ToolDefinition(
                name="Read",
                description="Read file contents",
                category="filesystem",
            )
        )
        self.register(
            ToolDefinition(
                name="Grep",
                description="Search file contents",
                category="filesystem",
            )
        )
        self.register(
            ToolDefinition(
                name="Glob",
                description="Find files by pattern",
                category="filesystem",
            )
        )

        # Web tools
        self.register(
            ToolDefinition(
                name="WebSearch",
                description="Search the web",
                category="web",
            )
        )
        self.register(
            ToolDefinition(
                name="WebFetch",
                description="Fetch web content",
                category="web",
            )
        )

        # Write tools (require approval in APPROVE mode)
        self.register(
            ToolDefinition(
                name="Bash",
                description="Execute bash commands",
                requires_approval=True,
                category="execution",
            )
        )
        self.register(
            ToolDefinition(
                name="Edit",
                description="Edit file contents",
                requires_approval=True,
                category="filesystem",
            )
        )
        self.register(
            ToolDefinition(
                name="Write",
                description="Write file contents",
                requires_approval=True,
                category="filesystem",
            )
        )

        # Agent tools
        self.register(
            ToolDefinition(
                name="Task",
                description="Spawn subtask agent",
                category="agent",
            )
        )
        self.register(
            ToolDefinition(
                name="Skill",
                description="Execute a skill",
                category="agent",
            )
        )

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        self.tools.pop(name, None)

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self, category: str | None = None) -> list[ToolDefinition]:
        """List all tools, optionally filtered by category."""
        if category is None:
            return list(self.tools.values())
        return [t for t in self.tools.values() if t.category == category]

    def get_tool_names(self, include_approval_required: bool = True) -> list[str]:
        """Get list of tool names."""
        if include_approval_required:
            return list(self.tools.keys())
        return [t.name for t in self.tools.values() if not t.requires_approval]

    def requires_approval(self, name: str) -> bool:
        """Check if a tool requires approval."""
        tool = self.get(name)
        return tool.requires_approval if tool else True


# Default instance
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the default tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def set_tool_registry(registry: ToolRegistry) -> None:
    """Set the default tool registry (for testing)."""
    global _registry
    _registry = registry
