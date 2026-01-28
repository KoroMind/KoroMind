"""SQLite database connection and initialization."""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from koro.core.config import DATABASE_PATH

logger = logging.getLogger(__name__)

# Migrations directory
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Run pending database migrations."""
    # Create migrations tracking table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Get applied migrations
    applied = {
        row[0] for row in conn.execute("SELECT name FROM _migrations").fetchall()
    }

    # Get all migration files
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    for migration_file in migration_files:
        if migration_file.name in applied:
            continue

        logger.info("Applying migration: %s", migration_file.name)
        sql = migration_file.read_text()
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO _migrations (name) VALUES (?)",
            (migration_file.name,),
        )
        conn.commit()
        logger.info("Migration applied: %s", migration_file.name)


def init_db(db_path: Path | str | None = None) -> None:
    """
    Initialize database with schema and migrations.

    Args:
        db_path: Path to SQLite database (defaults to DATABASE_PATH)
    """
    path = Path(db_path) if db_path else DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        # Enable WAL mode for better concurrent access
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")

        _run_migrations(conn)
    finally:
        conn.close()


@contextmanager
def get_connection(
    db_path: Path | str | None = None,
) -> Generator[sqlite3.Connection, None, None]:
    """
    Get a database connection with row factory.

    Args:
        db_path: Path to SQLite database (defaults to DATABASE_PATH)

    Yields:
        SQLite connection with row factory enabled
    """
    path = Path(db_path) if db_path else DATABASE_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Enable foreign keys for this connection
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# Default database path for direct use
_db_path: Path = DATABASE_PATH


def set_db_path(path: Path | str) -> None:
    """Set the default database path."""
    global _db_path
    _db_path = Path(path)


def get_db_path() -> Path:
    """Get the current default database path."""
    return _db_path
