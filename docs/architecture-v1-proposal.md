# KoroMind Architecture V1 Proposal

## Overview

This document describes the single-instance deployment architecture for KoroMind. It separates concerns into four main components: Worker, Sandbox, Vault, and Backup.

**Key Insight**: The Claude SDK handles most complexity (tools, MCP, hooks, permissions, sessions). KoroMind Core is a thin orchestration layer that loads user configuration from Vault and passes it to the SDK.

## System Diagram

```mermaid
graph TD
    subgraph Clients [Clients]
        TelegramApp[Telegram]
        MobileApp[Mobile]
        CLI[CLI]
    end

    subgraph Worker [Worker]
        TelegramBot[Telegram Bot]
        HTTPServer[HTTP Server]
        KoroMind[KoroMind Core<br/>thin orchestration]
        ClaudeSDK[Claude SDK<br/>does the heavy lifting]
        ElevenLabs[ElevenLabs]

        TelegramBot --> KoroMind
        HTTPServer --> KoroMind
        KoroMind -->|"passes config"| ClaudeSDK
        KoroMind --> ElevenLabs
    end

    subgraph Backup [Backup - External]
        Snapshots[Volume Snapshots]
        ExternalStorage[External Storage]
    end

    subgraph Vault [Vault - User State & Config]
        DotClaude[.claude]
        SQLiteDB[SQLite DB]
        GitRepos[Git Repos]
        SecondBrain[Second Brain]
        MCPConfig[MCP Servers Config]
        AgentsConfig[Agent Definitions]
        HooksConfig[Hooks Config]
        PermsConfig[Permission Rules]
    end

    subgraph Sandbox [Sandbox]
        direction LR
        WorkingFiles[Working Files]
        CodeExecution[Code Execution]
        TempArtifacts[Temp Artifacts]
    end

    %% Client connections
    TelegramApp --> TelegramBot
    MobileApp --> HTTPServer
    CLI --> HTTPServer

    %% Layout hints - Backup above Vault
    Backup --> Vault

    %% Worker connections
    KoroMind -.->|"loads config"| Vault
    ClaudeSDK <-->|"read/write/execute"| Sandbox
    ClaudeSDK -->|"manages"| MCPConfig
    Sandbox -->|"sync/commit"| Vault
```

## Core Architecture (Detailed)

```mermaid
flowchart TB
    subgraph Inputs["Input Layer"]
        direction LR
        TEXT["Text Message"]
        VOICE["Voice Message"]
    end

    subgraph Core["Core Layer - Thin Orchestration"]
        BRN["Brain"]
        BRN_PROC["process_message()"]
        BRN_SESS["session management"]
        BRN_SET["settings management"]

        BRN --> BRN_PROC
        BRN --> BRN_SESS
        BRN --> BRN_SET
    end

    subgraph Vault["Vault - User Configuration"]
        direction TB

        subgraph VaultState["Persistent State"]
            SQLITE["SQLite DB<br/>sessions, settings, memory"]
        end

        subgraph VaultConfig["User Config"]
            MCP_CFG["MCP Servers<br/>user-defined tools"]
            AGENTS_CFG["Agent Definitions<br/>custom personas"]
            HOOKS_CFG["Hooks<br/>user callbacks"]
            PERMS_CFG["Permissions<br/>tool rules"]
            PROMPTS_CFG["System Prompts<br/>persona files"]
        end
    end

    subgraph ClaudeSDK["Claude SDK - Does Everything"]
        SDK_CLIENT["ClaudeSDKClient"]

        subgraph SDKCapabilities["SDK Handles"]
            SDK_TOOLS["Tool Execution<br/>Read, Write, Bash, etc."]
            SDK_MCP["MCP Server Management<br/>stdio, sse, http, sdk"]
            SDK_HOOKS["Hook System<br/>PreToolUse, PostToolUse, etc."]
            SDK_PERMS["Permission System<br/>can_use_tool, updates"]
            SDK_AGENTS["Agent System<br/>custom definitions"]
            SDK_SESSION["Session Management<br/>resume, fork, continue"]
            SDK_SANDBOX["Sandbox<br/>bash isolation"]
        end

        SDK_CLIENT --> SDK_TOOLS
        SDK_CLIENT --> SDK_MCP
        SDK_CLIENT --> SDK_HOOKS
        SDK_CLIENT --> SDK_PERMS
        SDK_CLIENT --> SDK_AGENTS
        SDK_CLIENT --> SDK_SESSION
        SDK_CLIENT --> SDK_SANDBOX
    end

    subgraph External["External Services"]
        direction LR
        CLAUDE_API["Claude API<br/>Anthropic"]
        ELEVEN["ElevenLabs<br/>TTS/STT"]
        MCP_SERVERS["MCP Servers<br/>user-defined"]
    end

    subgraph Sandbox["Sandbox - Ephemeral"]
        WORK["Working Files"]
        EXEC["Code Execution"]
        TEMP["Temp Artifacts"]
    end

    %% Input Flow
    TEXT --> BRN_PROC
    VOICE --> BRN_PROC

    %% Core to Vault (read config)
    BRN_PROC -->|"load user config"| VaultConfig
    BRN_SESS --> SQLITE
    BRN_SET --> SQLITE

    %% Core passes config to SDK
    BRN_PROC -->|"pass ClaudeAgentOptions"| SDK_CLIENT
    MCP_CFG -.->|"mcp_servers"| SDK_CLIENT
    AGENTS_CFG -.->|"agents"| SDK_CLIENT
    HOOKS_CFG -.->|"hooks"| SDK_CLIENT
    PERMS_CFG -.->|"can_use_tool"| SDK_CLIENT
    PROMPTS_CFG -.->|"system_prompt"| SDK_CLIENT

    %% SDK to External
    SDK_CLIENT --> CLAUDE_API
    SDK_MCP --> MCP_SERVERS

    %% SDK to Sandbox
    SDK_TOOLS -->|"cwd"| Sandbox
    SDK_SANDBOX --> Sandbox

    %% Voice (separate from SDK)
    BRN_PROC -->|"transcribe/synthesize"| ELEVEN
```

## Components

### Worker

The runtime container that processes user requests. Contains:

- **Telegram Bot** - Handles Telegram messages
- **HTTP Server** - REST API for Mobile and CLI clients
- **KoroMind Core** - Thin orchestration layer
- **Claude SDK** - Does the heavy lifting (tools, MCP, hooks, permissions)
- **ElevenLabs** - Text-to-speech and speech-to-text

### KoroMind Core (Brain)

Thin orchestration layer. Its job is simple:

1. Receive input (text/voice)
2. Transcribe voice if needed (ElevenLabs)
3. Load user configuration from Vault
4. Build `ClaudeAgentOptions` and pass to SDK
5. Handle response (synthesize audio if needed)
6. Update session state

**Core does NOT**:
- Manage MCP servers (SDK does this)
- Handle tool permissions (SDK does this)
- Execute tools (SDK does this)
- Manage hooks (SDK does this)

### Claude SDK

The Claude Agent SDK handles all the complexity:

| Capability | Description |
|------------|-------------|
| **Tool Execution** | Read, Write, Edit, Bash, Grep, Glob, etc. |
| **MCP Servers** | stdio, sse, http, and in-process sdk servers |
| **Hook System** | PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop, PreCompact |
| **Permission System** | can_use_tool callback, PermissionUpdate, dynamic rules |
| **Agent System** | Custom agent definitions with own prompts/tools/models |
| **Session Management** | resume, fork, continue_conversation |
| **Sandbox** | Bash isolation, network controls |
| **Structured Output** | JSON schema validation |
| **File Checkpointing** | Track and rewind file changes |

### Sandbox

Ephemeral workspace where Claude executes code and creates files. This is the scratch area.

- **Working Files** - Files Claude is actively working on
- **Code Execution** - Where scripts run
- **Temp Artifacts** - Build outputs, temporary data

The Sandbox can be wiped without losing user data.

### Vault

Persistent user state AND configuration. Everything the user owns lives here.

**State**:
- **SQLite DB** - Sessions, settings, memory, conversation history

**Configuration** (passed to Claude SDK):
- **MCP Servers** - User-defined tool servers
- **Agent Definitions** - Custom personas with own prompts/tools
- **Hooks** - User callbacks for tool interception
- **Permission Rules** - Tool allow/deny rules
- **System Prompts** - Persona markdown files

**Other**:
- **.claude** - Claude Code settings
- **Git Repos** - User's code repositories
- **Second Brain** - Notes, ideas, personal knowledge base

On Worker startup, it hydrates from the Vault.

### Backup

External system that snapshots the Vault. Managed outside KoroMind (VPS scripts, cloud storage, etc.).

## Data Flow

1. **Client → Worker**: User sends message via Telegram, Mobile, or CLI
2. **Worker → Vault**: Core loads user configuration (MCP, agents, hooks, permissions)
3. **Worker → SDK**: Core passes `ClaudeAgentOptions` with all user config
4. **SDK ↔ Sandbox**: SDK reads/writes/executes in Sandbox freely
5. **SDK → MCP**: SDK manages user's MCP servers
6. **Sandbox → Vault**: Changes sync/commit from Sandbox to Vault when ready
7. **Vault → Backup**: External system snapshots Vault periodically

## Design Decisions

- **Core is thin** - Just orchestration, SDK does the work
- **MCP config lives in Vault** - User owns their tool configurations
- **SDK handles permissions** - Use can_use_tool callback, not custom logic
- **Vault holds all user config** - Portable, can mount to any Worker
- **Sandbox is ephemeral** - Can be wiped without losing user data
- **Backup is external** - Keeps the core system simple

## ClaudeAgentOptions Mapping

How Vault config maps to SDK options:

| Vault | ClaudeAgentOptions |
|-------|-------------------|
| MCP Servers | `mcp_servers` |
| Agent Definitions | `agents` |
| Hooks | `hooks` |
| Permission Rules | `can_use_tool` / `allowed_tools` |
| System Prompts | `system_prompt` |
| Sandbox Config | `sandbox` |
| Session ID | `resume` / `continue_conversation` |

## Future: Direct Vault Writes

Currently, agents can only write to Sandbox. Future enhancement:
- Agents can write directly to Vault with approval
- Use SDK's `can_use_tool` to gate Vault writes
- Sync gate still exists for unapproved changes
