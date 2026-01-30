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

    def test_get_user_state_creates_default(self, state_manager):
        """get_user_state creates default state for new user."""
        state = state_manager.get_user_state(99999)

        assert state["current_session"] is None
        assert state["sessions"] == []

    def test_get_user_settings_creates_defaults(self, state_manager):
        """get_user_settings creates default settings for new user."""
        settings = state_manager.get_user_settings(99999)

        assert settings["audio_enabled"] is True
        assert settings["mode"] == "go_all"
        assert settings["watch_enabled"] is False
        assert "voice_speed" in settings

    @pytest.mark.parametrize(
        "key,value,expected_key,expected_value",
        [
            ("audio_enabled", False, "audio_enabled", False),
            ("mode", "approve", "mode", "approve"),
            ("voice_speed", 0.9, "voice_speed", 0.9),
            ("watch_enabled", True, "watch_enabled", True),
        ],
    )
    def test_update_setting_saves(
        self, state_manager, key, value, expected_key, expected_value
    ):
        """update_setting updates and saves settings."""
        state_manager.update_setting(12345, key, value)

        settings = state_manager.get_user_settings(12345)
        assert settings[expected_key] == expected_value

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
    async def test_update_session_sets_current(self, state_manager):
        """update_session sets current session and adds to list."""
        await state_manager.update_session("12345", "new_session_xyz")

        state = state_manager.get_user_state(12345)
        assert state["current_session"] == "new_session_xyz"
        assert "new_session_xyz" in state["sessions"]

    @pytest.mark.asyncio
    async def test_update_session_no_duplicate(self, state_manager):
        """update_session doesn't add duplicate session IDs."""
        await state_manager.update_session("12345", "abc")
        await state_manager.update_session("12345", "abc")

        state = state_manager.get_user_state(12345)
        assert state["sessions"].count("abc") == 1

    @pytest.mark.asyncio
    async def test_create_session(self, state_manager):
        """create_session creates a new session."""
        session = await state_manager.create_session("12345")

        assert session.id is not None
        assert session.user_id == "12345"
        state = state_manager.get_user_state(12345)
        assert state["current_session"] == session.id

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
        state = state_manager.get_user_state(12345)
        assert len(state["sessions"]) == 1

    @pytest.mark.asyncio
    async def test_set_current_session(self, state_manager):
        """set_current_session switches to existing session."""
        session1 = await state_manager.create_session("12345")
        await state_manager.create_session("12345")  # Create second session

        await state_manager.set_current_session("12345", session1.id)

        current = await state_manager.get_current_session("12345")
        assert current.id == session1.id

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

    @pytest.mark.asyncio
    async def test_update_settings_async(self, state_manager):
        """update_settings updates and returns UserSettings."""
        settings = await state_manager.update_settings("12345", audio_enabled=False)

        assert settings.audio_enabled is False


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
            state = state_manager.get_user_state(i)
            assert state["current_session"] == f"session_{i}"


class TestSessionListLimits:
    """Tests for session list size limits."""

    @pytest.mark.asyncio
    async def test_session_list_pruned_at_limit(self, state_manager):
        """Session list should be pruned when exceeding MAX_SESSIONS."""
        # Add more sessions than the limit
        for i in range(MAX_SESSIONS + 20):
            await state_manager.update_session("12345", f"session_{i}")

        state = state_manager.get_user_state(12345)
        assert len(state["sessions"]) == MAX_SESSIONS
        # Oldest sessions should be removed (FIFO)
        assert "session_0" not in state["sessions"]
        assert f"session_{MAX_SESSIONS + 19}" in state["sessions"]


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


class TestSDKConfig:
    """Tests for SDK configuration storage."""

    @pytest.mark.asyncio
    async def test_get_sdk_config_creates_default(self, state_manager):
        """get_sdk_config creates default config for new user."""
        config = await state_manager.get_sdk_config("12345")

        assert config.permission_mode == "default"
        assert config.mcp_servers == []
        assert config.agents == {}
        assert "Read" in config.allowed_tools
        assert "Bash" in config.allowed_tools
        assert config.disallowed_tools == []

    @pytest.mark.asyncio
    async def test_get_sdk_config_persists(self, state_manager):
        """get_sdk_config returns same config on subsequent calls."""
        config1 = await state_manager.get_sdk_config("12345")
        config2 = await state_manager.get_sdk_config("12345")

        assert config1.to_dict() == config2.to_dict()

    @pytest.mark.asyncio
    async def test_update_sdk_config(self, state_manager):
        """update_sdk_config updates specific fields."""
        await state_manager.get_sdk_config("12345")  # Create default

        updated = await state_manager.update_sdk_config(
            "12345",
            permission_mode="acceptEdits",
            model="claude-sonnet-4-20250514",
        )

        assert updated.permission_mode == "acceptEdits"
        assert updated.model == "claude-sonnet-4-20250514"

        # Verify persisted
        config = await state_manager.get_sdk_config("12345")
        assert config.permission_mode == "acceptEdits"
        assert config.model == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_update_sdk_config_preserves_other_fields(self, state_manager):
        """update_sdk_config preserves fields not being updated."""
        await state_manager.update_sdk_config(
            "12345",
            permission_mode="plan",
            model="test-model",
        )

        await state_manager.update_sdk_config(
            "12345",
            permission_mode="default",
        )

        config = await state_manager.get_sdk_config("12345")
        assert config.permission_mode == "default"
        assert config.model == "test-model"  # Should be preserved

    @pytest.mark.asyncio
    async def test_add_mcp_server(self, state_manager):
        """add_mcp_server adds a server to config."""
        server = {
            "name": "test-server",
            "type": "stdio",
            "command": "test-cmd",
            "args": ["--flag"],
        }

        await state_manager.add_mcp_server("12345", server)

        servers = await state_manager.get_mcp_servers("12345")
        assert len(servers) == 1
        assert servers[0]["name"] == "test-server"
        assert servers[0]["command"] == "test-cmd"

    @pytest.mark.asyncio
    async def test_add_mcp_server_replaces_same_name(self, state_manager):
        """add_mcp_server replaces server with same name."""
        server1 = {"name": "test", "type": "stdio", "command": "cmd1"}
        server2 = {"name": "test", "type": "stdio", "command": "cmd2"}

        await state_manager.add_mcp_server("12345", server1)
        await state_manager.add_mcp_server("12345", server2)

        servers = await state_manager.get_mcp_servers("12345")
        assert len(servers) == 1
        assert servers[0]["command"] == "cmd2"

    @pytest.mark.asyncio
    async def test_remove_mcp_server(self, state_manager):
        """remove_mcp_server removes a server by name."""
        await state_manager.add_mcp_server("12345", {"name": "server1", "type": "stdio", "command": "cmd1"})
        await state_manager.add_mcp_server("12345", {"name": "server2", "type": "stdio", "command": "cmd2"})

        result = await state_manager.remove_mcp_server("12345", "server1")

        assert result is True
        servers = await state_manager.get_mcp_servers("12345")
        assert len(servers) == 1
        assert servers[0]["name"] == "server2"

    @pytest.mark.asyncio
    async def test_remove_mcp_server_nonexistent(self, state_manager):
        """remove_mcp_server returns False for nonexistent server."""
        result = await state_manager.remove_mcp_server("12345", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_add_agent(self, state_manager):
        """add_agent adds a custom agent."""
        definition = {
            "description": "Test agent",
            "prompt": "You are a test agent",
            "tools": ["Read", "Write"],
        }

        await state_manager.add_agent("12345", "test-agent", definition)

        agents = await state_manager.get_agents("12345")
        assert "test-agent" in agents
        assert agents["test-agent"]["description"] == "Test agent"

    @pytest.mark.asyncio
    async def test_add_agent_replaces_same_name(self, state_manager):
        """add_agent replaces agent with same name."""
        await state_manager.add_agent("12345", "agent", {"description": "Old"})
        await state_manager.add_agent("12345", "agent", {"description": "New"})

        agents = await state_manager.get_agents("12345")
        assert agents["agent"]["description"] == "New"

    @pytest.mark.asyncio
    async def test_remove_agent(self, state_manager):
        """remove_agent removes an agent by name."""
        await state_manager.add_agent("12345", "agent1", {"description": "Agent 1"})
        await state_manager.add_agent("12345", "agent2", {"description": "Agent 2"})

        result = await state_manager.remove_agent("12345", "agent1")

        assert result is True
        agents = await state_manager.get_agents("12345")
        assert "agent1" not in agents
        assert "agent2" in agents

    @pytest.mark.asyncio
    async def test_remove_agent_nonexistent(self, state_manager):
        """remove_agent returns False for nonexistent agent."""
        result = await state_manager.remove_agent("12345", "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_sdk_config_persists_across_instances(self, tmp_path):
        """SDK config persists across StateManager instances."""
        db_file = tmp_path / "test.db"

        manager1 = StateManager(db_path=db_file)
        await manager1.update_sdk_config(
            "12345",
            permission_mode="bypassPermissions",
            model="test-model",
        )
        await manager1.add_mcp_server("12345", {"name": "server", "type": "stdio", "command": "cmd"})
        await manager1.add_agent("12345", "agent", {"description": "Test"})

        # Create new instance with same db
        manager2 = StateManager(db_path=db_file)
        config = await manager2.get_sdk_config("12345")

        assert config.permission_mode == "bypassPermissions"
        assert config.model == "test-model"
        assert len(config.mcp_servers) == 1
        assert "agent" in config.agents

    @pytest.mark.asyncio
    async def test_sdk_config_to_dict(self, state_manager):
        """SDKConfig.to_dict returns complete dictionary."""
        config = await state_manager.get_sdk_config("12345")
        d = config.to_dict()

        assert "mcp_servers" in d
        assert "agents" in d
        assert "permission_mode" in d
        assert "allowed_tools" in d
        assert "disallowed_tools" in d
        assert "sandbox_settings" in d
        assert "model" in d
        assert "working_dir" in d
