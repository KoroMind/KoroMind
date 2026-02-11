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
