"""Vault layout and path helpers.

This module provides the directory structure and path management for the vault.
It is the only fully implemented module in the vault package.
"""

import shutil
from datetime import date
from pathlib import Path

from koro.core.config import VAULT_DIR

# Vault skeleton path (shipped with package)
_VAULT_SKELETON = (
    Path(__file__).parent.parent.parent.parent / "resources" / "vault_skeleton"
)


def get_vault_root() -> Path:
    """
    Get the vault root directory.

    Returns:
        Path to vault root
    """
    return VAULT_DIR


def get_inbox_path() -> Path:
    """
    Get the inbox folder path.

    Returns:
        Path to inbox folder
    """
    return get_vault_root() / "00_INBOX"


def get_daily_path(target_date: date | None = None) -> Path:
    """
    Get the daily notes folder path, optionally for a specific date.

    Args:
        target_date: Optional date for daily note path

    Returns:
        Path to daily folder or specific daily note
    """
    daily_dir = get_vault_root() / "daily"
    if target_date is None:
        return daily_dir
    # Format: daily/2024/01/2024-01-28.md
    return (
        daily_dir
        / str(target_date.year)
        / f"{target_date.month:02d}"
        / f"{target_date.isoformat()}.md"
    )


def get_templates_path() -> Path:
    """
    Get the templates folder path.

    Returns:
        Path to templates folder
    """
    return get_vault_root() / "_templates"


def get_projects_path() -> Path:
    """
    Get the projects folder path.

    Returns:
        Path to projects folder
    """
    return get_vault_root() / "projects"


def get_attachments_path() -> Path:
    """
    Get the attachments folder path.

    Returns:
        Path to attachments folder
    """
    return get_vault_root() / "_attachments"


def ensure_vault_structure() -> None:
    """
    Ensure the vault directory structure exists.

    Creates the vault directory and copies the skeleton structure if it
    doesn't exist. Safe to call multiple times.
    """
    vault_root = get_vault_root()

    # Create root if not exists
    vault_root.mkdir(parents=True, exist_ok=True)

    # Copy skeleton if vault is empty or missing key folders
    inbox = get_inbox_path()
    daily = get_daily_path()
    templates = get_templates_path()

    needs_init = not inbox.exists() or not daily.exists() or not templates.exists()

    if needs_init and _VAULT_SKELETON.exists():
        # Copy skeleton structure
        for item in _VAULT_SKELETON.iterdir():
            dest = vault_root / item.name
            if not dest.exists():
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

    # Ensure core directories exist regardless of skeleton
    inbox.mkdir(parents=True, exist_ok=True)
    daily.mkdir(parents=True, exist_ok=True)
    templates.mkdir(parents=True, exist_ok=True)
    get_projects_path().mkdir(parents=True, exist_ok=True)
    get_attachments_path().mkdir(parents=True, exist_ok=True)


def get_note_path(relative_path: str) -> Path:
    """
    Get absolute path for a note by relative path.

    Args:
        relative_path: Path relative to vault root

    Returns:
        Absolute path to note
    """
    return get_vault_root() / relative_path


def list_folders() -> list[str]:
    """
    List all top-level folders in the vault.

    Returns:
        List of folder names
    """
    vault_root = get_vault_root()
    if not vault_root.exists():
        return []
    return [
        d.name
        for d in vault_root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]


def list_notes(folder: str = ".") -> list[Path]:
    """
    List all markdown notes in a folder.

    Args:
        folder: Folder path relative to vault root

    Returns:
        List of note paths
    """
    folder_path = get_vault_root() / folder
    if not folder_path.exists():
        return []
    return sorted(folder_path.glob("**/*.md"))


def get_vault_size() -> int:
    """
    Get total size of all files in the vault.

    Returns:
        Size in bytes
    """
    vault_root = get_vault_root()
    if not vault_root.exists():
        return 0

    total = 0
    for item in vault_root.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def get_note_count() -> int:
    """
    Get total number of markdown notes in the vault.

    Returns:
        Number of notes
    """
    return len(list_notes())
