# Strict Pydantic Configs

**Lesson from PR #35 review**

## The Rule

Config models should use `extra="forbid"` and `Field(default_factory=...)` for mutable defaults.

## Why

### extra="forbid"

| extra="allow" (default) | extra="forbid" |
|--------------------------|----------------|
| Typos silently ignored | Typos raise ValidationError |
| "Why isn't my config working?" | Immediate feedback on wrong key |
| Stale keys accumulate | Clean configs only |

### default_factory

| Bare `= {}` / `= []` | `Field(default_factory=dict)` |
|------------------------|-------------------------------|
| Shared mutable reference risk | Fresh instance per model |
| Works in Pydantic but misleading | Explicit intent, safe everywhere |
| Fails in dataclasses | Consistent across Pydantic + dataclasses |

## How

```python
# BAD
class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    hooks: dict[str, list[Hook]] = {}
    plugins: list[str] = []

# GOOD
class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    hooks: dict[str, list[Hook]] = Field(default_factory=dict)
    plugins: list[str] = Field(default_factory=list)
```

## Exception

Use `extra="allow"` only when the model wraps external schemas you don't control (e.g., MCP server configs that may have arbitrary fields like `env`, `url`).

## Checklist

- [ ] Config models use `extra="forbid"`
- [ ] Mutable defaults use `Field(default_factory=...)`
- [ ] External/third-party schemas documented if using `extra="allow"`
