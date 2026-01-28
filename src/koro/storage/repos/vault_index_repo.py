"""Vault index repository - note index + FTS for vault search.

This is a stub implementation. TODO: Implement full-text search index
for the vault markdown files.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VaultNote:
    """Represents an indexed vault note."""

    path: str
    title: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    content_hash: str


class VaultIndexRepo:
    """Repository for vault note indexing and full-text search.

    TODO: Implement FTS5 index for vault markdown files.
    """

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize vault index repository.

        Args:
            conn: SQLite connection with row_factory set
        """
        self.conn = conn

    def index_note(self, note: VaultNote) -> None:
        """Index a vault note for search. TODO: Implement."""
        raise NotImplementedError("vault_index_repo.index_note not yet implemented")

    def remove_note(self, path: str) -> None:
        """Remove a note from the index. TODO: Implement."""
        raise NotImplementedError("vault_index_repo.remove_note not yet implemented")

    def search(self, query: str, limit: int = 10) -> list[VaultNote]:
        """Search vault notes by content. TODO: Implement."""
        raise NotImplementedError("vault_index_repo.search not yet implemented")

    def search_by_tag(self, tag: str, limit: int = 10) -> list[VaultNote]:
        """Search vault notes by tag. TODO: Implement."""
        raise NotImplementedError("vault_index_repo.search_by_tag not yet implemented")

    def get_all_tags(self) -> list[str]:
        """Get all unique tags across the vault. TODO: Implement."""
        raise NotImplementedError("vault_index_repo.get_all_tags not yet implemented")

    def get_recent(self, limit: int = 10) -> list[VaultNote]:
        """Get recently updated notes. TODO: Implement."""
        raise NotImplementedError("vault_index_repo.get_recent not yet implemented")

    def rebuild_index(self) -> int:
        """Rebuild the entire index from vault files. TODO: Implement."""
        raise NotImplementedError("vault_index_repo.rebuild_index not yet implemented")
