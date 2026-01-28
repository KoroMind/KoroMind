"""Session management business logic.

This module provides a higher-level interface for session management,
wrapping the storage layer with additional business rules.
"""

from datetime import datetime, timedelta

from koro.core.state import StateManager, get_state_manager
from koro.core.types import Session


class SessionManager:
    """High-level session management with business rules."""

    def __init__(
        self,
        state_manager: StateManager | None = None,
        session_timeout_hours: int = 24,
    ):
        """
        Initialize session manager.

        Args:
            state_manager: StateManager instance (defaults to global)
            session_timeout_hours: Hours after which a session is considered stale
        """
        self._state_manager = state_manager
        self.session_timeout = timedelta(hours=session_timeout_hours)

    @property
    def state_manager(self) -> StateManager:
        """Get state manager, using default if not injected."""
        if self._state_manager is None:
            self._state_manager = get_state_manager()
        return self._state_manager

    async def get_or_create_session(self, user_id: str) -> Session:
        """
        Get current session or create a new one.

        Args:
            user_id: User identifier

        Returns:
            Current or new session
        """
        current = await self.state_manager.get_current_session(user_id)

        if current:
            # Check if session is stale
            if self._is_session_stale(current):
                # Create new session for stale sessions
                return await self.state_manager.create_session(user_id)
            return current

        return await self.state_manager.create_session(user_id)

    async def ensure_session(self, user_id: str, session_id: str | None) -> str:
        """
        Ensure a valid session exists for processing.

        Args:
            user_id: User identifier
            session_id: Optional session ID

        Returns:
            Valid session ID to use
        """
        if session_id:
            # Verify session exists
            sessions = await self.state_manager.get_sessions(user_id)
            if any(s.id == session_id for s in sessions):
                return session_id

        # Get or create session
        session = await self.get_or_create_session(user_id)
        return session.id

    async def switch_session(
        self,
        user_id: str,
        session_id: str,
    ) -> Session | None:
        """
        Switch to a different session.

        Args:
            user_id: User identifier
            session_id: Session ID to switch to

        Returns:
            Session if found and switched, None otherwise
        """
        sessions = await self.state_manager.get_sessions(user_id)
        target = next((s for s in sessions if s.id == session_id), None)

        if target:
            await self.state_manager.set_current_session(user_id, session_id)
            return target

        return None

    async def list_sessions(
        self,
        user_id: str,
        include_stale: bool = False,
    ) -> list[Session]:
        """
        List sessions for a user.

        Args:
            user_id: User identifier
            include_stale: Whether to include stale sessions

        Returns:
            List of sessions
        """
        sessions = await self.state_manager.get_sessions(user_id)

        if include_stale:
            return sessions

        return [s for s in sessions if not self._is_session_stale(s)]

    async def clear_session(self, user_id: str) -> None:
        """
        Clear the current session (start fresh next time).

        Args:
            user_id: User identifier
        """
        await self.state_manager.clear_current_session(user_id)

    def _is_session_stale(self, session: Session) -> bool:
        """Check if a session is stale based on timeout."""
        now = datetime.now()
        return (now - session.last_active) > self.session_timeout


# Default instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get or create the default session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def set_session_manager(manager: SessionManager) -> None:
    """Set the default session manager instance (for testing)."""
    global _session_manager
    _session_manager = manager
