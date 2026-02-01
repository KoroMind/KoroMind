"""End-to-end integration tests."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from koro.claude import ClaudeClient
from koro.core.types import QueryConfig
from koro.voice import VoiceEngine

# Load environment variables
load_dotenv()


def _has_claude_auth():
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        return True
    creds_path = Path.home() / ".claude" / ".credentials.json"
    return creds_path.exists()


# Skip if missing any required API
pytestmark = pytest.mark.skipif(
    not os.getenv("ELEVENLABS_API_KEY") or not _has_claude_auth(),
    reason="Missing API keys for E2E test",
)


@pytest.mark.live
class TestFullPipeline:
    """End-to-end tests for the complete voice pipeline."""

    @pytest.mark.asyncio
    async def test_voice_to_voice_flow(self, tmp_path):
        """Complete flow: TTS -> STT -> Claude -> TTS."""
        voice = VoiceEngine(api_key=os.getenv("ELEVENLABS_API_KEY"))
        claude = ClaudeClient(
            sandbox_dir=str(tmp_path / "sandbox"), working_dir=str(tmp_path)
        )
        (tmp_path / "sandbox").mkdir()

        # 1. Simulate user voice input (generate test audio)
        user_input = "What is two plus two?"
        input_audio = await voice.text_to_speech(user_input)
        assert input_audio is not None

        # 2. Transcribe user input
        transcription = await voice.transcribe(input_audio.getvalue())
        assert len(transcription) > 0

        # 3. Send to Claude
        config = QueryConfig(prompt=transcription, include_megg=False)
        response, session_id, metadata = await claude.query(config)
        assert len(response) > 0

        # 4. Convert response to speech
        response_audio = await voice.text_to_speech(response[:200])
        assert response_audio is not None
        assert len(response_audio.getvalue()) > 1000

    @pytest.mark.asyncio
    async def test_session_persistence_flow(self, tmp_path):
        """Test that sessions persist across interactions."""
        claude = ClaudeClient(
            sandbox_dir=str(tmp_path / "sandbox"), working_dir=str(tmp_path)
        )
        (tmp_path / "sandbox").mkdir()

        # First interaction
        first_config = QueryConfig(
            prompt="My favorite color is purple. Remember this.",
            include_megg=False,
        )
        _, session_id, _ = await claude.query(first_config)
        assert session_id

        # Second interaction using same session
        followup_config = QueryConfig(
            prompt="What is my favorite color?",
            session_id=session_id,
            include_megg=False,
        )
        response, _, _ = await claude.query(followup_config)

        assert "purple" in response.lower()

    @pytest.mark.asyncio
    async def test_tool_execution_flow(self, tmp_path):
        """Test Claude can execute tools in the flow."""
        sandbox = tmp_path / "sandbox"
        sandbox.mkdir()

        claude = ClaudeClient(sandbox_dir=str(sandbox), working_dir=str(tmp_path))

        # Create a file for Claude to read
        test_file = tmp_path / "data.txt"
        test_file.write_text("The secret code is: ALPHA123")

        config = QueryConfig(
            prompt=f"Read the file at {test_file} and tell me the secret code.",
            include_megg=False,
        )
        response, _, metadata = await claude.query(config)

        assert "ALPHA123" in response


@pytest.mark.live
class TestErrorHandling:
    """Tests for error handling in the pipeline."""

    @pytest.mark.asyncio
    async def test_handles_empty_transcription(self):
        """Pipeline handles empty/failed transcription gracefully."""
        voice = VoiceEngine(api_key=os.getenv("ELEVENLABS_API_KEY"))

        # Try to transcribe invalid audio
        result = await voice.transcribe(b"not valid audio data")

        # Should return error message, not crash
        assert "error" in result.lower() or len(result) > 0

    @pytest.mark.asyncio
    async def test_handles_long_response(self, tmp_path):
        """Pipeline handles long Claude responses."""
        claude = ClaudeClient(
            sandbox_dir=str(tmp_path / "sandbox"), working_dir=str(tmp_path)
        )
        (tmp_path / "sandbox").mkdir()

        # Ask for a longer response
        config = QueryConfig(
            prompt="List the first 10 prime numbers with a brief explanation of each.",
            include_megg=False,
        )
        response, _, _ = await claude.query(config)

        # Should handle the response
        assert len(response) > 100

        # TTS should handle truncation if needed
        voice = VoiceEngine(api_key=os.getenv("ELEVENLABS_API_KEY"))
        audio = await voice.text_to_speech(response[:500])
        assert audio is not None
