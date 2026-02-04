# Singleton Safety

**Lesson from full-sdk-impl branch review**

## The Rule

Global singletons in concurrent code need double-checked locking. Always.

## Why

| No lock | With lock |
|---------|-----------|
| Two threads create two instances | One instance guaranteed |
| Race condition on first access | Safe initialization |
| Subtle bugs under load | Predictable behavior |
| Works in tests, fails in prod | Works everywhere |

## How

```python
# BAD: Race condition on concurrent first access
_brain: Brain | None = None

def get_brain() -> Brain:
    global _brain
    if _brain is None:
        _brain = Brain()  # Two threads can both enter here
    return _brain

# GOOD: Double-checked locking
from threading import Lock

_brain: Brain | None = None
_brain_lock = Lock()

def get_brain() -> Brain:
    global _brain
    if _brain is None:  # Fast path - no lock if already init
        with _brain_lock:
            if _brain is None:  # Re-check inside lock
                _brain = Brain()
    return _brain
```

## When This Matters

- FastAPI with multiple workers
- Telegram bot with concurrent handlers
- Any async code with shared state
- Background job schedulers

## Checklist

- [ ] Every `global _thing` has a corresponding `_thing_lock`
- [ ] Double-check pattern: check → lock → check again → create
- [ ] Lock is module-level, created once at import
- [ ] Consider `@lru_cache` for simpler cases (but less control)
