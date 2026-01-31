"""Vault - configuration loader for KoroMind.

The Vault loads configuration from vault-config.yaml and provides it
as a dict that passes directly to the Claude SDK via Brain.
"""

from pathlib import Path
from typing import Any

import yaml


class VaultError(Exception):
    """Raised when vault configuration is invalid."""

    pass


class Vault:
    """Loads vault-config.yaml and provides SDK-compatible configuration.

    The Vault is a thin loader that:
    1. Loads YAML configuration from vault root
    2. Resolves relative paths to absolute paths within the vault
    3. Returns a dict that Brain passes to ClaudeClient

    Example:
        vault = Vault("~/.koromind")
        config = vault.load()
        # config is a dict with cwd, add_dirs, mcp_servers, etc.
    """

    CONFIG_FILENAME = "vault-config.yaml"

    def __init__(self, path: Path | str):
        """Initialize vault with root directory path.

        Args:
            path: Path to vault root directory (e.g., ~/.koromind)
        """
        self.root = Path(path).expanduser().resolve()
        self.config_file = self.root / self.CONFIG_FILENAME
        self._config: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        """Load configuration, resolving paths relative to vault root.

        Returns:
            Dict with SDK-compatible configuration. Empty dict if no config file.

        Raises:
            VaultError: If config file exists but is invalid YAML.
        """
        if self._config is not None:
            return self._config

        if not self.config_file.exists():
            self._config = {}
            return self._config

        try:
            with open(self.config_file) as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise VaultError(f"Invalid YAML in {self.config_file}: {e}") from e

        if raw is None:
            self._config = {}
            return self._config

        if not isinstance(raw, dict):
            raise VaultError(
                f"vault-config.yaml must be a mapping, got {type(raw).__name__}"
            )

        self._config = self._resolve_paths(raw)
        return self._config

    def reload(self) -> dict[str, Any]:
        """Force reload configuration from disk.

        Returns:
            Fresh configuration dict.
        """
        self._config = None
        return self.load()

    def _resolve_paths(self, config: dict[str, Any]) -> dict[str, Any]:
        """Resolve relative paths to absolute paths within vault.

        Handles:
        - cwd: working directory
        - add_dirs: additional directories
        - system_prompt_file: prompt file path
        - Paths in mcp_servers args that start with ./

        Args:
            config: Raw configuration dict

        Returns:
            Config with resolved paths
        """
        result = config.copy()

        # Resolve cwd
        if "cwd" in result:
            result["cwd"] = str(self._resolve(result["cwd"]))

        # Resolve add_dirs (list of directories)
        if "add_dirs" in result:
            result["add_dirs"] = [str(self._resolve(p)) for p in result["add_dirs"]]

        # Resolve system_prompt_file
        if "system_prompt_file" in result:
            result["system_prompt_file"] = str(
                self._resolve(result["system_prompt_file"])
            )

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

    def _resolve_mcp_paths(
        self, mcp_servers: dict[str, Any]
    ) -> dict[str, Any]:
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
                    str(self._resolve(arg)) if isinstance(arg, str) and arg.startswith("./") else arg
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
