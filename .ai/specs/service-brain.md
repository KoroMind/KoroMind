---
id: SVC-004
type: service
status: active
severity: critical
issue: null
validated: 2026-01-29
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
| `process_text()` | Text-only shorthand |
| `process_voice()` | Voice-only shorthand |

### Modes
- **GO_ALL**: Auto-execute all tool calls
- **APPROVE**: Call `can_use_tool` callback for each tool (interface shows UI)

### Watch Mode
- `on_tool_call` callback streams tool executions to interface
- Enables real-time visibility into Claude's actions

### Claude Integration
- Session ID = Claude conversation ID (context preserved)
- System prompt: sandbox paths, date/time, user context
- Tools: Read, Grep, Glob, WebSearch, WebFetch, Task, Bash, Edit, Write, Skill

### Sandbox
- Write/execute: `CLAUDE_SANDBOX_DIR` (default: ~/claude-voice-sandbox)
- Read: `CLAUDE_WORKING_DIR` (default: home dir)
- Claude SDK enforces boundaries

### Dependencies
- `StateManager` - session/settings persistence
- `VoiceEngine` - STT/TTS (optional)
- `RateLimiter` - per-user throttling

## Test
- Text message returns text response
- Voice message transcribes then processes
- Session continuity across messages
- Mode switch affects tool approval behavior
- Rate limit rejection handled gracefully

## Changelog

### 2026-01-29
- Initial spec from codebase exploration
