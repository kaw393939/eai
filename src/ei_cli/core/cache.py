"""
File-based caching with TTL support.

Provides hash-based filesystem caching to reduce API costs
and improve performance for repeated requests.
"""
import hashlib
import json
import logging
import time
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


class Cache:
    """
    File-based cache with TTL support.

    Uses content hashing to generate cache keys and stores results
    on the filesystem with expiration times.
    """

    def __init__(self, cache_dir: Path | str, ttl_seconds: int = 86400):
        """
        Initialize cache.

        Args:
            cache_dir: Directory to store cache files
            ttl_seconds: Time to live in seconds (default: 24 hours)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Stats
        self._hits = 0
        self._misses = 0

    def _generate_key(self, *args: Any, **kwargs: Any) -> str:
        """
        Generate cache key from arguments.

        Args:
            *args: Positional arguments to hash
            **kwargs: Keyword arguments to hash

        Returns:
            MD5 hash of arguments
        """
        # Create a deterministic string from args and kwargs
        key_data = {
            "args": [str(arg) for arg in args],
            "kwargs": {k: str(v) for k, v in sorted(kwargs.items())},
        }
        key_str = json.dumps(key_data, sort_keys=True)

        # Generate hash (MD5 is fine for cache keys, not security)
        return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get filesystem path for cache key."""
        return self.cache_dir / f"{key}.json"

    def _is_expired(self, cache_data: dict[str, Any]) -> bool:
        """Check if cached data is expired."""
        cached_time = cache_data.get("cached_at", 0)
        age = time.time() - cached_time
        return age > self.ttl_seconds

    def get(self, *args: Any, **kwargs: Any) -> Any | None:
        """
        Get value from cache.

        Args:
            *args: Arguments to generate cache key
            **kwargs: Keyword arguments to generate cache key

        Returns:
            Cached value or None if not found/expired
        """
        key = self._generate_key(*args, **kwargs)
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            self._misses += 1
            logger.debug("Cache miss: %s", key)
            return None

        try:
            with cache_path.open(encoding="utf-8") as f:
                cache_data = json.load(f)

            # Check expiration
            if self._is_expired(cache_data):
                self._misses += 1
                logger.debug("Cache expired: %s", key)
                cache_path.unlink()
                return None

            self._hits += 1
            logger.debug("Cache hit: %s", key)
            return cache_data.get("value")

        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Error reading cache %s: %s", key, e)
            self._misses += 1
            return None

    def set(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """
        Store value in cache.

        Args:
            value: Value to cache
            *args: Arguments to generate cache key
            **kwargs: Keyword arguments to generate cache key
        """
        key = self._generate_key(*args, **kwargs)
        cache_path = self._get_cache_path(key)

        cache_data = {
            "cached_at": time.time(),
            "value": value,
        }

        try:
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(cache_data, f)
            logger.debug("Cached: %s", key)
        except (OSError, TypeError) as e:
            logger.warning("Error writing cache %s: %s", key, e)

    def delete(self, *args: Any, **kwargs: Any) -> bool:
        """
        Delete value from cache.

        Args:
            *args: Arguments to generate cache key
            **kwargs: Keyword arguments to generate cache key

        Returns:
            True if deleted, False if not found
        """
        key = self._generate_key(*args, **kwargs)
        cache_path = self._get_cache_path(key)

        if cache_path.exists():
            cache_path.unlink()
            logger.debug("Deleted cache: %s", key)
            return True

        return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1

        logger.info("Cleared %d cache entries", count)
        return count

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of expired entries removed
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with cache_file.open(encoding="utf-8") as f:
                    cache_data = json.load(f)

                if self._is_expired(cache_data):
                    cache_file.unlink()
                    count += 1

            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Error checking %s: %s", cache_file, e)
                # Delete corrupted cache files
                cache_file.unlink()
                count += 1

        logger.info("Cleaned up %d expired entries", count)
        return count

    def get_stats(self) -> dict[str, int | float]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hits, misses, hit_rate, size
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0

        size = sum(
            1 for _ in self.cache_dir.glob("*.json")
        )

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "size": size,
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._hits = 0
        self._misses = 0

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return (
            f"Cache(dir={self.cache_dir}, "
            f"ttl={self.ttl_seconds}s, "
            f"size={stats['size']}, "
            f"hit_rate={stats['hit_rate']}%)"
        )


def cached(
    ttl_hours: int = 24,
    cache_dir: Path | str | None = None,
    show_cache_hit: bool = True,
) -> Callable:
    """
    Decorator to cache function results.

    Args:
        ttl_hours: Time to live in hours (default: 24)
        cache_dir: Cache directory (default: ~/.ei_cli/cache)
        show_cache_hit: Print message when using cached result

    Returns:
        Decorator function

    Example:
        @cached(ttl_hours=48)
        def expensive_api_call(url: str) -> dict:
            response = requests.get(url)
            return response.json()
    """
    if cache_dir is None:
        cache_dir = Path.home() / ".ei_cli" / "cache"

    cache = Cache(cache_dir=cache_dir, ttl_seconds=ttl_hours * 3600)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key from function name and arguments
            func_name = f"{func.__module__}.{func.__name__}"
            cache_key_args = (func_name,) + args

            # Try to get from cache
            cached_value = cache.get(*cache_key_args, **kwargs)
            if cached_value is not None:
                if show_cache_hit:
                    console.print(
                        f"[dim]Using cached result for {func.__name__}()[/dim]",
                    )
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(result, *cache_key_args, **kwargs)
            return result

        # Expose cache management methods
        wrapper.cache = cache  # type: ignore
        wrapper.clear_cache = lambda: cache.clear()  # type: ignore
        wrapper.cache_stats = lambda: cache.get_stats()  # type: ignore

        return wrapper

    return decorator

