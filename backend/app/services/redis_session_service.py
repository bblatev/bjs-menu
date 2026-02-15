"""
Redis Session Service for Active Learning

Provides persistent storage for active learning sessions,
replacing the in-memory dictionary storage.
"""
import json
import pickle
from app.core.safe_pickle import safe_loads
import redis
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Session expiry in seconds (1 hour)
SESSION_TTL_SECONDS = 3600


class RedisSessionService:
    """Redis-backed session storage for active learning."""

    SESSION_PREFIX = "al_session:"  # active learning session

    def __init__(self):
        """Initialize Redis connection."""
        self._client: Optional[redis.Redis] = None
        self._fallback_store: Dict[str, Dict[str, Any]] = {}
        self._connect()

    def _connect(self):
        """Connect to Redis with fallback to in-memory store."""
        try:
            self._client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=False  # Need binary for pickle
            )
            self._client.ping()
            logger.info("RedisSessionService: Connected to Redis")
        except Exception as e:
            logger.warning(f"RedisSessionService: Redis unavailable, using in-memory fallback: {e}")
            self._client = None

    def _make_key(self, session_id: str) -> str:
        """Create Redis key from session ID."""
        return f"{self.SESSION_PREFIX}{session_id}"

    def set_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl_seconds: int = SESSION_TTL_SECONDS
    ) -> bool:
        """
        Store session data.

        Args:
            session_id: Unique session identifier
            data: Session data to store (must be pickle-serializable)
            ttl_seconds: Time to live in seconds

        Returns:
            True if successful
        """
        # Add timestamp to data
        data['_created_at'] = datetime.now(timezone.utc).isoformat()

        if self._client:
            try:
                key = self._make_key(session_id)
                serialized = pickle.dumps(data)
                self._client.setex(key, ttl_seconds, serialized)
                return True
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                # Fallback to in-memory
                self._fallback_store[session_id] = {
                    **data,
                    '_expires_at': datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
                }
                return True
        else:
            # Use in-memory fallback
            self._fallback_store[session_id] = {
                **data,
                '_expires_at': datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            }
            return True

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data.

        Args:
            session_id: Session identifier

        Returns:
            Session data dict or None if not found/expired
        """
        if self._client:
            try:
                key = self._make_key(session_id)
                data = self._client.get(key)
                if data:
                    return safe_loads(data)
                return None
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                # Try fallback
                return self._get_from_fallback(session_id)
        else:
            return self._get_from_fallback(session_id)

    def _get_from_fallback(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get from in-memory fallback with expiry check."""
        if session_id not in self._fallback_store:
            return None

        data = self._fallback_store[session_id]
        expires_at = data.get('_expires_at')

        if expires_at and datetime.now(timezone.utc) > expires_at:
            del self._fallback_store[session_id]
            return None

        # Return copy without internal fields
        result = {k: v for k, v in data.items() if not k.startswith('_')}
        result['_created_at'] = data.get('_created_at')
        return result

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session data.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted (or didn't exist)
        """
        if self._client:
            try:
                key = self._make_key(session_id)
                self._client.delete(key)
            except Exception as e:
                logger.error(f"Redis delete error: {e}")

        # Also clean from fallback
        self._fallback_store.pop(session_id, None)
        return True

    def cleanup_expired(self) -> int:
        """
        Clean up expired sessions from in-memory fallback.

        Redis handles expiry automatically, but we need to clean
        the fallback store manually.

        Returns:
            Number of expired sessions removed
        """
        if not self._fallback_store:
            return 0

        now = datetime.now(timezone.utc)
        expired = [
            sid for sid, data in self._fallback_store.items()
            if data.get('_expires_at') and data['_expires_at'] < now
        ]

        for sid in expired:
            del self._fallback_store[sid]

        return len(expired)

    def stats(self) -> Dict[str, Any]:
        """Get session store statistics."""
        stats = {
            "backend": "redis" if self._client else "in-memory",
            "fallback_sessions": len(self._fallback_store)
        }

        if self._client:
            try:
                # Count active learning sessions
                keys = self._client.keys(f"{self.SESSION_PREFIX}*")
                stats["redis_sessions"] = len(keys)
            except Exception as e:
                logger.warning(f"Failed to count Redis sessions: {e}")
                stats["redis_sessions"] = "error"

        return stats


# Global instance
_session_service: Optional[RedisSessionService] = None


def get_session_service() -> RedisSessionService:
    """Get or create the global session service instance."""
    global _session_service
    if _session_service is None:
        _session_service = RedisSessionService()
    return _session_service
