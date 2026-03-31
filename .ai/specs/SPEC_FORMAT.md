# Spec Format Standard

## Rules

1. **Max 50 lines** - If longer, split into multiple specs
2. **Structured frontmatter** - Required fields, machine-parseable
3. **Link don't duplicate** - Reference code locations, don't copy code
4. **One concern per file** - Not mega-specs
5. **Validate regularly** - Update `validated` field when checking against code

## Filename Pattern

```
<type>-<short-name>.md

Examples:
  bug-session-hijacking.md
  feature-token-tracking.md
  security-sandbox-isolation.md
```

## Template

```markdown
---
id: <TYPE>-<NNN>        # SEC-001, BUG-002, FEAT-003
type: bug | feature | security | refactor
status: open | in_progress | done | wontfix
severity: critical | high | medium | low  # for bugs/security
location: <file:lines>  # primary code location
issue: <number> | null  # linked GitHub issue
validated: <YYYY-MM-DD> | null
---

# <Title>

## Problem / Goal
- Bullet points only
- Max 5 points

## Solution
- Bullet points only
- Reference code: `file.py:123`

## Test
- How to verify this works
- One line per test case

## Notes
- Optional section
- Edge cases, gotchas, links
```

## Frontmatter Fields

| Field | Required | Values |
|-------|----------|--------|
| id | Yes | TYPE-NNN (e.g., SEC-001) |
| type | Yes | bug, feature, security, refactor |
| status | Yes | open, in_progress, done, wontfix |
| severity | If bug/security | critical, high, medium, low |
| location | Yes | file:lines or "multiple" |
| issue | No | GitHub issue number or null |
| validated | No | Date last checked against code |

## Validation

Specs can be validated with:

```bash
# Check all specs have required frontmatter
grep -L "^id:" .ai/specs/*.md

# Find specs not validated in 30 days
# (tooling TBD)
```

## Examples

Good: `security-session-hijacking.md` (40 lines, focused)
Bad: `security.md` (200 lines, covers everything)
