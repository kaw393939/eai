"""Tests for rate_limiter module."""
import threading
import time

from ei_cli.core.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_init(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        assert limiter.max_requests == 5
        assert limiter.window_seconds == 60
        assert len(limiter.requests) == 0

    def test_can_proceed_allows_requests_under_limit(self):
        """Test that requests under limit are allowed."""
        limiter = RateLimiter(max_requests=3, window_seconds=1)

        # First 3 requests should succeed
        can_proceed, wait_time = limiter.can_proceed()
        assert can_proceed is True
        assert wait_time == 0.0

        can_proceed, wait_time = limiter.can_proceed()
        assert can_proceed is True
        assert wait_time == 0.0

        can_proceed, wait_time = limiter.can_proceed()
        assert can_proceed is True
        assert wait_time == 0.0

    def test_can_proceed_blocks_requests_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # First 2 requests succeed
        limiter.can_proceed()
        limiter.can_proceed()

        # Third request should be blocked
        can_proceed, wait_time = limiter.can_proceed()
        assert can_proceed is False
        assert wait_time > 0.0
        assert wait_time <= 1.0

    def test_sliding_window_expires_old_requests(self):
        """Test that old requests expire and allow new ones."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.5)

        # Fill the limit
        limiter.can_proceed()
        limiter.can_proceed()

        # Third request blocked
        can_proceed, _ = limiter.can_proceed()
        assert can_proceed is False

        # Wait for window to expire
        time.sleep(0.6)

        # Should allow new request after window expires
        can_proceed, wait_time = limiter.can_proceed()
        assert can_proceed is True
        assert wait_time == 0.0

    def test_wait_if_needed_waits_when_limit_exceeded(self):
        """Test that wait_if_needed actually waits."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.5)

        # Fill the limit
        limiter.can_proceed()
        limiter.can_proceed()

        # This should wait
        start = time.time()
        wait_time = limiter.wait_if_needed()
        elapsed = time.time() - start

        assert wait_time > 0.0
        # Should have waited ~0.5s (with small tolerance)
        assert elapsed >= 0.4

    def test_wait_if_needed_no_wait_when_under_limit(self):
        """Test that wait_if_needed returns immediately when under limit."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)

        wait_time = limiter.wait_if_needed()
        assert wait_time == 0.0

    def test_reset_clears_requests(self):
        """Test that reset clears all tracked requests."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)

        # Add requests
        limiter.can_proceed()
        limiter.can_proceed()
        assert limiter.get_current_count() == 2

        # Reset
        limiter.reset()
        assert limiter.get_current_count() == 0

    def test_get_current_count(self):
        """Test get_current_count returns accurate count."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        assert limiter.get_current_count() == 0

        limiter.can_proceed()
        assert limiter.get_current_count() == 1

        limiter.can_proceed()
        limiter.can_proceed()
        assert limiter.get_current_count() == 3

    def test_get_current_count_removes_expired(self):
        """Test that get_current_count removes expired requests."""
        limiter = RateLimiter(max_requests=5, window_seconds=0.5)

        limiter.can_proceed()
        limiter.can_proceed()
        assert limiter.get_current_count() == 2

        # Wait for expiration
        time.sleep(0.6)
        assert limiter.get_current_count() == 0

    def test_get_availability(self):
        """Test get_availability returns correct used/available counts."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        used, available = limiter.get_availability()
        assert used == 0
        assert available == 5

        limiter.can_proceed()
        limiter.can_proceed()

        used, available = limiter.get_availability()
        assert used == 2
        assert available == 3

    def test_repr(self):
        """Test string representation."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        limiter.can_proceed()

        repr_str = repr(limiter)
        assert "RateLimiter" in repr_str
        assert "max=5" in repr_str
        assert "window=60s" in repr_str
        assert "used=1" in repr_str
        assert "available=4" in repr_str

    def test_thread_safety(self):
        """Test that rate limiter is thread-safe."""
        limiter = RateLimiter(max_requests=10, window_seconds=1)
        results = []

        def make_request():
            can_proceed, _ = limiter.can_proceed()
            results.append(can_proceed)

        # Create 20 threads trying to make requests
        threads = [threading.Thread(target=make_request) for _ in range(20)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have exactly 10 successes (the limit)
        assert sum(1 for r in results if r) == 10
        assert sum(1 for r in results if not r) == 10

    def test_multiple_wait_cycles(self):
        """Test that multiple wait cycles work correctly."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.3)

        # First batch
        limiter.can_proceed()
        limiter.can_proceed()

        # Wait and make another request
        time.sleep(0.4)
        can_proceed, _ = limiter.can_proceed()
        assert can_proceed is True

        # Should still respect the limit
        can_proceed, _ = limiter.can_proceed()
        assert can_proceed is True

        can_proceed, _ = limiter.can_proceed()
        assert can_proceed is False

    def test_zero_wait_time_when_slots_available(self):
        """Test that wait time is zero when slots are available."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)

        for _ in range(5):
            can_proceed, wait_time = limiter.can_proceed()
            assert can_proceed is True
            assert wait_time == 0.0

    def test_accurate_wait_time_calculation(self):
        """Test that wait time is calculated accurately."""
        limiter = RateLimiter(max_requests=1, window_seconds=1.0)

        # First request succeeds
        can_proceed, _ = limiter.can_proceed()
        assert can_proceed is True

        # Immediately check second request
        can_proceed, wait_time = limiter.can_proceed()
        assert can_proceed is False
        assert 0.9 <= wait_time <= 1.0  # Should be close to 1 second
