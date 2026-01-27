"""Session management endpoints."""

from datetime import datetime

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from koro.core.brain import get_brain

router = APIRouter()


class SessionResponse(BaseModel):
    """Response model for a session."""

    id: str
    user_id: str
    created_at: datetime
    last_active: datetime


class SessionListResponse(BaseModel):
    """Response model for list of sessions."""

    sessions: list[SessionResponse]
    current_session_id: str | None


class SwitchSessionRequest(BaseModel):
    """Request to switch to a different session."""

    session_id: str = Field(..., description="Session ID to switch to")


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    x_user_id: str = Header(..., description="User identifier"),
) -> SessionListResponse:
    """
    List all sessions for the user.

    Sessions are ordered by last_active descending.
    """
    brain = get_brain()

    sessions = await brain.get_sessions(x_user_id)
    current = await brain.get_current_session(x_user_id)

    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                user_id=s.user_id,
                created_at=s.created_at,
                last_active=s.last_active,
            )
            for s in sessions
        ],
        current_session_id=current.id if current else None,
    )


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    x_user_id: str = Header(..., description="User identifier"),
) -> SessionResponse:
    """
    Create a new session and set it as current.

    Returns the newly created session.
    """
    brain = get_brain()

    session = await brain.create_session(x_user_id)

    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        created_at=session.created_at,
        last_active=session.last_active,
    )


@router.get("/sessions/current", response_model=SessionResponse | None)
async def get_current_session(
    x_user_id: str = Header(..., description="User identifier"),
) -> SessionResponse | None:
    """
    Get the current session for the user.

    Returns null if no current session exists.
    """
    brain = get_brain()

    session = await brain.get_current_session(x_user_id)

    if session is None:
        return None

    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        created_at=session.created_at,
        last_active=session.last_active,
    )


@router.put("/sessions/current")
async def switch_session(
    request: SwitchSessionRequest,
    x_user_id: str = Header(..., description="User identifier"),
) -> dict:
    """
    Switch to a different session.

    The session must belong to the user.
    """
    brain = get_brain()

    # Verify the session exists for this user
    sessions = await brain.get_sessions(x_user_id)
    session_ids = {s.id for s in sessions}

    if request.session_id not in session_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Session {request.session_id} not found for user",
        )

    await brain.switch_session(x_user_id, request.session_id)

    return {"status": "ok", "current_session_id": request.session_id}
