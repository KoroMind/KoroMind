"""Tests for the SSE streaming endpoint.

Follows the test_api_http.py pattern: mocks brain.process_message_stream
as an async generator, verifies SSE event format and protocol compliance.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from koro.core.brain import set_brain

TEST_API_KEY = "test-secret-key-12345"


# ── Fake SDK types for testing ────────────────────────────────────────


class FakeTextBlock:
    def __init__(self, text: str):
        self.text = text


class FakeToolUseBlock:
    def __init__(self, id: str, name: str, input: dict | None = None):
        self.id = id
        self.name = name
        self.input = input or {}


class FakeToolResultBlock:
    def __init__(self, tool_use_id: str, content: str = "", is_error: bool = False):
        self.tool_use_id = tool_use_id
        self.content = content
        self.is_error = is_error


class FakeAssistantMessage:
    """Mimics claude_agent_sdk.types.AssistantMessage."""

    def __init__(self, content: list):
        self.content = content


class FakeResultMessage:
    """Mimics claude_agent_sdk.types.ResultMessage."""

    def __init__(
        self,
        result: str = "",
        session_id: str | None = None,
        total_cost_usd: float | None = None,
        num_turns: int | None = None,
        duration_ms: int | None = None,
        usage: dict | None = None,
        is_error: bool | None = None,
        structured_output: dict | None = None,
    ):
        self.result = result
        self.session_id = session_id
        self.total_cost_usd = total_cost_usd
        self.num_turns = num_turns
        self.duration_ms = duration_ms
        self.usage = usage
        self.is_error = is_error
        self.structured_output = structured_output


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_brain():
    """Reset global brain after each test."""
    yield
    set_brain(None)  # type: ignore[arg-type]


@pytest.fixture()
def _allow_rate_limit():
    """Mock rate limiter to always allow requests."""
    mock_rl = MagicMock()
    mock_rl.check.return_value = (True, "")
    with patch("koro.api.middleware.get_rate_limiter", return_value=mock_rl):
        yield


@pytest.fixture()
def mock_brain() -> MagicMock:
    """Create a mock Brain with process_message_stream."""
    brain = MagicMock()
    brain.health_check.return_value = {
        "claude": (True, "OK"),
        "voice": (True, "OK"),
    }
    return brain


@pytest.fixture()
def client(mock_brain: MagicMock, _allow_rate_limit: None) -> TestClient:
    """Create a TestClient with auth enabled and mock brain."""
    set_brain(mock_brain)
    with (
        patch("koro.api.middleware.KOROMIND_API_KEY", TEST_API_KEY),
        patch("koro.api.middleware.KOROMIND_ALLOW_NO_AUTH", False),
    ):
        from koro.api.app import create_app

        app = create_app()
        yield TestClient(app)


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": TEST_API_KEY}


def _parse_sse_events(response_text: str) -> list[dict | str]:
    """Parse SSE data lines into JSON objects or raw strings."""
    events = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            payload = line[6:]
            if payload == "[DONE]":
                events.append("[DONE]")
            else:
                events.append(json.loads(payload))
    return events


# ── Helpers ───────────────────────────────────────────────────────────


def _make_stream_gen(*events):
    """Create an async generator from a list of events."""

    async def gen(**kwargs):
        for event in events:
            yield event

    return gen


# ── Tests ─────────────────────────────────────────────────────────────


class TestStreamEndpoint:
    """Test the SSE streaming endpoint."""

    def test_returns_event_stream_content_type(
        self, client: TestClient, mock_brain: MagicMock
    ) -> None:
        """1. Returns Content-Type: text/event-stream."""
        mock_brain.process_message_stream = MagicMock(
            side_effect=_make_stream_gen(
                FakeResultMessage(result="Hi", session_id="s1")
            )
        )
        resp = client.post(
            "/api/v1/messages/stream",
            headers=_auth_headers(),
            json={"content": "Hello"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_returns_ui_message_stream_header(
        self, client: TestClient, mock_brain: MagicMock
    ) -> None:
        """2. Returns x-vercel-ai-ui-message-stream: v1 header."""
        mock_brain.process_message_stream = MagicMock(
            side_effect=_make_stream_gen(
                FakeResultMessage(result="Hi", session_id="s1")
            )
        )
        resp = client.post(
            "/api/v1/messages/stream",
            headers=_auth_headers(),
            json={"content": "Hello"},
        )
        assert resp.headers.get("x-vercel-ai-ui-message-stream") == "v1"

    def test_first_event_is_start_with_message_id(
        self, client: TestClient, mock_brain: MagicMock
    ) -> None:
        """3. First event is type: start with messageId."""
        mock_brain.process_message_stream = MagicMock(
            side_effect=_make_stream_gen(
                FakeResultMessage(result="Hi", session_id="s1")
            )
        )
        resp = client.post(
            "/api/v1/messages/stream",
            headers=_auth_headers(),
            json={"content": "Hello"},
        )
        events = _parse_sse_events(resp.text)
        assert events[0]["type"] == "start"
        assert "messageId" in events[0]
        assert events[0]["messageId"].startswith("msg-")

    @patch("koro.api.routes.stream.AssistantMessage", FakeAssistantMessage)
    @patch("koro.api.routes.stream.ResultMessage", FakeResultMessage)
    @patch("koro.api.routes.stream.TextBlock", FakeTextBlock)
    @patch("koro.api.routes.stream.ToolUseBlock", FakeToolUseBlock)
    @patch("koro.api.routes.stream.ToolResultBlock", FakeToolResultBlock)
    def test_text_blocks_emit_start_delta_end(
        self, client: TestClient, mock_brain: MagicMock
    ) -> None:
        """4. Text blocks emit text-start -> text-delta -> text-end."""
        mock_brain.process_message_stream = MagicMock(
            side_effect=_make_stream_gen(
                FakeAssistantMessage([FakeTextBlock("Hello")]),
                FakeAssistantMessage([FakeTextBlock("Hello world")]),
                FakeResultMessage(result="Hello world", session_id="s1"),
            )
        )
        resp = client.post(
            "/api/v1/messages/stream",
            headers=_auth_headers(),
            json={"content": "Hi"},
        )
        events = _parse_sse_events(resp.text)
        types = [e["type"] if isinstance(e, dict) else e for e in events]

        assert "text-start" in types
        assert "text-delta" in types
        assert "text-end" in types

        # Check delta content
        deltas = [e for e in events if isinstance(e, dict) and e.get("type") == "text-delta"]
        assert len(deltas) >= 1
        # First delta should be "Hello", second " world"
        assert deltas[0]["delta"] == "Hello"
        if len(deltas) > 1:
            assert deltas[1]["delta"] == " world"

    @patch("koro.api.routes.stream.AssistantMessage", FakeAssistantMessage)
    @patch("koro.api.routes.stream.ResultMessage", FakeResultMessage)
    @patch("koro.api.routes.stream.TextBlock", FakeTextBlock)
    @patch("koro.api.routes.stream.ToolUseBlock", FakeToolUseBlock)
    @patch("koro.api.routes.stream.ToolResultBlock", FakeToolResultBlock)
    def test_tool_blocks_emit_input_and_output(
        self, client: TestClient, mock_brain: MagicMock
    ) -> None:
        """5. Tool blocks emit tool-input-available and tool-output-available."""
        mock_brain.process_message_stream = MagicMock(
            side_effect=_make_stream_gen(
                FakeAssistantMessage(
                    [
                        FakeToolUseBlock(
                            id="tool-1", name="Bash", input={"command": "ls"}
                        ),
                    ]
                ),
                FakeAssistantMessage(
                    [
                        FakeToolUseBlock(
                            id="tool-1", name="Bash", input={"command": "ls"}
                        ),
                        FakeToolResultBlock(
                            tool_use_id="tool-1", content="file1.txt\nfile2.txt"
                        ),
                    ]
                ),
                FakeResultMessage(result="Done", session_id="s1"),
            )
        )
        resp = client.post(
            "/api/v1/messages/stream",
            headers=_auth_headers(),
            json={"content": "list files"},
        )
        events = _parse_sse_events(resp.text)
        types = [e["type"] if isinstance(e, dict) else e for e in events]

        assert "tool-input-available" in types
        assert "tool-output-available" in types

        tool_input = next(
            e for e in events if isinstance(e, dict) and e.get("type") == "tool-input-available"
        )
        assert tool_input["toolCallId"] == "tool-1"
        assert tool_input["toolName"] == "Bash"
        assert tool_input["input"] == {"command": "ls"}

        tool_output = next(
            e for e in events if isinstance(e, dict) and e.get("type") == "tool-output-available"
        )
        assert tool_output["toolCallId"] == "tool-1"
        assert tool_output["output"] == "file1.txt\nfile2.txt"

    @patch("koro.api.routes.stream.AssistantMessage", FakeAssistantMessage)
    @patch("koro.api.routes.stream.ResultMessage", FakeResultMessage)
    @patch("koro.api.routes.stream.TextBlock", FakeTextBlock)
    @patch("koro.api.routes.stream.ToolUseBlock", FakeToolUseBlock)
    @patch("koro.api.routes.stream.ToolResultBlock", FakeToolResultBlock)
    def test_result_message_emits_finish_with_metadata(
        self, client: TestClient, mock_brain: MagicMock
    ) -> None:
        """6. ResultMessage emits finish with metadata."""
        mock_brain.process_message_stream = MagicMock(
            side_effect=_make_stream_gen(
                FakeAssistantMessage([FakeTextBlock("Answer")]),
                FakeResultMessage(
                    result="Answer",
                    session_id="sess-42",
                    total_cost_usd=0.015,
                    num_turns=3,
                    duration_ms=1200,
                ),
            )
        )
        resp = client.post(
            "/api/v1/messages/stream",
            headers=_auth_headers(),
            json={"content": "question"},
        )
        events = _parse_sse_events(resp.text)
        finish = next(
            e for e in events if isinstance(e, dict) and e.get("type") == "finish"
        )
        assert finish["finishReason"] == "stop"
        meta = finish["messageMetadata"]
        assert meta["sessionId"] == "sess-42"
        assert meta["costUsd"] == 0.015
        assert meta["numTurns"] == 3
        assert meta["durationMs"] == 1200

    def test_stream_ends_with_done(
        self, client: TestClient, mock_brain: MagicMock
    ) -> None:
        """7. Stream ends with data: [DONE]."""
        mock_brain.process_message_stream = MagicMock(
            side_effect=_make_stream_gen(
                FakeResultMessage(result="Hi", session_id="s1")
            )
        )
        resp = client.post(
            "/api/v1/messages/stream",
            headers=_auth_headers(),
            json={"content": "Hello"},
        )
        events = _parse_sse_events(resp.text)
        assert events[-1] == "[DONE]"

    def test_auth_required_returns_401(
        self, client: TestClient, mock_brain: MagicMock
    ) -> None:
        """8. Auth required (401 without key)."""
        resp = client.post(
            "/api/v1/messages/stream",
            json={"content": "Hello"},
        )
        assert resp.status_code == 401

    def test_bad_input_returns_422(
        self, client: TestClient, mock_brain: MagicMock
    ) -> None:
        """9. Bad input returns 422."""
        resp = client.post(
            "/api/v1/messages/stream",
            headers=_auth_headers(),
            json={},  # missing required 'content' field
        )
        assert resp.status_code == 422

    @patch("koro.api.routes.stream.AssistantMessage", FakeAssistantMessage)
    @patch("koro.api.routes.stream.ResultMessage", FakeResultMessage)
    @patch("koro.api.routes.stream.TextBlock", FakeTextBlock)
    @patch("koro.api.routes.stream.ToolUseBlock", FakeToolUseBlock)
    @patch("koro.api.routes.stream.ToolResultBlock", FakeToolResultBlock)
    def test_mid_stream_error_emits_error_event(
        self, client: TestClient, mock_brain: MagicMock
    ) -> None:
        """10. Mid-stream error emits error event then [DONE]."""

        async def failing_stream(**kwargs):
            yield FakeAssistantMessage([FakeTextBlock("Start")])
            raise RuntimeError("Claude connection lost")

        mock_brain.process_message_stream = MagicMock(side_effect=failing_stream)
        resp = client.post(
            "/api/v1/messages/stream",
            headers=_auth_headers(),
            json={"content": "Hello"},
        )
        events = _parse_sse_events(resp.text)
        error_event = next(
            (e for e in events if isinstance(e, dict) and e.get("type") == "error"),
            None,
        )
        assert error_event is not None
        assert "Claude connection lost" in error_event["errorText"]
        assert events[-1] == "[DONE]"
