"""
RBAC Policy Enforcement

Centralized Role-Based Access Control for Zver POS.

When RBAC_V2_ENABLED is active:
- All endpoint access is validated against policies
- Strict tenant isolation is enforced
- Permission checks are logged for audit

Roles:
- admin: Full access to all venue resources
- manager: Manage staff, view reports, override operations
- staff: Standard POS operations
- kitchen: Kitchen display access only
- bar: Bar display access only
- kiosk: Self-service operations only
"""

from typing import Dict, List, Optional, Set, Any
from functools import wraps
from enum import Enum

from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.feature_flags import is_enabled


class Permission(str, Enum):
    """Available permissions in the system."""
    # Orders
    ORDER_CREATE = "order:create"
    ORDER_VIEW = "order:view"
    ORDER_MODIFY = "order:modify"
    ORDER_VOID = "order:void"
    ORDER_DISCOUNT = "order:discount"

    # Payments
    PAYMENT_PROCESS = "payment:process"
    PAYMENT_REFUND = "payment:refund"
    PAYMENT_VOID = "payment:void"

    # Menu
    MENU_VIEW = "menu:view"
    MENU_EDIT = "menu:edit"
    MENU_PRICING = "menu:pricing"

    # Kitchen
    KITCHEN_VIEW = "kitchen:view"
    KITCHEN_BUMP = "kitchen:bump"
    KITCHEN_MANAGE = "kitchen:manage"

    # Staff
    STAFF_VIEW = "staff:view"
    STAFF_MANAGE = "staff:manage"
    STAFF_SCHEDULE = "staff:schedule"

    # Reports
    REPORTS_VIEW = "reports:view"
    REPORTS_FINANCIAL = "reports:financial"
    REPORTS_EXPORT = "reports:export"

    # Settings
    SETTINGS_VIEW = "settings:view"
    SETTINGS_EDIT = "settings:edit"

    # Admin
    ADMIN_FULL = "admin:full"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    "admin": {
        Permission.ADMIN_FULL,
        Permission.ORDER_CREATE, Permission.ORDER_VIEW, Permission.ORDER_MODIFY,
        Permission.ORDER_VOID, Permission.ORDER_DISCOUNT,
        Permission.PAYMENT_PROCESS, Permission.PAYMENT_REFUND, Permission.PAYMENT_VOID,
        Permission.MENU_VIEW, Permission.MENU_EDIT, Permission.MENU_PRICING,
        Permission.KITCHEN_VIEW, Permission.KITCHEN_BUMP, Permission.KITCHEN_MANAGE,
        Permission.STAFF_VIEW, Permission.STAFF_MANAGE, Permission.STAFF_SCHEDULE,
        Permission.REPORTS_VIEW, Permission.REPORTS_FINANCIAL, Permission.REPORTS_EXPORT,
        Permission.SETTINGS_VIEW, Permission.SETTINGS_EDIT,
    },
    "manager": {
        Permission.ORDER_CREATE, Permission.ORDER_VIEW, Permission.ORDER_MODIFY,
        Permission.ORDER_VOID, Permission.ORDER_DISCOUNT,
        Permission.PAYMENT_PROCESS, Permission.PAYMENT_REFUND,
        Permission.MENU_VIEW, Permission.MENU_EDIT,
        Permission.KITCHEN_VIEW, Permission.KITCHEN_BUMP, Permission.KITCHEN_MANAGE,
        Permission.STAFF_VIEW, Permission.STAFF_MANAGE, Permission.STAFF_SCHEDULE,
        Permission.REPORTS_VIEW, Permission.REPORTS_FINANCIAL,
        Permission.SETTINGS_VIEW,
    },
    "staff": {
        Permission.ORDER_CREATE, Permission.ORDER_VIEW, Permission.ORDER_MODIFY,
        Permission.PAYMENT_PROCESS,
        Permission.MENU_VIEW,
        Permission.KITCHEN_VIEW, Permission.KITCHEN_BUMP,
    },
    "kitchen": {
        Permission.ORDER_VIEW,
        Permission.KITCHEN_VIEW, Permission.KITCHEN_BUMP,
    },
    "bar": {
        Permission.ORDER_VIEW,
        Permission.KITCHEN_VIEW, Permission.KITCHEN_BUMP,
        Permission.PAYMENT_PROCESS,
    },
    "kiosk": {
        Permission.ORDER_CREATE, Permission.ORDER_VIEW,
        Permission.MENU_VIEW,
        Permission.PAYMENT_PROCESS,
    },
}


class RBACPolicy:
    """
    RBAC Policy enforcement.

    Validates user permissions against requested actions.
    """

    @staticmethod
    def is_active() -> bool:
        """Check if RBAC V2 is enabled."""
        return is_enabled("RBAC_V2_ENABLED")

    @staticmethod
    def get_role_permissions(role: str) -> Set[Permission]:
        """Get permissions for a role."""
        return ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def has_permission(user_role: str, permission: Permission) -> bool:
        """Check if role has specific permission."""
        if not RBACPolicy.is_active():
            return True  # Legacy: allow all when disabled

        # Admin has all permissions
        if Permission.ADMIN_FULL in RBACPolicy.get_role_permissions(user_role):
            return True

        return permission in RBACPolicy.get_role_permissions(user_role)

    @staticmethod
    def has_any_permission(user_role: str, permissions: List[Permission]) -> bool:
        """Check if role has any of the specified permissions."""
        return any(
            RBACPolicy.has_permission(user_role, p)
            for p in permissions
        )

    @staticmethod
    def has_all_permissions(user_role: str, permissions: List[Permission]) -> bool:
        """Check if role has all of the specified permissions."""
        return all(
            RBACPolicy.has_permission(user_role, p)
            for p in permissions
        )

    @staticmethod
    def check_venue_access(user_venue_id: int, target_venue_id: int) -> bool:
        """
        Check if user can access target venue's resources.

        When STRICT_TENANT_ISOLATION is enabled, users can only
        access their own venue's resources.
        """
        if not is_enabled("STRICT_TENANT_ISOLATION"):
            return True  # Legacy: no isolation

        return user_venue_id == target_venue_id


def require_permission(*permissions: Permission):
    """
    Decorator to require specific permissions for an endpoint.

    Usage:
        @router.post("/orders")
        @require_permission(Permission.ORDER_CREATE)
        async def create_order(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from kwargs
            current_user = kwargs.get("current_user")

            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            user_role = getattr(current_user, "role", "staff")

            if not RBACPolicy.has_any_permission(user_role, list(permissions)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_venue_access(venue_id_param: str = "venue_id"):
    """
    Decorator to require venue access for an endpoint.

    Usage:
        @router.get("/venues/{venue_id}/orders")
        @require_venue_access("venue_id")
        async def get_venue_orders(venue_id: int, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not is_enabled("STRICT_TENANT_ISOLATION"):
                return await func(*args, **kwargs)

            current_user = kwargs.get("current_user")
            target_venue_id = kwargs.get(venue_id_param)

            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            user_venue_id = getattr(current_user, "venue_id", None)

            if user_venue_id and target_venue_id and user_venue_id != target_venue_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this venue"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


class RBACMiddleware:
    """
    RBAC Middleware for automatic permission checking.

    Can be used to enforce permissions at middleware level
    based on URL patterns.
    """

    # URL pattern to required permissions
    ROUTE_PERMISSIONS: Dict[str, List[Permission]] = {
        "/api/v1/orders": [Permission.ORDER_VIEW],
        "/api/v1/orders/create": [Permission.ORDER_CREATE],
        "/api/v1/payments": [Permission.PAYMENT_PROCESS],
        "/api/v1/kitchen": [Permission.KITCHEN_VIEW],
        "/api/v1/staff": [Permission.STAFF_VIEW],
        "/api/v1/reports": [Permission.REPORTS_VIEW],
        "/api/v1/settings": [Permission.SETTINGS_VIEW],
    }

    @classmethod
    def check_route_permission(
        cls,
        path: str,
        user_role: str,
    ) -> bool:
        """Check if role can access route."""
        if not RBACPolicy.is_active():
            return True

        for route_pattern, permissions in cls.ROUTE_PERMISSIONS.items():
            if path.startswith(route_pattern):
                return RBACPolicy.has_any_permission(user_role, permissions)

        return True  # Allow routes not in mapping
