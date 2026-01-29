---
id: SVC-ARCH-001
type: service
status: draft
severity: critical
issue: 28
validated: 2026-01-29
---

# System Architecture

## What
- High-level architecture for KoroMind: a multi-interface AI assistant
- Defines core components: Port, Brain, Voice Generation, Vault, Sandbox, Backup
- Single Worker model with pluggable client interfaces

## Why
- Clear mental model for contributors
- Separation of concerns: input/output, cognition, persistence
- Foundation for multi-tenant and distributed deployments

---

## Components

### Clients
External applications that connect to KoroMind.

| Client | Protocol | Notes |
|--------|----------|-------|
| Telegram | Bot API | Primary interface, voice + text |
| HTTP/Mobile | REST | Programmatic access, future mobile apps |
| CLI | stdin/stdout | Local development and testing |
| Discord | Bot API | Future integration |

Clients are NOT part of the Worker. They communicate through the Port.

---

### Port
Single entry point for all client connections.

**Responsibility:**
- Accept incoming messages from any client
- Route responses back to the originating client
- Protocol translation (Telegram markup, REST JSON, CLI text)
- Authentication and access control

**What it is NOT:**
- Does not process messages
- Does not maintain conversation state
- Does not know about Claude or tools

Location: `src/koro/interfaces/*/`

---

### Brain
Central intelligence that processes all requests.

**Responsibility:**
- Receive messages from Port
- Load context from Memory
- Invoke Claude SDK for reasoning and tool execution
- Return text response to Voice Generation

**Key behaviors:**
- Session continuity via conversation ID
- Mode switching: GO_ALL (auto-execute) vs APPROVE (human confirmation)
- Tool call streaming via `on_tool_call` callback

**What it is NOT:**
- Does not handle audio conversion
- Does not know which client sent the message
- Does not persist state directly (delegates to Vault)

Location: `src/koro/core/brain.py`

---

### Claude SDK
The reasoning engine wrapped by Brain.

**Responsibility:**
- Agentic tool execution (Read, Write, Bash, etc.)
- Conversation context management
- Sandbox enforcement

**Integration:**
- Brain passes system prompt, user message, session ID
- SDK executes tools within Sandbox boundaries
- SDK returns text response to Brain

Location: `src/koro/core/claude.py` (wrapper)

---

### Voice Generation
Output layer for text-to-speech conversion.

**Responsibility:**
- Convert Brain's text response to audio
- Optional: can be bypassed for text-only responses
- Runs after Brain processing, before Port delivery

**What it is NOT:**
- Not part of Brain's cognition
- Does not decide what to say
- Does not handle speech-to-text (that's input, handled before Brain)

Location: `src/koro/core/voice.py` (TTS portion)

---

### Vault
Persistent storage for user state and configuration.

| Component | Purpose |
|-----------|---------|
| SQLite DB | Sessions, settings, structured data |
| User Config | MCP servers, agent definitions, hooks, permissions |
| Memory | Long-term recall, user preferences, learned context |

**Key principle:** Brain reads/writes Memory; SDK reads Config; both are in Vault.

Location: `~/.koromind/` or `KOROMIND_DATA_DIR`

---

### Sandbox
Isolated execution environment for Claude.

| Component | Purpose |
|-----------|---------|
| Working Files | Temporary artifacts, code, downloads |
| Code Execution | Bash, Python, tool outputs |

**Security:**
- Write access limited to sandbox directory
- Read access configurable (default: user home)
- No network restrictions (may add later)

Location: `~/claude-voice-sandbox/` or `CLAUDE_SANDBOX_DIR`

---

### Backup
External snapshot storage.

**Responsibility:**
- Volume snapshots of Vault
- Disaster recovery
- Not real-time; scheduled

Flow: `Vault → Backup` (one-way)

---

## Data Flow

```
Clients → Port → Brain → Claude SDK ↔ Sandbox
                   ↓
            Voice Generation
                   ↓
                 Port → Clients

Brain ↔ Memory (in Vault)
Sandbox → Vault (sync/commit)
Vault → Backup (snapshots)
```

---

## Proposed Folder Structure

```
src/
├── koro/
│   ├── core/                    # Brain & business logic
│   │   ├── brain.py             # Central orchestrator
│   │   ├── claude.py            # Claude SDK wrapper
│   │   ├── voice.py             # Voice generation (TTS)
│   │   ├── memory.py            # Memory read/write
│   │   ├── state.py             # Session & settings persistence
│   │   └── types.py             # Shared types
│   │
│   ├── port/                    # Protocol translation layer
│   │   ├── base.py              # Port interface/ABC
│   │   ├── telegram.py          # Telegram adapter
│   │   ├── http.py              # REST API adapter
│   │   ├── cli.py               # CLI adapter
│   │   └── discord.py           # Discord adapter (future)
│   │
│   ├── vault/                   # Persistence layer
│   │   ├── db.py                # SQLite operations
│   │   ├── config.py            # User config (MCP, agents, hooks)
│   │   └── backup.py            # Snapshot management
│   │
│   └── sandbox/                 # Execution environment
│       ├── manager.py           # Sandbox lifecycle
│       └── permissions.py       # Access control
│
├── prompts/                     # System prompts per persona
│   ├── koro.md
│   └── custom/
│
└── tests/
    ├── unit/
    └── integration/
```

**Key changes from current structure:**
- `interfaces/` renamed to `port/` (aligns with architecture)
- New `vault/` package for all persistence concerns
- New `sandbox/` package for execution isolation
- `memory.py` extracted from state (distinct concern)

---

## Test
- Message flows from Client through Port to Brain and back
- Voice Generation is optional and bypassable
- Memory persists across sessions
- Sandbox isolation verified

## Changelog

### 2026-01-29
- Initial architecture spec from design session with Tako
