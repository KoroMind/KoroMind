# Explicit Over Implicit

**Lesson from full-sdk-impl branch review**

## The Rule

Make hidden behavior visible. Implicit assumptions become explicit code.

## Three Patterns

### 1. Typed Exceptions Over String Errors

```python
# BAD: Error hidden in return value
def transcribe(audio) -> str:
    if failed:
        return "[Error: transcription failed]"

text = transcribe(audio)
if text.startswith("[Error"):  # Fragile detection
    handle_error()

# GOOD: Explicit exception
class VoiceError(Exception): pass

def transcribe(audio) -> str:
    if failed:
        raise VoiceError("transcription failed")

try:
    text = transcribe(audio)
except VoiceError as e:
    handle_error(e)
```

### 2. isinstance Over hasattr

```python
# BAD: Duck typing without guarantees
if hasattr(event, "session_id"):
    update_session(event.session_id)  # What if it's None? Wrong type?

# GOOD: Type narrowing
if isinstance(event, ResultMessage) and event.session_id:
    update_session(event.session_id)  # Type checker knows the shape
```

### 3. Raise Over Silent Return

```python
# BAD: Caller doesn't know what happened
def migrate():
    if failed:
        return  # Silent - corruption possible

# GOOD: Failure is visible
def migrate():
    if failed:
        db.record("migration_failed", error_details)
        raise RuntimeError(f"Migration failed: {error_details}")
```

## Why This Matters

| Implicit | Explicit |
|----------|----------|
| Bugs hide until production | Bugs surface immediately |
| "Works on my machine" | Works everywhere or fails clearly |
| Debugging = guessing | Debugging = reading error message |
| Type checker can't help | Type checker catches mistakes |

## Checklist

- [ ] No error information in return values - use exceptions
- [ ] No `hasattr` for type discrimination - use `isinstance`
- [ ] No silent `return` on failure - raise or log explicitly
- [ ] No string matching for control flow - use types/enums
