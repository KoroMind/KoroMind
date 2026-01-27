"""Rate limiting for message handling."""

import time

from koro.config import RATE_LIMIT_PER_MINUTE, RATE_LIMIT_SECONDS


class RateLimiter:
    """Rate limiter for per-user message throttling."""

    def __init__(
        self,
        cooldown_seconds: float = None,
        per_minute_limit: int = None,
    ):
        """
        Initialize rate limiter.

        Args:
            cooldown_seconds: Minimum seconds between messages
            per_minute_limit: Maximum messages per minute
        """
        self.cooldown_seconds = cooldown_seconds or RATE_LIMIT_SECONDS
        self.per_minute_limit = per_minute_limit or RATE_LIMIT_PER_MINUTE
        self.user_limits: dict[str, dict] = {}

    def check(self, user_id: int) -> tuple[bool, str]:
        """
        Check if user is within rate limits.

        Args:
            user_id: User identifier

        Returns:
            (allowed, message) - If not allowed, message explains why
        """
        now = time.time()
        user_id_str = str(user_id)

        if user_id_str not in self.user_limits:
            self.user_limits[user_id_str] = {
                "last_message": 0,
                "minute_count": 0,
                "minute_start": now,
            }

        limits = self.user_limits[user_id_str]

        # Check per-message cooldown
        time_since_last = now - limits["last_message"]
        if time_since_last < self.cooldown_seconds:
            wait_time = self.cooldown_seconds - time_since_last
            return (
                False,
                f"Please wait {wait_time:.1f}s before sending another message.",
            )

        # Check per-minute limit
        if now - limits["minute_start"] > 60:
            # Reset minute counter
            limits["minute_start"] = now
            limits["minute_count"] = 0

        if limits["minute_count"] >= self.per_minute_limit:
            return (
                False,
                f"Rate limit reached ({self.per_minute_limit}/min). Please wait.",
            )

        # Update limits
        limits["last_message"] = now
        limits["minute_count"] += 1

        return True, ""

    def reset(self, user_id: int) -> None:
        """Reset rate limits for a user."""
        user_id_str = str(user_id)
        if user_id_str in self.user_limits:
            del self.user_limits[user_id_str]

    def reset_all(self) -> None:
        """Reset all rate limits."""
        self.user_limits.clear()


# Default instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the default rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def set_rate_limiter(limiter: RateLimiter) -> None:
    """Set the default rate limiter instance (for testing)."""
    global _rate_limiter
    _rate_limiter = limiter
