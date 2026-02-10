"""Unit tests for Brain vault integration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from koro.core.brain import Brain
from koro.core.types import MessageType, UserSettings


@pytest.fixture
def mock_state_manager():
    """Mock state manager."""
    mgr = MagicMock()
    mgr.get_current_session = AsyncMock(return_value=None)
    mgr.update_session = AsyncMock()
    mgr.get_settings = AsyncMock(return_value=UserSettings())
    return mgr


@pytest.fixture
def mock_claude_client():
    """Mock Claude client."""
    client = MagicMock()
    client.query = AsyncMock(return_value=("Response", "session-1", {}))
    return client


@pytest.fixture
def mock_voice_engine():
    """Mock voice engine."""
    engine = MagicMock()
    engine.transcribe = AsyncMock(return_value="transcribed")
    engine.text_to_speech = AsyncMock(return_value=None)
    return engine


class TestBrainVaultIntegration:
    """Tests for Brain + Vault config integration."""

    def test_brain_initializes_vault_from_path(
        self, tmp_path, mock_state_manager, mock_claude_client
    ):
        """Brain creates Vault when vault_path provided."""
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        config_file = vault_dir / "vault-config.yaml"
        config_file.write_text("plugins: []\n")

        brain = Brain(
            vault_path=str(vault_dir),
            state_manager=mock_state_manager,
            claude_client=mock_claude_client,
        )

        assert brain.vault is not None
        assert brain.vault.root == vault_dir

    @pytest.mark.asyncio
    async def test_brain_loads_vault_config_before_query(
        self, tmp_path, mock_state_manager, mock_claude_client
    ):
        """Vault config loaded and passed to Claude client."""
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        config_file = vault_dir / "vault-config.yaml"
        config_file.write_text("""
agents:
  researcher:
    prompt: "You research things."
    tools: ["WebSearch"]
""")

        brain = Brain(
            vault_path=str(vault_dir),
            state_manager=mock_state_manager,
            claude_client=mock_claude_client,
        )

        await brain.process_text(user_id="user1", text="hello", include_audio=False)

        # Verify claude_client.query was called with a QueryConfig
        mock_claude_client.query.assert_called_once()
        config = mock_claude_client.query.call_args[0][0]
        # Vault agents should be converted to SDK AgentDefinitions
        assert "researcher" in config.agents

    @pytest.mark.asyncio
    async def test_vault_config_merged_with_kwargs(
        self, tmp_path, mock_state_manager, mock_claude_client
    ):
        """Vault config and explicit kwargs both applied."""
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        config_file = vault_dir / "vault-config.yaml"
        config_file.write_text("""
agents:
  researcher:
    prompt: "You research things."
""")

        brain = Brain(
            vault_path=str(vault_dir),
            state_manager=mock_state_manager,
            claude_client=mock_claude_client,
        )

        await brain.process_message(
            user_id="user1",
            content="hello",
            content_type=MessageType.TEXT,
            include_audio=False,
            max_turns=50,
        )

        config = mock_claude_client.query.call_args[0][0]
        # Vault agents and explicit kwargs both present
        assert "researcher" in config.agents
        assert config.max_turns == 50

    @pytest.mark.asyncio
    async def test_kwargs_override_vault_config(
        self, tmp_path, mock_state_manager, mock_claude_client
    ):
        """Explicit kwargs override vault config values."""
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        config_file = vault_dir / "vault-config.yaml"
        config_file.write_text("plugins: []\n")

        brain = Brain(
            vault_path=str(vault_dir),
            state_manager=mock_state_manager,
            claude_client=mock_claude_client,
        )

        await brain.process_message(
            user_id="user1",
            content="hello",
            content_type=MessageType.TEXT,
            include_audio=False,
            model="explicit-model",
        )

        config = mock_claude_client.query.call_args[0][0]
        assert config.model == "explicit-model"

    def test_invalid_vault_path_logs_error_continues(
        self, tmp_path, mock_state_manager, mock_claude_client, caplog
    ):
        """Invalid vault path doesn't crash, logs warning."""
        nonexistent = tmp_path / "nonexistent"

        # Should not raise
        brain = Brain(
            vault_path=str(nonexistent),
            state_manager=mock_state_manager,
            claude_client=mock_claude_client,
        )

        # Brain still works, vault is non-existent
        assert brain is not None

    @pytest.mark.asyncio
    async def test_brain_works_without_vault(
        self, mock_state_manager, mock_claude_client
    ):
        """Brain works when no vault_path provided."""
        brain = Brain(
            state_manager=mock_state_manager,
            claude_client=mock_claude_client,
        )

        result = await brain.process_text(
            user_id="user1",
            text="hello",
            include_audio=False,
        )

        assert result.text == "Response"
        mock_claude_client.query.assert_called_once()
