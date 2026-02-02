---
name: agentic-guardrails
description: Enforce agentic coding guardrails for KoroMind. Use when coding in this repo or validating changes against project guidance.
---

# Agentic Guardrails

## Purpose
Ensure changes follow the agentic coding guardrails in `AGENTS.md` and avoid common review issues.

## Checklist
- No `hasattr`/`setattr` in core logic; use typed models with known attributes
- Prefer `@dataclass(frozen=True)` unless mutation is required and explicit
- Avoid optional containers for `list`/`dict`; use empty defaults instead
- Use `Protocol` for callback types instead of ad-hoc `Callable` aliases
- Use a config object when functions exceed ~5 parameters
- Extract shared logic to helpers to avoid duplication
- Raise exceptions for invalid inputs in core paths; don't yield error dicts
- Use Pydantic models when parsing external JSON or user-provided config

## How to Apply
1. Scan modified files for guardrail violations.
2. If any are found, propose fixes before additional refactors.
3. Keep suggestions minimal and consistent with project style.
