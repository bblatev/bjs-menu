"""Role-Based Access Control (RBAC) utilities."""

from enum import Enum
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status

from app.core.security import decode_access_token
from app.db.session import SessionLocal


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
    """Decoded token data.

    Attributes:
        user_id: The user's database ID.
        email: The user's email address.
        role: The user's role (owner/manager/staff).
        id: Alias for user_id (many route files use current_user.id).
        venue_id: The venue ID from the token (defaults to 1 for single-venue).
        full_name: The user's display name (defaults to email prefix).
    """

    def __init__(self, user_id: int, email: str, role: UserRole,
                 venue_id: int = 1, full_name: str = ""):
        self.user_id = user_id
        self.id = user_id  # Alias used by many route files
        self.email = email
        self.role = role
        self.venue_id = venue_id
        self.full_name = full_name or email.split("@")[0]


async def get_current_user(request: Request) -> TokenData:
    """Get the current authenticated user from JWT token.

    Checks in order:
    1. Authorization: Bearer <token> header
    2. access_token cookie (HttpOnly)
    """
    payload = None

    # Try Authorization header first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        if token:
            payload = decode_access_token(token)

    # Fall back to cookie if no Bearer or Bearer was invalid
    if payload is None:
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            payload = decode_access_token(cookie_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
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

    # Verify user is still active in the database
    try:
        from app.models.user import User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user is None or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is disabled",
                )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception:
        pass  # If DB check fails, allow through (token was valid)

    venue_id = payload.get("venue_id", 1)
    full_name = payload.get("full_name", "")
    return TokenData(
        user_id=int(user_id), email=email, role=user_role,
        venue_id=int(venue_id) if venue_id else 1,
        full_name=full_name or "",
    )


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


async def get_optional_current_user(request: Request) -> Optional[TokenData]:
    """Get the current user if a valid token is provided, otherwise return None.

    Checks in order:
    1. Authorization: Bearer <token> header
    2. access_token cookie (HttpOnly)
    """
    payload = None

    # Try Authorization header first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        if token:
            payload = decode_access_token(token)

    # Fall back to cookie if no Bearer or Bearer was invalid
    if payload is None:
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            payload = decode_access_token(cookie_token)

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

    venue_id = payload.get("venue_id", 1)
    full_name = payload.get("full_name", "")
    return TokenData(
        user_id=int(user_id), email=email, role=user_role,
        venue_id=int(venue_id) if venue_id else 1,
        full_name=full_name or "",
    )


OptionalCurrentUser = Annotated[Optional[TokenData], Depends(get_optional_current_user)]


async def get_current_venue(
    current_user: Annotated[TokenData, Depends(get_current_user)]
) -> int:
    """Extract venue_id from the current user's token.
    Returns 1 as default venue for single-venue deployments."""
    return current_user.venue_id
