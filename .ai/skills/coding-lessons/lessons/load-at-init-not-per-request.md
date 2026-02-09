# Load at Init, Not Per Request

**Lesson from PR #40 review (Phase 3)**

## The Rule

Static resources (files, configs, templates) should be loaded once at initialization, not on every request. Especially in async code — sync file I/O in a request path blocks the event loop.

## Why

| Per-request loading | Init-time loading |
|--------------------|-------------------|
| Sync `Path.read_text()` blocks event loop | File read happens once at startup |
| Repeated I/O for static content | Zero I/O at request time |
| File disappears mid-service → request fails | File disappears → caught at startup |
| N requests = N file reads | N requests = 0 file reads |

## How

```python
# BAD: File read on every request
class Brain:
    @staticmethod
    def _vault_agents_to_sdk(agents: dict[str, AgentConfig]):
        for name, agent in agents.items():
            prompt = agent.prompt or ""
            if agent.prompt_file:
                path = Path(agent.prompt_file)
                if path.exists():
                    prompt = path.read_text()  # Sync I/O per request!

# GOOD: Pre-load in model_post_init at config parse time
class AgentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    prompt: str | None = None
    prompt_file: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.prompt_file:
            path = Path(self.prompt_file)
            if path.exists():
                object.__setattr__(self, "prompt", path.read_text())
            else:
                logger.warning(f"Prompt file not found: {path}")

# Now Brain just reads the pre-loaded field — zero I/O
@staticmethod
def _vault_agents_to_sdk(agents):
    return {
        name: AgentDefinition(prompt=agent.prompt or "default")
        for name, agent in agents.items()
    }
```

## When to Apply

- Config files referenced by path → read at config parse time
- Template files → read at startup
- Static assets → load into memory once
- **Exception**: Large files that shouldn't live in memory → use async I/O

## Checklist

- [ ] No `Path.read_text()` or `open()` in request-handling code
- [ ] File contents pre-loaded in `__init__`, `model_post_init`, or startup
- [ ] Missing files logged at load time, not silently skipped at request time
- [ ] Request-path code uses only in-memory data
