---
id: FEA-001
type: feature
status: active
severity: low
issue: null
validated: 2026-01-29
---

# Commit Skill

## What
- Skill that creates git commits with senior-engineer quality messages
- Reviews all changes, stages everything, writes concise summary + bullets

## Why
- Consistent commit style across the project
- Saves time composing messages manually

## How
- Skill definition: `.ai/skills/commit/SKILL.md`
- Execution: Procedural git CLI workflow
- No external APIs or data structures

### Workflow
1. `git status` - inspect unstaged/untracked
2. `git diff` - review changes
3. `git add -A` - stage all
4. Compose message: 1-line summary (<=72 chars) + bullet list
5. `git commit`

## Test
- Commits include all untracked files
- Message summary under 72 chars
- Bullet points describe key changes

## Changelog

### 2026-01-29
- Refactored to new spec format

### 2026-01-27
- Initial specification
