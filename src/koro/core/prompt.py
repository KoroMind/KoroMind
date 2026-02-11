"""System prompt loading and building."""

from datetime import datetime
from pathlib import Path
from threading import Lock

from koro.core.config import (
    BASE_DIR,
    CLAUDE_WORKING_DIR,
    SANDBOX_DIR,
    SYSTEM_PROMPT_FILE,
)
from koro.core.types import UserSettings


def load_system_prompt(prompt_file: str | None = None) -> str:
    """
    Load system prompt from file or use default.

    Args:
        prompt_file: Path to prompt file (defaults to env)

    Returns:
        System prompt content
    """
    file_path = prompt_file or SYSTEM_PROMPT_FILE

    if file_path:
        prompt_path = Path(file_path)
        was_relative = not prompt_path.is_absolute()

        # If relative, look relative to BASE_DIR
        if was_relative:
            prompt_path = BASE_DIR / prompt_path

        try:
            resolved_path = prompt_path.resolve()

            # For relative paths, validate they stay within BASE_DIR
            # This prevents path traversal attacks like "../../../etc/passwd"
            if was_relative:
                base_resolved = BASE_DIR.resolve()
                if not str(resolved_path).startswith(str(base_resolved)):
                    # Path traversal attempt - fall through to default prompt
                    pass
                elif resolved_path.exists():
                    content = resolved_path.read_text()
                    content = content.replace("{sandbox_dir}", SANDBOX_DIR or "")
                    content = content.replace("{read_dir}", CLAUDE_WORKING_DIR or "")
                    return content
            elif resolved_path.exists():
                # Absolute paths are trusted (admin-configured)
                content = resolved_path.read_text()
                content = content.replace("{sandbox_dir}", SANDBOX_DIR or "")
                content = content.replace("{read_dir}", CLAUDE_WORKING_DIR or "")
                return content
        except (OSError, ValueError):
            # Invalid path - fall through to default prompt
            pass

    # Fallback default prompt
    return f"""You are a voice assistant. You're talking to the user.

## CRITICAL - Voice output rules:
- NO markdown formatting (no **, no ##, no ```)
- NO bullet points or numbered lists in speech
- Speak in natural flowing sentences

## Your capabilities:
- You can READ files from anywhere in {CLAUDE_WORKING_DIR}
- You can WRITE and EXECUTE only in {SANDBOX_DIR}
- You have WebSearch for current information

Remember: You're being heard, not read. Speak naturally."""


def build_dynamic_prompt(
    base_prompt: str,
    user_settings: UserSettings,
) -> str:
    """
    Build dynamic system prompt with current date/time and user settings.

    Args:
        base_prompt: The base system prompt
        user_settings: Optional user settings

    Returns:
        Complete system prompt with dynamic content
    """
    prompt = base_prompt

    # Inject current date and time
    now = datetime.now()
    timestamp_info = (
        f"\n\nCurrent date and time: {now.strftime('%Y-%m-%d %H:%M:%S %A')}"
    )
    prompt = prompt + timestamp_info

    # Optionally inject user settings summary
    if not user_settings.audio_enabled:
        prompt = prompt + "\n\nUser settings:\n- Audio responses disabled (text only)"

    return prompt


class PromptManager:
    """Manages system prompt loading and caching."""

    def __init__(self, prompt_file: str | None = None):
        """
        Initialize prompt manager.

        Args:
            prompt_file: Path to prompt file
        """
        self.prompt_file = prompt_file
        self._base_prompt: str | None = None

    @property
    def base_prompt(self) -> str:
        """Get base prompt, loading from file if needed."""
        if self._base_prompt is None:
            self._base_prompt = load_system_prompt(self.prompt_file)
        return self._base_prompt

    def reload(self) -> None:
        """Force reload of prompt from file."""
        self._base_prompt = None

    def get_prompt(self, user_settings: UserSettings) -> str:
        """
        Get complete prompt with dynamic content.

        Args:
            user_settings: User settings

        Returns:
            Complete system prompt
        """
        return build_dynamic_prompt(self.base_prompt, user_settings)


# Default instance
_prompt_manager: PromptManager | None = None
_prompt_manager_lock = Lock()


def get_prompt_manager() -> PromptManager:
    """Get or create the default prompt manager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        with _prompt_manager_lock:
            if _prompt_manager is None:
                _prompt_manager = PromptManager()
    return _prompt_manager


def set_prompt_manager(manager: PromptManager) -> None:
    """Set the default prompt manager instance (for testing)."""
    global _prompt_manager
    _prompt_manager = manager
