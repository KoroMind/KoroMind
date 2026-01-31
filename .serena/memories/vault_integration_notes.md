# Vault Integration Notes

## Config flow

```
vault-config.yaml → Vault.load() → Brain.process_message() → ClaudeClient._build_options() → ClaudeAgentOptions
```

## Gotcha: Config can exist but get ignored

Vault config for `cwd`, `add_dirs`, `system_prompt_file` was being ignored in `ClaudeClient._build_options()` which hardcoded defaults.

**Always trace actual data flow from source to destination.**

## Key files in the flow

- `src/koro/core/vault.py` - loads YAML, resolves paths
- `src/koro/core/brain.py` - passes vault config to claude client
- `src/koro/core/claude.py` - `_build_options()` must accept and use vault params
- `src/koro/interfaces/cli/app.py` - `--vault` flag, `_get_vault_path()` helper

## Vault config options that flow to SDK

- `model`, `max_turns` - direct pass-through
- `cwd`, `add_dirs` - working directories
- `system_prompt_file` - custom prompt (overrides prompt manager)
- `hooks`, `mcp_servers`, `agents`, `sandbox` - advanced SDK features
