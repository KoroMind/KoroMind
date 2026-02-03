---
name: coding-lessons
description: Review code against KoroMind coding lessons. Use when reviewing code, checking for common issues, or validating changes against project best practices.
---

# Coding Lessons Review

Review code against lessons learned from KoroMind development.

## Lessons Location

All lessons are in `.ai/lessons/`:

| Lesson | Focus |
|--------|-------|
| [typed-boundaries.md](../lessons/typed-boundaries.md) | Parse into Pydantic at boundary |
| [singleton-safety.md](../lessons/singleton-safety.md) | Double-checked locking for globals |
| [explicit-over-implicit.md](../lessons/explicit-over-implicit.md) | Exceptions > strings, isinstance > hasattr |
| [parameter-objects.md](../lessons/parameter-objects.md) | >5 params → config object |
| [sql-safety.md](../lessons/sql-safety.md) | Parameterized queries always |
| [normalize-at-boundaries.md](../lessons/normalize-at-boundaries.md) | Pick canonical type, convert at entry |

## How to Review

1. Read all lesson files from `.ai/lessons/`
2. For each lesson, check the code against its checklist
3. Report findings grouped by lesson

## Output Format

```markdown
## Coding Lessons Review

### ✅ Passed
- **typed-boundaries**: All external data parsed into Pydantic models

### ⚠️ Issues Found

#### singleton-safety
- `src/foo.py:42` - Global `_client` lacks lock protection
- **Fix**: Add `_client_lock = Lock()` with double-checked pattern

#### sql-safety
- `src/bar.py:78` - String interpolation in SQL: `f"SELECT * FROM {table}"`
- **Fix**: Use parameterized query or whitelist table names

### 📊 Summary
- Lessons checked: 6
- Passed: 4
- Issues: 2
```

## Quick Checklist

Run through each:

- [ ] **typed-boundaries**: External data → Pydantic immediately? No `dict[str, Any]` signatures?
- [ ] **singleton-safety**: Globals have locks? Double-checked pattern?
- [ ] **explicit-over-implicit**: No string errors? isinstance not hasattr? No silent returns?
- [ ] **parameter-objects**: Functions >5 params use config objects?
- [ ] **sql-safety**: All SQL parameterized? No f-strings with user data?
- [ ] **normalize-at-boundaries**: IDs normalized at entry? One canonical type?
