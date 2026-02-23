"""Shift swap marketplace routes."""

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db as DbSession
from app.core.rbac import get_current_user

router = APIRouter(prefix="/staff/shift-swaps", tags=["staff", "shift-swap"])


@router.get("")
def get_available_swaps(
    request: Request,
    venue_id: int = 1,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Get available shift swaps."""
    from app.services.shift_swap_service import ShiftSwapService
    return ShiftSwapService.get_available_swaps(db, venue_id, current_user.id)


@router.post("")
def request_swap(
    request: Request,
    data: dict,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Create a shift swap request."""
    from app.services.shift_swap_service import ShiftSwapService
    return ShiftSwapService.request_swap(
        db,
        venue_id=data.get("venue_id", 1),
        staff_id=current_user.id,
        shift_id=data["shift_id"],
        reason=data.get("reason", ""),
    )


@router.put("/{swap_id}/accept")
def accept_swap(
    request: Request,
    swap_id: int,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Accept a shift swap."""
    from app.services.shift_swap_service import ShiftSwapService
    result = ShiftSwapService.accept_swap(db, swap_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Swap not found")
    return result


@router.put("/{swap_id}/approve")
def approve_swap(
    request: Request,
    swap_id: int,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Manager approves a shift swap."""
    from app.services.shift_swap_service import ShiftSwapService
    result = ShiftSwapService.approve_swap(db, swap_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Swap not found")
    return result
