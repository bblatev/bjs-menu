"""Promotions routes."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.db.session import DbSession
from app.models.operations import Promotion as PromotionModel
from app.core.rbac import CurrentUser
from app.core.rate_limit import limiter

router = APIRouter()


# ---- Pydantic schemas ----

class PromotionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str = "percentage"  # percentage, fixed, bogo, combo
    value: Optional[float] = None
    min_order_amount: Optional[float] = None
    max_discount: Optional[float] = None
    code: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    active: bool = True
    usage_limit: Optional[int] = None
    applicable_items: Optional[list] = None


class PromotionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    value: Optional[float] = None
    min_order_amount: Optional[float] = None
    max_discount: Optional[float] = None
    code: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    active: Optional[bool] = None
    usage_limit: Optional[int] = None
    applicable_items: Optional[list] = None


# ---- Helper ----

def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-format datetime string, returning None when absent."""
    if not value:
        return None
    return datetime.fromisoformat(value)


def _serialize_promotion(p: PromotionModel) -> dict:
    """Convert a Promotion ORM instance to a JSON-friendly dict."""
    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "type": p.type,
        "value": float(p.value) if p.value is not None else None,
        "min_order_amount": float(p.min_order_amount) if p.min_order_amount is not None else None,
        "max_discount": float(p.max_discount) if p.max_discount is not None else None,
        "code": p.code,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "end_date": p.end_date.isoformat() if p.end_date else None,
        "active": p.active,
        "usage_count": p.usage_count or 0,
        "usage_limit": p.usage_limit,
        "applicable_items": p.applicable_items,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


# ---- Endpoints ----

@router.get("/")
@limiter.limit("60/minute")
async def get_promotions(
    request: Request,
    db: DbSession,
    active: Optional[bool] = None,
):
    """Get active promotions."""
    stmt = select(PromotionModel).order_by(PromotionModel.created_at.desc())
    if active is not None:
        stmt = stmt.where(PromotionModel.active == active)
    results = db.execute(stmt).scalars().all()
    return [_serialize_promotion(p) for p in results]


@router.get("/{promotion_id}")
@limiter.limit("60/minute")
async def get_promotion(request: Request, promotion_id: str, db: DbSession):
    """Get a specific promotion."""
    promo = db.get(PromotionModel, int(promotion_id))
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return _serialize_promotion(promo)


@router.post("/")
@limiter.limit("30/minute")
async def create_promotion(request: Request, data: dict, db: DbSession):
    """Create a promotion."""
    promo = PromotionModel(
        name=data.get("name", ""),
        description=data.get("description"),
        type=data.get("type", "percentage"),
        value=Decimal(str(data["value"])) if data.get("value") is not None else None,
        min_order_amount=Decimal(str(data["min_order_amount"])) if data.get("min_order_amount") is not None else None,
        max_discount=Decimal(str(data["max_discount"])) if data.get("max_discount") is not None else None,
        code=data.get("code"),
        start_date=_parse_dt(data.get("start_date")),
        end_date=_parse_dt(data.get("end_date")),
        active=data.get("active", True),
        usage_limit=data.get("usage_limit"),
        applicable_items=data.get("applicable_items"),
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return {"success": True, "id": str(promo.id)}


@router.put("/{promotion_id}")
@limiter.limit("30/minute")
async def update_promotion(request: Request, promotion_id: str, data: dict, db: DbSession):
    """Update a promotion."""
    promo = db.get(PromotionModel, int(promotion_id))
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")

    updatable_fields = {
        "name", "description", "type", "code", "active",
        "usage_limit", "applicable_items",
    }
    decimal_fields = {"value", "min_order_amount", "max_discount"}
    datetime_fields = {"start_date", "end_date"}

    for field in updatable_fields:
        if field in data:
            setattr(promo, field, data[field])

    for field in decimal_fields:
        if field in data:
            setattr(promo, field, Decimal(str(data[field])) if data[field] is not None else None)

    for field in datetime_fields:
        if field in data:
            setattr(promo, field, _parse_dt(data[field]))

    db.commit()
    db.refresh(promo)
    return {"success": True}


@router.patch("/{promotion_id}/toggle-active")
@limiter.limit("30/minute")
async def toggle_promotion_active(request: Request, promotion_id: str, db: DbSession):
    """Toggle a promotion's active status."""
    promo = db.get(PromotionModel, int(promotion_id))
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")

    promo.active = not promo.active
    db.commit()
    db.refresh(promo)
    return {"success": True, "id": str(promo.id), "active": promo.active}


@router.delete("/{promotion_id}")
@limiter.limit("30/minute")
async def delete_promotion(request: Request, promotion_id: str, db: DbSession):
    """Delete a promotion."""
    promo = db.get(PromotionModel, int(promotion_id))
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion not found")

    db.delete(promo)
    db.commit()
    return {"success": True}
