"""Session and settings state management."""

import fcntl
import json
from pathlib import Path
from typing import Any

from .config import SETTINGS_FILE, STATE_FILE, VOICE_SETTINGS

# Maximum number of sessions to keep per user (FIFO eviction)
MAX_SESSIONS = 100


class StateManager:
    """Manages user sessions and settings persistence."""

    def __init__(self, state_file: Path = None, settings_file: Path = None):
        """
        Initialize state manager.

        Args:
            state_file: Path to sessions state file
            settings_file: Path to user settings file
        """
        self.state_file = state_file or STATE_FILE
        self.settings_file = settings_file or SETTINGS_FILE
        self.sessions: dict[str, dict] = {}
        self.settings: dict[str, dict] = {}

    def load(self) -> None:
        """Load both sessions and settings from disk."""
        self.load_sessions()
        self.load_settings()

    def load_sessions(self) -> None:
        """Load session state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    self.sessions = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.sessions = {}

    def save_sessions(self) -> None:
        """Save session state to file with file locking."""
        with open(self.state_file, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(self.sessions, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def load_settings(self) -> None:
        """Load user settings from file."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file) as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.settings = {}

    def save_settings(self) -> None:
        """Save user settings to file with file locking."""
        with open(self.settings_file, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(self.settings, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def get_user_state(self, user_id: int) -> dict:
        """
        Get or create user session state.

        Args:
            user_id: Telegram user ID

        Returns:
            User state dict with 'current_session' and 'sessions' keys
        """
        user_id_str = str(user_id)
        if user_id_str not in self.sessions:
            self.sessions[user_id_str] = {"current_session": None, "sessions": []}
        return self.sessions[user_id_str]

    def get_user_settings(self, user_id: int) -> dict:
        """
        Get or create user settings with defaults.

        Args:
            user_id: Telegram user ID

        Returns:
            User settings dict
        """
        user_id_str = str(user_id)
        if user_id_str not in self.settings:
            self.settings[user_id_str] = {
                "audio_enabled": True,
                "voice_speed": VOICE_SETTINGS["speed"],
                "mode": "go_all",
                "watch_enabled": False,
            }
        else:
            # Ensure new settings exist for existing users
            defaults = {
                "mode": "go_all",
                "watch_enabled": False,
            }
            for key, value in defaults.items():
                if key not in self.settings[user_id_str]:
                    self.settings[user_id_str][key] = value
        return self.settings[user_id_str]

    def update_session(self, user_id: int, session_id: str) -> None:
        """
        Update user's current session.

        Args:
            user_id: Telegram user ID
            session_id: New session ID
        """
        state = self.get_user_state(user_id)
        if session_id and session_id != state["current_session"]:
            state["current_session"] = session_id
            if session_id not in state["sessions"]:
                state["sessions"].append(session_id)
                # FIFO eviction: remove oldest sessions if exceeding limit
                while len(state["sessions"]) > MAX_SESSIONS:
                    state["sessions"].pop(0)
            self.save_sessions()

    def update_setting(self, user_id: int, key: str, value: Any) -> None:
        """
        Update a user setting.

        Args:
            user_id: Telegram user ID
            key: Setting key
            value: New value
        """
        settings = self.get_user_settings(user_id)
        settings[key] = value
        self.save_settings()


# Default instance
_state_manager: StateManager | None = None


def get_state_manager() -> StateManager:
    """Get or create the default state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
        _state_manager.load()
    return _state_manager


def set_state_manager(manager: StateManager) -> None:
    """Set the default state manager instance (for testing)."""
    global _state_manager
    _state_manager = manager
