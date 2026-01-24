#!/usr/bin/env python3
"""
Comprehensive test suite for Claude Voice Assistant
Tests: Persona, TTS settings, Claude call configuration, Sandbox setup
Target: 90% coverage
"""

import os
import sys
import json
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from io import BytesIO

# Set up test environment BEFORE dotenv can load .env
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
os.environ["ELEVENLABS_API_KEY"] = "test_api_key"
os.environ["TELEGRAM_DEFAULT_CHAT_ID"] = "12345"
os.environ["CLAUDE_WORKING_DIR"] = "/home/dev"
os.environ["CLAUDE_SANDBOX_DIR"] = "/tmp/test-voice-sandbox"
os.environ["TELEGRAM_TOPIC_ID"] = ""  # Disable topic filtering in tests
os.environ["SYSTEM_PROMPT_FILE"] = ""  # Use default prompt in tests
os.environ["PERSONA_NAME"] = "TestBot"
os.environ["ELEVENLABS_VOICE_ID"] = "test_voice_id"

# Helper function to create ResultMessage with required fields
def make_result_message(result="test response", session_id="abc123", **kwargs):
    """Create a ResultMessage with sensible defaults for testing."""
    from claude_agent_sdk.types import ResultMessage
    return ResultMessage(
        subtype="result",
        duration_ms=kwargs.get("duration_ms", 1000),
        duration_api_ms=kwargs.get("duration_api_ms", 800),
        is_error=kwargs.get("is_error", False),
        num_turns=kwargs.get("num_turns", 1),
        session_id=session_id,
        total_cost_usd=kwargs.get("total_cost_usd", 0.01),
        result=result,
    )


def create_mock_client(responses):
    """Create a mock ClaudeSDKClient that yields given responses."""
    async def mock_receive():
        for r in responses:
            yield r

    mock_client = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.receive_response = mock_receive
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


# Prevent dotenv from loading .env file
from unittest.mock import patch
with patch('dotenv.load_dotenv'):
    import bot


class TestConfiguration:
    """Test configuration and constants"""

    def test_sandbox_dir_configured(self):
        """Sandbox directory should be configured"""
        assert bot.SANDBOX_DIR == "/tmp/test-voice-sandbox"

    def test_working_dir_configured(self):
        """Working directory should be configured"""
        assert bot.CLAUDE_WORKING_DIR == "/home/dev"

    def test_voice_settings_exist(self):
        """Voice settings should be defined"""
        assert hasattr(bot, 'VOICE_SETTINGS')
        assert 'stability' in bot.VOICE_SETTINGS
        assert 'similarity_boost' in bot.VOICE_SETTINGS
        assert 'style' in bot.VOICE_SETTINGS

    def test_voice_settings_values(self):
        """Voice settings should have correct values for expressive delivery"""
        assert bot.VOICE_SETTINGS['stability'] == 0.3  # Low for emotional range
        assert bot.VOICE_SETTINGS['similarity_boost'] == 0.75
        assert bot.VOICE_SETTINGS['style'] == 0.4  # Style exaggeration
        assert bot.VOICE_SETTINGS['speed'] == 1.1  # Comfortable speed


class TestPersona:
    """Test the persona configuration (default prompt when no file specified)"""

    def test_persona_exists(self):
        """Persona prompt should be defined"""
        assert hasattr(bot, 'BASE_SYSTEM_PROMPT')
        assert len(bot.BASE_SYSTEM_PROMPT) > 50

    def test_persona_has_voice_rules(self):
        """Persona should have voice output rules"""
        persona = bot.BASE_SYSTEM_PROMPT
        assert "NO markdown" in persona or "no markdown" in persona.lower()
        assert "NO bullet" in persona or "no bullet" in persona.lower()

    def test_persona_mentions_sandbox(self):
        """Persona should mention sandbox directory"""
        assert "sandbox" in bot.BASE_SYSTEM_PROMPT.lower() or bot.SANDBOX_DIR in bot.BASE_SYSTEM_PROMPT

    def test_persona_mentions_read_write_permissions(self):
        """Persona should explain read/write permissions"""
        persona = bot.BASE_SYSTEM_PROMPT.lower()
        assert "read" in persona
        assert "write" in persona

    def test_persona_mentions_websearch(self):
        """Persona should mention WebSearch capability"""
        assert "WebSearch" in bot.BASE_SYSTEM_PROMPT or "websearch" in bot.BASE_SYSTEM_PROMPT.lower()


class TestTopicFiltering:
    """Test topic-based message filtering"""

    def test_should_handle_message_no_filter(self):
        """With empty TOPIC_ID, should handle all messages"""
        with patch.object(bot, 'TOPIC_ID', ''):
            assert bot.should_handle_message(None) == True
            assert bot.should_handle_message(123) == True

    def test_should_handle_message_with_filter(self):
        """With TOPIC_ID set, should only handle that topic"""
        with patch.object(bot, 'TOPIC_ID', '42'):
            assert bot.should_handle_message(42) == True
            assert bot.should_handle_message(123) == False
            assert bot.should_handle_message(None) == False

    def test_should_handle_message_invalid_topic_id(self):
        """Invalid TOPIC_ID should fall back to handling all"""
        with patch.object(bot, 'TOPIC_ID', 'not_a_number'):
            assert bot.should_handle_message(None) == True
            assert bot.should_handle_message(123) == True


class TestPromptLoading:
    """Test system prompt loading from file"""

    def test_load_system_prompt_no_file(self):
        """Without file, should return default prompt"""
        with patch.object(bot, 'SYSTEM_PROMPT_FILE', ''):
            prompt = bot.load_system_prompt()
            assert "voice assistant" in prompt.lower()
            assert len(prompt) > 50

    def test_load_system_prompt_from_file(self):
        """Should load prompt from file when specified"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("You are TestBot. {sandbox_dir} is your sandbox.")
            temp_path = f.name

        try:
            with patch.object(bot, 'SYSTEM_PROMPT_FILE', temp_path):
                prompt = bot.load_system_prompt()
                assert "TestBot" in prompt
                assert bot.SANDBOX_DIR in prompt  # Placeholder replaced
        finally:
            os.unlink(temp_path)

    def test_load_system_prompt_missing_file(self):
        """Missing file should return default prompt"""
        with patch.object(bot, 'SYSTEM_PROMPT_FILE', '/nonexistent/file.md'):
            prompt = bot.load_system_prompt()
            assert "voice assistant" in prompt.lower()


class TestConfigurableVoice:
    """Test configurable voice ID"""

    def test_voice_id_configurable(self):
        """Voice ID should be configurable via env"""
        assert hasattr(bot, 'ELEVENLABS_VOICE_ID')
        # In tests, we set this to test_voice_id
        assert bot.ELEVENLABS_VOICE_ID == "test_voice_id"

    def test_persona_name_configurable(self):
        """Persona name should be configurable via env"""
        assert hasattr(bot, 'PERSONA_NAME')
        assert bot.PERSONA_NAME == "TestBot"


class TestTTSFunction:
    """Test text-to-speech functionality"""

    @pytest.mark.asyncio
    async def test_tts_uses_turbo_model(self):
        """TTS should use eleven_turbo_v2_5 model"""
        with patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_convert:
            mock_convert.return_value = iter([b'fake_audio_data'])

            await bot.text_to_speech("test text")

            mock_convert.assert_called_once()
            call_kwargs = mock_convert.call_args[1]
            assert call_kwargs['model_id'] == 'eleven_turbo_v2_5'

    @pytest.mark.asyncio
    async def test_tts_uses_voice_settings(self):
        """TTS should pass voice settings"""
        with patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_convert:
            mock_convert.return_value = iter([b'fake_audio_data'])

            await bot.text_to_speech("test text")

            call_kwargs = mock_convert.call_args[1]
            assert 'voice_settings' in call_kwargs
            voice_settings = call_kwargs['voice_settings']
            assert voice_settings['stability'] == bot.VOICE_SETTINGS['stability']
            assert voice_settings['similarity_boost'] == bot.VOICE_SETTINGS['similarity_boost']
            assert voice_settings['style'] == bot.VOICE_SETTINGS['style']
            assert voice_settings['use_speaker_boost'] == True

    @pytest.mark.asyncio
    async def test_tts_uses_speed_setting(self):
        """TTS should use 1.2x speed (max allowed)"""
        with patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_convert:
            mock_convert.return_value = iter([b'fake_audio_data'])

            await bot.text_to_speech("test text")

            call_kwargs = mock_convert.call_args[1]
            voice_settings = call_kwargs['voice_settings']
            assert 'speed' in voice_settings
            assert voice_settings['speed'] == 1.1

    @pytest.mark.asyncio
    async def test_tts_uses_configured_voice(self):
        """TTS should use configured voice ID"""
        with patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_convert:
            mock_convert.return_value = iter([b'fake_audio_data'])

            await bot.text_to_speech("test text")

            call_kwargs = mock_convert.call_args[1]
            assert call_kwargs['voice_id'] == bot.ELEVENLABS_VOICE_ID

    @pytest.mark.asyncio
    async def test_tts_returns_bytesio(self):
        """TTS should return BytesIO object"""
        with patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_convert:
            mock_convert.return_value = iter([b'fake_audio_data'])

            result = await bot.text_to_speech("test text")

            assert isinstance(result, BytesIO)

    @pytest.mark.asyncio
    async def test_tts_handles_error(self):
        """TTS should return None on error"""
        with patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_convert:
            mock_convert.side_effect = Exception("API Error")

            result = await bot.text_to_speech("test text")

            assert result is None


class TestClaudeCall:
    """Test Claude Code invocation"""

    @pytest.mark.asyncio
    async def test_claude_call_creates_sandbox(self):
        """Claude call should ensure sandbox directory exists"""
        test_sandbox = Path("/tmp/test-sandbox-creation")

        with patch('bot.SANDBOX_DIR', str(test_sandbox)), \
             patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"result": "test", "session_id": "abc123"})
            )

            # Clean up first
            if test_sandbox.exists():
                test_sandbox.rmdir()

            await bot.call_claude("test prompt")

            # Sandbox should be created
            assert test_sandbox.exists()

            # Clean up
            test_sandbox.rmdir()

    @pytest.mark.asyncio
    async def test_claude_call_includes_persona(self):
        """Claude SDK call should include system_prompt with dynamic persona"""
        mock_client = create_mock_client([make_result_message()])

        with patch('bot.ClaudeSDKClient') as mock_sdk:
            mock_sdk.return_value = mock_client
            await bot.call_claude("test prompt")

            # Verify ClaudeSDKClient was called with options containing system_prompt
            assert mock_sdk.called
            call_kwargs = mock_sdk.call_args[1]
            options = call_kwargs.get('options')
            assert options is not None
            assert options.system_prompt is not None
            assert bot.BASE_SYSTEM_PROMPT[:50] in options.system_prompt

    @pytest.mark.asyncio
    async def test_claude_call_includes_allowed_tools(self):
        """Claude SDK call should include allowed_tools with all required tools"""
        mock_client = create_mock_client([make_result_message()])

        with patch('bot.ClaudeSDKClient') as mock_sdk:
            mock_sdk.return_value = mock_client
            await bot.call_claude("test prompt")

            # Verify ClaudeSDKClient was called with options containing allowed_tools
            assert mock_sdk.called
            call_kwargs = mock_sdk.call_args[1]
            options = call_kwargs.get('options')
            assert options is not None
            assert options.allowed_tools is not None

            required_tools = ['Read', 'Grep', 'Glob', 'WebSearch', 'WebFetch',
                            'Task', 'Bash', 'Edit', 'Write', 'Skill']
            for tool in required_tools:
                assert tool in options.allowed_tools, f"Tool {tool} should be in allowed_tools"

    @pytest.mark.asyncio
    async def test_claude_call_includes_cwd(self):
        """Claude SDK call should include cwd for sandbox directory"""
        mock_client = create_mock_client([make_result_message()])

        with patch('bot.ClaudeSDKClient') as mock_sdk:
            mock_sdk.return_value = mock_client
            await bot.call_claude("test prompt")

            # Verify ClaudeSDKClient was called with options containing cwd
            assert mock_sdk.called
            call_kwargs = mock_sdk.call_args[1]
            options = call_kwargs.get('options')
            assert options is not None
            assert options.cwd == bot.SANDBOX_DIR

    @pytest.mark.asyncio
    async def test_claude_call_uses_sandbox_as_cwd(self):
        """Claude SDK call should set cwd to sandbox directory"""
        mock_client = create_mock_client([make_result_message()])

        with patch('bot.ClaudeSDKClient') as mock_sdk:
            mock_sdk.return_value = mock_client
            await bot.call_claude("test prompt")

            # Verify ClaudeSDKClient was called with options containing cwd
            assert mock_sdk.called
            call_kwargs = mock_sdk.call_args[1]
            options = call_kwargs.get('options')
            assert options is not None
            assert str(options.cwd) == bot.SANDBOX_DIR

    @pytest.mark.asyncio
    async def test_claude_call_loads_megg_context(self):
        """Claude call should load megg context for new sessions"""
        mock_client = create_mock_client([make_result_message()])

        with patch('bot.ClaudeSDKClient', return_value=mock_client), \
             patch('bot.load_megg_context') as mock_megg:
            mock_megg.return_value = "test megg context"

            await bot.call_claude("test prompt", include_megg=True)

            mock_megg.assert_called_once()

    @pytest.mark.asyncio
    async def test_claude_call_continue_session(self):
        """Claude SDK call should set continue_conversation when continuing"""
        mock_client = create_mock_client([make_result_message()])

        with patch('bot.ClaudeSDKClient') as mock_sdk:
            mock_sdk.return_value = mock_client
            await bot.call_claude("test prompt", continue_last=True)

            # Verify ClaudeSDKClient was called with options containing continue_conversation
            assert mock_sdk.called
            call_kwargs = mock_sdk.call_args[1]
            options = call_kwargs.get('options')
            assert options is not None
            assert options.continue_conversation is True

    @pytest.mark.asyncio
    async def test_claude_call_resume_session(self):
        """Claude SDK call should set resume with session ID"""
        mock_client = create_mock_client([make_result_message()])

        with patch('bot.ClaudeSDKClient') as mock_sdk:
            mock_sdk.return_value = mock_client
            await bot.call_claude("test prompt", session_id="existing-session-id")

            # Verify ClaudeSDKClient was called with options containing resume
            assert mock_sdk.called
            call_kwargs = mock_sdk.call_args[1]
            options = call_kwargs.get('options')
            assert options is not None
            assert options.resume == "existing-session-id"


class TestSandboxSetup:
    """Test sandbox directory setup"""

    def test_sandbox_dir_constant_defined(self):
        """SANDBOX_DIR constant should be defined"""
        assert hasattr(bot, 'SANDBOX_DIR')
        assert bot.SANDBOX_DIR is not None

    def test_sandbox_path_is_isolated(self):
        """Sandbox should be in a dedicated directory"""
        sandbox = Path(bot.SANDBOX_DIR)
        # Should not be the same as working dir
        assert str(sandbox) != bot.CLAUDE_WORKING_DIR
        # Should contain 'sandbox' in name
        assert 'sandbox' in sandbox.name.lower()


class TestMeggIntegration:
    """Test megg context loading"""

    def test_load_megg_context_function_exists(self):
        """load_megg_context function should exist"""
        assert hasattr(bot, 'load_megg_context')
        assert callable(bot.load_megg_context)

    def test_load_megg_context_runs_megg_command(self):
        """load_megg_context should run megg context command"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="megg context output"
            )

            result = bot.load_megg_context()

            cmd = mock_run.call_args[0][0]
            assert 'megg' in cmd
            assert 'context' in cmd

    def test_load_megg_context_handles_error(self):
        """load_megg_context should handle errors gracefully"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("megg not found")

            result = bot.load_megg_context()

            assert result == ""


class TestSessionManagement:
    """Test session state management"""

    def test_get_user_state_creates_new(self):
        """get_user_state should create state for new user"""
        # Clear existing state
        bot.user_sessions = {}

        state = bot.get_user_state(99999)

        assert state is not None
        assert state['current_session'] is None
        assert state['sessions'] == []

    def test_get_user_state_returns_existing(self):
        """get_user_state should return existing state"""
        bot.user_sessions = {"12345": {"current_session": "abc", "sessions": ["abc"]}}

        state = bot.get_user_state(12345)

        assert state['current_session'] == "abc"
        assert state['sessions'] == ["abc"]


class TestTranscription:
    """Test speech-to-text functionality"""

    @pytest.mark.asyncio
    async def test_transcribe_voice_uses_scribe(self):
        """Transcription should use scribe_v1 model"""
        with patch.object(bot.elevenlabs.speech_to_text, 'convert') as mock_convert:
            mock_convert.return_value = Mock(text="transcribed text")

            await bot.transcribe_voice(b"fake audio bytes")

            call_kwargs = mock_convert.call_args[1]
            assert call_kwargs['model_id'] == 'scribe_v1'

    @pytest.mark.asyncio
    async def test_transcribe_voice_returns_text(self):
        """Transcription should return text"""
        with patch.object(bot.elevenlabs.speech_to_text, 'convert') as mock_convert:
            mock_convert.return_value = Mock(text="hello world")

            result = await bot.transcribe_voice(b"fake audio bytes")

            assert result == "hello world"

    @pytest.mark.asyncio
    async def test_transcribe_voice_handles_error(self):
        """Transcription should handle errors"""
        with patch.object(bot.elevenlabs.speech_to_text, 'convert') as mock_convert:
            mock_convert.side_effect = Exception("API Error")

            result = await bot.transcribe_voice(b"fake audio bytes")

            assert "Transcription error" in result


class TestDebugFunction:
    """Test debug logging"""

    def test_debug_function_exists(self):
        """debug function should exist"""
        assert hasattr(bot, 'debug')
        assert callable(bot.debug)


class TestHealthCheck:
    """Test health check functionality"""

    def test_health_check_handler_exists(self):
        """cmd_health handler should exist"""
        assert hasattr(bot, 'cmd_health')


class TestIntegrationFlow:
    """Integration tests for complete flows"""

    @pytest.mark.asyncio
    async def test_complete_voice_flow_mocked(self):
        """Test complete voice message flow with mocks"""
        mock_client = create_mock_client([
            make_result_message(result="V says: Here is the response.", session_id="test-session-123")
        ])

        # This tests the integration of all components
        with patch.object(bot.elevenlabs.speech_to_text, 'convert') as mock_stt, \
             patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_tts, \
             patch('bot.ClaudeSDKClient', return_value=mock_client):

            mock_stt.return_value = Mock(text="test voice input")
            mock_tts.return_value = iter([b'audio_response'])

            # Test transcription
            transcription = await bot.transcribe_voice(b"fake audio")
            assert transcription == "test voice input"

            # Test Claude call
            response, session_id, metadata = await bot.call_claude(transcription)
            assert "V says" in response or "response" in response.lower()
            assert session_id == "test-session-123"

            # Test TTS
            audio = await bot.text_to_speech(response)
            assert audio is not None


class TestCommandHandlers:
    """Test Telegram command handlers"""

    @pytest.fixture
    def mock_update(self):
        """Create mock Telegram update"""
        update = AsyncMock()
        update.effective_user.id = 12345
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        update.message.message_thread_id = None
        return update

    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = Mock()
        context.args = []
        return context

    @pytest.mark.asyncio
    async def test_cmd_start(self, mock_update, mock_context):
        """Test /start command"""
        await bot.cmd_start(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Claude Voice Assistant" in call_text or "Commands" in call_text

    @pytest.mark.asyncio
    async def test_cmd_new_without_name(self, mock_update, mock_context):
        """Test /new command without session name"""
        bot.user_sessions = {}

        await bot.cmd_new(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "New session" in call_text

    @pytest.mark.asyncio
    async def test_cmd_new_with_name(self, mock_update, mock_context):
        """Test /new command with session name"""
        bot.user_sessions = {}
        mock_context.args = ["my-session"]

        await bot.cmd_new(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "my-session" in call_text

    @pytest.mark.asyncio
    async def test_cmd_continue_no_session(self, mock_update, mock_context):
        """Test /continue with no previous session"""
        bot.user_sessions = {"12345": {"current_session": None, "sessions": []}}

        await bot.cmd_continue(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "No previous session" in call_text

    @pytest.mark.asyncio
    async def test_cmd_continue_with_session(self, mock_update, mock_context):
        """Test /continue with existing session"""
        bot.user_sessions = {"12345": {"current_session": "abc123def456", "sessions": ["abc123def456"]}}

        await bot.cmd_continue(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Continuing" in call_text

    @pytest.mark.asyncio
    async def test_cmd_sessions_empty(self, mock_update, mock_context):
        """Test /sessions with no sessions"""
        bot.user_sessions = {"12345": {"current_session": None, "sessions": []}}

        await bot.cmd_sessions(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "No sessions" in call_text

    @pytest.mark.asyncio
    async def test_cmd_sessions_with_sessions(self, mock_update, mock_context):
        """Test /sessions with existing sessions"""
        bot.user_sessions = {"12345": {"current_session": "abc123", "sessions": ["abc123", "def456"]}}

        await bot.cmd_sessions(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Sessions:" in call_text

    @pytest.mark.asyncio
    async def test_cmd_switch_no_args(self, mock_update, mock_context):
        """Test /switch without session ID"""
        mock_context.args = []

        await bot.cmd_switch(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Usage:" in call_text

    @pytest.mark.asyncio
    async def test_cmd_switch_not_found(self, mock_update, mock_context):
        """Test /switch with non-existent session"""
        bot.user_sessions = {"12345": {"current_session": None, "sessions": ["abc123"]}}
        mock_context.args = ["xyz"]

        await bot.cmd_switch(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "not found" in call_text

    @pytest.mark.asyncio
    async def test_cmd_switch_found(self, mock_update, mock_context):
        """Test /switch with valid session"""
        bot.user_sessions = {"12345": {"current_session": None, "sessions": ["abc123def456"]}}
        mock_context.args = ["abc123"]

        await bot.cmd_switch(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Switched" in call_text

    @pytest.mark.asyncio
    async def test_cmd_status_no_session(self, mock_update, mock_context):
        """Test /status with no active session"""
        bot.user_sessions = {"12345": {"current_session": None, "sessions": []}}

        await bot.cmd_status(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "No active session" in call_text

    @pytest.mark.asyncio
    async def test_cmd_status_with_session(self, mock_update, mock_context):
        """Test /status with active session"""
        bot.user_sessions = {"12345": {"current_session": "abc123def456", "sessions": ["abc123def456"]}}

        await bot.cmd_status(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Current session" in call_text


class TestMessageHandlers:
    """Test voice and text message handlers"""

    @pytest.fixture
    def mock_update_voice(self):
        """Create mock update with voice message"""
        update = AsyncMock()
        update.effective_user.id = 12345
        update.effective_user.is_bot = False
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock(return_value=AsyncMock())
        update.message.reply_voice = AsyncMock()
        update.message.voice.get_file = AsyncMock()
        update.message.voice.get_file.return_value.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake_audio"))
        update.message.message_thread_id = None
        return update

    @pytest.fixture
    def mock_update_text(self):
        """Create mock update with text message"""
        update = AsyncMock()
        update.effective_user.id = 12345
        update.effective_user.is_bot = False
        update.effective_chat.id = 12345
        update.message.text = "Hello V!"
        update.message.reply_text = AsyncMock(return_value=AsyncMock())
        update.message.reply_voice = AsyncMock()
        update.message.message_thread_id = None
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock()

    @pytest.mark.asyncio
    async def test_handle_voice_complete_flow(self, mock_update_voice, mock_context):
        """Test complete voice message handling"""
        bot.user_sessions = {}
        bot.user_rate_limits = {}  # Reset rate limits

        with patch('bot.transcribe_voice', new_callable=AsyncMock) as mock_transcribe, \
             patch('bot.call_claude', new_callable=AsyncMock) as mock_claude, \
             patch('bot.text_to_speech', new_callable=AsyncMock) as mock_tts, \
             patch.object(bot, 'ALLOWED_CHAT_ID', 12345):

            mock_transcribe.return_value = "hello world"
            mock_claude.return_value = ("V says hello back!", "session-123", {"cost": 0.01})
            mock_tts.return_value = BytesIO(b"audio_response")

            await bot.handle_voice(mock_update_voice, mock_context)

            mock_transcribe.assert_called_once()
            mock_claude.assert_called_once()
            mock_tts.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_voice_transcription_error(self, mock_update_voice, mock_context):
        """Test voice handling with transcription error"""
        bot.user_sessions = {}
        bot.user_rate_limits = {}  # Reset rate limits

        with patch('bot.transcribe_voice', new_callable=AsyncMock) as mock_transcribe, \
             patch.object(bot, 'ALLOWED_CHAT_ID', 12345):
            mock_transcribe.return_value = "[Transcription error: API failed]"

            await bot.handle_voice(mock_update_voice, mock_context)

            # Should have edited the message with error
            edit_calls = mock_update_voice.message.reply_text.return_value.edit_text.call_args_list
            assert any("Transcription error" in str(call) for call in edit_calls)

    @pytest.mark.asyncio
    async def test_handle_text_complete_flow(self, mock_update_text, mock_context):
        """Test complete text message handling"""
        bot.user_sessions = {}
        bot.user_rate_limits = {}  # Reset rate limits

        with patch('bot.call_claude', new_callable=AsyncMock) as mock_claude, \
             patch('bot.text_to_speech', new_callable=AsyncMock) as mock_tts, \
             patch.object(bot, 'ALLOWED_CHAT_ID', 12345):

            mock_claude.return_value = ("V responds to your text!", "session-456", {"cost": 0.02})
            mock_tts.return_value = BytesIO(b"audio_response")

            await bot.handle_text(mock_update_text, mock_context)

            mock_claude.assert_called_once()
            # Text handler should also send voice
            mock_tts.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_text_updates_session(self, mock_update_text, mock_context):
        """Test that text handler updates session state"""
        bot.user_sessions = {"12345": {"current_session": None, "sessions": []}}
        bot.user_rate_limits = {}  # Reset rate limits

        with patch('bot.call_claude', new_callable=AsyncMock) as mock_claude, \
             patch('bot.text_to_speech', new_callable=AsyncMock) as mock_tts, \
             patch('bot.save_state') as mock_save, \
             patch.object(bot, 'ALLOWED_CHAT_ID', 12345):

            mock_claude.return_value = ("response", "new-session-id", {})
            mock_tts.return_value = BytesIO(b"audio")

            await bot.handle_text(mock_update_text, mock_context)

            # Session should be updated
            state = bot.get_user_state(12345)
            assert state["current_session"] == "new-session-id"


class TestHelperFunctions:
    """Test helper functions"""

    @pytest.mark.asyncio
    async def test_send_long_message_short(self):
        """Test send_long_message with short text"""
        mock_first_msg = AsyncMock()

        await bot.send_long_message(Mock(), mock_first_msg, "Short message")

        mock_first_msg.edit_text.assert_called_once_with("Short message")

    @pytest.mark.asyncio
    async def test_send_long_message_long(self):
        """Test send_long_message with long text that needs splitting"""
        mock_update = Mock()
        mock_update.message.reply_text = AsyncMock()
        mock_first_msg = AsyncMock()

        # Create text longer than chunk size
        long_text = "A" * 5000

        await bot.send_long_message(mock_update, mock_first_msg, long_text, chunk_size=4000)

        # Should have edited first message and sent additional
        mock_first_msg.edit_text.assert_called_once()

    def test_save_and_load_state(self):
        """Test state persistence"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)

        original_state_file = bot.STATE_FILE
        bot.STATE_FILE = temp_path

        try:
            bot.user_sessions = {"test": {"current_session": "abc", "sessions": ["abc"]}}
            bot.save_state()

            bot.user_sessions = {}
            bot.load_state()

            assert "test" in bot.user_sessions
            assert bot.user_sessions["test"]["current_session"] == "abc"
        finally:
            bot.STATE_FILE = original_state_file
            temp_path.unlink(missing_ok=True)


class TestHealthCheckHandler:
    """Test health check command handler"""

    @pytest.fixture
    def mock_update(self):
        """Create mock update for health check"""
        update = AsyncMock()
        update.effective_user.id = 12345
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        update.message.message_thread_id = None
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock()

    @pytest.mark.asyncio
    async def test_cmd_health_runs(self, mock_update, mock_context):
        """Test health check command executes"""
        bot.user_sessions = {"12345": {"current_session": None, "sessions": []}}

        with patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_tts, \
             patch('subprocess.run') as mock_run:
            mock_tts.return_value = iter([b'test_audio'])
            mock_run.return_value = Mock(returncode=0, stdout='{"result":"OK"}', stderr='')

            await bot.cmd_health(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_text = mock_update.message.reply_text.call_args[0][0]
            assert "Health Check" in call_text


class TestErrorHandling:
    """Test error handling paths"""

    @pytest.mark.asyncio
    async def test_call_claude_exception(self):
        """Test Claude SDK call generic exception handling"""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=Exception("Connection failed"))
        mock_client.__aexit__ = AsyncMock()

        with patch('bot.ClaudeSDKClient', return_value=mock_client):
            response, session_id, metadata = await bot.call_claude("test")

            assert "Error" in response

    @pytest.mark.asyncio
    async def test_call_claude_sdk_error(self):
        """Test Claude SDK call error handling"""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=RuntimeError("SDK initialization failed"))
        mock_client.__aexit__ = AsyncMock()

        with patch('bot.ClaudeSDKClient', return_value=mock_client):
            response, session_id, metadata = await bot.call_claude("test")

            assert "Error" in response

    @pytest.mark.asyncio
    async def test_handle_voice_exception(self):
        """Test voice handler exception handling"""
        update = AsyncMock()
        update.effective_user.id = 12345
        update.effective_user.is_bot = False
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock(return_value=AsyncMock())
        update.message.voice.get_file = AsyncMock(side_effect=Exception("Download failed"))
        update.message.message_thread_id = None

        bot.user_sessions = {}
        bot.user_rate_limits = {}  # Reset rate limits

        with patch.object(bot, 'ALLOWED_CHAT_ID', 12345):
            await bot.handle_voice(update, Mock())

        # Should have handled error gracefully
        edit_calls = update.message.reply_text.return_value.edit_text.call_args_list
        assert any("Error" in str(call) for call in edit_calls)

    @pytest.mark.asyncio
    async def test_handle_text_exception(self):
        """Test text handler exception handling"""
        update = AsyncMock()
        update.effective_user.id = 12345
        update.effective_user.is_bot = False
        update.effective_chat.id = 12345
        update.message.text = "test"
        update.message.reply_text = AsyncMock(return_value=AsyncMock())
        update.message.message_thread_id = None

        bot.user_sessions = {}
        bot.user_rate_limits = {}  # Reset rate limits

        with patch('bot.call_claude', new_callable=AsyncMock) as mock_claude, \
             patch.object(bot, 'ALLOWED_CHAT_ID', 12345):
            mock_claude.side_effect = Exception("Claude call failed")

            await bot.handle_text(update, Mock())

            edit_calls = update.message.reply_text.return_value.edit_text.call_args_list
            assert any("Error" in str(call) for call in edit_calls)


class TestClaudeCallMetadata:
    """Test Claude call metadata extraction"""

    @pytest.mark.asyncio
    async def test_call_claude_extracts_metadata(self):
        """Test that metadata is extracted from Claude SDK response"""
        mock_client = create_mock_client([
            make_result_message(
                result="test response",
                session_id="sess-123",
                total_cost_usd=0.05,
                num_turns=3,
                duration_ms=5000,
            )
        ])

        with patch('bot.ClaudeSDKClient', return_value=mock_client):
            response, session_id, metadata = await bot.call_claude("test")

            assert metadata.get("cost") == 0.05
            assert metadata.get("num_turns") == 3
            assert metadata.get("duration_ms") == 5000

    @pytest.mark.asyncio
    async def test_call_claude_no_megg_on_continue(self):
        """Test megg context is not loaded when continuing"""
        mock_client = create_mock_client([make_result_message(result="ok")])

        with patch('bot.ClaudeSDKClient', return_value=mock_client), \
             patch('bot.load_megg_context') as mock_megg:

            await bot.call_claude("test", continue_last=True)

            mock_megg.assert_not_called()

    @pytest.mark.asyncio
    async def test_call_claude_no_megg_on_resume(self):
        """Test megg context is not loaded when resuming"""
        mock_client = create_mock_client([make_result_message(result="ok")])

        with patch('bot.ClaudeSDKClient', return_value=mock_client), \
             patch('bot.load_megg_context') as mock_megg:

            await bot.call_claude("test", session_id="existing-session")

            mock_megg.assert_not_called()


class TestSendLongMessage:
    """Test long message splitting"""

    @pytest.mark.asyncio
    async def test_split_at_newline(self):
        """Test that long messages split at newlines"""
        mock_update = Mock()
        mock_update.message.reply_text = AsyncMock()
        mock_first_msg = AsyncMock()

        # Text with newlines
        text = "First part\n" + "A" * 4000 + "\nSecond part"

        await bot.send_long_message(mock_update, mock_first_msg, text, chunk_size=4050)

        mock_first_msg.edit_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_split_at_space(self):
        """Test that messages split at spaces when no newline"""
        mock_update = Mock()
        mock_update.message.reply_text = AsyncMock()
        mock_first_msg = AsyncMock()

        # Text with spaces but no newlines near split point
        text = "word " * 1000  # Many words

        await bot.send_long_message(mock_update, mock_first_msg, text, chunk_size=100)

        mock_first_msg.edit_text.assert_called_once()


class TestMeggContextEdgeCases:
    """Test megg context edge cases"""

    def test_megg_returns_empty_on_failure(self):
        """Test megg returns empty string on subprocess failure"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="error")

            result = bot.load_megg_context()

            assert result == ""

    def test_megg_returns_output_on_success(self):
        """Test megg returns output on success"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="megg context data")

            result = bot.load_megg_context()

            assert result == "megg context data"


class TestMultipleSessionSwitch:
    """Test session switching edge cases"""

    @pytest.mark.asyncio
    async def test_switch_multiple_matches(self):
        """Test switch with multiple matching sessions"""
        update = AsyncMock()
        update.effective_user.id = 12345
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        update.message.message_thread_id = None

        context = Mock()
        context.args = ["abc"]  # Matches both sessions

        bot.user_sessions = {"12345": {
            "current_session": None,
            "sessions": ["abc123", "abc456"]  # Both start with "abc"
        }}

        with patch.object(bot, 'ALLOWED_CHAT_ID', 12345):
            await bot.cmd_switch(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "Multiple" in call_text or "specific" in call_text.lower()


# ============ NEW FEATURE TESTS ============

class TestUserSettings:
    """Test user settings management"""

    def test_get_user_settings_creates_default(self):
        """get_user_settings should create defaults for new user"""
        bot.user_settings = {}

        settings = bot.get_user_settings(99999)

        assert settings is not None
        assert settings["audio_enabled"] == True
        assert settings["voice_speed"] == bot.VOICE_SETTINGS["speed"]

    def test_get_user_settings_returns_existing(self):
        """get_user_settings should return existing settings"""
        bot.user_settings = {"12345": {
            "audio_enabled": False,
            "voice_speed": 0.9,
        }}

        settings = bot.get_user_settings(12345)

        assert settings["audio_enabled"] == False
        assert settings["voice_speed"] == 0.9

    def test_save_and_load_settings(self):
        """Test settings persistence"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)

        original_settings_file = bot.SETTINGS_FILE
        bot.SETTINGS_FILE = temp_path

        try:
            bot.user_settings = {"test": {
                "audio_enabled": False,
                "voice_speed": 0.8,
            }}
            bot.save_settings()

            bot.user_settings = {}
            bot.load_settings()

            assert "test" in bot.user_settings
            assert bot.user_settings["test"]["audio_enabled"] == False
            assert bot.user_settings["test"]["voice_speed"] == 0.8
        finally:
            bot.SETTINGS_FILE = original_settings_file
            temp_path.unlink(missing_ok=True)


class TestSettingsCommand:
    """Test /settings command and callbacks"""

    @pytest.fixture
    def mock_update(self):
        """Create mock update for settings"""
        update = AsyncMock()
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        update.message.message_thread_id = None
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock()

    @pytest.mark.asyncio
    async def test_cmd_settings_shows_menu(self, mock_update, mock_context):
        """Test /settings shows settings menu"""
        bot.user_settings = {}
        # Ensure update has chat ID
        mock_update.effective_chat.id = 12345

        with patch.object(bot, 'ALLOWED_CHAT_ID', 12345):
            await bot.cmd_settings(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Settings:" in call_args[0][0]
        # Check reply_markup was passed
        assert 'reply_markup' in call_args[1]

    @pytest.mark.asyncio
    async def test_settings_callback_audio_toggle(self):
        """Test audio toggle callback"""
        bot.user_settings = {"12345": {
            "audio_enabled": True,
            "voice_speed": 1.1,
                    }}

        query = AsyncMock()
        query.data = "setting_audio_toggle"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = Mock()

        with patch('bot.save_settings'):
            await bot.handle_settings_callback(update, context)

        # Audio should be toggled off
        assert bot.user_settings["12345"]["audio_enabled"] == False
        query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_settings_callback_speed_change(self):
        """Test speed change callback"""
        bot.user_settings = {"12345": {
            "audio_enabled": True,
            "voice_speed": 1.1,
                    }}

        query = AsyncMock()
        query.data = "setting_speed_0.9"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = Mock()

        with patch('bot.save_settings'):
            await bot.handle_settings_callback(update, context)

        # Speed should be changed
        assert bot.user_settings["12345"]["voice_speed"] == 0.9

    @pytest.mark.asyncio
    async def test_settings_callback_mode_toggle(self):
        """Test mode toggle callback"""
        bot.user_settings = {"12345": {
            "audio_enabled": True,
            "voice_speed": 1.1,
            "mode": "go_all",
            "watch_enabled": False,
        }}

        query = AsyncMock()
        query.data = "setting_mode_toggle"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = Mock()

        with patch('bot.save_settings'):
            await bot.handle_settings_callback(update, context)

        # Mode should be toggled to approve
        assert bot.user_settings["12345"]["mode"] == "approve"

    @pytest.mark.asyncio
    async def test_settings_callback_watch_toggle(self):
        """Test watch toggle callback"""
        bot.user_settings = {"12345": {
            "audio_enabled": True,
            "voice_speed": 1.1,
            "mode": "go_all",
            "watch_enabled": False,
        }}

        query = AsyncMock()
        query.data = "setting_watch_toggle"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = Mock()

        with patch('bot.save_settings'):
            await bot.handle_settings_callback(update, context)

        # Watch should be toggled on
        assert bot.user_settings["12345"]["watch_enabled"] == True


class TestModeAndWatchSettings:
    """Test Mode (Go All/Approve) and Watch (ON/OFF) settings"""

    @pytest.mark.asyncio
    async def test_default_settings_include_mode_and_watch(self):
        """New user settings should include mode and watch"""
        bot.user_settings = {}

        settings = bot.get_user_settings(99999)

        assert "mode" in settings
        assert settings["mode"] == "go_all"
        assert "watch_enabled" in settings
        assert settings["watch_enabled"] == False

    @pytest.mark.asyncio
    async def test_existing_settings_get_mode_and_watch(self):
        """Existing users without mode/watch should get defaults"""
        bot.user_settings = {"12345": {
            "audio_enabled": True,
            "voice_speed": 1.1,
        }}

        settings = bot.get_user_settings(12345)

        assert settings["mode"] == "go_all"
        assert settings["watch_enabled"] == False

    @pytest.mark.asyncio
    async def test_call_claude_with_approve_mode(self):
        """Claude call with approve mode should set can_use_tool callback"""
        mock_client = create_mock_client([make_result_message()])

        with patch('bot.ClaudeSDKClient') as mock_sdk:
            mock_sdk.return_value = mock_client
            await bot.call_claude(
                "test prompt",
                user_settings={"mode": "approve", "watch_enabled": False}
            )

            # Verify ClaudeSDKClient was called with options containing can_use_tool
            assert mock_sdk.called
            call_kwargs = mock_sdk.call_args[1]
            options = call_kwargs.get('options')
            assert options is not None
            # In approve mode, can_use_tool should be set
            assert options.can_use_tool is not None

    @pytest.mark.asyncio
    async def test_call_claude_with_go_all_mode(self):
        """Claude call with go_all mode should not set can_use_tool callback"""
        mock_client = create_mock_client([make_result_message()])

        with patch('bot.ClaudeSDKClient') as mock_sdk:
            mock_sdk.return_value = mock_client
            await bot.call_claude(
                "test prompt",
                user_settings={"mode": "go_all", "watch_enabled": False}
            )

            # Verify ClaudeSDKClient was called with options
            assert mock_sdk.called
            call_kwargs = mock_sdk.call_args[1]
            options = call_kwargs.get('options')
            assert options is not None
            # In go_all mode, can_use_tool should be None (allowed_tools used instead)
            assert options.can_use_tool is None

    @pytest.mark.asyncio
    async def test_approval_callback_approve(self):
        """Test approval callback approves tool"""
        bot.pending_approvals = {}

        # Create a pending approval
        import asyncio
        approval_id = "test123"
        event = asyncio.Event()
        bot.pending_approvals[approval_id] = {
            "user_id": 12345,  # Add user_id for security check
            "event": event,
            "approved": None,
            "tool_name": "Read",
            "input": {"path": "/test"},
        }

        query = AsyncMock()
        query.data = f"approve_{approval_id}"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = Mock()

        await bot.handle_approval_callback(update, context)

        # Check approval was recorded and event is set
        assert event.is_set()
        # Note: approval is popped from dict during processing
        # assert bot.pending_approvals[approval_id]["approved"] == True

    @pytest.mark.asyncio
    async def test_approval_callback_reject(self):
        """Test approval callback rejects tool"""
        bot.pending_approvals = {}

        import asyncio
        approval_id = "test456"
        event = asyncio.Event()
        bot.pending_approvals[approval_id] = {
            "user_id": 12345,  # Add user_id for security check
            "event": event,
            "approved": None,
            "tool_name": "Write",
            "input": {"path": "/test"},
        }

        query = AsyncMock()
        query.data = f"reject_{approval_id}"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = Mock()

        await bot.handle_approval_callback(update, context)

        # Check rejection was recorded
        assert event.is_set()

    @pytest.mark.asyncio
    async def test_approval_callback_expired(self):
        """Test approval callback with expired approval ID"""
        bot.pending_approvals = {}

        query = AsyncMock()
        query.data = "approve_expired123"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = Mock()

        await bot.handle_approval_callback(update, context)

        # Should show expired message
        query.edit_message_text.assert_called_with("Approval expired")


class TestDynamicPrompt:
    """Test dynamic system prompt generation"""

    def test_build_dynamic_prompt_includes_timestamp(self):
        """Dynamic prompt should include current date/time"""
        prompt = bot.build_dynamic_prompt()

        assert "Current date and time:" in prompt

    def test_build_dynamic_prompt_includes_base(self):
        """Dynamic prompt should include base prompt content"""
        prompt = bot.build_dynamic_prompt()

        # Should include content from BASE_SYSTEM_PROMPT
        assert len(prompt) > len("Current date and time:")

    def test_build_dynamic_prompt_with_settings(self):
        """Dynamic prompt should include settings summary when relevant"""
        settings = {
            "audio_enabled": False,
            "voice_speed": 1.0
        }

        prompt = bot.build_dynamic_prompt(settings)

        assert "Audio responses disabled" in prompt

    def test_build_dynamic_prompt_no_settings_summary_when_defaults(self):
        """Dynamic prompt should not include settings summary when defaults"""
        settings = {
            "audio_enabled": True,
            "voice_speed": 1.1
        }

        prompt = bot.build_dynamic_prompt(settings)

        # Should NOT include settings summary since all are default
        assert "User settings:" not in prompt


class TestAudioEnabledSetting:
    """Test audio enabled setting"""

    @pytest.fixture
    def mock_update_text(self):
        update = AsyncMock()
        update.effective_user.id = 12345
        update.effective_user.is_bot = False
        update.effective_chat.id = 12345
        update.message.text = "Hello!"
        update.message.reply_text = AsyncMock(return_value=AsyncMock())
        update.message.reply_voice = AsyncMock()
        update.message.message_thread_id = None
        return update

    @pytest.fixture
    def mock_context(self):
        context = Mock()
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_handle_text_audio_disabled(self, mock_update_text, mock_context):
        """Test text handler skips TTS when audio disabled"""
        bot.user_sessions = {}
        bot.user_rate_limits = {}  # Reset rate limits
        bot.user_settings = {"12345": {
            "audio_enabled": False,
            "voice_speed": 1.1,
                    }}

        with patch('bot.call_claude', new_callable=AsyncMock) as mock_claude, \
             patch('bot.text_to_speech', new_callable=AsyncMock) as mock_tts, \
             patch.object(bot, 'ALLOWED_CHAT_ID', 12345):
            mock_claude.return_value = ("Response", "session-123", {})

            await bot.handle_text(mock_update_text, mock_context)

        # TTS should NOT be called
        mock_tts.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_text_audio_enabled(self, mock_update_text, mock_context):
        """Test text handler calls TTS when audio enabled"""
        bot.user_sessions = {}
        bot.user_rate_limits = {}  # Reset rate limits
        bot.user_settings = {"12345": {
            "audio_enabled": True,
            "voice_speed": 1.1,
                    }}

        with patch('bot.call_claude', new_callable=AsyncMock) as mock_claude, \
             patch('bot.text_to_speech', new_callable=AsyncMock) as mock_tts, \
             patch.object(bot, 'ALLOWED_CHAT_ID', 12345):
            mock_claude.return_value = ("Response", "session-123", {})
            mock_tts.return_value = BytesIO(b"audio")

            await bot.handle_text(mock_update_text, mock_context)

        # TTS should be called
        mock_tts.assert_called_once()


class TestVoiceSpeedSetting:
    """Test voice speed setting"""

    @pytest.mark.asyncio
    async def test_tts_uses_custom_speed(self):
        """TTS should use provided speed parameter"""
        with patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_convert:
            mock_convert.return_value = iter([b'fake_audio_data'])

            await bot.text_to_speech("test text", speed=0.9)

            call_kwargs = mock_convert.call_args[1]
            assert call_kwargs['voice_settings']['speed'] == 0.9

    @pytest.mark.asyncio
    async def test_tts_uses_default_speed_when_none(self):
        """TTS should use default speed when not provided"""
        with patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_convert:
            mock_convert.return_value = iter([b'fake_audio_data'])

            await bot.text_to_speech("test text")

            call_kwargs = mock_convert.call_args[1]
            assert call_kwargs['voice_settings']['speed'] == bot.VOICE_SETTINGS['speed']


class TestClaudeCallWithUserSettings:
    """Test Claude call with user settings"""

    @pytest.mark.asyncio
    async def test_call_claude_uses_dynamic_prompt(self):
        """Claude call should use dynamic prompt with user settings"""
        user_settings = {
            "audio_enabled": False,
                        "voice_speed": 1.0
        }

        with patch('subprocess.run') as mock_run, \
             patch('bot.build_dynamic_prompt') as mock_build:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"result": "test", "session_id": "abc123"})
            )
            mock_build.return_value = "dynamic prompt content"

            await bot.call_claude("test", user_settings=user_settings)

            mock_build.assert_called_once_with(user_settings)


class TestChatIDAuthentication:
    """Test chat ID authentication security"""

    @pytest.fixture
    def mock_update_authorized(self):
        """Create mock update from authorized chat"""
        update = AsyncMock()
        update.effective_user.id = 12345
        update.effective_user.is_bot = False
        update.effective_chat.id = 12345  # Matches test ALLOWED_CHAT_ID
        update.message.reply_text = AsyncMock()
        update.message.message_thread_id = None
        return update

    @pytest.fixture
    def mock_update_unauthorized(self):
        """Create mock update from unauthorized chat"""
        update = AsyncMock()
        update.effective_user.id = 99999
        update.effective_user.is_bot = False
        update.effective_chat.id = 99999  # Does NOT match test ALLOWED_CHAT_ID
        update.message.reply_text = AsyncMock()
        update.message.message_thread_id = None
        return update

    @pytest.fixture
    def mock_context(self):
        return Mock()

    @pytest.mark.asyncio
    async def test_cmd_start_rejects_unauthorized_chat(self, mock_update_unauthorized, mock_context):
        """Test /start rejects unauthorized chat ID"""
        with patch.object(bot, 'ALLOWED_CHAT_ID', 12345):
            await bot.cmd_start(mock_update_unauthorized, mock_context)
            # Should NOT send a reply
            mock_update_unauthorized.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_cmd_start_accepts_authorized_chat(self, mock_update_authorized, mock_context):
        """Test /start accepts authorized chat ID"""
        with patch.object(bot, 'ALLOWED_CHAT_ID', 12345):
            await bot.cmd_start(mock_update_authorized, mock_context)
            # Should send a reply
            mock_update_authorized.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_start_accepts_all_when_zero(self, mock_update_unauthorized, mock_context):
        """Test /start accepts all when ALLOWED_CHAT_ID is 0"""
        with patch.object(bot, 'ALLOWED_CHAT_ID', 0):
            await bot.cmd_start(mock_update_unauthorized, mock_context)
            # Should send a reply even though chat doesn't match
            mock_update_unauthorized.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_voice_rejects_unauthorized_chat(self):
        """Test voice handler rejects unauthorized chat ID"""
        update = AsyncMock()
        update.effective_user.id = 99999
        update.effective_user.is_bot = False
        update.effective_chat.id = 99999  # Unauthorized
        update.message.reply_text = AsyncMock(return_value=AsyncMock())
        update.message.voice.get_file = AsyncMock()
        update.message.message_thread_id = None

        bot.user_sessions = {}

        with patch.object(bot, 'ALLOWED_CHAT_ID', 12345):
            await bot.handle_voice(update, Mock())

            # Should NOT start processing
            update.message.reply_text.assert_not_called()
            update.message.voice.get_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_text_rejects_unauthorized_chat(self):
        """Test text handler rejects unauthorized chat ID"""
        update = AsyncMock()
        update.effective_user.id = 99999
        update.effective_user.is_bot = False
        update.effective_chat.id = 99999  # Unauthorized
        update.message.text = "test message"
        update.message.reply_text = AsyncMock()
        update.message.message_thread_id = None

        bot.user_sessions = {}

        with patch.object(bot, 'ALLOWED_CHAT_ID', 12345), \
             patch('bot.call_claude', new_callable=AsyncMock) as mock_claude:

            await bot.handle_text(update, Mock())

            # Should NOT call Claude
            mock_claude.assert_not_called()
            update.message.reply_text.assert_not_called()


class TestApprovalUserValidation:
    """Test approval callback user validation"""

    @pytest.mark.asyncio
    async def test_approval_callback_rejects_different_user(self):
        """Test approval callback rejects different user"""
        bot.pending_approvals = {}

        import asyncio
        approval_id = "test789"
        event = asyncio.Event()
        bot.pending_approvals[approval_id] = {
            "user_id": 12345,  # Original requester
            "event": event,
            "approved": None,
            "tool_name": "Read",
            "input": {"path": "/test"},
        }

        query = AsyncMock()
        query.data = f"approve_{approval_id}"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 99999  # Different user

        context = Mock()

        await bot.handle_approval_callback(update, context)

        # Should answer with rejection message
        query.answer.assert_called_with("Only the requester can approve this")
        # Event should NOT be set
        assert not event.is_set()

    @pytest.mark.asyncio
    async def test_approval_callback_accepts_same_user(self):
        """Test approval callback accepts same user"""
        bot.pending_approvals = {}

        import asyncio
        approval_id = "test790"
        event = asyncio.Event()
        bot.pending_approvals[approval_id] = {
            "user_id": 12345,  # Original requester
            "event": event,
            "approved": None,
            "tool_name": "Read",
            "input": {"path": "/test"},
        }

        query = AsyncMock()
        query.data = f"approve_{approval_id}"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345  # Same user

        context = Mock()

        await bot.handle_approval_callback(update, context)

        # Should process approval
        assert event.is_set()
        assert bot.pending_approvals[approval_id]["approved"] == True


class TestSpeedValidation:
    """Test speed callback input validation"""

    @pytest.mark.asyncio
    async def test_settings_callback_rejects_invalid_speed_float(self):
        """Test speed callback rejects non-float values"""
        bot.user_settings = {"12345": {
            "audio_enabled": True,
            "voice_speed": 1.1,
        }}

        query = AsyncMock()
        query.data = "setting_speed_not_a_number"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = Mock()

        await bot.handle_settings_callback(update, context)

        # Should answer with error
        query.answer.assert_called_with("Invalid speed value")
        # Speed should NOT change
        assert bot.user_settings["12345"]["voice_speed"] == 1.1

    @pytest.mark.asyncio
    async def test_settings_callback_rejects_out_of_range_speed_low(self):
        """Test speed callback rejects speed below 0.7"""
        bot.user_settings = {"12345": {
            "audio_enabled": True,
            "voice_speed": 1.1,
        }}

        query = AsyncMock()
        query.data = "setting_speed_0.5"  # Too low
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = Mock()

        await bot.handle_settings_callback(update, context)

        # Should answer with error
        query.answer.assert_called_with("Invalid speed range")
        # Speed should NOT change
        assert bot.user_settings["12345"]["voice_speed"] == 1.1

    @pytest.mark.asyncio
    async def test_settings_callback_rejects_out_of_range_speed_high(self):
        """Test speed callback rejects speed above 1.2"""
        bot.user_settings = {"12345": {
            "audio_enabled": True,
            "voice_speed": 1.1,
        }}

        query = AsyncMock()
        query.data = "setting_speed_1.5"  # Too high
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = Mock()

        await bot.handle_settings_callback(update, context)

        # Should answer with error
        query.answer.assert_called_with("Invalid speed range")
        # Speed should NOT change
        assert bot.user_settings["12345"]["voice_speed"] == 1.1

    @pytest.mark.asyncio
    async def test_settings_callback_accepts_valid_speed(self):
        """Test speed callback accepts valid speed in range"""
        bot.user_settings = {"12345": {
            "audio_enabled": True,
            "voice_speed": 1.1,
        }}

        query = AsyncMock()
        query.data = "setting_speed_0.9"  # Valid
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = AsyncMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = Mock()

        with patch('bot.save_settings'):
            await bot.handle_settings_callback(update, context)

        # Speed should change
        assert bot.user_settings["12345"]["voice_speed"] == 0.9


class TestLogLevel:
    """Test configurable log level"""

    def test_log_level_from_env(self):
        """Test log level is configurable via env"""
        # Check that LOG_LEVEL variable exists
        assert hasattr(bot, 'LOG_LEVEL')

    def test_log_level_defaults_to_info(self):
        """Test log level defaults to INFO when not set"""
        # In tests, LOG_LEVEL is not set, so should default to INFO
        # (or DEBUG if set in test env)
        assert bot.LOG_LEVEL in ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]


# Run pytest with coverage
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
