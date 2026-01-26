"""Tests for koro.state module."""

import json

from koro.state import StateManager


class TestStateManager:
    """Tests for StateManager class."""

    def test_init_with_custom_paths(self, tmp_path):
        """StateManager accepts custom file paths."""
        state_file = tmp_path / "state.json"
        settings_file = tmp_path / "settings.json"

        manager = StateManager(state_file=state_file, settings_file=settings_file)

        assert manager.state_file == state_file
        assert manager.settings_file == settings_file

    def test_load_sessions_empty_when_missing(self, tmp_path):
        """load_sessions returns empty dict when file missing."""
        manager = StateManager(
            state_file=tmp_path / "missing.json",
            settings_file=tmp_path / "settings.json"
        )
        manager.load_sessions()

        assert manager.sessions == {}

    def test_load_sessions_from_file(self, tmp_path, sample_state):
        """load_sessions reads existing file."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(sample_state))

        manager = StateManager(
            state_file=state_file,
            settings_file=tmp_path / "settings.json"
        )
        manager.load_sessions()

        assert manager.sessions == sample_state

    def test_save_sessions_creates_file(self, tmp_path):
        """save_sessions creates file with data."""
        state_file = tmp_path / "state.json"

        manager = StateManager(
            state_file=state_file,
            settings_file=tmp_path / "settings.json"
        )
        manager.sessions = {"user1": {"current_session": "abc", "sessions": ["abc"]}}
        manager.save_sessions()

        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["user1"]["current_session"] == "abc"

    def test_load_settings_empty_when_missing(self, tmp_path):
        """load_settings returns empty dict when file missing."""
        manager = StateManager(
            state_file=tmp_path / "state.json",
            settings_file=tmp_path / "missing.json"
        )
        manager.load_settings()

        assert manager.settings == {}

    def test_load_settings_from_file(self, tmp_path, sample_settings):
        """load_settings reads existing file."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps(sample_settings))

        manager = StateManager(
            state_file=tmp_path / "state.json",
            settings_file=settings_file
        )
        manager.load_settings()

        assert manager.settings == sample_settings

    def test_get_user_state_creates_default(self, tmp_path):
        """get_user_state creates default state for new user."""
        manager = StateManager(
            state_file=tmp_path / "state.json",
            settings_file=tmp_path / "settings.json"
        )

        state = manager.get_user_state(99999)

        assert state["current_session"] is None
        assert state["sessions"] == []

    def test_get_user_state_returns_existing(self, tmp_path, sample_state):
        """get_user_state returns existing state."""
        manager = StateManager(
            state_file=tmp_path / "state.json",
            settings_file=tmp_path / "settings.json"
        )
        manager.sessions = sample_state

        state = manager.get_user_state(12345)

        assert state["current_session"] == "session_abc123"
        assert len(state["sessions"]) == 2

    def test_get_user_settings_creates_defaults(self, tmp_path):
        """get_user_settings creates default settings for new user."""
        manager = StateManager(
            state_file=tmp_path / "state.json",
            settings_file=tmp_path / "settings.json"
        )

        settings = manager.get_user_settings(99999)

        assert settings["audio_enabled"] is True
        assert settings["mode"] == "go_all"
        assert settings["watch_enabled"] is False
        assert "voice_speed" in settings

    def test_get_user_settings_adds_missing_keys(self, tmp_path):
        """get_user_settings adds missing keys to existing settings."""
        manager = StateManager(
            state_file=tmp_path / "state.json",
            settings_file=tmp_path / "settings.json"
        )
        # Old settings without new keys
        manager.settings = {"12345": {"audio_enabled": False, "voice_speed": 0.9}}

        settings = manager.get_user_settings(12345)

        # Old values preserved
        assert settings["audio_enabled"] is False
        assert settings["voice_speed"] == 0.9
        # New keys added
        assert settings["mode"] == "go_all"
        assert settings["watch_enabled"] is False

    def test_update_session_sets_current(self, tmp_path):
        """update_session sets current session and adds to list."""
        state_file = tmp_path / "state.json"
        manager = StateManager(
            state_file=state_file,
            settings_file=tmp_path / "settings.json"
        )

        manager.update_session(12345, "new_session_xyz")

        state = manager.get_user_state(12345)
        assert state["current_session"] == "new_session_xyz"
        assert "new_session_xyz" in state["sessions"]
        # Verify saved to disk
        assert state_file.exists()

    def test_update_session_no_duplicate(self, tmp_path):
        """update_session doesn't add duplicate session IDs."""
        manager = StateManager(
            state_file=tmp_path / "state.json",
            settings_file=tmp_path / "settings.json"
        )
        manager.sessions = {"12345": {"current_session": "abc", "sessions": ["abc"]}}

        manager.update_session(12345, "abc")

        state = manager.get_user_state(12345)
        assert state["sessions"].count("abc") == 1

    def test_update_setting_saves(self, tmp_path):
        """update_setting updates and saves settings."""
        settings_file = tmp_path / "settings.json"
        manager = StateManager(
            state_file=tmp_path / "state.json",
            settings_file=settings_file
        )

        manager.update_setting(12345, "audio_enabled", False)

        settings = manager.get_user_settings(12345)
        assert settings["audio_enabled"] is False
        # Verify saved
        assert settings_file.exists()

    def test_load_both(self, tmp_path, sample_state, sample_settings):
        """load() loads both sessions and settings."""
        state_file = tmp_path / "state.json"
        settings_file = tmp_path / "settings.json"
        state_file.write_text(json.dumps(sample_state))
        settings_file.write_text(json.dumps(sample_settings))

        manager = StateManager(state_file=state_file, settings_file=settings_file)
        manager.load()

        assert manager.sessions == sample_state
        assert manager.settings == sample_settings
