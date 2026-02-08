# Use model_dump() Over Manual Field Extraction

**Lesson from PR #35 review**

## The Rule

When extracting fields from a Pydantic model into a dict, use `model_dump()` with `include`/`exclude` instead of manual `getattr` loops.

## Why

| Manual getattr | model_dump() |
|----------------|-------------|
| Verbose loop, easy to miss fields | Declarative, one line |
| No built-in None/default filtering | `exclude_none`, `exclude_defaults` |
| Must manually maintain field list | Model schema is the source of truth |
| Silent bugs if field is renamed | Pydantic validates field names |

## How

```python
# BAD: manual getattr loop
config_kwargs = {}
for field in ("hooks", "mcp_servers", "sandbox", "plugins"):
    value = getattr(vault_config, field)
    if value:
        config_kwargs[field] = value

# GOOD: model_dump with filtering
vault_data = vault_config.model_dump(
    exclude_none=True,
    exclude_defaults=True,
    include={"hooks", "mcp_servers", "sandbox", "plugins"},
)
config_kwargs.update(vault_data)
```

## Exception

If a field needs transformation (e.g., `AgentConfig` -> SDK `AgentDefinition`), handle it separately after the dump.

## Checklist

- [ ] Using `model_dump()` instead of getattr loops for field extraction
- [ ] Using `include`/`exclude` to select fields
- [ ] Using `exclude_none`/`exclude_defaults` to filter empties
- [ ] Fields needing transformation handled separately
