"""API middleware for authentication and rate limiting."""

import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from koro.core.config import KOROMIND_API_KEY
from koro.core.rate_limit import get_rate_limiter

logger = logging.getLogger(__name__)

# Paths that don't require authentication
PUBLIC_PATHS = {"/api/v1/health", "/docs", "/openapi.json", "/redoc"}


async def api_key_middleware(request: Request, call_next) -> Response:
    """
    Middleware to validate API key authentication.

    Checks the X-API-Key header against KOROMIND_API_KEY.
    Public paths are exempt from authentication.
    """
    path = request.url.path

    # Allow public paths without authentication
    if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
        return await call_next(request)

    # If no API key is configured, allow all requests (development mode)
    if not KOROMIND_API_KEY:
        logger.warning(
            "KOROMIND_API_KEY not set - API is running without authentication"
        )
        return await call_next(request)

    # Check API key header
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"detail": "Missing X-API-Key header"},
        )

    if api_key != KOROMIND_API_KEY:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid API key"},
        )

    return await call_next(request)


async def rate_limit_middleware(request: Request, call_next) -> Response:
    """
    Middleware to apply rate limiting per user.

    User is identified by X-User-ID header or API key.
    """
    # Get user identifier from header or use API key as fallback
    user_id = (
        request.headers.get("X-User-ID")
        or request.headers.get("X-API-Key")
        or "anonymous"
    )

    rate_limiter = get_rate_limiter()
    allowed, message = rate_limiter.check(user_id)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": message},
        )

    return await call_next(request)
