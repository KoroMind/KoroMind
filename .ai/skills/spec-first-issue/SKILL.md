---
name: spec-first-issue
description: Create or update a feature spec in `.ai/specs/` and then open a detailed GitHub issue. Use when the user asks to “add a spec and open an issue,” “create an issue after documenting the spec,” or similar spec-first workflow requests. This skill enforces: (1) discuss scope, (2) deep code research, (3) write/update spec, (4) create GH issue.
---

# Spec-First Issue Workflow

## Overview

Follow a spec-first workflow: clarify the task, research the codebase deeply, write the spec in `.ai/specs/`, then open a detailed GitHub issue referencing that spec.

## Workflow

### 1. Clarify the task (brief discussion)

- Ask for missing essentials: goal, scope, and any constraints or preferences.
- Confirm whether a new spec is needed or an existing spec should be updated.
- If the user wants alternatives or architectural options, state that you will propose them after research.

### 2. Deep code research

- Search the codebase with `rg` to locate relevant modules, config files, and existing specs.
- Read the key files to understand architecture, entry points, and configuration patterns.
- Note any existing spec or documentation that must be aligned.

### 3. Create or update the spec in `.ai/specs/`

- Create a new spec file if none exists for the feature. Use the naming pattern `<module-or-feature>.md`.
- Follow `.ai/specs/AGENTS.md` structure: Overview, Architecture, Data Models, API Contracts, UI/UX (if relevant), Configuration, Changelog.
- Add a changelog entry with today’s date and a short summary.
- Keep it crisp and aligned to the discovered architecture.
- If alternatives are viable, include them briefly in Architecture or Technical Notes.

### 4. Create the GitHub issue (after spec)

- Use the spec as the source of truth for the issue body.
- Include these sections in the issue:
  - User Story
  - Acceptance Criteria
  - Test Cases
  - Technical Notes
- Mention the spec file path in the issue body.
- Ask for approval or assumptions if labels, repo, or issue title are unclear.

## Practical Notes

- Respect repo conventions (e.g., `.ai/specs/` workflow and any CLAUDE/AGENTS instructions).
- Do not implement code changes; this skill is only for spec + issue creation.
- If GitHub CLI requires network access, request approval and explain why.

## Example Triggers

- “Let’s create a new issue and spec for adding MCP servers.”
- “Add a spec in .ai/specs and then open a GH issue.”
- “Document the feature first, then create the issue.”
