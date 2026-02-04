# Refactoring Chain

**Lesson from KoroMind refactoring mistakes**

## The Rule

When changing a return type or data structure, update **all** consumers. Don't leave callers using the old access pattern.

## Why

| Incomplete refactor | Complete refactor |
|---------------------|-------------------|
| Runtime errors in production | Caught at dev time |
| Tests pass (using old types) | Tests use real types |
| Stale data bugs | Fresh data after mutations |

## How

### Update All Consumers

```python
# BAD: Changed get_user_settings() to return UserSettings, but handlers still do:
settings["audio_enabled"]  # TypeError: UserSettings is not subscriptable

# GOOD: Update all consumers to use attribute access:
settings.audio_enabled
```

### Re-fetch After Mutations

```python
# BAD: Read from stale local variable after DB update
settings = state_manager.get_user_settings(user_id)
state_manager.update_setting(user_id, "audio_enabled", not settings.audio_enabled)
# settings still has OLD value here!
audio_status = "ON" if settings.audio_enabled else "OFF"  # Wrong!

# GOOD: Re-fetch after mutation
state_manager.update_setting(user_id, "audio_enabled", not settings.audio_enabled)
settings = state_manager.get_user_settings(user_id)  # Fresh data
audio_status = "ON" if settings.audio_enabled else "OFF"  # Correct
```

### Tests Must Use Production Types

```python
# BAD: Tests pass dicts when production code expects dataclass
settings = {"audio_enabled": False}  # Test fixture
result = build_dynamic_prompt(base, settings)  # Fails if function expects UserSettings

# GOOD: Tests use the same types as production
settings = UserSettings(audio_enabled=False)
result = build_dynamic_prompt(base, settings)
```

## Pydantic Gotchas

```python
# BAD: Protocol types can't be validated by Pydantic
class QueryConfig(BaseModel):
    on_tool_call: OnToolCall | None = None  # Pydantic can't validate Protocol

# GOOD: Use concrete callable type
class QueryConfig(BaseModel):
    on_tool_call: Callable[[ToolCall], None] | None = None

# BAD: Replacing SDK types with Any loses validation
hooks: dict[str, Any] = Field(default_factory=dict)

# GOOD: Keep precise SDK types
hooks: dict[HookEvent, list[HookMatcher]] = Field(default_factory=dict)
```

## Checklist

- [ ] Found all callers with grep/search?
- [ ] Updated each caller's access pattern?
- [ ] Tests use production types, not dicts?
- [ ] Re-fetch after mutations, not reading stale copies?
- [ ] Checked Python version compatibility for type features?
