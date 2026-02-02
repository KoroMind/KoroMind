# Code Smells and Fixes (Generalized)

This file captures generalized smells observed during the PR review and how they were fixed, so future changes avoid repeating them.

## 1) Type‑unsafe event handling in streams
- **Smell:** Accessing attributes on heterogeneous stream events without narrowing types.
- **Risk:** Runtime attribute errors when event shapes differ.
- **Fix:** Narrow event types before reading fields; restrict session updates to result‑bearing events.
- **Pattern to follow:** Always narrow event types before accessing attributes.

## 2) SQL string interpolation
- **Smell:** Interpolating SQL identifiers or values into query strings.
- **Risk:** Injection, fragile queries, and security regressions.
- **Fix:** Use explicit statements and parameterized values.
- **Pattern to follow:** Never interpolate SQL identifiers from runtime input.

## 3) In‑memory caches without lifecycle controls
- **Smell:** TTL caches cleaned only on writes and missing cleanup on error paths.
- **Risk:** Memory leaks and stale state.
- **Fix:** Add scheduled cleanup and exception‑safe removal.
- **Pattern to follow:** Any TTL cache needs periodic cleanup and safe eviction.

## 4) API layers leaking core exceptions
- **Smell:** Core exceptions bubble to generic 500 errors.
- **Risk:** Incorrect HTTP semantics and poor client UX.
- **Fix:** Map known domain errors to explicit status codes.
- **Pattern to follow:** API layers translate domain errors to HTTP responses.

## 5) Unsynchronized singleton initialization
- **Smell:** Global singletons created without locks in concurrent contexts.
- **Risk:** Multiple instances, inconsistent state, resource leaks.
- **Fix:** Guard creation with locks or dependency injection.
- **Pattern to follow:** Synchronize singleton creation in concurrent runtimes.

## 6) Migrations without failure recording
- **Smell:** Migration failures not recorded and silently retried.
- **Risk:** Repeated failures, performance hits, silent data loss.
- **Fix:** Persist success/failure markers and surface errors.
- **Pattern to follow:** Record migration outcomes in durable storage.

## 7) Persisting state on failed operations
- **Smell:** State updated even when upstream operations fail.
- **Risk:** Corrupted or inconsistent state.
- **Fix:** Only persist state for successful outcomes.
- **Pattern to follow:** Guard persistence behind success criteria.

## 8) Stringly‑typed error signaling
- **Smell:** Errors returned as strings and detected via prefix checks.
- **Risk:** Fragile detection and false positives.
- **Fix:** Use typed exceptions and catch specific error classes.
- **Pattern to follow:** Prefer structured errors over string inspection.

## 9) Volatile security/abuse controls
- **Smell:** Rate limits or abuse controls stored only in memory.
- **Risk:** Reset on restart, easy to bypass.
- **Fix:** Persist to durable storage.
- **Pattern to follow:** Persist security controls across restarts.

## 10) Boundary type drift
- **Smell:** Identifiers change type across layers (e.g., int vs str).
- **Risk:** Mismatched lookups and subtle bugs.
- **Fix:** Normalize at system boundaries.
- **Pattern to follow:** Standardize identifier types at boundaries.

## 11) Missing tool execution outcomes
- **Smell:** Tool calls tracked without success/failure outcome.
- **Risk:** Poor observability and debugging.
- **Fix:** Capture tool results and errors in metadata.
- **Pattern to follow:** Emit success/failure telemetry for tool execution.

## 12) Validation outside models
- **Smell:** Manual validation in callers rather than model validators.
- **Risk:** Duplicated logic and drift from model definition.
- **Fix:** Move validation to Pydantic validators.
- **Pattern to follow:** Keep validation inside the model layer.

## 13) Inline imports
- **Smell:** Imports inside functions without a cyclic‑dependency reason.
- **Risk:** Hidden dependencies and analysis/tooling gaps.
- **Fix:** Move imports to module scope.
- **Pattern to follow:** Keep imports at module top level unless needed to break cycles.

## 14) Optional domain models where defaults exist
- **Smell:** Optional model parameters handled with `None` branches.
- **Risk:** Weaker contracts and extra branching.
- **Fix:** Require models and pass explicit defaults.
- **Pattern to follow:** Prefer non‑optional domain models; supply defaults explicitly.
