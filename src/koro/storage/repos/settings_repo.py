"""Settings repository - pure data access for user settings persistence."""

import sqlite3

from koro.core.config import VOICE_SETTINGS
from koro.core.types import Mode, UserSettings


class SettingsRepo:
    """Repository for user settings data access."""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize settings repository.

        Args:
            conn: SQLite connection with row_factory set
        """
        self.conn = conn

    def get(self, user_id: str) -> UserSettings | None:
        """Get settings for a user, or None if not exists."""
        row = self.conn.execute(
            """
            SELECT mode, audio_enabled, voice_speed, watch_enabled
            FROM settings WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if row:
            return UserSettings(
                mode=Mode(row["mode"]),
                audio_enabled=bool(row["audio_enabled"]),
                voice_speed=row["voice_speed"],
                watch_enabled=bool(row["watch_enabled"]),
            )
        return None

    def get_or_create(self, user_id: str) -> UserSettings:
        """Get settings for a user, creating defaults if not exists."""
        settings = self.get(user_id)
        if settings:
            return settings

        # Create default settings
        default = UserSettings()
        self.create(user_id, default)
        return default

    def create(self, user_id: str, settings: UserSettings) -> None:
        """Create settings for a user."""
        self.conn.execute(
            """
            INSERT INTO settings (user_id, mode, audio_enabled, voice_speed, watch_enabled)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                settings.mode.value,
                1 if settings.audio_enabled else 0,
                settings.voice_speed,
                1 if settings.watch_enabled else 0,
            ),
        )

    def update(self, user_id: str, settings: UserSettings) -> None:
        """Update settings for a user."""
        self.conn.execute(
            """
            UPDATE settings
            SET mode = ?, audio_enabled = ?, voice_speed = ?, watch_enabled = ?
            WHERE user_id = ?
            """,
            (
                settings.mode.value,
                1 if settings.audio_enabled else 0,
                settings.voice_speed,
                1 if settings.watch_enabled else 0,
                user_id,
            ),
        )

    def upsert(self, user_id: str, settings: UserSettings) -> None:
        """Insert or update settings for a user."""
        self.conn.execute(
            """
            INSERT INTO settings (user_id, mode, audio_enabled, voice_speed, watch_enabled)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                mode = excluded.mode,
                audio_enabled = excluded.audio_enabled,
                voice_speed = excluded.voice_speed,
                watch_enabled = excluded.watch_enabled
            """,
            (
                user_id,
                settings.mode.value,
                1 if settings.audio_enabled else 0,
                settings.voice_speed,
                1 if settings.watch_enabled else 0,
            ),
        )

    def update_field(self, user_id: str, key: str, value) -> None:
        """Update a single setting field."""
        column_map = {
            "mode": "mode",
            "audio_enabled": "audio_enabled",
            "voice_speed": "voice_speed",
            "watch_enabled": "watch_enabled",
        }

        if key not in column_map:
            return

        # Convert boolean fields
        if key in ("audio_enabled", "watch_enabled"):
            value = 1 if value else 0

        self.conn.execute(
            f"UPDATE settings SET {column_map[key]} = ? WHERE user_id = ?",
            (value, user_id),
        )

    def delete(self, user_id: str) -> None:
        """Delete settings for a user."""
        self.conn.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))

    def get_as_dict(self, user_id: str) -> dict:
        """Get settings as a dictionary (for legacy compatibility)."""
        row = self.conn.execute(
            """
            SELECT mode, audio_enabled, voice_speed, watch_enabled
            FROM settings WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if row:
            return {
                "mode": row["mode"],
                "audio_enabled": bool(row["audio_enabled"]),
                "voice_speed": row["voice_speed"],
                "watch_enabled": bool(row["watch_enabled"]),
            }

        # Return defaults
        return {
            "mode": "go_all",
            "audio_enabled": True,
            "voice_speed": VOICE_SETTINGS["speed"],
            "watch_enabled": False,
        }
