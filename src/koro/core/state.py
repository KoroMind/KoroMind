"""SQLite-backed state persistence for KoroMind."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator
from uuid import uuid4

from koro.core.config import DATABASE_PATH, SETTINGS_FILE, STATE_FILE, VOICE_SETTINGS
from koro.core.types import Mode, Session, UserSettings

# Maximum number of sessions to keep per user (FIFO eviction)
MAX_SESSIONS = 100


class StateManager:
    """Manages user sessions and settings with SQLite persistence."""

    def __init__(self, db_path: Path | str | None = None):
        """
        Initialize state manager.

        Args:
            db_path: Path to SQLite database (defaults to ~/.koromind/koromind.db)
        """
        self.db_path = Path(db_path) if db_path else DATABASE_PATH
        self._ensure_schema()
        self._migrate_from_json()

    def _ensure_schema(self) -> None:
        """Create database schema if not exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    is_current INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_user_id
                ON sessions(user_id);

                CREATE INDEX IF NOT EXISTS idx_sessions_user_current
                ON sessions(user_id, is_current);

                CREATE TABLE IF NOT EXISTS settings (
                    user_id TEXT PRIMARY KEY,
                    mode TEXT DEFAULT 'go_all',
                    audio_enabled INTEGER DEFAULT 1,
                    voice_speed REAL DEFAULT 1.1,
                    watch_enabled INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS memory (
                    user_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, key)
                );

                CREATE TABLE IF NOT EXISTS migration_status (
                    name TEXT PRIMARY KEY,
                    completed_at TEXT NOT NULL
                );
            """)

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _migrate_from_json(self) -> None:
        """Migrate data from legacy JSON files if not already done."""
        with self._get_connection() as conn:
            # Check if migration was already done
            result = conn.execute(
                "SELECT 1 FROM migration_status WHERE name = 'json_migration'"
            ).fetchone()
            if result:
                return

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
                    pass

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
                    pass

            # Mark migration as complete
            conn.execute(
                "INSERT INTO migration_status (name, completed_at) VALUES (?, ?)",
                ("json_migration", datetime.now().isoformat()),
            )

    # Session Management

    async def get_sessions(self, user_id: str) -> list[Session]:
        """Get all sessions for a user, ordered by last_active descending."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, created_at, last_active
                FROM sessions
                WHERE user_id = ?
                ORDER BY last_active DESC
                """,
                (user_id,),
            ).fetchall()
            return [
                Session(
                    id=row["id"],
                    user_id=row["user_id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    last_active=datetime.fromisoformat(row["last_active"]),
                )
                for row in rows
            ]

    async def create_session(self, user_id: str) -> Session:
        """Create a new session for a user."""
        now = datetime.now()
        session_id = str(uuid4())

        with self._get_connection() as conn:
            # Clear current flag from all user sessions
            conn.execute(
                "UPDATE sessions SET is_current = 0 WHERE user_id = ?",
                (user_id,),
            )

            # Insert new session as current
            conn.execute(
                """
                INSERT INTO sessions (id, user_id, created_at, last_active, is_current)
                VALUES (?, ?, ?, ?, 1)
                """,
                (session_id, user_id, now.isoformat(), now.isoformat()),
            )

            # FIFO eviction: remove oldest sessions if exceeding limit
            conn.execute(
                """
                DELETE FROM sessions
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM sessions
                    WHERE user_id = ?
                    ORDER BY last_active DESC
                    LIMIT ?
                )
                """,
                (user_id, user_id, MAX_SESSIONS),
            )

        return Session(
            id=session_id,
            user_id=user_id,
            created_at=now,
            last_active=now,
        )

    async def get_current_session(self, user_id: str) -> Session | None:
        """Get the current session for a user."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, user_id, created_at, last_active
                FROM sessions
                WHERE user_id = ? AND is_current = 1
                """,
                (user_id,),
            ).fetchone()
            if row:
                return Session(
                    id=row["id"],
                    user_id=row["user_id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    last_active=datetime.fromisoformat(row["last_active"]),
                )
            return None

    async def set_current_session(self, user_id: str, session_id: str) -> None:
        """Set the current session for a user."""
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            # Clear current flag from all user sessions
            conn.execute(
                "UPDATE sessions SET is_current = 0 WHERE user_id = ?",
                (user_id,),
            )

            # Set new current session and update last_active
            conn.execute(
                """
                UPDATE sessions
                SET is_current = 1, last_active = ?
                WHERE user_id = ? AND id = ?
                """,
                (now, user_id, session_id),
            )

    async def clear_current_session(self, user_id: str) -> None:
        """Clear the current session for a user (for /new command)."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET is_current = 0 WHERE user_id = ?",
                (user_id,),
            )

    async def update_session(self, user_id: str, session_id: str) -> None:
        """
        Update or create a session as current.

        This maintains backward compatibility with the old API.
        """
        if not session_id:
            return

        with self._get_connection() as conn:
            now = datetime.now().isoformat()

            # Check if session exists
            existing = conn.execute(
                "SELECT 1 FROM sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            ).fetchone()

            if existing:
                # Update existing session
                conn.execute(
                    "UPDATE sessions SET is_current = 0 WHERE user_id = ?",
                    (user_id,),
                )
                conn.execute(
                    """
                    UPDATE sessions
                    SET is_current = 1, last_active = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (now, session_id, user_id),
                )
            else:
                # Create new session
                conn.execute(
                    "UPDATE sessions SET is_current = 0 WHERE user_id = ?",
                    (user_id,),
                )
                conn.execute(
                    """
                    INSERT INTO sessions (id, user_id, created_at, last_active, is_current)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (session_id, user_id, now, now),
                )

                # FIFO eviction
                conn.execute(
                    """
                    DELETE FROM sessions
                    WHERE user_id = ? AND id NOT IN (
                        SELECT id FROM sessions
                        WHERE user_id = ?
                        ORDER BY last_active DESC
                        LIMIT ?
                    )
                    """,
                    (user_id, user_id, MAX_SESSIONS),
                )

    # Settings Management

    async def get_settings(self, user_id: str) -> UserSettings:
        """Get settings for a user, creating defaults if not exists."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT mode, audio_enabled, voice_speed, watch_enabled FROM settings WHERE user_id = ?",
                (user_id,),
            ).fetchone()

            if row:
                return UserSettings(
                    mode=Mode(row["mode"]),
                    audio_enabled=bool(row["audio_enabled"]),
                    voice_speed=row["voice_speed"],
                    watch_enabled=bool(row["watch_enabled"]),
                )

            # Create default settings
            default_settings = UserSettings()
            conn.execute(
                """
                INSERT INTO settings (user_id, mode, audio_enabled, voice_speed, watch_enabled)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    default_settings.mode.value,
                    1 if default_settings.audio_enabled else 0,
                    default_settings.voice_speed,
                    1 if default_settings.watch_enabled else 0,
                ),
            )
            return default_settings

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
            conn.execute(
                """
                UPDATE settings
                SET mode = ?, audio_enabled = ?, voice_speed = ?, watch_enabled = ?
                WHERE user_id = ?
                """,
                (
                    current.mode.value,
                    1 if current.audio_enabled else 0,
                    current.voice_speed,
                    1 if current.watch_enabled else 0,
                    user_id,
                ),
            )

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
            row = conn.execute(
                "SELECT mode, audio_enabled, voice_speed, watch_enabled FROM settings WHERE user_id = ?",
                (user_id_str,),
            ).fetchone()

            if row:
                return {
                    "mode": row["mode"],
                    "audio_enabled": bool(row["audio_enabled"]),
                    "voice_speed": row["voice_speed"],
                    "watch_enabled": bool(row["watch_enabled"]),
                }

            # Create default settings
            default_settings = {
                "mode": "go_all",
                "audio_enabled": True,
                "voice_speed": VOICE_SETTINGS["speed"],
                "watch_enabled": False,
            }
            conn.execute(
                """
                INSERT INTO settings (user_id, mode, audio_enabled, voice_speed, watch_enabled)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id_str,
                    default_settings["mode"],
                    1,
                    default_settings["voice_speed"],
                    0,
                ),
            )
            return default_settings

    def update_setting(self, user_id: int, key: str, value) -> None:
        """
        Update a single setting.

        Deprecated: Use async update_settings instead.
        """
        user_id_str = str(user_id)
        # Ensure user has settings
        self.get_user_settings(user_id)

        column_map = {
            "mode": "mode",
            "audio_enabled": "audio_enabled",
            "voice_speed": "voice_speed",
            "watch_enabled": "watch_enabled",
        }

        if key not in column_map:
            return

        with self._get_connection() as conn:
            if key in ("audio_enabled", "watch_enabled"):
                value = 1 if value else 0
            conn.execute(
                f"UPDATE settings SET {column_map[key]} = ? WHERE user_id = ?",
                (value, user_id_str),
            )


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
