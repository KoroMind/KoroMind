---
id: SVC-010
type: service
status: active
severity: critical
issue: 36
validated: 2026-02-01
---

# Claude SDK Service

## What
- Python wrapper for Claude Agent SDK (`claude-agent-sdk`)
- Exposes full SDK capabilities: streaming, hooks, MCP, agents, plugins
- Handles auth via OAuth token or API key

## Why
- Single interface for all Claude interactions
- Abstracts SDK complexity from Brain/interfaces
- Enables full Claude Code feature parity

## How

### Core: `src/koro/core/claude.py`

```
ClaudeClient
├── query()           → Full response with metadata
├── query_stream()    → AsyncIterator of events
├── interrupt()       → Stop active query
└── health_check()    → Verify connectivity
```

### Authentication

Priority order (first wins):
1. `CLAUDE_CODE_OAUTH_TOKEN` - OAuth token from `claude setup-token`
2. Claude Code login (stored in keychain via `/login`)
3. `ANTHROPIC_API_KEY` - Direct API key (pay-as-you-go)

**Getting OAuth token:**
```bash
claude setup-token  # Generates token, save to credentials.json
export CLAUDE_CODE_OAUTH_TOKEN=$(cat credentials.json | jq -r '.claude_token')
```

### SDK Options Supported

| Option | Type | Purpose |
|--------|------|---------|
| `model` | str | Model to use |
| `max_turns` | int | Max agentic turns |
| `hooks` | dict | Lifecycle hooks |
| `mcp_servers` | dict | MCP server configs |
| `agents` | dict | Subagent definitions |
| `plugins` | list | SDK plugins |
| `sandbox` | SandboxSettings | Sandbox config |
| `output_format` | OutputFormat | Structured output |
| `max_budget_usd` | float | Cost limit |

### Response Metadata

```python
result, session_id, metadata = await client.query(prompt)
# metadata contains:
# - cost: float (USD)
# - num_turns: int
# - duration_ms: int
# - usage: dict (tokens)
# - tool_count: int
# - thinking: str (if extended thinking)
# - structured_output: dict (if requested)
# - is_error: bool
```

### Debug Logging

Enable with `DEBUG` log level:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Logs at key points:
- Client initialization (auth env vars)
- Options building
- Query start/complete
- Health check subprocess output

## Test
- Health check passes with valid auth
- Query returns response and session ID
- Session continuation preserves context
- Tool callbacks invoked
- Streaming yields events incrementally
- Interrupt stops active query
- All SDK options passed through

## Changelog

### 2026-02-01
- Added debug logging throughout
- Fixed OAuth token auth (CLAUDE_CODE_OAUTH_TOKEN)

### 2026-01-31
- Initial implementation with full SDK support
- Added streaming, interrupt, hooks, MCP, agents
