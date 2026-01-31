# Branch Dependencies

## Rule: Understand dependencies before merging

Before asking "can this branch go to master?", check what capabilities it assumes exist.

## KoroMind branch structure

```
master (basic SDK)
  └── full-sdk-impl (hooks, mcp, agents, streaming, interrupt)
        └── vault-component (config loading for all those options)
```

## Why vault needs full-sdk-impl

Vault passes config options that don't exist on master's ClaudeClient:
- `hooks` - PreToolUse, PostToolUse matchers
- `mcp_servers` - MCP server configs
- `agents` - agent definitions
- `sandbox` - sandbox settings
- `cwd`, `add_dirs` - working directory options

Master's `claude.py` only has basic `sandbox_dir` and `working_dir`.

## How to check dependencies

1. What does this code import/call?
2. Do those imports/methods exist on target branch?
3. `git show master:path/to/file.py` to compare

## Merge strategy

Stack PRs: merge full-sdk-impl first, then vault-component.
