"""Integration tests for Vault configuration loading.

These tests verify the complete vault experience:
- Config loads correctly
- Paths resolve to absolute paths
- All referenced files exist
- Config is SDK-compatible
"""

import os
from pathlib import Path

from koro.core.vault import Vault, VaultConfig

# Path to test vault fixture
TEST_VAULT = Path(__file__).parent.parent / "fixtures" / "test-vault"


class TestVaultIntegration:
    """Integration tests for the complete vault experience."""

    def test_vault_exists(self):
        """Test vault fixture exists."""
        assert TEST_VAULT.exists(), f"Test vault not found at {TEST_VAULT}"
        assert (TEST_VAULT / "vault-config.yaml").exists()

    def test_load_complete_config(self):
        """Load the complete vault config successfully."""
        vault = Vault(TEST_VAULT)
        config = vault.load()

        assert config is not None
        assert isinstance(config, VaultConfig)

    def test_model_configuration(self):
        """Verify model is set to Opus 4.5."""
        vault = Vault(TEST_VAULT)
        config = vault.load()

        assert config.model == "claude-opus-4-5-20250514"
        assert config.max_turns == 100

    def test_system_prompt_file_resolves(self):
        """System prompt file path resolves to absolute path."""
        vault = Vault(TEST_VAULT)
        config = vault.load()

        prompt_path = Path(config.system_prompt_file)

        # Should be absolute
        assert prompt_path.is_absolute()

        # Should exist
        assert prompt_path.exists(), f"System prompt not found: {prompt_path}"

        # Should contain second brain content
        content = prompt_path.read_text()
        assert "KoroMind" in content
        assert "Second Brain" in content

    def test_cwd_resolves(self):
        """CWD resolves to vault root."""
        vault = Vault(TEST_VAULT)
        config = vault.load()

        assert config.cwd == str(TEST_VAULT)

    def test_hooks_command_resolves(self):
        """Hook command paths resolve to absolute paths."""
        vault = Vault(TEST_VAULT)
        config = vault.load()

        # Get the safety hook command
        pre_tool_hooks = config.hooks["PreToolUse"]
        bash_matcher = next(h for h in pre_tool_hooks if h.matcher == "Bash")
        command_hook = bash_matcher.hooks[0]

        hook_path = Path(command_hook.command)

        # Should be absolute
        assert hook_path.is_absolute()

        # Should exist
        assert hook_path.exists(), f"Hook script not found: {hook_path}"

        # Should be executable
        assert os.access(hook_path, os.X_OK), f"Hook not executable: {hook_path}"

    def test_all_referenced_files_exist(self):
        """Every file referenced in config actually exists."""
        vault = Vault(TEST_VAULT)
        config = vault.load()

        # Check system prompt
        if config.system_prompt_file:
            assert Path(config.system_prompt_file).exists()

        # Check hooks
        if config.hooks:
            for event, matchers in config.hooks.items():
                for matcher in matchers:
                    for hook in matcher.hooks:
                        cmd_path = Path(hook.command)
                        if cmd_path.is_absolute():
                            assert cmd_path.exists(), f"Hook not found: {cmd_path}"

    def test_agent_files_exist(self):
        """Agent markdown files exist in vault."""
        agents_dir = TEST_VAULT / "agents"
        assert agents_dir.exists()

        researcher = agents_dir / "researcher.md"
        assert researcher.exists()

        content = researcher.read_text()
        assert "researcher" in content.lower()

    def test_config_is_sdk_compatible(self):
        """Config structure is compatible with Claude SDK expectations."""
        vault = Vault(TEST_VAULT)
        config = vault.load()

        # These fields should be present and valid for SDK
        assert isinstance(config.model, str)
        assert isinstance(config.max_turns, int)
        assert isinstance(config.cwd, str)
        assert isinstance(config.hooks, dict)

        # Paths should be strings (SDK expects strings, not Path objects)
        assert isinstance(config.system_prompt_file, str)

    def test_reload_works(self):
        """Reload clears cache and re-reads config."""
        vault = Vault(TEST_VAULT)

        config1 = vault.load()
        config2 = vault.reload()

        # Should return fresh config
        assert config1 is not config2
        assert config1 == config2  # But same content


class TestVaultSecondBrainExperience:
    """Tests that verify the 'second brain' user experience."""

    def test_has_personality(self):
        """System prompt has character, not just instructions."""
        prompt_path = TEST_VAULT / "prompts" / "system.md"
        content = prompt_path.read_text()

        # Should have warmth
        assert "extension of" in content.lower() or "alongside" in content.lower()

        # Should have agency
        assert "proactive" in content.lower() or "agentic" in content.lower()

        # Should have honesty
        assert "honest" in content.lower()

    def test_has_safety_hooks(self):
        """Safety hooks protect user from accidents."""
        hook_path = TEST_VAULT / "hooks" / "safety.sh"
        content = hook_path.read_text()

        # Should block git push
        assert "git" in content and "push" in content

        # Should block dangerous rm
        assert "rm" in content or "dangerous" in content.lower()

    def test_uses_opus(self):
        """Uses the best model for a second brain."""
        vault = Vault(TEST_VAULT)
        config = vault.load()

        assert "opus" in config.model.lower()

    def test_generous_turn_limit(self):
        """Has enough turns for complex tasks."""
        vault = Vault(TEST_VAULT)
        config = vault.load()

        assert config.max_turns >= 50
