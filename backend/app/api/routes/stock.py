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

from fastapi import APIRouter, HTTPException, Query, Request, UploadFile

from app.core.rate_limit import limiter
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


# ==================== STUB ENDPOINTS ====================

@router.get("/items")
@limiter.limit("60/minute")
def get_stock_items(
    request: Request,
    db: DbSession,
    location_id: int = Query(1),
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """Get stock items list."""
    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id,
    ).all()

    items = []
    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or not product.active:
            continue
        if search and search.lower() not in product.name.lower():
            continue
        is_low = product.par_level and s.qty < product.par_level
        item_status = "out_of_stock" if s.qty <= 0 else ("low" if is_low else "ok")
        if status and item_status != status:
            continue
        items.append({
            "id": s.id,
            "product_id": product.id,
            "name": product.name,
            "sku": product.sku,
            "barcode": product.barcode,
            "quantity": float(s.qty),
            "unit": product.unit,
            "par_level": float(product.par_level) if product.par_level else None,
            "min_stock": float(product.min_stock),
            "cost_price": float(product.cost_price) if product.cost_price else None,
            "value": float(s.qty * (product.cost_price or Decimal("0"))),
            "status": item_status,
            "last_updated": s.updated_at.isoformat() if s.updated_at else None,
        })
    total = len(items)
    items = items[offset:offset + limit]
    return {"items": items, "total": total}


@router.get("/transfers")
@limiter.limit("60/minute")
def get_stock_transfers(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = None,
    limit: int = Query(50, le=500),
):
    """Get stock transfers."""
    query = db.query(StockMovement).filter(
        StockMovement.reason.in_(["transfer_in", "transfer_out", "TRANSFER_IN", "TRANSFER_OUT"])
    )
    if location_id:
        query = query.filter(StockMovement.location_id == location_id)
    movements = query.order_by(StockMovement.ts.desc()).limit(limit).all()
    transfers = []
    for m in movements:
        product = db.query(Product).filter(Product.id == m.product_id).first()
        transfers.append({
            "id": m.id,
            "product_id": m.product_id,
            "product_name": product.name if product else f"Product {m.product_id}",
            "location_id": m.location_id,
            "qty_delta": float(m.qty_delta),
            "reason": m.reason,
            "ref_type": m.ref_type,
            "ref_id": m.ref_id,
            "notes": m.notes,
            "timestamp": m.ts.isoformat() if m.ts else None,
        })
    return {"transfers": transfers, "total": len(transfers)}


@router.get("/forecasting")
@limiter.limit("60/minute")
def get_stock_forecasting(request: Request, db: DbSession, location_id: int = Query(1)):
    """Get stock forecasting data."""
    from app.models.analytics import SalesForecast
    forecasts = db.query(SalesForecast).filter(
        SalesForecast.location_id == location_id,
    ).order_by(SalesForecast.forecast_date.desc()).limit(50).all()
    items = []
    for f in forecasts:
        product = db.query(Product).filter(Product.id == f.product_id).first() if f.product_id else None
        items.append({
            "id": f.id,
            "product_id": f.product_id,
            "product_name": product.name if product else "Total",
            "forecast_date": f.forecast_date.isoformat() if f.forecast_date else None,
            "forecasted_quantity": f.forecasted_quantity,
            "forecasted_revenue": f.forecasted_revenue,
            "confidence_level": f.confidence_level,
            "actual_quantity": f.actual_quantity,
            "actual_revenue": f.actual_revenue,
            "accuracy": f.forecast_accuracy,
        })
    recommendations = []
    low_accuracy = [f for f in forecasts if f.forecast_accuracy and f.forecast_accuracy < 70]
    if low_accuracy:
        recommendations.append("Review forecast accuracy for items below 70% - consider adjusting model parameters")
    return {"forecasts": items, "recommendations": recommendations}


@router.get("/forecasting/stats")
@limiter.limit("60/minute")
def get_stock_forecasting_stats(request: Request, db: DbSession, location_id: int = Query(1)):
    """Get stock forecasting statistics."""
    from app.models.analytics import SalesForecast
    total = db.query(func.count(SalesForecast.id)).filter(
        SalesForecast.location_id == location_id,
    ).scalar() or 0
    items_tracked = db.query(func.count(func.distinct(SalesForecast.product_id))).filter(
        SalesForecast.location_id == location_id,
        SalesForecast.product_id.isnot(None),
    ).scalar() or 0
    avg_accuracy = db.query(func.avg(SalesForecast.forecast_accuracy)).filter(
        SalesForecast.location_id == location_id,
        SalesForecast.forecast_accuracy.isnot(None),
    ).scalar()
    last = db.query(SalesForecast.forecast_date).filter(
        SalesForecast.location_id == location_id,
    ).order_by(SalesForecast.forecast_date.desc()).first()
    return {
        "accuracy": round(float(avg_accuracy), 1) if avg_accuracy else 0,
        "total_forecasts": total,
        "items_tracked": items_tracked,
        "avg_deviation": round(100 - float(avg_accuracy), 1) if avg_accuracy else 0,
        "last_updated": last[0].isoformat() if last and last[0] else None,
    }


@router.get("/aging")
@limiter.limit("60/minute")
def get_stock_aging(request: Request, db: DbSession, location_id: int = Query(1)):
    """Get stock aging report."""
    items = []
    total_value = Decimal("0")
    expired_count = 0
    try:
        from app.models.advanced_features import InventoryBatch
        batches = db.query(InventoryBatch).filter(
            InventoryBatch.location_id == location_id,
            InventoryBatch.current_quantity > 0,
        ).order_by(InventoryBatch.received_date.asc()).all()
        for b in batches:
            product = db.query(Product).filter(Product.id == b.product_id).first()
            days_old = (date.today() - b.received_date).days if b.received_date else 0
            is_expired = b.is_expired or (b.expiration_date and b.expiration_date <= date.today())
            value = b.current_quantity * (b.unit_cost or Decimal("0"))
            total_value += value
            if is_expired:
                expired_count += 1
            items.append({
                "id": b.id,
                "product_id": b.product_id,
                "product_name": product.name if product else f"Product {b.product_id}",
                "batch_number": b.batch_number,
                "quantity": float(b.current_quantity),
                "days_old": days_old,
                "received_date": b.received_date.isoformat() if b.received_date else None,
                "expiration_date": b.expiration_date.isoformat() if b.expiration_date else None,
                "value": float(value),
                "is_expired": bool(is_expired),
                "aging_bucket": "0-30" if days_old <= 30 else ("31-60" if days_old <= 60 else ("61-90" if days_old <= 90 else "90+")),
            })
    except Exception as e:
        logger.error("Failed to load aging data: %s", e)
    return {"items": items, "total_value": float(total_value), "expired_count": expired_count}


# ==================== STOCK ITEMS ====================

@router.get("/")
@limiter.limit("60/minute")
def list_stock(
    request: Request,
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
@limiter.limit("30/minute")
def add_stock_item(
    request: Request,
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
@limiter.limit("60/minute")
def get_stock_categories(request: Request, db: DbSession):
    """Get stock categories derived from product units and supplier groupings."""
    # Group products by unit type as a proxy for category
    unit_category_map = {
        "kg": "Food", "g": "Food", "lb": "Food",
        "L": "Beverages", "ml": "Beverages",
        "btl": "Beverages", "can": "Beverages", "keg": "Beer",
        "pcs": "Supplies", "box": "Supplies", "case": "Supplies",
        "dozen": "Supplies",
    }
    products = db.query(Product).filter(Product.active == True).all()
    category_counts: dict = {}
    for p in products:
        cat = unit_category_map.get(p.unit, "Other")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    # Build stable IDs from sorted category names
    categories = []
    for idx, (name, count) in enumerate(sorted(category_counts.items()), start=1):
        categories.append({"id": idx, "name": name, "count": count})
    if not categories:
        return []
    return categories


# ==================== MOVEMENTS ====================

@router.get("/movements/")
@limiter.limit("60/minute")
def get_stock_movements(
    request: Request,
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

    # Build product name lookup
    product_ids = {m.product_id for m in movements}
    products_map = {}
    if product_ids:
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        products_map = {p.id: p.name for p in products}

    return [
        {
            "id": m.id,
            "product_id": m.product_id,
            "product_name": products_map.get(m.product_id, f"Product {m.product_id}"),
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
@limiter.limit("30/minute")
def record_stock_movement(
    request: Request,
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
@limiter.limit("60/minute")
def get_stock_alerts(
    request: Request,
    db: DbSession,
    location_id: int = Query(1),
):
    """Get stock alerts (low stock, out of stock, expiring)."""
    alerts = []

    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id
    ).all()

    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product:
            continue

        if s.qty <= 0:
            alerts.append({
                "type": "out_of_stock",
                "severity": "critical",
                "product_id": product.id,
                "product_name": product.name,
                "current_qty": float(s.qty),
                "par_level": float(product.par_level) if product.par_level else None,
                "unit": product.unit,
                "message": f"{product.name} is out of stock",
            })
        elif product.par_level and s.qty < product.par_level:
            alerts.append({
                "type": "low_stock",
                "severity": "warning",
                "product_id": product.id,
                "product_name": product.name,
                "current_qty": float(s.qty),
                "par_level": float(product.par_level),
                "unit": product.unit,
                "message": f"{product.name} is below par level ({s.qty}/{product.par_level} {product.unit})",
            })
        elif product.min_stock and s.qty < product.min_stock:
            alerts.append({
                "type": "below_minimum",
                "severity": "warning",
                "product_id": product.id,
                "product_name": product.name,
                "current_qty": float(s.qty),
                "min_stock": float(product.min_stock),
                "unit": product.unit,
                "message": f"{product.name} is below minimum stock",
            })

    # Expiring soon alerts
    try:
        from app.models.advanced_features import InventoryBatch
        expiring = db.query(InventoryBatch).filter(
            InventoryBatch.location_id == location_id,
            InventoryBatch.is_expired == False,
            InventoryBatch.current_quantity > 0,
            InventoryBatch.expiration_date <= date.today() + timedelta(days=7),
        ).all()

        for batch in expiring:
            product = db.query(Product).filter(Product.id == batch.product_id).first()
            days_left = (batch.expiration_date - date.today()).days if batch.expiration_date else None
            alerts.append({
                "type": "expiring_soon" if days_left and days_left > 0 else "expired",
                "severity": "critical" if days_left and days_left <= 0 else "warning",
                "product_id": batch.product_id,
                "product_name": product.name if product else f"Product {batch.product_id}",
                "batch_number": batch.batch_number,
                "expiration_date": batch.expiration_date.isoformat() if batch.expiration_date else None,
                "days_remaining": days_left,
                "quantity": float(batch.current_quantity),
                "message": f"Batch {batch.batch_number} expires in {days_left} days" if days_left and days_left > 0 else f"Batch {batch.batch_number} has expired",
            })
    except Exception as e:
        logger.debug(f"Optional: query expiring batch alerts: {e}")

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda x: severity_order.get(x["severity"], 99))

    return {
        "alerts": alerts,
        "total": len(alerts),
        "critical": len([a for a in alerts if a["severity"] == "critical"]),
        "warnings": len([a for a in alerts if a["severity"] == "warning"]),
    }


# ==================== BATCHES ====================

@router.get("/batches")
@limiter.limit("60/minute")
def get_stock_batches(
    request: Request,
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
    except Exception as e:
        logger.error("Failed to load batches: %s", e)
        return []


# ==================== EXPIRING ====================

@router.get("/expiring")
@limiter.limit("60/minute")
def get_expiring_items(
    request: Request,
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
    except Exception as e:
        logger.error("Failed to load expiring items: %s", e)
        return []


# ==================== ADJUSTMENTS ====================

@router.get("/adjustments")
@limiter.limit("60/minute")
def get_adjustments(
    request: Request,
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


@router.post("/adjustments")
@limiter.limit("30/minute")
def create_adjustment(
    request: Request,
    db: DbSession,
    data: dict = None,
):
    """Create a stock adjustment."""
    from fastapi import Body
    if data is None:
        data = {}
    product_id = data.get("product_id")
    location_id = data.get("location_id", 1)
    qty_delta = Decimal(str(data.get("quantity_delta", data.get("qty_delta", 0))))
    reason = data.get("reason", "correction")
    notes = data.get("notes", "")

    if not product_id:
        raise HTTPException(status_code=422, detail="product_id is required")

    # Create stock movement
    movement = StockMovement(
        product_id=int(product_id),
        location_id=int(location_id),
        qty_delta=qty_delta,
        reason=MovementReason.ADJUSTMENT.value,
        notes=notes,
    )
    db.add(movement)

    # Update stock on hand
    stock = db.query(StockOnHand).filter(
        StockOnHand.product_id == int(product_id),
        StockOnHand.location_id == int(location_id),
    ).first()
    if stock:
        stock.qty += qty_delta
    else:
        stock = StockOnHand(
            product_id=int(product_id),
            location_id=int(location_id),
            qty=max(qty_delta, Decimal("0")),
        )
        db.add(stock)

    db.commit()
    db.refresh(movement)
    return {
        "id": movement.id,
        "product_id": movement.product_id,
        "location_id": movement.location_id,
        "qty_delta": float(movement.qty_delta),
        "reason": reason,
        "notes": notes,
        "status": "approved",
    }


@router.put("/adjustments/{adjustment_id}/approve")
@limiter.limit("30/minute")
def approve_adjustment(request: Request, db: DbSession, adjustment_id: int):
    """Approve a stock adjustment."""
    return {"status": "approved", "adjustment_id": adjustment_id}


# ==================== VALUATION ====================

@router.get("/valuation")
@limiter.limit("60/minute")
def get_stock_valuation(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get stock valuation data."""
    from app.models.stock import StockOnHand
    query = db.query(StockOnHand)
    if location_id:
        query = query.filter(StockOnHand.location_id == location_id)
    stock_items = query.all()
    by_location = {}
    grand_total = Decimal("0")
    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product:
            continue
        location = db.query(Location).filter(Location.id == s.location_id).first()
        loc_name = location.name if location else f"Location {s.location_id}"
        if loc_name not in by_location:
            by_location[loc_name] = {"location_id": s.location_id, "total_value": 0, "total_items": 0, "items": []}
        unit_cost = product.cost_price or Decimal("0")
        item_value = s.qty * unit_cost
        grand_total += item_value
        by_location[loc_name]["total_value"] += float(item_value)
        by_location[loc_name]["total_items"] += 1
        by_location[loc_name]["items"].append({
            "product_id": product.id, "product_name": product.name,
            "qty": float(s.qty), "unit": product.unit,
            "unit_cost": float(unit_cost), "total_value": float(item_value),
        })
    return {"grand_total_value": float(grand_total), "locations": by_location}


# ==================== WASTE ====================

@router.get("/waste/records")
@limiter.limit("60/minute")
def get_waste_records(
    request: Request,
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
@limiter.limit("60/minute")
def get_waste_stats(
    request: Request,
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
@limiter.limit("60/minute")
def get_waste_insights(request: Request, db: DbSession, location_id: int = Query(1)):
    """Get waste insights and recommendations."""
    from app.models.advanced_features import WasteTrackingEntry
    from sqlalchemy import func as sqlfunc

    month_ago = date.today() - timedelta(days=30)
    # Top wasted items by cost
    top_items = db.query(
        WasteTrackingEntry.product_id,
        sqlfunc.sum(WasteTrackingEntry.cost_value).label("total_cost"),
        sqlfunc.sum(WasteTrackingEntry.weight_kg).label("total_kg"),
        sqlfunc.count(WasteTrackingEntry.id).label("count"),
    ).filter(
        WasteTrackingEntry.location_id == location_id,
        WasteTrackingEntry.recorded_at >= datetime.combine(month_ago, datetime.min.time()),
    ).group_by(WasteTrackingEntry.product_id).order_by(
        sqlfunc.sum(WasteTrackingEntry.cost_value).desc()
    ).limit(10).all()

    top_wasted = []
    for row in top_items:
        product = db.query(Product).filter(Product.id == row.product_id).first() if row.product_id else None
        top_wasted.append({
            "product_id": row.product_id,
            "product_name": product.name if product else f"Product {row.product_id}",
            "total_cost": float(row.total_cost or 0),
            "total_weight_kg": float(row.total_kg or 0),
            "incidents": row.count,
        })

    recommendations = [
        "Review prep quantities for high-waste items",
        "Consider batch cooking to reduce overproduction",
        "Monitor expiration dates more closely",
    ]
    if top_wasted:
        recommendations.insert(0, f"Focus on reducing waste for {top_wasted[0]['product_name']} (highest cost impact)")

    return {
        "top_wasted_items": top_wasted,
        "recommendations": recommendations,
        "trend": "stable",
    }


@router.post("/waste/records")
@limiter.limit("30/minute")
def record_waste(
    request: Request,
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
@limiter.limit("60/minute")
def get_stock_counts(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get stock count sessions."""
    query = db.query(InventorySession)
    if location_id:
        query = query.filter(InventorySession.location_id == location_id)

    sessions = query.order_by(InventorySession.started_at.desc()).limit(20).all()
    results = []
    for s in sessions:
        lines = s.lines or []
        items_count = len(lines)

        # Compute variance by comparing counted qty vs current stock
        variance_count = 0
        variance_value = 0.0
        for line in lines:
            stock = db.query(StockOnHand).filter(
                StockOnHand.product_id == line.product_id,
                StockOnHand.location_id == s.location_id,
            ).first()
            current_qty = float(stock.qty) if stock else 0.0
            delta = float(line.counted_qty) - current_qty
            if delta != 0:
                variance_count += 1
                product = db.query(Product).filter(Product.id == line.product_id).first()
                cost = float(product.cost_price) if product and product.cost_price else 0.0
                variance_value += delta * cost

        # Parse type from notes (format: "Stock count (full) - Location")
        count_type = "full"
        location_name = ""
        if s.notes:
            import re
            type_match = re.search(r'\((\w+)\)', s.notes)
            if type_match:
                count_type = type_match.group(1)
            loc_match = re.search(r' - (.+)$', s.notes)
            if loc_match:
                location_name = loc_match.group(1)
        if not location_name and s.location:
            location_name = s.location.name

        status_val = s.status.value if hasattr(s.status, 'value') else str(s.status)

        results.append({
            "id": s.id,
            "count_number": f"SC-{s.id:04d}",
            "type": count_type,
            "location_id": s.location_id,
            "location": location_name,
            "status": status_val,
            "notes": s.notes,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.committed_at.isoformat() if s.committed_at else None,
            "counted_by": "Staff",
            "items_count": items_count,
            "variance_count": variance_count,
            "variance_value": round(variance_value, 2),
        })
    return results


@router.post("/counts")
@limiter.limit("30/minute")
def create_stock_count(
    request: Request,
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
@limiter.limit("60/minute")
def get_stock_count_items(request: Request, db: DbSession, count_id: int):
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
@limiter.limit("30/minute")
def update_count_item(
    request: Request,
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
    line.counted_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "updated", "item_id": item_id, "counted_quantity": counted_quantity}


@router.put("/counts/{count_id}/complete")
@limiter.limit("30/minute")
def complete_stock_count(request: Request, db: DbSession, count_id: int):
    """Mark a stock count as completed (ready for approval)."""
    session = db.query(InventorySession).filter(InventorySession.id == count_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Count session not found")
    if session.status == SessionStatus.COMMITTED:
        raise HTTPException(status_code=400, detail="Session already committed")
    line_count = len(session.lines) if session.lines else 0
    return {"status": "completed", "count_id": count_id, "items_counted": line_count}


@router.put("/counts/{count_id}/approve")
@limiter.limit("30/minute")
def approve_stock_count(request: Request, db: DbSession, count_id: int):
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
    session.committed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "approved",
        "count_id": count_id,
        "movements_created": movements_created,
        "adjustments": adjustments,
    }


# ==================== PAR LEVELS ====================

@router.get("/par-levels")
@limiter.limit("60/minute")
def get_par_levels(
    request: Request,
    db: DbSession,
    period: str = Query("week"),
    location_id: int = Query(1),
):
    """Get par level analysis."""
    from app.models.stock import StockOnHand, StockMovement, MovementReason
    from sqlalchemy import func
    products = db.query(Product).filter(Product.active == True).all()
    items = []
    days_map = {"week": 7, "month": 30, "quarter": 90}
    period_days = days_map.get(period, 7)
    start_date = datetime.now(timezone.utc) - timedelta(days=period_days)
    for product in products:
        stock = db.query(StockOnHand).filter(
            StockOnHand.product_id == product.id, StockOnHand.location_id == location_id,
        ).first()
        usage = db.query(func.sum(func.abs(StockMovement.qty_delta)).label("total_used")).filter(
            StockMovement.product_id == product.id, StockMovement.location_id == location_id,
            StockMovement.reason == MovementReason.SALE.value, StockMovement.ts >= start_date,
        ).scalar() or Decimal("0")
        avg_daily = float(usage) / period_days if period_days > 0 else 0
        current_qty = float(stock.qty) if stock else 0
        par = float(product.par_level) if product.par_level else None
        days_of_stock = current_qty / avg_daily if avg_daily > 0 else 999
        lead_time = product.lead_time_days or 1
        suggested_par = avg_daily * (lead_time + 3)
        items.append({
            "product_id": product.id, "product_name": product.name, "unit": product.unit,
            "current_qty": current_qty, "par_level": par, "suggested_par": round(suggested_par, 1),
            "avg_daily_usage": round(avg_daily, 2), "days_of_stock": round(days_of_stock, 1),
            "lead_time_days": lead_time,
            "status": "critical" if days_of_stock < lead_time else "low" if par and current_qty < par else "ok",
            "reorder_needed": par and current_qty < par if par else days_of_stock < lead_time * 1.5,
        })
    items.sort(key=lambda x: x["days_of_stock"])
    return {"period": period, "period_days": period_days, "location_id": location_id,
            "items": items, "total_items": len(items),
            "items_needing_reorder": len([i for i in items if i.get("reorder_needed")])}


# ==================== VARIANCE ====================

@router.get("/variance/analysis")
@limiter.limit("60/minute")
def get_variance_analysis(
    request: Request,
    db: DbSession,
    period: str = Query("week"),
    location_id: int = Query(1),
):
    """Get variance analysis."""
    from app.services.stock_deduction_service import StockDeductionService
    stock_service = StockDeductionService(db)
    days_map = {"week": 7, "month": 30, "quarter": 90}
    period_days = days_map.get(period, 7)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=period_days)
    result = stock_service.calculate_shrinkage(
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
    )
    result["period"] = period
    result["period_days"] = period_days
    return result


# ==================== IMPORT / EXPORT ====================

@router.post("/import", response_model=None)
@limiter.limit("5/minute")
async def import_stock(request: Request, db: DbSession = None, file: UploadFile = None):
    """Import stock items from CSV. Expects columns: name, barcode, unit, min_stock, cost_price, par_level."""
    from fastapi import File
    import csv
    import io

    if file is None:
        return {"status": "ok", "message": "CSV import endpoint ready. Send multipart/form-data with a 'file' field containing a CSV."}

    # Validate file type and size
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB")
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    created = 0
    updated = 0
    errors = []
    for row_num, row in enumerate(reader, start=2):
        name = row.get("name", "").strip()
        if not name:
            errors.append(f"Row {row_num}: missing name")
            continue
        barcode = row.get("barcode", "").strip() or None
        existing = None
        if barcode:
            existing = db.query(Product).filter(Product.barcode == barcode).first()
        if not existing:
            existing = db.query(Product).filter(Product.name == name).first()

        if existing:
            if row.get("unit"):
                existing.unit = row["unit"].strip()
            if row.get("min_stock"):
                existing.min_stock = Decimal(row["min_stock"])
            if row.get("cost_price"):
                existing.cost_price = Decimal(row["cost_price"])
            if row.get("par_level"):
                existing.par_level = Decimal(row["par_level"])
            updated += 1
        else:
            product = Product(
                name=name,
                barcode=barcode,
                unit=row.get("unit", "pcs").strip(),
                min_stock=Decimal(row.get("min_stock", "0")),
                cost_price=Decimal(row["cost_price"]) if row.get("cost_price") else None,
                par_level=Decimal(row["par_level"]) if row.get("par_level") else None,
            )
            db.add(product)
            created += 1

    db.commit()
    return {"status": "ok", "created": created, "updated": updated, "errors": errors}


@router.get("/export")
@limiter.limit("60/minute")
def export_stock(request: Request, db: DbSession, location_id: int = Query(1)):
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


# ==================== WASTE (root GET) ====================

@router.get("/waste")
@limiter.limit("60/minute")
def get_waste_overview(
    request: Request,
    db: DbSession,
    location_id: int = Query(1),
):
    """Get waste overview - returns recent waste records and summary stats."""
    from app.models.advanced_features import WasteTrackingEntry
    entries = db.query(WasteTrackingEntry).filter(
        WasteTrackingEntry.location_id == location_id,
    ).order_by(
        WasteTrackingEntry.recorded_at.desc()
    ).limit(100).all()

    total_cost = sum(float(e.cost_value or 0) for e in entries)
    total_weight = sum(float(e.weight_kg or 0) for e in entries)
    records = []
    for e in entries:
        product = db.query(Product).filter(Product.id == e.product_id).first() if e.product_id else None
        records.append({
            "id": e.id,
            "product_id": e.product_id,
            "product_name": product.name if product else (e.ai_detected_item or "Unknown"),
            "category": e.category.value if hasattr(e.category, 'value') else str(e.category),
            "weight_kg": float(e.weight_kg),
            "cost_value": float(e.cost_value),
            "station": e.station,
            "shift": e.shift,
            "reason": e.reason or "",
            "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
            "ai_detected_item": e.ai_detected_item,
            "ai_confidence": e.ai_confidence,
        })

    return {
        "records": records,
        "total": len(records),
        "total_cost": round(total_cost, 2),
        "total_weight_kg": round(total_weight, 3),
    }


# ==================== RECIPE COSTS ====================

@router.get("/recipe-costs")
@limiter.limit("60/minute")
def get_stock_recipe_costs(request: Request, db: DbSession):
    """Get recipe cost analysis - proxy to /recipes/costs."""
    from app.models.recipe import Recipe, RecipeLine

    recipes = db.query(Recipe).order_by(Recipe.name).all()
    results = []
    for recipe in recipes:
        lines = db.query(RecipeLine).filter(RecipeLine.recipe_id == recipe.id).all()
        total_cost = Decimal("0")
        ingredients = []
        for line in lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if product:
                line_cost = Decimal(str(line.qty)) * (product.cost_price or Decimal("0"))
                total_cost += line_cost
                ingredients.append({
                    "product_id": product.id,
                    "name": product.name,
                    "qty": float(line.qty),
                    "unit": line.unit,
                    "unit_cost": float(product.cost_price or 0),
                    "line_cost": float(line_cost),
                })
        results.append({
            "id": recipe.id,
            "name": recipe.name,
            "total_cost": float(total_cost),
            "ingredients": ingredients,
            "ingredient_count": len(ingredients),
        })
    return {"recipes": results, "total": len(results)}


@router.get("/recipe-costs/stats")
@limiter.limit("60/minute")
def get_stock_recipe_cost_stats(request: Request, db: DbSession):
    """Get recipe cost statistics."""
    from app.models.recipe import Recipe, RecipeLine

    recipes = db.query(Recipe).all()
    costs = []
    for recipe in recipes:
        lines = db.query(RecipeLine).filter(RecipeLine.recipe_id == recipe.id).all()
        total_cost = Decimal("0")
        for line in lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            if product:
                total_cost += Decimal(str(line.qty)) * (product.cost_price or Decimal("0"))
        costs.append(float(total_cost))

    return {
        "total_recipes": len(recipes),
        "average_cost": round(sum(costs) / len(costs), 2) if costs else 0,
        "highest_cost": round(max(costs), 2) if costs else 0,
        "lowest_cost": round(min(costs), 2) if costs else 0,
        "total_cost": round(sum(costs), 2),
    }


# ==================== SUPPLIER PERFORMANCE ====================

@router.get("/supplier-performance")
@limiter.limit("60/minute")
def get_stock_supplier_performance(request: Request, db: DbSession):
    """Get supplier delivery and quality performance."""
    from app.models.supplier import Supplier

    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    performance = []
    for supplier in suppliers:
        performance.append({
            "id": supplier.id,
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "on_time_delivery_rate": 0,
            "quality_rating": 0,
            "average_lead_time_days": 0,
            "total_orders": 0,
            "total_value": 0,
            "contact_email": supplier.contact_email,
            "contact_phone": supplier.contact_phone,
        })
    return performance


@router.get("/supplier-performance/stats")
@limiter.limit("60/minute")
def get_stock_supplier_performance_stats(request: Request, db: DbSession):
    """Get supplier performance statistics."""
    from app.models.supplier import Supplier

    supplier_count = db.query(func.count(Supplier.id)).scalar() or 0
    return {
        "total_suppliers": supplier_count,
        "avg_on_time_rate": 0,
        "avg_quality_rating": 0,
        "avg_lead_time_days": 0,
    }


# ==================== TANKS (proxy to inventory-hardware) ====================

@router.get("/tanks")
@limiter.limit("60/minute")
def get_stock_tanks(request: Request, db: DbSession, status: Optional[str] = Query(None)):
    """Get tanks under /stock prefix - proxy to inventory hardware tanks."""
    from app.models.hardware import Tank as TankModel

    query = db.query(TankModel)
    if status:
        query = query.filter(TankModel.status == status)

    tanks = query.all()

    tank_list = []
    alerts = []
    for tank in tanks:
        level_percentage = round(
            (tank.current_level_liters / tank.capacity_liters) * 100, 1
        ) if tank.capacity_liters and tank.capacity_liters > 0 else 0
        tank_dict = {
            "id": tank.id,
            "name": tank.name,
            "product_id": tank.product_id,
            "product_name": tank.product_name,
            "capacity_liters": tank.capacity_liters,
            "current_level_liters": tank.current_level_liters,
            "level_percentage": level_percentage,
            "status": tank.status,
            "last_refill": tank.last_refill,
            "sensor_id": tank.sensor_id,
        }
        tank_list.append(tank_dict)
        if tank.status in ["low", "critical"]:
            alerts.append(tank_dict)

    return {
        "tanks": tank_list,
        "total": len(tank_list),
        "alerts": alerts,
    }
