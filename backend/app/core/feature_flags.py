"""
Feature Flags Framework for Zver POS + Zver Control A.I.

All new features MUST be behind feature flags with default=OFF.
This ensures backwards compatibility during production rollout.

Usage:
    from app.core.feature_flags import flags, is_enabled

    if is_enabled("LEDGER_ENABLED"):
        # New ledger behavior
    else:
        # Original behavior
"""

import os
from typing import Dict, Optional
from functools import lru_cache


class FeatureFlags:
    """
    Feature flag management with environment-based configuration.

    Flags default to OFF (False) unless explicitly enabled.
    Enable via environment variables: FEATURE_<FLAG_NAME>=true
    """

    # Registry of all feature flags with descriptions
    REGISTRY: Dict[str, str] = {
        # Phase 2: Video Policy
        "VIDEO_STORAGE_BLOCKED": "Block all video file storage on HQ server",

        # Phase 3: Ledger & Audit
        "LEDGER_ENABLED": "Enable immutable ledger for payment operations",
        "IDEMPOTENCY_KEYS_ENABLED": "Enable idempotency key support for payments",
        "CASH_VARIANCE_ALERTS": "Enable cash variance detection and alerts",

        # Phase 4: Offline Sync
        "OFFLINE_SYNC_ENABLED": "Enable terminal offline queue and sync",
        "MENU_VERSIONING_ENABLED": "Enable menu version tracking for sync",

        # Phase 5: Persistence
        "REDIS_CACHE_ENABLED": "Use Redis instead of in-memory cache",
        "PERSISTENT_WEBSOCKET_QUEUE": "Persist WebSocket message queue to DB",
        "PERSISTENT_THROTTLE_STATE": "Persist order throttle state to DB",
        "PERSISTENT_KIOSK_SESSIONS": "Persist kiosk sessions to DB",

        # Phase 6: RBAC
        "RBAC_V2_ENABLED": "Enable centralized RBAC policy enforcement",
        "STRICT_TENANT_ISOLATION": "Enforce strict multi-tenant isolation",

        # Phase 7: Anti-Theft
        "ANTI_THEFT_FUSION": "Enable anti-theft fusion engine",
        "STAFF_RISK_SCORING": "Enable staff risk scoring",
        "EVIDENCE_PACKETS": "Enable evidence packet generation",

        # Phase 8: Observability
        "CORRELATION_IDS_ENABLED": "Add correlation IDs to all requests",
        "PROMETHEUS_METRICS": "Enable Prometheus metrics endpoint",
    }

    def __init__(self):
        self._cache: Dict[str, bool] = {}
        self._load_from_environment()

    def _load_from_environment(self) -> None:
        """Load flag values from environment variables."""
        for flag_name in self.REGISTRY:
            env_key = f"FEATURE_{flag_name}"
            env_value = os.environ.get(env_key, "").lower()
            # Only enable if explicitly set to 'true', '1', or 'yes'
            self._cache[flag_name] = env_value in ("true", "1", "yes")

    def is_enabled(self, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag_name: Name of the flag (without FEATURE_ prefix)

        Returns:
            True if enabled, False otherwise (default)
        """
        if flag_name not in self.REGISTRY:
            # Unknown flags default to False for safety
            return False
        return self._cache.get(flag_name, False)

    def get_all(self) -> Dict[str, bool]:
        """Get all flag states."""
        return {
            flag: self.is_enabled(flag)
            for flag in self.REGISTRY
        }

    def get_enabled(self) -> Dict[str, bool]:
        """Get only enabled flags."""
        return {
            flag: True
            for flag in self.REGISTRY
            if self.is_enabled(flag)
        }

    def override(self, flag_name: str, value: bool) -> None:
        """
        Override a flag value (for testing only).

        Args:
            flag_name: Name of the flag
            value: New value
        """
        if flag_name in self.REGISTRY:
            self._cache[flag_name] = value

    def reset(self) -> None:
        """Reset all flags to environment values (for testing)."""
        self._load_from_environment()

    def __repr__(self) -> str:
        enabled = [f for f in self.REGISTRY if self.is_enabled(f)]
        return f"<FeatureFlags enabled={enabled}>"


# Global singleton instance
_flags_instance: Optional[FeatureFlags] = None


def get_flags() -> FeatureFlags:
    """Get the global FeatureFlags instance."""
    global _flags_instance
    if _flags_instance is None:
        _flags_instance = FeatureFlags()
    return _flags_instance


def is_enabled(flag_name: str) -> bool:
    """
    Convenience function to check if a flag is enabled.

    Usage:
        from app.core.feature_flags import is_enabled

        if is_enabled("LEDGER_ENABLED"):
            record_to_ledger(payment)
    """
    return get_flags().is_enabled(flag_name)


def require_flag(flag_name: str):
    """
    Decorator to require a feature flag for an endpoint.

    Usage:
        @router.post("/new-feature")
        @require_flag("NEW_FEATURE_ENABLED")
        async def new_feature():
            ...
    """
    from functools import wraps
    from fastapi import HTTPException

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not is_enabled(flag_name):
                raise HTTPException(
                    status_code=404,
                    detail=f"Feature not available"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience alias
flags = get_flags()
