"""Tests for koro.state module."""

import pytest

from koro.state import MAX_SESSIONS, StateManager


class TestStateManager:
    """Tests for StateManager class."""

    def test_init_with_default_path(self, tmp_path):
        """StateManager uses provided db_path."""
        db_file = tmp_path / "test.db"
        manager = StateManager(db_path=db_file)

        assert manager.db_path == db_file
        assert db_file.exists()

    def test_get_user_state_creates_default(self, tmp_path):
        """get_user_state creates default state for new user."""
        manager = StateManager(db_path=tmp_path / "test.db")

        state = manager.get_user_state(99999)

        assert state["current_session"] is None
        assert state["sessions"] == []

    def test_get_user_settings_creates_defaults(self, tmp_path):
        """get_user_settings creates default settings for new user."""
        manager = StateManager(db_path=tmp_path / "test.db")

        settings = manager.get_user_settings(99999)

        assert settings["audio_enabled"] is True
        assert settings["mode"] == "go_all"
        assert settings["watch_enabled"] is False
        assert "voice_speed" in settings

    def test_update_setting_saves(self, tmp_path):
        """update_setting updates and saves settings."""
        manager = StateManager(db_path=tmp_path / "test.db")

        manager.update_setting(12345, "audio_enabled", False)

        settings = manager.get_user_settings(12345)
        assert settings["audio_enabled"] is False

    def test_update_setting_mode(self, tmp_path):
        """update_setting can update mode."""
        manager = StateManager(db_path=tmp_path / "test.db")

        manager.update_setting(12345, "mode", "approve")

        settings = manager.get_user_settings(12345)
        assert settings["mode"] == "approve"

    def test_update_setting_voice_speed(self, tmp_path):
        """update_setting can update voice_speed."""
        manager = StateManager(db_path=tmp_path / "test.db")

        manager.update_setting(12345, "voice_speed", 0.9)

        settings = manager.get_user_settings(12345)
        assert settings["voice_speed"] == 0.9

    def test_update_setting_watch_enabled(self, tmp_path):
        """update_setting can update watch_enabled."""
        manager = StateManager(db_path=tmp_path / "test.db")

        manager.update_setting(12345, "watch_enabled", True)

        settings = manager.get_user_settings(12345)
        assert settings["watch_enabled"] is True

    def test_settings_persist_after_recreation(self, tmp_path):
        """Settings persist across StateManager instances."""
        db_file = tmp_path / "test.db"

        manager1 = StateManager(db_path=db_file)
        manager1.update_setting(12345, "audio_enabled", False)
        manager1.update_setting(12345, "mode", "approve")

        # Create new instance with same db
        manager2 = StateManager(db_path=db_file)
        settings = manager2.get_user_settings(12345)

        assert settings["audio_enabled"] is False
        assert settings["mode"] == "approve"


class TestStateManagerAsync:
    """Tests for async StateManager methods."""

    @pytest.mark.asyncio
    async def test_update_session_sets_current(self, tmp_path):
        """update_session sets current session and adds to list."""
        manager = StateManager(db_path=tmp_path / "test.db")

        await manager.update_session("12345", "new_session_xyz")

        state = manager.get_user_state(12345)
        assert state["current_session"] == "new_session_xyz"
        assert "new_session_xyz" in state["sessions"]

    @pytest.mark.asyncio
    async def test_update_session_no_duplicate(self, tmp_path):
        """update_session doesn't add duplicate session IDs."""
        manager = StateManager(db_path=tmp_path / "test.db")

        await manager.update_session("12345", "abc")
        await manager.update_session("12345", "abc")

        state = manager.get_user_state(12345)
        assert state["sessions"].count("abc") == 1

    @pytest.mark.asyncio
    async def test_create_session(self, tmp_path):
        """create_session creates a new session."""
        manager = StateManager(db_path=tmp_path / "test.db")

        session = await manager.create_session("12345")

        assert session.id is not None
        assert session.user_id == "12345"
        state = manager.get_user_state(12345)
        assert state["current_session"] == session.id

    @pytest.mark.asyncio
    async def test_get_current_session(self, tmp_path):
        """get_current_session returns the current session."""
        manager = StateManager(db_path=tmp_path / "test.db")

        created = await manager.create_session("12345")
        current = await manager.get_current_session("12345")

        assert current is not None
        assert current.id == created.id

    @pytest.mark.asyncio
    async def test_get_current_session_none_for_new_user(self, tmp_path):
        """get_current_session returns None for user without sessions."""
        manager = StateManager(db_path=tmp_path / "test.db")

        current = await manager.get_current_session("99999")

        assert current is None

    @pytest.mark.asyncio
    async def test_clear_current_session(self, tmp_path):
        """clear_current_session removes current session."""
        manager = StateManager(db_path=tmp_path / "test.db")

        await manager.create_session("12345")
        await manager.clear_current_session("12345")

        current = await manager.get_current_session("12345")
        assert current is None
        # But session should still exist in the list
        state = manager.get_user_state(12345)
        assert len(state["sessions"]) == 1

    @pytest.mark.asyncio
    async def test_set_current_session(self, tmp_path):
        """set_current_session switches to existing session."""
        manager = StateManager(db_path=tmp_path / "test.db")

        session1 = await manager.create_session("12345")
        await manager.create_session("12345")  # Create second session

        await manager.set_current_session("12345", session1.id)

        current = await manager.get_current_session("12345")
        assert current.id == session1.id

    @pytest.mark.asyncio
    async def test_get_sessions(self, tmp_path):
        """get_sessions returns all sessions for user."""
        manager = StateManager(db_path=tmp_path / "test.db")

        await manager.create_session("12345")
        await manager.create_session("12345")
        await manager.create_session("12345")

        sessions = await manager.get_sessions("12345")

        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_get_settings_async(self, tmp_path):
        """get_settings returns UserSettings object."""
        manager = StateManager(db_path=tmp_path / "test.db")

        settings = await manager.get_settings("12345")

        assert settings.audio_enabled is True
        assert settings.mode.value == "go_all"

    @pytest.mark.asyncio
    async def test_update_settings_async(self, tmp_path):
        """update_settings updates and returns UserSettings."""
        manager = StateManager(db_path=tmp_path / "test.db")

        settings = await manager.update_settings("12345", audio_enabled=False)

        assert settings.audio_enabled is False


class TestStateManagerConcurrency:
    """Tests for StateManager thread safety."""

    @pytest.mark.asyncio
    async def test_concurrent_session_updates_no_corruption(self, tmp_path):
        """Concurrent updates should not corrupt state."""
        import asyncio

        manager = StateManager(db_path=tmp_path / "test.db")

        async def update_session(user_id, session_id):
            await manager.update_session(str(user_id), session_id)

        # Run 50 concurrent updates
        tasks = [update_session(i, f"session_{i}") for i in range(50)]
        await asyncio.gather(*tasks)

        # Verify all sessions exist
        for i in range(50):
            state = manager.get_user_state(i)
            assert state["current_session"] == f"session_{i}"


class TestSessionListLimits:
    """Tests for session list size limits."""

    @pytest.mark.asyncio
    async def test_session_list_pruned_at_limit(self, tmp_path):
        """Session list should be pruned when exceeding MAX_SESSIONS."""
        manager = StateManager(db_path=tmp_path / "test.db")

        # Add more sessions than the limit
        for i in range(MAX_SESSIONS + 20):
            await manager.update_session("12345", f"session_{i}")

        state = manager.get_user_state(12345)
        assert len(state["sessions"]) == MAX_SESSIONS
        # Oldest sessions should be removed (FIFO)
        assert "session_0" not in state["sessions"]
        assert f"session_{MAX_SESSIONS + 19}" in state["sessions"]


class TestMemoryOperations:
    """Tests for memory storage operations."""

    @pytest.mark.asyncio
    async def test_store_and_recall_memory(self, tmp_path):
        """store_memory and recall_memory work correctly."""
        manager = StateManager(db_path=tmp_path / "test.db")

        await manager.store_memory("12345", "favorite_color", "blue")
        value = await manager.recall_memory("12345", "favorite_color")

        assert value == "blue"

    @pytest.mark.asyncio
    async def test_recall_nonexistent_memory(self, tmp_path):
        """recall_memory returns None for nonexistent key."""
        manager = StateManager(db_path=tmp_path / "test.db")

        value = await manager.recall_memory("12345", "nonexistent")

        assert value is None

    @pytest.mark.asyncio
    async def test_list_memories(self, tmp_path):
        """list_memories returns all memory keys for user."""
        manager = StateManager(db_path=tmp_path / "test.db")

        await manager.store_memory("12345", "key1", "value1")
        await manager.store_memory("12345", "key2", "value2")

        keys = await manager.list_memories("12345")

        assert "key1" in keys
        assert "key2" in keys

    @pytest.mark.asyncio
    async def test_store_memory_updates_existing(self, tmp_path):
        """store_memory updates existing key."""
        manager = StateManager(db_path=tmp_path / "test.db")

        await manager.store_memory("12345", "key", "original")
        await manager.store_memory("12345", "key", "updated")

        value = await manager.recall_memory("12345", "key")
        assert value == "updated"
