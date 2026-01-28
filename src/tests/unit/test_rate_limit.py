"""Tests for koro.rate_limit module."""

import pytest

import koro.core.rate_limit as rate_limit


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.fixture
    def time_controller(self, monkeypatch):
        """Provide a controllable time source for deterministic tests."""

        class TimeController:
            def __init__(self, start: float = 0.0):
                self.current = start

            def time(self) -> float:
                return self.current

            def advance(self, seconds: float) -> None:
                self.current += seconds

        controller = TimeController()
        monkeypatch.setattr(rate_limit.time, "time", controller.time)
        return controller

    def test_init_with_defaults(self):
        """RateLimiter uses default values."""
        limiter = rate_limit.RateLimiter()

        assert limiter.cooldown_seconds == 2
        assert limiter.per_minute_limit == 10

    def test_init_with_custom_values(self):
        """RateLimiter accepts custom values."""
        limiter = rate_limit.RateLimiter(cooldown_seconds=5, per_minute_limit=20)

        assert limiter.cooldown_seconds == 5
        assert limiter.per_minute_limit == 20

    def test_first_message_allowed(self, time_controller):
        """First message from user is always allowed."""
        limiter = rate_limit.RateLimiter()

        allowed, message = limiter.check(12345)

        assert allowed is True
        assert message == ""

    def test_cooldown_blocks_rapid_messages(self, time_controller):
        """Messages within cooldown period are blocked."""
        limiter = rate_limit.RateLimiter(cooldown_seconds=2)

        # First message
        limiter.check(12345)

        # Immediate second message should be blocked
        allowed, message = limiter.check(12345)

        assert allowed is False
        assert "wait" in message.lower()

    def test_cooldown_allows_after_delay(self, time_controller):
        """Messages after cooldown period are allowed."""
        limiter = rate_limit.RateLimiter(cooldown_seconds=0.1)

        limiter.check(12345)
        time_controller.advance(0.15)
        allowed, message = limiter.check(12345)

        assert allowed is True

    def test_per_minute_limit_blocks_excess(self, time_controller):
        """Per-minute limit blocks excess messages."""
        limiter = rate_limit.RateLimiter(cooldown_seconds=0.01, per_minute_limit=3)

        # First 3 should pass (with tiny delay between)
        for i in range(3):
            time_controller.advance(0.02)
            allowed, _ = limiter.check(12345)
            assert allowed is True, f"Message {i+1} should be allowed"

        # 4th should be blocked by per-minute limit
        time_controller.advance(0.02)
        allowed, message = limiter.check(12345)

        assert allowed is False
        assert "limit reached" in message.lower()

    def test_per_minute_resets_after_minute(self, time_controller):
        """Per-minute counter resets after a minute."""
        limiter = rate_limit.RateLimiter(cooldown_seconds=0.01, per_minute_limit=2)

        # Use up limit
        time_controller.advance(0.02)
        limiter.check(12345)
        time_controller.advance(0.02)
        limiter.check(12345)
        allowed, _ = limiter.check(12345)
        assert allowed is False

        # Move past the minute window
        time_controller.advance(61)

        # Should be allowed again
        allowed, _ = limiter.check(12345)
        assert allowed is True

    def test_different_users_independent(self, time_controller):
        """Different users have independent limits."""
        limiter = rate_limit.RateLimiter(cooldown_seconds=0, per_minute_limit=1)

        # User 1 uses their limit
        limiter.check(11111)
        allowed1, _ = limiter.check(11111)
        assert allowed1 is False

        # User 2 should still be allowed
        allowed2, _ = limiter.check(22222)
        assert allowed2 is True

    def test_reset_clears_user_limits(self, time_controller):
        """reset() clears limits for specific user."""
        limiter = rate_limit.RateLimiter(cooldown_seconds=0, per_minute_limit=1)

        limiter.check(12345)
        limiter.check(12345)  # Blocked

        limiter.reset(12345)

        allowed, _ = limiter.check(12345)
        assert allowed is True

    def test_reset_all_clears_all(self, time_controller):
        """reset_all() clears all user limits."""
        limiter = rate_limit.RateLimiter(cooldown_seconds=0, per_minute_limit=1)

        limiter.check(11111)
        limiter.check(22222)

        limiter.reset_all()

        assert limiter.user_limits == {}

    def test_check_updates_last_message_time(self, time_controller):
        """check() updates last message timestamp."""
        limiter = rate_limit.RateLimiter()

        limiter.check(12345)
        last_msg = limiter.user_limits["12345"]["last_message"]
        assert last_msg == time_controller.current

    def test_check_increments_minute_count(self, time_controller):
        """check() increments minute counter."""
        limiter = rate_limit.RateLimiter(cooldown_seconds=0.01)

        time_controller.advance(0.02)
        limiter.check(12345)
        assert limiter.user_limits["12345"]["minute_count"] == 1

        time_controller.advance(0.02)
        limiter.check(12345)
        assert limiter.user_limits["12345"]["minute_count"] == 2

    def test_cooldown_message_shows_wait_time(self, time_controller):
        """Cooldown message shows how long to wait."""
        limiter = rate_limit.RateLimiter(cooldown_seconds=10)

        limiter.check(12345)
        _, message = limiter.check(12345)

        assert "please wait" in message.lower()
        assert "s" in message
