"""Batch CRUD, shrinkage, cycle counts, reconciliation, unit conversions"""
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

# ==================== BATCH CRUD (item-level + create) ====================

class BatchCreateRequest(BaseModel):
    stock_item_id: int
    batch_number: str
    quantity: float
    expiry_date: Optional[str] = None
    cost_per_unit: Optional[float] = None


@router.get("/batches/item/{item_id}")
@limiter.limit("60/minute")
def get_batches_for_item(request: Request, item_id: int, db: DbSession, location_id: int = Query(1)):
    """Get batches for a specific item."""
    batches = []
    try:
        from app.models.advanced_features import InventoryBatch
        batch_rows = db.query(InventoryBatch).filter(
            InventoryBatch.product_id == item_id,
            InventoryBatch.location_id == location_id,
            InventoryBatch.current_quantity > 0,
        ).all()
        for b in batch_rows:
            batches.append({
                "id": b.id,
                "stock_item_id": b.product_id,
                "batch_number": b.batch_number,
                "quantity": float(b.current_quantity),
                "received_date": b.received_date.isoformat() if b.received_date else None,
                "expiry_date": b.expiration_date.isoformat() if b.expiration_date else None,
                "cost_per_unit": float(b.unit_cost) if b.unit_cost else None,
                "is_active": not b.is_expired,
            })
    except Exception as e:
        logger.debug(f"Optional: query batches for item {item_id}: {e}")
    return batches


@router.post("/batches")
@limiter.limit("30/minute")
def create_stock_batch(request: Request, batch_request: BatchCreateRequest, db: DbSession, location_id: int = Query(1)):
    """Record a new batch."""
    from app.models.advanced_features import InventoryBatch
    today = date.today()
    exp = date.fromisoformat(batch_request.expiry_date) if batch_request.expiry_date else today + timedelta(days=365)
    batch = InventoryBatch(
        product_id=batch_request.stock_item_id,
        location_id=location_id,
        batch_number=batch_request.batch_number,
        received_quantity=batch_request.quantity,
        current_quantity=batch_request.quantity,
        received_date=today,
        expiration_date=exp,
        unit_cost=batch_request.cost_per_unit or 0,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return {
        "id": batch.id,
        "stock_item_id": batch.product_id,
        "batch_number": batch.batch_number,
        "quantity": float(batch.current_quantity),
        "received_date": batch.received_date.isoformat(),
        "expiry_date": batch.expiration_date.isoformat(),
        "cost_per_unit": float(batch.unit_cost),
        "is_active": not batch.is_expired,
    }


# ==================== SHRINKAGE ====================

class ShrinkageRecordRequest(BaseModel):
    stock_item_id: int
    quantity: float
    reason: str
    notes: Optional[str] = None


@router.get("/shrinkage")
@limiter.limit("60/minute")
def get_shrinkage_analysis(
    request: Request,
    db: DbSession,
    location_id: int = Query(1),
    days: int = Query(30, le=365),
):
    """
    Calculate shrinkage (theoretical vs actual usage).

    Theoretical usage = recipe ingredients x sales quantity
    Actual usage = measured by inventory count adjustments
    Shrinkage = unaccounted loss (potential theft, spillage, or counting errors)

    Matches Restaurant365/MarketMan variance analysis.
    Also falls back to listing waste/loss movements when the shrinkage
    service is unavailable.
    """
    stock_service = StockDeductionService(db)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    try:
        result = stock_service.calculate_shrinkage(
            location_id=location_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as exc:
        logger.warning("Shrinkage service unavailable, falling back to movement records: %s", exc)

    # Fallback: raw waste/loss movements
    waste_movements = db.query(StockMovement).filter(
        StockMovement.location_id == location_id,
        StockMovement.reason.in_(["waste", "spoilage", "theft", "damage", "shrinkage"]),
        StockMovement.ts >= start_date,
    ).order_by(StockMovement.ts.desc()).all()

    records = []
    for m in waste_movements:
        product = db.query(Product).filter(Product.id == m.product_id).first()
        cost = float(abs(m.qty_delta) * (product.cost_price or 0)) if product else 0
        records.append({
            "id": m.id,
            "stock_item_id": m.product_id,
            "product_name": product.name if product else f"Product {m.product_id}",
            "quantity": float(abs(m.qty_delta)),
            "reason": m.reason,
            "value_lost": cost,
            "recorded_at": m.ts.isoformat() if m.ts else None,
            "notes": m.notes,
        })
    return records


@router.post("/shrinkage/record")
@limiter.limit("30/minute")
def record_shrinkage(request: Request, shrinkage_request: ShrinkageRecordRequest, db: DbSession, location_id: int = Query(1)):
    """Record a shrinkage event."""
    movement = StockMovement(
        product_id=shrinkage_request.stock_item_id,
        location_id=location_id,
        qty_delta=-abs(shrinkage_request.quantity),
        reason=shrinkage_request.reason if shrinkage_request.reason in ("waste", "spoilage", "theft", "damage", "shrinkage") else "shrinkage",
        notes=shrinkage_request.notes,
        ts=datetime.now(timezone.utc),
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return {
        "id": movement.id,
        "stock_item_id": movement.product_id,
        "quantity": shrinkage_request.quantity,
        "reason": movement.reason,
        "notes": movement.notes,
        "recorded_at": movement.ts.isoformat() if movement.ts else datetime.now(timezone.utc).isoformat(),
    }


# ==================== CYCLE COUNTS ====================

class CycleCountScheduleRequest(BaseModel):
    name: str
    count_type: str = "full"
    frequency_days: int = 30
    is_active: bool = True


@router.get("/cycle-counts/schedules")
@limiter.limit("60/minute")
def get_cycle_count_schedules(request: Request, db: DbSession):
    """Get cycle count schedules."""
    from app.models.operations import AppSetting
    setting = db.query(AppSetting).filter(
        AppSetting.category == "cycle_count_schedules",
        AppSetting.key == "default",
    ).first()
    if setting and isinstance(setting.value, list):
        return setting.value
    return []


@router.get("/cycle-counts/tasks")
@limiter.limit("60/minute")
def get_cycle_count_tasks(request: Request, db: DbSession):
    """Get cycle count tasks."""
    sessions = db.query(InventorySession).order_by(
        InventorySession.id.desc()
    ).limit(20).all()

    tasks = []
    for s in sessions:
        line_count = db.query(func.count(InventoryLine.id)).filter(
            InventoryLine.session_id == s.id,
        ).scalar() or 0
        tasks.append({
            "id": s.id,
            "schedule_id": None,
            "status": s.status if isinstance(s.status, str) else s.status.value,
            "started_at": s.created_at.isoformat() if hasattr(s, 'created_at') and s.created_at else None,
            "completed_at": s.committed_at.isoformat() if s.committed_at else None,
            "items_counted": line_count,
            "discrepancies_found": 0,
        })
    return tasks


@router.post("/cycle-counts/schedules")
@limiter.limit("30/minute")
def create_cycle_count_schedule(request: Request, schedule_request: CycleCountScheduleRequest, db: DbSession):
    """Create a cycle count schedule."""
    from app.models.operations import AppSetting
    setting = db.query(AppSetting).filter(
        AppSetting.category == "cycle_count_schedules",
        AppSetting.key == "default",
    ).first()
    schedules = []
    if setting and isinstance(setting.value, list):
        schedules = list(setting.value)
    next_id = max((s.get("id", 0) for s in schedules), default=0) + 1
    new_schedule = {
        "id": next_id,
        "name": schedule_request.name,
        "count_type": schedule_request.count_type,
        "frequency_days": schedule_request.frequency_days,
        "next_count_date": (date.today() + timedelta(days=schedule_request.frequency_days)).isoformat(),
        "is_active": schedule_request.is_active,
    }
    schedules.append(new_schedule)
    if setting:
        setting.value = schedules
    else:
        setting = AppSetting(category="cycle_count_schedules", key="default", value=schedules)
        db.add(setting)
    db.commit()
    return new_schedule


# ==================== RECONCILIATION ====================

@router.get("/reconciliation/sessions")
@limiter.limit("60/minute")
def get_reconciliation_sessions(request: Request, db: DbSession, location_id: int = Query(1)):
    """Get reconciliation sessions."""
    sessions = db.query(InventorySession).filter(
        InventorySession.location_id == location_id,
    ).order_by(InventorySession.id.desc()).limit(20).all()

    result = []
    for s in sessions:
        line_count = db.query(func.count(InventoryLine.id)).filter(
            InventoryLine.session_id == s.id,
        ).scalar() or 0
        result.append({
            "id": s.id,
            "session_name": s.notes or f"Session {s.id}",
            "status": s.status if isinstance(s.status, str) else s.status.value,
            "started_at": s.created_at.isoformat() if hasattr(s, 'created_at') and s.created_at else datetime.now(timezone.utc).isoformat(),
            "completed_at": s.committed_at.isoformat() if s.committed_at else None,
            "total_items": line_count,
            "discrepancies": 0,
            "total_variance_value": 0,
        })
    return result


@router.post("/reconciliation/start")
@limiter.limit("30/minute")
def start_reconciliation(request: Request, db: DbSession, location_id: int = Query(1)):
    """Start a new reconciliation session."""
    session = InventorySession(
        location_id=location_id,
        notes=f"Reconciliation - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
    )
    db.add(session)
    db.commit()
    return {
        "id": session.id,
        "session_name": session.notes,
        "status": "draft",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== UNIT CONVERSIONS ====================

class UnitConversionRequest(BaseModel):
    from_unit: str
    to_unit: str
    conversion_factor: float
    is_active: bool = True


@router.get("/unit-conversions")
@limiter.limit("60/minute")
def get_unit_conversions(request: Request, db: DbSession):
    """Get unit conversion table."""
    from app.models.operations import AppSetting
    setting = db.query(AppSetting).filter(
        AppSetting.category == "unit_conversions",
        AppSetting.key == "default",
    ).first()
    if setting and isinstance(setting.value, list):
        return setting.value
    return []


@router.post("/unit-conversions")
@limiter.limit("30/minute")
def create_unit_conversion(request: Request, conversion_request: UnitConversionRequest, db: DbSession):
    """Create a unit conversion."""
    from app.models.operations import AppSetting
    setting = db.query(AppSetting).filter(
        AppSetting.category == "unit_conversions",
        AppSetting.key == "default",
    ).first()
    conversions = setting.value if setting and isinstance(setting.value, list) else []
    new_id = max((c.get("id", 0) for c in conversions), default=0) + 1
    new_conversion = {
        "id": new_id,
        "from_unit": conversion_request.from_unit,
        "to_unit": conversion_request.to_unit,
        "conversion_factor": conversion_request.conversion_factor,
        "is_active": conversion_request.is_active,
    }
    conversions.append(new_conversion)
    if setting:
        setting.value = conversions
    else:
        setting = AppSetting(category="unit_conversions", key="default", value=conversions)
        db.add(setting)
    db.commit()
    return new_conversion


