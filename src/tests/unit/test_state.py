"""Tests for koro.state module."""

import asyncio

import pytest

from koro.state import MAX_SESSIONS, StateManager


@pytest.fixture
def state_manager(tmp_path):
    """Create a StateManager with a temp database."""
    return StateManager(db_path=tmp_path / "test.db")


class TestStateManager:
    """Tests for StateManager class."""

    def test_init_with_default_path(self, tmp_path):
        """StateManager uses provided db_path."""
        db_file = tmp_path / "test.db"
        manager = StateManager(db_path=db_file)

        assert manager.db_path == db_file
        assert db_file.exists()

    @pytest.mark.asyncio
    async def test_get_session_state_creates_default(self, state_manager):
        """get_session_state creates default state for new user."""
        state = await state_manager.get_session_state("99999")

        assert state.current_session_id is None
        assert state.sessions == []

    @pytest.mark.asyncio
    async def test_get_settings_creates_defaults(self, state_manager):
        """get_settings creates default settings for new user."""
        settings = await state_manager.get_settings("99999")

        assert settings.audio_enabled is True
        assert settings.mode.value == "go_all"
        assert settings.watch_enabled is False
        assert settings.voice_speed is not None
        assert settings.model == ""
        assert settings.stt_language == "auto"

    @pytest.mark.parametrize(
        "key,value,expected_attr,expected_value",
        [
            ("audio_enabled", False, "audio_enabled", False),
            ("mode", "approve", "mode", "approve"),
            ("voice_speed", 0.9, "voice_speed", 0.9),
            ("watch_enabled", True, "watch_enabled", True),
            ("model", "claude-test", "model", "claude-test"),
            ("stt_language", "pl", "stt_language", "pl"),
        ],
    )
    @pytest.mark.asyncio
    async def test_update_settings_saves(
        self, state_manager, key, value, expected_attr, expected_value
    ):
        """update_settings updates and saves settings."""
        await state_manager.update_settings("12345", **{key: value})

        settings = await state_manager.get_settings("12345")
        actual = getattr(settings, expected_attr)
        # Mode is an enum, compare values
        if expected_attr == "mode":
            actual = actual.value
        assert actual == expected_value

    @pytest.mark.asyncio
    async def test_settings_persist_after_recreation(self, tmp_path):
        """Settings persist across StateManager instances."""
        db_file = tmp_path / "test.db"

        manager1 = StateManager(db_path=db_file)
        await manager1.update_settings("12345", audio_enabled=False)
        await manager1.update_settings("12345", mode="approve")
        await manager1.update_settings("12345", stt_language="pl")

        # Create new instance with same db
        manager2 = StateManager(db_path=db_file)
        settings = await manager2.get_settings("12345")

        assert settings.audio_enabled is False
        assert settings.mode.value == "approve"
        assert settings.stt_language == "pl"


class TestStateManagerAsync:
    """Tests for async StateManager methods."""

    @pytest.mark.asyncio
    async def test_get_session_state_typed_for_new_user(self, state_manager):
        """get_session_state returns typed empty state for new users."""
        state = await state_manager.get_session_state("99999")

        assert state.current_session_id is None
        assert state.sessions == []
        assert state.pending_session_name is None

    @pytest.mark.asyncio
    async def test_update_session_sets_current(self, state_manager):
        """update_session sets current session and adds to list."""
        await state_manager.update_session("12345", "new_session_xyz")

        typed = await state_manager.get_session_state("12345")
        assert typed.current_session_id == "new_session_xyz"
        assert typed.sessions[0].id == "new_session_xyz"
        assert typed.sessions[0].is_current is True

    @pytest.mark.asyncio
    async def test_update_session_no_duplicate(self, state_manager):
        """update_session doesn't add duplicate session IDs."""
        await state_manager.update_session("12345", "abc")
        await state_manager.update_session("12345", "abc")

        state = await state_manager.get_session_state("12345")
        assert [session.id for session in state.sessions].count("abc") == 1

    @pytest.mark.asyncio
    async def test_create_session(self, state_manager):
        """create_session creates a new session."""
        session = await state_manager.create_session("12345")

        assert session.id is not None
        assert session.user_id == "12345"
        state = await state_manager.get_session_state("12345")
        assert state.current_session_id == session.id

    @pytest.mark.asyncio
    async def test_get_current_session(self, state_manager):
        """get_current_session returns the current session."""
        created = await state_manager.create_session("12345")
        current = await state_manager.get_current_session("12345")

        assert current is not None
        assert current.id == created.id

    @pytest.mark.asyncio
    async def test_get_current_session_none_for_new_user(self, state_manager):
        """get_current_session returns None for user without sessions."""
        current = await state_manager.get_current_session("99999")

        assert current is None

    @pytest.mark.asyncio
    async def test_clear_current_session(self, state_manager):
        """clear_current_session removes current session."""
        await state_manager.create_session("12345")
        await state_manager.clear_current_session("12345")

        current = await state_manager.get_current_session("12345")
        assert current is None
        # But session should still exist in the list
        state = await state_manager.get_session_state("12345")
        assert len(state.sessions) == 1

    @pytest.mark.asyncio
    async def test_set_current_session(self, state_manager):
        """set_current_session switches to existing session."""
        session1 = await state_manager.create_session("12345")
        await state_manager.create_session("12345")  # Create second session

        await state_manager.set_current_session("12345", session1.id)

        current = await state_manager.get_current_session("12345")
        assert current.id == session1.id

    @pytest.mark.asyncio
    async def test_update_session_uses_pending_name(self, state_manager):
        """Pending session name is consumed when first session is created."""
        await state_manager.set_pending_session_name("12345", "project-x")

        await state_manager.update_session("12345", "sess-1")
        state = await state_manager.get_session_state("12345")

        assert state.pending_session_name is None
        assert state.sessions[0].name == "project-x"

    @pytest.mark.asyncio
    async def test_create_session_does_not_consume_pending_name(self, state_manager):
        """create_session leaves pending name intact for explicit update_session flow."""
        await state_manager.set_pending_session_name("12345", "project-x")

        session = await state_manager.create_session("12345")
        state = await state_manager.get_session_state("12345")

        assert state.pending_session_name == "project-x"
        assert state.sessions[0].id == session.id
        assert state.sessions[0].name is None

    @pytest.mark.asyncio
    async def test_update_session_can_set_name(self, state_manager):
        """update_session persists explicit session names."""
        await state_manager.update_session("12345", "sess-1", session_name="alpha")
        state = await state_manager.get_session_state("12345")

        assert state.sessions[0].name == "alpha"

    @pytest.mark.asyncio
    async def test_update_session_applies_pending_name_to_existing_session(
        self, state_manager
    ):
        """Pending name should apply when switching/updating an existing session."""
        await state_manager.update_session("12345", "sess-1")
        await state_manager.set_pending_session_name("12345", "renamed")

        await state_manager.update_session("12345", "sess-1")
        state = await state_manager.get_session_state("12345")

        assert state.pending_session_name is None
        assert state.sessions[0].name == "renamed"

    @pytest.mark.asyncio
    async def test_update_session_does_not_clear_newer_pending_name(
        self, state_manager
    ):
        """
        Explicit stale session_name should not clear a newer pending name.

        This guards the race where /new runs while a message is in-flight.
        """
        await state_manager.set_pending_session_name("12345", "newer-name")

        await state_manager.update_session("12345", "sess-1", session_name="stale-name")
        state = await state_manager.get_session_state("12345")

        assert state.sessions[0].name == "stale-name"
        assert state.pending_session_name == "newer-name"

    @pytest.mark.asyncio
    async def test_set_pending_session_name_initializes_stt_language_from_default(
        self, state_manager, monkeypatch
    ):
        """Creating settings via pending session should preserve configured STT default."""
        monkeypatch.setattr("koro.core.state.VOICE_STT_LANGUAGE_DEFAULT", "pl")

        await state_manager.set_pending_session_name("12345", "project-x")
        settings = await state_manager.get_settings("12345")

        assert settings.stt_language == "pl"

    @pytest.mark.asyncio
    async def test_get_sessions(self, state_manager):
        """get_sessions returns all sessions for user."""
        await state_manager.create_session("12345")
        await state_manager.create_session("12345")
        await state_manager.create_session("12345")

        sessions = await state_manager.get_sessions("12345")

        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_get_settings_async(self, state_manager):
        """get_settings returns UserSettings object."""
        settings = await state_manager.get_settings("12345")

        assert settings.audio_enabled is True
        assert settings.mode.value == "go_all"
        assert settings.model == ""
        assert settings.stt_language == "auto"

    @pytest.mark.asyncio
    async def test_update_settings_async(self, state_manager):
        """update_settings updates and returns UserSettings."""
        settings = await state_manager.update_settings("12345", audio_enabled=False)

        assert settings.audio_enabled is False

    @pytest.mark.asyncio
    async def test_update_settings_rejects_invalid_stt_language(self, state_manager):
        """Invalid STT language code is rejected."""
        with pytest.raises(ValueError):
            await state_manager.update_settings("12345", stt_language="bad/code")

    @pytest.mark.asyncio
    async def test_update_settings_rejects_non_string_stt_language(self, state_manager):
        """Non-string STT language values are rejected explicitly."""
        with pytest.raises(ValueError, match="stt_language must be a string"):
            await state_manager.update_settings("12345", stt_language=123)


class TestStateManagerConcurrency:
    """Tests for StateManager thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_session_updates_no_corruption(self, state_manager):
        """Concurrent updates should not corrupt state."""

        async def update_session(user_id, session_id):
            await state_manager.update_session(str(user_id), session_id)

        # Run 50 concurrent updates
        tasks = [update_session(i, f"session_{i}") for i in range(50)]
        await asyncio.gather(*tasks)

        # Verify all sessions exist
        for i in range(50):
            state = await state_manager.get_session_state(str(i))
            assert state.current_session_id == f"session_{i}"


class TestSessionListLimits:
    """Tests for session list size limits."""

    @pytest.mark.asyncio
    async def test_session_list_pruned_at_limit(self, state_manager):
        """Session list should be pruned when exceeding MAX_SESSIONS."""
        # Add more sessions than the limit
        for i in range(MAX_SESSIONS + 20):
            await state_manager.update_session("12345", f"session_{i}")

        state = await state_manager.get_session_state("12345")
        assert len(state.sessions) == MAX_SESSIONS
        # Oldest sessions should be removed (FIFO)
        session_ids = [session.id for session in state.sessions]
        assert "session_0" not in session_ids
        assert f"session_{MAX_SESSIONS + 19}" in session_ids


class TestMemoryOperations:
    """Tests for memory storage operations."""

    @pytest.mark.asyncio
    async def test_store_and_recall_memory(self, state_manager):
        """store_memory and recall_memory work correctly."""
        await state_manager.store_memory("12345", "favorite_color", "blue")
        value = await state_manager.recall_memory("12345", "favorite_color")

        assert value == "blue"

    @pytest.mark.asyncio
    async def test_recall_nonexistent_memory(self, state_manager):
        """recall_memory returns None for nonexistent key."""
        value = await state_manager.recall_memory("12345", "nonexistent")

        assert value is None

    @pytest.mark.asyncio
    async def test_list_memories(self, state_manager):
        """list_memories returns all memory keys for user."""
        await state_manager.store_memory("12345", "key1", "value1")
        await state_manager.store_memory("12345", "key2", "value2")

        keys = await state_manager.list_memories("12345")

        assert "key1" in keys
        assert "key2" in keys

    @pytest.mark.asyncio
    async def test_store_memory_updates_existing(self, state_manager):
        """store_memory updates existing key."""
        await state_manager.store_memory("12345", "key", "original")
        await state_manager.store_memory("12345", "key", "updated")

        value = await state_manager.recall_memory("12345", "key")
        assert value == "updated"
