"""Tests for Telegram handler utilities, commands, callbacks, and messages."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

import koro.interfaces.telegram.handlers.callbacks as callbacks
import koro.interfaces.telegram.handlers.commands as commands
import koro.interfaces.telegram.handlers.messages as messages
import koro.interfaces.telegram.handlers.utils as utils
from koro.state import StateManager
from koro.voice import VoiceTranscriptionError


@pytest.fixture
def state_manager(tmp_path):
    """Create a StateManager with a temp database."""
    return StateManager(db_path=tmp_path / "test.db")


@pytest.fixture
def allow_all_handlers(monkeypatch):
    """Allow handlers to run for any chat/topic."""
    monkeypatch.setattr(utils, "ALLOWED_CHAT_ID", 0)
    monkeypatch.setattr(utils, "should_handle_message", lambda _: True)


@pytest.fixture
def allow_all_commands(allow_all_handlers):
    """Allow commands to run for any chat/topic."""


@pytest.fixture
def allow_all_messages(allow_all_handlers):
    """Allow messages to run for any chat/topic."""


@pytest.fixture
def clear_pending_approvals():
    """Clear pending approvals between tests."""
    messages.pending_approvals.clear()
    return messages.pending_approvals


class TestShouldHandleMessage:
    """Tests for should_handle_message function."""

    @pytest.mark.parametrize(
        "topic_config,thread_id,expected",
        [
            (None, None, True),
            (None, 123, True),
            ("100", 100, True),
            ("100", 200, False),
            ("100", None, False),
            ("not_a_number", None, True),
        ],
    )
    def test_topic_filtering(self, monkeypatch, topic_config, thread_id, expected):
        """Topic filter respects configured topic ID."""
        monkeypatch.setattr(utils, "TOPIC_ID", topic_config)

        assert utils.should_handle_message(thread_id) is expected


class TestAuthorizedHandler:
    """Tests for authorized_handler decorator behavior."""

    @pytest.mark.asyncio
    async def test_callback_uses_callback_message_thread_even_with_sync_answer(
        self, monkeypatch
    ):
        """Callback updates should use callback message thread regardless of answer() type."""
        monkeypatch.setattr(utils, "TOPIC_ID", "100")
        monkeypatch.setattr(utils, "ALLOWED_CHAT_ID", 0)

        called = False

        @utils.authorized_handler
        async def _handler(update, context):
            nonlocal called
            called = True
            return "ok"

        update = MagicMock()
        update.message = None
        update.effective_chat.id = 12345
        update.callback_query = MagicMock()
        update.callback_query.answer = MagicMock()  # Sync callable (not coroutine func)
        update.callback_query.message.message_thread_id = 100

        result = await _handler(update, MagicMock())

        assert result == "ok"
        assert called is True

    @pytest.mark.asyncio
    async def test_callback_wrong_topic_still_answers_with_sync_answer(
        self, monkeypatch
    ):
        """Rejected callback updates should still answer callback query."""
        monkeypatch.setattr(utils, "TOPIC_ID", "100")
        monkeypatch.setattr(utils, "ALLOWED_CHAT_ID", 0)

        called = False

        @utils.authorized_handler
        async def _handler(update, context):
            nonlocal called
            called = True
            return "ok"

        update = MagicMock()
        update.message = None
        update.effective_chat.id = 12345
        update.callback_query = MagicMock()
        update.callback_query.answer = MagicMock()
        update.callback_query.message.message_thread_id = 999

        result = await _handler(update, MagicMock())

        assert result is None
        assert called is False
        update.callback_query.answer.assert_called_once()


class TestSendLongMessage:
    """Tests for send_long_message function."""

    @pytest.mark.asyncio
    async def test_short_message_single_edit(
        self, make_update, make_processing_message
    ):
        """Short messages are sent as single edit."""
        update = make_update()
        first_msg = make_processing_message()

        await utils.send_long_message(update, first_msg, "Short message")

        first_msg.edit_text.assert_called_once_with("Short message")

    @pytest.mark.asyncio
    async def test_long_message_split(self, make_update, make_processing_message):
        """Long messages are split into chunks."""
        update = make_update()
        first_msg = make_processing_message()

        long_text = "word " * 1000  # ~5000 chars
        await utils.send_long_message(update, first_msg, long_text, chunk_size=2000)

        first_msg.edit_text.assert_called_once()
        assert update.message.reply_text.call_count >= 1

    @pytest.mark.asyncio
    async def test_chunk_includes_counter(self, make_update, make_processing_message):
        """Chunked messages include counter."""
        update = make_update()
        first_msg = make_processing_message()

        long_text = "x" * 5000
        await utils.send_long_message(update, first_msg, long_text, chunk_size=2000)

        first_call_text = first_msg.edit_text.call_args.args[0]
        assert "[1/" in first_call_text


class TestCommandHandlers:
    """Tests for command handler authentication and responses."""

    @pytest.mark.asyncio
    async def test_cmd_new_creates_session(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_new resets current session."""
        await state_manager.update_session("12345", "old_session")
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)
        context = MagicMock()
        context.args = []

        await commands.cmd_new(update, context)

        state = await state_manager.get_session_state("12345")
        assert state.current_session_id is None
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_new_with_name(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_new with name shows session name."""
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)
        context = MagicMock()
        context.args = ["my", "session"]

        await commands.cmd_new(update, context)

        call_text = update.message.reply_text.call_args.args[0]
        assert "my session" in call_text
        typed_state = await state_manager.get_session_state("12345")
        assert typed_state.pending_session_name == "my session"

    @pytest.mark.asyncio
    async def test_cmd_continue_with_session(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_continue shows session info when exists."""
        await state_manager.update_session("12345", "abc12345")
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)

        await commands.cmd_continue(update, MagicMock())

        call_text = update.message.reply_text.call_args.args[0]
        assert "abc12345" in call_text

    @pytest.mark.asyncio
    async def test_cmd_continue_without_session(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_continue shows message when no session."""
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)

        await commands.cmd_continue(update, MagicMock())

        call_text = update.message.reply_text.call_args.args[0]
        assert "No previous session" in call_text

    @pytest.mark.asyncio
    async def test_cmd_sessions_empty(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_sessions shows empty message when no sessions."""
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)

        await commands.cmd_sessions(update, MagicMock())

        call_text = update.message.reply_text.call_args.args[0]
        assert "No sessions" in call_text

    @pytest.mark.asyncio
    async def test_cmd_sessions_lists_sessions(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_sessions lists available sessions."""
        await state_manager.update_session("12345", "sess1-abcdef")
        await state_manager.update_session("12345", "sess2-fedcba")
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)

        await commands.cmd_sessions(update, MagicMock())

        call_text = update.message.reply_text.call_args.args[0]
        assert "sess1-ab" in call_text
        assert "sess2-fe" in call_text
        assert "current" in call_text
        assert "Use /switch <name|id-prefix>" in call_text

    @pytest.mark.asyncio
    async def test_cmd_sessions_shows_pending_name(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_sessions includes pending new-session label."""
        await state_manager.set_pending_session_name("12345", "project-z")
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)
        await commands.cmd_sessions(update, MagicMock())

        call_text = update.message.reply_text.call_args.args[0]
        assert "Pending new session: project-z" in call_text

    @pytest.mark.asyncio
    async def test_cmd_switch_no_args(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_switch shows empty state when no sessions exist."""
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(chat_id=12345)
        context = MagicMock()
        context.args = []

        await commands.cmd_switch(update, context)

        call_text = update.message.reply_text.call_args.args[0]
        assert "No sessions yet" in call_text

    @pytest.mark.asyncio
    async def test_cmd_switch_no_args_shows_picker(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_switch without args shows inline selector when sessions exist."""
        await state_manager.update_session("12345", "abc123456789")
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(chat_id=12345)
        context = MagicMock()
        context.args = []

        await commands.cmd_switch(update, context)

        call_text = update.message.reply_text.call_args.args[0]
        call_kwargs = update.message.reply_text.call_args.kwargs
        assert "Select a session to switch" in call_text
        assert call_kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_cmd_switch_finds_session(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_switch switches to matching session."""
        await state_manager.update_session("12345", "abc123456789")
        await state_manager.clear_current_session("12345")
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)
        context = MagicMock()
        context.args = ["abc"]

        await commands.cmd_switch(update, context)

        state = await state_manager.get_session_state("12345")
        assert state.current_session_id == "abc123456789"

    @pytest.mark.asyncio
    async def test_cmd_switch_finds_session_by_name(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_switch switches by session name."""
        await state_manager.update_session("12345", "id-1", session_name="alpha")
        await state_manager.update_session("12345", "id-2", session_name="beta")
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)
        context = MagicMock()
        context.args = ["alpha"]

        await commands.cmd_switch(update, context)

        typed_state = await state_manager.get_session_state("12345")
        assert typed_state.current_session_id == "id-1"

    @pytest.mark.asyncio
    async def test_cmd_switch_by_name_reports_ambiguous(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_switch reports ambiguity for non-unique name prefix."""
        await state_manager.update_session("12345", "id-1", session_name="project-a")
        await state_manager.update_session("12345", "id-2", session_name="project-b")
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)
        context = MagicMock()
        context.args = ["project"]

        await commands.cmd_switch(update, context)

        call_text = update.message.reply_text.call_args.args[0]
        assert "Multiple matches" in call_text
        call_kwargs = update.message.reply_text.call_args.kwargs
        assert call_kwargs.get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_cmd_switch_not_found(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_switch shows error when session not found."""
        await state_manager.update_session("12345", "abc123")
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)
        context = MagicMock()
        context.args = ["xyz"]

        await commands.cmd_switch(update, context)

        call_text = update.message.reply_text.call_args.args[0]
        assert "not found" in call_text

    @pytest.mark.asyncio
    async def test_cmd_status_with_session(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_status shows session info."""
        await state_manager.update_session("12345", "abc12345")
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)

        await commands.cmd_status(update, MagicMock())

        call_text = update.message.reply_text.call_args.args[0]
        assert "abc12345" in call_text

    @pytest.mark.asyncio
    async def test_cmd_status_no_session(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_status shows message when no session."""
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)

        await commands.cmd_status(update, MagicMock())

        call_text = update.message.reply_text.call_args.args[0]
        assert "No active session" in call_text

    @pytest.mark.asyncio
    async def test_cmd_setup_shows_status(
        self, make_update, allow_all_commands, monkeypatch
    ):
        """cmd_setup shows credentials status."""
        monkeypatch.setattr(commands, "load_credentials", lambda: {})

        update = make_update(chat_id=12345)

        await commands.cmd_setup(update, MagicMock())

        update.message.reply_text.assert_called_once()
        call_kwargs = update.message.reply_text.call_args.kwargs
        assert call_kwargs["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_cmd_health_checks_systems(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_health checks all systems."""
        mock_voice = MagicMock()
        mock_voice.health_check.return_value = (True, "OK")
        mock_claude = MagicMock()
        mock_claude.health_check.return_value = (True, "OK")

        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)
        monkeypatch.setattr(commands, "get_voice_engine", lambda: mock_voice)
        monkeypatch.setattr(commands, "get_claude_client", lambda: mock_claude)
        monkeypatch.setattr(commands, "SANDBOX_DIR", "/tmp/sandbox")

        update = make_update(user_id=12345, chat_id=12345)

        await commands.cmd_health(update, MagicMock())

        call_text = update.message.reply_text.call_args.args[0]
        assert "Health Check" in call_text
        assert "ElevenLabs" in call_text
        assert "Claude" in call_text

    @pytest.mark.asyncio
    async def test_cmd_settings_shows_menu(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_settings shows settings menu."""
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)

        await commands.cmd_settings(update, MagicMock())

        call_text = update.message.reply_text.call_args.args[0]
        assert "Settings" in call_text

    @pytest.mark.asyncio
    async def test_cmd_model_shows_current(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_model shows current model."""
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)
        context = MagicMock()
        context.args = []

        await commands.cmd_model(update, context)

        call_text = update.message.reply_text.call_args.args[0]
        assert "Current model" in call_text

    @pytest.mark.asyncio
    async def test_cmd_model_sets_value(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_model sets the model."""
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)
        context = MagicMock()
        context.args = ["claude-test"]

        await commands.cmd_model(update, context)

        settings = await state_manager.get_settings("12345")
        assert settings.model == "claude-test"

    @pytest.mark.asyncio
    async def test_cmd_model_rejects_invalid_identifier(
        self, make_update, allow_all_commands, state_manager, monkeypatch
    ):
        """cmd_model rejects invalid model identifier values."""
        monkeypatch.setattr(commands, "get_state_manager", lambda: state_manager)

        update = make_update(user_id=12345, chat_id=12345)
        context = MagicMock()
        context.args = ["bad/model"]

        await commands.cmd_model(update, context)

        settings = await state_manager.get_settings("12345")
        assert settings.model == ""
        update.message.reply_text.assert_called_once()
        assert "Invalid model identifier" in update.message.reply_text.call_args.args[0]

    @pytest.mark.asyncio
    async def test_cmd_claude_token_no_args(self, make_update, allow_all_commands):
        """cmd_claude_token shows usage without args."""
        update = make_update(chat_id=12345)
        context = MagicMock()
        context.args = []

        await commands.cmd_claude_token(update, context)

        call_text = update.effective_chat.send_message.call_args.args[0]
        assert "Usage" in call_text

    @pytest.mark.asyncio
    async def test_cmd_claude_token_invalid_format(
        self, make_update, allow_all_commands
    ):
        """cmd_claude_token rejects invalid token format."""
        update = make_update(chat_id=12345)
        context = MagicMock()
        context.args = ["invalid_token"]

        await commands.cmd_claude_token(update, context)

        call_text = update.effective_chat.send_message.call_args.args[0]
        assert "Invalid" in call_text

    @pytest.mark.asyncio
    async def test_cmd_claude_token_saves_valid(
        self, make_update, allow_all_commands, monkeypatch
    ):
        """cmd_claude_token saves valid token."""
        creds = {}
        monkeypatch.setattr(commands, "load_credentials", lambda: creds)
        monkeypatch.setattr(commands, "save_credentials", lambda c: creds.update(c))

        update = make_update(chat_id=12345)
        context = MagicMock()
        context.args = ["sk-ant-valid-token-123"]

        await commands.cmd_claude_token(update, context)

        assert creds.get("claude_token") == "sk-ant-valid-token-123"
        call_text = update.effective_chat.send_message.call_args.args[0]
        assert "saved" in call_text.lower()

    @pytest.mark.asyncio
    async def test_cmd_elevenlabs_key_no_args(self, make_update, allow_all_commands):
        """cmd_elevenlabs_key shows usage without args."""
        update = make_update(chat_id=12345)
        context = MagicMock()
        context.args = []

        await commands.cmd_elevenlabs_key(update, context)

        call_text = update.effective_chat.send_message.call_args.args[0]
        assert "Usage" in call_text

    @pytest.mark.asyncio
    async def test_cmd_elevenlabs_key_too_short(self, make_update, allow_all_commands):
        """cmd_elevenlabs_key rejects short key."""
        update = make_update(chat_id=12345)
        context = MagicMock()
        context.args = ["short"]

        await commands.cmd_elevenlabs_key(update, context)

        call_text = update.effective_chat.send_message.call_args.args[0]
        assert "Invalid" in call_text or "short" in call_text.lower()


class TestApprovalCallbackHandlers:
    """Tests for approval callback handlers."""

    @pytest.mark.asyncio
    async def test_approval_callback_approves(
        self, make_callback_query, clear_pending_approvals, allow_all_messages
    ):
        """Approval callback approves tool use."""
        approval_event = asyncio.Event()
        messages.pending_approvals["test123"] = {
            "user_id": "12345",
            "event": approval_event,
            "approved": None,
            "tool_name": "Read",
            "input": {},
        }

        query = make_callback_query("approve_test123")
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        await callbacks.handle_approval_callback(update, MagicMock())

        assert messages.pending_approvals.get("test123", {}).get("approved") is True
        query.edit_message_text.assert_called()

    @pytest.mark.asyncio
    async def test_approval_callback_rejects(
        self, make_callback_query, clear_pending_approvals, allow_all_messages
    ):
        """Approval callback rejects tool use."""
        approval_event = asyncio.Event()
        messages.pending_approvals["test456"] = {
            "user_id": "12345",
            "event": approval_event,
            "approved": None,
            "tool_name": "Bash",
            "input": {},
        }

        query = make_callback_query("reject_test456")
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        await callbacks.handle_approval_callback(update, MagicMock())

        call_text = query.edit_message_text.call_args.args[0]
        assert "Rejected" in call_text

    @pytest.mark.asyncio
    async def test_approval_callback_expired(
        self, make_callback_query, clear_pending_approvals, allow_all_messages
    ):
        """Approval callback handles expired approvals."""
        query = make_callback_query("approve_expired123")
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        await callbacks.handle_approval_callback(update, MagicMock())

        call_text = query.edit_message_text.call_args.args[0]
        assert "expired" in call_text.lower()


class TestMessageHandlers:
    """Tests for voice and text message handlers."""

    @pytest.mark.asyncio
    async def test_handle_voice_ignores_bot(self, make_update):
        """handle_voice ignores bot messages."""
        update = make_update(is_bot=True)

        await messages.handle_voice(update, MagicMock())

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_text_ignores_bot(self, make_update):
        """handle_text ignores bot messages."""
        update = make_update(is_bot=True)

        await messages.handle_text(update, MagicMock())

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_voice_ignores_wrong_topic(self, make_update, monkeypatch):
        """handle_voice ignores wrong topic."""
        monkeypatch.setattr(utils, "should_handle_message", lambda _: False)
        update = make_update(thread_id=999)

        await messages.handle_voice(update, MagicMock())

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_text_ignores_wrong_topic(self, make_update, monkeypatch):
        """handle_text ignores wrong topic."""
        monkeypatch.setattr(utils, "should_handle_message", lambda _: False)
        update = make_update(thread_id=999)

        await messages.handle_text(update, MagicMock())

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_voice_ignores_wrong_chat(self, make_update, monkeypatch):
        """handle_voice ignores unauthorized chat."""
        monkeypatch.setattr(utils, "should_handle_message", lambda _: True)
        monkeypatch.setattr(utils, "ALLOWED_CHAT_ID", 12345)
        update = make_update(chat_id=99999)

        await messages.handle_voice(update, MagicMock())

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_text_ignores_wrong_chat(self, make_update, monkeypatch):
        """handle_text ignores unauthorized chat."""
        monkeypatch.setattr(utils, "should_handle_message", lambda _: True)
        monkeypatch.setattr(utils, "ALLOWED_CHAT_ID", 12345)
        update = make_update(chat_id=99999)

        await messages.handle_text(update, MagicMock())

        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_voice_rate_limited(
        self, make_update, allow_all_messages, monkeypatch
    ):
        """handle_voice respects rate limits."""
        limiter = MagicMock()
        limiter.check.return_value = (False, "Please wait")
        monkeypatch.setattr(messages, "get_rate_limiter", lambda: limiter)

        update = make_update(user_id=12345, chat_id=12345)

        await messages.handle_voice(update, MagicMock())

        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args.args[0]
        assert "wait" in call_text.lower()

    @pytest.mark.asyncio
    async def test_handle_text_rate_limited(
        self, make_update, allow_all_messages, monkeypatch
    ):
        """handle_text respects rate limits."""
        limiter = MagicMock()
        limiter.check.return_value = (False, "Rate limit reached")
        monkeypatch.setattr(messages, "get_rate_limiter", lambda: limiter)

        update = make_update(user_id=12345, chat_id=12345, text="Hello")

        await messages.handle_text(update, MagicMock())

        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args.args[0]
        assert "limit" in call_text.lower()


class TestCallbackHandlers:
    """Tests for callback query handlers."""

    @pytest.mark.asyncio
    async def test_settings_callback_ignores_wrong_topic(
        self, make_callback_query, monkeypatch
    ):
        """Settings callback ignores updates from wrong topic."""
        monkeypatch.setattr(utils, "should_handle_message", lambda _: False)
        monkeypatch.setattr(utils, "ALLOWED_CHAT_ID", 0)

        query = make_callback_query("setting_audio_toggle")
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345
        update.effective_chat.id = 12345

        await callbacks.handle_settings_callback(update, MagicMock())

        query.answer.assert_called_once()
        query.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_approval_callback_ignores_wrong_chat(
        self, make_callback_query, monkeypatch
    ):
        """Approval callback ignores unauthorized chat."""
        monkeypatch.setattr(utils, "should_handle_message", lambda _: True)
        monkeypatch.setattr(utils, "ALLOWED_CHAT_ID", 12345)

        query = make_callback_query("approve_test123")
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345
        update.effective_chat.id = 99999

        await callbacks.handle_approval_callback(update, MagicMock())

        query.answer.assert_called_once()
        query.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_settings_callback_answers_when_data_missing(self, monkeypatch):
        """Settings callback acknowledges callback query when data is missing."""
        monkeypatch.setattr(utils, "should_handle_message", lambda _: True)
        monkeypatch.setattr(utils, "ALLOWED_CHAT_ID", 0)

        query = MagicMock()
        query.data = None
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345
        update.effective_chat.id = 12345

        await callbacks.handle_settings_callback(update, MagicMock())

        query.answer.assert_called_once()
        query.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_approval_callback_answers_when_data_missing(self, monkeypatch):
        """Approval callback acknowledges callback query when data is missing."""
        monkeypatch.setattr(utils, "should_handle_message", lambda _: True)
        monkeypatch.setattr(utils, "ALLOWED_CHAT_ID", 0)

        query = MagicMock()
        query.data = None
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345
        update.effective_chat.id = 12345

        await callbacks.handle_approval_callback(update, MagicMock())

        query.answer.assert_called_once()
        query.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_switch_callback_answers_when_data_missing(self, monkeypatch):
        """Switch callback acknowledges callback query when data is missing."""
        monkeypatch.setattr(utils, "should_handle_message", lambda _: True)
        monkeypatch.setattr(utils, "ALLOWED_CHAT_ID", 0)

        query = MagicMock()
        query.data = None
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345
        update.effective_chat.id = 12345

        await callbacks.handle_switch_callback(update, MagicMock())

        query.answer.assert_called_once()
        query.edit_message_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_settings_toggle_audio(
        self, make_callback_query, state_manager, monkeypatch, allow_all_messages
    ):
        """Settings callback toggles audio."""
        await state_manager.update_settings("12345", audio_enabled=True)
        monkeypatch.setattr(callbacks, "get_state_manager", lambda: state_manager)

        query = make_callback_query("setting_audio_toggle")
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        await callbacks.handle_settings_callback(update, MagicMock())

        settings = await state_manager.get_settings("12345")
        assert settings.audio_enabled is False

    @pytest.mark.asyncio
    async def test_settings_toggle_mode(
        self, make_callback_query, state_manager, monkeypatch, allow_all_messages
    ):
        """Settings callback toggles mode."""
        await state_manager.update_settings("12345", mode="go_all")
        monkeypatch.setattr(callbacks, "get_state_manager", lambda: state_manager)

        query = make_callback_query("setting_mode_toggle")
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        await callbacks.handle_settings_callback(update, MagicMock())

        settings = await state_manager.get_settings("12345")
        assert settings.mode.value == "approve"

    @pytest.mark.asyncio
    async def test_settings_set_speed(
        self, make_callback_query, state_manager, monkeypatch, allow_all_messages
    ):
        """Settings callback sets voice speed."""
        await state_manager.update_settings("12345", voice_speed=1.0)
        monkeypatch.setattr(callbacks, "get_state_manager", lambda: state_manager)

        query = make_callback_query("setting_speed_0.9")
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        await callbacks.handle_settings_callback(update, MagicMock())

        settings = await state_manager.get_settings("12345")
        assert settings.voice_speed == 0.9

    @pytest.mark.asyncio
    async def test_settings_rejects_invalid_speed(
        self, make_callback_query, state_manager, monkeypatch, allow_all_messages
    ):
        """Settings callback rejects invalid speed."""
        await state_manager.update_settings("12345", voice_speed=1.0)
        monkeypatch.setattr(callbacks, "get_state_manager", lambda: state_manager)

        query = make_callback_query("setting_speed_5.0")
        update = MagicMock()
        update.callback_query = query
        update.effective_user.id = 12345

        await callbacks.handle_settings_callback(update, MagicMock())

        settings = await state_manager.get_settings("12345")
        assert settings.voice_speed == 1.0
        query.answer.assert_called_with("Invalid speed range")


class TestMessageHandlersFullFlow:
    """Tests for full message handler flow."""

    @pytest.mark.asyncio
    async def test_handle_text_full_flow(
        self,
        make_update,
        make_processing_message,
        allow_all_messages,
        state_manager,
        monkeypatch,
    ):
        """handle_text processes text and calls Claude."""
        limiter = MagicMock()
        limiter.check.return_value = (True, "")
        mock_voice = MagicMock()
        mock_voice.text_to_speech = AsyncMock(return_value=b"audio_bytes")
        mock_claude = MagicMock()
        mock_claude.query = AsyncMock(
            return_value=("Hello from Claude!", "sess123", {"cost": 0.01})
        )

        monkeypatch.setattr(messages, "get_state_manager", lambda: state_manager)
        monkeypatch.setattr(messages, "get_rate_limiter", lambda: limiter)
        monkeypatch.setattr(messages, "get_voice_engine", lambda: mock_voice)
        monkeypatch.setattr(messages, "get_claude_client", lambda: mock_claude)

        processing_msg = make_processing_message()
        update = make_update(
            user_id=12345,
            chat_id=12345,
            text="Hello Claude",
        )
        update.message.reply_text = AsyncMock(return_value=processing_msg)

        await messages.handle_text(update, MagicMock())

        mock_claude.query.assert_called_once()
        processing_msg.edit_text.assert_called()

    @pytest.mark.asyncio
    async def test_handle_text_no_audio_when_disabled(
        self,
        make_update,
        make_processing_message,
        allow_all_messages,
        state_manager,
        monkeypatch,
    ):
        """handle_text skips audio when disabled."""
        await state_manager.update_settings("12345", audio_enabled=False)

        limiter = MagicMock()
        limiter.check.return_value = (True, "")
        mock_voice = MagicMock()
        mock_voice.text_to_speech = AsyncMock(return_value=b"audio_bytes")
        mock_claude = MagicMock()
        mock_claude.query = AsyncMock(return_value=("Response", "sess123", {}))

        monkeypatch.setattr(messages, "get_state_manager", lambda: state_manager)
        monkeypatch.setattr(messages, "get_rate_limiter", lambda: limiter)
        monkeypatch.setattr(messages, "get_voice_engine", lambda: mock_voice)
        monkeypatch.setattr(messages, "get_claude_client", lambda: mock_claude)

        processing_msg = make_processing_message()
        update = make_update(user_id=12345, chat_id=12345, text="Hello")
        update.message.reply_text = AsyncMock(return_value=processing_msg)

        await messages.handle_text(update, MagicMock())

        mock_voice.text_to_speech.assert_not_called()
        update.message.reply_voice.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_voice_transcribes_and_calls_claude(
        self,
        make_update,
        make_processing_message,
        make_voice_message,
        allow_all_messages,
        state_manager,
        monkeypatch,
    ):
        """handle_voice transcribes voice and calls Claude."""
        limiter = MagicMock()
        limiter.check.return_value = (True, "")
        mock_voice = MagicMock()
        mock_voice.transcribe = AsyncMock(return_value="Hello from voice")
        mock_voice.text_to_speech = AsyncMock(return_value=b"audio_bytes")
        mock_claude = MagicMock()
        mock_claude.query = AsyncMock(return_value=("Hello back!", "sess123", {}))

        monkeypatch.setattr(messages, "get_state_manager", lambda: state_manager)
        monkeypatch.setattr(messages, "get_rate_limiter", lambda: limiter)
        monkeypatch.setattr(messages, "get_voice_engine", lambda: mock_voice)
        monkeypatch.setattr(messages, "get_claude_client", lambda: mock_claude)

        processing_msg = make_processing_message()
        update = make_update(
            user_id=12345,
            chat_id=12345,
            voice=make_voice_message(),
        )
        update.message.reply_text = AsyncMock(return_value=processing_msg)

        await messages.handle_voice(update, MagicMock())

        mock_voice.transcribe.assert_called_once()
        mock_claude.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_voice_error_on_transcription_failure(
        self,
        make_update,
        make_processing_message,
        make_voice_message,
        allow_all_messages,
        state_manager,
        monkeypatch,
    ):
        """handle_voice shows error on transcription failure."""
        limiter = MagicMock()
        limiter.check.return_value = (True, "")
        mock_voice = MagicMock()
        mock_voice.transcribe = AsyncMock(
            side_effect=VoiceTranscriptionError("API failed")
        )

        monkeypatch.setattr(messages, "get_state_manager", lambda: state_manager)
        monkeypatch.setattr(messages, "get_rate_limiter", lambda: limiter)
        monkeypatch.setattr(messages, "get_voice_engine", lambda: mock_voice)

        processing_msg = make_processing_message()
        update = make_update(
            user_id=12345,
            chat_id=12345,
            voice=make_voice_message(),
        )
        update.message.reply_text = AsyncMock(return_value=processing_msg)

        await messages.handle_voice(update, MagicMock())

        call_text = processing_msg.edit_text.call_args.args[0]
        assert "error" in call_text.lower()

    @pytest.mark.asyncio
    async def test_handle_text_handles_exception(
        self,
        make_update,
        make_processing_message,
        allow_all_messages,
        state_manager,
        monkeypatch,
    ):
        """handle_text handles exceptions gracefully."""
        limiter = MagicMock()
        limiter.check.return_value = (True, "")
        mock_claude = MagicMock()
        mock_claude.query = AsyncMock(side_effect=Exception("Connection failed"))

        monkeypatch.setattr(messages, "get_state_manager", lambda: state_manager)
        monkeypatch.setattr(messages, "get_rate_limiter", lambda: limiter)
        monkeypatch.setattr(messages, "get_claude_client", lambda: mock_claude)

        processing_msg = make_processing_message()
        update = make_update(user_id=12345, chat_id=12345, text="Hello")
        update.message.reply_text = AsyncMock(return_value=processing_msg)

        await messages.handle_text(update, MagicMock())

        call_text = processing_msg.edit_text.call_args.args[0]
        assert "Error" in call_text


class TestPendingApprovalsCleanup:
    """Tests for pending_approvals memory management."""

    def test_pending_approvals_cleaned_on_timeout(self):
        """pending_approvals entries should be removed after timeout."""
        messages.pending_approvals.clear()

        approval_id = "test123"
        messages.pending_approvals[approval_id] = {
            "created_at": time.time() - 600,
            "user_id": "12345",
            "tool_name": "Bash",
        }

        messages.cleanup_stale_approvals(max_age_seconds=300)

        assert approval_id not in messages.pending_approvals

    def test_pending_approvals_max_size_enforced(self):
        """pending_approvals should not exceed max size."""
        messages.pending_approvals.clear()

        for i in range(messages.MAX_PENDING_APPROVALS + 10):
            messages.add_pending_approval(
                f"id_{i}", {"user_id": str(i), "created_at": time.time()}
            )

        assert len(messages.pending_approvals) <= messages.MAX_PENDING_APPROVALS


class TestExceptionLogging:
    """Tests for proper exception logging instead of silent swallowing."""

    @pytest.mark.asyncio
    async def test_message_delete_failure_logged(
        self, capsys, make_update, allow_all_commands
    ):
        """Failed message deletion should be logged."""
        update = make_update(chat_id=12345)
        update.message.delete = AsyncMock(side_effect=Exception("Cannot delete"))
        context = MagicMock()
        context.args = []

        await commands.cmd_claude_token(update, context)

        captured = capsys.readouterr()
        assert "delete" in captured.out.lower()
