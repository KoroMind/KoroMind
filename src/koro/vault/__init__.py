"""Vault module for long-term memory storage (Markdown + attachments).

The vault is KoroMind's long-term memory - a durable, human-readable knowledge
base stored as Markdown files. It enables:
- Persisting notes, decisions, summaries beyond chat sessions
- Human-editable outside the app (VS Code, Obsidian, git)
- Search/recall for consistent future answers (via SQLite FTS index)
- Separation from sandbox (working scratchpad) for curated content
"""

from koro.vault.layout import (
    ensure_vault_structure,
    get_daily_path,
    get_inbox_path,
    get_templates_path,
    get_vault_root,
)

__all__ = [
    "ensure_vault_structure",
    "get_daily_path",
    "get_inbox_path",
    "get_templates_path",
    "get_vault_root",
]
