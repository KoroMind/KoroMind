# Agent Guidelines (Mirror)

Source of truth: `../AGENTS.md`.
Update the root file first and sync this copy if you change guardrails.

## Agentic Coding Guardrails
- Avoid `hasattr`/`setattr` in core logic; use typed models with known attributes
- Prefer `@dataclass(frozen=True)` unless mutation is required and explicit
- Avoid optional containers for `list`/`dict`; use empty defaults instead
- Use `Protocol` for callback types instead of ad-hoc `Callable` aliases
- Use a config object when functions exceed ~5 parameters
- Extract shared logic to helpers to avoid duplication
- Raise exceptions for invalid inputs in core paths; don't yield error dicts
- Use Pydantic models when parsing external JSON or user-provided config
