"""SQLite-backed state persistence for KoroMind."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Generator
from uuid import uuid4

from koro.core.config import DATABASE_PATH, SETTINGS_FILE, STATE_FILE, VOICE_SETTINGS
from koro.core.types import (
    Mode,
    Session,
    SessionStateItem,
    UserSessionState,
    UserSettings,
)

# Maximum number of sessions to keep per user (FIFO eviction)
MAX_SESSIONS = 100

logger = logging.getLogger(__name__)


class StateManager:
    """Manages user sessions and settings with SQLite persistence."""

    def __init__(self, db_path: Path | str | None = None):
        """
        Initialize state manager.

        Args:
            db_path: Path to SQLite database (defaults to ~/.koromind/koromind.db)
        """
        self._using_custom_path = db_path is not None
        self.db_path = Path(db_path) if db_path else DATABASE_PATH
        self._connection: sqlite3.Connection | None = None
        self._connection_lock = Lock()
        self._ensure_schema()
        # Only migrate from global JSON files when using default path
        if not self._using_custom_path:
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
                    watch_enabled INTEGER DEFAULT 0,
                    model TEXT DEFAULT '',
                    pending_session_name TEXT DEFAULT NULL
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

            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(settings)").fetchall()
            }
            if "model" not in columns:
                conn.execute("ALTER TABLE settings ADD COLUMN model TEXT DEFAULT ''")
            if "pending_session_name" not in columns:
                conn.execute(
                    "ALTER TABLE settings ADD COLUMN pending_session_name TEXT DEFAULT NULL"
                )

            session_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
            }
            if "name" not in session_columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN name TEXT DEFAULT NULL")

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with row factory."""
        with self._connection_lock:
            if self._connection is None:
                self._connection = sqlite3.connect(
                    self.db_path, check_same_thread=False
                )
                self._connection.row_factory = sqlite3.Row
            try:
                yield self._connection
                self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    def close(self) -> None:
        """Close the shared database connection."""
        with self._connection_lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def _migrate_from_json(self) -> None:
        """Migrate data from legacy JSON files if not already done."""
        with self._get_connection() as conn:
            # Check if migration was already done
            result = conn.execute("""
                SELECT 1
                FROM migration_status
                WHERE name IN ('json_migration', 'json_migration_failed')
                """).fetchone()
            if result:
                return

            errors: list[str] = []

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
                except (json.JSONDecodeError, OSError) as exc:
                    logger.error(
                        "Failed to migrate sessions from %s",
                        STATE_FILE,
                        exc_info=True,
                    )
                    errors.append(f"Sessions: {exc}")

            # Migrate settings from JSON
            if SETTINGS_FILE.exists():
                try:
                    with open(SETTINGS_FILE) as f:
                        settings_data = json.load(f)
                    for user_id, user_settings in settings_data.items():
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO settings
                            (user_id, mode, audio_enabled, voice_speed, watch_enabled, model)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                user_id,
                                user_settings.get("mode", "go_all"),
                                1 if user_settings.get("audio_enabled", True) else 0,
                                user_settings.get(
                                    "voice_speed", VOICE_SETTINGS["speed"]
                                ),
                                1 if user_settings.get("watch_enabled", False) else 0,
                                user_settings.get("model", ""),
                            ),
                        )
                except (json.JSONDecodeError, OSError) as exc:
                    logger.error(
                        "Failed to migrate settings from %s",
                        SETTINGS_FILE,
                        exc_info=True,
                    )
                    errors.append(f"Settings: {exc}")

            if errors:
                conn.execute(
                    "INSERT INTO migration_status (name, completed_at) VALUES (?, ?)",
                    ("json_migration_failed", datetime.now().isoformat()),
                )
                raise RuntimeError(f"JSON migration failed: {'; '.join(errors)}")

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

    async def get_session_state(
        self, user_id: str, limit: int | None = None
    ) -> UserSessionState:
        """Get typed session state for a user."""
        with self._get_connection() as conn:
            pending_row = conn.execute(
                "SELECT pending_session_name FROM settings WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            pending_session_name = (
                pending_row["pending_session_name"]
                if pending_row and pending_row["pending_session_name"]
                else None
            )

            query = """
                SELECT id, name, is_current
                FROM sessions
                WHERE user_id = ?
                ORDER BY last_active DESC
            """
            params: tuple[str, int] | tuple[str]
            params = (user_id,)
            if limit is not None:
                query += " LIMIT ?"
                params = (user_id, limit)

            rows = conn.execute(query, params).fetchall()
            sessions = [
                SessionStateItem(
                    id=row["id"],
                    name=row["name"],
                    is_current=bool(row["is_current"]),
                )
                for row in rows
            ]
            current = next((s.id for s in sessions if s.is_current), None)
            return UserSessionState(
                current_session_id=current,
                sessions=sessions,
                pending_session_name=pending_session_name,
            )

    async def create_session(self, user_id: str) -> Session:
        """Create a new session for a user."""
        now = datetime.now()
        session_id = str(uuid4())

        with self._get_connection() as conn:
            pending_name_row = conn.execute(
                "SELECT pending_session_name FROM settings WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            pending_name = (
                pending_name_row["pending_session_name"]
                if pending_name_row and pending_name_row["pending_session_name"]
                else None
            )

            # Clear current flag from all user sessions
            conn.execute(
                "UPDATE sessions SET is_current = 0 WHERE user_id = ?",
                (user_id,),
            )

            # Insert new session as current
            conn.execute(
                """
                INSERT INTO sessions (id, user_id, created_at, last_active, is_current, name)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (session_id, user_id, now.isoformat(), now.isoformat(), pending_name),
            )

            conn.execute(
                "UPDATE settings SET pending_session_name = NULL WHERE user_id = ?",
                (user_id,),
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

    async def set_pending_session_name(self, user_id: str, name: str | None) -> None:
        """Store an optional name for the next newly created session."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (
                    user_id, mode, audio_enabled, voice_speed, watch_enabled, model,
                    pending_session_name
                )
                VALUES (?, 'go_all', 1, 1.1, 0, '', ?)
                ON CONFLICT(user_id) DO UPDATE SET pending_session_name = excluded.pending_session_name
                """,
                (user_id, name),
            )

    async def update_session(
        self, user_id: str, session_id: str, session_name: str | None = None
    ) -> None:
        """
        Update or create a session as current.

        This maintains backward compatibility with the old API.
        """
        if not session_id:
            return

        with self._get_connection() as conn:
            now = datetime.now().isoformat()
            requested_name = session_name.strip() if session_name else None

            pending_name = None
            if not requested_name:
                pending_row = conn.execute(
                    "SELECT pending_session_name FROM settings WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                if pending_row and pending_row["pending_session_name"]:
                    pending_name = pending_row["pending_session_name"].strip() or None

            # Check if session exists
            existing = conn.execute(
                "SELECT name FROM sessions WHERE id = ? AND user_id = ?",
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
                    SET is_current = 1, last_active = ?, name = COALESCE(?, name)
                    WHERE id = ? AND user_id = ?
                    """,
                    (now, requested_name, session_id, user_id),
                )
            else:
                # Create new session
                conn.execute(
                    "UPDATE sessions SET is_current = 0 WHERE user_id = ?",
                    (user_id,),
                )
                conn.execute(
                    """
                    INSERT INTO sessions (id, user_id, created_at, last_active, is_current, name)
                    VALUES (?, ?, ?, ?, 1, ?)
                    """,
                    (session_id, user_id, now, now, requested_name or pending_name),
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

            if requested_name or pending_name:
                conn.execute(
                    "UPDATE settings SET pending_session_name = NULL WHERE user_id = ?",
                    (user_id,),
                )

    # Settings Management

    async def get_settings(self, user_id: str) -> UserSettings:
        """Get settings for a user, creating defaults if not exists."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT mode, audio_enabled, voice_speed, watch_enabled, model FROM settings WHERE user_id = ?",
                (user_id,),
            ).fetchone()

            if row:
                return UserSettings(
                    mode=Mode(row["mode"]),
                    audio_enabled=bool(row["audio_enabled"]),
                    voice_speed=row["voice_speed"],
                    watch_enabled=bool(row["watch_enabled"]),
                    model=row["model"] or "",
                )

            # Create default settings
            default_settings = UserSettings()
            conn.execute(
                """
                INSERT INTO settings (user_id, mode, audio_enabled, voice_speed, watch_enabled, model)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    default_settings.mode.value,
                    1 if default_settings.audio_enabled else 0,
                    default_settings.voice_speed,
                    1 if default_settings.watch_enabled else 0,
                    default_settings.model,
                ),
            )
            return default_settings

    async def update_settings(self, user_id: str, **kwargs) -> UserSettings:
        """Update settings for a user."""
        # Get current settings first
        current = await self.get_settings(user_id)

        updates: dict[str, object] = {}
        if "mode" in kwargs:
            mode_val = kwargs["mode"]
            updates["mode"] = mode_val if isinstance(mode_val, Mode) else Mode(mode_val)
        if "audio_enabled" in kwargs:
            updates["audio_enabled"] = kwargs["audio_enabled"]
        if "voice_speed" in kwargs:
            updates["voice_speed"] = kwargs["voice_speed"]
        if "watch_enabled" in kwargs:
            updates["watch_enabled"] = kwargs["watch_enabled"]
        if "model" in kwargs:
            updates["model"] = kwargs["model"]

        if updates:
            current = current.model_copy(update=updates)

        # Save to database
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE settings
                SET mode = ?, audio_enabled = ?, voice_speed = ?, watch_enabled = ?, model = ?
                WHERE user_id = ?
                """,
                (
                    current.mode.value,
                    1 if current.audio_enabled else 0,
                    current.voice_speed,
                    1 if current.watch_enabled else 0,
                    current.model,
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

    def get_user_settings(self, user_id: int) -> UserSettings:
        """
        Get user settings.

        Deprecated: Use async get_settings instead.
        """
        user_id_str = str(user_id)
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT mode, audio_enabled, voice_speed, watch_enabled, model FROM settings WHERE user_id = ?",
                (user_id_str,),
            ).fetchone()

            if row:
                return UserSettings(
                    mode=Mode(row["mode"]),
                    audio_enabled=bool(row["audio_enabled"]),
                    voice_speed=row["voice_speed"],
                    watch_enabled=bool(row["watch_enabled"]),
                    model=row["model"] or "",
                )

            # Create default settings
            default_settings = UserSettings()
            conn.execute(
                """
                INSERT INTO settings (user_id, mode, audio_enabled, voice_speed, watch_enabled, model)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id_str,
                    default_settings.mode.value,
                    1 if default_settings.audio_enabled else 0,
                    default_settings.voice_speed,
                    1 if default_settings.watch_enabled else 0,
                    default_settings.model,
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

        if key not in {
            "mode",
            "audio_enabled",
            "voice_speed",
            "watch_enabled",
            "model",
        }:
            return

        with self._get_connection() as conn:
            if key in ("audio_enabled", "watch_enabled"):
                value = 1 if value else 0
            if key == "mode":
                conn.execute(
                    "UPDATE settings SET mode = ? WHERE user_id = ?",
                    (value, user_id_str),
                )
            elif key == "audio_enabled":
                conn.execute(
                    "UPDATE settings SET audio_enabled = ? WHERE user_id = ?",
                    (value, user_id_str),
                )
            elif key == "voice_speed":
                conn.execute(
                    "UPDATE settings SET voice_speed = ? WHERE user_id = ?",
                    (value, user_id_str),
                )
            elif key == "watch_enabled":
                conn.execute(
                    "UPDATE settings SET watch_enabled = ? WHERE user_id = ?",
                    (value, user_id_str),
                )
            elif key == "model":
                conn.execute(
                    "UPDATE settings SET model = ? WHERE user_id = ?",
                    (value, user_id_str),
                )


# Default instance
_state_manager: StateManager | None = None
_state_manager_lock = Lock()


def get_state_manager() -> StateManager:
    """Get or create the default state manager instance."""
    global _state_manager
    if _state_manager is None:
        with _state_manager_lock:
            if _state_manager is None:
                _state_manager = StateManager()
    return _state_manager


def set_state_manager(manager: StateManager) -> None:
    """Set the default state manager instance (for testing)."""
    global _state_manager
    _state_manager = manager
