---
id: SVC-004
type: service
status: active
severity: critical
issue: 38
validated: 2026-02-01
---

# Brain Service

## What
- Central orchestrator connecting all components
- Single API for all interfaces (Telegram, REST, CLI)
- Wraps Claude Agent SDK for agentic tool execution

## Why
- One brain, multiple interfaces - bug fixes apply everywhere
- Encapsulates complexity: voice → Claude → tools → response
- Interfaces stay thin and stateless

## How
- Core: `src/koro/core/brain.py` - `Brain` class
- Claude wrapper: `src/koro/core/claude.py` - `ClaudeClient` class

### Data Flow
```
Input → Brain.process_message() → [STT if voice] → Claude → [Tools] → [TTS if audio] → Response
```

### Key Methods
| Method | Purpose |
|--------|---------|
| `process_message()` | Main entry: handles voice/text, returns BrainResponse |
| `process_message_stream()` | Async generator: yields partial events (`StreamEvent`) |
| `interrupt()` | Stop current running execution |
| `process_text()` | Text-only shorthand |
| `process_voice()` | Voice-only shorthand |

### Modes
- **GO_ALL**: Auto-execute all tool calls
- **APPROVE**: Call `can_use_tool` callback for each tool (interface shows UI)

### Callbacks Pattern (Decision 4)
Structured callbacks for interface integration:

```python
@dataclass
class BrainCallbacks:
    on_tool_use: Callable[[str, str | None], None] | None = None      # Watch mode
    on_tool_approval: CanUseTool | None = None                         # Approve mode
    on_progress: Callable[[str], None] | None = None                   # Progress updates
```

- `on_tool_use`: Called when tools execute (watch mode visibility)
- `on_tool_approval`: Called to approve tool use (SDK-compatible)
- `on_progress`: Called with status updates during processing
- None callback = feature disabled gracefully
- Legacy `on_tool_call` and `can_use_tool` params still work (deprecated)

### Claude Integration
- **Full SDK Parity**: Supports all `ClaudeAgentOptions` including hooks, MCP servers, subagents, plugins, and sandbox settings
- **Streaming**: Yields partial messages and events via `query_stream()`
- **Interrupts**: Allows stopping long-running tasks via `interrupt()`
- **Extended Metadata**: Captures thinking blocks, token usage, structured output, and cost
- **Session**: Context preserved via session ID
- **Tools**: Read, Grep, Glob, WebSearch, WebFetch, Task, Bash, Edit, Write, Skill (plus any MCP tools)

### Advanced Capabilities (New)
The Brain now exposes the full power of the Claude Agent SDK:

1.  **Hooks**: Inject custom logic at lifecycle events (`PreToolUse`, `PostToolUse`, `UserPromptSubmit`, etc.). Allows for logging, policy enforcement, and dynamic behavior modification.
2.  **MCP Servers**: Connect to external Model Context Protocol servers for extended toolsets and resources. Configured via `mcp_servers` option.
3.  **Subagents**: Define specialized subagents (`agents` option) with distinct system prompts and tools for complex task delegation.
4.  **Plugins**: Load local SDK plugins (`plugins` option) to extend functionality.
5.  **Structured Output**: Request JSON-formatted responses (`output_format` option) validated against a schema.
6.  **Thinking Blocks**: Access Claude's internal reasoning process (extended thinking) via `metadata["thinking"]`.
7.  **Usage & Cost**: Detailed token usage and cost tracking in response metadata.

### Sandbox
- Write/execute: `CLAUDE_SANDBOX_DIR` (default: ~/claude-voice-sandbox)
- Read: `CLAUDE_WORKING_DIR` (default: home dir)
- **Settings**: `SandboxSettings` can be passed dynamically for finer control over network access, shell command restrictions, and file access policies.
- Claude SDK enforces boundaries

### Streaming Protocol
`process_message_stream()` yields events:
- `AssistantMessage`: Standard partial message chunks
- `StreamEvent`: Detailed events (tool use, content block deltas)
- `ResultMessage`: Final completion data

### Vault Integration
- `Brain(vault_path=...)` loads config from vault directory
- Vault config merged with explicit kwargs (kwargs take precedence)
- Supports: model, max_turns, cwd, add_dirs, system_prompt_file, hooks, mcp_servers, agents, sandbox
- See `service-vault.md` for details

### Dependencies
- `Vault` - configuration loading (optional)
- `StateManager` - session/settings persistence
- `VoiceEngine` - STT/TTS (optional)
- `RateLimiter` - per-user throttling

## Test
- Text message returns text response
- Voice message transcribes then processes
- Session continuity across messages
- Mode switch affects tool approval behavior
- Rate limit rejection handled gracefully
- Streaming yields events incrementally
- Interrupt stops active execution
- Full SDK options passed correctly to client
- Thinking blocks captured in metadata
- Structured output returned when requested

## Changelog

### 2026-02-01 (Issue #38)
- Added `BrainCallbacks` dataclass for structured event handling
- Callbacks: on_tool_use, on_tool_approval, on_progress
- None callback = graceful feature disabling
- Backward compatible with legacy params (deprecated)
- Enhanced DEBUG logging throughout
- Added 60 total Brain tests:
  - Unit: 25 tests (callbacks, vault, streaming, errors)
  - Live: 27 tests (processing, vault, tools, sessions, streaming)
  - Eval: 8 tests (code gen, explanations, quality)

### 2026-02-01
- Added vault integration for stateless configuration
- Config merging: vault config + explicit kwargs
- Added debug logging throughout

### 2026-01-31
- Added full Claude SDK support (Hooks, MCP, Agents, Plugins)
- Added `process_message_stream()` for streaming responses
- Added `interrupt()` for task cancellation
- Added extended metadata support (thinking, usage, structured output)

### 2026-01-29
- Initial spec from codebase exploration
