---
id: FEA-001
type: feature
status: active
severity: medium
issue: 35
validated: 2026-02-01
---

# Debug Logging

## What
- Structured logging across all core components
- Enabled via `--debug` CLI flag or programmatically
- Uses Python's standard `logging` module

## Why
- Trace config flow from vault → brain → claude → SDK
- Debug issues without modifying code
- Production-safe: off by default, minimal overhead

## How

### Logger Setup
Each module creates its own logger:
```python
import logging
logger = logging.getLogger(__name__)
```

### Enabling
```bash
# CLI
koro-cli chat --debug

# Programmatic
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Log Levels Used
| Level | When |
|-------|------|
| DEBUG | Config loading, option building, flow tracing |
| INFO | Vault loaded, session started |
| WARNING | Config file missing, fallback used |
| ERROR | YAML invalid, connection failed |

### Components with Logging
| Module | What's Logged |
|--------|---------------|
| `vault.py` | Config load, path resolution, cache hits |
| `brain.py` | Vault init, config merging, kwargs override |
| `claude.py` | Options built, query start/end, tool counts, errors |
| `cli/app.py` | Vault path resolution |

### Log Format (--debug)
```
HH:MM:SS koro.core.vault DEBUG: Loading config from /path/to/vault-config.yaml
HH:MM:SS koro.core.brain INFO: Brain initialized with vault: /path/to/vault
```

## Test
- --debug flag enables DEBUG level
- Without --debug, no debug output
- Errors logged at ERROR level
- No sensitive data in logs (no API keys, no prompts)

## Changelog

### 2026-02-01
- Initial logging implementation across vault, brain, claude, cli
