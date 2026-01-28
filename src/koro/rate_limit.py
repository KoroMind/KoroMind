"""Rate limiting for message handling.

This module re-exports from koro.core.rate_limit for backward compatibility.
New code should import directly from koro.core.rate_limit.
"""

# Re-export everything from core rate_limit
from koro.core.rate_limit import (
    RateLimiter,
    get_rate_limiter,
    set_rate_limiter,
)

__all__ = [
    "RateLimiter",
    "get_rate_limiter",
    "set_rate_limiter",
]
