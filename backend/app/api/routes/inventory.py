"""Inventory session and line routes."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Request, status

logger = logging.getLogger("inventory")

from app.core.rbac import CurrentUser, OptionalCurrentUser
from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.models.inventory import CountMethod, InventoryLine, InventorySession, SessionStatus
from app.models.location import Location
from app.models.product import Product
from app.models.stock import MovementReason, StockMovement, StockOnHand
from app.schemas.inventory import (
    InventoryLineCreate,
    InventoryLineResponse,
    InventoryLineUpdate,
    InventorySessionCommitResponse,
    InventorySessionCreate,
    InventorySessionResponse,
)

router = APIRouter()


# Stock and movements endpoints
@router.get("/stock")
@limiter.limit("60/minute")
def get_stock_levels(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    location_id: Optional[int] = Query(None),
):
    """Get current stock levels."""
    query = db.query(StockOnHand)
    if location_id:
        query = query.filter(StockOnHand.location_id == location_id)
    rows = (
        query.join(Product, Product.id == StockOnHand.product_id, isouter=True)
        .with_entities(StockOnHand, Product.unit)
        .all()
    )
    results = []
    for s, product_unit in rows:
        results.append({
            "id": s.id,
            "product_id": s.product_id,
            "location_id": s.location_id,
            "quantity": float(s.qty) if s.qty else 0,
            "unit": product_unit or "unit",
            "last_updated": s.updated_at.isoformat() if s.updated_at else None,
        })
    return {
        "stock": results,
        "total": len(results),
    }


@router.get("/movements")
@limiter.limit("60/minute")
def get_stock_movements(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    location_id: Optional[int] = Query(None),
    limit: int = Query(50, le=500),
):
    """Get recent stock movements."""
    query = db.query(StockMovement)
    if location_id:
        query = query.filter(StockMovement.location_id == location_id)
    movements = query.order_by(StockMovement.ts.desc()).limit(limit).all()
    return {
        "movements": [
            {
                "id": m.id,
                "product_id": m.product_id,
                "location_id": m.location_id,
                "qty_delta": float(m.qty_delta) if m.qty_delta else 0,
                "reason": m.reason,
                "ref_type": m.ref_type,
                "ref_id": m.ref_id,
                "notes": m.notes,
                "timestamp": m.ts.isoformat() if m.ts else None,
            }
            for m in movements
        ],
        "total": len(movements),
    }


@router.get("/sessions", response_model=List[InventorySessionResponse])
@limiter.limit("60/minute")
def list_sessions(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: Optional[int] = Query(None),
    status_filter: Optional[SessionStatus] = Query(None, alias="status"),
):
    """List inventory sessions with optional filters."""
    query = db.query(InventorySession)
    if location_id:
        query = query.filter(InventorySession.location_id == location_id)
    if status_filter:
        query = query.filter(InventorySession.status == status_filter)
    return query.order_by(InventorySession.started_at.desc()).all()


@router.get("/sessions/{session_id}", response_model=InventorySessionResponse)
@limiter.limit("60/minute")
def get_session(request: Request, session_id: int, db: DbSession, current_user: CurrentUser):
    """Get a specific inventory session with lines."""
    session = db.query(InventorySession).filter(InventorySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.post("/sessions", response_model=InventorySessionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_session(request: Request, session_data: InventorySessionCreate, db: DbSession, current_user: CurrentUser):
    """Create a new inventory session."""
    # Verify location exists
    location = db.query(Location).filter(Location.id == session_data.location_id).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    session = InventorySession(
        location_id=session_data.location_id,
        notes=session_data.notes,
        created_by=current_user.user_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(f"Inventory session created: ID={session.id}, location={session_data.location_id}, user={current_user.user_id}")
    return session


@router.post("/sessions/{session_id}/lines", response_model=InventoryLineResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def add_line(request: Request, session_id: int, line_data: InventoryLineCreate, db: DbSession, current_user: CurrentUser):
    """Add a line to an inventory session."""
    session = db.query(InventorySession).filter(InventorySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status != SessionStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add lines to a non-draft session",
        )

    # Verify product exists
    product = db.query(Product).filter(Product.id == line_data.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Check if line for this product already exists in session
    existing_line = (
        db.query(InventoryLine)
        .filter(InventoryLine.session_id == session_id, InventoryLine.product_id == line_data.product_id)
        .first()
    )

    if existing_line:
        # Update existing line (add to count)
        existing_line.counted_qty += line_data.counted_qty
        existing_line.method = line_data.method
        existing_line.confidence = line_data.confidence
        existing_line.counted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing_line)
        return existing_line

    # Create new line
    line = InventoryLine(
        session_id=session_id,
        product_id=line_data.product_id,
        counted_qty=line_data.counted_qty,
        method=line_data.method,
        confidence=line_data.confidence,
        photo_id=line_data.photo_id,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


@router.put("/sessions/{session_id}/lines/{line_id}", response_model=InventoryLineResponse)
@limiter.limit("30/minute")
def update_line(
    request: Request,
    session_id: int,
    line_id: int,
    line_update: InventoryLineUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Update a line in an inventory session."""
    session = db.query(InventorySession).filter(InventorySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status != SessionStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update lines in a non-draft session",
        )

    line = (
        db.query(InventoryLine)
        .filter(InventoryLine.id == line_id, InventoryLine.session_id == session_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line not found")

    update_data = line_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(line, field, value)
    line.counted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(line)
    return line


@router.delete("/sessions/{session_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
def delete_line(request: Request, session_id: int, line_id: int, db: DbSession, current_user: CurrentUser):
    """Delete a line from an inventory session."""
    session = db.query(InventorySession).filter(InventorySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status != SessionStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete lines from a non-draft session",
        )

    line = (
        db.query(InventoryLine)
        .filter(InventoryLine.id == line_id, InventoryLine.session_id == session_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line not found")

    db.delete(line)
    db.commit()


@router.post("/sessions/{session_id}/commit", response_model=InventorySessionCommitResponse)
@limiter.limit("30/minute")
def commit_session(request: Request, session_id: int, db: DbSession, current_user: CurrentUser):
    """
    Commit an inventory session.

    This will:
    1. Calculate the difference between counted and current stock
    2. Create stock movements for the adjustments
    3. Update stock on hand
    4. Mark the session as committed
    """
    session = db.query(InventorySession).filter(InventorySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.status != SessionStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not in draft status",
        )
    if not session.lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has no lines to commit",
        )

    movements_created = 0
    adjustments = []

    for line in session.lines:
        # Get current stock on hand
        stock = (
            db.query(StockOnHand)
            .filter(
                StockOnHand.product_id == line.product_id,
                StockOnHand.location_id == session.location_id,
            )
            .first()
        )

        current_qty = stock.qty if stock else Decimal("0")
        delta = line.counted_qty - current_qty

        if delta != 0:
            # Create stock movement
            movement = StockMovement(
                product_id=line.product_id,
                location_id=session.location_id,
                qty_delta=delta,
                reason=MovementReason.INVENTORY_COUNT.value,
                ref_type="inventory_session",
                ref_id=session.id,
                created_by=current_user.user_id,
            )
            db.add(movement)
            movements_created += 1

            # Update or create stock on hand
            if stock:
                stock.qty = line.counted_qty
            else:
                stock = StockOnHand(
                    product_id=line.product_id,
                    location_id=session.location_id,
                    qty=line.counted_qty,
                )
                db.add(stock)

            adjustments.append({
                "product_id": line.product_id,
                "previous_qty": float(current_qty),
                "counted_qty": float(line.counted_qty),
                "delta": float(delta),
            })

    # Mark session as committed
    session.status = SessionStatus.COMMITTED
    session.committed_at = datetime.now(timezone.utc)

    db.commit()

    logger.info(
        f"Inventory session committed: ID={session.id}, location={session.location_id}, "
        f"movements={movements_created}, user={current_user.user_id}"
    )
    if adjustments:
        logger.info(f"Stock adjustments for session {session.id}: {adjustments}")

    return InventorySessionCommitResponse(
        session_id=session.id,
        status=session.status,
        committed_at=session.committed_at,
        movements_created=movements_created,
        stock_adjustments=adjustments,
    )
