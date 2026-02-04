---
name: coding-lessons
description: Review code against KoroMind coding lessons. Use when reviewing code, checking for common issues, or validating changes against project best practices.
---

# Coding Lessons Review

Review code against lessons learned from KoroMind development.

## Detailed Lessons

Full lessons with examples, explanations, and checklists:

| Lesson | Focus |
|--------|-------|
| [typed-boundaries](lessons/typed-boundaries.md) | Parse into Pydantic at boundary |
| [singleton-safety](lessons/singleton-safety.md) | Double-checked locking for globals |
| [explicit-over-implicit](lessons/explicit-over-implicit.md) | Exceptions > strings, isinstance > hasattr |
| [parameter-objects](lessons/parameter-objects.md) | >5 params → config object |
| [sql-safety](lessons/sql-safety.md) | Parameterized queries always |
| [normalize-at-boundaries](lessons/normalize-at-boundaries.md) | Pick canonical type, convert at entry |

## Quick Reference

One-liner smells that don't need full lessons:

| Smell | Risk | Fix |
|-------|------|-----|
| Type-unsafe event handling | Runtime attribute errors on heterogeneous streams | Narrow types before accessing fields |
| In-memory caches without lifecycle | Memory leaks, stale state | Add scheduled cleanup + exception-safe removal |
| API layers leaking core exceptions | Generic 500s, poor client UX | Map domain errors to HTTP status codes |
| Migrations without failure recording | Silent retries, data loss | Persist success/failure markers |
| Persisting state on failed operations | Corrupted state | Only persist on success |
| Volatile security controls | Bypass on restart | Persist rate limits to durable storage |
| Missing tool execution outcomes | Poor observability | Capture success/failure in metadata |
| Inline imports (without cycle reason) | Hidden dependencies | Move to module scope |
| Optional models where defaults exist | Extra None branches | Require models, pass explicit defaults |
| Mutable dataclasses | Accidental mutation bugs | Prefer `@dataclass(frozen=True)` |
| Ad-hoc Callable aliases | Unclear signatures | Use `Protocol` for callback types |
| Duplicated logic | Drift, maintenance burden | Extract shared logic to helpers |

## How to Review

1. Read all lesson files from `lessons/`
2. For each lesson, check code against its checklist
3. Scan code for quick reference smells
4. Report findings grouped by lesson/smell

## Output Format

```markdown
## Coding Lessons Review

### ✅ Passed
- **typed-boundaries**: All external data parsed into Pydantic models
- **sql-safety**: All queries parameterized

### ⚠️ Issues Found

#### singleton-safety
- `src/foo.py:42` - Global `_client` lacks lock protection
- **Fix**: Add `_client_lock = Lock()` with double-checked pattern

#### Quick Reference: API layers leaking exceptions
- `src/api/routes.py:89` - `BrainError` bubbles as 500
- **Fix**: Add exception handler mapping to 4xx/5xx

### 📊 Summary
- Lessons checked: 6
- Quick refs checked: 9
- Passed: 12
- Issues: 3
```

## Full Checklist

### Detailed Lessons
- [ ] **typed-boundaries**: External data → Pydantic immediately? No `dict[str, Any]`?
- [ ] **singleton-safety**: Globals have locks? Double-checked pattern?
- [ ] **explicit-over-implicit**: No string errors? isinstance not hasattr?
- [ ] **parameter-objects**: Functions >5 params use config objects?
- [ ] **sql-safety**: All SQL parameterized? No f-strings with user data?
- [ ] **normalize-at-boundaries**: IDs normalized at entry? One canonical type?

### Quick Reference
- [ ] Event types narrowed before field access?
- [ ] Caches have cleanup + TTL?
- [ ] Domain errors mapped to HTTP codes?
- [ ] Migration outcomes persisted?
- [ ] State only saved on success?
- [ ] Security controls in durable storage?
- [ ] Tool calls log success/failure?
- [ ] Imports at module scope?
- [ ] Models required, not optional with defaults?
- [ ] Dataclasses frozen unless mutation needed?
- [ ] Callbacks use Protocol, not raw Callable?
- [ ] Shared logic extracted to helpers?
