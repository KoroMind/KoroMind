"""Message processing endpoints."""

import base64
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from koro.core.brain import get_brain
from koro.core.types import MessageType, Mode

router = APIRouter()


class MessageRequest(BaseModel):
    """Request body for processing a message."""

    content: str = Field(
        ..., description="Message content (text or base64-encoded audio)"
    )
    content_type: Literal["text", "voice"] = Field(
        default="text", description="Type of content"
    )
    session_id: str | None = Field(
        default=None, description="Session ID to continue conversation"
    )
    mode: Literal["go_all", "approve"] = Field(
        default="go_all", description="Execution mode for tool calls"
    )
    include_audio: bool = Field(
        default=True, description="Whether to include TTS audio in response"
    )
    voice_speed: float = Field(
        default=1.1, ge=0.7, le=1.2, description="Voice speed for TTS"
    )


class MessageResponse(BaseModel):
    """Response from message processing."""

    text: str = Field(..., description="Response text")
    session_id: str = Field(..., description="Session ID for continuation")
    audio: str | None = Field(
        default=None, description="Base64-encoded audio (if include_audio was true)"
    )
    tool_calls: list[dict] = Field(
        default_factory=list, description="List of tool calls made"
    )
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


@router.post("/messages", response_model=MessageResponse)
async def process_message(
    request: MessageRequest,
    http_request: Request,
) -> MessageResponse:
    """
    Process a text or voice message and return Claude's response.

    For voice messages, the content should be base64-encoded audio bytes.
    """
    brain = get_brain()
    user_id = http_request.state.user_id

    # Decode voice content if needed
    if request.content_type == "voice":
        try:
            content = base64.b64decode(request.content)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64-encoded audio: {e}",
            )
        message_type = MessageType.VOICE
    else:
        content = request.content
        message_type = MessageType.TEXT

    # Process the message
    response = await brain.process_message(
        user_id=user_id,
        content=content,
        content_type=message_type,
        session_id=request.session_id,
        mode=Mode(request.mode),
        include_audio=request.include_audio,
        voice_speed=request.voice_speed,
    )

    # Encode audio as base64 if present
    audio_b64 = None
    if response.audio:
        audio_b64 = base64.b64encode(response.audio).decode("utf-8")

    return MessageResponse(
        text=response.text,
        session_id=response.session_id,
        audio=audio_b64,
        tool_calls=[
            {"name": tc.name, "detail": tc.detail} for tc in response.tool_calls
        ],
        metadata=response.metadata,
    )


class TextMessageRequest(BaseModel):
    """Simplified request body for text messages."""

    text: str = Field(..., description="Text message to process")
    session_id: str | None = Field(default=None, description="Session ID to continue")
    include_audio: bool = Field(default=True, description="Include TTS audio")


@router.post("/messages/text", response_model=MessageResponse)
async def process_text_message(
    request: TextMessageRequest,
    http_request: Request,
) -> MessageResponse:
    """
    Process a text message (convenience endpoint).

    This is a simplified version of POST /messages for text-only requests.
    """
    brain = get_brain()
    user_id = http_request.state.user_id

    response = await brain.process_text(
        user_id=user_id,
        text=request.text,
        session_id=request.session_id,
        include_audio=request.include_audio,
    )

    audio_b64 = None
    if response.audio:
        audio_b64 = base64.b64encode(response.audio).decode("utf-8")

    return MessageResponse(
        text=response.text,
        session_id=response.session_id,
        audio=audio_b64,
        tool_calls=[
            {"name": tc.name, "detail": tc.detail} for tc in response.tool_calls
        ],
        metadata=response.metadata,
    )
