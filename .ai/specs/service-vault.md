---
id: SVC-009
type: service
status: active
severity: high
issue: 35
validated: 2026-02-03
---

# Vault Service

## What
- Loads configuration from `vault-config.yaml` in a vault directory
- Resolves relative paths to absolute paths within vault
- Passes SDK-compatible config to Brain → ClaudeClient

## Why
- **User ownership**: User owns their data, not the service
- **Portable**: Copy vault directory anywhere, everything works
- **Easy to eject**: No vendor lock-in, plain files on disk

## How
- Core: `src/koro/core/vault.py` - `Vault` class, `VaultConfig` model
- Integration: `src/koro/core/brain.py:180-195` - merges vault config into kwargs

### Config Flow
```
vault-config.yaml → Vault.load() → VaultConfig → Brain.process_message() → model_dump() → ClaudeAgentOptions
```

### Typed Models (frozen Pydantic)
- `VaultConfig` - main config with all SDK options
- `HookConfig` - single hook (type, command)
- `HookMatcher` - matcher with hooks list
- `McpServerConfig` - MCP server (command, args)
- `AgentConfig` - subagent definition
- `SandboxConfig` - sandbox settings

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
- Empty/missing config returns empty `VaultConfig`
- Invalid YAML raises VaultError
- Relative paths resolve to vault root
- Absolute paths preserved
- Home directory expansion works
- Cached after first load, reload() clears cache
- All referenced files exist (integration test)
- VaultConfig is frozen (immutable)

## Changelog

### 2026-02-03
- Added VaultConfig frozen Pydantic model
- Added typed models: HookConfig, HookMatcher, McpServerConfig, AgentConfig, SandboxConfig
- Vault.load() now returns VaultConfig instead of dict
- Brain uses model_dump() for SDK compatibility

### 2026-02-01
- Added system_prompt_file loading in ClaudeClient
- Added cwd/add_dirs pass-through to SDK
- Added debug logging throughout
- Added CLI --vault and --debug flags
- Created test-vault fixture with second brain defaults

### 2026-01-31
- Initial implementation for PR #35
