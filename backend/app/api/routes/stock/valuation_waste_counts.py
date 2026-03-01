"""Valuation, waste tracking, stock counts, par levels"""
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
    try:
        result = StockCountService.commit_session(
            db=db,
            session_id=count_id,
            ref_type="inventory_session",
            require_lines=False,
        )
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail="Count session not found")
        raise HTTPException(status_code=400, detail=detail)

    return {
        "status": "approved",
        "count_id": count_id,
        "movements_created": result["movements_created"],
        "adjustments": result["adjustments"],
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


