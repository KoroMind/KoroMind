"""State management for KoroMind sessions and settings.

This module provides a facade over the storage repositories, adding
business logic like FIFO eviction, default values, and legacy JSON migration.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from koro.core.config import (
    DATABASE_PATH,
    SETTINGS_FILE,
    STATE_FILE,
    VOICE_SETTINGS,
)
from koro.core.types import Mode, Session, UserSettings
from koro.storage.db import get_connection, init_db
from koro.storage.repos.sessions_repo import SessionsRepo
from koro.storage.repos.settings_repo import SettingsRepo

logger = logging.getLogger(__name__)

# Maximum sessions to retain per user
MAX_SESSIONS = 10


class StateManager:
    """Manages user sessions and settings with SQLite persistence."""

    def __init__(self, db_path: Path | str | None = None):
        """
        Initialize state manager.

        Args:
            db_path: Path to SQLite database (defaults to ~/.koromind/db/koromind.db)
        """
        self._using_custom_path = db_path is not None
        self.db_path = Path(db_path) if db_path else DATABASE_PATH

        # Initialize database with migrations
        init_db(self.db_path)

        # Only migrate from global JSON files when using default path
        if not self._using_custom_path:
            self._migrate_from_json()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with row factory."""
        with get_connection(self.db_path) as conn:
            yield conn

    def _migrate_from_json(self) -> None:
        """Migrate data from legacy JSON files if not already done."""
        with self._get_connection() as conn:
            # Check if migration was already done
            result = conn.execute(
                "SELECT 1 FROM migration_status WHERE name = 'json_migration'"
            ).fetchone()
            if result:
                return

            migration_failed = False

            # Migrate sessions from JSON
            if STATE_FILE.exists():
                try:
                    with open(STATE_FILE) as f:
                        sessions_data = json.load(f)
                    for user_id, user_state in sessions_data.items():
                        current_session = user_state.get("current_session")
                        sessions = user_state.get("sessions", [])
                        now = datetime.now().isoformat()
                        for session_id in sessions:
                            is_current = 1 if session_id == current_session else 0
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO sessions
                                (id, user_id, created_at, last_active, is_current)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (session_id, user_id, now, now, is_current),
                            )
                except (json.JSONDecodeError, IOError):
                    logger.warning(
                        "Failed to migrate sessions from %s",
                        STATE_FILE,
                        exc_info=True,
                    )
                    migration_failed = True

            # Migrate settings from JSON
            if SETTINGS_FILE.exists():
                try:
                    with open(SETTINGS_FILE) as f:
                        settings_data = json.load(f)
                    for user_id, user_settings in settings_data.items():
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO settings
                            (user_id, mode, audio_enabled, voice_speed, watch_enabled)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                user_id,
                                user_settings.get("mode", "go_all"),
                                1 if user_settings.get("audio_enabled", True) else 0,
                                user_settings.get(
                                    "voice_speed", VOICE_SETTINGS["speed"]
                                ),
                                1 if user_settings.get("watch_enabled", False) else 0,
                            ),
                        )
                except (json.JSONDecodeError, IOError):
                    logger.warning(
                        "Failed to migrate settings from %s",
                        SETTINGS_FILE,
                        exc_info=True,
                    )
                    migration_failed = True

            if migration_failed:
                return

            # Mark migration as complete
            conn.execute(
                "INSERT INTO migration_status (name, completed_at) VALUES (?, ?)",
                ("json_migration", datetime.now().isoformat()),
            )

    # Session Management

    async def get_sessions(self, user_id: str) -> list[Session]:
        """Get all sessions for a user, ordered by last_active descending."""
        with self._get_connection() as conn:
            repo = SessionsRepo(conn)
            return repo.get_all(user_id)

    async def create_session(self, user_id: str) -> Session:
        """Create a new session for a user."""
        with self._get_connection() as conn:
            repo = SessionsRepo(conn)
            session = repo.create(user_id)
            # FIFO eviction
            repo.evict_oldest(user_id, MAX_SESSIONS)
            return session

    async def get_current_session(self, user_id: str) -> Session | None:
        """Get the current session for a user."""
        with self._get_connection() as conn:
            repo = SessionsRepo(conn)
            return repo.get_current(user_id)

    async def set_current_session(self, user_id: str, session_id: str) -> None:
        """Set the current session for a user."""
        with self._get_connection() as conn:
            repo = SessionsRepo(conn)
            repo.set_current(user_id, session_id)

    async def clear_current_session(self, user_id: str) -> None:
        """Clear the current session for a user (for /new command)."""
        with self._get_connection() as conn:
            repo = SessionsRepo(conn)
            repo.clear_current(user_id)

    async def update_session(self, user_id: str, session_id: str) -> None:
        """
        Update or create a session as current.

        This maintains backward compatibility with the old API.
        """
        if not session_id:
            return

        with self._get_connection() as conn:
            repo = SessionsRepo(conn)
            repo.update_or_create(user_id, session_id)
            # FIFO eviction
            repo.evict_oldest(user_id, MAX_SESSIONS)

    # Settings Management

    async def get_settings(self, user_id: str) -> UserSettings:
        """Get settings for a user, creating defaults if not exists."""
        with self._get_connection() as conn:
            repo = SettingsRepo(conn)
            return repo.get_or_create(user_id)

    async def update_settings(self, user_id: str, **kwargs) -> UserSettings:
        """Update settings for a user."""
        # Get current settings first
        current = await self.get_settings(user_id)

        # Apply updates
        if "mode" in kwargs:
            mode_val = kwargs["mode"]
            current.mode = mode_val if isinstance(mode_val, Mode) else Mode(mode_val)
        if "audio_enabled" in kwargs:
            current.audio_enabled = kwargs["audio_enabled"]
        if "voice_speed" in kwargs:
            current.voice_speed = kwargs["voice_speed"]
        if "watch_enabled" in kwargs:
            current.watch_enabled = kwargs["watch_enabled"]

        # Save to database
        with self._get_connection() as conn:
            repo = SettingsRepo(conn)
            repo.update(user_id, current)

        return current

    # Memory Management (for future long-term memory features)

    async def store_memory(self, user_id: str, key: str, value: str) -> None:
        """Store a memory entry for a user."""
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO memory (user_id, key, value, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (user_id, key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (user_id, key, value, now, now),
            )

    async def recall_memory(self, user_id: str, key: str) -> str | None:
        """Recall a memory entry for a user."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM memory WHERE user_id = ? AND key = ?",
                (user_id, key),
            ).fetchone()
            return row["value"] if row else None

    async def list_memories(self, user_id: str) -> list[str]:
        """List all memory keys for a user."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT key FROM memory WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
            return [row["key"] for row in rows]

    # Backward Compatibility Methods

    def get_user_state(self, user_id: int) -> dict:
        """
        Get user session state in legacy format.

        Deprecated: Use async methods instead.
        """
        user_id_str = str(user_id)
        with self._get_connection() as conn:
            # Get current session
            current_row = conn.execute(
                "SELECT id FROM sessions WHERE user_id = ? AND is_current = 1",
                (user_id_str,),
            ).fetchone()

            # Get all sessions
            session_rows = conn.execute(
                "SELECT id FROM sessions WHERE user_id = ? ORDER BY last_active DESC",
                (user_id_str,),
            ).fetchall()

            return {
                "current_session": current_row["id"] if current_row else None,
                "sessions": [row["id"] for row in session_rows],
            }

    def get_user_settings(self, user_id: int) -> dict:
        """
        Get user settings in legacy format.

        Deprecated: Use async get_settings instead.
        """
        user_id_str = str(user_id)
        with self._get_connection() as conn:
            repo = SettingsRepo(conn)
            return repo.get_as_dict(user_id_str)

    def update_setting(self, user_id: int, key: str, value) -> None:
        """
        Update a single setting.

        Deprecated: Use async update_settings instead.
        """
        user_id_str = str(user_id)

        with self._get_connection() as conn:
            repo = SettingsRepo(conn)
            # Ensure user has settings row (creates with defaults if not exists)
            repo.get_or_create(user_id_str)
            # Now update the specific field
            repo.update_field(user_id_str, key, value)


# Default instance
_state_manager: StateManager | None = None


def get_state_manager() -> StateManager:
    """Get or create the default state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager


def set_state_manager(manager: StateManager) -> None:
    """Set the default state manager instance (for testing)."""
    global _state_manager
    _state_manager = manager
