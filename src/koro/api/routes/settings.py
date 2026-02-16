"""User settings endpoints."""

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from koro.core.brain import get_brain
from koro.core.config import VOICE_STT_LANGUAGE_DEFAULT
from koro.core.model_validation import MODEL_IDENTIFIER_PATTERN
from koro.core.types import Mode, normalize_stt_language_code

router = APIRouter()


def _default_stt_language() -> str:
    """Return normalized default STT language, falling back to auto."""
    try:
        return normalize_stt_language_code(VOICE_STT_LANGUAGE_DEFAULT)
    except ValueError:
        return "auto"


class SettingsResponse(BaseModel):
    """Response model for user settings."""

    mode: Literal["go_all", "approve"]
    audio_enabled: bool
    voice_speed: float
    watch_enabled: bool
    model: str = Field(default="", description="Claude model override")
    stt_language: str = Field(
        default="auto", description="STT language code ('auto', 'en', 'pl', ...)"
    )


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
    model: str | None = Field(
        default=None, description="Claude model override (empty string for default)"
    )
    stt_language: str | None = Field(
        default=None, description="STT language code ('auto', 'en', 'pl', ...)"
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str | None) -> str | None:
        """Allow empty/default model, otherwise enforce a safe model identifier."""
        if value is None or value == "":
            return value
        if not MODEL_IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError("Invalid model identifier")
        return value

    @field_validator("stt_language")
    @classmethod
    def validate_stt_language(cls, value: str | None) -> str | None:
        """Validate STT language code."""
        if value is None:
            return None
        return normalize_stt_language_code(value)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    http_request: Request,
) -> SettingsResponse:
    """
    Get the current settings for the user.
    """
    brain = get_brain()
    user_id = http_request.state.user_id

    settings = await brain.get_settings(user_id)

    return SettingsResponse(
        mode=settings.mode.value,
        audio_enabled=settings.audio_enabled,
        voice_speed=settings.voice_speed,
        watch_enabled=settings.watch_enabled,
        model=settings.model,
        stt_language=settings.stt_language,
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    request: UpdateSettingsRequest,
    http_request: Request,
) -> SettingsResponse:
    """
    Update user settings.

    Only the fields provided will be updated.
    """
    brain = get_brain()
    user_id = http_request.state.user_id

    # Build kwargs for update
    kwargs: dict[str, Mode | bool | float | str] = {}
    if request.mode is not None:
        kwargs["mode"] = Mode(request.mode)
    if request.audio_enabled is not None:
        kwargs["audio_enabled"] = request.audio_enabled
    if request.voice_speed is not None:
        kwargs["voice_speed"] = request.voice_speed
    if request.watch_enabled is not None:
        kwargs["watch_enabled"] = request.watch_enabled
    if request.model is not None:
        kwargs["model"] = request.model
    if request.stt_language is not None:
        kwargs["stt_language"] = request.stt_language

    settings = await brain.update_settings(user_id, **kwargs)

    return SettingsResponse(
        mode=settings.mode.value,
        audio_enabled=settings.audio_enabled,
        voice_speed=settings.voice_speed,
        watch_enabled=settings.watch_enabled,
        model=settings.model,
        stt_language=settings.stt_language,
    )


@router.post("/settings/reset", response_model=SettingsResponse)
async def reset_settings(
    http_request: Request,
) -> SettingsResponse:
    """
    Reset user settings to defaults.
    """
    brain = get_brain()
    user_id = http_request.state.user_id

    # Reset by setting all values to defaults
    settings = await brain.update_settings(
        user_id,
        mode=Mode.GO_ALL,
        audio_enabled=True,
        voice_speed=1.1,
        watch_enabled=False,
        model="",
        stt_language=_default_stt_language(),
    )

    return SettingsResponse(
        mode=settings.mode.value,
        audio_enabled=settings.audio_enabled,
        voice_speed=settings.voice_speed,
        watch_enabled=settings.watch_enabled,
        model=settings.model,
        stt_language=settings.stt_language,
    )
