---
id: FEA-044
type: feature
status: active
severity: medium
issue: 44
validated: 2026-02-07
---

# Mypy CI Gate

## What
- Add static type checking with mypy as a CI gate for application code.
- Scope includes `src/koro` and explicitly excludes tests in `src/tests`.

## Why
- Catch type regressions before merge, especially in shared core/API/interface flows.
- Keep a fast, deterministic signal in PR checks alongside unit tests.

## How
- Define mypy config in `pyproject.toml` with Python 3.12 target and repository scope.
- Run mypy in a dedicated GitHub Actions CI job in `.github/workflows/ci.yml`.
- Install mypy via project dev dependencies to keep local/CI tool versions aligned.
- Keep `implicit_optional = true` for compatibility with current code style.

## Test
- Introduce a deliberate type mismatch in `src/koro` and verify CI `mypy` job fails.
- Remove the mismatch and verify CI `mypy` job passes.
- Verify `src/tests` changes alone do not affect mypy results.

## Changelog
- 2026-02-07: Added mypy configuration and dedicated CI type-check job for issue #44.
