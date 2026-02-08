"""The Brain - central orchestration layer for KoroMind."""

import asyncio
import inspect
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from threading import Lock
from typing import Any, NamedTuple

from claude_agent_sdk.types import (
    AgentDefinition,
    AssistantMessage,
    HookCallback,
    HookMatcher,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    UserMessage,
)

from koro.core.claude import ClaudeClient, get_claude_client
from koro.core.rate_limit import RateLimiter, get_rate_limiter
from koro.core.state import StateManager, get_state_manager
from koro.core.types import (
    BrainCallbacks,
    BrainResponse,
    CanUseTool,
    MessageType,
    Mode,
    OnProgress,
    OnToolCall,
    QueryConfig,
    Session,
    ToolCall,
    UserSettings,
)
from koro.core.vault import AgentConfig, Vault, VaultConfig, VaultHookRule
from koro.core.voice import VoiceEngine, VoiceError, get_voice_engine

logger = logging.getLogger(__name__)

StreamedEvent = (
    AssistantMessage | ResultMessage | StreamEvent | UserMessage | SystemMessage
)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _make_command_hook(command: str) -> HookCallback:
    """Create an SDK HookCallback that executes a shell command.

    The hook passes HookInput as JSON on stdin and parses
    HookJSONOutput from stdout.
    """

    async def _run(hook_input: Any, tool_use_id: str | None, ctx: Any) -> Any:
        input_data = json.dumps({"hook_input": hook_input, "tool_use_id": tool_use_id})
        proc = await asyncio.create_subprocess_shell(
            command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input_data.encode())
        if proc.returncode != 0:
            logger.warning(
                f"Hook command failed (exit {proc.returncode}): {stderr.decode()}"
            )
            return {"continue_": True}
        if stdout.strip():
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                logger.warning(f"Hook returned invalid JSON: {stdout.decode()[:200]}")
        return {"continue_": True}

    return _run


def _vault_hooks_to_sdk(
    vault_hooks: dict[str, list[VaultHookRule]],
) -> dict[str, list[HookMatcher]]:
    """Convert vault command-based hooks to SDK callable hooks."""
    sdk_hooks: dict[str, list[HookMatcher]] = {}
    for event_name, rules in vault_hooks.items():
        sdk_matchers = []
        for rule in rules:
            callbacks = [_make_command_hook(h.command) for h in rule.hooks]
            sdk_matchers.append(HookMatcher(matcher=rule.matcher, hooks=callbacks))
        sdk_hooks[event_name] = sdk_matchers
    return sdk_hooks


class _RequestContext(NamedTuple):
    """Internal: resolved context for a Brain request."""

    text: str
    session_id: str | None
    stored_settings: UserSettings
    vault_config: VaultConfig | None
    model_override: str | None


class Brain:
    """The second brain - central orchestration layer for KoroMind."""

    def __init__(
        self,
        vault_path: Path | str | None = None,
        state_manager: StateManager | None = None,
        claude_client: ClaudeClient | None = None,
        voice_engine: VoiceEngine | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        """
        Initialize the brain with optional dependency injection.

        Args:
            vault_path: Path to vault directory containing vault-config.yaml.
                If provided, configuration is loaded and passed to Claude SDK.
            state_manager: State manager instance (defaults to global)
            claude_client: Claude client instance (defaults to global)
            voice_engine: Voice engine instance (defaults to global)
            rate_limiter: Rate limiter instance (defaults to global)
        """
        self._vault = Vault(vault_path) if vault_path else None
        self._state_manager = state_manager
        self._claude_client = claude_client
        self._voice_engine = voice_engine
        self._rate_limiter = rate_limiter

        if self._vault:
            logger.debug(f"Brain initialized with vault: {vault_path}")
        else:
            logger.warning(
                "Brain initialized without vault. "
                "Consider using --vault or setting KOROMIND_VAULT for configuration."
            )

    @property
    def vault(self) -> Vault | None:
        """Get vault instance if configured."""
        return self._vault

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

    async def interrupt(self) -> bool:
        """
        Interrupt the currently active request.

        Returns:
            True if interrupt was sent, False otherwise
        """
        return await self.claude_client.interrupt()

    async def _resolve_request_context(
        self,
        *,
        user_id: str,
        content: str | bytes,
        content_type: MessageType,
        session_id: str | None,
        kwargs: dict[str, Any],
        progress_callback: OnProgress | None = None,
    ) -> _RequestContext:
        """Resolve common request context: transcription, session, settings, vault.

        Note: Pops 'model' from kwargs if present (consumed for model_override).
        """
        # Transcribe voice if needed
        if content_type == MessageType.VOICE:
            if not isinstance(content, bytes):
                raise ValueError("Voice content must be bytes")
            if progress_callback:
                progress_callback("Transcribing voice input...")
            try:
                text = await self.voice_engine.transcribe(content)
            except VoiceError as exc:
                raise RuntimeError(str(exc)) from exc
        else:
            text = content if isinstance(content, str) else content.decode("utf-8")

        # Get current session if not provided
        if session_id is None:
            current_session = await self.state_manager.get_current_session(user_id)
            session_id = current_session.id if current_session else None

        # Fetch stored settings
        stored_settings = await _maybe_await(self.state_manager.get_settings(user_id))
        if not isinstance(stored_settings, UserSettings):
            stored_settings = UserSettings()

        # Resolve model override (pops from kwargs)
        if "model" in kwargs:
            model_override: str | None = kwargs.pop("model") or None
        else:
            model_override = stored_settings.model or None

        # Load vault config if available
        vault_config = self._vault.load() if self._vault else None

        return _RequestContext(
            text=text,
            session_id=session_id,
            stored_settings=stored_settings,
            vault_config=vault_config,
            model_override=model_override,
        )

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
        on_tool_call: OnToolCall | None = None,
        can_use_tool: CanUseTool | None = None,
        callbacks: BrainCallbacks | None = None,
        **kwargs: Any,
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
            can_use_tool: SDK-compatible callback for tool approval (for approve mode)
            callbacks: Structured callbacks (preferred over individual params)
            **kwargs: Additional arguments passed to ClaudeClient.query
                (hooks, mcp_servers, agents, plugins, sandbox, output_format, etc.)

        Returns:
            BrainResponse with text, optional audio, and metadata
        """
        tool_calls: list[ToolCall] = []

        # Prefer structured callbacks over individual params
        tool_use_callback = callbacks.on_tool_use if callbacks else on_tool_call
        tool_approval_callback = (
            callbacks.on_tool_approval if callbacks else can_use_tool
        )
        progress_callback = callbacks.on_progress if callbacks else None

        ctx = await self._resolve_request_context(
            user_id=user_id,
            content=content,
            content_type=content_type,
            session_id=session_id,
            kwargs=kwargs,
            progress_callback=progress_callback,
        )

        user_settings = UserSettings(
            mode=mode,
            audio_enabled=include_audio,
            voice_speed=voice_speed,
            watch_enabled=watch_enabled,
            model=ctx.stored_settings.model,
        )

        # Tool call tracking wrapper
        async def _on_tool_call(tool_name: str, detail: str | None) -> None:
            tool_calls.append(ToolCall(name=tool_name, detail=detail))
            if tool_use_callback and watch_enabled:
                await tool_use_callback(tool_name, detail)

        config = self._build_query_config(
            prompt=ctx.text,
            session_id=ctx.session_id,
            continue_last=False,
            user_settings=user_settings,
            mode=mode,
            on_tool_call=_on_tool_call if watch_enabled else None,
            can_use_tool=tool_approval_callback if mode == Mode.APPROVE else None,
            vault_config=ctx.vault_config,
            model=ctx.model_override,
            **kwargs,
        )

        # Call Claude
        if progress_callback:
            progress_callback("Processing with Claude SDK...")
        response_text, new_session_id, metadata = await self.claude_client.query(config)

        # Update session state only on successful Claude responses
        if not metadata.get("error"):
            await self.state_manager.update_session(user_id, new_session_id)

        # Generate TTS if requested
        audio_bytes: bytes | None = None
        if include_audio:
            if progress_callback:
                progress_callback("Generating voice response...")
            # Note: We only TTS the main text response, not structured output or thinking
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

    @staticmethod
    def _vault_agents_to_sdk(
        agents: dict[str, AgentConfig],
    ) -> dict[str, AgentDefinition]:
        """Convert vault AgentConfig to SDK AgentDefinition."""
        result = {}
        for name, agent in agents.items():
            prompt = agent.prompt or ""
            if agent.prompt_file:
                path = Path(agent.prompt_file)
                if path.exists():
                    prompt = path.read_text()
                else:
                    logger.warning(f"Agent prompt file not found: {agent.prompt_file}")
            result[name] = AgentDefinition(
                description=agent.description,
                prompt=prompt,
                tools=agent.tools,
                model=agent.model,
            )
        return result

    def _build_query_config(
        self,
        *,
        prompt: str,
        session_id: str | None,
        continue_last: bool,
        user_settings: UserSettings,
        mode: Mode,
        on_tool_call: OnToolCall | None,
        can_use_tool: CanUseTool | None,
        vault_config: VaultConfig | None = None,
        **kwargs: Any,
    ) -> QueryConfig:
        config_kwargs: dict[str, Any] = {
            "prompt": prompt,
            "session_id": session_id,
            "continue_last": continue_last,
            "user_settings": user_settings,
            "mode": mode,
            "on_tool_call": on_tool_call,
            "can_use_tool": can_use_tool,
        }

        # Apply vault config (if provided)
        if vault_config:
            vault_data = vault_config.model_dump(
                exclude_none=True,
                exclude_defaults=True,
                include={"mcp_servers", "sandbox", "plugins"},
            )
            config_kwargs.update(vault_data)
            if vault_config.hooks:
                config_kwargs["hooks"] = _vault_hooks_to_sdk(vault_config.hooks)
            if vault_config.agents:
                config_kwargs["agents"] = self._vault_agents_to_sdk(vault_config.agents)
            logger.debug(
                f"Applied vault config: hooks={len(vault_config.hooks)}, "
                f"mcp_servers={len(vault_config.mcp_servers)}, "
                f"agents={len(vault_config.agents)}"
            )

        # Allowed kwargs (can override vault config)
        allowed_keys = {
            # Core SDK options (from env vars or explicit kwargs)
            "model",
            "fallback_model",
            "max_turns",
            "max_budget_usd",
            "cwd",
            "add_dirs",
            "system_prompt_file",
            "include_partial_messages",
            "enable_file_checkpointing",
            "output_format",
            "include_megg",
            # Vault config options (explicit kwargs override vault)
            "hooks",
            "mcp_servers",
            "agents",
            "plugins",
            "sandbox",
        }

        # Explicit kwargs override vault config
        for key in list(kwargs.keys()):
            if key in allowed_keys:
                config_kwargs[key] = kwargs.pop(key)

        if kwargs:
            unknown = ", ".join(sorted(kwargs.keys()))
            raise ValueError(f"Unsupported query options: {unknown}")

        return QueryConfig(**config_kwargs)

    async def process_message_stream(
        self,
        user_id: str,
        content: str | bytes,
        content_type: MessageType,
        session_id: str | None = None,
        mode: Mode = Mode.GO_ALL,
        watch_enabled: bool = False,
        on_tool_call: OnToolCall | None = None,
        can_use_tool: CanUseTool | None = None,
        callbacks: BrainCallbacks | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamedEvent]:
        """
        Process a message and yield streaming events.

        Unlike process_message() which waits for completion and returns
        a BrainResponse, this method yields events as they arrive from
        the Claude SDK. Use this for real-time streaming UIs (CLI, web).

        Args:
            Same as process_message, but returns an async iterator of events.
        """
        # Prefer structured callbacks over individual params
        tool_use_callback = callbacks.on_tool_use if callbacks else on_tool_call
        tool_approval_callback = (
            callbacks.on_tool_approval if callbacks else can_use_tool
        )

        ctx = await self._resolve_request_context(
            user_id=user_id,
            content=content,
            content_type=content_type,
            session_id=session_id,
            kwargs=kwargs,
        )

        user_settings = UserSettings(
            mode=mode,
            watch_enabled=watch_enabled,
            model=ctx.stored_settings.model,
        )

        # Wrap callback in async to match SDK expectations (like process_message does)
        async def _on_tool_call(tool_name: str, detail: str | None) -> None:
            if tool_use_callback:
                await _maybe_await(tool_use_callback(tool_name, detail))

        config = self._build_query_config(
            prompt=ctx.text,
            session_id=ctx.session_id,
            continue_last=False,
            user_settings=user_settings,
            mode=mode,
            on_tool_call=_on_tool_call if watch_enabled else None,
            can_use_tool=tool_approval_callback if mode == Mode.APPROVE else None,
            vault_config=ctx.vault_config,
            model=ctx.model_override,
            **kwargs,
        )

        # Yield events from Claude
        resolved_session_id = ctx.session_id
        async for event in self.claude_client.query_stream(config):
            yield event

            if isinstance(event, ResultMessage) and event.session_id:
                if event.session_id != resolved_session_id:
                    await self.state_manager.update_session(user_id, event.session_id)
                    resolved_session_id = event.session_id

    async def process_text(
        self,
        user_id: str,
        text: str,
        session_id: str | None = None,
        mode: Mode = Mode.GO_ALL,
        include_audio: bool = True,
        voice_speed: float = 1.1,
        **kwargs: Any,
    ) -> BrainResponse:
        """
        Process a text message (convenience method).
        """
        return await self.process_message(
            user_id=user_id,
            content=text,
            content_type=MessageType.TEXT,
            session_id=session_id,
            mode=mode,
            include_audio=include_audio,
            voice_speed=voice_speed,
            **kwargs,
        )

    async def process_voice(
        self,
        user_id: str,
        voice_bytes: bytes,
        session_id: str | None = None,
        mode: Mode = Mode.GO_ALL,
        include_audio: bool = True,
        voice_speed: float = 1.1,
        **kwargs: Any,
    ) -> BrainResponse:
        """
        Process a voice message (convenience method).
        """
        return await self.process_message(
            user_id=user_id,
            content=voice_bytes,
            content_type=MessageType.VOICE,
            session_id=session_id,
            mode=mode,
            include_audio=include_audio,
            voice_speed=voice_speed,
            **kwargs,
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

    async def update_settings(self, user_id: str, **kwargs: object) -> UserSettings:
        """Update settings for a user."""
        return await self.state_manager.update_settings(user_id, **kwargs)

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
_brain_lock = Lock()


def get_brain() -> Brain:
    """Get or create the default brain instance."""
    global _brain
    if _brain is None:
        with _brain_lock:
            if _brain is None:
                _brain = Brain()
    return _brain


def set_brain(brain: Brain) -> None:
    """Set the default brain instance (for testing)."""
    global _brain
    _brain = brain
