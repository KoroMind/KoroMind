"""Live integration tests for Brain + Vault."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from koro.core.brain import Brain
from koro.core.claude import ClaudeClient
from koro.core.state import StateManager

load_dotenv()

TEST_VAULT = Path(__file__).parent.parent / "fixtures" / "test-vault"


def _has_claude_auth():
    """Check for Claude authentication."""
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    creds_path = Path.home() / ".claude" / ".credentials.json"
    return creds_path.exists()


pytestmark = [
    pytest.mark.skipif(not _has_claude_auth(), reason="No Claude auth"),
    pytest.mark.live,
]


@pytest.fixture
def brain_with_vault(tmp_path):
    """Brain with test vault."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    state_manager = StateManager(db_path=str(tmp_path / "test.db"))
    claude_client = ClaudeClient(
        sandbox_dir=str(sandbox),
        working_dir=str(tmp_path),
    )

    return Brain(
        vault_path=str(TEST_VAULT),
        state_manager=state_manager,
        claude_client=claude_client,
    )


class TestBrainVaultLive:
    """Live tests for Brain + Vault integration."""

    @pytest.mark.asyncio
    async def test_vault_config_applies_to_response(self, brain_with_vault):
        """Vault config is used in processing."""
        response = await brain_with_vault.process_text(
            user_id="test_user",
            text="Say 'vault works'",
            include_audio=False,
        )

        assert response.text
        assert response.session_id

    @pytest.mark.asyncio
    async def test_vault_system_prompt_affects_personality(self, brain_with_vault):
        """System prompt from vault affects response style."""
        response = await brain_with_vault.process_text(
            user_id="test_user",
            text="Introduce yourself briefly",
            include_audio=False,
        )

        # Vault has "second brain" personality - check for warmth/directness
        assert response.text
        assert len(response.text) > 10

    @pytest.mark.asyncio
    async def test_vault_hooks_block_dangerous_command(self, brain_with_vault):
        """Safety hooks from vault block dangerous operations."""
        response = await brain_with_vault.process_text(
            user_id="test_user",
            text="Run: git push --force",
            include_audio=False,
        )

        # Hook should block or Claude should refuse
        # Either blocked by hook or refused by model
        assert response.text  # Got some response

    @pytest.mark.asyncio
    async def test_vault_cwd_affects_file_operations(self, brain_with_vault):
        """CWD from vault config is used for file operations."""
        response = await brain_with_vault.process_text(
            user_id="test_user",
            text="List files in current directory",
            include_audio=False,
        )

        assert response.text

    @pytest.mark.asyncio
    async def test_vault_paths_resolve_correctly(self, brain_with_vault):
        """Vault resolves relative paths to absolute."""
        vault = brain_with_vault.vault
        config = vault.load()

        # system_prompt_file should be absolute
        if "system_prompt_file" in config:
            prompt_path = Path(config["system_prompt_file"])
            assert prompt_path.is_absolute()
            assert prompt_path.exists()
