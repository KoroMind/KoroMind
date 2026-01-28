"""Sessions repository - pure data access for session persistence."""

import sqlite3
from datetime import datetime
from uuid import uuid4

from koro.core.types import Session


class SessionsRepo:
    """Repository for session data access."""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize sessions repository.

        Args:
            conn: SQLite connection with row_factory set
        """
        self.conn = conn

    def get_all(self, user_id: str) -> list[Session]:
        """Get all sessions for a user, ordered by last_active descending."""
        rows = self.conn.execute(
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

    def get_by_id(self, session_id: str, user_id: str) -> Session | None:
        """Get a specific session by ID."""
        row = self.conn.execute(
            """
            SELECT id, user_id, created_at, last_active
            FROM sessions
            WHERE id = ? AND user_id = ?
            """,
            (session_id, user_id),
        ).fetchone()
        if row:
            return Session(
                id=row["id"],
                user_id=row["user_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                last_active=datetime.fromisoformat(row["last_active"]),
            )
        return None

    def get_current(self, user_id: str) -> Session | None:
        """Get the current session for a user."""
        row = self.conn.execute(
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

    def create(self, user_id: str) -> Session:
        """Create a new session for a user."""
        now = datetime.now()
        session_id = str(uuid4())

        # Clear current flag from all user sessions
        self.conn.execute(
            "UPDATE sessions SET is_current = 0 WHERE user_id = ?",
            (user_id,),
        )

        # Insert new session as current
        self.conn.execute(
            """
            INSERT INTO sessions (id, user_id, created_at, last_active, is_current)
            VALUES (?, ?, ?, ?, 1)
            """,
            (session_id, user_id, now.isoformat(), now.isoformat()),
        )

        return Session(
            id=session_id,
            user_id=user_id,
            created_at=now,
            last_active=now,
        )

    def set_current(self, user_id: str, session_id: str) -> None:
        """Set a session as current for a user."""
        now = datetime.now().isoformat()

        # Clear current flag from all user sessions
        self.conn.execute(
            "UPDATE sessions SET is_current = 0 WHERE user_id = ?",
            (user_id,),
        )

        # Set new current session and update last_active
        self.conn.execute(
            """
            UPDATE sessions
            SET is_current = 1, last_active = ?
            WHERE user_id = ? AND id = ?
            """,
            (now, user_id, session_id),
        )

    def clear_current(self, user_id: str) -> None:
        """Clear the current session for a user."""
        self.conn.execute(
            "UPDATE sessions SET is_current = 0 WHERE user_id = ?",
            (user_id,),
        )

    def update_or_create(self, user_id: str, session_id: str) -> None:
        """Update an existing session as current, or create it if not exists."""
        if not session_id:
            return

        now = datetime.now().isoformat()

        # Check if session exists
        existing = self.conn.execute(
            "SELECT 1 FROM sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()

        # Clear current flag
        self.conn.execute(
            "UPDATE sessions SET is_current = 0 WHERE user_id = ?",
            (user_id,),
        )

        if existing:
            # Update existing session
            self.conn.execute(
                """
                UPDATE sessions
                SET is_current = 1, last_active = ?
                WHERE id = ? AND user_id = ?
                """,
                (now, session_id, user_id),
            )
        else:
            # Create new session
            self.conn.execute(
                """
                INSERT INTO sessions (id, user_id, created_at, last_active, is_current)
                VALUES (?, ?, ?, ?, 1)
                """,
                (session_id, user_id, now, now),
            )

    def evict_oldest(self, user_id: str, max_sessions: int) -> None:
        """Remove oldest sessions beyond the limit (FIFO eviction)."""
        self.conn.execute(
            """
            DELETE FROM sessions
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM sessions
                WHERE user_id = ?
                ORDER BY last_active DESC
                LIMIT ?
            )
            """,
            (user_id, user_id, max_sessions),
        )

    def count(self, user_id: str) -> int:
        """Get the number of sessions for a user."""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row[0] if row else 0
