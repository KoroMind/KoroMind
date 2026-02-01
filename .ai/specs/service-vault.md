---
id: SVC-009
type: service
status: active
severity: high
issue: 35
validated: 2026-02-01
---

# Vault Service

## What
- Loads configuration from `vault-config.yaml` in a vault directory
- Resolves relative paths to absolute paths within vault
- Passes SDK-compatible config to Brain → ClaudeClient

## Why
- Stateless configuration: no environment variables or runtime state
- Portable: copy vault directory, everything works
- User-friendly: one YAML file configures entire experience

## How
- Core: `src/koro/core/vault.py` - `Vault` class
- Integration: `src/koro/core/brain.py:168-181` - merges vault config into kwargs

### Config Flow
```
vault-config.yaml → Vault.load() → Brain.process_message() → ClaudeClient._build_options() → ClaudeAgentOptions
```

### Supported Options
| Option | Type | Path Resolution |
|--------|------|-----------------|
| `model` | string | No |
| `max_turns` | int | No |
| `cwd` | string | Yes - relative to vault root |
| `add_dirs` | list[string] | Yes - each path resolved |
| `system_prompt_file` | string | Yes - loaded as system prompt |
| `hooks` | dict | Yes - command paths resolved |
| `mcp_servers` | dict | Yes - args with `./` resolved |
| `agents` | dict | Pass-through |
| `sandbox` | dict | Pass-through |

### Path Resolution Rules
- `./path` → `{vault_root}/path`
- `~/path` → expanded home directory
- `/absolute/path` → unchanged

### Default Location
- CLI: `--vault PATH` or `$KOROMIND_VAULT` or `~/.koromind`

## Test
- Empty/missing config returns empty dict
- Invalid YAML raises VaultError
- Relative paths resolve to vault root
- Absolute paths preserved
- Home directory expansion works
- Cached after first load, reload() clears cache
- All referenced files exist (integration test)

## Changelog

### 2026-02-01
- Added system_prompt_file loading in ClaudeClient
- Added cwd/add_dirs pass-through to SDK
- Added debug logging throughout
- Added CLI --vault and --debug flags
- Created test-vault fixture with second brain defaults

### 2026-01-31
- Initial implementation for PR #35
