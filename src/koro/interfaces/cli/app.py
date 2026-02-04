"""CLI application for KoroMind using Rich and Typer."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from koro.core.brain import Brain
from koro.core.config import validate_core_environment
from koro.core.types import Mode

# Default vault location
DEFAULT_VAULT_PATH = Path.home() / ".koromind"

app = typer.Typer(
    name="koro",
    help="KoroMind CLI - Your Personal AI Assistant",
    no_args_is_help=False,
)

console = Console()


def print_welcome():
    """Print welcome message."""
    console.print(
        Panel.fit(
            "[bold blue]KoroMind CLI[/bold blue]\n"
            "[dim]Your Personal AI Assistant[/dim]\n\n"
            "Type your message and press Enter.\n"
            "Commands: /new, /sessions, /settings, /help, /quit",
            title="Welcome",
            border_style="blue",
        )
    )


def print_help():
    """Print help message."""
    table = Table(title="Commands", show_header=True, header_style="bold cyan")
    table.add_column("Command", style="green")
    table.add_column("Description")

    commands = [
        ("/new", "Start a new conversation session"),
        ("/sessions", "List all sessions"),
        ("/switch <id>", "Switch to a specific session"),
        ("/settings", "View/modify settings"),
        ("/audio on|off", "Toggle audio responses"),
        ("/mode go_all|approve", "Set execution mode"),
        ("/health", "Check system health"),
        ("/help", "Show this help message"),
        ("/quit", "Exit the CLI"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)


async def handle_command(brain: Brain, user_id: str, command: str) -> bool:
    """
    Handle a CLI command.

    Returns True if the REPL should continue, False to exit.
    """
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if cmd in ("/quit", "/exit", "/q"):
        console.print("[dim]Goodbye![/dim]")
        return False

    elif cmd == "/help":
        print_help()

    elif cmd == "/new":
        session = await brain.create_session(user_id)
        console.print(f"[green]New session created: {session.id[:8]}...[/green]")

    elif cmd == "/sessions":
        sessions = await brain.get_sessions(user_id)
        current = await brain.get_current_session(user_id)
        current_id = current.id if current else None

        if not sessions:
            console.print("[dim]No sessions yet.[/dim]")
        else:
            table = Table(title="Sessions", show_header=True)
            table.add_column("#", style="dim")
            table.add_column("ID")
            table.add_column("Last Active")
            table.add_column("Status")

            for i, sess in enumerate(sessions[:10], 1):
                status = "[green]current[/green]" if sess.id == current_id else ""
                table.add_row(
                    str(i),
                    sess.id[:8] + "...",
                    sess.last_active.strftime("%Y-%m-%d %H:%M"),
                    status,
                )

            console.print(table)

    elif cmd == "/switch":
        if not args:
            console.print("[red]Usage: /switch <session_id>[/red]")
        else:
            sessions = await brain.get_sessions(user_id)
            matches = [s for s in sessions if s.id.startswith(args)]

            if len(matches) == 1:
                await brain.switch_session(user_id, matches[0].id)
                console.print(
                    f"[green]Switched to session: {matches[0].id[:8]}...[/green]"
                )
            elif len(matches) > 1:
                console.print("[yellow]Multiple matches. Be more specific.[/yellow]")
            else:
                console.print(f"[red]Session not found: {args}[/red]")

    elif cmd == "/settings":
        settings = await brain.get_settings(user_id)
        table = Table(title="Settings", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value")

        table.add_row("Mode", settings.mode.value)
        table.add_row("Audio", "enabled" if settings.audio_enabled else "disabled")
        table.add_row("Voice Speed", f"{settings.voice_speed}x")
        table.add_row("Watch Mode", "enabled" if settings.watch_enabled else "disabled")

        console.print(table)

    elif cmd == "/audio":
        if args.lower() in ("on", "true", "1"):
            await brain.update_settings(user_id, audio_enabled=True)
            console.print("[green]Audio enabled[/green]")
        elif args.lower() in ("off", "false", "0"):
            await brain.update_settings(user_id, audio_enabled=False)
            console.print("[yellow]Audio disabled[/yellow]")
        else:
            console.print("[red]Usage: /audio on|off[/red]")

    elif cmd == "/mode":
        if args.lower() == "go_all":
            await brain.update_settings(user_id, mode=Mode.GO_ALL)
            console.print("[green]Mode set to: go_all[/green]")
        elif args.lower() == "approve":
            await brain.update_settings(user_id, mode=Mode.APPROVE)
            console.print(
                "[yellow]Mode set to: approve (not supported in CLI)[/yellow]"
            )
        else:
            console.print("[red]Usage: /mode go_all|approve[/red]")

    elif cmd == "/health":
        health = brain.health_check()
        table = Table(title="Health Check", show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Status")
        table.add_column("Message")

        for component, (healthy, message) in health.items():
            status = "[green]OK[/green]" if healthy else "[red]FAILED[/red]"
            table.add_row(component.title(), status, message)

        console.print(table)

    else:
        console.print(f"[red]Unknown command: {cmd}[/red]")
        console.print("[dim]Type /help for available commands.[/dim]")

    return True


async def process_message(brain: Brain, user_id: str, text: str):
    """Process a user message and display the response."""
    settings = await brain.get_settings(user_id)

    with console.status("[bold blue]Thinking...[/bold blue]"):
        response = await brain.process_text(
            user_id=user_id,
            text=text,
            mode=settings.mode,
            include_audio=False,  # No audio in CLI for now
        )

    # Display response
    console.print()
    console.print(Panel(Markdown(response.text), title="Koro", border_style="green"))

    # Show metadata if available
    if response.metadata:
        meta_parts = []
        if "cost" in response.metadata:
            meta_parts.append(f"Cost: ${response.metadata['cost']:.4f}")
        if "num_turns" in response.metadata:
            meta_parts.append(f"Turns: {response.metadata['num_turns']}")
        if "tool_count" in response.metadata:
            meta_parts.append(f"Tools: {response.metadata['tool_count']}")

        if meta_parts:
            console.print(f"[dim]{' | '.join(meta_parts)}[/dim]")

    console.print()


def _get_vault_path(vault: Optional[str]) -> Optional[Path]:
    """Resolve vault path from argument, env var, or default."""
    if vault:
        path = Path(vault).expanduser()
        if path.exists():
            return path
        console.print(f"[yellow]Warning: Vault path not found: {vault}[/yellow]")
        return None

    # Check env var
    env_vault = os.environ.get("KOROMIND_VAULT")
    if env_vault:
        path = Path(env_vault).expanduser()
        if path.exists():
            return path

    # Check default location
    if DEFAULT_VAULT_PATH.exists():
        return DEFAULT_VAULT_PATH

    return None


async def repl(user_id: str, vault_path: Optional[Path] = None):
    """Run the REPL (Read-Eval-Print Loop)."""
    brain = Brain(vault_path=vault_path)

    # Check environment
    is_valid, message = validate_core_environment()
    if not is_valid:
        console.print(f"[red]Error: {message}[/red]")
        console.print("[dim]Please set ANTHROPIC_API_KEY in your environment.[/dim]")
        return

    print_welcome()

    # Show vault status
    if brain.vault and brain.vault.exists:
        config = brain.vault.load()
        console.print(f"[dim]Vault: {brain.vault.root}[/dim]")
        parts = []
        if config.mcp_servers:
            parts.append(f"{len(config.mcp_servers)} MCP servers")
        if config.agents:
            parts.append(f"{len(config.agents)} agents")
        if config.hooks:
            parts.append(f"{len(config.hooks)} hooks")
        if parts:
            console.print(f"[dim]Loaded: {', '.join(parts)}[/dim]")
    else:
        console.print(
            "[yellow]Warning: No vault configured. "
            "Use --vault or set KOROMIND_VAULT for custom configuration.[/yellow]"
        )
    console.print()

    while True:
        try:
            # Get input
            text = Prompt.ask("[bold blue]You[/bold blue]")

            if not text.strip():
                continue

            # Handle commands
            if text.startswith("/"):
                should_continue = await handle_command(brain, user_id, text)
                if not should_continue:
                    break
            else:
                # Process as message
                await process_message(brain, user_id, text)

        except KeyboardInterrupt:
            console.print("\n[dim]Use /quit to exit.[/dim]")
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


@app.command()
def chat(
    user_id: Optional[str] = typer.Option(
        None,
        "--user",
        "-u",
        help="User ID (defaults to 'cli-user')",
    ),
    vault: Optional[str] = typer.Option(
        None,
        "--vault",
        "-v",
        help="Path to vault directory (default: ~/.koromind or $KOROMIND_VAULT)",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug logging",
    ),
):
    """Start an interactive chat session."""
    # Configure logging
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(name)s %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        console.print("[dim]Debug logging enabled[/dim]")

    uid = user_id or "cli-user"
    vault_path = _get_vault_path(vault)
    asyncio.run(repl(uid, vault_path))


@app.command()
def health(
    vault: Optional[str] = typer.Option(
        None,
        "--vault",
        "-v",
        help="Path to vault directory",
    ),
):
    """Check system health."""
    vault_path = _get_vault_path(vault)
    brain = Brain(vault_path=vault_path)
    health_status = brain.health_check()

    table = Table(title="Health Check", show_header=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Message")

    # Add vault status
    if brain.vault:
        vault_ok = brain.vault.exists
        vault_msg = str(brain.vault.root) if vault_ok else "config not found"
        table.add_row(
            "Vault",
            "[green]OK[/green]" if vault_ok else "[yellow]WARN[/yellow]",
            vault_msg,
        )

    all_healthy = True
    for component, (healthy, message) in health_status.items():
        status = "[green]OK[/green]" if healthy else "[red]FAILED[/red]"
        table.add_row(component.title(), status, message)
        if not healthy:
            all_healthy = False

    console.print(table)
    raise typer.Exit(0 if all_healthy else 1)


@app.command()
def sessions(
    user_id: Optional[str] = typer.Option(
        None,
        "--user",
        "-u",
        help="User ID (defaults to 'cli-user')",
    ),
):
    """List all sessions for a user."""

    async def _list():
        brain = Brain()
        uid = user_id or "cli-user"
        sess_list = await brain.get_sessions(uid)
        current = await brain.get_current_session(uid)
        current_id = current.id if current else None

        if not sess_list:
            console.print("[dim]No sessions yet.[/dim]")
            return

        table = Table(title=f"Sessions for {uid}", show_header=True)
        table.add_column("#", style="dim")
        table.add_column("ID")
        table.add_column("Created")
        table.add_column("Last Active")
        table.add_column("Status")

        for i, sess in enumerate(sess_list, 1):
            status = "[green]current[/green]" if sess.id == current_id else ""
            table.add_row(
                str(i),
                sess.id[:8] + "...",
                sess.created_at.strftime("%Y-%m-%d %H:%M"),
                sess.last_active.strftime("%Y-%m-%d %H:%M"),
                status,
            )

        console.print(table)

    asyncio.run(_list())


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """KoroMind CLI - Your Personal AI Assistant."""
    if ctx.invoked_subcommand is None:
        # Default to chat
        chat()


def run_cli():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    run_cli()
