"""SSE streaming endpoint for real-time message processing."""

import json
import logging
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

from koro.core.brain import get_brain
from koro.core.types import MessageType, Mode

logger = logging.getLogger(__name__)

router = APIRouter()

# System prompt suffix for the chat UI interface
_CHAT_UI_SYSTEM_PROMPT = (
    "## Chat UI context\n"
    "You are responding in a rich web chat UI that renders markdown with full support "
    "for code blocks, mermaid diagrams, tables, and other formatting.\n"
    "- Use markdown freely: headings, bold, lists, code blocks, tables\n"
    "- Output diagrams (mermaid, etc.) as inline fenced code blocks — the UI renders them automatically\n"
    "- Do NOT write diagrams or content to files when the user wants to see them — output them inline\n"
    "- Speak naturally but use rich formatting when it helps clarity"
)


class StreamMessageRequest(BaseModel):
    """Request body for streaming message processing."""

    content: str = Field(..., description="Message content (text)")
    content_type: Literal["text"] = Field(
        default="text", description="Type of content"
    )
    session_id: str | None = Field(
        default=None, description="Session ID to continue conversation"
    )
    mode: Literal["go_all", "approve"] = Field(
        default="go_all", description="Execution mode for tool calls"
    )


def _sse_event(data: dict[str, Any] | str) -> str:
    """Format a single SSE event."""
    if isinstance(data, str):
        return f"data: {data}\n\n"
    return f"data: {json.dumps(data)}\n\n"


async def _stream_events(
    user_id: str,
    request: StreamMessageRequest,
) -> Any:
    """Async generator that yields AI SDK v6 UI Message Stream SSE events."""
    brain = get_brain()
    message_id = f"msg-{uuid.uuid4().hex[:12]}"

    # Emit start event
    yield _sse_event({"type": "start", "messageId": message_id})
    yield _sse_event({"type": "start-step"})

    # State tracking for diffing partial messages
    last_text = ""
    text_id: str | None = None
    seen_tool_ids: set[str] = set()
    seen_result_ids: set[str] = set()

    try:
        async for event in brain.process_message_stream(
            user_id=user_id,
            content=request.content,
            content_type=MessageType(request.content_type),
            session_id=request.session_id,
            mode=Mode(request.mode),
            system_prompt_append=_CHAT_UI_SYSTEM_PROMPT,
        ):
            if isinstance(event, AssistantMessage):
                # Reconstruct full text from all TextBlocks
                full_text = ""
                for block in event.content:
                    if isinstance(block, TextBlock):
                        full_text += block.text

                # Diff text: emit new characters
                if full_text and len(full_text) > len(last_text):
                    if text_id is None:
                        text_id = f"text-{uuid.uuid4().hex[:8]}"
                        yield _sse_event({"type": "text-start", "id": text_id})
                    delta = full_text[len(last_text) :]
                    yield _sse_event(
                        {"type": "text-delta", "id": text_id, "delta": delta}
                    )
                    last_text = full_text

                # Emit tool use blocks (dedupe by block.id)
                for block in event.content:
                    if isinstance(block, ToolUseBlock) and block.id not in seen_tool_ids:
                        seen_tool_ids.add(block.id)
                        yield _sse_event(
                            {
                                "type": "tool-input-available",
                                "toolCallId": block.id,
                                "toolName": block.name,
                                "input": block.input or {},
                            }
                        )

                    if (
                        isinstance(block, ToolResultBlock)
                        and block.tool_use_id not in seen_result_ids
                    ):
                        seen_result_ids.add(block.tool_use_id)
                        # Extract text content from tool result
                        output = block.content if block.content else ""
                        yield _sse_event(
                            {
                                "type": "tool-output-available",
                                "toolCallId": block.tool_use_id,
                                "output": output,
                            }
                        )

            elif isinstance(event, ResultMessage):
                # If there's result text that wasn't streamed yet
                if event.result and event.result != last_text:
                    if text_id is None:
                        text_id = f"text-{uuid.uuid4().hex[:8]}"
                        yield _sse_event({"type": "text-start", "id": text_id})
                    delta = event.result[len(last_text) :]
                    if delta:
                        yield _sse_event(
                            {"type": "text-delta", "id": text_id, "delta": delta}
                        )

                # Close text block if opened
                if text_id is not None:
                    yield _sse_event({"type": "text-end", "id": text_id})

                # Build metadata for messageMetadata field
                msg_metadata: dict[str, Any] = {}
                if event.session_id:
                    msg_metadata["sessionId"] = event.session_id
                if event.total_cost_usd is not None:
                    msg_metadata["costUsd"] = event.total_cost_usd
                if event.num_turns is not None:
                    msg_metadata["numTurns"] = event.num_turns
                if event.duration_ms is not None:
                    msg_metadata["durationMs"] = event.duration_ms
                if event.is_error:
                    msg_metadata["isError"] = True

                yield _sse_event({"type": "finish-step"})
                finish_event: dict[str, Any] = {
                    "type": "finish",
                    "finishReason": "error" if event.is_error else "stop",
                }
                if msg_metadata:
                    finish_event["messageMetadata"] = msg_metadata
                yield _sse_event(finish_event)

    except Exception as exc:
        logger.exception("Error during message streaming")
        yield _sse_event({"type": "error", "errorText": str(exc)})

    # End stream
    yield _sse_event("[DONE]")


@router.post("/messages/stream")
async def stream_message(
    request: StreamMessageRequest,
    http_request: Request,
) -> StreamingResponse:
    """
    Process a text message and stream the response as SSE events.

    Uses the AI SDK v6 UI Message Stream Protocol (v1).
    """
    brain = get_brain()
    if brain is None:
        raise HTTPException(status_code=503, detail="Brain not initialized")

    user_id = http_request.state.user_id

    return StreamingResponse(
        _stream_events(user_id, request),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
