# Test Writing Guidelines

This document defines **how tests should be written** in this repository.
All contributors and automated agents are expected to follow these rules.

The goal is **clean, readable, maintainable tests** that verify behavior, not implementation details.

---

## Core Principles

### 1. Tests must validate system behavior
Tests should describe **what the system does**, not **how it does it**.

Focus on:
- Inputs → outputs
- State before → state after
- Messages sent, values returned, side effects produced

❌ Avoid:
- Testing private helpers directly
- Asserting internal control flow
- Over-mocking internal logic

If an implementation changes but behavior stays the same, **tests should not break**.

---

### 2. Prefer GIVEN / WHEN / THEN structure
When possible, structure tests using the **GIVEN – WHEN – THEN** mental model.

This improves clarity and helps readers understand intent immediately.

✅ Example:
```python
# GIVEN an authorized user with no active session
# WHEN /continue is called
# THEN the user is informed that no session exists
````

This can be expressed via:

* Comments
* Blank-line-separated sections
* Clear variable naming

The structure does **not** need to be literal, but the flow should be obvious.

---

### 3. Use pytest.parametrize instead of duplicating tests (IMPORTANT)

If the same behavior is tested with multiple inputs, **use `pytest.mark.parametrize`**.

This is strongly preferred over writing multiple nearly-identical tests.

✅ Preferred:

```python
@pytest.mark.parametrize(
    "topic_id,expected",
    [
        (None, True),
        (100, True),
        (200, False),
    ],
)
def test_should_handle_message(topic_id, expected):
    assert should_handle_message(topic_id) is expected
```

❌ Avoid:

* Copy-pasting the same test with small input changes
* Multiple tests that differ only by literals

Benefits:

* Less code
* Clearer intent
* Easier to extend
* Better failure reporting

---

## Pytest Conventions

### 4. Use fixtures to remove repetition

Repeated setup logic **must be extracted into fixtures**.

Common candidates:

* `monkeypatch` configuration
* Authorization / permission setup
* Mocked services or managers
* Common `update` / `context` objects

✅ Preferred:

```python
@pytest.fixture
def allow_all_chats(monkeypatch):
    monkeypatch.setattr("...ALLOWED_CHAT_ID", 0)
    monkeypatch.setattr("...should_handle_message", lambda _: True)
```

❌ Avoid repeating the same monkeypatch blocks across tests.

---

### 5. Async tests must use pytest-asyncio

All async tests **must** use:

```python
@pytest.mark.asyncio
```

* Use `AsyncMock` for async functions
* Do not manually manage event loops
* Do not mix sync and async assertions

---

## Mocking Guidelines

### 6. Mock at system boundaries

Mocks should represent **external systems**, not internal logic.

✅ Acceptable:

* Network / API calls
* Database adapters
* Telegram client methods
* Time, randomness, environment variables

❌ Avoid:

* Mocking the function under test
* Mocking multiple internal layers
* Mocking private helpers unless unavoidable

---

### 7. Prefer helper factories over raw MagicMock

For complex objects (e.g. Telegram `update`), prefer small factory helpers.

✅ Preferred:

```python
def make_update(chat_id=123, user_id=123, thread_id=None):
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_user.id = user_id
    update.message.message_thread_id = thread_id
    update.message.reply_text = AsyncMock()
    return update
```

This reduces fragility and keeps tests consistent.

---

## Assertions

### 8. Be explicit and deterministic

Assertions should clearly communicate **what is expected**.

✅ Good:

```python
update.message.reply_text.assert_called_once()
assert "No sessions" in reply_text
```

❌ Avoid:

```python
assert update.message.reply_text.call_count >= 1
assert "a" in text or "b" in text
```

Loose assertions hide regressions and make failures harder to debug.

---

### 9. Assert outcomes, not just activity

Whenever possible:

* Assert **content**, not just that something was called
* Assert **final state**, not intermediate steps

---

## Test Structure

### 10. Follow Arrange → Act → Assert

Tests should follow a clear structure:

1. **Arrange**: setup state, mocks, fixtures
2. **Act**: call the function under test
3. **Assert**: verify outcomes

Blank lines between sections are encouraged for readability.

---

### 11. Keep imports clean and consistent

* Do not leave unused imports
* Avoid importing inside tests unless required for monkeypatch timing
* Prefer consistent import style across test files

---

## Scope & Coverage

### 12. Cover edge cases explicitly

Tests should include:

* Invalid or missing configuration
* Empty inputs
* Boundary values
* Permission / authorization failures

If behavior differs in an edge case, it **must** be tested.

---

### 13. One failure reason per test

A test should fail for **one clear reason**.

If multiple cases test the same behavior:

* Use `pytest.mark.parametrize`
* Or split into separate tests with clear intent

---

## Anti-Patterns to Avoid

❌ Testing implementation details
❌ Over-mocking everything
❌ Copy-pasting test bodies
❌ Tests that depend on execution order
❌ Tests that still pass when behavior is broken

---

## Final Rule

> A test is considered “good” if a new contributor can:
>
> 1. Understand what behavior is expected
> 2. See immediately why it failed
> 3. Fix the code without touching the test

If a test does not meet these criteria, refactor it.
