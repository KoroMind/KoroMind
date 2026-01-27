"""Tests for koro.main module."""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestMainErrorHandler:
    """Tests for main application error handling."""

    def test_error_handler_registered(self, monkeypatch, tmp_path):
        """Application should have an error handler registered."""
        mock_app = MagicMock()
        mock_builder = MagicMock()
        mock_builder.token.return_value = mock_builder
        mock_builder.concurrent_updates.return_value = mock_builder
        mock_builder.build.return_value = mock_app

        # Track calls to add_error_handler
        error_handler_calls = []
        mock_app.add_error_handler = lambda handler: error_handler_calls.append(handler)

        # Use tmp_path for sandbox
        sandbox_dir = tmp_path / "sandbox"

        # Monkeypatch SANDBOX_DIR before importing main
        import koro.main

        monkeypatch.setattr(koro.main, "SANDBOX_DIR", str(sandbox_dir))
        monkeypatch.setattr(koro.main, "ApplicationBuilder", lambda: mock_builder)
        monkeypatch.setattr(koro.main, "validate_environment", lambda: (True, ""))
        monkeypatch.setattr(koro.main, "check_claude_auth", lambda: (True, "api_key"))
        monkeypatch.setattr(koro.main, "apply_saved_credentials", lambda: (None, None))

        mock_state = MagicMock()
        mock_state.load = MagicMock()
        monkeypatch.setattr(koro.main, "get_state_manager", lambda: mock_state)
        monkeypatch.setattr(koro.main, "setup_logging", lambda: None)
        monkeypatch.setattr(mock_app, "run_polling", lambda **kwargs: None)

        koro.main.main()

        # Error handler should have been registered
        assert len(error_handler_calls) == 1, "Error handler should be registered"

    @pytest.mark.asyncio
    async def test_error_handler_logs_errors(self, caplog):
        """Error handler should log errors appropriately."""
        import logging

        with caplog.at_level(logging.ERROR):
            from koro.main import error_handler

            update = MagicMock()
            update.effective_chat.id = 12345
            update.effective_chat.send_message = AsyncMock()

            context = MagicMock()
            context.error = Exception("Test error")

            await error_handler(update, context)

            # Should log the error
            assert any("error" in record.message.lower() for record in caplog.records)
