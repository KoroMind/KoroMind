"""The Brain - central orchestration layer for KoroMind."""

from typing import Any, Callable

from koro.core.claude import ClaudeClient, get_claude_client
from koro.core.rate_limit import RateLimiter, get_rate_limiter
from koro.core.state import StateManager, get_state_manager
from koro.core.types import (
    BrainResponse,
    MessageType,
    Mode,
    SDKConfig,
    Session,
    ToolCall,
    UserSettings,
)
from koro.core.voice import VoiceEngine, get_voice_engine


class Brain:
    """The second brain - central orchestration layer for KoroMind."""

    def __init__(
        self,
        state_manager: StateManager | None = None,
        claude_client: ClaudeClient | None = None,
        voice_engine: VoiceEngine | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        """
        Initialize the brain with optional dependency injection.

        Args:
            state_manager: State manager instance (defaults to global)
            claude_client: Claude client instance (defaults to global)
            voice_engine: Voice engine instance (defaults to global)
            rate_limiter: Rate limiter instance (defaults to global)
        """
        self._state_manager = state_manager
        self._claude_client = claude_client
        self._voice_engine = voice_engine
        self._rate_limiter = rate_limiter

    @property
    def state_manager(self) -> StateManager:
        """Get state manager, using default if not injected."""
        if self._state_manager is None:
            self._state_manager = get_state_manager()
        return self._state_manager

    @property
    def claude_client(self) -> ClaudeClient:
        """Get Claude client, using default if not injected."""
        if self._claude_client is None:
            self._claude_client = get_claude_client()
        return self._claude_client

    @property
    def voice_engine(self) -> VoiceEngine:
        """Get voice engine, using default if not injected."""
        if self._voice_engine is None:
            self._voice_engine = get_voice_engine()
        return self._voice_engine

    @property
    def rate_limiter(self) -> RateLimiter:
        """Get rate limiter, using default if not injected."""
        if self._rate_limiter is None:
            self._rate_limiter = get_rate_limiter()
        return self._rate_limiter

    async def process_message(
        self,
        user_id: str,
        content: str | bytes,
        content_type: MessageType,
        session_id: str | None = None,
        mode: Mode = Mode.GO_ALL,
        include_audio: bool = True,
        voice_speed: float = 1.1,
        watch_enabled: bool = False,
        on_tool_call: Callable[[str, str | None], None] | None = None,
        can_use_tool: Callable[[str, dict, Any], Any] | None = None,
    ) -> BrainResponse:
        """
        Process a message and return response.

        Args:
            user_id: Unique identifier for the user
            content: Message content (text string or voice bytes)
            content_type: Type of message (TEXT or VOICE)
            session_id: Optional session ID to continue
            mode: Execution mode (GO_ALL or APPROVE)
            include_audio: Whether to include TTS audio in response
            voice_speed: Voice speed for TTS (0.7-1.2)
            watch_enabled: Whether to call on_tool_call for each tool
            on_tool_call: Callback when tool is called (for watch mode)
            can_use_tool: Callback for tool approval (for approve mode)

        Returns:
            BrainResponse with text, optional audio, and metadata
        """
        tool_calls: list[ToolCall] = []

        # Transcribe voice if needed
        if content_type == MessageType.VOICE:
            if not isinstance(content, bytes):
                return BrainResponse(
                    text="Error: Voice content must be bytes",
                    session_id=session_id or "",
                )
            text = await self.voice_engine.transcribe(content)
            if text.startswith("[Transcription error") or text.startswith("[Error"):
                return BrainResponse(
                    text=text,
                    session_id=session_id or "",
                )
        else:
            text = content if isinstance(content, str) else content.decode("utf-8")

        # Get current session if not provided
        if session_id is None:
            current_session = await self.state_manager.get_current_session(user_id)
            session_id = current_session.id if current_session else None

        # Determine if we're continuing a session
        continue_last = session_id is not None

        # Build user settings dict for Claude
        user_settings = {
            "audio_enabled": include_audio,
            "voice_speed": voice_speed,
            "mode": mode.value,
            "watch_enabled": watch_enabled,
        }

        # Load SDK config from Vault
        sdk_config = await self.state_manager.get_sdk_config(user_id)

        # Tool call tracking wrapper
        def _on_tool_call(tool_name: str, detail: str | None):
            tool_calls.append(ToolCall(name=tool_name, detail=detail))
            if on_tool_call and watch_enabled:
                on_tool_call(tool_name, detail)

        # Call Claude with SDK config from Vault
        response_text, new_session_id, metadata = await self.claude_client.query(
            prompt=text,
            session_id=session_id,
            continue_last=continue_last,
            user_settings=user_settings,
            mode=mode.value,
            on_tool_call=_on_tool_call if watch_enabled else None,
            can_use_tool=can_use_tool if mode == Mode.APPROVE else None,
            sdk_config=sdk_config,
        )

        # Update session state
        await self.state_manager.update_session(user_id, new_session_id)

        # Generate TTS if requested
        audio_bytes: bytes | None = None
        if include_audio:
            audio_buffer = await self.voice_engine.text_to_speech(
                response_text, speed=voice_speed
            )
            if audio_buffer:
                audio_bytes = audio_buffer.read()

        return BrainResponse(
            text=response_text,
            session_id=new_session_id or "",
            audio=audio_bytes,
            tool_calls=tool_calls,
            metadata=metadata,
        )

    async def process_text(
        self,
        user_id: str,
        text: str,
        session_id: str | None = None,
        mode: Mode = Mode.GO_ALL,
        include_audio: bool = True,
        voice_speed: float = 1.1,
    ) -> BrainResponse:
        """
        Process a text message (convenience method).

        Args:
            user_id: Unique identifier for the user
            text: Text message content
            session_id: Optional session ID to continue
            mode: Execution mode (GO_ALL or APPROVE)
            include_audio: Whether to include TTS audio in response
            voice_speed: Voice speed for TTS

        Returns:
            BrainResponse with text, optional audio, and metadata
        """
        return await self.process_message(
            user_id=user_id,
            content=text,
            content_type=MessageType.TEXT,
            session_id=session_id,
            mode=mode,
            include_audio=include_audio,
            voice_speed=voice_speed,
        )

    async def process_voice(
        self,
        user_id: str,
        voice_bytes: bytes,
        session_id: str | None = None,
        mode: Mode = Mode.GO_ALL,
        include_audio: bool = True,
        voice_speed: float = 1.1,
    ) -> BrainResponse:
        """
        Process a voice message (convenience method).

        Args:
            user_id: Unique identifier for the user
            voice_bytes: Voice audio bytes
            session_id: Optional session ID to continue
            mode: Execution mode (GO_ALL or APPROVE)
            include_audio: Whether to include TTS audio in response
            voice_speed: Voice speed for TTS

        Returns:
            BrainResponse with text, optional audio, and metadata
        """
        return await self.process_message(
            user_id=user_id,
            content=voice_bytes,
            content_type=MessageType.VOICE,
            session_id=session_id,
            mode=mode,
            include_audio=include_audio,
            voice_speed=voice_speed,
        )

    # Session Management

    async def get_sessions(self, user_id: str) -> list[Session]:
        """Get all sessions for a user."""
        return await self.state_manager.get_sessions(user_id)

    async def create_session(self, user_id: str) -> Session:
        """Create a new session for a user."""
        return await self.state_manager.create_session(user_id)

    async def get_current_session(self, user_id: str) -> Session | None:
        """Get the current session for a user."""
        return await self.state_manager.get_current_session(user_id)

    async def switch_session(self, user_id: str, session_id: str) -> None:
        """Switch to a different session."""
        await self.state_manager.set_current_session(user_id, session_id)

    # Settings Management

    async def get_settings(self, user_id: str) -> UserSettings:
        """Get settings for a user."""
        return await self.state_manager.get_settings(user_id)

    async def update_settings(self, user_id: str, **kwargs) -> UserSettings:
        """Update settings for a user."""
        return await self.state_manager.update_settings(user_id, **kwargs)

    # SDK Config Management

    async def get_sdk_config(self, user_id: str) -> SDKConfig:
        """Get SDK config for a user."""
        return await self.state_manager.get_sdk_config(user_id)

    async def update_sdk_config(self, user_id: str, **kwargs) -> SDKConfig:
        """Update SDK config for a user."""
        return await self.state_manager.update_sdk_config(user_id, **kwargs)

    async def add_mcp_server(self, user_id: str, server: dict) -> None:
        """Add an MCP server to user's config."""
        await self.state_manager.add_mcp_server(user_id, server)

    async def remove_mcp_server(self, user_id: str, name: str) -> bool:
        """Remove an MCP server from user's config."""
        return await self.state_manager.remove_mcp_server(user_id, name)

    async def list_mcp_servers(self, user_id: str) -> list[dict]:
        """List MCP servers for a user."""
        return await self.state_manager.get_mcp_servers(user_id)

    async def add_agent(self, user_id: str, name: str, definition: dict) -> None:
        """Add a custom agent for a user."""
        await self.state_manager.add_agent(user_id, name, definition)

    async def remove_agent(self, user_id: str, name: str) -> bool:
        """Remove a custom agent from user's config."""
        return await self.state_manager.remove_agent(user_id, name)

    async def list_agents(self, user_id: str) -> dict[str, dict]:
        """List custom agents for a user."""
        return await self.state_manager.get_agents(user_id)

    # Rate Limiting

    def check_rate_limit(self, user_id: str) -> tuple[bool, str]:
        """
        Check if user is within rate limits.

        Args:
            user_id: User identifier

        Returns:
            (allowed, message) - If not allowed, message explains why
        """
        return self.rate_limiter.check(user_id)

    # Health Checks

    def health_check(self) -> dict[str, tuple[bool, str]]:
        """
        Check health of all components.

        Returns:
            Dict mapping component name to (healthy, message)
        """
        return {
            "claude": self.claude_client.health_check(),
            "voice": self.voice_engine.health_check(),
        }


# Default instance
_brain: Brain | None = None


def get_brain() -> Brain:
    """Get or create the default brain instance."""
    global _brain
    if _brain is None:
        _brain = Brain()
    return _brain


def set_brain(brain: Brain) -> None:
    """Set the default brain instance (for testing)."""
    global _brain
    _brain = brain
