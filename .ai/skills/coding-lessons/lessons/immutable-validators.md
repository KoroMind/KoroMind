# Immutable Validators

**Lesson from PR #35 review**

## The Rule

Pydantic validators should not mutate input data, and should use proper type annotations for framework parameters.

## Why

### Don't mutate input

| Mutating `data` | Copying first |
|-----------------|---------------|
| Caller's dict silently changed | Original data preserved |
| Spooky action at a distance | Pure function, no side effects |
| Hard to debug shared-dict bugs | Safe to reuse input elsewhere |

### Type validator params

| `info: Any` | `info: ValidationInfo` |
|-------------|------------------------|
| No autocomplete | Full IDE support |
| No type checking | mypy catches misuse |
| "What's on info?" - read docs | `.context`, `.field_name` discoverable |

## How

```python
from pydantic import ValidationInfo, model_validator

# BAD: mutates input, untyped params
@model_validator(mode="before")
@classmethod
def transform(cls, data: Any, info: Any) -> Any:
    data["key"] = transformed_value  # mutates caller's dict!
    return data

# GOOD: copies input, typed params
@model_validator(mode="before")
@classmethod
def transform(cls, data: Any, info: ValidationInfo) -> Any:
    if not isinstance(data, dict):
        return data
    new_data = dict(data)
    new_data["key"] = transformed_value
    return new_data
```

## Also: Separate I/O error types

When loading files in validators, catch I/O and parse errors separately:

```python
# BAD: OSError propagates raw
try:
    with open(path) as f:
        parsed = json.load(f)
except json.JSONDecodeError as e:
    raise ConfigError(...) from e

# GOOD: both wrapped in domain error
try:
    parsed = json.loads(path.read_text(encoding="utf-8"))
except OSError as e:
    raise ConfigError(f"Failed to read {path}: {e}") from e
except json.JSONDecodeError as e:
    raise ConfigError(f"Invalid JSON in {path}: {e}") from e
```

## Checklist

- [ ] `mode="before"` validators copy `data` before mutating
- [ ] Validator `info` parameter typed as `ValidationInfo`
- [ ] File I/O catches `OSError` and parse errors separately
- [ ] All errors wrapped in domain exception type
