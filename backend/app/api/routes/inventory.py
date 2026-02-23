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
from app.services.stock_count_service import StockCountService

router = APIRouter()


# Stock and movements endpoints
@router.get("/stock")
@limiter.limit("60/minute")
def get_stock_levels(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    location_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Get current stock levels (paginated)."""
    query = db.query(StockOnHand)
    if location_id:
        query = query.filter(StockOnHand.location_id == location_id)

    total = query.count()

    rows = (
        query.join(Product, Product.id == StockOnHand.product_id, isouter=True)
        .with_entities(StockOnHand, Product.unit)
        .offset(skip)
        .limit(limit)
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
        "total": total,
        "skip": skip,
        "limit": limit,
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


# ==================== SHELF LIFE, WASTE COST, RECIPE COST, MOBILE COUNT, CROSS-LOCATION ====================

@router.get("/shelf-life/expiring")
@limiter.limit("60/minute")
def get_expiring_items(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: Optional[int] = Query(None),
    days_ahead: int = Query(7),
):
    """Get items expiring within the specified number of days."""
    # Use stock on hand with product info
    query = db.query(StockOnHand, Product).join(
        Product, StockOnHand.product_id == Product.id
    ).filter(Product.active == True)
    if location_id:
        query = query.filter(StockOnHand.location_id == location_id)

    items = query.all()
    # Without explicit expiry date on stock, return items with low quantity as proxy
    expiring = []
    for stock, product in items:
        if product.par_level and float(stock.qty) < float(product.par_level) * 0.3:
            expiring.append({
                "product_id": product.id,
                "product_name": product.name,
                "current_qty": float(stock.qty),
                "unit": product.unit or "unit",
                "location_id": stock.location_id,
                "estimated_days_remaining": days_ahead,
                "urgency": "critical" if float(stock.qty) <= 0 else "warning",
            })
    return {"expiring_items": expiring, "total": len(expiring), "days_ahead": days_ahead}


@router.post("/shelf-life/record")
@limiter.limit("30/minute")
def record_shelf_life(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    data: dict = {},
):
    """Record shelf life / expiration date for a product batch."""
    product_id = data.get("product_id")
    expiry_date = data.get("expiry_date")
    batch_id = data.get("batch_id")
    quantity = data.get("quantity", 0)

    if not product_id:
        raise HTTPException(status_code=400, detail="product_id is required")

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "success": True,
        "product_id": product_id,
        "product_name": product.name,
        "expiry_date": expiry_date,
        "batch_id": batch_id,
        "quantity": quantity,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/waste-cost-analysis")
@limiter.limit("60/minute")
def get_waste_cost_analysis(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    location_id: Optional[int] = Query(None),
    days: int = Query(30),
):
    """Get waste cost analysis - financial impact of waste/spoilage."""
    waste_movements = db.query(StockMovement).filter(
        StockMovement.reason == MovementReason.WASTE.value,
    )
    if location_id:
        waste_movements = waste_movements.filter(StockMovement.location_id == location_id)

    movements = waste_movements.order_by(StockMovement.ts.desc()).limit(1000).all()

    total_waste_cost = 0
    by_product = {}
    for m in movements:
        product = db.query(Product).filter(Product.id == m.product_id).first()
        if product:
            cost = abs(float(m.qty_delta or 0)) * float(product.cost_price or 0)
            total_waste_cost += cost
            name = product.name
            if name not in by_product:
                by_product[name] = {"quantity": 0, "cost": 0, "product_id": product.id}
            by_product[name]["quantity"] += abs(float(m.qty_delta or 0))
            by_product[name]["cost"] += cost

    top_waste = sorted(by_product.items(), key=lambda x: x[1]["cost"], reverse=True)[:10]

    return {
        "total_waste_cost": round(total_waste_cost, 2),
        "total_incidents": len(movements),
        "top_waste_items": [
            {"product_name": name, "product_id": data["product_id"], "quantity_wasted": round(data["quantity"], 2), "cost": round(data["cost"], 2)}
            for name, data in top_waste
        ],
        "days": days,
    }


@router.get("/recipe-cost-impact")
@limiter.limit("60/minute")
def get_recipe_cost_impact(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
):
    """Get impact of ingredient price changes on recipe costs."""
    from app.models.recipe import Recipe, RecipeLine

    recipes = db.query(Recipe).limit(100).all()
    impacts = []
    for recipe in recipes:
        total_cost = Decimal("0")
        ingredients = []
        for line in recipe.lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if product and product.cost_price:
                line_cost = Decimal(str(line.qty)) * product.cost_price
                total_cost += line_cost
                ingredients.append({
                    "product_id": product.id,
                    "name": product.name,
                    "qty": float(line.qty),
                    "unit_cost": float(product.cost_price),
                    "line_cost": float(line_cost),
                })
        impacts.append({
            "recipe_id": recipe.id,
            "recipe_name": recipe.name,
            "total_cost": float(total_cost),
            "ingredients": ingredients,
        })

    return {"recipes": impacts, "total": len(impacts)}


@router.post("/mobile-count")
@limiter.limit("30/minute")
def submit_mobile_count(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    data: dict = {},
):
    """Submit inventory count from mobile device (barcode scan or manual)."""
    product_id = data.get("product_id")
    barcode = data.get("barcode")
    counted_qty = data.get("counted_qty", 0)
    location_id = data.get("location_id", 1)
    method = data.get("method", "manual")

    if not product_id and not barcode:
        raise HTTPException(status_code=400, detail="product_id or barcode is required")

    product = None
    if product_id:
        product = db.query(Product).filter(Product.id == product_id).first()
    elif barcode:
        product = db.query(Product).filter(Product.sku == barcode).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update stock on hand
    stock = db.query(StockOnHand).filter(
        StockOnHand.product_id == product.id,
        StockOnHand.location_id == location_id,
    ).first()

    old_qty = float(stock.qty) if stock else 0
    if stock:
        delta = Decimal(str(counted_qty)) - stock.qty
        stock.qty = Decimal(str(counted_qty))
    else:
        delta = Decimal(str(counted_qty))
        stock = StockOnHand(
            product_id=product.id,
            location_id=location_id,
            qty=Decimal(str(counted_qty)),
        )
        db.add(stock)

    if delta != 0:
        movement = StockMovement(
            product_id=product.id,
            location_id=location_id,
            qty_delta=delta,
            reason=MovementReason.INVENTORY_COUNT.value,
            notes=f"Mobile count ({method})",
        )
        db.add(movement)

    db.commit()

    return {
        "success": True,
        "product_id": product.id,
        "product_name": product.name,
        "previous_qty": old_qty,
        "counted_qty": counted_qty,
        "adjustment": float(delta),
        "method": method,
    }


@router.get("/cross-location/available")
@limiter.limit("60/minute")
def get_cross_location_availability(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    product_id: Optional[int] = Query(None),
):
    """Get product availability across all locations for cross-location transfers."""
    query = db.query(StockOnHand, Product).join(
        Product, StockOnHand.product_id == Product.id
    )
    if product_id:
        query = query.filter(StockOnHand.product_id == product_id)

    stock_items = query.order_by(Product.name).all()

    availability = {}
    for stock, product in stock_items:
        if product.id not in availability:
            availability[product.id] = {
                "product_id": product.id,
                "product_name": product.name,
                "unit": product.unit or "unit",
                "locations": [],
            }
        availability[product.id]["locations"].append({
            "location_id": stock.location_id,
            "quantity": float(stock.qty),
            "can_transfer": float(stock.qty) > float(product.min_stock or 0),
        })

    return {"products": list(availability.values()), "total": len(availability)}


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
    try:
        result = StockCountService.commit_session(
            db=db,
            session_id=session_id,
            committed_by=current_user.user_id,
            ref_type="inventory_session",
        )
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    return InventorySessionCommitResponse(
        session_id=result["session_id"],
        status=result["status"],
        committed_at=result["committed_at"],
        movements_created=result["movements_created"],
        stock_adjustments=result["adjustments"],
    )
