"""Unit tests for the Vault component."""

from pathlib import Path

import pytest

from koro.core.vault import Vault, VaultConfig, VaultError


class TestVaultLoad:
    """Tests for Vault.load() method."""

    def test_load_empty_when_no_config_file(self, tmp_path: Path):
        """Returns empty VaultConfig when vault-config.yaml doesn't exist."""
        vault = Vault(tmp_path)
        config = vault.load()
        assert config == VaultConfig()

    def test_load_empty_when_config_is_empty(self, tmp_path: Path):
        """Returns empty VaultConfig when config file is empty."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("")

        vault = Vault(tmp_path)
        config = vault.load()
        assert config == VaultConfig()

    def test_load_empty_when_config_is_null(self, tmp_path: Path):
        """Returns empty VaultConfig when config file contains only null."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("null")

        vault = Vault(tmp_path)
        config = vault.load()
        assert config == VaultConfig()

    def test_load_simple_config(self, tmp_path: Path):
        """Loads simple configuration correctly."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
mcp_servers:
  sqlite:
    command: "uvx"
    args: ["mcp-server-sqlite"]
""")
        vault = Vault(tmp_path)
        config = vault.load()

        assert "sqlite" in config.mcp_servers
        assert config.mcp_servers["sqlite"].command == "uvx"

    def test_load_raises_on_invalid_yaml(self, tmp_path: Path):
        """Raises VaultError on invalid YAML syntax."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        vault = Vault(tmp_path)
        with pytest.raises(VaultError, match="Invalid YAML"):
            vault.load()

    def test_load_raises_on_non_dict_yaml(self, tmp_path: Path):
        """Raises VaultError when YAML is not a mapping."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("- item1\n- item2")

        vault = Vault(tmp_path)
        with pytest.raises(VaultError, match="must be a mapping"):
            vault.load()

    def test_load_caches_config(self, tmp_path: Path):
        """Config is cached after first load."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
agents:
  test:
    system_prompt: "Test agent"
""")

        vault = Vault(tmp_path)
        config1 = vault.load()

        # Modify file
        config_file.write_text("""
agents:
  different:
    system_prompt: "Different agent"
""")

        # Should return cached version
        config2 = vault.load()
        assert config1 is config2
        assert "test" in config2.agents


class TestVaultReload:
    """Tests for Vault.reload() method."""

    def test_reload_clears_cache(self, tmp_path: Path):
        """Reload clears cache and reads fresh config."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
agents:
  original:
    system_prompt: "Original"
""")

        vault = Vault(tmp_path)
        config1 = vault.load()
        assert "original" in config1.agents

        # Modify file
        config_file.write_text("""
agents:
  updated:
    system_prompt: "Updated"
""")

        # Reload should get fresh content
        config2 = vault.reload()
        assert "updated" in config2.agents


class TestVaultPathResolution:
    """Tests for path resolution in Vault."""

    def test_resolves_mcp_server_paths(self, tmp_path: Path):
        """Paths in MCP server args are resolved."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
mcp_servers:
  sqlite:
    command: "uvx"
    args: ["mcp-server-sqlite", "--db-path", "./data.db"]
""")
        vault = Vault(tmp_path)
        config = vault.load()

        assert config.mcp_servers["sqlite"].args == [
            "mcp-server-sqlite",
            "--db-path",
            str(tmp_path / "data.db"),
        ]

    def test_resolves_hook_command_paths(self, tmp_path: Path):
        """Paths in hook commands are resolved."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./hooks/validate.sh"
""")
        vault = Vault(tmp_path)
        config = vault.load()

        hook_cmd = config.hooks["PreToolUse"][0].hooks[0].command
        assert hook_cmd == str(tmp_path / "hooks" / "validate.sh")

    def test_preserves_absolute_mcp_paths(self, tmp_path: Path):
        """Absolute paths in MCP args are preserved."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
mcp_servers:
  test:
    command: "test"
    args: ["/absolute/path", "relative"]
""")
        vault = Vault(tmp_path)
        config = vault.load()

        # Absolute path preserved, relative not starting with ./ also preserved
        assert config.mcp_servers["test"].args == ["/absolute/path", "relative"]


class TestVaultProperties:
    """Tests for Vault properties."""

    def test_exists_true_when_config_file_exists(self, tmp_path: Path):
        """exists property returns True when config file exists."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("plugins: []")

        vault = Vault(tmp_path)
        assert vault.exists is True

    def test_exists_false_when_config_file_missing(self, tmp_path: Path):
        """exists property returns False when config file is missing."""
        vault = Vault(tmp_path)
        assert vault.exists is False

    def test_root_is_resolved_absolute_path(self, tmp_path: Path):
        """Vault root is always an absolute resolved path."""
        vault = Vault(tmp_path / "subdir" / ".." / "actual")
        assert vault.root.is_absolute()
        # Path should be normalized
        assert ".." not in str(vault.root)

    def test_repr(self, tmp_path: Path):
        """String representation is useful for debugging."""
        vault = Vault(tmp_path)
        assert "Vault" in repr(vault)
        assert str(tmp_path) in repr(vault)


class TestVaultFullConfig:
    """Tests for loading complete vault configurations."""

    def test_load_full_config(self, tmp_path: Path):
        """Loads a complete configuration with all sections."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
mcp_servers:
  sqlite:
    command: "uvx"
    args: ["mcp-server-sqlite", "--db-path", "./data.db"]

agents:
  researcher:
    model: "claude-sonnet-4-20250514"
    system_prompt: "You are a researcher."
    allowed_tools: ["WebSearch", "Read"]

hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./hooks/validate.sh"

sandbox:
  enabled: false
  autoAllowBashIfSandboxed: true
  whiteListedCommands:
    - git
    - docker

plugins: []
""")
        vault = Vault(tmp_path)
        config = vault.load()

        # Check all sections are present
        assert "sqlite" in config.mcp_servers
        assert "researcher" in config.agents
        assert "PreToolUse" in config.hooks
        assert config.sandbox.enabled is False
        assert config.sandbox.white_listed_commands == ["git", "docker"]
        assert config.plugins == []


class TestSandboxConfig:
    """Tests for SandboxConfig with aliases."""

    def test_snake_case_fields(self, tmp_path: Path):
        """Snake case field names work."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
sandbox:
  enabled: true
  auto_allow_bash_if_sandboxed: false
  white_listed_commands:
    - npm
""")
        vault = Vault(tmp_path)
        config = vault.load()

        assert config.sandbox.enabled is True
        assert config.sandbox.auto_allow_bash_if_sandboxed is False
        assert config.sandbox.white_listed_commands == ["npm"]

    def test_camel_case_aliases(self, tmp_path: Path):
        """CamelCase aliases work for backwards compatibility."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
sandbox:
  enabled: true
  autoAllowBashIfSandboxed: false
  whiteListedCommands:
    - yarn
""")
        vault = Vault(tmp_path)
        config = vault.load()

        assert config.sandbox.enabled is True
        assert config.sandbox.auto_allow_bash_if_sandboxed is False
        assert config.sandbox.white_listed_commands == ["yarn"]
