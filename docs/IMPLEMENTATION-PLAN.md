# KoroMind Architecture Implementation Plan v3

## Executive Summary

Three core components to build/enhance:
1. **Brain (Gatekeeper)** - Central orchestrator, builds ClaudeAgentOptions from Vault config
2. **Claude Code SDK** - Leverage full SDK capabilities (hooks, MCP servers, agents)
3. **Vault** - Store user config (MCP servers, agents, hooks, permissions) that Brain passes to SDK

---

## Claude Code SDK Capabilities

The SDK (`claude_agent_sdk`) offers far more than we're using:

| Feature | Currently Using | Available |
|---------|----------------|-----------|
| Basic query | ✓ | ✓ |
| Session continuation | ✓ | ✓ |
| Tool permission callback | ✓ | ✓ |
| System prompt | ✓ | ✓ |
| **MCP Servers** | ✗ | In-process, stdio, SSE, HTTP servers |
| **Hooks** | ✗ | PreToolUse, PostToolUse, UserPromptSubmit, Stop |
| **Custom Agents** | ✗ | AgentDefinition with tools, model, prompt |
| **Sandbox** | ✗ | Bash isolation settings |
| **Plugins** | ✗ | SDK plugin support |
| **Structured Output** | ✗ | JSON schema output |
| **File Checkpointing** | ✗ | Track/rewind file changes |

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CONNECTORS                                      │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────────────┤
│  Telegram   │    HTTP     │    CLI      │   Discord   │      (future)       │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴─────────────────────┘
       │             │             │             │
       └─────────────┴──────┬──────┴─────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │      API      │  (FastAPI routes)
                    └───────┬───────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                           BRAIN (Gatekeeper)                                   │
│                                                                                │
│  • Loads user config from Vault                                               │
│  • Builds ClaudeAgentOptions (MCP servers, hooks, agents, permissions)        │
│  • Manages sessions (maps KoroMind sessions to SDK sessions)                  │
│  • Coordinates Voice (TTS/STT)                                                │
│  • Emits events to connectors via callbacks                                   │
└───────────────────────────────────────────────────────────────────────────────┘
       │                            │                            │
       ▼                            ▼                            ▼
┌─────────────┐             ┌─────────────┐             ┌─────────────┐
│   Voice     │             │ Claude Code │             │   Vault     │
│  (TTS/STT)  │             │    SDK      │             │  (SQLite)   │
│             │             │             │             │             │
│ ElevenLabs  │             │ ClaudeSDK   │             │ • Config    │
│             │             │ Client      │             │ • Sessions  │
│             │             │             │             │ • Settings  │
│             │             │ • MCP       │             │ • Memory    │
│             │             │ • Hooks     │             │             │
│             │             │ • Agents    │             │             │
└─────────────┘             └──────┬──────┘             └─────────────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │   Sandbox   │
                            │  (files)    │
                            └─────────────┘
```

**Key principle:** Vault stores configuration, Brain loads it and builds proper SDK options.

---

## Implementation Phases

### Phase 1: Vault Config Storage (FOUNDATION)

**Goal:** Vault stores user config that Brain passes to Claude Code SDK.

**New Vault Schema:**

```sql
-- User config for Claude SDK options
CREATE TABLE user_config (
    user_id TEXT PRIMARY KEY,

    -- MCP Servers (JSON array)
    -- Format: [{"name": "server1", "type": "stdio", "command": "...", "args": [...]}]
    mcp_servers JSON DEFAULT '[]',

    -- Agents (JSON object)
    -- Format: {"agent_name": {"description": "...", "prompt": "...", "tools": [...]}}
    agents JSON DEFAULT '{}',

    -- Permission mode: "default", "acceptEdits", "plan", "bypassPermissions"
    permission_mode TEXT DEFAULT 'default',

    -- Allowed tools (JSON array)
    allowed_tools JSON DEFAULT '["Read", "Grep", "Glob", "WebSearch", "WebFetch", "Task", "Bash", "Edit", "Write", "Skill"]',

    -- Disallowed tools (JSON array)
    disallowed_tools JSON DEFAULT '[]',

    -- Sandbox settings (JSON object, optional)
    sandbox_settings JSON DEFAULT NULL,

    -- Model preferences
    model TEXT DEFAULT NULL,
    fallback_model TEXT DEFAULT NULL,

    -- Working directories
    working_dir TEXT DEFAULT NULL,
    sandbox_dir TEXT DEFAULT NULL,
    add_dirs JSON DEFAULT '[]',

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**StateManager additions:**

```python
async def get_sdk_config(self, user_id: str) -> dict:
    """Get Claude SDK config for a user."""
    # Returns dict ready to build ClaudeAgentOptions

async def update_sdk_config(self, user_id: str, **kwargs) -> dict:
    """Update Claude SDK config for a user."""
    # Partial update of config fields

async def get_mcp_servers(self, user_id: str) -> list[dict]:
    """Get MCP server configs for a user."""

async def add_mcp_server(self, user_id: str, server: dict) -> None:
    """Add an MCP server to user's config."""

async def get_agents(self, user_id: str) -> dict[str, dict]:
    """Get custom agent definitions for a user."""

async def add_agent(self, user_id: str, name: str, definition: dict) -> None:
    """Add a custom agent for a user."""
```

**Files to modify:**
- `src/koro/core/state.py` - Add schema and methods

**Validation:**
- [ ] New schema created
- [ ] Config methods work
- [ ] Default config reasonable

---

### Phase 2: Brain Uses Vault Config

**Goal:** Brain loads config from Vault and builds proper ClaudeAgentOptions.

**Brain.process_message() flow:**

```python
async def process_message(self, user_id: str, content: str | bytes, ...):
    # 1. Load user config from Vault
    sdk_config = await self.state_manager.get_sdk_config(user_id)

    # 2. Build ClaudeAgentOptions from config
    options = self._build_sdk_options(sdk_config, user_settings, callbacks)

    # 3. Handle session (map to SDK session)
    if session_id:
        options.resume = session_id

    # 4. Execute query
    async with ClaudeSDKClient(options=options) as client:
        ...

def _build_sdk_options(self, config: dict, settings: dict, callbacks) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions from Vault config."""
    return ClaudeAgentOptions(
        system_prompt=self._get_system_prompt(settings),
        mcp_servers=self._build_mcp_servers(config.get('mcp_servers', [])),
        agents=self._build_agents(config.get('agents', {})),
        hooks=self._build_hooks(callbacks),
        allowed_tools=config.get('allowed_tools', []),
        disallowed_tools=config.get('disallowed_tools', []),
        permission_mode=config.get('permission_mode', 'default'),
        cwd=config.get('sandbox_dir') or self.sandbox_dir,
        add_dirs=config.get('add_dirs', [self.working_dir]),
        sandbox=config.get('sandbox_settings'),
        model=config.get('model'),
        fallback_model=config.get('fallback_model'),
        can_use_tool=callbacks.on_permission_request if callbacks else None,
    )
```

**New Brain methods:**

```python
# Config management (through Vault)
async def get_config(self, user_id: str) -> dict
async def update_config(self, user_id: str, **kwargs) -> dict

# MCP server management
async def add_mcp_server(self, user_id: str, server: dict) -> None
async def remove_mcp_server(self, user_id: str, name: str) -> None
async def list_mcp_servers(self, user_id: str) -> list[dict]

# Agent management
async def add_agent(self, user_id: str, name: str, definition: dict) -> None
async def remove_agent(self, user_id: str, name: str) -> None
async def list_agents(self, user_id: str) -> dict[str, dict]
```

**Files to modify:**
- `src/koro/core/brain.py` - Load config, build options
- `src/koro/core/claude.py` - Simplify, Brain handles options building

**Validation:**
- [ ] Brain loads config from Vault
- [ ] ClaudeAgentOptions built correctly
- [ ] MCP servers passed to SDK
- [ ] Custom agents work

---

### Phase 3: Hooks Integration

**Goal:** Brain uses SDK hooks for tool notifications and control.

**Hook types available:**
- `PreToolUse` - Before tool executes (can approve/deny/modify)
- `PostToolUse` - After tool executes (can add context)
- `UserPromptSubmit` - When user sends prompt
- `Stop` - When session stops

**Brain callback mapping:**

```python
@dataclass
class BrainCallbacks:
    """Callbacks for connectors to receive events."""
    on_tool_start: Callable[[str, dict], None] | None = None      # Maps to PreToolUse
    on_tool_end: Callable[[str, Any], None] | None = None         # Maps to PostToolUse
    on_permission_request: Callable[[str, dict], Awaitable[PermissionResult]] | None = None
```

**Brain builds hooks from callbacks:**

```python
def _build_hooks(self, callbacks: BrainCallbacks | None) -> dict:
    """Build SDK hooks from Brain callbacks."""
    if not callbacks:
        return {}

    hooks = {}

    if callbacks.on_tool_start:
        async def pre_tool_hook(input: PreToolUseHookInput, tool_use_id, ctx):
            callbacks.on_tool_start(input['tool_name'], input['tool_input'])
            return {'continue_': True}

        hooks['PreToolUse'] = [HookMatcher(hooks=[pre_tool_hook])]

    if callbacks.on_tool_end:
        async def post_tool_hook(input: PostToolUseHookInput, tool_use_id, ctx):
            callbacks.on_tool_end(input['tool_name'], input['tool_response'])
            return {'continue_': True}

        hooks['PostToolUse'] = [HookMatcher(hooks=[post_tool_hook])]

    return hooks
```

**Benefits:**
- Watch mode uses PostToolUse hook (SDK handles it, not our code)
- Tool notifications are standardized
- Connectors just provide callbacks, Brain does the wiring

**Files to modify:**
- `src/koro/core/brain.py` - Add callback dataclass, hook building
- `src/koro/core/callbacks.py` - New file for BrainCallbacks

**Validation:**
- [ ] Hooks build correctly
- [ ] Tool notifications work through hooks
- [ ] Watch mode uses SDK hooks

---

### Phase 4: Connector Unification

**Goal:** All connectors use Brain with callbacks.

**Telegram handler update:**

```python
# Before
from koro.claude import get_claude_client
client = get_claude_client()
response = await client.query(...)

# After
from koro.core.brain import get_brain, BrainCallbacks

brain = get_brain()

callbacks = BrainCallbacks(
    on_tool_start=lambda name, input: send_tool_notification(chat_id, name, input),
    on_tool_end=lambda name, result: update_tool_status(chat_id, name),
    on_permission_request=lambda name, input: show_approval_dialog(chat_id, name, input),
)

response = await brain.process_message(
    user_id=str(user.id),
    content=text,
    content_type=MessageType.TEXT,
    callbacks=callbacks,
)
```

**Changes:**
1. Update `interfaces/telegram/handlers/messages.py` to use Brain
2. Update `interfaces/telegram/handlers/callbacks.py` to use Brain
3. Remove legacy imports from Telegram handlers
4. Delete legacy modules (`koro/claude.py`, `koro/voice.py`, etc.)

**Files to modify:**
- `src/koro/interfaces/telegram/handlers/messages.py`
- `src/koro/interfaces/telegram/handlers/callbacks.py`
- `src/koro/interfaces/telegram/bot.py`

**Files to delete:**
- `src/koro/claude.py`
- `src/koro/voice.py`
- `src/koro/state.py`
- `src/koro/config.py`
- `src/koro/prompt.py`
- `src/koro/rate_limit.py`
- `src/koro/auth.py`
- `src/koro/handlers/` (entire directory)

**Validation:**
- [ ] Telegram uses Brain
- [ ] HTTP API uses Brain
- [ ] No legacy imports
- [ ] All tests pass

---

### Phase 5: CLI & Documentation

**Goal:** Implement CLI, update docs.

**CLI implementation:**

```python
# src/koro/interfaces/cli/app.py
async def run_cli():
    brain = get_brain()
    user_id = "cli_user"

    print("KoroMind CLI. Type 'exit' to quit.")

    while True:
        text = input("> ")
        if text.lower() == 'exit':
            break

        response = await brain.process_text(
            user_id=user_id,
            text=text,
            include_audio=False,
        )
        print(response.text)
```

**Documentation updates:**
- Update architecture diagrams to match implementation
- Document Vault config options
- Document how to add MCP servers, agents

**Validation:**
- [ ] CLI works
- [ ] Docs match implementation

---

## Summary: What Gets Built

| Component | What Changes |
|-----------|--------------|
| **Vault (StateManager)** | New `user_config` table, SDK config methods |
| **Brain** | Loads config from Vault, builds ClaudeAgentOptions, BrainCallbacks |
| **ClaudeClient** | Simplified, Brain handles options building |
| **Telegram handlers** | Use Brain with callbacks |
| **Legacy modules** | Deleted |
| **CLI** | Implemented |

---

## Decision Log

1. **Vault stores SDK config** - MCP servers, agents, permissions in SQLite
2. **Brain builds ClaudeAgentOptions** - Single place that constructs SDK options
3. **Hooks for notifications** - Use SDK hooks instead of custom tracking
4. **BrainCallbacks for connectors** - Standardized callback interface

---

## Questions for Tako

1. **Default MCP servers**: Should new users have any default MCP servers configured?

2. **Config editing UI**: How should users edit their config (MCP servers, agents)? Telegram commands? HTTP API? Config file?

3. **Per-session vs per-user config**: Should config be per-user or allow per-session overrides?

---

## Estimated Effort

| Phase | Time | Priority |
|-------|------|----------|
| Phase 1: Vault Config | 2-3 hours | CRITICAL |
| Phase 2: Brain Uses Config | 3-4 hours | CRITICAL |
| Phase 3: Hooks Integration | 2-3 hours | HIGH |
| Phase 4: Connector Unification | 2-3 hours | HIGH |
| Phase 5: CLI & Docs | 1-2 hours | MEDIUM |

**Total: 10-15 hours**

---

## Next Step

Review this plan. If approved, I'll start with Phase 1: Vault Config Storage.
