"""Tests for koro.rate_limit module."""

import time
import pytest
from unittest.mock import patch

from koro.rate_limit import RateLimiter


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_init_with_defaults(self):
        """RateLimiter uses default values."""
        limiter = RateLimiter()

        assert limiter.cooldown_seconds == 2
        assert limiter.per_minute_limit == 10

    def test_init_with_custom_values(self):
        """RateLimiter accepts custom values."""
        limiter = RateLimiter(cooldown_seconds=5, per_minute_limit=20)

        assert limiter.cooldown_seconds == 5
        assert limiter.per_minute_limit == 20

    def test_first_message_allowed(self):
        """First message from user is always allowed."""
        limiter = RateLimiter()

        allowed, message = limiter.check(12345)

        assert allowed is True
        assert message == ""

    def test_cooldown_blocks_rapid_messages(self):
        """Messages within cooldown period are blocked."""
        limiter = RateLimiter(cooldown_seconds=2)

        # First message
        limiter.check(12345)

        # Immediate second message should be blocked
        allowed, message = limiter.check(12345)

        assert allowed is False
        assert "wait" in message.lower()

    def test_cooldown_allows_after_delay(self):
        """Messages after cooldown period are allowed."""
        limiter = RateLimiter(cooldown_seconds=0.1)

        limiter.check(12345)
        time.sleep(0.15)
        allowed, message = limiter.check(12345)

        assert allowed is True

    def test_per_minute_limit_blocks_excess(self):
        """Per-minute limit blocks excess messages."""
        # Use a small but non-zero cooldown to avoid timing edge cases
        limiter = RateLimiter(cooldown_seconds=0.001, per_minute_limit=3)

        # First 3 should pass (with tiny delay between)
        for i in range(3):
            time.sleep(0.002)  # Small delay to pass cooldown
            allowed, _ = limiter.check(12345)
            assert allowed is True, f"Message {i+1} should be allowed"

        # 4th should be blocked by per-minute limit
        time.sleep(0.002)
        allowed, message = limiter.check(12345)

        assert allowed is False
        assert "limit reached" in message.lower()

    def test_per_minute_resets_after_minute(self):
        """Per-minute counter resets after a minute."""
        limiter = RateLimiter(cooldown_seconds=0.001, per_minute_limit=2)

        # Use up limit
        time.sleep(0.002)
        limiter.check(12345)
        time.sleep(0.002)
        limiter.check(12345)
        time.sleep(0.002)
        allowed, _ = limiter.check(12345)
        assert allowed is False

        # Simulate time passing by adjusting minute_start and last_message
        limiter.user_limits["12345"]["minute_start"] = time.time() - 61
        limiter.user_limits["12345"]["last_message"] = time.time() - 61

        # Should be allowed again
        allowed, _ = limiter.check(12345)
        assert allowed is True

    def test_different_users_independent(self):
        """Different users have independent limits."""
        limiter = RateLimiter(cooldown_seconds=0, per_minute_limit=1)

        # User 1 uses their limit
        limiter.check(11111)
        allowed1, _ = limiter.check(11111)
        assert allowed1 is False

        # User 2 should still be allowed
        allowed2, _ = limiter.check(22222)
        assert allowed2 is True

    def test_reset_clears_user_limits(self):
        """reset() clears limits for specific user."""
        limiter = RateLimiter(cooldown_seconds=0, per_minute_limit=1)

        limiter.check(12345)
        limiter.check(12345)  # Blocked

        limiter.reset(12345)

        allowed, _ = limiter.check(12345)
        assert allowed is True

    def test_reset_all_clears_all(self):
        """reset_all() clears all user limits."""
        limiter = RateLimiter(cooldown_seconds=0, per_minute_limit=1)

        limiter.check(11111)
        limiter.check(22222)

        limiter.reset_all()

        assert limiter.user_limits == {}

    def test_check_updates_last_message_time(self):
        """check() updates last message timestamp."""
        limiter = RateLimiter()

        before = time.time()
        limiter.check(12345)
        after = time.time()

        last_msg = limiter.user_limits["12345"]["last_message"]
        assert before <= last_msg <= after

    def test_check_increments_minute_count(self):
        """check() increments minute counter."""
        limiter = RateLimiter(cooldown_seconds=0.001)

        time.sleep(0.002)
        limiter.check(12345)
        assert limiter.user_limits["12345"]["minute_count"] == 1

        time.sleep(0.002)
        limiter.check(12345)
        assert limiter.user_limits["12345"]["minute_count"] == 2

    def test_cooldown_message_shows_wait_time(self):
        """Cooldown message shows how long to wait."""
        limiter = RateLimiter(cooldown_seconds=10)

        limiter.check(12345)
        _, message = limiter.check(12345)

        # Should show approximately 10 seconds to wait
        assert "9" in message or "10" in message
