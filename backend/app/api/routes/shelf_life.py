"""Shelf life tracking and expiry management routes."""

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db as DbSession
from app.core.rbac import get_current_user

router = APIRouter(prefix="/inventory/shelf-life", tags=["inventory", "shelf-life"])


@router.get("")
def get_shelf_life_items(
    request: Request,
    venue_id: int = 1,
    status: str = None,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Get all shelf life tracked items."""
    from app.services.shelf_life_service import ShelfLifeService
    return ShelfLifeService.get_shelf_life_items(db, venue_id, status)


@router.get("/expiring-soon")
def get_expiring_soon(
    request: Request,
    venue_id: int = 1,
    days: int = 3,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Get items expiring within N days."""
    from app.services.shelf_life_service import ShelfLifeService
    return ShelfLifeService.get_expiring_soon(db, venue_id, days)


@router.get("/waste-prediction")
def get_waste_prediction(
    request: Request,
    venue_id: int = 1,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Get waste prediction based on expiring items."""
    from app.services.shelf_life_service import ShelfLifeService
    return ShelfLifeService.get_waste_prediction(db, venue_id)


@router.post("")
def add_shelf_life_item(
    request: Request,
    data: dict,
    venue_id: int = 1,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Add a new shelf life tracked item."""
    from app.services.shelf_life_service import ShelfLifeService
    return ShelfLifeService.add_item(db, venue_id, data)


@router.post("/{item_id}/discard")
def discard_item(
    request: Request,
    item_id: int,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Mark an item as discarded."""
    from app.services.shelf_life_service import ShelfLifeService
    result = ShelfLifeService.discard_item(db, item_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result
