"""Unit tests for settings API request model validation."""

import pytest
from pydantic import ValidationError

from koro.api.routes.settings import UpdateSettingsRequest


def test_update_settings_model_allows_empty_and_valid_identifiers() -> None:
    """Model override accepts empty/default and valid model IDs."""
    assert UpdateSettingsRequest(model="").model == ""
    assert UpdateSettingsRequest(model=None).model is None
    assert (
        UpdateSettingsRequest(model="claude-sonnet-4.5_2026.01").model
        == "claude-sonnet-4.5_2026.01"
    )


def test_update_settings_model_rejects_invalid_identifier() -> None:
    """Model override rejects unsupported characters and formatting."""
    with pytest.raises(ValidationError):
        UpdateSettingsRequest(model="bad model\nname")


def test_update_settings_stt_language_accepts_auto_and_codes() -> None:
    """STT language accepts auto and normalized language codes."""
    assert UpdateSettingsRequest(stt_language="auto").stt_language == "auto"
    assert UpdateSettingsRequest(stt_language="PL").stt_language == "pl"
    assert UpdateSettingsRequest(stt_language="pt-BR").stt_language == "pt-br"


def test_update_settings_stt_language_rejects_invalid_code() -> None:
    """STT language rejects invalid code formats."""
    with pytest.raises(ValidationError):
        UpdateSettingsRequest(stt_language="bad/code")
