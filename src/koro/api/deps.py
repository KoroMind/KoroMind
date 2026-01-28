"""FastAPI dependencies for the KoroMind API.

This module provides dependency injection for FastAPI routes,
including authentication, brain instance, and database connections.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from koro.core.brain import Brain, get_brain
from koro.core.config import KOROMIND_ALLOW_NO_AUTH, KOROMIND_API_KEY


async def get_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """
    Extract API key from request headers.

    Checks X-API-Key header first, then Authorization: Bearer token.

    Args:
        x_api_key: X-API-Key header value
        authorization: Authorization header value

    Returns:
        API key if found, None otherwise
    """
    if x_api_key:
        return x_api_key

    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]

    return None


async def verify_api_key(
    api_key: Annotated[str | None, Depends(get_api_key)],
) -> str:
    """
    Verify API key is valid.

    Args:
        api_key: Extracted API key

    Returns:
        Verified API key

    Raises:
        HTTPException: If authentication fails
    """
    # Allow no auth if configured (development mode)
    if KOROMIND_ALLOW_NO_AUTH:
        return api_key or "anonymous"

    # Require API key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header or Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate against configured key
    if KOROMIND_API_KEY and api_key != KOROMIND_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return api_key


async def get_brain_instance() -> Brain:
    """
    Get Brain instance for request processing.

    Returns:
        Brain instance
    """
    return get_brain()


# Type aliases for dependency injection
APIKey = Annotated[str, Depends(verify_api_key)]
BrainDep = Annotated[Brain, Depends(get_brain_instance)]


async def get_optional_user_id(
    x_user_id: Annotated[str | None, Header()] = None,
) -> str | None:
    """
    Get optional user ID from header.

    Args:
        x_user_id: X-User-ID header value

    Returns:
        User ID if provided
    """
    return x_user_id


OptionalUserID = Annotated[str | None, Depends(get_optional_user_id)]


async def require_user_id(
    user_id: OptionalUserID,
) -> str:
    """
    Require user ID to be provided.

    Args:
        user_id: Optional user ID

    Returns:
        User ID

    Raises:
        HTTPException: If user ID not provided
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-User-ID header",
        )
    return user_id


RequiredUserID = Annotated[str, Depends(require_user_id)]
