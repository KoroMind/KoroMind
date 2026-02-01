---
id: TST-001
type: feature
status: active
severity: high
issue: 38
validated: 2026-02-01
---

# Integration Testing Strategy

## What
- Comprehensive integration tests for Brain + Vault + Claude SDK
- Three test layers: unit (mocked), live (real API), eval (agent-judged)
- Machine-verifiable quality gates before shipping

## Why
- Brain orchestrates Vault config and SDK execution - must work together
- Unit tests catch regressions; live tests prove it actually works
- Eval tests validate output quality, not just execution

## Test Layers

### Layer 1: Unit Tests (Mocked Dependencies)
Fast, deterministic, run on every commit.

| File | Coverage |
|------|----------|
| `test_brain_callbacks.py` | Callback firing, backward compat |
| `test_brain_vault.py` | Config loading, merging, path resolution |
| `test_brain_streaming.py` | Event types, session capture |
| `test_brain_errors.py` | Error paths, graceful failures |

### Layer 2: Live Tests (Real Claude API)
Slow, require credentials, run with `-m live`.

| File | Coverage |
|------|----------|
| `test_brain_live.py` | Basic processing, sessions, metadata |
| `test_brain_vault_live.py` | Real vault + real Claude |
| `test_brain_tools_live.py` | Tool execution, sandbox, approve mode |
| `test_brain_streaming_live.py` | Streaming events, callbacks, interrupt |
| `test_brain_session_live.py` | Multi-user isolation, continuity |

### Layer 3: Eval Tests (Agent-Judged Quality)
Non-deterministic, run with `-m eval`.

| File | Coverage |
|------|----------|
| `test_brain_eval.py` | Code gen, explanations, multi-step |
| `test_brain_quality_eval.py` | Personality, reasoning, safety |

## Test Scenarios

### Brain + Vault Integration

```
Scenario: Vault config applies to SDK
Given: vault with model=opus, max_turns=50
When: Brain.process_text() called
Then: ClaudeClient receives those options

Scenario: Explicit kwargs override vault
Given: vault with model=sonnet
When: Brain.process_text(model="opus") called
Then: ClaudeClient receives model=opus

Scenario: Vault paths resolve correctly
Given: vault with system_prompt_file="./prompts/main.md"
When: Brain initializes
Then: Absolute path passed to SDK

Scenario: Vault hooks execute
Given: vault with safety hook blocking "rm -rf"
When: Brain processes "delete everything with rm -rf"
Then: Hook blocks execution, response indicates blocked
```

### Brain + SDK Advanced Features

```
Scenario: Interrupt stops execution
Given: Long-running Brain query
When: brain.interrupt() called mid-execution
Then: Query stops, partial response returned
```

### Session Management

```
Scenario: Multi-user sessions isolated
Given: user1 says "remember A", user2 says "remember B"
When: Each asks "what did I say?"
Then: user1 gets A, user2 gets B

Scenario: Session continuity
Given: user sends message, gets session_id
When: User sends follow-up with same session_id
Then: Context preserved, conversation continues

Scenario: Session switching
Given: User has sessions S1 and S2
When: User switches from S1 to S2
Then: S2 context active, S1 preserved
```

### Streaming

```
Scenario: Stream yields events
When: brain.process_message_stream() called
Then: Yields AssistantMessage, StreamEvent, ResultMessage

Scenario: Callbacks fire during stream
Given: BrainCallbacks with on_progress, on_tool_use
When: Streaming with tool execution
Then: Callbacks fire as tools execute

Scenario: Session ID captured from stream
When: Stream completes with new session
Then: Session ID available in final event
```

### Error Handling

```
Scenario: Invalid vault config
Given: vault-config.yaml with syntax error
When: Brain(vault_path=...) called
Then: Error logged, Brain works without vault config

Scenario: Claude API failure
Given: Network error or rate limit
When: Brain.process_text() called
Then: Error bubbles up with clear message

Scenario: Transcription failure
Given: Corrupt audio bytes
When: Brain.process_voice() called
Then: Error message returned, no crash
```

### Quality (Eval)

```
Scenario: Vault personality evident
Given: vault with warm, direct personality prompt
When: Brain responds to greeting
Then: Response matches personality criteria (agent evaluates)

Scenario: Safety boundaries enforced
Given: Request for dangerous operation
When: Brain processes request
Then: Operation denied, safety explanation provided

Scenario: Multi-tool task completes
Given: Task requiring multiple tool calls
When: Brain processes task
Then: All tools used correctly, result accurate
```

## Fixtures Required

```python
# conftest.py additions

@pytest.fixture
def brain_with_vault(tmp_path):
    """Brain with real vault directory."""
    vault_path = create_test_vault(tmp_path)
    return Brain(vault_path=vault_path, ...)

@pytest.fixture
def vault_with_hooks(tmp_path):
    """Vault configured with safety hooks."""
    return create_vault(tmp_path, hooks={...})

@pytest.fixture
def vault_with_mcp(tmp_path):
    """Vault with MCP server configured."""
    return create_vault(tmp_path, mcp_servers={...})

@pytest.fixture
def multi_user_brain(tmp_path):
    """Brain configured for multi-user testing."""
    return Brain(state_manager=StateManager(tmp_path / "state.db"), ...)
```

## Markers

```python
# pyproject.toml
markers = [
    "live: requires live API keys (ANTHROPIC_API_KEY or OAuth)",
    "eval: agent-evaluated quality tests (non-deterministic)",
    "slow: tests that take >10s",
]
```

## Run Commands

```bash
# All unit tests (fast, no API)
pytest src/tests/unit -v

# Live tests (need credentials)
pytest -m live -v

# Eval tests (agent-judged)
pytest -m eval -v

# Full integration suite
pytest src/tests/integration -v

# Skip slow/live for quick check
pytest -m "not live and not slow" -v
```

## Success Criteria

Before merge, all must pass:
- [ ] Unit tests: 100% pass (exit 0)
- [ ] Live tests: 100% pass (exit 0)
- [ ] Eval tests: 80%+ pass (score >= 0.7)
- [ ] No CRITICAL security issues
- [ ] Coverage >= 80% on Brain module

## Test

- Run `pytest src/tests/unit -v` - all pass
- Run `pytest -m live -v` - all pass with credentials
- Run `pytest -m eval -v` - 80%+ pass
- Verify fixtures create valid test environments

## Changelog

### 2026-02-01 (Issue #38)
- Initial spec for integration testing strategy
- Define three test layers: unit, live, eval
- Document test scenarios for Brain + Vault + SDK
- Specify fixtures and run commands
- Implemented 37 new tests (8 files)
- Removed budget/skills/extended-thinking scenarios (not MVP)
