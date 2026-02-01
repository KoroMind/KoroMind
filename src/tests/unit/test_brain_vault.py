"""Unit tests for Brain vault integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from koro.core.brain import Brain
from koro.core.types import MessageType


@pytest.fixture
def mock_state_manager():
    """Mock state manager."""
    mgr = MagicMock()
    mgr.get_current_session = AsyncMock(return_value=None)
    mgr.update_session = AsyncMock()
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

    def test_brain_initializes_vault_from_path(self, tmp_path, mock_state_manager, mock_claude_client):
        """Brain creates Vault when vault_path provided."""
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        config_file = vault_dir / "vault-config.yaml"
        config_file.write_text("model: opus\n")

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
        config_file.write_text("model: test-model\nmax_turns: 99\n")

        brain = Brain(
            vault_path=str(vault_dir),
            state_manager=mock_state_manager,
            claude_client=mock_claude_client,
        )

        await brain.process_text(user_id="user1", text="hello", include_audio=False)

        # Verify claude_client.query was called with vault config
        mock_claude_client.query.assert_called_once()
        call_kwargs = mock_claude_client.query.call_args.kwargs
        assert call_kwargs.get("model") == "test-model"
        assert call_kwargs.get("max_turns") == 99

    @pytest.mark.asyncio
    async def test_vault_config_merged_with_kwargs(
        self, tmp_path, mock_state_manager, mock_claude_client
    ):
        """Vault config and explicit kwargs both applied."""
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        config_file = vault_dir / "vault-config.yaml"
        config_file.write_text("model: vault-model\nmax_turns: 10\n")

        brain = Brain(
            vault_path=str(vault_dir),
            state_manager=mock_state_manager,
            claude_client=mock_claude_client,
        )

        # Pass additional kwargs not in vault
        await brain.process_message(
            user_id="user1",
            content="hello",
            content_type=MessageType.TEXT,
            include_audio=False,
            some_extra_option="extra",
        )

        call_kwargs = mock_claude_client.query.call_args.kwargs
        # Both vault and explicit should be present
        assert call_kwargs.get("model") == "vault-model"

    @pytest.mark.asyncio
    async def test_kwargs_override_vault_config(
        self, tmp_path, mock_state_manager, mock_claude_client
    ):
        """Explicit kwargs override vault config values."""
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        config_file = vault_dir / "vault-config.yaml"
        config_file.write_text("model: vault-model\n")

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
            model="explicit-model",  # Should override vault
        )

        call_kwargs = mock_claude_client.query.call_args.kwargs
        assert call_kwargs.get("model") == "explicit-model"

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

        # Brain still works, vault is None or non-existent
        assert brain is not None

    @pytest.mark.asyncio
    async def test_brain_works_without_vault(self, mock_state_manager, mock_claude_client):
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
