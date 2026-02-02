# Source Code Guidelines

Coding rules and guardrails for working in the `src/` directory.

## Coding Guardrails

- Avoid `hasattr`/`setattr` in core logic; use typed models with known attributes
- Prefer `@dataclass(frozen=True)` unless mutation is required and explicit
- Avoid optional containers for `list`/`dict`; use empty defaults instead
- Use `Protocol` for callback types instead of ad-hoc `Callable` aliases
- Use a config object when functions exceed ~5 parameters
- Extract shared logic to helpers to avoid duplication
- Raise exceptions for invalid inputs in core paths; don't yield error dicts
- Use Pydantic models when parsing external JSON or user-provided config
- Use Pydantic validators for type checks instead of manual validation in callers
- Normalize identifiers (e.g., user_id) at system boundaries
- Do not interpolate SQL identifiers or values; use explicit statements and parameters
- Avoid inline imports in core code unless resolving a hard cycle

## Python Best Practices

### Asyncio / Non-Blocking I/O

- Use `aiofiles` for file operations in async contexts
- Use async HTTP clients (`httpx.AsyncClient`) instead of `requests`
- Use `asyncio.sleep()` instead of `time.sleep()` in async functions
- Load static resources (prompts, config files) at app startup, not per-request

### Exception Handling

- Catch specific exceptions (`ValueError`, `KeyError`, `httpx.HTTPError`), never bare `except Exception`
- Keep try blocks small and focused around the specific operation that may fail
- Let exceptions propagate to framework handlers when you can't meaningfully handle them
- Don't wrap entire function bodies in try/except—isolate the risky operation
- Use typed exceptions for domain errors (avoid stringly-typed error signaling)

### Code Organization

- Keep all imports at module top level, not inside functions
- Return new objects instead of mutating parameters as side effects, use immutable structures (frozen=True) if possible
- If mutation is unavoidable, make it explicit in the function name (e.g., `append_to_list()`)
- Guard singleton initialization in concurrent contexts (lock or DI)
- Add scheduled cleanup for in-memory caches with TTLs

### Defensive Programming

- Avoid defensive programming in core logic; trust internal invariants.
- Validate inputs at system boundaries (user input, external APIs)
- Trust internal code and framework guarantees—don't over-validate
- Make function behavior explicit through clear naming
- Prefer non-optional domain models; pass explicit defaults instead of `None`

## Refactoring Learnings

These learnings come from actual mistakes made in this codebase. Follow them to avoid repeat issues.

### Complete the Refactoring Chain

When changing a return type or data structure, update **all** consumers:

```python
# BAD: Changed get_user_settings() to return UserSettings, but handlers still do:
settings["audio_enabled"]  # TypeError: UserSettings is not subscriptable

# GOOD: Update all consumers to use attribute access:
settings.audio_enabled
```

**Checklist when changing a function's return type:**
1. Find all callers with grep/search
2. Update each caller's access pattern
3. Update tests to use the new type (not the old one)
4. Re-fetch after mutations—don't read stale local copies

### Avoid Stale Data After Mutations

```python
# BAD: Mutate local variable, then read from it after DB update
settings = state_manager.get_user_settings(user_id)
state_manager.update_setting(user_id, "audio_enabled", not settings.audio_enabled)
# settings still has OLD value here!
audio_status = "ON" if settings.audio_enabled else "OFF"  # Wrong!

# GOOD: Re-fetch after mutation
state_manager.update_setting(user_id, "audio_enabled", not settings.audio_enabled)
settings = state_manager.get_user_settings(user_id)  # Fresh data
audio_status = "ON" if settings.audio_enabled else "OFF"  # Correct
```

### Pydantic + Type Compatibility

Pydantic has limitations with certain Python types:

```python
# BAD: Protocol types can't be validated by Pydantic
class QueryConfig(BaseModel):
    on_tool_call: OnToolCall | None = None  # Pydantic can't validate Protocol

# GOOD: Use a concrete callable type (and validate explicitly if needed)
class QueryConfig(BaseModel):
    on_tool_call: Callable[[ToolCall], None] | None = None

# BAD: Replacing precise SDK types with Any loses validation and type safety
hooks: dict[str, Any] = Field(default_factory=dict)

# GOOD: Keep precise SDK types; use Pydantic config/validators if needed
hooks: dict[HookEvent, list[HookMatcher]] = Field(default_factory=dict)
```

### Test Data Must Match Production Types

```python
# BAD: Tests pass dicts when production code expects dataclass
settings = {"audio_enabled": False}  # Test fixture
result = build_dynamic_prompt(base, settings)  # Fails if function expects UserSettings

# GOOD: Tests use the same types as production
settings = UserSettings(audio_enabled=False)
result = build_dynamic_prompt(base, settings)
```

### Python Version Awareness

Before using a feature, verify it works with the project's minimum Python version:

- `typing.TypedDict` + Pydantic validation is supported on Python 3.12+
- `from __future__ import annotations` can break Protocol + Pydantic combos
- When in doubt, check `pyproject.toml` for `requires-python`
