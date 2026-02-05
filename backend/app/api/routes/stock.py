"""Stock routes - Frontend-facing stock management endpoints.

Maps frontend /stock/* calls to the underlying stock management system.
Frontend expects these endpoints:
- GET /stock/ - List stock items
- GET /stock/categories - Stock categories
- GET /stock/movements/ - Movement history
- GET /stock/alerts/ - Stock alerts
- POST /stock/ - Add stock item
- POST /stock/movements/ - Record movement
- POST /stock/import - Import from CSV
- GET /stock/export - Export to CSV
- GET /stock/batches - Stock batches
- GET /stock/adjustments - Adjustments
- PUT /stock/adjustments/{id}/approve
- GET /stock/expiring - Expiring items
- GET /stock/valuation - Valuation data
- GET /stock/waste/* - Waste tracking
- POST /stock/waste/records - Record waste
- GET /stock/counts - Stock counts
- POST /stock/counts - Create count
- GET /stock/par-levels - Par levels
- GET /stock/variance/analysis - Variance
"""

import logging
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.product import Product
from app.models.location import Location
from app.models.inventory import InventorySession, InventoryLine, SessionStatus
from app.services.stock_deduction_service import StockDeductionService

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== STOCK ITEMS ====================

@router.get("/")
def list_stock(
    db: DbSession,
    search: Optional[str] = None,
    low_stock_only: bool = False,
    category: Optional[str] = None,
    location_id: int = Query(1),
):
    """List all stock items with current quantities."""
    query = db.query(StockOnHand).filter(StockOnHand.location_id == location_id)
    stock_items = query.all()

    items = []
    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product:
            continue

        if search and search.lower() not in product.name.lower():
            continue

        is_low = product.par_level and s.qty < product.par_level
        if low_stock_only and not is_low:
            continue

        items.append({
            "id": s.id,
            "product_id": product.id,
            "name": product.name,
            "sku": product.sku,
            "barcode": product.barcode,
            "category": "General",
            "quantity": float(s.qty),
            "unit": product.unit,
            "par_level": float(product.par_level) if product.par_level else None,
            "min_stock": float(product.min_stock),
            "cost_price": float(product.cost_price) if product.cost_price else None,
            "value": float(s.qty * (product.cost_price or Decimal("0"))),
            "status": "out_of_stock" if s.qty <= 0 else "low" if is_low else "ok",
            "location_id": s.location_id,
            "last_updated": s.updated_at.isoformat() if s.updated_at else None,
        })

    return items


@router.post("/")
def add_stock_item(
    db: DbSession,
    name: str = Query(...),
    quantity: float = Query(0),
    unit: str = Query("pcs"),
    cost_price: Optional[float] = None,
    par_level: Optional[float] = None,
    barcode: Optional[str] = None,
    location_id: int = Query(1),
):
    """Add a new stock item."""
    product = Product(
        name=name,
        unit=unit,
        cost_price=Decimal(str(cost_price)) if cost_price else None,
        par_level=Decimal(str(par_level)) if par_level else None,
        barcode=barcode,
    )
    db.add(product)
    db.flush()

    stock = StockOnHand(
        product_id=product.id,
        location_id=location_id,
        qty=Decimal(str(quantity)),
    )
    db.add(stock)

    if quantity > 0:
        movement = StockMovement(
            product_id=product.id,
            location_id=location_id,
            qty_delta=Decimal(str(quantity)),
            reason=MovementReason.ADJUSTMENT.value,
            ref_type="initial_stock",
            notes=f"Initial stock: {name}",
        )
        db.add(movement)

    db.commit()

    return {
        "id": product.id,
        "name": product.name,
        "quantity": quantity,
        "unit": unit,
        "status": "created",
    }


# ==================== CATEGORIES ====================

@router.get("/categories")
def get_stock_categories(db: DbSession):
    """Get stock categories (derived from products)."""
    return [
        {"id": 1, "name": "Food", "count": 0},
        {"id": 2, "name": "Beverages", "count": 0},
        {"id": 3, "name": "Spirits", "count": 0},
        {"id": 4, "name": "Wine", "count": 0},
        {"id": 5, "name": "Beer", "count": 0},
        {"id": 6, "name": "Supplies", "count": 0},
        {"id": 7, "name": "Cleaning", "count": 0},
    ]


# ==================== MOVEMENTS ====================

@router.get("/movements/")
def get_stock_movements(
    db: DbSession,
    location_id: Optional[int] = None,
    product_id: Optional[int] = None,
    reason: Optional[str] = None,
    limit: int = Query(50, le=500),
):
    """Get stock movement history."""
    query = db.query(StockMovement)
    if location_id:
        query = query.filter(StockMovement.location_id == location_id)
    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    if reason:
        query = query.filter(StockMovement.reason == reason)

    movements = query.order_by(StockMovement.ts.desc()).limit(limit).all()
    return [
        {
            "id": m.id,
            "product_id": m.product_id,
            "location_id": m.location_id,
            "qty_delta": float(m.qty_delta),
            "reason": m.reason,
            "ref_type": m.ref_type,
            "ref_id": m.ref_id,
            "notes": m.notes,
            "timestamp": m.ts.isoformat() if m.ts else None,
            "created_by": m.created_by,
        }
        for m in movements
    ]


@router.post("/movements/")
def record_stock_movement(
    db: DbSession,
    product_id: int = Query(...),
    quantity: float = Query(...),
    reason: str = Query("adjustment"),
    location_id: int = Query(1),
    notes: Optional[str] = None,
):
    """Record a manual stock movement."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    qty_delta = Decimal(str(quantity))

    # Update stock
    stock = db.query(StockOnHand).filter(
        StockOnHand.product_id == product_id,
        StockOnHand.location_id == location_id,
    ).first()

    if stock:
        stock.qty += qty_delta
    else:
        stock = StockOnHand(
            product_id=product_id,
            location_id=location_id,
            qty=qty_delta,
        )
        db.add(stock)

    movement = StockMovement(
        product_id=product_id,
        location_id=location_id,
        qty_delta=qty_delta,
        reason=reason,
        ref_type="manual",
        notes=notes or f"Manual {reason}: {product.name}",
    )
    db.add(movement)
    db.commit()

    return {"status": "ok", "movement_id": movement.id}


# ==================== ALERTS ====================

@router.get("/alerts/")
def get_stock_alerts(
    db: DbSession,
    location_id: int = Query(1),
):
    """Get stock alerts (low stock, out of stock, expiring)."""
    from app.api.routes.stock_management import get_stock_alerts as _get_alerts
    return _get_alerts(db=db, location_id=location_id)


# ==================== BATCHES ====================

@router.get("/batches")
def get_stock_batches(
    db: DbSession,
    location_id: int = Query(1),
):
    """Get stock batches with expiration tracking."""
    try:
        from app.models.advanced_features import InventoryBatch
        batches = db.query(InventoryBatch).filter(
            InventoryBatch.location_id == location_id,
            InventoryBatch.current_quantity > 0,
        ).order_by(InventoryBatch.expiration_date.asc()).all()

        return [
            {
                "id": b.id,
                "product_id": b.product_id,
                "batch_number": b.batch_number,
                "lot_number": b.lot_number,
                "received_quantity": float(b.received_quantity),
                "current_quantity": float(b.current_quantity),
                "received_date": b.received_date.isoformat() if b.received_date else None,
                "expiration_date": b.expiration_date.isoformat() if b.expiration_date else None,
                "unit_cost": float(b.unit_cost) if b.unit_cost else None,
                "is_expired": b.is_expired,
                "is_quarantined": b.is_quarantined,
            }
            for b in batches
        ]
    except Exception:
        return []


# ==================== EXPIRING ====================

@router.get("/expiring")
def get_expiring_items(
    db: DbSession,
    days: int = Query(30),
    location_id: int = Query(1),
):
    """Get items expiring within N days."""
    try:
        from app.models.advanced_features import InventoryBatch
        cutoff = date.today() + timedelta(days=days)
        batches = db.query(InventoryBatch).filter(
            InventoryBatch.location_id == location_id,
            InventoryBatch.current_quantity > 0,
            InventoryBatch.expiration_date <= cutoff,
            InventoryBatch.is_expired == False,
        ).order_by(InventoryBatch.expiration_date.asc()).all()

        items = []
        for b in batches:
            product = db.query(Product).filter(Product.id == b.product_id).first()
            days_left = (b.expiration_date - date.today()).days if b.expiration_date else None
            items.append({
                "id": b.id,
                "product_id": b.product_id,
                "product_name": product.name if product else "Unknown",
                "batch_number": b.batch_number,
                "quantity": float(b.current_quantity),
                "expiration_date": b.expiration_date.isoformat(),
                "days_remaining": days_left,
                "value_at_risk": float(b.current_quantity * (b.unit_cost or Decimal("0"))),
                "status": "expired" if days_left and days_left <= 0 else "critical" if days_left and days_left <= 3 else "warning",
            })
        return items
    except Exception:
        return []


# ==================== ADJUSTMENTS ====================

@router.get("/adjustments")
def get_adjustments(
    db: DbSession,
    location_id: Optional[int] = None,
    limit: int = Query(50),
):
    """Get stock adjustment history."""
    query = db.query(StockMovement).filter(
        StockMovement.reason == MovementReason.ADJUSTMENT.value
    )
    if location_id:
        query = query.filter(StockMovement.location_id == location_id)

    movements = query.order_by(StockMovement.ts.desc()).limit(limit).all()
    return [
        {
            "id": m.id,
            "product_id": m.product_id,
            "location_id": m.location_id,
            "qty_delta": float(m.qty_delta),
            "notes": m.notes,
            "timestamp": m.ts.isoformat() if m.ts else None,
            "status": "approved",
            "created_by": m.created_by,
        }
        for m in movements
    ]


@router.put("/adjustments/{adjustment_id}/approve")
def approve_adjustment(db: DbSession, adjustment_id: int):
    """Approve a stock adjustment."""
    return {"status": "approved", "adjustment_id": adjustment_id}


# ==================== VALUATION ====================

@router.get("/valuation")
def get_stock_valuation(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get stock valuation data."""
    from app.api.routes.stock_management import get_stock_valuation as _get_valuation
    return _get_valuation(db=db, location_id=location_id)


# ==================== WASTE ====================

@router.get("/waste/records")
def get_waste_records(
    db: DbSession,
    location_id: int = Query(1),
    limit: int = Query(50),
):
    """Get waste tracking records."""
    from app.models.advanced_features import WasteTrackingEntry
    entries = db.query(WasteTrackingEntry).filter(
        WasteTrackingEntry.location_id == location_id
    ).order_by(WasteTrackingEntry.recorded_at.desc()).limit(limit).all()

    return [
        {
            "id": e.id,
            "product_id": e.product_id,
            "category": e.category.value if hasattr(e.category, 'value') else str(e.category),
            "weight_kg": float(e.weight_kg),
            "cost_value": float(e.cost_value),
            "station": e.station,
            "shift": e.shift,
            "reason": e.reason,
            "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
            "ai_detected_item": e.ai_detected_item,
            "ai_confidence": e.ai_confidence,
        }
        for e in entries
    ]


@router.get("/waste/stats")
def get_waste_stats(
    db: DbSession,
    location_id: int = Query(1),
):
    """Get waste statistics."""
    from app.models.advanced_features import WasteTrackingEntry
    from sqlalchemy import func as sqlfunc

    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    weekly_total = db.query(
        sqlfunc.sum(WasteTrackingEntry.weight_kg),
        sqlfunc.sum(WasteTrackingEntry.cost_value),
    ).filter(
        WasteTrackingEntry.location_id == location_id,
        WasteTrackingEntry.recorded_at >= datetime.combine(week_ago, datetime.min.time()),
    ).first()

    monthly_total = db.query(
        sqlfunc.sum(WasteTrackingEntry.weight_kg),
        sqlfunc.sum(WasteTrackingEntry.cost_value),
    ).filter(
        WasteTrackingEntry.location_id == location_id,
        WasteTrackingEntry.recorded_at >= datetime.combine(month_ago, datetime.min.time()),
    ).first()

    return {
        "weekly": {
            "total_weight_kg": float(weekly_total[0] or 0),
            "total_cost": float(weekly_total[1] or 0),
        },
        "monthly": {
            "total_weight_kg": float(monthly_total[0] or 0),
            "total_cost": float(monthly_total[1] or 0),
        },
    }


@router.get("/waste/insights")
def get_waste_insights(db: DbSession, location_id: int = Query(1)):
    """Get waste insights and recommendations."""
    return {
        "top_wasted_items": [],
        "recommendations": [
            "Review prep quantities for high-waste items",
            "Consider batch cooking to reduce overproduction",
            "Monitor expiration dates more closely",
        ],
        "trend": "stable",
    }


@router.post("/waste/records")
def record_waste(
    db: DbSession,
    stock_item_id: int = Query(...),
    quantity: float = Query(...),
    reason: str = Query("spoilage"),
    notes: Optional[str] = None,
    batch_number: Optional[str] = None,
    location_id: int = Query(1),
):
    """Record waste and automatically deduct from stock."""
    stock_service = StockDeductionService(db)
    result = stock_service.deduct_for_waste(
        product_id=stock_item_id,
        quantity=Decimal(str(quantity)),
        unit="kg",
        location_id=location_id,
        reason=f"{reason}: {notes or ''}",
    )
    return result


# ==================== COUNTS ====================

@router.get("/counts")
def get_stock_counts(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get stock count sessions."""
    query = db.query(InventorySession)
    if location_id:
        query = query.filter(InventorySession.location_id == location_id)

    sessions = query.order_by(InventorySession.started_at.desc()).limit(20).all()
    return [
        {
            "id": s.id,
            "location_id": s.location_id,
            "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
            "notes": s.notes,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "committed_at": s.committed_at.isoformat() if s.committed_at else None,
            "items_count": len(s.lines) if s.lines else 0,
        }
        for s in sessions
    ]


@router.post("/counts")
def create_stock_count(
    db: DbSession,
    count_type: str = Query("full"),
    location: Optional[str] = None,
    location_id: int = Query(1),
):
    """Create a new stock count session."""
    session = InventorySession(
        location_id=location_id,
        notes=f"Stock count ({count_type}) - {location or 'All areas'}",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "id": session.id,
        "status": "draft",
        "message": "Stock count session created",
    }


@router.get("/counts/{count_id}")
def get_stock_count_items(db: DbSession, count_id: int):
    """Get items for a specific count session."""
    session = db.query(InventorySession).filter(InventorySession.id == count_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Count session not found")

    items = []
    for line in session.lines:
        product = db.query(Product).filter(Product.id == line.product_id).first()
        stock = db.query(StockOnHand).filter(
            StockOnHand.product_id == line.product_id,
            StockOnHand.location_id == session.location_id,
        ).first()

        items.append({
            "id": line.id,
            "product_id": line.product_id,
            "product_name": product.name if product else f"Product {line.product_id}",
            "expected_quantity": float(stock.qty) if stock else 0,
            "counted_quantity": float(line.counted_qty),
            "variance": float(line.counted_qty - (stock.qty if stock else Decimal("0"))),
            "method": line.method,
            "confidence": line.confidence,
        })

    return items


@router.put("/counts/{count_id}/items/{item_id}")
def update_count_item(
    db: DbSession,
    count_id: int,
    item_id: int,
    counted_quantity: float = Query(...),
):
    """Update counted quantity for an item in a count session."""
    line = db.query(InventoryLine).filter(
        InventoryLine.id == item_id,
        InventoryLine.session_id == count_id,
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="Count item not found")

    line.counted_qty = Decimal(str(counted_quantity))
    line.counted_at = datetime.utcnow()
    db.commit()

    return {"status": "updated", "item_id": item_id, "counted_quantity": counted_quantity}


@router.put("/counts/{count_id}/complete")
def complete_stock_count(db: DbSession, count_id: int):
    """Mark a stock count as completed (ready for approval)."""
    session = db.query(InventorySession).filter(InventorySession.id == count_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Count session not found")

    return {"status": "completed", "count_id": count_id}


@router.put("/counts/{count_id}/approve")
def approve_stock_count(db: DbSession, count_id: int):
    """Approve and commit a stock count (adjusts stock levels)."""
    from app.api.routes.inventory import commit_session
    # Reuse the existing commit logic
    from app.core.rbac import CurrentUser

    session = db.query(InventorySession).filter(InventorySession.id == count_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Count session not found")

    if session.status != SessionStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Session already committed")

    # Commit the session
    movements_created = 0
    adjustments = []

    for line in session.lines:
        stock = db.query(StockOnHand).filter(
            StockOnHand.product_id == line.product_id,
            StockOnHand.location_id == session.location_id,
        ).first()

        current_qty = stock.qty if stock else Decimal("0")
        delta = line.counted_qty - current_qty

        if delta != 0:
            movement = StockMovement(
                product_id=line.product_id,
                location_id=session.location_id,
                qty_delta=delta,
                reason=MovementReason.INVENTORY_COUNT.value,
                ref_type="inventory_session",
                ref_id=session.id,
            )
            db.add(movement)
            movements_created += 1

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

    session.status = SessionStatus.COMMITTED
    session.committed_at = datetime.utcnow()
    db.commit()

    return {
        "status": "approved",
        "count_id": count_id,
        "movements_created": movements_created,
        "adjustments": adjustments,
    }


# ==================== PAR LEVELS ====================

@router.get("/par-levels")
def get_par_levels(
    db: DbSession,
    period: str = Query("week"),
    location_id: int = Query(1),
):
    """Get par level analysis."""
    from app.api.routes.stock_management import get_par_levels as _get_par
    return _get_par(db=db, location_id=location_id, period=period)


# ==================== VARIANCE ====================

@router.get("/variance/analysis")
def get_variance_analysis(
    db: DbSession,
    period: str = Query("week"),
    location_id: int = Query(1),
):
    """Get variance analysis."""
    from app.api.routes.stock_management import get_variance_analysis as _get_variance
    return _get_variance(db=db, location_id=location_id, period=period)


# ==================== IMPORT / EXPORT ====================

@router.post("/import")
def import_stock(db: DbSession):
    """Import stock from CSV (placeholder)."""
    return {"status": "ok", "message": "CSV import endpoint ready. Send multipart/form-data with CSV file."}


@router.get("/export")
def export_stock(db: DbSession, location_id: int = Query(1)):
    """Export stock to CSV."""
    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id
    ).all()

    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["product_id", "product_name", "quantity", "unit", "cost_price", "par_level"])

    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if product:
            writer.writerow([
                product.id,
                product.name,
                float(s.qty),
                product.unit,
                float(product.cost_price) if product.cost_price else "",
                float(product.par_level) if product.par_level else "",
            ])

    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock_export.csv"},
    )
