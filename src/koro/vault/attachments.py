"""Attachment handling for the vault.

TODO: Implement attachment operations.
"""

from pathlib import Path
from typing import BinaryIO


def save_attachment(
    content: bytes | BinaryIO,
    filename: str,
    subfolder: str | None = None,
) -> Path:
    """
    Save an attachment to the vault.

    Args:
        content: File content as bytes or file-like object
        filename: Original filename
        subfolder: Optional subfolder within _attachments

    Returns:
        Path to saved attachment

    TODO: Implement attachment saving.
    """
    raise NotImplementedError("attachments.save_attachment not yet implemented")


def get_attachment(path: str) -> bytes:
    """
    Get attachment content.

    Args:
        path: Relative path to attachment

    Returns:
        Attachment content as bytes

    TODO: Implement attachment retrieval.
    """
    raise NotImplementedError("attachments.get_attachment not yet implemented")


def delete_attachment(path: str) -> bool:
    """
    Delete an attachment.

    Args:
        path: Relative path to attachment

    Returns:
        True if deleted, False if not found

    TODO: Implement attachment deletion.
    """
    raise NotImplementedError("attachments.delete_attachment not yet implemented")


def list_attachments(subfolder: str | None = None) -> list[Path]:
    """
    List attachments in the vault.

    Args:
        subfolder: Optional subfolder to list

    Returns:
        List of attachment paths

    TODO: Implement attachment listing.
    """
    raise NotImplementedError("attachments.list_attachments not yet implemented")


def get_attachment_url(path: str) -> str:
    """
    Get a reference URL for an attachment.

    Args:
        path: Relative path to attachment

    Returns:
        Markdown-compatible reference URL

    TODO: Implement attachment URL generation.
    """
    raise NotImplementedError("attachments.get_attachment_url not yet implemented")


def clean_orphaned_attachments() -> int:
    """
    Remove attachments not referenced by any note.

    Returns:
        Number of attachments deleted

    TODO: Implement orphan cleanup.
    """
    raise NotImplementedError(
        "attachments.clean_orphaned_attachments not yet implemented"
    )
