"""User settings endpoints."""

from typing import Literal

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from koro.core.brain import get_brain
from koro.core.types import Mode

router = APIRouter()


class SettingsResponse(BaseModel):
    """Response model for user settings."""

    mode: Literal["go_all", "approve"]
    audio_enabled: bool
    voice_speed: float
    watch_enabled: bool


class UpdateSettingsRequest(BaseModel):
    """Request to update user settings."""

    mode: Literal["go_all", "approve"] | None = Field(
        default=None, description="Execution mode for tool calls"
    )
    audio_enabled: bool | None = Field(
        default=None, description="Whether to enable audio responses"
    )
    voice_speed: float | None = Field(
        default=None, ge=0.7, le=1.2, description="Voice speed for TTS"
    )
    watch_enabled: bool | None = Field(
        default=None, description="Whether to stream tool calls"
    )


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    x_user_id: str = Header(..., description="User identifier"),
) -> SettingsResponse:
    """
    Get the current settings for the user.
    """
    brain = get_brain()

    settings = await brain.get_settings(x_user_id)

    return SettingsResponse(
        mode=settings.mode.value,
        audio_enabled=settings.audio_enabled,
        voice_speed=settings.voice_speed,
        watch_enabled=settings.watch_enabled,
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    request: UpdateSettingsRequest,
    x_user_id: str = Header(..., description="User identifier"),
) -> SettingsResponse:
    """
    Update user settings.

    Only the fields provided will be updated.
    """
    brain = get_brain()

    # Build kwargs for update
    kwargs = {}
    if request.mode is not None:
        kwargs["mode"] = Mode(request.mode)
    if request.audio_enabled is not None:
        kwargs["audio_enabled"] = request.audio_enabled
    if request.voice_speed is not None:
        kwargs["voice_speed"] = request.voice_speed
    if request.watch_enabled is not None:
        kwargs["watch_enabled"] = request.watch_enabled

    settings = await brain.update_settings(x_user_id, **kwargs)

    return SettingsResponse(
        mode=settings.mode.value,
        audio_enabled=settings.audio_enabled,
        voice_speed=settings.voice_speed,
        watch_enabled=settings.watch_enabled,
    )


@router.post("/settings/reset", response_model=SettingsResponse)
async def reset_settings(
    x_user_id: str = Header(..., description="User identifier"),
) -> SettingsResponse:
    """
    Reset user settings to defaults.
    """
    brain = get_brain()

    # Reset by setting all values to defaults
    settings = await brain.update_settings(
        x_user_id,
        mode=Mode.GO_ALL,
        audio_enabled=True,
        voice_speed=1.1,
        watch_enabled=False,
    )

    return SettingsResponse(
        mode=settings.mode.value,
        audio_enabled=settings.audio_enabled,
        voice_speed=settings.voice_speed,
        watch_enabled=settings.watch_enabled,
    )
