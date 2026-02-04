# Singleton Safety

**Lesson from full-sdk-impl branch review**

## The Rule

Prefer dependency injection over global singletons. If you must use singletons, use double-checked locking.

## Why Avoid Singletons

| Singletons | Dependency Injection |
|------------|---------------------|
| Hidden dependencies | Explicit dependencies |
| Hard to test (global state) | Easy to mock/stub |
| Tight coupling | Loose coupling |
| Order-dependent initialization | Constructor receives deps |
| Race conditions in concurrent code | No shared mutable state |

## Prefer: Dependency Injection

```python
# BAD: Global singleton
_brain: Brain | None = None

def get_brain() -> Brain:
    global _brain
    if _brain is None:
        _brain = Brain()
    return _brain

def handle_message(text: str):
    brain = get_brain()  # Hidden dependency
    return brain.process(text)

# GOOD: Dependency injection
class MessageHandler:
    def __init__(self, brain: Brain):
        self.brain = brain  # Explicit dependency

    def handle(self, text: str):
        return self.brain.process(text)

# At app startup (composition root)
brain = Brain(config=load_config())
handler = MessageHandler(brain)
```

## Fallback: Double-Checked Locking

If singletons are unavoidable (legacy code, framework constraints):

```python
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

## When Singletons Cause Problems

- FastAPI with multiple workers
- Telegram bot with concurrent handlers
- Any async code with shared state
- Tests that need isolation

## Checklist

- [ ] Can this be passed as a constructor argument instead?
- [ ] Is this truly app-wide, or just laziness?
- [ ] If singleton: does it have a corresponding lock?
- [ ] If singleton: double-check pattern used?
- [ ] Consider `@lru_cache` for simpler cases (but less control)
