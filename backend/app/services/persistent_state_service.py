"""
Persistent State Service

Replaces in-memory state with persistent storage (Redis or DB fallback).

Addresses critical in-memory state issues identified in safety audit:
- WebSocket message queue
- Order throttling state
- Kiosk sessions
- Course firing state

When feature flags are enabled, state is persisted to survive restarts.
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func

from app.core.feature_flags import is_enabled
from app.db.base import Base


class PersistentStateEntry(Base):
    """
    Generic persistent state storage.

    Replaces in-memory dicts/caches with DB-backed storage.
    """
    __tablename__ = "persistent_state"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    namespace = Column(String(50), nullable=False, index=True)  # websocket, throttle, kiosk
    key = Column(String(255), nullable=False, index=True)
    value = Column(JSON, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PersistentStateService:
    """
    Service for persistent state management.

    Provides Redis-like interface with DB fallback.
    Respects feature flags for gradual migration.
    """

    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.redis = redis_client
        self._use_redis = redis_client is not None and is_enabled("REDIS_CACHE_ENABLED")

    def get(
        self,
        namespace: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get a value from persistent state."""
        if self._use_redis:
            return self._redis_get(namespace, key, default)
        return self._db_get(namespace, key, default)

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Set a value in persistent state."""
        if self._use_redis:
            return self._redis_set(namespace, key, value, ttl_seconds)
        return self._db_set(namespace, key, value, ttl_seconds)

    def delete(self, namespace: str, key: str) -> bool:
        """Delete a value from persistent state."""
        if self._use_redis:
            return self._redis_delete(namespace, key)
        return self._db_delete(namespace, key)

    def get_all(self, namespace: str) -> Dict[str, Any]:
        """Get all values in a namespace."""
        if self._use_redis:
            return self._redis_get_all(namespace)
        return self._db_get_all(namespace)

    def cleanup_expired(self) -> int:
        """Clean up expired entries. Returns count deleted."""
        if self._use_redis:
            return 0  # Redis handles TTL automatically

        deleted = self.db.query(PersistentStateEntry).filter(
            PersistentStateEntry.expires_at < datetime.utcnow()
        ).delete()
        self.db.commit()
        return deleted

    # DB implementations
    def _db_get(self, namespace: str, key: str, default: Any) -> Any:
        entry = self.db.query(PersistentStateEntry).filter(
            PersistentStateEntry.namespace == namespace,
            PersistentStateEntry.key == key,
        ).first()

        if not entry:
            return default

        # Check expiration
        if entry.expires_at and entry.expires_at < datetime.utcnow():
            self.db.delete(entry)
            self.db.commit()
            return default

        return entry.value

    def _db_set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int],
    ) -> bool:
        entry = self.db.query(PersistentStateEntry).filter(
            PersistentStateEntry.namespace == namespace,
            PersistentStateEntry.key == key,
        ).first()

        expires_at = None
        if ttl_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        if entry:
            entry.value = value
            entry.expires_at = expires_at
        else:
            entry = PersistentStateEntry(
                namespace=namespace,
                key=key,
                value=value,
                expires_at=expires_at,
            )
            self.db.add(entry)

        self.db.commit()
        return True

    def _db_delete(self, namespace: str, key: str) -> bool:
        deleted = self.db.query(PersistentStateEntry).filter(
            PersistentStateEntry.namespace == namespace,
            PersistentStateEntry.key == key,
        ).delete()
        self.db.commit()
        return deleted > 0

    def _db_get_all(self, namespace: str) -> Dict[str, Any]:
        entries = self.db.query(PersistentStateEntry).filter(
            PersistentStateEntry.namespace == namespace,
        ).all()

        result = {}
        now = datetime.utcnow()

        for entry in entries:
            if entry.expires_at and entry.expires_at < now:
                continue
            result[entry.key] = entry.value

        return result

    # Redis implementations (when available)
    def _redis_get(self, namespace: str, key: str, default: Any) -> Any:
        try:
            redis_key = f"{namespace}:{key}"
            value = self.redis.get(redis_key)
            if value is None:
                return default
            return json.loads(value)
        except Exception as e:
            logger.warning(f"Redis GET failed for {namespace}:{key}: {e}")
            return default

    def _redis_set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int],
    ) -> bool:
        try:
            redis_key = f"{namespace}:{key}"
            serialized = json.dumps(value)
            if ttl_seconds:
                self.redis.setex(redis_key, ttl_seconds, serialized)
            else:
                self.redis.set(redis_key, serialized)
            return True
        except Exception as e:
            logger.warning(f"Redis SET failed for {namespace}:{key}: {e}")
            return False

    def _redis_delete(self, namespace: str, key: str) -> bool:
        try:
            redis_key = f"{namespace}:{key}"
            return self.redis.delete(redis_key) > 0
        except Exception as e:
            logger.warning(f"Redis DELETE failed for {namespace}:{key}: {e}")
            return False

    def _redis_get_all(self, namespace: str) -> Dict[str, Any]:
        try:
            pattern = f"{namespace}:*"
            keys = self.redis.keys(pattern)
            result = {}
            for key in keys:
                value = self.redis.get(key)
                if value:
                    short_key = key.decode().replace(f"{namespace}:", "")
                    result[short_key] = json.loads(value)
            return result
        except Exception as e:
            logger.warning(f"Redis GET_ALL failed for namespace {namespace}: {e}")
            return {}


# Specialized state managers for specific use cases

class WebSocketQueueManager:
    """Persistent WebSocket message queue."""

    NAMESPACE = "websocket_queue"

    def __init__(self, state_service: PersistentStateService):
        self.state = state_service

    def is_persistent(self) -> bool:
        return is_enabled("PERSISTENT_WEBSOCKET_QUEUE")

    def enqueue(self, connection_id: str, message: Dict[str, Any]) -> None:
        if not self.is_persistent():
            return  # Fall back to in-memory

        queue = self.state.get(self.NAMESPACE, connection_id, [])
        queue.append({
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.state.set(self.NAMESPACE, connection_id, queue, ttl_seconds=3600)

    def dequeue_all(self, connection_id: str) -> List[Dict[str, Any]]:
        if not self.is_persistent():
            return []

        queue = self.state.get(self.NAMESPACE, connection_id, [])
        self.state.delete(self.NAMESPACE, connection_id)
        return [item["message"] for item in queue]


class ThrottleStateManager:
    """Persistent order throttling state."""

    NAMESPACE = "throttle_state"

    def __init__(self, state_service: PersistentStateService):
        self.state = state_service

    def is_persistent(self) -> bool:
        return is_enabled("PERSISTENT_THROTTLE_STATE")

    def record_request(self, key: str, window_seconds: int = 60) -> int:
        """Record a request and return count in window."""
        if not self.is_persistent():
            return 0

        data = self.state.get(self.NAMESPACE, key, {"count": 0, "window_start": None})

        now = datetime.utcnow()
        window_start = data.get("window_start")

        if window_start:
            window_start = datetime.fromisoformat(window_start)
            if (now - window_start).total_seconds() > window_seconds:
                # Reset window
                data = {"count": 1, "window_start": now.isoformat()}
            else:
                data["count"] += 1
        else:
            data = {"count": 1, "window_start": now.isoformat()}

        self.state.set(self.NAMESPACE, key, data, ttl_seconds=window_seconds * 2)
        return data["count"]


class KioskSessionManager:
    """Persistent kiosk session state."""

    NAMESPACE = "kiosk_sessions"
    SESSION_TTL = 3600  # 1 hour

    def __init__(self, state_service: PersistentStateService):
        self.state = state_service

    def is_persistent(self) -> bool:
        return is_enabled("PERSISTENT_KIOSK_SESSIONS")

    def create_session(self, kiosk_id: str, session_data: Dict[str, Any]) -> str:
        """Create a new kiosk session."""
        session_id = hashlib.sha256(
            f"{kiosk_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:32]

        session = {
            "session_id": session_id,
            "kiosk_id": kiosk_id,
            "created_at": datetime.utcnow().isoformat(),
            "data": session_data,
        }

        if self.is_persistent():
            self.state.set(self.NAMESPACE, session_id, session, ttl_seconds=self.SESSION_TTL)

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get kiosk session."""
        if not self.is_persistent():
            return None
        return self.state.get(self.NAMESPACE, session_id)

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update kiosk session data."""
        if not self.is_persistent():
            return False

        session = self.get_session(session_id)
        if not session:
            return False

        session["data"].update(data)
        session["updated_at"] = datetime.utcnow().isoformat()
        self.state.set(self.NAMESPACE, session_id, session, ttl_seconds=self.SESSION_TTL)
        return True

    def end_session(self, session_id: str) -> bool:
        """End kiosk session."""
        if not self.is_persistent():
            return False
        return self.state.delete(self.NAMESPACE, session_id)
