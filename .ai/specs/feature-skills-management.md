---
id: FEAT-002
type: feature
status: open
severity: medium
location: src/koro/core/tools/registry.py
issue: null
validated: 2026-01-28
---

# Skills Management via Settings

## Goal
- Users enable/disable Claude Code skills
- Telegram `/skills` command and settings menu
- Persist preferences in user settings

## Solution
- Scan `~/.claude/skills/*/SKILL.md` for available skills
- Add `disabled_skills` to UserSettings
- Filter skills before passing to Claude SDK

## UI
```
/skills              - List with status
/skills disable X    - Disable skill X
/skills enable X     - Enable skill X
```

## Test
- Disable "commit" skill
- Ask Claude to run /commit
- Expected: Skill not available
