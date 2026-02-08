"""Unit tests for the Vault component."""

import json
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
    prompt: "Test agent"
""")

        vault = Vault(tmp_path)
        config1 = vault.load()

        # Modify file
        config_file.write_text("""
agents:
  different:
    prompt: "Different agent"
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
    prompt: "Original"
""")

        vault = Vault(tmp_path)
        config1 = vault.load()
        assert "original" in config1.agents

        # Modify file
        config_file.write_text("""
agents:
  updated:
    prompt: "Updated"
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
    model: "sonnet"
    description: "Research assistant"
    prompt: "You are a researcher."
    tools: ["WebSearch", "Read"]

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
        assert config.agents["researcher"].model == "sonnet"
        assert config.agents["researcher"].tools == ["WebSearch", "Read"]
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


class TestAgentConfig:
    """Tests for agent configuration with model selection."""

    def test_agent_with_model(self, tmp_path: Path):
        """Agent can specify model as short name."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
agents:
  researcher:
    model: "haiku"
    description: "Research agent"
    prompt: "You research things."
    tools: ["WebSearch"]
""")
        vault = Vault(tmp_path)
        config = vault.load()

        agent = config.agents["researcher"]
        assert agent.model == "haiku"
        assert agent.description == "Research agent"
        assert agent.prompt == "You research things."
        assert agent.tools == ["WebSearch"]

    def test_agent_model_literals(self, tmp_path: Path):
        """Model field only accepts valid SDK literals."""
        config_file = tmp_path / "vault-config.yaml"

        for model in ("sonnet", "opus", "haiku", "inherit"):
            config_file.write_text(f"""
agents:
  test:
    model: "{model}"
    prompt: "Test"
""")
            vault = Vault(tmp_path)
            config = vault.load()
            assert config.agents["test"].model == model

    def test_agent_rejects_full_model_id(self, tmp_path: Path):
        """Full model IDs like 'claude-sonnet-4-20250514' are rejected."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
agents:
  test:
    model: "claude-sonnet-4-20250514"
    prompt: "Test"
""")
        vault = Vault(tmp_path)
        with pytest.raises(Exception):
            vault.load()

    def test_agent_prompt_file_resolves(self, tmp_path: Path):
        """Agent prompt_file paths are resolved relative to vault root."""
        prompt_dir = tmp_path / "agents"
        prompt_dir.mkdir()
        (prompt_dir / "helper.md").write_text("You are a helper.")

        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
agents:
  helper:
    prompt_file: "./agents/helper.md"
""")
        vault = Vault(tmp_path)
        config = vault.load()

        agent = config.agents["helper"]
        assert agent.prompt_file == str(tmp_path / "agents" / "helper.md")

    def test_agent_without_model(self, tmp_path: Path):
        """Agent without model defaults to None (inherits)."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
agents:
  simple:
    prompt: "A simple agent"
""")
        vault = Vault(tmp_path)
        config = vault.load()

        assert config.agents["simple"].model is None
        assert config.agents["simple"].prompt == "A simple agent"

    def test_agent_rejects_unknown_fields(self, tmp_path: Path):
        """Unknown fields in agent config are rejected."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
agents:
  test:
    prompt: "Test"
    unknown_field: "value"
""")
        vault = Vault(tmp_path)
        with pytest.raises(Exception):
            vault.load()

    def test_agent_rejects_prompt_and_prompt_file(self, tmp_path: Path):
        """Cannot set both prompt and prompt_file."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
agents:
  test:
    prompt: "Inline prompt"
    prompt_file: "./agents/test.md"
""")
        vault = Vault(tmp_path)
        with pytest.raises(Exception, match="prompt or prompt_file, not both"):
            vault.load()


class TestMcpJsonFile:
    """Tests for loading MCP servers from a JSON file."""

    def _write_mcp_json(self, path: Path, data: dict) -> None:
        with open(path, "w") as f:
            json.dump(data, f)

    def test_load_mcp_from_json_file(self, tmp_path: Path):
        """Loads MCP servers from a referenced JSON file."""
        mcp_file = tmp_path / "mcp.json"
        self._write_mcp_json(
            mcp_file,
            {
                "mcpServers": {
                    "sqlite": {
                        "command": "uvx",
                        "args": ["mcp-server-sqlite"],
                    },
                },
            },
        )

        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text('mcp_servers: "./mcp.json"')

        vault = Vault(tmp_path)
        config = vault.load()

        assert "sqlite" in config.mcp_servers
        assert config.mcp_servers["sqlite"].command == "uvx"
        assert config.mcp_servers["sqlite"].args == ["mcp-server-sqlite"]

    def test_load_mcp_json_resolves_paths(self, tmp_path: Path):
        """Relative paths in MCP server args are resolved after JSON loading."""
        mcp_file = tmp_path / "mcp.json"
        self._write_mcp_json(
            mcp_file,
            {
                "mcpServers": {
                    "sqlite": {
                        "command": "uvx",
                        "args": ["mcp-server-sqlite", "--db-path", "./data.db"],
                    },
                },
            },
        )

        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text('mcp_servers: "./mcp.json"')

        vault = Vault(tmp_path)
        config = vault.load()

        assert config.mcp_servers["sqlite"].args == [
            "mcp-server-sqlite",
            "--db-path",
            str(tmp_path / "data.db"),
        ]

    def test_load_mcp_json_missing_file(self, tmp_path: Path):
        """Raises VaultError when referenced JSON file doesn't exist."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text('mcp_servers: "./nonexistent.json"')

        vault = Vault(tmp_path)
        with pytest.raises(VaultError, match="not found"):
            vault.load()

    def test_load_mcp_json_invalid_json(self, tmp_path: Path):
        """Raises VaultError when JSON file contains invalid JSON."""
        mcp_file = tmp_path / "mcp.json"
        mcp_file.write_text("{invalid json")

        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text('mcp_servers: "./mcp.json"')

        vault = Vault(tmp_path)
        with pytest.raises(VaultError, match="Invalid JSON"):
            vault.load()

    def test_load_mcp_json_missing_key(self, tmp_path: Path):
        """Raises VaultError when JSON file lacks mcpServers key."""
        mcp_file = tmp_path / "mcp.json"
        self._write_mcp_json(mcp_file, {"servers": {}})

        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text('mcp_servers: "./mcp.json"')

        vault = Vault(tmp_path)
        with pytest.raises(VaultError, match="mcpServers"):
            vault.load()
