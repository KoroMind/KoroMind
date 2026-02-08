---
id: SVC-001
type: service
status: draft
issue: 28
validated: 2026-01-31
---

# Single-Instance Architecture Overview

## What
Single-instance deployment architecture for KoroMind with four components: Worker (containing Connectors, Brain, Vault, SDK, Voice), Mount, Sandbox, Backup.

## Why
**Safe by design:**
- **Stateless Worker**: No user data in runtime - compromise doesn't leak secrets
- **Personal Vault**: User owns their data in Mount - portable, ejectable, no lock-in
- **Isolated Sandbox**: Ephemeral workspace - wipe without losing anything important

## How
- Diagram: `docs/single-instance-architecture.mmd`
- Brain is thin orchestrator - loads config from Vault, passes to Claude SDK
- Vault is in-worker state manager bridging Brain to Mount
- SDK handles complexity: tools, MCP, hooks, permissions, sessions
- Sandbox is disposable; Mount is portable

## Test
- Worker starts with empty Mount (creates defaults)
- Worker recovers state after restart from Mount
- Sandbox wipe doesn't affect user data

---

id: SVC-002
type: service
status: draft
issue: 28
validated: 2026-01-31
---

# Worker

## What
Runtime container processing user requests. NOT persistent.

## Why
Stateless compute that can be replaced/scaled without data loss.

## How
Worker contains:
- **Connectors** (1+): Protocol adapters - Telegram, HTTP API, Discord, etc. Multiple can run simultaneously.
- **CLI**: Direct Brain access for testing/development
- **Brain**: Thin orchestrator - receives input, loads config from Vault, calls SDK
- **Vault**: In-memory state manager bridging Brain ↔ Mount
- **Voice**: ElevenLabs/OpenAI STT/TTS
- **Claude SDK**: The heavy lifter - tools, MCP, hooks, permissions, sessions

Flow:
```
Client → Connector → Brain → Vault → Mount
                   → SDK   → Sandbox
                   → Voice → ElevenLabs
```

## Test
- Telegram message processed end-to-end
- HTTP API returns valid response
- Voice transcription and synthesis work

---

id: SVC-003
type: service
status: draft
issue: 28
validated: 2026-01-31
---

# Mount

## What
Persistent user state and configuration. Docker volume mount.

## Why
Portable user data - can mount to any Worker instance.

## How
Contents:
- **Settings**: User preferences and configuration
- **mcp.json**: MCP server definitions
- **Directories**: User data directories (git repos, notes)
- **Memories**: Long-term memory storage

On startup, Vault (in Worker) hydrates from Mount.

## Test
- Config changes persist across restarts
- Sessions survive Worker replacement
- Mount can be backed up and restored

---

id: SVC-004
type: service
status: draft
issue: 28
validated: 2026-01-29
---

# Sandbox

## What
Ephemeral workspace for Claude to read/write/execute. Docker volume mount.

## Why
Isolated scratch space that can be wiped without losing user data.

## How
- Working files Claude creates/modifies
- Code execution environment
- Temp artifacts (build outputs, etc.)
- SDK tools operate here by default

Sync to Vault happens explicitly (git commit, file copy).

## Test
- Claude can write files to Sandbox
- Sandbox wipe doesn't affect Vault
- Code execution is isolated

---

id: SVC-005
type: service
status: draft
issue: 28
validated: 2026-01-31
---

# Worker Stateless

## What
Worker holds no persistent user data. All state lives in Mount. Vault is an in-memory bridge.

## Why
Security: Worker compromise doesn't leak persistent data. Portability: mount to any Worker.

## How
- No credentials in Worker
- No conversation history in Worker memory
- No user config baked into Worker image
- Vault reads/writes to Mount, holds nothing persistent
- Everything belongs to user, stored in Mount

## Test
- Kill Worker, start new one with same Mount → works
- Worker image contains no user-specific data

---

id: SVC-006
type: service
status: draft
issue: 28
validated: 2026-01-31
---

# Unified Protocol

## What
All connectors speak one JSON protocol to Brain.

## Why
Telegram was bypassing Brain, calling SDK directly. Business logic duplicated, behavior inconsistent.

## How
- External clients connect to their respective Connectors (Telegram→TGW, HTTP→HTTPW, Discord→DISCW)
- Connectors translate native format → JSON
- Connectors send JSON to Brain
- Brain processes, returns JSON
- Connectors translate JSON → native format
- CLI connects directly to Brain (no connector needed)

## Test
- Same JSON request produces same response regardless of connector origin
- New connector only needs to implement JSON translation

---

id: SVC-007
type: service
status: draft
issue: 28
validated: 2026-01-31
---

# Thin Connectors

## What
Connectors only translate. They don't think.

## Why
No duplication. Test Brain once, not each connector separately.

## How
Connectors DO:
- Receive native input from external clients
- Translate to JSON
- Send to Brain
- Translate response to native output

Connectors do NOT:
- Call SDK directly
- Manage sessions
- Store state
- Implement approval logic

## Test
- Connector has no business logic
- All behavior comes from Brain

---

id: SVC-008
type: service
status: draft
issue: 28
validated: 2026-01-31
---

# Vault (In-Worker)

## What
In-worker state manager that bridges Brain to Mount.

## Why
Provides abstraction layer between Brain's in-memory operations and Mount's persistent storage.

## How
- Loads configuration from Mount on startup
- Caches frequently accessed data in memory
- Writes state changes back to Mount
- SDK also accesses Mount directly for tool operations

## Test
- Vault initializes correctly from Mount
- State changes propagate to Mount
- Cache invalidation works correctly

## Changelog

### 2026-01-31
- Updated architecture: Vault moved inside Worker, Mount as persistent storage
- Added explicit Connectors subgraph
- Added Voice connections to ElevenLabs/OpenAI
- Added SVC-008 Vault (In-Worker) spec

### 2026-01-29
- Initial specification from architecture-v1-proposal.md
- Split into four focused specs: Overview, Worker, Vault, Sandbox
- Added Worker Stateless, Unified Protocol, Thin Connectors specs
