"""Stock items, movements, alerts, batches, adjustments"""
import logging
import random
import uuid
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, UploadFile

from app.core.rate_limit import limiter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, and_, or_

from app.db.session import DbSession
from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.product import Product
from app.models.location import Location
from app.models.order import PurchaseOrder, PurchaseOrderLine
from app.models.inventory import InventorySession, InventoryLine, SessionStatus
from app.services.stock_deduction_service import StockDeductionService
from app.services.stock_alert_service import StockAlertService
from app.services.stock_count_service import StockCountService
from app.models.menu_inventory_complete import (
    StockItemBarcode, StockBatchFIFO, ShrinkageRecord,
    CycleCountSchedule, CycleCountTask, CycleCountItem, UnitConversion,
    ReconciliationSession, ReconciliationItem, SupplierPerformanceRecord,
    ReorderPriority, CountType, ShrinkageReason, ReconciliationStatus
)
from app.models.feature_models import AutoReorderRule

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
    return StockAlertService.get_alerts(db, location_id=location_id)


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

