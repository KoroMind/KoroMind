"""Workspace tools for sandbox operations.

These tools provide helpers for managing the Claude sandbox workspace.
"""

import shutil
from pathlib import Path


class WorkspaceTools:
    """Tools for sandbox workspace management."""

    def __init__(self, sandbox_dir: Path):
        """
        Initialize workspace tools.

        Args:
            sandbox_dir: Root path of the sandbox
        """
        self.sandbox_dir = sandbox_dir

    def ensure_sandbox(self) -> Path:
        """
        Ensure sandbox directory exists.

        Returns:
            Path to sandbox directory
        """
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        return self.sandbox_dir

    def get_path(self, relative_path: str) -> Path:
        """
        Get an absolute path within the sandbox.

        Args:
            relative_path: Path relative to sandbox root

        Returns:
            Absolute path within sandbox
        """
        return self.sandbox_dir / relative_path

    def list_files(self, relative_path: str = ".") -> list[str]:
        """
        List files in a sandbox directory.

        Args:
            relative_path: Path relative to sandbox root

        Returns:
            List of file names
        """
        path = self.sandbox_dir / relative_path
        if not path.exists():
            return []
        return [f.name for f in path.iterdir() if f.is_file()]

    def list_dirs(self, relative_path: str = ".") -> list[str]:
        """
        List directories in a sandbox directory.

        Args:
            relative_path: Path relative to sandbox root

        Returns:
            List of directory names
        """
        path = self.sandbox_dir / relative_path
        if not path.exists():
            return []
        return [d.name for d in path.iterdir() if d.is_dir()]

    def read_file(self, relative_path: str) -> str | None:
        """
        Read a file from the sandbox.

        Args:
            relative_path: Path relative to sandbox root

        Returns:
            File contents or None if not found
        """
        path = self.sandbox_dir / relative_path
        if not path.exists():
            return None
        return path.read_text()

    def write_file(self, relative_path: str, content: str) -> Path:
        """
        Write a file to the sandbox.

        Args:
            relative_path: Path relative to sandbox root
            content: File contents

        Returns:
            Path to written file
        """
        path = self.sandbox_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def delete_file(self, relative_path: str) -> bool:
        """
        Delete a file from the sandbox.

        Args:
            relative_path: Path relative to sandbox root

        Returns:
            True if file was deleted, False if not found
        """
        path = self.sandbox_dir / relative_path
        if path.exists() and path.is_file():
            path.unlink()
            return True
        return False

    def delete_dir(self, relative_path: str) -> bool:
        """
        Delete a directory from the sandbox.

        Args:
            relative_path: Path relative to sandbox root

        Returns:
            True if directory was deleted, False if not found
        """
        path = self.sandbox_dir / relative_path
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            return True
        return False

    def clear_sandbox(self) -> int:
        """
        Clear all files from the sandbox.

        Returns:
            Number of items deleted
        """
        count = 0
        for item in self.sandbox_dir.iterdir():
            if item.is_file():
                item.unlink()
                count += 1
            elif item.is_dir():
                shutil.rmtree(item)
                count += 1
        return count

    def get_size(self, relative_path: str = ".") -> int:
        """
        Get total size of files in a sandbox path.

        Args:
            relative_path: Path relative to sandbox root

        Returns:
            Total size in bytes
        """
        path = self.sandbox_dir / relative_path
        if not path.exists():
            return 0

        if path.is_file():
            return path.stat().st_size

        total = 0
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
        return total


# Default instance
_workspace_tools: WorkspaceTools | None = None


def get_workspace_tools(sandbox_dir: Path | None = None) -> WorkspaceTools:
    """Get or create the default workspace tools instance."""
    global _workspace_tools
    if _workspace_tools is None:
        if sandbox_dir is None:
            from koro.core.config import SANDBOX_DIR

            sandbox_dir = SANDBOX_DIR
        _workspace_tools = WorkspaceTools(sandbox_dir)
    return _workspace_tools


def set_workspace_tools(tools: WorkspaceTools) -> None:
    """Set the default workspace tools instance (for testing)."""
    global _workspace_tools
    _workspace_tools = tools
