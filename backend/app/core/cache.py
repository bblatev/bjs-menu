"""
Simple in-memory caching for API responses.
For production, use Redis via the CACHE_URL environment variable.
"""
from functools import wraps
from typing import Optional, Callable, Any
from datetime import datetime, timedelta
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    """In-memory cache with TTL support and size limit."""

    MAX_ENTRIES = 10000  # Prevent unbounded memory growth

    def __init__(self):
        self._cache: dict = {}
        self._expiry: dict = {}

    def _evict_expired(self):
        """Remove expired entries to reclaim memory."""
        now = datetime.now()
        expired = [k for k, exp in self._expiry.items() if exp <= now]
        for k in expired:
            self._cache.pop(k, None)
            self._expiry.pop(k, None)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            if datetime.now() < self._expiry.get(key, datetime.min):
                return self._cache[key]
            else:
                # Expired
                del self._cache[key]
                del self._expiry[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set value in cache with TTL."""
        # Evict expired entries if approaching limit
        if len(self._cache) >= self.MAX_ENTRIES:
            self._evict_expired()
        # If still at limit after eviction, remove oldest entries
        if len(self._cache) >= self.MAX_ENTRIES:
            oldest_keys = sorted(self._expiry, key=self._expiry.get)[:100]
            for k in oldest_keys:
                self._cache.pop(k, None)
                self._expiry.pop(k, None)
        self._cache[key] = value
        self._expiry[key] = datetime.now() + timedelta(seconds=ttl_seconds)

    def delete(self, key: str):
        """Delete key from cache."""
        self._cache.pop(key, None)
        self._expiry.pop(key, None)

    def clear_prefix(self, prefix: str):
        """Clear all keys with given prefix."""
        keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            self.delete(key)

    def clear(self):
        """Clear entire cache."""
        self._cache.clear()
        self._expiry.clear()

    def stats(self) -> dict:
        """Get cache statistics."""
        now = datetime.now()
        valid = sum(1 for k, exp in self._expiry.items() if exp > now)
        return {
            "total_keys": len(self._cache),
            "valid_keys": valid,
            "expired_keys": len(self._cache) - valid
        }


# Global cache instance (in-memory)
cache = SimpleCache()


class RedisCacheClient:
    """Redis-backed cache with in-memory fallback."""

    def __init__(self):
        self._redis = None
        self._fallback = cache  # Use in-memory SimpleCache as fallback

    def initialize(self, redis_url: str | None = None):
        if redis_url:
            try:
                import redis
                self._redis = redis.from_url(
                    redis_url, socket_connect_timeout=2, decode_responses=True,
                )
                self._redis.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis unavailable, using memory cache: {e}")
                self._redis = None

    def get(self, key: str) -> Any | None:
        try:
            if self._redis:
                val = self._redis.get(key)
                return json.loads(val) if val else None
        except Exception:
            pass
        return self._fallback.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        serialized = json.dumps(value, default=str)
        try:
            if self._redis:
                self._redis.setex(key, ttl_seconds, serialized)
                return
        except Exception:
            pass
        self._fallback.set(key, value, ttl_seconds)

    def delete(self, key: str):
        try:
            if self._redis:
                self._redis.delete(key)
                return
        except Exception:
            pass
        self._fallback.delete(key)

    def invalidate_pattern(self, pattern: str):
        try:
            if self._redis:
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        self._redis.delete(*keys)
                    if cursor == 0:
                        break
                return
        except Exception:
            pass
        prefix = pattern.replace("*", "")
        self._fallback.clear_prefix(prefix)


redis_cache = RedisCacheClient()


def make_cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments."""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(ttl_seconds: int = 300, prefix: str = ""):
    """
    Decorator to cache function results.

    Usage:
        @cached(ttl_seconds=300, prefix="menu")
        def get_menu(venue_id: int):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_key = f"{prefix}:{func.__name__}:{make_cache_key(*args, **kwargs)}"
            cached_value = cache.get(cache_key)

            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = f"{prefix}:{func.__name__}:{make_cache_key(*args, **kwargs)}"
            cached_value = cache.get(cache_key)

            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            return result

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_cache(prefix: str):
    """Invalidate all cache entries with given prefix."""
    cache.clear_prefix(prefix)


# Cache keys for common operations
class CacheKeys:
    MENU = "menu"
    CATEGORIES = "categories"
    MODIFIERS = "modifiers"
    ANALYTICS = "analytics"
    DASHBOARD = "dashboard"
    FORECAST = "forecast"
    STOCK = "stock"
