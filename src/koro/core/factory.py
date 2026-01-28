"""Factory for building the Brain instance with all dependencies wired.

Both Telegram and API processes should call build_brain() to get a fully
configured Brain instance. This prevents drift across processes.
"""

from pathlib import Path

from koro.core.brain import Brain
from koro.core.config import DATABASE_PATH, SANDBOX_DIR, VAULT_DIR
from koro.core.rate_limit import RateLimiter
from koro.core.state import StateManager
from koro.providers.llm.claude import ClaudeClient
from koro.providers.voice.elevenlabs import VoiceEngine, get_voice_engine


def build_brain(
    db_path: Path | str | None = None,
    sandbox_dir: Path | str | None = None,
    vault_dir: Path | str | None = None,
    elevenlabs_api_key: str | None = None,
    voice_id: str | None = None,
) -> Brain:
    """
    Build a fully configured Brain instance.

    This is the canonical way to create a Brain. Both Telegram bot and API
    server should use this function to ensure consistent configuration.

    Args:
        db_path: Path to SQLite database (defaults to config)
        sandbox_dir: Directory for Claude to write/execute (defaults to config)
        vault_dir: Directory for vault storage (defaults to config)
        elevenlabs_api_key: ElevenLabs API key (defaults to env)
        voice_id: ElevenLabs voice ID (defaults to env)

    Returns:
        Fully configured Brain instance
    """
    # Resolve paths
    actual_db_path = Path(db_path) if db_path else DATABASE_PATH
    actual_sandbox = str(sandbox_dir) if sandbox_dir else str(SANDBOX_DIR)
    actual_vault = Path(vault_dir) if vault_dir else VAULT_DIR

    # Ensure directories exist
    actual_db_path.parent.mkdir(parents=True, exist_ok=True)
    Path(actual_sandbox).mkdir(parents=True, exist_ok=True)
    actual_vault.mkdir(parents=True, exist_ok=True)

    # Create components
    state_manager = StateManager(db_path=actual_db_path)

    claude_client = ClaudeClient(
        sandbox_dir=actual_sandbox,
        working_dir=actual_sandbox,
    )

    # Get voice engine (uses global singleton with defaults)
    if elevenlabs_api_key:
        voice_engine = VoiceEngine(api_key=elevenlabs_api_key, voice_id=voice_id)
    else:
        voice_engine = get_voice_engine()

    rate_limiter = RateLimiter()

    return Brain(
        state_manager=state_manager,
        claude_client=claude_client,
        voice_engine=voice_engine,
        rate_limiter=rate_limiter,
    )


def build_brain_minimal() -> Brain:
    """
    Build a minimal Brain instance with default configuration.

    Convenience wrapper that uses all defaults from environment/config.
    """
    return build_brain()
