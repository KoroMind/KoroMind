# Parameter Objects

**Lesson from full-sdk-impl branch review**

## The Rule

When a function has more than 5 parameters, consolidate into a config object.

## Why

| Many params | Config object |
|-------------|---------------|
| Hard to remember order | Named fields, IDE autocomplete |
| Easy to miss one | Pydantic validates required fields |
| Breaking change to add param | Add optional field, no breakage |
| Defaults scattered in signatures | Defaults centralized in model |
| No validation | Validators run at construction |

## How

```python
# BAD: 15 parameters, growing
async def query(
    prompt: str,
    session_id: str,
    user_settings: dict,
    mode: str,
    on_tool_call: Callable,
    can_use_tool: Callable,
    max_turns: int = 10,
    max_budget_usd: float | None = None,
    hooks: dict | None = None,
    mcp_servers: dict | None = None,
    # ... 5 more
) -> Response:
    ...

# GOOD: Single config object
class QueryConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt: str
    session_id: str
    user_settings: UserSettings
    mode: Mode = Mode.GO_ALL
    on_tool_call: OnToolCall | None = None
    can_use_tool: CanUseTool | None = None
    max_turns: int = 10
    max_budget_usd: float | None = None

    @field_validator("max_turns")
    @classmethod
    def validate_max_turns(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_turns must be positive")
        return v

async def query(config: QueryConfig) -> Response:
    ...
```

## When to Use

- **5+ parameters** → Consider config object
- **Optional parameters growing** → Definitely use config object
- **Parameters have validation logic** → Config object with validators
- **Same params passed through multiple layers** → Config object

## Benefits Beyond Cleanliness

```python
# Easy to extend
config = base_config.model_copy(update={"max_turns": 50})

# Easy to test
test_config = QueryConfig(prompt="test", session_id="123", ...)

# Easy to log/debug
logger.debug(f"Query config: {config.model_dump()}")
```

## Checklist

- [ ] Function has >5 params? → Create config model
- [ ] Config is frozen (immutable)
- [ ] Validators for constraints (positive ints, valid enums)
- [ ] Use `model_copy(update={})` for variations
