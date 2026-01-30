# KoroMind Single-Instance Architecture

## System Overview

```mermaid
graph TD
    subgraph Clients[Clients]
        TG[Telegram]
        HTTP[HTTP/Mobile]
        CLI[CLI]
        DISC[Discord]
    end

    subgraph Worker[Worker]
        BRAIN[Brain <br> Gatekeeper]
        SDK[Claude SDK]
        VOICE[Audio Processing]

        BRAIN <--> VOICE
        API <--> BRAIN

        BRAIN <--> SDK
    end

    subgraph Vault[Vault]
        STATE[SQLite DB]
        CONFIG[User Config<br/>MCP, Agents, Hooks]
        MEMORY[Memory]
    end

    subgraph Backup[Backup]
        SNAP[Snapshots]
    end

    subgraph Sandbox[Sandbox]
        TOOLS[Tools]
        TMP[Temporary <br> Experiments]
    end

    TG --> API
    HTTP --> API
    CLI --> API
    DISC --> API

    BRAIN <--> Vault
    BRAIN <--> Sandbox
    SDK <-.-> Vault
    Vault --> Backup
```

## Components

| Component | Role |
|-----------|------|
| **API** | Single entry point, routes requests, protocol translation |
| **Brain (Gatekeeper)** | Central orchestrator—loads config, calls SDK, handles voice, manages all component communication |
| **Audio** | ElevenLabs STT/TTS |
| **Claude SDK** | Tool execution, MCP, permissions, sessions, Vault access |
| **Vault** | Persistent user state and config (Docker volume) |
| **Sandbox** | Ephemeral workspace for Claude (Docker volume) |

---

## Design Decisions

### Decision 1: Unified Protocol

**Problem discovered**: Connectors were inconsistent.

| Connector | What it was doing |
|-----------|-------------------|
| HTTP API | `routes/messages.py` → `Brain.process_message()` ✓ |
| Telegram | `handlers/messages.py` → `get_claude_client()` directly ✗ |

Telegram was bypassing Brain entirely—calling Claude SDK directly, managing its own `pending_approvals`, implementing its own `can_use_tool` callback, its own watch mode. Business logic duplicated, behavior inconsistent, hard to add new connectors.

**Decision**: One protocol. All connectors speak it. API routes to Brain, Brain handles everything.

```
Connector → JSON Request → API → Brain → SDK
                            ↓
Connector ← JSON Response ← API
```

**Value**: Single source of truth. Add Discord? Just translate its messages to JSON. Same logic, same behavior.

---

### Decision 2: Thin Connectors

**Pattern**: Connectors only translate. They don't think.

Connector responsibilities:
1. Receive native input (Telegram update, HTTP request)
2. Translate to JSON
3. Send to API
4. Receive JSON response
5. Translate to native output

Connectors do NOT:
- Call Brain directly
- Call Claude SDK
- Manage sessions
- Store state
- Implement approval logic

**Value**: No duplication. Test API and Brain once, not each connector separately.

---

### Decision 3: Brain is Thin

**Insight**: The Claude SDK already solves the hard problems—tool execution, MCP server management, hooks, permissions, session continuity.

Brain's job:
1. Receive input from API
2. Transcribe voice if needed
3. Load user config from Vault
4. Build `ClaudeAgentOptions`, pass to SDK
5. Synthesize audio if needed
6. Update state

Brain does NOT:
- Execute tools (SDK does)
- Manage MCP servers (SDK does)
- Handle permissions (SDK does)
- Manage hooks (SDK does)

**Value**: We don't reinvent what the SDK already does well. Less code, fewer bugs.

---

### Decision 4: Callbacks for Interactive Features

**Problem**: Some connectors support interactive UI (Telegram inline buttons), some don't (HTTP).

**Pattern**: Connectors register callbacks. If callback is `None`, feature is disabled.

```python
callbacks = WorkerCallbacks(
    on_tool_approval=lambda req: show_telegram_approval_ui(req),  # Telegram has this
    on_tool_use=lambda notif: send_notification(notif),           # Watch mode
    on_progress=lambda msg: update_status(msg),                   # Progress
)
```

HTTP doesn't register callbacks → approve mode doesn't work → that's fine, it's an API.

**Value**: Graceful degradation. Features work where they make sense, silently disabled elsewhere.

---

### Decision 5: Vault Holds Config

User configuration (MCP servers, agents, hooks, permissions) lives in Vault, not code.

On startup, Worker loads config from Vault and passes it straight to SDK:

| Vault | `ClaudeAgentOptions` |
|-------|---------------------|
| MCP Servers | `mcp_servers` |
| Agent Definitions | `agents` |
| Hooks | `hooks` |
| Permission Rules | `can_use_tool` |
| System Prompts | `system_prompt` |

**Value**:
- Portable—mount Vault to any Worker
- User-owned—no vendor lock-in
- SDK-native—no translation layer

---

### Decision 6: Sandbox vs Vault Access

Claude has two places to work:

**Sandbox** (ephemeral):
- Working files, temp artifacts
- Code execution
- Can be wiped without data loss

**Vault** (persistent):
- SDK reads config (MCP, agents, hooks)
- SDK can write user data (git repos, notes)
- Protected from accidental wipes

Sandbox is the default scratchpad. Vault access is for intentional, persistent changes.

**Value**: Safety with flexibility. Temp work in Sandbox, important work in Vault.

---

### Decision 7: Worker is Stateless

**Security concern**: If Worker holds user data, it becomes a target. Compromise Worker, leak data.

**Pattern**: Worker holds nothing. All state lives in Vault.

- No credentials stored in Worker
- No conversation history in Worker memory
- No user config baked into Worker image
- Worker can be killed and replaced without data loss

**Value**:
- **Portability**: Mount Vault to any Worker, instantly working
- **Security**: Worker compromise doesn't leak persistent data
- **Simplicity**: No sync, no migration, no "where's my data?"

Everything belongs to the user, stored in their Vault.

---

### Decision 8: Single Worker (for now)

Multi-tenancy is on the roadmap, but this architecture is for one user.

No tenant isolation, no credential rotation, no distributed state.

The architecture supports multi-tenancy later—Vault is portable, Worker is stateless. But MVP serves one user well before serving many poorly.

---

## Data Flow

```
1. Client sends message (Telegram/HTTP/CLI)
2. Connector translates to JSON, sends to API
3. API routes to Brain
4. Brain loads user config from Vault
5. Brain passes ClaudeAgentOptions to SDK
6. SDK executes (tools run in Sandbox, can access Vault)
7. Brain updates state in Vault
8. Brain synthesizes audio if requested
9. API returns JSON response
10. Connector translates to native output
```

---

## Changelog

- **2026-01-29**: Initial architecture document from V design sessions
