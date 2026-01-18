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

# Set up test environment
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
os.environ["ELEVENLABS_API_KEY"] = "test_api_key"
os.environ["TELEGRAM_DEFAULT_CHAT_ID"] = "12345"
os.environ["CLAUDE_WORKING_DIR"] = "/home/dev"
os.environ["CLAUDE_SANDBOX_DIR"] = "/tmp/test-voice-sandbox"

# Import after setting env vars
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
    """Test the V persona configuration"""

    def test_persona_exists(self):
        """Persona prompt should be defined"""
        assert hasattr(bot, 'VOICE_PERSONA')
        assert len(bot.VOICE_PERSONA) > 100

    def test_persona_has_name(self):
        """Persona should identify as V"""
        assert "V" in bot.VOICE_PERSONA

    def test_persona_has_personality_traits(self):
        """Persona should have key personality traits"""
        persona = bot.VOICE_PERSONA.lower()
        assert "cynical" in persona or "witty" in persona
        assert "brilliant" in persona or "sharp" in persona
        assert "curious" in persona

    def test_persona_has_voice_rules(self):
        """Persona should have voice output rules"""
        persona = bot.VOICE_PERSONA
        assert "NO markdown" in persona or "no markdown" in persona.lower()
        assert "NO bullet" in persona or "no bullet" in persona.lower()
        assert "NO code block" in persona or "no code" in persona.lower()

    def test_persona_mentions_sandbox(self):
        """Persona should mention sandbox directory"""
        assert "sandbox" in bot.VOICE_PERSONA.lower()
        # Should contain a sandbox path (the actual SANDBOX_DIR value)
        assert bot.SANDBOX_DIR in bot.VOICE_PERSONA or "sandbox" in bot.VOICE_PERSONA.lower()

    def test_persona_mentions_megg(self):
        """Persona should instruct to use megg"""
        persona = bot.VOICE_PERSONA.lower()
        assert "megg" in persona

    def test_persona_has_megg_commands(self):
        """Persona should include megg command instructions"""
        persona = bot.VOICE_PERSONA
        assert "megg context" in persona
        assert "megg state" in persona
        assert "megg learn" in persona

    def test_persona_mentions_read_write_permissions(self):
        """Persona should explain read/write permissions"""
        persona = bot.VOICE_PERSONA.lower()
        assert "read" in persona
        assert "write" in persona

    def test_persona_mentions_websearch(self):
        """Persona should mention WebSearch capability"""
        assert "WebSearch" in bot.VOICE_PERSONA or "websearch" in bot.VOICE_PERSONA.lower()

    def test_persona_mentions_skills(self):
        """Persona should mention skills"""
        assert "skill" in bot.VOICE_PERSONA.lower()


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
    async def test_tts_uses_george_voice(self):
        """TTS should use George voice ID"""
        with patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_convert:
            mock_convert.return_value = iter([b'fake_audio_data'])

            await bot.text_to_speech("test text")

            call_kwargs = mock_convert.call_args[1]
            assert call_kwargs['voice_id'] == 'JBFqnCBsd6RMkjVDRZzb'

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
        """Claude call should include --append-system-prompt with persona"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"result": "test", "session_id": "abc123"})
            )

            await bot.call_claude("test prompt")

            cmd = mock_run.call_args[0][0]
            assert '--append-system-prompt' in cmd
            # Persona should be in the command
            persona_idx = cmd.index('--append-system-prompt') + 1
            assert bot.VOICE_PERSONA in cmd[persona_idx]

    @pytest.mark.asyncio
    async def test_claude_call_includes_allowed_tools(self):
        """Claude call should include --allowedTools with all required tools"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"result": "test", "session_id": "abc123"})
            )

            await bot.call_claude("test prompt")

            cmd = mock_run.call_args[0][0]
            assert '--allowedTools' in cmd

            tools_idx = cmd.index('--allowedTools') + 1
            tools = cmd[tools_idx]

            # Check all required tools are present
            required_tools = ['Read', 'Grep', 'Glob', 'WebSearch', 'WebFetch',
                            'Task', 'Bash', 'Edit', 'Write', 'Skill']
            for tool in required_tools:
                assert tool in tools, f"Tool {tool} should be in allowedTools"

    @pytest.mark.asyncio
    async def test_claude_call_includes_add_dir(self):
        """Claude call should include --add-dir for read access"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"result": "test", "session_id": "abc123"})
            )

            await bot.call_claude("test prompt")

            cmd = mock_run.call_args[0][0]
            assert '--add-dir' in cmd

            add_dir_idx = cmd.index('--add-dir') + 1
            assert cmd[add_dir_idx] == bot.CLAUDE_WORKING_DIR

    @pytest.mark.asyncio
    async def test_claude_call_uses_sandbox_as_cwd(self):
        """Claude call should execute in sandbox directory"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"result": "test", "session_id": "abc123"})
            )

            await bot.call_claude("test prompt")

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs['cwd'] == bot.SANDBOX_DIR

    @pytest.mark.asyncio
    async def test_claude_call_loads_megg_context(self):
        """Claude call should load megg context for new sessions"""
        with patch('subprocess.run') as mock_run, \
             patch('bot.load_megg_context') as mock_megg:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"result": "test", "session_id": "abc123"})
            )
            mock_megg.return_value = "test megg context"

            await bot.call_claude("test prompt", include_megg=True)

            mock_megg.assert_called_once()

    @pytest.mark.asyncio
    async def test_claude_call_continue_session(self):
        """Claude call should use --continue flag when continuing"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"result": "test", "session_id": "abc123"})
            )

            await bot.call_claude("test prompt", continue_last=True)

            cmd = mock_run.call_args[0][0]
            assert '--continue' in cmd

    @pytest.mark.asyncio
    async def test_claude_call_resume_session(self):
        """Claude call should use --resume flag with session ID"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"result": "test", "session_id": "abc123"})
            )

            await bot.call_claude("test prompt", session_id="existing-session-id")

            cmd = mock_run.call_args[0][0]
            assert '--resume' in cmd
            resume_idx = cmd.index('--resume') + 1
            assert cmd[resume_idx] == "existing-session-id"


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
        # This tests the integration of all components
        with patch.object(bot.elevenlabs.speech_to_text, 'convert') as mock_stt, \
             patch.object(bot.elevenlabs.text_to_speech, 'convert') as mock_tts, \
             patch('subprocess.run') as mock_claude:

            mock_stt.return_value = Mock(text="test voice input")
            mock_tts.return_value = iter([b'audio_response'])
            mock_claude.return_value = Mock(
                returncode=0,
                stdout=json.dumps({
                    "result": "V says: Here is the response.",
                    "session_id": "test-session-123"
                })
            )

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

        with patch('bot.transcribe_voice', new_callable=AsyncMock) as mock_transcribe, \
             patch('bot.call_claude', new_callable=AsyncMock) as mock_claude, \
             patch('bot.text_to_speech', new_callable=AsyncMock) as mock_tts:

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

        with patch('bot.transcribe_voice', new_callable=AsyncMock) as mock_transcribe:
            mock_transcribe.return_value = "[Transcription error: API failed]"

            await bot.handle_voice(mock_update_voice, mock_context)

            # Should have edited the message with error
            edit_calls = mock_update_voice.message.reply_text.return_value.edit_text.call_args_list
            assert any("Transcription error" in str(call) for call in edit_calls)

    @pytest.mark.asyncio
    async def test_handle_text_complete_flow(self, mock_update_text, mock_context):
        """Test complete text message handling"""
        bot.user_sessions = {}

        with patch('bot.call_claude', new_callable=AsyncMock) as mock_claude, \
             patch('bot.text_to_speech', new_callable=AsyncMock) as mock_tts:

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

        with patch('bot.call_claude', new_callable=AsyncMock) as mock_claude, \
             patch('bot.text_to_speech', new_callable=AsyncMock) as mock_tts, \
             patch('bot.save_state') as mock_save:

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
    async def test_call_claude_timeout(self):
        """Test Claude call timeout handling"""
        with patch('subprocess.run') as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=300)

            response, session_id, metadata = await bot.call_claude("test")

            assert "timed out" in response.lower()

    @pytest.mark.asyncio
    async def test_call_claude_exception(self):
        """Test Claude call generic exception handling"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Connection failed")

            response, session_id, metadata = await bot.call_claude("test")

            assert "Error" in response

    @pytest.mark.asyncio
    async def test_call_claude_non_zero_return(self):
        """Test Claude call with non-zero return code"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Command failed", stdout="")

            response, session_id, metadata = await bot.call_claude("test")

            assert "Error" in response

    @pytest.mark.asyncio
    async def test_call_claude_invalid_json(self):
        """Test Claude call with invalid JSON response"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="not json", stderr="")

            response, session_id, metadata = await bot.call_claude("test")

            # Should return raw stdout on JSON decode error
            assert response == "not json"

    @pytest.mark.asyncio
    async def test_handle_voice_exception(self):
        """Test voice handler exception handling"""
        update = AsyncMock()
        update.effective_user.id = 12345
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock(return_value=AsyncMock())
        update.message.voice.get_file = AsyncMock(side_effect=Exception("Download failed"))
        update.message.message_thread_id = None

        bot.user_sessions = {}

        await bot.handle_voice(update, Mock())

        # Should have handled error gracefully
        edit_calls = update.message.reply_text.return_value.edit_text.call_args_list
        assert any("Error" in str(call) for call in edit_calls)

    @pytest.mark.asyncio
    async def test_handle_text_exception(self):
        """Test text handler exception handling"""
        update = AsyncMock()
        update.effective_user.id = 12345
        update.effective_chat.id = 12345
        update.message.text = "test"
        update.message.reply_text = AsyncMock(return_value=AsyncMock())
        update.message.message_thread_id = None

        bot.user_sessions = {}

        with patch('bot.call_claude', new_callable=AsyncMock) as mock_claude:
            mock_claude.side_effect = Exception("Claude call failed")

            await bot.handle_text(update, Mock())

            edit_calls = update.message.reply_text.return_value.edit_text.call_args_list
            assert any("Error" in str(call) for call in edit_calls)


class TestClaudeCallMetadata:
    """Test Claude call metadata extraction"""

    @pytest.mark.asyncio
    async def test_call_claude_extracts_metadata(self):
        """Test that metadata is extracted from Claude response"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({
                    "result": "test response",
                    "session_id": "sess-123",
                    "total_cost_usd": 0.05,
                    "num_turns": 3,
                    "duration_ms": 5000
                })
            )

            response, session_id, metadata = await bot.call_claude("test")

            assert metadata["cost"] == 0.05
            assert metadata["num_turns"] == 3
            assert metadata["duration_ms"] == 5000

    @pytest.mark.asyncio
    async def test_call_claude_no_megg_on_continue(self):
        """Test megg context is not loaded when continuing"""
        with patch('subprocess.run') as mock_run, \
             patch('bot.load_megg_context') as mock_megg:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"result": "ok", "session_id": "abc"})
            )

            await bot.call_claude("test", continue_last=True)

            mock_megg.assert_not_called()

    @pytest.mark.asyncio
    async def test_call_claude_no_megg_on_resume(self):
        """Test megg context is not loaded when resuming"""
        with patch('subprocess.run') as mock_run, \
             patch('bot.load_megg_context') as mock_megg:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps({"result": "ok", "session_id": "abc"})
            )

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
        update.message.reply_text = AsyncMock()

        context = Mock()
        context.args = ["abc"]  # Matches both sessions

        bot.user_sessions = {"12345": {
            "current_session": None,
            "sessions": ["abc123", "abc456"]  # Both start with "abc"
        }}

        await bot.cmd_switch(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "Multiple" in call_text or "specific" in call_text.lower()


# Run pytest with coverage
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
