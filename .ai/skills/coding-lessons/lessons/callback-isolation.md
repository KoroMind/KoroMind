# Callback Isolation

**Lesson from PR #40 review (Phases 1 & 2)**

## The Rule

Interface-provided callbacks must never abort the main processing path. Handle both sync and async callbacks consistently across all code paths.

## Why

| Problem | Result |
|---------|--------|
| `await cb()` but cb is sync | TypeError — crashes the request |
| No try/except around callback | Caller's bug becomes your outage |
| Streaming path handles sync, non-streaming doesn't | Bug only in one mode — hard to reproduce |
| Tests mock with sync lambdas, prod uses async | Tests pass, prod crashes |

## How

### 1. Use `_maybe_await` for sync/async parity

```python
async def _maybe_await(value: Any) -> Any:
    """Await if awaitable, otherwise return directly."""
    if inspect.isawaitable(value):
        return await value
    return value

# BAD: Only works for async callbacks
await callback(name, detail)  # TypeError if sync

# GOOD: Works for both
await _maybe_await(callback(name, detail))
```

### 2. Isolate every invocation

```python
# BAD: Callback exception kills the request
if progress_callback:
    progress_callback("Processing...")  # Throws → caller gets 500

# GOOD: Isolated + sync/async safe
if tool_use_callback:
    try:
        await _maybe_await(tool_use_callback(tool_name, detail))
    except Exception:
        logger.warning("on_tool_use callback failed", exc_info=True)
```

## When to Apply

- **Always** for callbacks from external callers (UI, API consumers)
- **Always** for callbacks crossing layer boundaries (brain → interface)
- **Not needed** for internal callbacks within the same module

## Checklist

- [ ] Every interface callback wrapped in try/except
- [ ] `_maybe_await()` used consistently (not ad-hoc `inspect.isawaitable`)
- [ ] Same handling in both streaming and non-streaming paths
- [ ] `logger.warning` with `exc_info=True` (caller's bug, not ours)
- [ ] Main path continues after callback failure
- [ ] Tests cover sync + async callback scenarios for each path
