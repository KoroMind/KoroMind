"""Vault tools for reading, searching, and committing to the vault.

These tools provide the interface between the Brain and the vault storage.
"""

from pathlib import Path
from typing import Any


class VaultTools:
    """Tools for vault operations."""

    def __init__(self, vault_root: Path):
        """
        Initialize vault tools.

        Args:
            vault_root: Root path of the vault
        """
        self.vault_root = vault_root

    def read_note(self, path: str) -> str:
        """
        Read a note from the vault.

        Args:
            path: Relative path to the note

        Returns:
            Note content

        TODO: Implement full note reading with frontmatter parsing.
        """
        raise NotImplementedError("vault_tools.read_note not yet implemented")

    def search_notes(
        self,
        query: str,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search notes in the vault.

        Args:
            query: Search query
            tags: Optional tag filters
            limit: Maximum results

        Returns:
            List of matching note metadata

        TODO: Implement full-text search with FTS5.
        """
        raise NotImplementedError("vault_tools.search_notes not yet implemented")

    def create_note(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        folder: str = "00_INBOX",
    ) -> Path:
        """
        Create a new note in the vault.

        Args:
            title: Note title
            content: Note content
            tags: Optional tags
            folder: Target folder (default: inbox)

        Returns:
            Path to created note

        TODO: Implement note creation with frontmatter.
        """
        raise NotImplementedError("vault_tools.create_note not yet implemented")

    def update_note(
        self,
        path: str,
        content: str,
        update_frontmatter: dict | None = None,
    ) -> None:
        """
        Update an existing note.

        Args:
            path: Relative path to the note
            content: New content
            update_frontmatter: Frontmatter fields to update

        TODO: Implement note updates.
        """
        raise NotImplementedError("vault_tools.update_note not yet implemented")

    def commit_from_session(
        self,
        session_id: str,
        summary: str,
        folder: str = "00_INBOX",
    ) -> Path:
        """
        Commit session insights to a note in the vault.

        This is the "hot to cold" pipeline - taking transient session
        data and persisting it as a note.

        Args:
            session_id: Session to commit from
            summary: Summary of the session
            folder: Target folder

        Returns:
            Path to created note

        TODO: Implement session commit pipeline.
        """
        raise NotImplementedError("vault_tools.commit_from_session not yet implemented")

    def get_daily_note(self, date: str | None = None) -> dict[str, Any]:
        """
        Get or create a daily note.

        Args:
            date: Date string (YYYY-MM-DD), defaults to today

        Returns:
            Daily note metadata and content

        TODO: Implement daily notes.
        """
        raise NotImplementedError("vault_tools.get_daily_note not yet implemented")

    def append_to_daily(self, content: str, date: str | None = None) -> None:
        """
        Append content to the daily note.

        Args:
            content: Content to append
            date: Date string (YYYY-MM-DD), defaults to today

        TODO: Implement daily note appending.
        """
        raise NotImplementedError("vault_tools.append_to_daily not yet implemented")


# Default instance
_vault_tools: VaultTools | None = None


def get_vault_tools(vault_root: Path | None = None) -> VaultTools:
    """Get or create the default vault tools instance."""
    global _vault_tools
    if _vault_tools is None:
        if vault_root is None:
            from koro.core.config import VAULT_DIR

            vault_root = VAULT_DIR
        _vault_tools = VaultTools(vault_root)
    return _vault_tools


def set_vault_tools(tools: VaultTools) -> None:
    """Set the default vault tools instance (for testing)."""
    global _vault_tools
    _vault_tools = tools
