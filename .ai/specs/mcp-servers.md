# MCP Server Configuration

## Overview

This spec adds configurable MCP servers so KoroMind can expose MCP tools to the
Claude Agent SDK. Users can define servers in an `mcp.json` file (preferably a
standard MCP config shape) and KoroMind will load the configuration and wire it
into the Claude client. This enables tools like MEGG or project-specific MCP
servers without hardcoding them.

## Architecture

- Add a new module `koro.core.mcp_config` responsible for loading and validating
  MCP configuration from JSON.
- `koro.core.config` exposes `MCP_CONFIG_FILE` (env) and default config
  discovery, so the core remains interface-agnostic.
- `koro.core.claude.ClaudeClient` uses the loader to attach MCP server
  definitions to `ClaudeAgentOptions` during query setup.
- When MCP is configured, tool allowlisting must not block MCP tools. Prefer a
  strategy that allows dynamic MCP tool names (e.g., a prefix allowlist for
  `mcp__*` or deferring to SDK defaults). The exact integration should follow
  the SDK's supported API.

## Data Models

### MCPConfig

- `mcp_servers: dict[str, MCPServerConfig]`

### MCPServerConfig

Fields match standard MCP config expectations and are serialized in `mcp.json`:

- `command: str` (required)
- `args: list[str]` (optional, default `[]`)
- `env: dict[str, str]` (optional, default `{}`)
- `cwd: str` (optional)
- `enabled: bool` (optional, default `true`)

### JSON Schema (conceptual)

```json
{
  "mcpServers": {
    "megg": {
      "command": "python",
      "args": ["-m", "megg_mcp"],
      "env": {
        "MEGG_DB": "~/.koromind/megg.db"
      },
      "cwd": "~",
      "enabled": true
    }
  }
}
```

## API Contracts

No external API changes are required for initial MCP support. If a future API
exposes or edits MCP settings, it should reuse the same schema and validation
rules defined here.

## UI/UX

No UI changes required. Interfaces will automatically benefit from MCP tools
once the server config is present and enabled.

## Configuration

- `MCP_CONFIG_FILE` (env, optional): explicit path to an MCP JSON config.
- Default search order (first match wins):
  1. `MCP_CONFIG_FILE`
  2. `${KOROMIND_DATA_DIR}/mcp.json`
  3. `${BASE_DIR}/mcp.json`
- The loader should expand `~` and environment variables in paths.
- Invalid configs should log a warning and disable MCP integration rather than
  crashing the request.

## Changelog

### 2026-01-28
- Added MCP server configuration spec with `mcp.json` support and Claude client
  integration guidance.
