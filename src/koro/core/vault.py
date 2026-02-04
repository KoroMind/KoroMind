"""Vault - configuration loader for KoroMind.

The Vault loads configuration from vault-config.yaml and provides it
as a typed VaultConfig that passes to the Claude SDK via Brain.
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# --- Typed Configuration Models ---


class HookConfig(BaseModel):
    """Configuration for a single hook."""

    model_config = ConfigDict(frozen=True, extra="allow")

    type: str = "command"
    command: str


class HookMatcher(BaseModel):
    """Matcher configuration for hooks."""

    model_config = ConfigDict(frozen=True, extra="allow")

    matcher: str
    hooks: list[HookConfig] = []


class McpServerConfig(BaseModel):
    """Configuration for an MCP server."""

    model_config = ConfigDict(frozen=True, extra="allow")

    command: str
    args: list[str] = []


class AgentConfig(BaseModel):
    """Configuration for a subagent."""

    model_config = ConfigDict(frozen=True, extra="allow")

    model: str | None = None
    system_prompt: str | None = None
    allowed_tools: list[str] = []


class SandboxConfig(BaseModel):
    """Sandbox settings."""

    model_config = ConfigDict(frozen=True, extra="allow", populate_by_name=True)

    enabled: bool = False
    auto_allow_bash_if_sandboxed: bool = Field(
        default=True, alias="autoAllowBashIfSandboxed"
    )
    white_listed_commands: list[str] = Field(
        default=[], alias="whiteListedCommands"
    )


class VaultConfig(BaseModel):
    """Typed configuration loaded from vault-config.yaml.

    All fields are optional to allow partial configs.
    Frozen to prevent accidental mutation.

    Note: Core SDK options (model, cwd, max_turns, etc.) are provided
    via environment variables, not vault config.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    # Extensibility - user-specific configurations
    hooks: dict[str, list[HookMatcher]] = {}
    mcp_servers: dict[str, McpServerConfig] = {}
    agents: dict[str, AgentConfig] = {}
    sandbox: SandboxConfig | None = None
    plugins: list[Any] = []


class VaultError(Exception):
    """Raised when vault configuration is invalid."""

    pass


class Vault:
    """Loads vault-config.yaml and provides SDK-compatible configuration.

    The Vault is a thin loader that:
    1. Loads YAML configuration from vault root
    2. Resolves relative paths to absolute paths within the vault
    3. Returns a typed VaultConfig that Brain passes to ClaudeClient

    Example:
        vault = Vault("~/.koromind")
        config = vault.load()
        # config is a VaultConfig with cwd, add_dirs, mcp_servers, etc.
    """

    CONFIG_FILENAME = "vault-config.yaml"

    # Empty config singleton (frozen, so safe to share)
    _EMPTY_CONFIG = VaultConfig()

    def __init__(self, path: Path | str):
        """Initialize vault with root directory path.

        Args:
            path: Path to vault root directory (e.g., ~/.koromind)
        """
        self.root = Path(path).expanduser().resolve()
        self.config_file = self.root / self.CONFIG_FILENAME
        self._config: VaultConfig | None = None

    def load(self) -> VaultConfig:
        """Load configuration, resolving paths relative to vault root.

        Returns:
            VaultConfig with SDK-compatible configuration. Empty config if no config file.

        Raises:
            VaultError: If config file exists but is invalid YAML.
        """
        if self._config is not None:
            logger.debug("Returning cached config")
            return self._config

        if not self.config_file.exists():
            logger.debug(f"No config file at {self.config_file}")
            self._config = self._EMPTY_CONFIG
            return self._config

        logger.debug(f"Loading config from {self.config_file}")

        try:
            with open(self.config_file) as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {self.config_file}: {e}")
            raise VaultError(f"Invalid YAML in {self.config_file}: {e}") from e

        if raw is None:
            logger.debug("Config file is empty or null")
            self._config = self._EMPTY_CONFIG
            return self._config

        if not isinstance(raw, dict):
            logger.error(f"Config must be a mapping, got {type(raw).__name__}")
            raise VaultError(
                f"vault-config.yaml must be a mapping, got {type(raw).__name__}"
            )

        resolved = self._resolve_paths(raw)
        self._config = VaultConfig.model_validate(resolved)
        logger.info(
            f"Vault config loaded: "
            f"mcp_servers={len(self._config.mcp_servers)}, "
            f"agents={len(self._config.agents)}, "
            f"hooks={len(self._config.hooks)}"
        )
        return self._config

    def reload(self) -> VaultConfig:
        """Force reload configuration from disk.

        Returns:
            Fresh VaultConfig.
        """
        self._config = None
        return self.load()

    def _resolve_paths(self, config: dict[str, Any]) -> dict[str, Any]:
        """Resolve relative paths to absolute paths within vault.

        Handles:
        - Paths in mcp_servers args that start with ./
        - Paths in hooks commands that start with ./

        Args:
            config: Raw configuration dict

        Returns:
            Config with resolved paths
        """
        result = config.copy()

        # Resolve paths in MCP server args
        if "mcp_servers" in result and isinstance(result["mcp_servers"], dict):
            result["mcp_servers"] = self._resolve_mcp_paths(result["mcp_servers"])

        # Resolve paths in hooks
        if "hooks" in result and isinstance(result["hooks"], dict):
            result["hooks"] = self._resolve_hook_paths(result["hooks"])

        return result

    def _resolve(self, path: str) -> Path:
        """Resolve a path: relative paths are relative to vault root.

        Args:
            path: Path string (relative or absolute)

        Returns:
            Resolved absolute Path
        """
        p = Path(path).expanduser()
        if p.is_absolute():
            return p
        return self.root / p

    def _resolve_mcp_paths(self, mcp_servers: dict[str, Any]) -> dict[str, Any]:
        """Resolve paths in MCP server configurations.

        Looks for paths starting with ./ in args lists.
        """
        resolved = {}
        for name, server in mcp_servers.items():
            if not isinstance(server, dict):
                resolved[name] = server
                continue

            server_copy = server.copy()
            if "args" in server_copy and isinstance(server_copy["args"], list):
                server_copy["args"] = [
                    (
                        str(self._resolve(arg))
                        if isinstance(arg, str) and arg.startswith("./")
                        else arg
                    )
                    for arg in server_copy["args"]
                ]
            resolved[name] = server_copy
        return resolved

    def _resolve_hook_paths(self, hooks: dict[str, Any]) -> dict[str, Any]:
        """Resolve paths in hook configurations.

        Looks for command fields with relative paths.
        """
        resolved = {}
        for event, matchers in hooks.items():
            if not isinstance(matchers, list):
                resolved[event] = matchers
                continue

            resolved_matchers = []
            for matcher in matchers:
                if not isinstance(matcher, dict):
                    resolved_matchers.append(matcher)
                    continue

                matcher_copy = matcher.copy()
                if "hooks" in matcher_copy and isinstance(matcher_copy["hooks"], list):
                    resolved_hooks = []
                    for hook in matcher_copy["hooks"]:
                        if isinstance(hook, dict) and "command" in hook:
                            hook_copy = hook.copy()
                            cmd = hook_copy["command"]
                            if isinstance(cmd, str) and cmd.startswith("./"):
                                hook_copy["command"] = str(self._resolve(cmd))
                            resolved_hooks.append(hook_copy)
                        else:
                            resolved_hooks.append(hook)
                    matcher_copy["hooks"] = resolved_hooks
                resolved_matchers.append(matcher_copy)
            resolved[event] = resolved_matchers
        return resolved

    @property
    def exists(self) -> bool:
        """Check if vault config file exists."""
        return self.config_file.exists()

    def __repr__(self) -> str:
        return f"Vault({self.root})"
