"""Roles management API routes."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.operations import AppSetting
from app.core.rbac import CurrentUser

router = APIRouter()

ROLE_CATEGORY = "role"


# --------------- Pydantic Schemas ---------------

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class RoleOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    updated_at: Optional[str] = None


# --------------- Helpers ---------------

def _role_row_to_dict(row: AppSetting) -> Dict[str, Any]:
    """Convert an AppSetting row (category='role') to a role response dict."""
    value = row.value if isinstance(row.value, dict) else {}
    return {
        "id": str(row.id),
        "name": row.key,
        "description": value.get("description"),
        "permissions": value.get("permissions", []),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


# --------------- Endpoints ---------------

@router.get("/")
async def get_roles(db: DbSession):
    """Get all user roles."""
    rows = (
        db.query(AppSetting)
        .filter(AppSetting.category == ROLE_CATEGORY)
        .order_by(AppSetting.id)
        .all()
    )
    return {"roles": [_role_row_to_dict(r) for r in rows]}


@router.get("/{role_name}")
async def get_role(role_name: str, db: DbSession):
    """Get a single role by name."""
    row = (
        db.query(AppSetting)
        .filter(AppSetting.category == ROLE_CATEGORY, AppSetting.key == role_name)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found",
        )
    return _role_row_to_dict(row)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_role(payload: RoleCreate, db: DbSession, current_user: CurrentUser):
    """Create a new role."""
    existing = (
        db.query(AppSetting)
        .filter(AppSetting.category == ROLE_CATEGORY, AppSetting.key == payload.name)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{payload.name}' already exists",
        )

    value = {
        "description": payload.description,
        "permissions": payload.permissions or [],
    }
    row = AppSetting(
        category=ROLE_CATEGORY,
        key=payload.name,
        value=value,
        updated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _role_row_to_dict(row)


@router.put("/{role_name}")
async def update_role(role_name: str, payload: RoleUpdate, db: DbSession, current_user: CurrentUser):
    """Update an existing role."""
    row = (
        db.query(AppSetting)
        .filter(AppSetting.category == ROLE_CATEGORY, AppSetting.key == role_name)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found",
        )

    current_value = row.value if isinstance(row.value, dict) else {}

    if payload.description is not None:
        current_value["description"] = payload.description
    if payload.permissions is not None:
        current_value["permissions"] = payload.permissions

    row.value = current_value
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _role_row_to_dict(row)


@router.delete("/{role_name}", status_code=status.HTTP_200_OK)
async def delete_role(role_name: str, db: DbSession, current_user: CurrentUser):
    """Delete a role."""
    row = (
        db.query(AppSetting)
        .filter(AppSetting.category == ROLE_CATEGORY, AppSetting.key == role_name)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found",
        )
    db.delete(row)
    db.commit()
    return {"detail": f"Role '{role_name}' deleted"}
