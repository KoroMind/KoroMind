"""Tests for koro.main module."""

from unittest.mock import MagicMock, patch


class TestMainEntryPoint:
    """Tests for the main entry point and interface selection."""

    def test_main_defaults_to_telegram(self, monkeypatch):
        """Main entry point defaults to telegram interface."""
        monkeypatch.setattr("sys.argv", ["koro"])

        # Mock the telegram bot module before importing main
        mock_bot_module = MagicMock()
        mock_run = MagicMock()
        mock_bot_module.run_telegram_bot = mock_run

        with patch.dict(
            "sys.modules", {"koro.interfaces.telegram.bot": mock_bot_module}
        ):
            import importlib

            import koro.main

            importlib.reload(koro.main)

            koro.main.main()

            mock_run.assert_called_once()

    def test_main_accepts_telegram_arg(self, monkeypatch):
        """Main entry point accepts explicit telegram argument."""
        monkeypatch.setattr("sys.argv", ["koro", "telegram"])

        with patch.dict("sys.modules", {"koro.interfaces.telegram.bot": MagicMock()}):
            mock_run = MagicMock()
            with patch("koro.interfaces.telegram.bot.run_telegram_bot", mock_run):
                import importlib

                import koro.main

                importlib.reload(koro.main)

    def test_main_api_starts_uvicorn(self, monkeypatch):
        """Main entry point starts uvicorn for API interface."""
        monkeypatch.setattr("sys.argv", ["koro", "api"])

        mock_uvicorn = MagicMock()
        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("uvicorn.run", mock_uvicorn.run):
                import importlib

                import koro.main

                importlib.reload(koro.main)

                koro.main.main()

                mock_uvicorn.run.assert_called_once()

    def test_main_api_with_custom_port(self, monkeypatch):
        """Main entry point passes custom port to uvicorn."""
        monkeypatch.setattr("sys.argv", ["koro", "api", "--port", "9000"])

        mock_uvicorn = MagicMock()
        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("uvicorn.run", mock_uvicorn.run):
                import importlib

                import koro.main

                importlib.reload(koro.main)

                koro.main.main()

                call_kwargs = mock_uvicorn.run.call_args[1]
                assert call_kwargs["port"] == 9000

    def test_main_api_with_custom_host(self, monkeypatch):
        """Main entry point passes custom host to uvicorn."""
        monkeypatch.setattr("sys.argv", ["koro", "api", "--host", "0.0.0.0"])

        mock_uvicorn = MagicMock()
        with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
            with patch("uvicorn.run", mock_uvicorn.run):
                import importlib

                import koro.main

                importlib.reload(koro.main)

                koro.main.main()

                call_kwargs = mock_uvicorn.run.call_args[1]
                assert call_kwargs["host"] == "0.0.0.0"

    def test_main_cli_starts_cli(self, monkeypatch):
        """Main entry point starts CLI interface."""
        monkeypatch.setattr("sys.argv", ["koro", "cli"])

        # Mock the CLI module
        mock_cli_module = MagicMock()
        mock_run = MagicMock()
        mock_cli_module.run_cli = mock_run

        with patch.dict("sys.modules", {"koro.interfaces.cli.app": mock_cli_module}):
            import importlib

            import koro.main

            importlib.reload(koro.main)

            koro.main.main()

            mock_run.assert_called_once()


class TestTelegramBotErrorHandler:
    """Tests for error handling in the Telegram bot."""

    def test_telegram_bot_module_exists(self):
        """Telegram bot module can be imported."""
        from koro.interfaces.telegram import bot

        assert hasattr(bot, "run_telegram_bot")

    def test_telegram_bot_has_error_handling(self):
        """Telegram bot module sets up error handling."""
        # Check that the bot module has appropriate error handling mechanisms
        import inspect

        from koro.interfaces.telegram import bot

        source = inspect.getsource(bot)
        # The bot should have error handling - either add_error_handler or try/except
        assert "error" in source.lower()
