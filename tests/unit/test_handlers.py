"""Tests for koro.handlers module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from koro.handlers.utils import should_handle_message, send_long_message


class TestShouldHandleMessage:
    """Tests for should_handle_message function."""

    def test_handles_all_when_no_topic_filter(self, monkeypatch):
        """Handles all messages when TOPIC_ID not set."""
        monkeypatch.setattr("koro.handlers.utils.TOPIC_ID", None)

        assert should_handle_message(None) is True
        assert should_handle_message(123) is True
        assert should_handle_message(456) is True

    def test_handles_matching_topic(self, monkeypatch):
        """Handles messages in matching topic."""
        monkeypatch.setattr("koro.handlers.utils.TOPIC_ID", "100")

        assert should_handle_message(100) is True

    def test_rejects_non_matching_topic(self, monkeypatch):
        """Rejects messages in non-matching topic."""
        monkeypatch.setattr("koro.handlers.utils.TOPIC_ID", "100")

        assert should_handle_message(200) is False

    def test_rejects_no_topic_when_filter_set(self, monkeypatch):
        """Rejects messages without topic when filter is set."""
        monkeypatch.setattr("koro.handlers.utils.TOPIC_ID", "100")

        assert should_handle_message(None) is False

    def test_handles_invalid_topic_id_config(self, monkeypatch):
        """Handles all messages when TOPIC_ID is invalid."""
        monkeypatch.setattr("koro.handlers.utils.TOPIC_ID", "not_a_number")

        assert should_handle_message(None) is True
        assert should_handle_message(123) is True


class TestSendLongMessage:
    """Tests for send_long_message function."""

    @pytest.mark.asyncio
    async def test_short_message_single_edit(self):
        """Short messages are sent as single edit."""
        update = MagicMock()
        first_msg = MagicMock()
        first_msg.edit_text = AsyncMock()

        await send_long_message(update, first_msg, "Short message")

        first_msg.edit_text.assert_called_once_with("Short message")

    @pytest.mark.asyncio
    async def test_long_message_split(self):
        """Long messages are split into chunks."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        first_msg = MagicMock()
        first_msg.edit_text = AsyncMock()

        # Message longer than chunk size
        long_text = "word " * 1000  # ~5000 chars

        await send_long_message(update, first_msg, long_text, chunk_size=2000)

        # First message edited, additional messages sent
        first_msg.edit_text.assert_called_once()
        assert update.message.reply_text.call_count >= 1

    @pytest.mark.asyncio
    async def test_chunk_includes_counter(self):
        """Chunked messages include counter."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        first_msg = MagicMock()
        first_msg.edit_text = AsyncMock()

        long_text = "x" * 5000

        await send_long_message(update, first_msg, long_text, chunk_size=2000)

        first_call_text = first_msg.edit_text.call_args[0][0]
        assert "[1/" in first_call_text


class TestCommandHandlers:
    """Tests for command handler authentication."""

    @pytest.mark.asyncio
    async def test_cmd_start_ignores_wrong_chat(self, monkeypatch):
        """cmd_start ignores unauthorized chats."""
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 12345)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_start

        update = MagicMock()
        update.effective_chat.id = 99999  # Wrong chat
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_start(update, context)

        # Should not reply to wrong chat
        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_cmd_start_responds_to_correct_chat(self, monkeypatch):
        """cmd_start responds to authorized chat."""
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 12345)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_start

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_start(update, context)

        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "Voice Assistant" in call_text

    @pytest.mark.asyncio
    async def test_cmd_start_allows_all_when_chat_id_zero(self, monkeypatch):
        """cmd_start allows all chats when ALLOWED_CHAT_ID is 0."""
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_start

        update = MagicMock()
        update.effective_chat.id = 99999
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_start(update, context)

        update.message.reply_text.assert_called_once()


class TestMoreCommandHandlers:
    """Additional tests for command handlers."""

    @pytest.mark.asyncio
    async def test_cmd_new_creates_session(self, monkeypatch):
        """cmd_new resets current session."""
        from koro.state import StateManager

        manager = StateManager()
        manager.sessions = {"12345": {"current_session": "old_session", "sessions": ["old_session"]}}
        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_new

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []

        await cmd_new(update, context)

        assert manager.sessions["12345"]["current_session"] is None
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_new_with_name(self, monkeypatch):
        """cmd_new with name shows session name."""
        from koro.state import StateManager

        manager = StateManager()
        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_new

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["my", "session"]

        await cmd_new(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "my session" in call_text

    @pytest.mark.asyncio
    async def test_cmd_continue_with_session(self, monkeypatch):
        """cmd_continue shows session info when exists."""
        from koro.state import StateManager

        manager = StateManager()
        manager.sessions = {"12345": {"current_session": "abc12345", "sessions": ["abc12345"]}}
        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_continue

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_continue(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "abc12345" in call_text

    @pytest.mark.asyncio
    async def test_cmd_continue_without_session(self, monkeypatch):
        """cmd_continue shows message when no session."""
        from koro.state import StateManager

        manager = StateManager()
        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_continue

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_continue(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "No previous session" in call_text

    @pytest.mark.asyncio
    async def test_cmd_sessions_empty(self, monkeypatch):
        """cmd_sessions shows empty message when no sessions."""
        from koro.state import StateManager

        manager = StateManager()
        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_sessions

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_sessions(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "No sessions" in call_text

    @pytest.mark.asyncio
    async def test_cmd_sessions_lists_sessions(self, monkeypatch):
        """cmd_sessions lists available sessions."""
        from koro.state import StateManager

        manager = StateManager()
        manager.sessions = {"12345": {"current_session": "sess2", "sessions": ["sess1", "sess2"]}}
        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_sessions

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_sessions(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "sess1" in call_text or "sess2" in call_text

    @pytest.mark.asyncio
    async def test_cmd_switch_no_args(self, monkeypatch):
        """cmd_switch shows usage without args."""
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_switch

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []

        await cmd_switch(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "Usage" in call_text

    @pytest.mark.asyncio
    async def test_cmd_switch_finds_session(self, monkeypatch):
        """cmd_switch switches to matching session."""
        from koro.state import StateManager

        manager = StateManager()
        manager.sessions = {"12345": {"current_session": None, "sessions": ["abc123456789"]}}
        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_switch

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["abc"]

        await cmd_switch(update, context)

        assert manager.sessions["12345"]["current_session"] == "abc123456789"

    @pytest.mark.asyncio
    async def test_cmd_switch_not_found(self, monkeypatch):
        """cmd_switch shows error when session not found."""
        from koro.state import StateManager

        manager = StateManager()
        manager.sessions = {"12345": {"current_session": None, "sessions": ["abc123"]}}
        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_switch

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["xyz"]

        await cmd_switch(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "not found" in call_text

    @pytest.mark.asyncio
    async def test_cmd_status_with_session(self, monkeypatch):
        """cmd_status shows session info."""
        from koro.state import StateManager

        manager = StateManager()
        manager.sessions = {"12345": {"current_session": "abc12345", "sessions": ["abc12345"]}}
        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_status

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_status(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "abc12345" in call_text

    @pytest.mark.asyncio
    async def test_cmd_status_no_session(self, monkeypatch):
        """cmd_status shows message when no session."""
        from koro.state import StateManager

        manager = StateManager()
        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_status

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_status(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "No active session" in call_text

    @pytest.mark.asyncio
    async def test_cmd_setup_shows_status(self, monkeypatch):
        """cmd_setup shows credentials status."""
        monkeypatch.setattr("koro.handlers.commands.load_credentials", lambda: {})
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_setup

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_setup(update, context)

        update.message.reply_text.assert_called_once()
        call_kwargs = update.message.reply_text.call_args[1]
        assert call_kwargs["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_cmd_health_checks_systems(self, monkeypatch):
        """cmd_health checks all systems."""
        from koro.state import StateManager
        from koro.voice import VoiceEngine
        from koro.claude import ClaudeClient

        manager = StateManager()
        mock_voice = MagicMock(spec=VoiceEngine)
        mock_voice.health_check.return_value = (True, "OK")
        mock_claude = MagicMock(spec=ClaudeClient)
        mock_claude.health_check.return_value = (True, "OK")

        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.get_voice_engine", lambda: mock_voice)
        monkeypatch.setattr("koro.handlers.commands.get_claude_client", lambda: mock_claude)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)
        monkeypatch.setattr("koro.handlers.commands.SANDBOX_DIR", "/tmp/sandbox")

        from koro.handlers.commands import cmd_health

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_health(update, context)

        call_text = update.message.reply_text.call_args[0][0]
        assert "Health Check" in call_text
        assert "ElevenLabs" in call_text
        assert "Claude" in call_text

    @pytest.mark.asyncio
    async def test_cmd_settings_shows_menu(self, monkeypatch):
        """cmd_settings shows settings menu."""
        from koro.state import StateManager

        manager = StateManager()
        monkeypatch.setattr("koro.handlers.commands.get_state_manager", lambda: manager)
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_settings

        update = MagicMock()
        update.effective_chat.id = 12345
        update.effective_user.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await cmd_settings(update, context)

        call_args = update.message.reply_text.call_args
        call_text = call_args[0][0]
        assert "Settings" in call_text
        assert "Mode" in call_text
        assert "Audio" in call_text

    @pytest.mark.asyncio
    async def test_cmd_claude_token_no_args(self, monkeypatch):
        """cmd_claude_token shows usage without args."""
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_claude_token

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.message_thread_id = None
        update.message.delete = AsyncMock()
        update.effective_chat.send_message = AsyncMock()

        context = MagicMock()
        context.args = []

        await cmd_claude_token(update, context)

        call_text = update.effective_chat.send_message.call_args[0][0]
        assert "Usage" in call_text

    @pytest.mark.asyncio
    async def test_cmd_claude_token_invalid_format(self, monkeypatch):
        """cmd_claude_token rejects invalid token format."""
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_claude_token

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.message_thread_id = None
        update.message.delete = AsyncMock()
        update.effective_chat.send_message = AsyncMock()

        context = MagicMock()
        context.args = ["invalid_token"]

        await cmd_claude_token(update, context)

        call_text = update.effective_chat.send_message.call_args[0][0]
        assert "Invalid" in call_text

    @pytest.mark.asyncio
    async def test_cmd_claude_token_saves_valid(self, monkeypatch, tmp_path):
        """cmd_claude_token saves valid token."""
        creds = {}
        monkeypatch.setattr("koro.handlers.commands.load_credentials", lambda: creds)
        monkeypatch.setattr("koro.handlers.commands.save_credentials", lambda c: creds.update(c))
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_claude_token

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.message_thread_id = None
        update.message.delete = AsyncMock()
        update.effective_chat.send_message = AsyncMock()

        context = MagicMock()
        context.args = ["sk-ant-valid-token-123"]

        await cmd_claude_token(update, context)

        assert creds.get("claude_token") == "sk-ant-valid-token-123"
        call_text = update.effective_chat.send_message.call_args[0][0]
        assert "saved" in call_text.lower()

    @pytest.mark.asyncio
    async def test_cmd_elevenlabs_key_no_args(self, monkeypatch):
        """cmd_elevenlabs_key shows usage without args."""
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_elevenlabs_key

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.message_thread_id = None
        update.message.delete = AsyncMock()
        update.effective_chat.send_message = AsyncMock()

        context = MagicMock()
        context.args = []

        await cmd_elevenlabs_key(update, context)

        call_text = update.effective_chat.send_message.call_args[0][0]
        assert "Usage" in call_text

    @pytest.mark.asyncio
    async def test_cmd_elevenlabs_key_too_short(self, monkeypatch):
        """cmd_elevenlabs_key rejects short key."""
        monkeypatch.setattr("koro.handlers.commands.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.commands.should_handle_message", lambda x: True)

        from koro.handlers.commands import cmd_elevenlabs_key

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.message_thread_id = None
        update.message.delete = AsyncMock()
        update.effective_chat.send_message = AsyncMock()

        context = MagicMock()
        context.args = ["short"]

        await cmd_elevenlabs_key(update, context)

        call_text = update.effective_chat.send_message.call_args[0][0]
        assert "Invalid" in call_text or "short" in call_text.lower()


class TestApprovalCallbackHandlers:
    """Tests for approval callback handlers."""

    @pytest.mark.asyncio
    async def test_approval_callback_approves(self, monkeypatch):
        """Approval callback approves tool use."""
        import asyncio
        from koro.handlers.messages import pending_approvals

        approval_event = asyncio.Event()
        pending_approvals["test123"] = {
            "user_id": 12345,
            "event": approval_event,
            "approved": None,
            "tool_name": "Read",
            "input": {},
        }

        from koro.handlers.callbacks import handle_approval_callback

        query = MagicMock()
        query.data = "approve_test123"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = MagicMock()

        await handle_approval_callback(update, context)

        assert pending_approvals.get("test123") is None or pending_approvals["test123"].get("approved") is True
        query.edit_message_text.assert_called()

    @pytest.mark.asyncio
    async def test_approval_callback_rejects(self, monkeypatch):
        """Approval callback rejects tool use."""
        import asyncio
        from koro.handlers.messages import pending_approvals

        approval_event = asyncio.Event()
        pending_approvals["test456"] = {
            "user_id": 12345,
            "event": approval_event,
            "approved": None,
            "tool_name": "Bash",
            "input": {},
        }

        from koro.handlers.callbacks import handle_approval_callback

        query = MagicMock()
        query.data = "reject_test456"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = MagicMock()

        await handle_approval_callback(update, context)

        query.edit_message_text.assert_called()
        call_text = query.edit_message_text.call_args[0][0]
        assert "Rejected" in call_text

    @pytest.mark.asyncio
    async def test_approval_callback_expired(self, monkeypatch):
        """Approval callback handles expired approvals."""
        from koro.handlers.callbacks import handle_approval_callback

        query = MagicMock()
        query.data = "approve_expired123"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = MagicMock()

        await handle_approval_callback(update, context)

        call_text = query.edit_message_text.call_args[0][0]
        assert "expired" in call_text.lower()


class TestMessageHandlers:
    """Tests for voice and text message handlers."""

    @pytest.mark.asyncio
    async def test_handle_voice_ignores_bot(self, monkeypatch):
        """handle_voice ignores bot messages."""
        from koro.handlers.messages import handle_voice

        update = MagicMock()
        update.effective_user.is_bot = True

        context = MagicMock()

        # Should return early without processing
        await handle_voice(update, context)

        # No reply_text should be called
        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_text_ignores_bot(self, monkeypatch):
        """handle_text ignores bot messages."""
        from koro.handlers.messages import handle_text

        update = MagicMock()
        update.effective_user.is_bot = True

        context = MagicMock()

        await handle_text(update, context)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_voice_ignores_wrong_topic(self, monkeypatch):
        """handle_voice ignores wrong topic."""
        monkeypatch.setattr("koro.handlers.messages.should_handle_message", lambda x: False)

        from koro.handlers.messages import handle_voice

        update = MagicMock()
        update.effective_user.is_bot = False
        update.message.message_thread_id = 999

        context = MagicMock()

        await handle_voice(update, context)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_text_ignores_wrong_topic(self, monkeypatch):
        """handle_text ignores wrong topic."""
        monkeypatch.setattr("koro.handlers.messages.should_handle_message", lambda x: False)

        from koro.handlers.messages import handle_text

        update = MagicMock()
        update.effective_user.is_bot = False
        update.message.message_thread_id = 999

        context = MagicMock()

        await handle_text(update, context)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_voice_ignores_wrong_chat(self, monkeypatch):
        """handle_voice ignores unauthorized chat."""
        monkeypatch.setattr("koro.handlers.messages.should_handle_message", lambda x: True)
        monkeypatch.setattr("koro.handlers.messages.ALLOWED_CHAT_ID", 12345)

        from koro.handlers.messages import handle_voice

        update = MagicMock()
        update.effective_user.is_bot = False
        update.effective_chat.id = 99999  # Wrong chat
        update.message.message_thread_id = None

        context = MagicMock()

        await handle_voice(update, context)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_text_ignores_wrong_chat(self, monkeypatch):
        """handle_text ignores unauthorized chat."""
        monkeypatch.setattr("koro.handlers.messages.should_handle_message", lambda x: True)
        monkeypatch.setattr("koro.handlers.messages.ALLOWED_CHAT_ID", 12345)

        from koro.handlers.messages import handle_text

        update = MagicMock()
        update.effective_user.is_bot = False
        update.effective_chat.id = 99999
        update.message.message_thread_id = None

        context = MagicMock()

        await handle_text(update, context)

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_voice_rate_limited(self, monkeypatch):
        """handle_voice respects rate limits."""
        from koro.rate_limit import RateLimiter

        limiter = RateLimiter()
        limiter.user_limits["12345"] = {
            "last_message": 9999999999,  # Future time
            "minute_count": 100,
            "minute_start": 9999999999,
        }

        monkeypatch.setattr("koro.handlers.messages.should_handle_message", lambda x: True)
        monkeypatch.setattr("koro.handlers.messages.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.messages.get_rate_limiter", lambda: limiter)

        from koro.handlers.messages import handle_voice

        update = MagicMock()
        update.effective_user.is_bot = False
        update.effective_user.id = 12345
        update.effective_chat.id = 12345
        update.message.message_thread_id = None
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await handle_voice(update, context)

        # Should get rate limit message
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "wait" in call_text.lower() or "limit" in call_text.lower()

    @pytest.mark.asyncio
    async def test_handle_text_rate_limited(self, monkeypatch):
        """handle_text respects rate limits."""
        from koro.rate_limit import RateLimiter

        limiter = RateLimiter()
        limiter.user_limits["12345"] = {
            "last_message": 9999999999,
            "minute_count": 100,
            "minute_start": 9999999999,
        }

        monkeypatch.setattr("koro.handlers.messages.should_handle_message", lambda x: True)
        monkeypatch.setattr("koro.handlers.messages.ALLOWED_CHAT_ID", 0)
        monkeypatch.setattr("koro.handlers.messages.get_rate_limiter", lambda: limiter)

        from koro.handlers.messages import handle_text

        update = MagicMock()
        update.effective_user.is_bot = False
        update.effective_user.id = 12345
        update.effective_chat.id = 12345
        update.message.message_thread_id = None
        update.message.text = "Hello"
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await handle_text(update, context)

        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "wait" in call_text.lower() or "limit" in call_text.lower()


class TestCallbackHandlers:
    """Tests for callback query handlers."""

    @pytest.mark.asyncio
    async def test_settings_toggle_audio(self, monkeypatch):
        """Settings callback toggles audio."""
        from koro.state import StateManager

        manager = StateManager()
        manager.settings = {"12345": {"audio_enabled": True, "voice_speed": 1.0, "mode": "go_all", "watch_enabled": False}}
        monkeypatch.setattr("koro.handlers.callbacks.get_state_manager", lambda: manager)

        from koro.handlers.callbacks import handle_settings_callback

        query = MagicMock()
        query.data = "setting_audio_toggle"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = MagicMock()

        await handle_settings_callback(update, context)

        # Audio should be toggled off
        assert manager.settings["12345"]["audio_enabled"] is False

    @pytest.mark.asyncio
    async def test_settings_toggle_mode(self, monkeypatch):
        """Settings callback toggles mode."""
        from koro.state import StateManager

        manager = StateManager()
        manager.settings = {"12345": {"audio_enabled": True, "voice_speed": 1.0, "mode": "go_all", "watch_enabled": False}}
        monkeypatch.setattr("koro.handlers.callbacks.get_state_manager", lambda: manager)

        from koro.handlers.callbacks import handle_settings_callback

        query = MagicMock()
        query.data = "setting_mode_toggle"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = MagicMock()

        await handle_settings_callback(update, context)

        assert manager.settings["12345"]["mode"] == "approve"

    @pytest.mark.asyncio
    async def test_settings_set_speed(self, monkeypatch):
        """Settings callback sets voice speed."""
        from koro.state import StateManager

        manager = StateManager()
        manager.settings = {"12345": {"audio_enabled": True, "voice_speed": 1.0, "mode": "go_all", "watch_enabled": False}}
        monkeypatch.setattr("koro.handlers.callbacks.get_state_manager", lambda: manager)

        from koro.handlers.callbacks import handle_settings_callback

        query = MagicMock()
        query.data = "setting_speed_0.9"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = MagicMock()

        await handle_settings_callback(update, context)

        assert manager.settings["12345"]["voice_speed"] == 0.9

    @pytest.mark.asyncio
    async def test_settings_rejects_invalid_speed(self, monkeypatch):
        """Settings callback rejects invalid speed."""
        from koro.state import StateManager

        manager = StateManager()
        manager.settings = {"12345": {"audio_enabled": True, "voice_speed": 1.0, "mode": "go_all", "watch_enabled": False}}
        monkeypatch.setattr("koro.handlers.callbacks.get_state_manager", lambda: manager)

        from koro.handlers.callbacks import handle_settings_callback

        query = MagicMock()
        query.data = "setting_speed_5.0"  # Out of range
        query.answer = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        context = MagicMock()

        await handle_settings_callback(update, context)

        # Speed unchanged
        assert manager.settings["12345"]["voice_speed"] == 1.0
        # Error shown
        query.answer.assert_called_with("Invalid speed range")
