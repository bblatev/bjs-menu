"""Role-Based Access Control (RBAC) utilities."""

from enum import Enum
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    """User roles for RBAC."""

    OWNER = "owner"
    MANAGER = "manager"
    STAFF = "staff"


# Role hierarchy: owner > manager > staff
ROLE_HIERARCHY = {
    UserRole.OWNER: 3,
    UserRole.MANAGER: 2,
    UserRole.STAFF: 1,
}


class TokenData:
    """Decoded token data."""

    def __init__(self, user_id: int, email: str, role: UserRole):
        self.user_id = user_id
        self.email = email
        self.role = role


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> TokenData:
    """Get the current authenticated user from JWT token."""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    email = payload.get("email")
    role = payload.get("role")

    if user_id is None or email is None or role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_role = UserRole(role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid role in token",
        )

    return TokenData(user_id=int(user_id), email=email, role=user_role)


def require_role(minimum_role: UserRole):
    """Dependency to require a minimum role level."""

    async def role_checker(
        current_user: Annotated[TokenData, Depends(get_current_user)]
    ) -> TokenData:
        user_level = ROLE_HIERARCHY.get(current_user.role, 0)
        required_level = ROLE_HIERARCHY.get(minimum_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role {minimum_role.value} or higher",
            )
        return current_user

    return role_checker


# Common role dependencies
RequireOwner = Annotated[TokenData, Depends(require_role(UserRole.OWNER))]
RequireManager = Annotated[TokenData, Depends(require_role(UserRole.MANAGER))]
RequireStaff = Annotated[TokenData, Depends(require_role(UserRole.STAFF))]
CurrentUser = Annotated[TokenData, Depends(get_current_user)]


async def get_optional_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(optional_security)] = None,
) -> Optional[TokenData]:
    """Get the current user if a valid token is provided, otherwise return None."""
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        return None

    user_id = payload.get("sub")
    email = payload.get("email")
    role = payload.get("role")

    if user_id is None or email is None or role is None:
        return None

    try:
        user_role = UserRole(role)
    except ValueError:
        return None

    return TokenData(user_id=int(user_id), email=email, role=user_role)


OptionalCurrentUser = Annotated[Optional[TokenData], Depends(get_optional_current_user)]


async def get_current_venue(
    current_user: Annotated[TokenData, Depends(get_current_user)]
) -> int:
    """Extract venue_id from the current user's token.
    Returns 1 as default venue for single-venue deployments."""
    return getattr(current_user, 'venue_id', 1)
