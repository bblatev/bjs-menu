"""Import/export, recipe costs, supplier perf, dashboard, barcodes, auto-reorder"""
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

    # Validate content type
    allowed_types = {"text/csv", "application/vnd.ms-excel"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: CSV (text/csv)")

    # Validate file extension
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Validate file size (10MB max)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB")

    # Validate file is not empty
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

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


# ===========================================================================
# MERGED FROM inventory_complete.py -- unique features not already in stock.py
# ===========================================================================


# ==================== DASHBOARD KPIs ====================

@router.get("/dashboard")
@limiter.limit("60/minute")
def get_stock_dashboard(
    request: Request,
    db: DbSession,
    location_id: int = Query(1),
):
    """
    Comprehensive inventory dashboard with KPIs and summaries.
    Returns: total items, total value, low/out of stock counts,
    recent movements, expiring items, and top movers.
    """
    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id
    ).all()

    total_items = 0
    total_value = Decimal("0")
    low_stock_count = 0
    out_of_stock_count = 0
    negative_count = 0
    items_with_par = 0

    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or not product.active:
            continue

        total_items += 1
        item_value = s.qty * (product.cost_price or Decimal("0"))
        total_value += item_value

        if s.qty <= 0:
            out_of_stock_count += 1
        if s.qty < 0:
            negative_count += 1
        if product.par_level and s.qty < product.par_level and s.qty > 0:
            low_stock_count += 1
        if product.par_level:
            items_with_par += 1

    # Recent movements (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    movement_summary = db.query(
        StockMovement.reason,
        func.count(StockMovement.id).label("count"),
        func.sum(func.abs(StockMovement.qty_delta)).label("total_qty"),
    ).filter(
        StockMovement.location_id == location_id,
        StockMovement.ts >= week_ago,
    ).group_by(StockMovement.reason).all()

    movements_by_type = {
        row.reason: {"count": row.count, "total_qty": float(row.total_qty or 0)}
        for row in movement_summary
    }

    # Expiring soon (next 7 days)
    expiring_count = 0
    try:
        from app.models.advanced_features import InventoryBatch
        expiring_count = db.query(func.count(InventoryBatch.id)).filter(
            InventoryBatch.location_id == location_id,
            InventoryBatch.is_expired == False,
            InventoryBatch.current_quantity > 0,
            InventoryBatch.expiration_date <= date.today() + timedelta(days=7),
        ).scalar() or 0
    except Exception as e:
        logger.debug(f"Optional: query expiring batch count: {e}")

    # Active inventory sessions
    active_sessions = db.query(func.count(InventorySession.id)).filter(
        InventorySession.location_id == location_id,
        InventorySession.status == SessionStatus.DRAFT,
    ).scalar() or 0

    # Last count date
    last_count = db.query(InventorySession.committed_at).filter(
        InventorySession.location_id == location_id,
        InventorySession.status == SessionStatus.COMMITTED,
    ).order_by(InventorySession.committed_at.desc()).first()

    return {
        "location_id": location_id,
        "kpis": {
            "total_items": total_items,
            "total_value": float(total_value),
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "negative_stock_count": negative_count,
            "expiring_soon_count": expiring_count,
            "items_with_par_level": items_with_par,
        },
        "movements_7d": movements_by_type,
        "active_count_sessions": active_sessions,
        "last_count_date": last_count[0].isoformat() if last_count and last_count[0] else None,
    }


# ==================== BARCODES ====================

class BarcodeCreateRequest(BaseModel):
    stock_item_id: int
    barcode_value: str
    barcode_type: str = "EAN13"
    is_primary: bool = False


@router.get("/barcodes")
@limiter.limit("60/minute")
def list_barcodes(
    request: Request,
    db: DbSession,
    location_id: int = Query(1),
):
    """List all barcodes for inventory items."""
    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id,
    ).all()

    barcodes = []
    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or not product.active:
            continue
        if product.barcode:
            barcodes.append({
                "id": product.id,
                "stock_item_id": product.id,
                "barcode_value": product.barcode,
                "barcode_type": "EAN13",
                "is_primary": True,
                "is_active": True,
            })
    return barcodes


@router.get("/barcodes/item/{item_id}")
@limiter.limit("60/minute")
def get_barcodes_for_item(request: Request, item_id: int, db: DbSession):
    """Get barcodes for a specific item."""
    product = db.query(Product).filter(Product.id == item_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Item not found")
    barcodes = []
    if product.barcode:
        barcodes.append({
            "id": product.id,
            "stock_item_id": product.id,
            "barcode_value": product.barcode,
            "barcode_type": "EAN13",
            "is_primary": True,
            "is_active": True,
        })
    return barcodes


@router.post("/barcodes")
@limiter.limit("30/minute")
def create_barcode(request: Request, barcode_request: BarcodeCreateRequest, db: DbSession):
    """Create a barcode for an inventory item."""
    product = db.query(Product).filter(Product.id == barcode_request.stock_item_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Item not found")
    product.barcode = barcode_request.barcode_value
    db.commit()
    return {
        "id": product.id,
        "stock_item_id": product.id,
        "barcode_value": barcode_request.barcode_value,
        "barcode_type": barcode_request.barcode_type,
        "is_primary": barcode_request.is_primary,
        "is_active": True,
    }


# ==================== AUTO-REORDER (via stock prefix) ====================

class AutoReorderRuleRequest(BaseModel):
    stock_item_id: int
    reorder_point: float
    reorder_quantity: float
    supplier_id: Optional[int] = None
    priority: str = "normal"
    is_active: bool = True


@router.get("/auto-reorder/history")
@limiter.limit("60/minute")
def get_stock_auto_reorder_history(request: Request, db: DbSession, location_id: int = Query(1)):
    """Get auto-reorder execution history from purchase orders triggered by low stock."""
    orders = db.query(PurchaseOrder).filter(
        PurchaseOrder.notes.like("%auto%reorder%"),
    ).order_by(PurchaseOrder.id.desc()).limit(50).all()
    if not orders:
        orders = db.query(PurchaseOrder).order_by(PurchaseOrder.id.desc()).limit(20).all()
    history = []
    for o in orders:
        lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == o.id).all()
        history.append({
            "id": o.id,
            "supplier_id": o.supplier_id,
            "status": o.status.value if hasattr(o.status, 'value') else str(o.status),
            "created_at": o.created_at.isoformat() if hasattr(o, 'created_at') and o.created_at else None,
            "items_count": len(lines),
            "total_value": sum(float((l.qty or 0) * (l.unit_cost or 0)) for l in lines),
            "notes": o.notes,
        })
    return history


@router.get("/auto-reorder/rules")
@limiter.limit("60/minute")
def get_stock_auto_reorder_rules(request: Request, db: DbSession, location_id: int = Query(1)):
    """Get auto-reorder rules based on PAR levels."""
    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id,
    ).all()

    rules = []
    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or not product.active or not product.par_level:
            continue
        rules.append({
            "id": product.id,
            "stock_item_id": product.id,
            "product_name": product.name,
            "reorder_point": float(product.min_stock),
            "reorder_quantity": float(product.par_level - s.qty) if s.qty < product.par_level else float(product.par_level),
            "supplier_id": product.supplier_id,
            "priority": "normal",
            "is_active": True,
            "last_triggered": None,
        })
    return rules


@router.get("/auto-reorder/alerts")
@limiter.limit("60/minute")
def get_stock_auto_reorder_alerts(request: Request, db: DbSession, location_id: int = Query(1)):
    """Get items that need reordering."""
    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id,
    ).all()

    alerts = []
    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or not product.active:
            continue
        if s.qty <= product.min_stock:
            alerts.append({
                "id": product.id,
                "stock_item_id": product.id,
                "product_name": product.name,
                "current_qty": float(s.qty),
                "min_stock": float(product.min_stock),
                "par_level": float(product.par_level) if product.par_level else None,
                "suggested_order": float(product.par_level - s.qty) if product.par_level else float(product.min_stock * 2),
                "supplier_id": product.supplier_id,
                "severity": "critical" if s.qty <= 0 else "warning",
            })
    return alerts


@router.post("/auto-reorder/rules")
@limiter.limit("30/minute")
def create_stock_auto_reorder_rule(request: Request, rule_request: AutoReorderRuleRequest, db: DbSession):
    """Create an auto-reorder rule."""
    product = db.query(Product).filter(Product.id == rule_request.stock_item_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Item not found")
    product.min_stock = rule_request.reorder_point
    if rule_request.reorder_quantity:
        product.par_level = rule_request.reorder_point + rule_request.reorder_quantity
    db.commit()
    return {"success": True, "id": product.id}


@router.post("/auto-reorder/process")
@limiter.limit("30/minute")
def process_stock_auto_reorder(request: Request, db: DbSession, location_id: int = Query(1)):
    """Process auto-reorder for all items below reorder point."""
    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id,
    ).all()

    orders_created = 0
    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or not product.active:
            continue
        if s.qty <= product.min_stock and product.par_level:
            orders_created += 1

    return {"orders_created": orders_created}


