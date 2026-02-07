"""Health check endpoints."""

from typing import Any

from fastapi import APIRouter

from koro.core.brain import get_brain

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Check the health of all KoroMind components.

    Returns:
        dict with status and component health details
    """
    brain = get_brain()
    health_status = brain.health_check()

    # Determine overall status
    all_healthy = all(status[0] for status in health_status.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "components": {
            name: {"healthy": status[0], "message": status[1]}
            for name, status in health_status.items()
        },
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """
    Kubernetes-style liveness probe.

    Returns:
        Simple OK response if the service is running
    """
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """
    Kubernetes-style readiness probe.

    Returns:
        OK if the service is ready to accept traffic
    """
    brain = get_brain()
    health_status = brain.health_check()

    # Check if Claude is healthy (critical dependency)
    claude_healthy = health_status.get("claude", (False, ""))[0]

    if claude_healthy:
        return {"status": "ok", "ready": True}

    return {
        "status": "not_ready",
        "ready": False,
        "reason": "Claude service unavailable",
    }
