"""Tests for cache module."""
import tempfile
import time
from pathlib import Path

from ei_cli.core.cache import Cache


class TestCache:
    """Test Cache class."""

    def test_init_creates_directory(self):
        """Test that cache directory is created on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            assert not cache_dir.exists()

            cache = Cache(cache_dir, ttl_seconds=60)

            assert cache_dir.exists()
            assert cache.cache_dir == cache_dir
            assert cache.ttl_seconds == 60

    def test_generate_key_same_args_same_key(self):
        """Test that same arguments generate same key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            key1 = cache._generate_key("arg1", "arg2", kwarg1="val1")
            key2 = cache._generate_key("arg1", "arg2", kwarg1="val1")

            assert key1 == key2

    def test_generate_key_different_args_different_key(self):
        """Test that different arguments generate different keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            key1 = cache._generate_key("arg1", "arg2")
            key2 = cache._generate_key("arg1", "arg3")

            assert key1 != key2

    def test_get_miss_returns_none(self):
        """Test that cache miss returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            result = cache.get("nonexistent")

            assert result is None
            assert cache._misses == 1
            assert cache._hits == 0

    def test_set_and_get_basic(self):
        """Test basic set and get operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            cache.set("test_value", "key1", "key2")
            result = cache.get("key1", "key2")

            assert result == "test_value"
            assert cache._hits == 1
            assert cache._misses == 0

    def test_set_and_get_complex_value(self):
        """Test caching complex data structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            complex_value = {
                "text": "result",
                "numbers": [1, 2, 3],
                "nested": {"key": "value"},
            }

            cache.set(complex_value, "complex_key")
            result = cache.get("complex_key")

            assert result == complex_value

    def test_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir, ttl_seconds=0.5)

            cache.set("value", "key")

            # Should be available immediately
            result = cache.get("key")
            assert result == "value"

            # Wait for expiration
            time.sleep(0.6)

            # Should be expired
            result = cache.get("key")
            assert result is None

    def test_delete_existing_key(self):
        """Test deleting an existing cache entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            cache.set("value", "key")
            assert cache.get("key") == "value"

            deleted = cache.delete("key")
            assert deleted is True
            assert cache.get("key") is None

    def test_delete_nonexistent_key(self):
        """Test deleting a non-existent key returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            deleted = cache.delete("nonexistent")
            assert deleted is False

    def test_clear_all_entries(self):
        """Test clearing all cache entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            cache.set("value1", "key1")
            cache.set("value2", "key2")
            cache.set("value3", "key3")

            count = cache.clear()

            assert count == 3
            assert cache.get("key1") is None
            assert cache.get("key2") is None
            assert cache.get("key3") is None

    def test_cleanup_expired_removes_old_entries(self):
        """Test that cleanup removes expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir, ttl_seconds=0.5)

            cache.set("value1", "key1")
            cache.set("value2", "key2")

            # Wait for expiration
            time.sleep(0.6)

            # Add a new entry
            cache.set("value3", "key3")

            count = cache.cleanup_expired()

            # Should remove 2 expired entries
            assert count == 2
            assert cache.get("key1") is None
            assert cache.get("key2") is None
            assert cache.get("key3") == "value3"

    def test_cleanup_expired_removes_corrupted(self):
        """Test that cleanup removes corrupted cache files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            # Create a corrupted cache file
            corrupted_path = cache.cache_dir / "corrupted.json"
            with corrupted_path.open("w") as f:
                f.write("not valid json {")

            count = cache.cleanup_expired()

            assert count == 1
            assert not corrupted_path.exists()

    def test_get_stats_tracks_hits_and_misses(self):
        """Test that statistics are tracked correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            cache.set("value", "key")

            cache.get("key")  # hit
            cache.get("key")  # hit
            cache.get("nonexistent")  # miss

            stats = cache.get_stats()

            assert stats["hits"] == 2
            assert stats["misses"] == 1
            assert stats["hit_rate"] == 66.67
            assert stats["size"] == 1

    def test_reset_stats(self):
        """Test resetting statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            cache.set("value", "key")
            cache.get("key")
            cache.get("nonexistent")

            cache.reset_stats()
            stats = cache.get_stats()

            assert stats["hits"] == 0
            assert stats["misses"] == 0
            assert stats["hit_rate"] == 0.0

    def test_repr(self):
        """Test string representation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir, ttl_seconds=3600)
            cache.set("value", "key")

            repr_str = repr(cache)

            assert "Cache" in repr_str
            assert "ttl=3600s" in repr_str
            assert "size=1" in repr_str
            assert "hit_rate=" in repr_str

    def test_get_handles_corrupted_files(self):
        """Test that get handles corrupted cache files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            # Create a corrupted cache file directly
            key = cache._generate_key("test_key")
            cache_path = cache._get_cache_path(key)

            with cache_path.open("w") as f:
                f.write("invalid json")

            result = cache.get("test_key")

            assert result is None
            assert cache._misses == 1

    def test_multiple_kwargs_order_independent(self):
        """Test that kwargs order doesn't affect cache key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            key1 = cache._generate_key(a=1, b=2, c=3)
            key2 = cache._generate_key(c=3, b=2, a=1)

            assert key1 == key2

    def test_cache_persistence_across_instances(self):
        """Test that cache persists across different instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache1 = Cache(tmpdir)
            cache1.set("value1", "key1")

            # Create new instance pointing to same directory
            cache2 = Cache(tmpdir)
            result = cache2.get("key1")

            assert result == "value1"

    def test_zero_ttl_always_expires(self):
        """Test that zero TTL causes immediate expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir, ttl_seconds=0)

            cache.set("value", "key")

            # Should be expired immediately
            result = cache.get("key")
            assert result is None

    def test_get_cache_path_format(self):
        """Test cache file path format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)
            key = "abc123"

            path = cache._get_cache_path(key)

            assert path.parent == cache.cache_dir
            assert path.name == f"{key}.json"

    def test_is_expired_checks_age(self):
        """Test expiration check logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir, ttl_seconds=60)

            # Fresh data
            cache_data = {"cached_at": time.time(), "value": "test"}
            assert not cache._is_expired(cache_data)

            # Old data
            old_data = {"cached_at": time.time() - 120, "value": "test"}
            assert cache._is_expired(old_data)

    def test_hit_rate_zero_when_no_requests(self):
        """Test hit rate is 0 when no requests made."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = Cache(tmpdir)

            stats = cache.get_stats()
            assert stats["hit_rate"] == 0.0
