---
id: SVC-009
type: service
status: active
severity: high
issue: 35
validated: 2026-02-08
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
vault-config.yaml → Vault.load() → VaultConfig → Brain._build_query_config() → QueryConfig
```

### Typed Models (frozen Pydantic, path resolution via `model_post_init`)
- `VaultConfig` - top-level config (`extra="forbid"`)
- `HookConfig` - single hook (resolves `./` in command)
- `HookMatcher` - matcher with hooks list
- `McpServerConfig` - MCP server (resolves `./` in args)
- `AgentConfig` - subagent (model, prompt/prompt_file, tools)
- `SandboxConfig` - sandbox settings (camelCase aliases)

### Fields
| Field | Type | Notes |
|-------|------|-------|
| `hooks` | dict[str, list[HookMatcher]] | Command paths resolved |
| `mcp_servers` | dict or string path | String loads JSON file (`mcpServers` key) |
| `agents` | dict[str, AgentConfig] | model: sonnet/opus/haiku/inherit |
| `sandbox` | SandboxConfig | camelCase or snake_case |
| `plugins` | list | Pass-through |

### Path Resolution (in models, not Vault.load())
- `./path` → `{vault_root}/path` (via `model_post_init` + `object.__setattr__`)
- `~/path` → expanded home directory
- `/absolute/path` → unchanged

### Default Location
- CLI: `--vault PATH` or `$KOROMIND_VAULT` or `~/.koromind`

## Test
- Empty/missing config returns empty `VaultConfig`
- Invalid YAML raises VaultError
- Relative paths resolve to vault root
- Absolute paths preserved
- Cached after first load, reload() clears cache
- MCP JSON file: loads, resolves paths, errors on missing/invalid/no key
- Agent model literals validated, prompt vs prompt_file exclusive
- Extra fields rejected (`extra="forbid"`)

## Changelog

### 2026-02-08
- mcp_servers accepts JSON file path (model_validator mode="before")
- Path resolution moved into models via model_post_init
- AgentConfig: model field (sonnet/opus/haiku/inherit), prompt_file support
- extra="forbid" on VaultConfig and AgentConfig

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
