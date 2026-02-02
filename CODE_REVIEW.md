# Code Review: full-sdk-impl Branch

**Branch:** `full-sdk-impl` → `main`
**Reviewer:** Elite Code Review Expert
**Date:** 2026-02-01
**Scope:** Full SDK implementation refactor

---

## Executive Summary

This is a **major architectural refactor** implementing the Claude Agent SDK across the entire codebase. The changes are extensive (8,409 additions, 3,461 deletions across 99 files) and introduce significant breaking changes to the internal architecture while maintaining backward compatibility at interface boundaries.

## Changelog (Post-Review Fixes)

- 2026-02-02: Fix streaming session update to only use ResultMessage (commit `c6ad053`).
- 2026-02-02: Remove SQL column interpolation in settings updates (commit `a7890db`).
- 2026-02-02: Add periodic pending-approvals cleanup and timeout cleanup (commit `7104482`).
- 2026-02-02: Map Brain input/transcription errors to 400/422 in API endpoints (commit `9a2db44`).
- 2026-02-02: Validate query config option types before Pydantic (commit `f97fccf`).
- 2026-02-02: Record JSON migration failures and stop retries (commit `c6c6b9d`).
- 2026-02-02: Guard singleton initialization with locks (commit `b87d6ed`).

### Critical Issues Found: 3
### High Priority Issues: 7
### Medium Priority Issues: 5

---

## 🚨 CRITICAL ISSUES - Must Fix Before Merge

### 1. Race Condition in StateManager Session Updates (CRITICAL)

**Location:** `src/koro/core/brain.py:295-298`

```python
if isinstance(event, (ResultMessage, StreamEvent)) and event.session_id:
    if event.session_id != session_id:
        await self.state_manager.update_session(user_id, event.session_id)
        session_id = event.session_id
```

**Problem:**
- `StreamEvent` is checked but doesn't have a `session_id` attribute
- This will cause `AttributeError` at runtime when streaming
- The type hint suggests this code path was not tested

**Impact:** Streaming mode will crash when Claude returns events

**Fix Required:**
```python
if isinstance(event, ResultMessage) and event.session_id:
    if event.session_id != session_id:
        await self.state_manager.update_session(user_id, event.session_id)
        session_id = event.session_id
```

---

### 2. SQL Injection Vulnerability in StateManager (CRITICAL - Security)

**Location:** `src/koro/core/state.py:543`

```python
conn.execute(
    f"UPDATE settings SET {column_map[key]} = ? WHERE user_id = ?",
    (value, user_id_str),
)
```

**Problem:**
- String interpolation (`f-string`) used for column name in SQL query
- Even though `column_map` provides limited options, this violates security best practices
- Future modifications could accidentally introduce SQL injection

**Impact:** Potential SQL injection vector if `column_map` is modified without security review

**Fix Required:**
```python
# Use explicit conditional updates or prepared column list
allowed_columns = {"mode", "audio_enabled", "voice_speed", "watch_enabled"}
if key not in allowed_columns:
    raise ValueError(f"Invalid setting key: {key}")

query = f"UPDATE settings SET {key} = ? WHERE user_id = ?"  # Still needs whitelist validation
conn.execute(query, (value, user_id_str))
```

Better approach: Use explicit if/else for each column or ORM-style update builder.

---

### 3. Memory Leak in pending_approvals Dictionary (CRITICAL - Production)

**Location:** `src/koro/interfaces/telegram/handlers/messages.py:22-69`

**Problem:**
- Global `pending_approvals` dict grows indefinitely
- Cleanup only runs on new approval creation (line 41)
- Timeout at line 272 doesn't guarantee cleanup if exception occurs
- Max size check (line 44) helps but doesn't prevent all leaks

**Scenario:**
1. User requests tool approval
2. Bot crashes/restarts before approval
3. Entry remains in memory until 100+ new approvals arrive
4. High-traffic bot accumulates stale entries

**Impact:** Memory leak in production Telegram bots with high approval mode usage

**Fix Required:**
```python
# Add periodic background cleanup task in bot initialization
async def periodic_cleanup():
    while True:
        await asyncio.sleep(60)  # Every minute
        cleanup_stale_approvals()

# Start in bot.py initialization
asyncio.create_task(periodic_cleanup())

# Also ensure cleanup in exception handlers
try:
    await asyncio.wait_for(approval_event.wait(), timeout=300)
except (asyncio.TimeoutError, Exception):
    pending_approvals.pop(approval_id, None)  # Use pop with default
    return PermissionResultDeny(message="Approval timed out")
```

---

## ⚠️ HIGH PRIORITY ISSUES - Should Fix Before Merge

### 4. Inconsistent Error Handling Between Brain Methods

**Location:** `src/koro/core/brain.py:100-186` vs `src/koro/core/brain.py:236-298`

**Problem:**
- `process_message()` raises exceptions for invalid input (line 125, 128)
- `process_message_stream()` also raises exceptions (line 257, 260)
- But there's no documentation about which exceptions callers should catch
- API endpoints don't have consistent error handling wrappers

**Example Issue in API:**
```python
# src/koro/api/routes/messages.py:80-88
response = await brain.process_message(...)  # Can raise ValueError, RuntimeError
# No try/except - errors will become 500 instead of 400
```

**Impact:**
- 400-level errors (bad input) returned as 500 Internal Server Error
- Poor API client experience
- Violates REST API best practices

**Fix Required:**
```python
# In api/routes/messages.py
try:
    response = await brain.process_message(...)
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
except RuntimeError as e:
    raise HTTPException(status_code=422, detail=str(e))
```

---

### 5. Missing Type Validation in QueryConfig Builder

**Location:** `src/koro/core/brain.py:188-234`

**Problem:**
- `_build_query_config()` accepts `**kwargs` and filters allowed keys
- No type validation before passing to `QueryConfig(**config_kwargs)`
- Runtime errors will be cryptic Pydantic validation errors

**Example:**
```python
await brain.process_message(
    user_id="123",
    content="hello",
    content_type=MessageType.TEXT,
    max_turns="not_a_number"  # Should be int, but no validation until QueryConfig
)
```

**Impact:** Poor error messages when callers pass wrong types

**Fix Required:**
```python
def _build_query_config(self, ..., **kwargs) -> QueryConfig:
    # Add type hints to docstring
    # Or validate types explicitly before QueryConfig construction
    if "max_turns" in kwargs and not isinstance(kwargs["max_turns"], int):
        raise TypeError(f"max_turns must be int, got {type(kwargs['max_turns'])}")
    # ... similar for other fields
```

---

### 6. Race Condition in Global Singleton Initialization

**Location:** Multiple files (`brain.py:409-414`, `state.py:552-557`, etc.)

```python
def get_brain() -> Brain:
    """Get or create the default brain instance."""
    global _brain
    if _brain is None:
        _brain = Brain()
    return _brain
```

**Problem:**
- Not thread-safe (though Python GIL provides some protection)
- More critically: async race condition if multiple coroutines call simultaneously
- First to check `_brain is None` all create instances, last one wins

**Impact:** In high-concurrency scenarios (FastAPI under load), multiple Brain instances could be created, leading to:
- Multiple database connections
- Inconsistent state across instances
- Resource leaks

**Fix Required:**
```python
import asyncio

_brain: Brain | None = None
_brain_lock = asyncio.Lock()

async def get_brain() -> Brain:
    """Get or create the default brain instance (async-safe)."""
    global _brain
    if _brain is None:
        async with _brain_lock:
            if _brain is None:  # Double-check pattern
                _brain = Brain()
    return _brain
```

Or use dependency injection pattern instead of global singletons (recommended).

---

### 7. Incomplete Migration from JSON to SQLite

**Location:** `src/koro/core/state.py:93-169`

**Problem:**
- Migration runs on first access, not on startup
- If migration fails, it logs warning but continues (line 129, 159)
- `migration_failed` flag prevents marking migration complete, but doesn't retry
- Future runs will attempt migration again and again

**Impact:**
- Failed migrations cause performance degradation (re-attempt on every startup)
- No alerting or clear indication that migration failed
- Users might lose data without knowing

**Fix Required:**
```python
def _migrate_from_json(self) -> None:
    with self._get_connection() as conn:
        result = conn.execute(
            "SELECT 1 FROM migration_status WHERE name = 'json_migration'"
        ).fetchone()
        if result:
            return

        errors = []

        # Migrate sessions
        if STATE_FILE.exists():
            try:
                # ... migration code ...
            except (json.JSONDecodeError, IOError) as e:
                errors.append(f"Sessions migration failed: {e}")
                logger.error("Sessions migration failed", exc_info=True)

        # Migrate settings
        if SETTINGS_FILE.exists():
            try:
                # ... migration code ...
            except (json.JSONDecodeError, IOError) as e:
                errors.append(f"Settings migration failed: {e}")
                logger.error("Settings migration failed", exc_info=True)

        if errors:
            # Mark as attempted but failed
            conn.execute(
                "INSERT INTO migration_status (name, completed_at) VALUES (?, ?)",
                ("json_migration_failed", datetime.now().isoformat()),
            )
            raise RuntimeError(f"Migration failed: {'; '.join(errors)}")

        # Mark as successful
        conn.execute(
            "INSERT INTO migration_status (name, completed_at) VALUES (?, ?)",
            ("json_migration", datetime.now().isoformat()),
        )
```

---

### 8. Authentication Bypass in Middleware

**Location:** `src/koro/api/middleware.py:38-50`

**Problem:**
- If `KOROMIND_API_KEY` is empty/None and `KOROMIND_ALLOW_NO_AUTH` is falsy, returns 503
- But the check `if not KOROMIND_ALLOW_NO_AUTH:` treats empty string as False
- Configuration with `KOROMIND_ALLOW_NO_AUTH=""` (empty string from env var) will allow access

**Security Issue:**
```bash
# .env file
KOROMIND_API_KEY=
KOROMIND_ALLOW_NO_AUTH=  # Empty string, not explicitly "false"

# Result: Empty ALLOW_NO_AUTH is falsy in Python, so line 40 passes
# But then line 46 sets user_id="local" and continues!
```

**Impact:** Potential authentication bypass with misconfigured environment variables

**Fix Required:**
```python
# Explicit boolean parsing
ALLOW_NO_AUTH = os.getenv("KOROMIND_ALLOW_NO_AUTH", "false").lower() in ("1", "true", "yes")

# Or in middleware
if not KOROMIND_API_KEY:
    # Explicitly check for true boolean value
    allow_no_auth = os.getenv("KOROMIND_ALLOW_NO_AUTH", "").lower() in ("1", "true", "yes")
    if not allow_no_auth:
        logger.error("KOROMIND_API_KEY not set - refusing unauthenticated access")
        return JSONResponse(status_code=503, content={"detail": "API key not configured"})
```

---

### 9. Unclear Session State After Claude Errors

**Location:** `src/koro/core/brain.py:165-168`

```python
# Call Claude
response_text, new_session_id, metadata = await self.claude_client.query(config)

# Update session state
await self.state_manager.update_session(user_id, new_session_id)
```

**Problem:**
- If `claude_client.query()` returns error text (lines 230-265 in claude.py), it still returns a session_id
- Session is always updated even on error
- Unclear if session should be updated when Claude fails

**Impact:**
- Failed requests might corrupt session state
- Users might lose conversation context on errors

**Decision Needed:**
- Should session be updated on error responses?
- Should there be a separate error code path?

---

### 10. Rate Limiter Not Reset on Server Restart

**Location:** `src/koro/core/rate_limit.py` (rate limiter is in-memory only)

**Problem:**
- Rate limiting state stored in memory (dict)
- Server restart resets all rate limits
- Could be exploited by repeatedly restarting the service (if attacker has access)

**Impact:**
- Rate limits not persistent across restarts
- Not a direct security issue but reduces effectiveness of rate limiting

**Recommendation:**
- Move rate limit state to SQLite (like sessions/settings)
- Or document this limitation clearly

---

## ⚡ MEDIUM PRIORITY ISSUES - Consider Fixing

### 11. Inconsistent User ID Types

**Problem:** User IDs are mixed between `int` and `str` throughout codebase
- Telegram handlers use `int` (user_id from Telegram API)
- StateManager internally converts to `str`
- API uses `str` (derived from API key hash)
- Legacy methods like `get_user_state(user_id: int)` still exist

**Impact:**
- Type confusion
- Potential bugs when comparing IDs
- Makes testing harder

**Recommendation:** Standardize on `str` everywhere, document conversion at boundaries.

---

### 12. Missing Database Connection Pooling

**Location:** `src/koro/core/state.py:83-91`

**Problem:**
- New SQLite connection created per operation
- No connection pooling
- Each query opens/closes connection

**Impact:**
- Performance overhead (minor for SQLite)
- Could hit connection limits under high load

**Recommendation:** Use connection pooling or keep connection open per request.

---

### 13. No Telemetry on Tool Call Failures

**Location:** `src/koro/core/brain.py:148-151`

**Problem:**
- Tool calls tracked in `tool_calls` list
- No tracking of tool success/failure
- Callback only receives name and detail, not outcome

**Impact:**
- Hard to debug tool execution issues
- No metrics on tool reliability

**Recommendation:** Extend `ToolCall` type to include `success: bool | None` and populate after execution.

---

### 14. Voice Engine Error Messages Lost in Production

**Location:** `src/koro/core/brain.py:127-128`

```python
if text.startswith("[Transcription error") or text.startswith("[Error"):
    raise RuntimeError(text)
```

**Problem:**
- Error detection by string prefix is fragile
- Voice engine could return text starting with "[Error" legitimately
- Error details lost (just re-raised as RuntimeError string)

**Recommendation:**
- Return structured error types from voice engine
- Use custom exceptions for voice errors

---

### 15. Incomplete Test Coverage for New Brain API

**Observation:**
- New `Brain` class has extensive functionality
- Tests exist but may not cover all edge cases (especially streaming)
- No tests for `process_message_stream()` session update logic (the buggy code from Critical Issue #1)

**Recommendation:** Add integration tests for streaming mode before merge.

---

## 📋 ADDITIONAL OBSERVATIONS (Non-Blocking)

### Architecture Improvements ✅
- Clean separation of concerns (core, api, interfaces)
- Good use of dependency injection in Brain
- Protocol-based typing in types.py
- SQLite migration from JSON is well-structured

### Documentation ✅
- Excellent spec-driven approach in `.ai/specs/`
- AGENTS.md provides clear coding guidelines
- Good docstrings on public methods

### Testing ✅
- Comprehensive test suite migration to `src/tests/`
- Good use of fixtures in conftest.py
- Integration tests properly marked with `@pytest.mark.live`

### Code Quality Issues ⚠️
- Some files exceed 500 lines (brain.py: 420, state.py: 564, claude.py: 380)
- Consider splitting into smaller modules
- Type hints are good but inconsistent (`str | None` vs `Optional[str]`)

---

## 🎯 RECOMMENDATIONS FOR MERGE

### Before Merging:
1. **MUST FIX:**
   - Critical Issue #1: StreamEvent session_id bug
   - Critical Issue #2: SQL injection in state.py
   - Critical Issue #3: Memory leak in pending_approvals

2. **SHOULD FIX:**
   - High Priority Issues #4-7 (error handling, type validation, concurrency, migration)
   - High Priority Issue #8 (authentication bypass risk)

3. **TESTING REQUIRED:**
   - Add tests for streaming mode session updates
   - Test authentication middleware with various env var configurations
   - Test concurrent singleton initialization
   - Test migration failure scenarios

### After Merging (Follow-up PRs):
- Medium priority issues (#11-15)
- Performance optimization (connection pooling)
- Enhanced telemetry and monitoring

---

## 📊 RISK ASSESSMENT

**Overall Risk Level: HIGH**

**Reasoning:**
- 3 critical security/reliability issues
- Large architectural change (8,400 LOC changed)
- Insufficient test coverage for new streaming functionality
- Authentication and session management have edge cases

**Merge Recommendation: DO NOT MERGE** until critical issues are resolved and additional tests are added.

---

## 🔍 TESTING CHECKLIST

Before merging, verify:
- [ ] Streaming mode works without AttributeError
- [ ] Pending approvals cleanup under various failure scenarios
- [ ] Authentication with missing/empty env vars
- [ ] Migration from JSON files (both success and failure)
- [ ] Concurrent access to Brain/StateManager singletons
- [ ] Error responses return correct HTTP status codes (400 vs 500)
- [ ] Rate limiting persists correctly
- [ ] Session state after Claude errors

---

**Review Complete**
Generated: 2026-02-01
Reviewer: Elite Code Review Expert (AI-Assisted)
