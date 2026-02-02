# Code Smells and Fixes

This file captures code smells discovered during the PR #34 review and the fixes applied, so future changes avoid repeating them.

## 1) Streaming session update used non‑Result events
- **Smell:** `StreamEvent` does not expose `session_id`, but code accessed it in streaming updates.
- **Risk:** Runtime `AttributeError` in streaming mode.
- **Fix:** Update session only for `ResultMessage` events.
- **Pattern to follow:** Always narrow event types before accessing attributes.

## 2) SQL column interpolation in updates
- **Smell:** `f"UPDATE settings SET {column} = ?"` with string interpolation.
- **Risk:** SQL injection vector if the column map changes.
- **Fix:** Use explicit per‑column updates with parameterized values.
- **Pattern to follow:** Parameterize values; never interpolate SQL identifiers from runtime input.

## 3) pending_approvals memory growth
- **Smell:** In‑memory approval cache only cleaned on new approvals and incomplete error cleanup.
- **Risk:** Unbounded memory growth and stale approvals.
- **Fix:** Add periodic cleanup task; ensure `pop(..., None)` on timeout/cancel paths.
- **Pattern to follow:** Any in‑memory cache with TTL must have scheduled cleanup and exception‑safe removal.

## 4) API error handling leaked 500s
- **Smell:** Exceptions from core (`ValueError`, `RuntimeError`) bubbled to 500.
- **Risk:** Incorrect HTTP semantics and poor client experience.
- **Fix:** Map input errors to 400 and transcription errors to 422.
- **Pattern to follow:** API layers must translate known domain errors to explicit status codes.

## 5) Singleton initialization race
- **Smell:** Global singletons created without synchronization.
- **Risk:** Multiple instances under concurrency (resource leaks, state divergence).
- **Fix:** Double‑checked lock around singleton creation.
- **Pattern to follow:** Guard singleton creation or use DI in framework.

## 6) JSON → SQLite migration retries forever
- **Smell:** Migration failure not recorded; retried every start with no signal.
- **Risk:** Performance hits, silent data loss.
- **Fix:** Record failed migrations and raise with details.
- **Pattern to follow:** Persist migration status for both success and failure.

## 7) Session updated on Claude error
- **Smell:** Session updated even when Claude returned an error response.
- **Risk:** Session state corruption or unexpected context jumps.
- **Fix:** Skip session update when metadata indicates error.
- **Pattern to follow:** Only persist session changes for successful responses.

## 8) Voice errors encoded as strings
- **Smell:** Voice errors returned as strings and detected via prefix checks.
- **Risk:** Fragile detection and false positives.
- **Fix:** Raise structured exceptions (`VoiceError`, `VoiceTranscriptionError`).
- **Pattern to follow:** Use typed exceptions for error signaling.

## 9) Rate limiter state lost on restart
- **Smell:** In‑memory rate limit tracking only.
- **Risk:** Limits reset on restart; easy to bypass.
- **Fix:** Persist limits to SQLite and add tests for persistence.
- **Pattern to follow:** Persist security/abuse controls across restarts.

## 10) Inconsistent user_id types
- **Smell:** Telegram handlers used `int` while core used `str`.
- **Risk:** Type drift and mismatched state lookups.
- **Fix:** Normalize Telegram user IDs to `str` at boundaries.
- **Pattern to follow:** Standardize identifiers at system boundaries.

## 11) Tool telemetry missing
- **Smell:** Tool calls tracked without outcome.
- **Risk:** No visibility into tool failures.
- **Fix:** Track tool results (tool_use_id + is_error) in metadata.
- **Pattern to follow:** Emit success/failure data for tool execution.

## 12) QueryConfig validation done manually in Brain
- **Smell:** `_build_query_config` performed ad‑hoc type checks.
- **Risk:** Duplicated logic and drift from model definition.
- **Fix:** Move validation to Pydantic validators in `QueryConfig`.
- **Pattern to follow:** Keep validation inside the model.

## 13) Inline imports of core types
- **Smell:** Imports inside functions (e.g., `from koro.core.types import Mode`).
- **Risk:** Hidden dependencies and harder static analysis.
- **Fix:** Move imports to module top level.
- **Pattern to follow:** Keep imports at module scope unless there is a real cycle.

## 14) Optional `UserSettings` in prompt building
- **Smell:** Prompt building accepted `None` and handled `None` checks.
- **Risk:** Weakened contract and extra branches.
- **Fix:** Require `UserSettings` for prompt building; pass defaults explicitly.
- **Pattern to follow:** Prefer non‑optional domain models and explicit defaults.
