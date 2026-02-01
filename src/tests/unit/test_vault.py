"""Unit tests for the Vault component."""

from pathlib import Path

import pytest

from koro.core.vault import Vault, VaultError


class TestVaultLoad:
    """Tests for Vault.load() method."""

    def test_load_empty_when_no_config_file(self, tmp_path: Path):
        """Returns empty dict when vault-config.yaml doesn't exist."""
        vault = Vault(tmp_path)
        config = vault.load()
        assert config == {}

    def test_load_empty_when_config_is_empty(self, tmp_path: Path):
        """Returns empty dict when config file is empty."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("")

        vault = Vault(tmp_path)
        config = vault.load()
        assert config == {}

    def test_load_empty_when_config_is_null(self, tmp_path: Path):
        """Returns empty dict when config file contains only null."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("null")

        vault = Vault(tmp_path)
        config = vault.load()
        assert config == {}

    def test_load_simple_config(self, tmp_path: Path):
        """Loads simple configuration correctly."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
model: "claude-sonnet-4-20250514"
max_turns: 50
""")
        vault = Vault(tmp_path)
        config = vault.load()

        assert config["model"] == "claude-sonnet-4-20250514"
        assert config["max_turns"] == 50

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
        config_file.write_text("model: test-model")

        vault = Vault(tmp_path)
        config1 = vault.load()

        # Modify file
        config_file.write_text("model: different-model")

        # Should return cached version
        config2 = vault.load()
        assert config1 is config2
        assert config2["model"] == "test-model"


class TestVaultReload:
    """Tests for Vault.reload() method."""

    def test_reload_clears_cache(self, tmp_path: Path):
        """Reload clears cache and reads fresh config."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("model: original")

        vault = Vault(tmp_path)
        config1 = vault.load()
        assert config1["model"] == "original"

        # Modify file
        config_file.write_text("model: updated")

        # Reload should get fresh content
        config2 = vault.reload()
        assert config2["model"] == "updated"


class TestVaultPathResolution:
    """Tests for path resolution in Vault."""

    def test_resolves_relative_cwd(self, tmp_path: Path):
        """Relative cwd is resolved to absolute path."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text('cwd: "."')

        vault = Vault(tmp_path)
        config = vault.load()

        assert config["cwd"] == str(tmp_path)

    def test_resolves_relative_cwd_subdirectory(self, tmp_path: Path):
        """Relative cwd with subdirectory is resolved correctly."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text('cwd: "./sandbox"')

        vault = Vault(tmp_path)
        config = vault.load()

        assert config["cwd"] == str(tmp_path / "sandbox")

    def test_preserves_absolute_cwd(self, tmp_path: Path):
        """Absolute cwd paths are preserved as-is."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text('cwd: "/usr/local/bin"')

        vault = Vault(tmp_path)
        config = vault.load()

        assert config["cwd"] == "/usr/local/bin"

    def test_resolves_add_dirs(self, tmp_path: Path):
        """add_dirs list is resolved correctly."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("""
add_dirs:
  - "."
  - "./projects"
  - "/absolute/path"
""")
        vault = Vault(tmp_path)
        config = vault.load()

        assert config["add_dirs"] == [
            str(tmp_path),
            str(tmp_path / "projects"),
            "/absolute/path",
        ]

    def test_resolves_system_prompt_file(self, tmp_path: Path):
        """system_prompt_file is resolved correctly."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text('system_prompt_file: "./prompts/main.md"')

        vault = Vault(tmp_path)
        config = vault.load()

        assert config["system_prompt_file"] == str(tmp_path / "prompts" / "main.md")

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

        assert config["mcp_servers"]["sqlite"]["args"] == [
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

        hook_cmd = config["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        assert hook_cmd == str(tmp_path / "hooks" / "validate.sh")

    def test_expands_home_directory(self, tmp_path: Path):
        """Tilde is expanded to home directory."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text('cwd: "~/Documents"')

        vault = Vault(tmp_path)
        config = vault.load()

        assert config["cwd"] == str(Path.home() / "Documents")


class TestVaultProperties:
    """Tests for Vault properties."""

    def test_exists_true_when_config_file_exists(self, tmp_path: Path):
        """exists property returns True when config file exists."""
        config_file = tmp_path / "vault-config.yaml"
        config_file.write_text("model: test")

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
cwd: "."
add_dirs:
  - "./projects"

model: "claude-sonnet-4-20250514"
fallback_model: "claude-sonnet-4-20250514"
max_turns: 50
max_budget_usd: 5.0

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
  excludedCommands:
    - git
    - docker

plugins: []
""")
        vault = Vault(tmp_path)
        config = vault.load()

        # Check all sections are present
        assert config["cwd"] == str(tmp_path)
        assert config["add_dirs"] == [str(tmp_path / "projects")]
        assert config["model"] == "claude-sonnet-4-20250514"
        assert config["max_turns"] == 50
        assert config["max_budget_usd"] == 5.0
        assert "sqlite" in config["mcp_servers"]
        assert "researcher" in config["agents"]
        assert "PreToolUse" in config["hooks"]
        assert config["sandbox"]["enabled"] is False
        assert config["plugins"] == []
