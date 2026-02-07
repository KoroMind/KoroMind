"""API middleware for authentication and rate limiting."""

import hashlib
import logging
import secrets
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from koro.core.config import KOROMIND_ALLOW_NO_AUTH, KOROMIND_API_KEY
from koro.core.rate_limit import get_rate_limiter

logger = logging.getLogger(__name__)

# Paths that don't require authentication
PUBLIC_PATHS = {"/api/v1/health", "/docs", "/openapi.json", "/redoc"}


def _derive_user_id(api_key: str | None) -> str:
    if not api_key:
        return "anonymous"
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


async def api_key_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Middleware to validate API key authentication.

    Checks the X-API-Key header against KOROMIND_API_KEY.
    Public paths are exempt from authentication.
    """
    path = request.url.path

    # Allow public paths without authentication
    if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
        response = await call_next(request)
        return response

    # If no API key is configured, fail closed unless explicitly allowed
    if not KOROMIND_API_KEY:
        if not KOROMIND_ALLOW_NO_AUTH:
            logger.error("KOROMIND_API_KEY not set - refusing unauthenticated access")
            return JSONResponse(
                status_code=503,
                content={"detail": "API key not configured"},
            )
        request.state.user_id = "local"
        logger.warning(
            "KOROMIND_API_KEY not set - API is running without authentication"
        )
        response = await call_next(request)
        return response

    # Check API key header
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"detail": "Missing X-API-Key header"},
        )

    if not secrets.compare_digest(api_key, KOROMIND_API_KEY):
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid API key"},
        )

    request.state.user_id = _derive_user_id(api_key)
    response = await call_next(request)
    return response


async def rate_limit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    Middleware to apply rate limiting per user.

    User is identified by authenticated API key.
    """
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
        response = await call_next(request)
        return response

    user_id = getattr(request.state, "user_id", None) or _derive_user_id(
        request.headers.get("X-API-Key")
    )

    rate_limiter = get_rate_limiter()
    allowed, message = rate_limiter.check(user_id)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": message},
        )

    response = await call_next(request)
    return response
