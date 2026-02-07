"""Unified entry point for KoroMind.

This module provides a unified entry point that can start different interfaces:
- Telegram bot (default)
- REST API server
- CLI interface (future)
"""

import argparse
import sys


def main():
    """Main entry point with interface selection."""
    parser = argparse.ArgumentParser(
        description="KoroMind - Your Personal AI Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Interfaces:
  telegram    Start the Telegram bot (default)
  api         Start the REST API server
  cli         Start the CLI interface (coming soon)

Examples:
  python -m koro                    # Start Telegram bot
  python -m koro telegram           # Start Telegram bot
  python -m koro api                # Start API server
  python -m koro api --port 8080    # Start API on custom port
""",
    )

    parser.add_argument(
        "interface",
        nargs="?",
        default="telegram",
        choices=["telegram", "api", "cli"],
        help="Which interface to start (default: telegram)",
    )

    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind API server to (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for API server (default: 8420)",
    )

    args = parser.parse_args()

    if args.interface == "telegram":
        from koro.interfaces.telegram.bot import run_telegram_bot

        run_telegram_bot()

    elif args.interface == "api":
        import uvicorn

        from koro.core.config import KOROMIND_HOST, KOROMIND_PORT

        host = args.host or KOROMIND_HOST or "127.0.0.1"
        port = args.port or KOROMIND_PORT

        print(f"Starting KoroMind API server on {host}:{port}")
        uvicorn.run(
            "koro.api.app:app",
            host=host,
            port=port,
            reload=False,
        )

    elif args.interface == "cli":
        try:
            from koro.interfaces.cli.app import run_cli

            run_cli()
        except ImportError:
            print("CLI interface not yet available. Use 'telegram' or 'api'.")
            sys.exit(1)


if __name__ == "__main__":
    main()
