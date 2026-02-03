# Normalize at Boundaries

**Lesson from full-sdk-impl branch review**

## The Rule

Pick one canonical form for IDs and types. Convert at system boundaries, use consistently inside.

## Why

| Mixed types | Normalized |
|-------------|------------|
| `user_id == 123` vs `"123"` fails | Comparison always works |
| Dict keys inconsistent | Lookups reliable |
| Bugs only in some code paths | Consistent behavior |
| "Works sometimes" | Works always |

## How

```python
# BAD: Mixed int/str user IDs throughout codebase
async def handle_message(update: Update):
    user_id = update.effective_user.id  # int from Telegram
    settings = get_settings(user_id)     # Expects str? int? Who knows

async def handle_callback(update: Update):
    user_id = str(update.effective_user.id)  # str here
    settings = get_settings(user_id)          # Different type

# GOOD: Normalize at boundary, use str everywhere
def normalize_user_id(user_id: int | str) -> str:
    return str(user_id)

async def handle_message(update: Update):
    user_id = normalize_user_id(update.effective_user.id)
    settings = get_settings(user_id)  # Always str

async def handle_callback(update: Update):
    user_id = normalize_user_id(update.effective_user.id)
    settings = get_settings(user_id)  # Always str
```

## Common Boundaries

| Boundary | Normalize |
|----------|-----------|
| API input | IDs to str, dates to datetime |
| Database read | Row to Pydantic model |
| External service | Response to typed model |
| Environment vars | str to typed config |

## Pick a Side and Stick

| Type | Canonical Form | Why |
|------|----------------|-----|
| User IDs | `str` | JSON-safe, database-safe |
| Timestamps | `datetime` | Arithmetic, comparison |
| Money | `Decimal` or `int` cents | No float errors |
| Paths | `Path` | Cross-platform |

## Checklist

- [ ] IDs converted to canonical type at entry point
- [ ] No type conversion deep in business logic
- [ ] Type hints match canonical form everywhere
- [ ] Tests use canonical form (not mixed)
