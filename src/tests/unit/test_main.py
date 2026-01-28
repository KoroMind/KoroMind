"""Tests for koro.main module."""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

import koro.core.config as config
from koro.main import main


@pytest.fixture
def mock_telegram_bot(monkeypatch):
    """Provide a mocked telegram bot module."""
    module = MagicMock()
    module.run_telegram_bot = MagicMock()
    monkeypatch.setitem(sys.modules, "koro.interfaces.telegram.bot", module)
    return module


@pytest.fixture
def mock_cli_app(monkeypatch):
    """Provide a mocked CLI app module."""
    module = MagicMock()
    module.run_cli = MagicMock()
    monkeypatch.setitem(sys.modules, "koro.interfaces.cli.app", module)
    return module


@pytest.fixture
def mock_uvicorn(monkeypatch):
    """Provide a mocked uvicorn module."""
    module = MagicMock()
    module.run = MagicMock()
    monkeypatch.setitem(sys.modules, "uvicorn", module)
    return module


@pytest.fixture
def config_defaults(monkeypatch):
    """Set predictable API defaults for tests."""
    monkeypatch.setattr(config, "KOROMIND_HOST", "127.0.0.1")
    monkeypatch.setattr(config, "KOROMIND_PORT", 8420)


class TestMainEntryPoint:
    """Tests for the main entry point and interface selection."""

    def test_main_defaults_to_telegram(self, monkeypatch, mock_telegram_bot):
        """Main entry point defaults to telegram interface."""
        monkeypatch.setattr(sys, "argv", ["koro"])

        main()

        mock_telegram_bot.run_telegram_bot.assert_called_once()

    def test_main_accepts_telegram_arg(self, monkeypatch, mock_telegram_bot):
        """Main entry point accepts explicit telegram argument."""
        monkeypatch.setattr(sys, "argv", ["koro", "telegram"])

        main()

        mock_telegram_bot.run_telegram_bot.assert_called_once()

    @pytest.mark.parametrize(
        "argv,expected_host,expected_port",
        [
            (["koro", "api"], "127.0.0.1", 8420),
            (["koro", "api", "--port", "9000"], "127.0.0.1", 9000),
            (["koro", "api", "--host", "0.0.0.0"], "0.0.0.0", 8420),
        ],
    )
    def test_main_api_starts_uvicorn(
        self,
        monkeypatch,
        mock_uvicorn,
        config_defaults,
        argv,
        expected_host,
        expected_port,
    ):
        """Main entry point starts uvicorn for API interface."""
        monkeypatch.setattr(sys, "argv", argv)

        main()

        mock_uvicorn.run.assert_called_once()
        call_kwargs = mock_uvicorn.run.call_args.kwargs
        assert call_kwargs["host"] == expected_host
        assert call_kwargs["port"] == expected_port

    def test_main_cli_starts_cli(self, monkeypatch, mock_cli_app):
        """Main entry point starts CLI interface."""
        monkeypatch.setattr(sys, "argv", ["koro", "cli"])

        main()

        mock_cli_app.run_cli.assert_called_once()


class TestTelegramBotErrorHandler:
    """Tests for error handling in the Telegram bot."""

    @pytest.mark.asyncio
    async def test_error_handler_reports_to_chat(self):
        """error_handler sends a user-friendly message."""
        from koro.interfaces.telegram.bot import error_handler

        update = MagicMock()
        update.effective_chat.send_message = AsyncMock()
        context = MagicMock()
        context.error = Exception("boom")

        await error_handler(update, context)

        update.effective_chat.send_message.assert_called_once()
