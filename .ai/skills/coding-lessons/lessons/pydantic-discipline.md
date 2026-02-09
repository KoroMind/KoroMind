# Pydantic Discipline

**Lesson from PR #35 and #40 reviews**

## The Rule

Configure Pydantic models strictly, write validators safely.

## Model Configuration

```python
# BAD
class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")
    hooks: dict[str, list[Hook]] = {}

# GOOD
class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    hooks: dict[str, list[Hook]] = Field(default_factory=dict)
```

| Setting | Why |
|---------|-----|
| `extra="forbid"` | Typos raise ValidationError instead of silently passing |
| `Field(default_factory=...)` | Fresh mutable instance per model, no shared reference |
| `frozen=True` | Prevents accidental mutation after construction |

**Exception:** `extra="allow"` only for external schemas you don't control (e.g., MCP server configs).

## Validator Safety

```python
# BAD: mutates input, untyped params
@model_validator(mode="before")
@classmethod
def transform(cls, data: Any, info: Any) -> Any:
    data["key"] = value  # mutates caller's dict!
    return data

# GOOD: copies input, typed params
@model_validator(mode="before")
@classmethod
def transform(cls, data: Any, info: ValidationInfo) -> Any:
    if not isinstance(data, dict):
        return data
    new_data = dict(data)
    new_data["key"] = value
    return new_data
```

## I/O in Validators

Catch I/O and parse errors separately, wrap in domain error:

```python
try:
    parsed = json.loads(path.read_text(encoding="utf-8"))
except OSError as e:
    raise ConfigError(f"Failed to read {path}: {e}") from e
except json.JSONDecodeError as e:
    raise ConfigError(f"Invalid JSON in {path}: {e}") from e
```

## Checklist

- [ ] Models use `extra="forbid"` (document exceptions)
- [ ] Mutable defaults use `Field(default_factory=...)`
- [ ] Models are `frozen=True`
- [ ] `mode="before"` validators copy `data` before mutating
- [ ] Validator `info` typed as `ValidationInfo`
- [ ] File I/O in validators catches `OSError` + parse errors separately
