---
name: spec-first-issue
description: Full spec-first workflow with git. Clarify → Research → Branch → Spec → Diagrams → Commit → Push → Issue → PR. Use for any feature, bug, or architecture work that needs tracking.
---

# Spec-First Issue Workflow

## Overview

Complete workflow: clarify scope, research codebase, create git branch, write spec, add diagrams if needed, commit, create GitHub issue, then PR linking to issue.

## Workflow

### 1. Clarify the task

- Ask for: goal, scope, type (bug/feature/security/arch), constraints
- Confirm: new spec or update existing?
- If alternatives needed: propose after research

### 2. Deep code research

- Search with Grep to locate relevant modules, configs, existing specs
- Read key files to understand architecture and patterns
- Note any specs or docs that must stay aligned

### 3. Create git branch

```bash
git checkout master && git pull
git checkout -b <type>-<short-name>
```

Types: `bug`, `feature`, `security`, `refactor`, `arch`

### 4. Create spec in `.ai/specs/`

- Filename: `<type>-<short-name>.md`
- Follow SPEC_FORMAT.md if exists, otherwise AGENTS.md structure
- Add changelog entry with today's date
- Keep crisp - split large specs

### 5. Create diagrams (if needed)

- Ask: "Need diagrams for this?"
- Save to `.ai/specs/diagrams/<short-name>-*.mmd`
- Mermaid format for easy rendering

### 6. Commit (spec + diagrams only)

```bash
git add .ai/specs/<type>-<short-name>.md .ai/specs/diagrams/
git commit -m "Add spec: <title>"
```

**Do NOT commit issue draft files** - those are temp.

### 7. User pushes

Ask user to push. Wait for confirmation before creating issue/PR.

### 8. Create GitHub issue

- Title: descriptive, matches spec
- Labels: bug→`bug`, feature→`enhancement`, security→`bug`+`security`, arch→`enhancement`+`architecture`
- Body sections:
  - User Story
  - Acceptance Criteria
  - Test Cases
  - Technical Notes
  - Reference to spec file path

### 9. Create PR

- Title: `Add spec: <title>`
- Body: Summary + `Closes #XX` linking to issue
- Report both URLs to user

## Labels Mapping

| Type | Labels |
|------|--------|
| bug | `bug` |
| feature | `enhancement` |
| security | `bug`, `security` |
| refactor | `enhancement`, `refactor` |
| arch | `enhancement`, `architecture` |

## Important

- Do NOT implement code - spec + issue + PR only
- User must push before issue/PR creation (needs remote branch)
- Update spec's `issue:` field after issue created if using frontmatter
- Respect repo conventions (CLAUDE.md, AGENTS.md)

## Example Triggers

- "Create a spec and issue for adding MCP servers"
- "Let's document this feature and open a PR"
- "Add architecture spec for multi-tenancy"
- `/spec-first-issue feature token-tracking "Add token usage tracking"`
