"""Vault - configuration loader for KoroMind.

The Vault loads configuration from vault-config.yaml and provides it
as a typed VaultConfig that passes to the Claude SDK via Brain.
"""

import json
import logging
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger(__name__)


def _resolve_path(path_str: str, vault_root: Path) -> str:
    """Resolve a relative path against vault root.

    Handles ~ expansion and absolute path preservation.
    """
    p = Path(path_str).expanduser()
    if p.is_absolute():
        return str(p)
    return str(vault_root / p)


# --- Typed Configuration Models ---


class HookConfig(BaseModel):
    """Configuration for a single hook."""

    model_config = ConfigDict(frozen=True, extra="allow")

    type: str = "command"
    command: str

    def model_post_init(self, __context: Any) -> None:
        if __context and self.command.startswith("./"):
            vault_root = __context.get("vault_root")
            if vault_root:
                object.__setattr__(
                    self, "command", _resolve_path(self.command, vault_root)
                )


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

    def model_post_init(self, __context: Any) -> None:
        if __context and self.args:
            vault_root = __context.get("vault_root")
            if vault_root:
                resolved = [
                    _resolve_path(a, vault_root) if a.startswith("./") else a
                    for a in self.args
                ]
                object.__setattr__(self, "args", resolved)


class AgentConfig(BaseModel):
    """Configuration for a subagent.

    Fields align with Claude SDK's AgentDefinition.
    Model accepts short names: "sonnet", "opus", "haiku", "inherit".
    Use prompt for inline text, or prompt_file for a file path (resolved by vault).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    model: Literal["sonnet", "opus", "haiku", "inherit"] | None = None
    description: str = ""
    prompt: str | None = None
    prompt_file: str | None = None
    tools: list[str] | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.prompt and self.prompt_file:
            raise ValueError("Use prompt or prompt_file, not both")
        if __context and self.prompt_file:
            vault_root = __context.get("vault_root")
            if vault_root:
                object.__setattr__(
                    self, "prompt_file", _resolve_path(self.prompt_file, vault_root)
                )


class SandboxConfig(BaseModel):
    """Sandbox settings."""

    model_config = ConfigDict(frozen=True, extra="allow", populate_by_name=True)

    enabled: bool = False
    auto_allow_bash_if_sandboxed: bool = Field(
        default=True, alias="autoAllowBashIfSandboxed"
    )
    white_listed_commands: list[str] = Field(default=[], alias="whiteListedCommands")


class VaultConfig(BaseModel):
    """Typed configuration loaded from vault-config.yaml.

    All fields are optional to allow partial configs.
    Frozen to prevent accidental mutation.
    Extra fields are forbidden to catch typos in config.

    Note: Core SDK options (model, cwd, max_turns, etc.) are provided
    via environment variables, not vault config.

    mcp_servers accepts either:
    - A dict of server configs (inline)
    - A string path to a JSON file containing a "mcpServers" key
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Extensibility - user-specific configurations
    hooks: dict[str, list[HookMatcher]] = {}
    mcp_servers: dict[str, McpServerConfig] = {}
    agents: dict[str, AgentConfig] = {}
    sandbox: SandboxConfig | None = None
    plugins: list[Any] = []

    @model_validator(mode="before")
    @classmethod
    def _resolve_mcp_json(cls, data: Any, info: Any) -> Any:
        if not isinstance(data, dict):
            return data
        mcp = data.get("mcp_servers")
        if not isinstance(mcp, str):
            return data

        vault_root = info.context.get("vault_root") if info.context else None
        if vault_root is None:
            raise VaultError("Cannot resolve mcp_servers path without vault_root")

        mcp_path = Path(mcp).expanduser()
        if not mcp_path.is_absolute():
            mcp_path = Path(vault_root) / mcp_path

        if not mcp_path.exists():
            raise VaultError(f"MCP config file not found: {mcp_path}")

        try:
            with open(mcp_path) as f:
                mcp_data = json.load(f)
        except json.JSONDecodeError as e:
            raise VaultError(f"Invalid JSON in {mcp_path}: {e}") from e

        if not isinstance(mcp_data, dict) or "mcpServers" not in mcp_data:
            raise VaultError(
                f"MCP config file must contain a 'mcpServers' key: {mcp_path}"
            )

        data["mcp_servers"] = mcp_data["mcpServers"]
        return data


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

        self._config = VaultConfig.model_validate(
            raw, context={"vault_root": self.root}
        )
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

    @property
    def exists(self) -> bool:
        """Check if vault config file exists."""
        return self.config_file.exists()

    def __repr__(self) -> str:
        return f"Vault({self.root})"
