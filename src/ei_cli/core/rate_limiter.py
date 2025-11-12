"""
Rate limiting with sliding window algorithm.

Provides thread-safe rate limiting for API calls with better accuracy
than simple fixed-window approaches.
"""
import threading
import time
from collections import deque


class RateLimiter:
    """
    Sliding window rate limiter.

    Tracks requests with timestamps and enforces rate limits
    more accurately than simple counters.
    """

    def __init__(self, max_requests: int, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in window
            window_seconds: Time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque[float] = deque()
        self._lock = threading.Lock()

    def can_proceed(self) -> tuple[bool, float]:
        """
        Check if a request can proceed and return wait time if not.

        Returns:
            Tuple of (can_proceed, wait_seconds)
            - can_proceed: True if request can proceed
            - wait_seconds: Seconds to wait if cannot proceed (0 if can)
        """
        now = time.time()

        with self._lock:
            # Remove requests outside the window
            cutoff = now - self.window_seconds
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            # Check if we can proceed
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True, 0.0

            # Calculate wait time until oldest request expires
            oldest = self.requests[0]
            wait_time = self.window_seconds - (now - oldest)
            return False, max(0.0, wait_time)

    def wait_if_needed(self) -> float:
        """
        Wait if rate limit is exceeded.

        Returns:
            Seconds waited (0 if no wait needed)
        """
        can_proceed, wait_time = self.can_proceed()

        if not can_proceed and wait_time > 0:
            time.sleep(wait_time)
            # After waiting, mark the request
            with self._lock:
                self.requests.append(time.time())
            return wait_time

        return 0.0

    def reset(self) -> None:
        """Clear all tracked requests."""
        with self._lock:
            self.requests.clear()

    def get_current_count(self) -> int:
        """
        Get current number of requests in the window.

        Returns:
            Number of active requests
        """
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            # Remove expired requests
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            return len(self.requests)

    def get_availability(self) -> tuple[int, int]:
        """
        Get current availability status.

        Returns:
            Tuple of (used_slots, available_slots)
        """
        current = self.get_current_count()
        available = self.max_requests - current
        return current, max(0, available)

    def __repr__(self) -> str:
        """String representation."""
        used, available = self.get_availability()
        return (
            f"RateLimiter(max={self.max_requests}, "
            f"window={self.window_seconds}s, "
            f"used={used}, available={available})"
        )
