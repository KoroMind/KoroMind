---
id: SVC-001
type: service
status: draft
issue: 28
validated: 2026-01-29
---

# Single-Instance Architecture Overview

## What
Single-instance deployment architecture for KoroMind with four components: Worker, Vault, Sandbox, Backup.

## Why
Clear separation of concerns: runtime (Worker), persistent data (Vault), ephemeral workspace (Sandbox), disaster recovery (Backup).

## How
- Diagram: `docs/single-instance-architecture.mmd`
- Brain is thin orchestrator - loads config from Vault, passes to Claude SDK
- SDK handles complexity: tools, MCP, hooks, permissions, sessions
- Sandbox is disposable; Vault is portable

## Test
- Worker starts with empty Vault (creates defaults)
- Worker recovers state after restart from Vault
- Sandbox wipe doesn't affect user data

---

id: SVC-002
type: service
status: draft
issue: 28
validated: 2026-01-29
---

# Worker

## What
Runtime container processing user requests. NOT persistent.

## Why
Stateless compute that can be replaced/scaled without data loss.

## How
Components:
- **Port**: Protocol adapters (Telegram bot, HTTP server)
- **Brain**: Orchestration - receives input, loads config, calls SDK, returns response
- **Audio**: ElevenLabs STT/TTS
- **Claude SDK**: Tool execution, MCP management, permissions, Vault access

Flow: Client → Port ↔ Audio ↔ Brain → SDK → Response

## Test
- Telegram message processed end-to-end
- HTTP API returns valid response
- Voice transcription and synthesis work

---

id: SVC-003
type: service
status: draft
issue: 28
validated: 2026-01-29
---

# Vault

## What
Persistent user state and configuration. Docker volume mount.

## Why
Portable user data - can mount to any Worker instance.

## How
Contents:
- SQLite DB: sessions, settings, memory
- User config: MCP servers, agents, hooks, permissions, prompts
- User data: .claude settings, git repos, notes

On startup, Worker hydrates from Vault.

## Test
- Config changes persist across restarts
- Sessions survive Worker replacement
- Vault can be backed up and restored

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
validated: 2026-01-29
---

# Worker Stateless

## What
Worker holds no user data. All state lives in Vault.

## Why
Security: Worker compromise doesn't leak persistent data. Portability: mount Vault to any Worker.

## How
- No credentials in Worker
- No conversation history in Worker memory
- No user config baked into Worker image
- Everything belongs to user, stored in Vault

## Test
- Kill Worker, start new one with same Vault → works
- Worker image contains no user-specific data

---

id: SVC-006
type: service
status: draft
issue: 28
validated: 2026-01-29
---

# Unified Protocol

## What
All connectors speak one JSON protocol to Port.

## Why
Telegram was bypassing Brain, calling SDK directly. Business logic duplicated, behavior inconsistent.

## How
- Connectors translate native format → JSON
- Port receives JSON, routes to Brain
- Brain processes, returns JSON
- Connectors translate JSON → native format

## Test
- Same JSON request produces same response regardless of connector origin
- New connector only needs to implement JSON translation

---

id: SVC-007
type: service
status: draft
issue: 28
validated: 2026-01-29
---

# Thin Connectors

## What
Connectors only translate. They don't think.

## Why
No duplication. Test Port once, not each connector separately.

## How
Connectors DO:
- Receive native input
- Translate to JSON
- Send to Port
- Translate response to native output

Connectors do NOT:
- Call Brain or SDK directly
- Manage sessions
- Store state
- Implement approval logic

## Test
- Connector has no business logic
- All behavior comes from Port/Brain

## Changelog

### 2026-01-29
- Initial specification from architecture-v1-proposal.md
- Split into four focused specs: Overview, Worker, Vault, Sandbox
- Added Worker Stateless, Unified Protocol, Thin Connectors specs
