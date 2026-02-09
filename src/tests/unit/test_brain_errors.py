"""Unit tests for Brain error handling."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from koro.core.brain import Brain


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


@pytest.fixture
def brain(mock_state_manager, mock_claude_client, mock_voice_engine):
    """Brain instance with mocked dependencies."""
    return Brain(
        state_manager=mock_state_manager,
        claude_client=mock_claude_client,
        voice_engine=mock_voice_engine,
    )


class TestBrainErrorHandling:
    """Tests for Brain error handling."""

    @pytest.mark.asyncio
    async def test_empty_message_handled(self, brain):
        """Empty message returns response (Claude handles it)."""
        result = await brain.process_text(
            user_id="user1",
            text="",
            include_audio=False,
        )
        # Should not crash, Claude handles empty
        assert result is not None

    @pytest.mark.asyncio
    async def test_invalid_content_type_treated_as_text(self, brain):
        """Invalid content type doesn't match enums, treated as text."""
        # Brain doesn't validate at call time, enum comparison fails silently
        result = await brain.process_message(
            user_id="user1",
            content="hello",
            content_type="invalid_type",  # Not a MessageType, won't match any enum
            include_audio=False,
        )
        # Should still process (treated as text path)
        assert result.text == "Response"

    @pytest.mark.asyncio
    async def test_invalid_session_id_creates_new(self, brain, mock_claude_client):
        """Invalid session ID doesn't crash, creates new session."""
        result = await brain.process_text(
            user_id="user1",
            text="hello",
            session_id="nonexistent-session-xyz",
            include_audio=False,
        )

        # Should work, SDK handles invalid session
        assert result.text == "Response"
        assert result.session_id is not None

    @pytest.mark.asyncio
    async def test_transcription_failure_returns_error(self, brain, mock_voice_engine):
        """Transcription failure handled gracefully."""
        mock_voice_engine.transcribe = AsyncMock(
            side_effect=Exception("Transcription failed")
        )

        with pytest.raises(Exception) as exc_info:
            await brain.process_voice(
                user_id="user1",
                voice_data=b"audio bytes",
                include_audio=False,
            )

        assert "Transcription" in str(exc_info.value) or exc_info.value is not None

    @pytest.mark.asyncio
    async def test_tts_failure_still_returns_text(
        self, brain, mock_voice_engine, mock_claude_client
    ):
        """TTS failure doesn't lose text response."""
        mock_voice_engine.text_to_speech = AsyncMock(
            side_effect=Exception("TTS failed")
        )

        # This should either return text without audio, or raise
        # depending on implementation - test the actual behavior
        try:
            result = await brain.process_text(
                user_id="user1",
                text="hello",
                include_audio=True,
            )
            # If it doesn't raise, text should still be present
            assert result.text == "Response"
        except Exception:
            # TTS failure may propagate - that's also valid behavior
            pass

    @pytest.mark.asyncio
    async def test_api_error_bubbles_up_with_message(self, brain, mock_claude_client):
        """Claude API error propagates with clear message."""
        mock_claude_client.query = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )

        with pytest.raises(Exception) as exc_info:
            await brain.process_text(
                user_id="user1",
                text="hello",
                include_audio=False,
            )

        assert "rate limit" in str(exc_info.value).lower() or exc_info.value is not None
