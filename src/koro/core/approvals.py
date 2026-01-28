"""Approval tracking for tool calls in APPROVE mode.

This module manages pending tool approvals and callbacks for human-in-the-loop
tool execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from uuid import uuid4


class ApprovalStatus(Enum):
    """Status of a pending approval."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"


@dataclass
class PendingApproval:
    """A pending tool approval request."""

    id: str
    tool_name: str
    tool_input: dict
    context: Any
    created_at: datetime
    status: ApprovalStatus = ApprovalStatus.PENDING
    resolved_at: datetime | None = None
    resolved_by: str | None = None


@dataclass
class ApprovalTracker:
    """Tracks pending tool approvals for a session."""

    pending: dict[str, PendingApproval] = field(default_factory=dict)
    history: list[PendingApproval] = field(default_factory=list)

    def add_pending(
        self,
        tool_name: str,
        tool_input: dict,
        context: Any,
    ) -> PendingApproval:
        """Add a new pending approval."""
        approval = PendingApproval(
            id=str(uuid4()),
            tool_name=tool_name,
            tool_input=tool_input,
            context=context,
            created_at=datetime.now(),
        )
        self.pending[approval.id] = approval
        return approval

    def resolve(
        self,
        approval_id: str,
        status: ApprovalStatus,
        resolved_by: str | None = None,
    ) -> PendingApproval | None:
        """Resolve a pending approval."""
        approval = self.pending.pop(approval_id, None)
        if approval:
            approval.status = status
            approval.resolved_at = datetime.now()
            approval.resolved_by = resolved_by
            self.history.append(approval)
        return approval

    def get_pending(self, approval_id: str) -> PendingApproval | None:
        """Get a pending approval by ID."""
        return self.pending.get(approval_id)

    def get_all_pending(self) -> list[PendingApproval]:
        """Get all pending approvals."""
        return list(self.pending.values())

    def clear_pending(self) -> int:
        """Clear all pending approvals (mark as timeout)."""
        count = len(self.pending)
        for approval_id in list(self.pending.keys()):
            self.resolve(approval_id, ApprovalStatus.TIMEOUT)
        return count


class ApprovalManager:
    """Manages approval trackers across sessions."""

    def __init__(self):
        """Initialize approval manager."""
        self.trackers: dict[str, ApprovalTracker] = {}

    def get_tracker(self, session_id: str) -> ApprovalTracker:
        """Get or create a tracker for a session."""
        if session_id not in self.trackers:
            self.trackers[session_id] = ApprovalTracker()
        return self.trackers[session_id]

    def remove_tracker(self, session_id: str) -> None:
        """Remove a tracker for a session."""
        self.trackers.pop(session_id, None)

    def create_callback(
        self,
        session_id: str,
        notify_callback: Callable[[PendingApproval], None] | None = None,
    ) -> Callable[[str, dict, Any], Any]:
        """
        Create a can_use_tool callback that tracks approvals.

        Args:
            session_id: Session ID for tracking
            notify_callback: Optional callback to notify about pending approvals

        Returns:
            Callback function for Claude SDK
        """
        tracker = self.get_tracker(session_id)

        def can_use_tool(tool_name: str, tool_input: dict, context: Any) -> Any:
            approval = tracker.add_pending(tool_name, tool_input, context)

            if notify_callback:
                notify_callback(approval)

            # Return the approval object - caller must resolve it
            return approval

        return can_use_tool


# Global approval manager
_approval_manager: ApprovalManager | None = None


def get_approval_manager() -> ApprovalManager:
    """Get or create the global approval manager."""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    return _approval_manager


def set_approval_manager(manager: ApprovalManager) -> None:
    """Set the global approval manager (for testing)."""
    global _approval_manager
    _approval_manager = manager
