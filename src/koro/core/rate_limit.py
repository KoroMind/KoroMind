"""Rate limiting for message handling."""

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Generator

from koro.core.config import DATABASE_PATH, RATE_LIMIT_PER_MINUTE, RATE_LIMIT_SECONDS


class RateLimiter:
    """Rate limiter for per-user message throttling."""

    def __init__(
        self,
        cooldown_seconds: float = None,
        per_minute_limit: int = None,
        db_path: Path | str | None = None,
    ):
        """
        Initialize rate limiter.

        Args:
            cooldown_seconds: Minimum seconds between messages
            per_minute_limit: Maximum messages per minute
            db_path: Optional SQLite path for persistence
        """
        self.cooldown_seconds = (
            RATE_LIMIT_SECONDS if cooldown_seconds is None else cooldown_seconds
        )
        self.per_minute_limit = (
            RATE_LIMIT_PER_MINUTE if per_minute_limit is None else per_minute_limit
        )
        self.db_path = Path(db_path) if db_path else DATABASE_PATH
        self.user_limits: dict[str, dict] = {}
        self._connection: sqlite3.Connection | None = None
        self._connection_lock = Lock()
        self._cache_lock = Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limits (
                    user_id TEXT PRIMARY KEY,
                    last_message REAL,
                    minute_start REAL NOT NULL,
                    minute_count INTEGER NOT NULL
                )
                """)

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a reusable database connection with thread safety."""
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

    def _load_limits(self, user_id: str) -> dict | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT last_message, minute_start, minute_count
                FROM rate_limits
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "last_message": row["last_message"],
            "minute_start": row["minute_start"],
            "minute_count": row["minute_count"],
        }

    def _save_limits(self, user_id: str, limits: dict) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO rate_limits (user_id, last_message, minute_start, minute_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    last_message = excluded.last_message,
                    minute_start = excluded.minute_start,
                    minute_count = excluded.minute_count
                """,
                (
                    user_id,
                    limits["last_message"],
                    limits["minute_start"],
                    limits["minute_count"],
                ),
            )

    def check(self, user_id: int | str) -> tuple[bool, str]:
        """
        Check if user is within rate limits.

        Args:
            user_id: User identifier

        Returns:
            (allowed, message) - If not allowed, message explains why
        """
        now = time.time()
        user_id_str = str(user_id)

        with self._cache_lock:
            limits = self.user_limits.get(user_id_str)

        if limits is None:
            loaded = self._load_limits(user_id_str)
            if loaded is None:
                loaded = {
                    "last_message": None,
                    "minute_count": 0,
                    "minute_start": now,
                }
            with self._cache_lock:
                self.user_limits.setdefault(user_id_str, loaded)

        with self._cache_lock:
            limits = self.user_limits[user_id_str]

            # Check per-message cooldown
            if limits["last_message"] is not None and self.cooldown_seconds > 0:
                time_since_last = now - limits["last_message"]
                if time_since_last < self.cooldown_seconds:
                    wait_time = self.cooldown_seconds - time_since_last
                    return (
                        False,
                        f"Please wait {wait_time:.1f}s before sending another message.",
                    )

            # Check per-minute limit
            if now - limits["minute_start"] > 60:
                # Reset minute counter
                limits["minute_start"] = now
                limits["minute_count"] = 0

            if limits["minute_count"] >= self.per_minute_limit:
                return (
                    False,
                    f"Rate limit reached ({self.per_minute_limit}/min). Please wait.",
                )

            # Update limits
            limits["last_message"] = now
            limits["minute_count"] += 1
            limits_to_save = limits.copy()

        self._save_limits(user_id_str, limits_to_save)
        return True, ""

    def reset(self, user_id: int | str) -> None:
        """Reset rate limits for a user."""
        user_id_str = str(user_id)
        with self._cache_lock:
            self.user_limits.pop(user_id_str, None)
        with self._get_connection() as conn:
            conn.execute("DELETE FROM rate_limits WHERE user_id = ?", (user_id_str,))

    def reset_all(self) -> None:
        """Reset all rate limits."""
        with self._cache_lock:
            self.user_limits.clear()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM rate_limits")


# Default instance
_rate_limiter: RateLimiter | None = None
_rate_limiter_lock = Lock()


def get_rate_limiter() -> RateLimiter:
    """Get or create the default rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        with _rate_limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = RateLimiter()
    return _rate_limiter


def set_rate_limiter(limiter: RateLimiter) -> None:
    """Set the default rate limiter instance (for testing)."""
    global _rate_limiter
    _rate_limiter = limiter
