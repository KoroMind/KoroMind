# Boundaries

**Lesson from PR #35 review**

## The Rule

Parse external data into typed models and normalize types at system boundaries. Never pass raw dicts or mixed types through your codebase.

## Parse at Entry

```python
# BAD: dict travels through the system
def load_config(path: str) -> dict[str, Any]:
    return yaml.safe_load(open(path))

def use_config(config: dict[str, Any]):
    if "model" in config and isinstance(config["model"], str):  # defensive
        ...

# GOOD: typed at the boundary
class Config(BaseModel):
    model_config = ConfigDict(frozen=True)
    model: str
    max_turns: int = 10

def load_config(path: str) -> Config:
    return Config.model_validate(yaml.safe_load(open(path)))

def use_config(config: Config):
    print(config.model)  # just use it
```

## Normalize at Entry

Pick one canonical form for IDs and types. Convert once, use everywhere.

```python
# BAD: Mixed int/str user IDs
user_id = update.effective_user.id      # int from Telegram
user_id = str(update.effective_user.id)  # str elsewhere

# GOOD: Normalize at boundary, str everywhere
def normalize_user_id(user_id: int | str) -> str:
    return str(user_id)

user_id = normalize_user_id(update.effective_user.id)
```

| Type | Canonical Form | Why |
|------|----------------|-----|
| User IDs | `str` | JSON-safe, database-safe |
| Timestamps | `datetime` | Arithmetic, comparison |
| Money | `Decimal` or `int` cents | No float errors |
| Paths | `Path` | Cross-platform |

## Common Boundaries

| Boundary | Action |
|----------|--------|
| API/webhook input | Parse into Pydantic model, normalize IDs |
| Database read | Row to typed model |
| YAML/JSON config | `model_validate()` immediately |
| Environment vars | Parse to typed config at startup |

## Checklist

- [ ] External data (YAML, JSON, API) → Pydantic model immediately
- [ ] No `dict[str, Any]` in function signatures
- [ ] IDs converted to canonical type at entry point
- [ ] No type conversion deep in business logic
- [ ] Nested structures get their own models
