# Typed Boundaries

**Lesson from PR #35 review**

## The Rule

Parse external data into typed models at the boundary. Never pass `dict[str, Any]` through your codebase.

## Why

| Raw dict | Typed model |
|----------|-------------|
| Errors surface deep in code | Errors surface at load time |
| `isinstance()` checks everywhere | Trust the types |
| "What keys exist?" - go read YAML | IDE autocomplete tells you |
| Accidental mutation | Frozen = immutable |
| Schema lives in docs (maybe) | Schema IS the code |

## How

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

## Checklist

- [ ] External data (YAML, JSON, API) → Pydantic model immediately
- [ ] Model is frozen (`frozen=True`)
- [ ] No `dict[str, Any]` in function signatures
- [ ] No `isinstance()` for structure validation
- [ ] Nested structures get their own models
