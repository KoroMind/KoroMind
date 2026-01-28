"""System prompt loading and building.

This module re-exports from koro.core.prompt for backward compatibility.
New code should import directly from koro.core.prompt.
"""

# Re-export everything from core prompt
from koro.core.prompt import (
    PromptManager,
    build_dynamic_prompt,
    get_prompt_manager,
    load_system_prompt,
    set_prompt_manager,
)

__all__ = [
    "PromptManager",
    "build_dynamic_prompt",
    "get_prompt_manager",
    "load_system_prompt",
    "set_prompt_manager",
]
