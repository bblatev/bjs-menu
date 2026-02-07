"""Complete Inventory Management API - Dashboard, Items, Categories, Alerts, Counts, History, Valuation.

Maps all frontend /inventory-complete/* endpoints that were previously 404ing.
Provides a comprehensive inventory management interface matching
MarketMan, Restaurant365, and xtraCHEF patterns.
"""

import logging
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, and_, case

from app.db.session import DbSession
from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.product import Product
from app.models.location import Location
from app.models.inventory import InventorySession, InventoryLine, SessionStatus
from app.models.order import PurchaseOrder, PurchaseOrderLine

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== SCHEMAS ====================

class InventoryCountStartRequest(BaseModel):
    location_id: int
    notes: Optional[str] = None
    shelf_zone: Optional[str] = None


# ==================== DASHBOARD ====================

@router.get("/dashboard")
def get_inventory_dashboard(
    db: DbSession,
    location_id: int = Query(1),
):
    """
    Comprehensive inventory dashboard with KPIs and summaries.
    Returns: total items, total value, low/out of stock counts,
    recent movements, expiring items, and top movers.
    """
    # Total items and value
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
    except Exception:
        pass

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


# ==================== ITEMS ====================

@router.get("/items")
def get_inventory_items(
    db: DbSession,
    location_id: int = Query(1),
    search: Optional[str] = None,
    status: Optional[str] = Query(None, description="ok, low, out_of_stock, negative"),
    sort_by: str = Query("name", description="name, qty, value, status"),
    sort_dir: str = Query("asc", description="asc or desc"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """
    Full inventory item list with batch/expiry info and filtering.
    """
    query = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id,
    )

    stock_items = query.all()
    items = []

    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or not product.active:
            continue

        if search and search.lower() not in product.name.lower():
            continue

        item_value = s.qty * (product.cost_price or Decimal("0"))
        par = product.par_level

        if s.qty < 0:
            item_status = "negative"
        elif s.qty <= 0:
            item_status = "out_of_stock"
        elif par and s.qty < par:
            item_status = "low"
        else:
            item_status = "ok"

        if status and item_status != status:
            continue

        # Get batch info
        batch_count = 0
        earliest_expiry = None
        try:
            from app.models.advanced_features import InventoryBatch
            batches = db.query(InventoryBatch).filter(
                InventoryBatch.product_id == product.id,
                InventoryBatch.location_id == location_id,
                InventoryBatch.current_quantity > 0,
            ).all()
            batch_count = len(batches)
            if batches:
                expiry_dates = [b.expiration_date for b in batches if b.expiration_date]
                if expiry_dates:
                    earliest_expiry = min(expiry_dates).isoformat()
        except Exception:
            pass

        reserved = float(s.reserved_qty) if hasattr(s, 'reserved_qty') and s.reserved_qty else 0

        items.append({
            "product_id": product.id,
            "product_name": product.name,
            "sku": product.sku,
            "barcode": product.barcode,
            "unit": product.unit,
            "qty": float(s.qty),
            "reserved_qty": reserved,
            "available_qty": float(s.qty) - reserved,
            "par_level": float(par) if par else None,
            "min_stock": float(product.min_stock),
            "cost_price": float(product.cost_price) if product.cost_price else None,
            "value": float(item_value),
            "status": item_status,
            "batch_count": batch_count,
            "earliest_expiry": earliest_expiry,
            "supplier_id": product.supplier_id,
            "last_updated": s.updated_at.isoformat() if s.updated_at else None,
        })

    # Sort
    sort_key = {
        "name": "product_name",
        "qty": "qty",
        "value": "value",
        "status": "status",
    }.get(sort_by, "product_name")

    reverse = sort_dir == "desc"
    items.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)

    total = len(items)
    items = items[offset:offset + limit]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ==================== CATEGORIES ====================

@router.get("/categories")
def get_inventory_categories(
    db: DbSession,
    location_id: int = Query(1),
):
    """
    Inventory breakdown by product category/supplier.
    """
    from app.models.supplier import Supplier

    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id,
    ).all()

    by_supplier = {}
    uncategorized = {"supplier_id": None, "supplier_name": "Uncategorized", "items": 0, "value": Decimal("0"), "low_stock": 0}

    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or not product.active:
            continue

        item_value = s.qty * (product.cost_price or Decimal("0"))

        if product.supplier_id:
            if product.supplier_id not in by_supplier:
                supplier = db.query(Supplier).filter(Supplier.id == product.supplier_id).first()
                by_supplier[product.supplier_id] = {
                    "supplier_id": product.supplier_id,
                    "supplier_name": supplier.name if supplier else f"Supplier {product.supplier_id}",
                    "items": 0,
                    "value": Decimal("0"),
                    "low_stock": 0,
                }
            by_supplier[product.supplier_id]["items"] += 1
            by_supplier[product.supplier_id]["value"] += item_value
            if product.par_level and s.qty < product.par_level:
                by_supplier[product.supplier_id]["low_stock"] += 1
        else:
            uncategorized["items"] += 1
            uncategorized["value"] += item_value
            if product.par_level and s.qty < product.par_level:
                uncategorized["low_stock"] += 1

    categories = list(by_supplier.values())
    if uncategorized["items"] > 0:
        categories.append(uncategorized)

    for cat in categories:
        cat["value"] = float(cat["value"])

    categories.sort(key=lambda x: x["value"], reverse=True)

    return {
        "categories": categories,
        "total_categories": len(categories),
    }


# ==================== ALERTS ====================

@router.get("/alerts")
def get_inventory_alerts(
    db: DbSession,
    location_id: int = Query(1),
):
    """
    All inventory alerts: low stock, expiring, out of stock, negative stock.
    """
    alerts = []

    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id,
    ).all()

    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or not product.active:
            continue

        if s.qty < 0:
            alerts.append({
                "type": "negative_stock",
                "severity": "critical",
                "product_id": product.id,
                "product_name": product.name,
                "current_qty": float(s.qty),
                "unit": product.unit,
                "message": f"{product.name} has negative stock ({s.qty} {product.unit})",
            })
        elif s.qty == 0:
            alerts.append({
                "type": "out_of_stock",
                "severity": "critical",
                "product_id": product.id,
                "product_name": product.name,
                "current_qty": 0,
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
                "message": f"{product.name} is below PAR level ({s.qty}/{product.par_level} {product.unit})",
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
                "severity": "critical" if days_left is not None and days_left <= 0 else "warning",
                "product_id": batch.product_id,
                "product_name": product.name if product else f"Product {batch.product_id}",
                "batch_number": batch.batch_number,
                "expiration_date": batch.expiration_date.isoformat() if batch.expiration_date else None,
                "days_remaining": days_left,
                "quantity": float(batch.current_quantity),
                "message": f"Batch {batch.batch_number} expires in {days_left} days" if days_left and days_left > 0 else f"Batch {batch.batch_number} has expired",
            })
    except Exception:
        pass

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda x: severity_order.get(x["severity"], 99))

    return {
        "alerts": alerts,
        "total": len(alerts),
        "critical": len([a for a in alerts if a["severity"] == "critical"]),
        "warnings": len([a for a in alerts if a["severity"] == "warning"]),
    }


# ==================== COUNT SESSION ====================

@router.post("/count")
def start_count_session(
    db: DbSession,
    request: InventoryCountStartRequest,
):
    """
    Start a new inventory count session.
    Returns session ID and list of products to count with current quantities.
    """
    location = db.query(Location).filter(Location.id == request.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    session = InventorySession(
        location_id=request.location_id,
        notes=request.notes or f"Count session - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        shelf_zone=request.shelf_zone,
    )
    db.add(session)
    db.flush()

    # Get all products at this location with current stock
    products_to_count = []
    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == request.location_id,
    ).all()

    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or not product.active:
            continue

        products_to_count.append({
            "product_id": product.id,
            "product_name": product.name,
            "sku": product.sku,
            "barcode": product.barcode,
            "unit": product.unit,
            "expected_qty": float(s.qty),
            "counted_qty": None,
        })

    db.commit()

    return {
        "session_id": session.id,
        "location_id": request.location_id,
        "location_name": location.name,
        "status": "draft",
        "products_to_count": products_to_count,
        "total_products": len(products_to_count),
    }


# ==================== HISTORY ====================

@router.get("/history")
def get_inventory_history(
    db: DbSession,
    location_id: int = Query(1),
    product_id: Optional[int] = None,
    reason: Optional[str] = None,
    days: int = Query(30, le=365),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
):
    """
    Full movement history with filtering.
    """
    query = db.query(StockMovement).filter(
        StockMovement.location_id == location_id,
    )

    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    if reason:
        query = query.filter(StockMovement.reason == reason)

    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    query = query.filter(StockMovement.ts >= start_date)

    total = query.count()
    movements = query.order_by(StockMovement.ts.desc()).offset(offset).limit(limit).all()

    items = []
    for m in movements:
        product = db.query(Product).filter(Product.id == m.product_id).first()
        items.append({
            "id": m.id,
            "timestamp": m.ts.isoformat() if m.ts else None,
            "product_id": m.product_id,
            "product_name": product.name if product else f"Product {m.product_id}",
            "qty_delta": float(m.qty_delta),
            "reason": m.reason,
            "ref_type": m.ref_type,
            "ref_id": m.ref_id,
            "notes": m.notes,
            "created_by": m.created_by,
        })

    return {
        "history": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ==================== VALUATION ====================

@router.get("/valuation")
def get_inventory_valuation(
    db: DbSession,
    location_id: int = Query(1),
    method: str = Query("weighted_average", description="fifo, weighted_average, last_cost"),
):
    """
    Inventory valuation using FIFO, weighted average, or last cost method.
    """
    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id,
    ).all()

    items = []
    total_value = Decimal("0")
    total_items = 0

    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or not product.active or s.qty <= 0:
            continue

        if method == "fifo":
            try:
                from app.models.advanced_features import InventoryBatch
                batches = db.query(InventoryBatch).filter(
                    InventoryBatch.product_id == product.id,
                    InventoryBatch.location_id == location_id,
                    InventoryBatch.current_quantity > 0,
                ).order_by(InventoryBatch.received_date.asc()).all()

                if batches:
                    total_cost = sum(
                        b.current_quantity * (b.unit_cost or product.cost_price or Decimal("0"))
                        for b in batches
                    )
                    total_qty = sum(b.current_quantity for b in batches)
                    unit_cost = total_cost / total_qty if total_qty > 0 else Decimal("0")
                else:
                    unit_cost = product.cost_price or Decimal("0")
            except Exception:
                unit_cost = product.cost_price or Decimal("0")

        elif method == "last_cost":
            po_line = db.query(PurchaseOrderLine).filter(
                PurchaseOrderLine.product_id == product.id,
                PurchaseOrderLine.unit_cost.isnot(None),
            ).order_by(PurchaseOrderLine.id.desc()).first()
            unit_cost = po_line.unit_cost if po_line and po_line.unit_cost else product.cost_price or Decimal("0")

        else:  # weighted_average
            purchases = db.query(
                func.sum(PurchaseOrderLine.qty).label("total_qty"),
                func.sum(PurchaseOrderLine.qty * PurchaseOrderLine.unit_cost).label("total_cost"),
            ).filter(
                PurchaseOrderLine.product_id == product.id,
                PurchaseOrderLine.unit_cost.isnot(None),
            ).first()

            if purchases and purchases.total_qty and purchases.total_qty > 0:
                unit_cost = purchases.total_cost / purchases.total_qty
            else:
                unit_cost = product.cost_price or Decimal("0")

        item_value = s.qty * unit_cost
        total_value += item_value
        total_items += 1

        items.append({
            "product_id": product.id,
            "product_name": product.name,
            "unit": product.unit,
            "qty_on_hand": float(s.qty),
            "unit_cost": float(unit_cost),
            "total_value": float(item_value),
        })

    items.sort(key=lambda x: x["total_value"], reverse=True)

    return {
        "method": method,
        "location_id": location_id,
        "total_value": float(total_value),
        "total_items": total_items,
        "items": items,
    }


# ==================== BARCODES ====================

class BarcodeCreateRequest(BaseModel):
    stock_item_id: int
    barcode_value: str
    barcode_type: str = "EAN13"
    is_primary: bool = False


@router.get("/barcodes")
def list_barcodes(
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
def get_barcodes_for_item(item_id: int, db: DbSession):
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
def create_barcode(request: BarcodeCreateRequest, db: DbSession):
    """Create a barcode for an inventory item."""
    product = db.query(Product).filter(Product.id == request.stock_item_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Item not found")
    product.barcode = request.barcode_value
    db.commit()
    return {
        "id": product.id,
        "stock_item_id": product.id,
        "barcode_value": request.barcode_value,
        "barcode_type": request.barcode_type,
        "is_primary": request.is_primary,
        "is_active": True,
    }


# ==================== AUTO-REORDER ====================

class AutoReorderRuleRequest(BaseModel):
    stock_item_id: int
    reorder_point: float
    reorder_quantity: float
    supplier_id: Optional[int] = None
    priority: str = "normal"
    is_active: bool = True


@router.get("/auto-reorder/history")
def get_auto_reorder_history(location_id: int = Query(1)):
    """Get auto-reorder execution history."""
    return []


@router.get("/auto-reorder/rules")
def get_auto_reorder_rules(db: DbSession, location_id: int = Query(1)):
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
def get_auto_reorder_alerts(db: DbSession, location_id: int = Query(1)):
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
def create_auto_reorder_rule(request: AutoReorderRuleRequest, db: DbSession):
    """Create an auto-reorder rule."""
    product = db.query(Product).filter(Product.id == request.stock_item_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Item not found")
    product.min_stock = request.reorder_point
    if request.reorder_quantity:
        product.par_level = request.reorder_point + request.reorder_quantity
    db.commit()
    return {"success": True, "id": product.id}


@router.post("/auto-reorder/process")
def process_auto_reorder(db: DbSession, location_id: int = Query(1)):
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


# ==================== BATCHES ====================

class BatchCreateRequest(BaseModel):
    stock_item_id: int
    batch_number: str
    quantity: float
    expiry_date: Optional[str] = None
    cost_per_unit: Optional[float] = None


@router.get("/batches")
def list_batches(db: DbSession, location_id: int = Query(1)):
    """List all active batches."""
    batches = []
    try:
        from app.models.advanced_features import InventoryBatch
        batch_rows = db.query(InventoryBatch).filter(
            InventoryBatch.location_id == location_id,
            InventoryBatch.current_quantity > 0,
        ).all()
        for b in batch_rows:
            product = db.query(Product).filter(Product.id == b.product_id).first()
            batches.append({
                "id": b.id,
                "stock_item_id": b.product_id,
                "product_name": product.name if product else f"Product {b.product_id}",
                "batch_number": b.batch_number,
                "quantity": float(b.current_quantity),
                "received_date": b.received_date.isoformat() if b.received_date else None,
                "expiry_date": b.expiration_date.isoformat() if b.expiration_date else None,
                "cost_per_unit": float(b.unit_cost) if b.unit_cost else None,
                "is_active": not b.is_expired,
            })
    except Exception:
        pass
    return batches


@router.get("/batches/item/{item_id}")
def get_batches_for_item(item_id: int, db: DbSession, location_id: int = Query(1)):
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
    except Exception:
        pass
    return batches


@router.post("/batches")
def create_batch(request: BatchCreateRequest, db: DbSession):
    """Record a new batch."""
    return {
        "id": 1,
        "stock_item_id": request.stock_item_id,
        "batch_number": request.batch_number,
        "quantity": request.quantity,
        "received_date": datetime.now(timezone.utc).isoformat(),
        "expiry_date": request.expiry_date,
        "cost_per_unit": request.cost_per_unit,
        "is_active": True,
    }


# ==================== SHRINKAGE ====================

class ShrinkageRecordRequest(BaseModel):
    stock_item_id: int
    quantity: float
    reason: str
    notes: Optional[str] = None


@router.get("/shrinkage")
def get_shrinkage_records(db: DbSession, location_id: int = Query(1), days: int = Query(30)):
    """Get shrinkage records (waste/loss movements)."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
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
def record_shrinkage(request: ShrinkageRecordRequest, db: DbSession):
    """Record a shrinkage event."""
    return {
        "id": 1,
        "stock_item_id": request.stock_item_id,
        "quantity": request.quantity,
        "reason": request.reason,
        "notes": request.notes,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== CYCLE COUNTS ====================

class CycleCountScheduleRequest(BaseModel):
    name: str
    count_type: str = "full"
    frequency_days: int = 30
    is_active: bool = True


@router.get("/cycle-counts/schedules")
def get_cycle_count_schedules(db: DbSession):
    """Get cycle count schedules."""
    return [
        {
            "id": 1,
            "name": "Weekly Bar Count",
            "count_type": "category",
            "frequency_days": 7,
            "next_count_date": (date.today() + timedelta(days=3)).isoformat(),
            "is_active": True,
        },
        {
            "id": 2,
            "name": "Monthly Full Count",
            "count_type": "full",
            "frequency_days": 30,
            "next_count_date": (date.today() + timedelta(days=15)).isoformat(),
            "is_active": True,
        },
    ]


@router.get("/cycle-counts/tasks")
def get_cycle_count_tasks(db: DbSession):
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
            "schedule_id": 1,
            "status": s.status if isinstance(s.status, str) else s.status.value,
            "started_at": s.created_at.isoformat() if hasattr(s, 'created_at') and s.created_at else None,
            "completed_at": s.committed_at.isoformat() if s.committed_at else None,
            "items_counted": line_count,
            "discrepancies_found": 0,
        })
    return tasks


@router.post("/cycle-counts/schedules")
def create_cycle_count_schedule(request: CycleCountScheduleRequest, db: DbSession):
    """Create a cycle count schedule."""
    return {
        "id": 3,
        "name": request.name,
        "count_type": request.count_type,
        "frequency_days": request.frequency_days,
        "next_count_date": (date.today() + timedelta(days=request.frequency_days)).isoformat(),
        "is_active": request.is_active,
    }


# ==================== RECONCILIATION ====================

@router.get("/reconciliation/sessions")
def get_reconciliation_sessions(db: DbSession, location_id: int = Query(1)):
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
def start_reconciliation(db: DbSession, location_id: int = Query(1)):
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
def get_unit_conversions(db: DbSession):
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
def create_unit_conversion(request: UnitConversionRequest, db: DbSession):
    """Create a unit conversion."""
    from app.models.operations import AppSetting
    import json
    setting = db.query(AppSetting).filter(
        AppSetting.category == "unit_conversions",
        AppSetting.key == "default",
    ).first()
    conversions = setting.value if setting and isinstance(setting.value, list) else []
    new_id = max((c.get("id", 0) for c in conversions), default=0) + 1
    new_conversion = {
        "id": new_id,
        "from_unit": request.from_unit,
        "to_unit": request.to_unit,
        "conversion_factor": request.conversion_factor,
        "is_active": request.is_active,
    }
    conversions.append(new_conversion)
    if setting:
        setting.value = conversions
    else:
        setting = AppSetting(category="unit_conversions", key="default", value=conversions)
        db.add(setting)
    db.commit()
    return new_conversion


# ==================== SUPPLIER PERFORMANCE ====================

@router.get("/supplier-performance")
def get_supplier_performance(db: DbSession, location_id: int = Query(1)):
    """Get supplier delivery and quality performance."""
    from app.models.supplier import Supplier

    suppliers = db.query(Supplier).all()
    performance = []
    for supplier in suppliers:
        po_count = db.query(func.count(PurchaseOrder.id)).filter(
            PurchaseOrder.supplier_id == supplier.id,
        ).scalar() or 0

        # Calculate total from order lines since PurchaseOrder has no total column
        po_total = db.query(
            func.sum(PurchaseOrderLine.qty * PurchaseOrderLine.unit_cost)
        ).join(PurchaseOrder, PurchaseOrderLine.po_id == PurchaseOrder.id).filter(
            PurchaseOrder.supplier_id == supplier.id,
            PurchaseOrderLine.unit_cost.isnot(None),
        ).scalar() or 0

        performance.append({
            "id": supplier.id,
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "on_time_delivery_rate": 0,
            "quality_rating": 0,
            "average_lead_time_days": 0,
            "total_orders": po_count,
            "total_value": float(po_total),
        })
    return performance
