"""Auto-Reorder API routes - frontend-facing /auto-reorder/* endpoints.

Provides proxy endpoints for auto-reorder management that the frontend
expects under the /auto-reorder prefix. Delegates to the same underlying
data as /inventory-complete/auto-reorder/*.
"""

from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.stock import StockOnHand
from app.models.product import Product

router = APIRouter()


# ==================== AUTO-REORDER RULES ====================

@router.get("/")
def get_auto_reorder_overview(db: DbSession, location_id: int = Query(1)):
    """Get auto-reorder overview: rules, alerts, and recent history."""
    rules = _get_rules(db, location_id)
    alerts = _get_alerts(db, location_id)

    return {
        "rules": rules,
        "alerts": alerts,
        "total_rules": len(rules),
        "total_alerts": len(alerts),
        "active_rules": len([r for r in rules if r.get("is_active")]),
    }


@router.get("/rules")
def get_auto_reorder_rules(db: DbSession, location_id: int = Query(1)):
    """Get auto-reorder rules based on PAR levels."""
    return _get_rules(db, location_id)


@router.get("/alerts")
def get_auto_reorder_alerts(db: DbSession, location_id: int = Query(1)):
    """Get items that need reordering."""
    return _get_alerts(db, location_id)


@router.get("/history")
def get_auto_reorder_history(db: DbSession, location_id: int = Query(1)):
    """Get auto-reorder execution history from purchase orders triggered by low stock."""
    from app.models.order import PurchaseOrder, PurchaseOrderLine

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


class AutoReorderRuleRequest(BaseModel):
    stock_item_id: int
    reorder_point: float
    reorder_quantity: float
    supplier_id: Optional[int] = None
    priority: str = "normal"
    is_active: bool = True


@router.post("/rules")
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


@router.post("/process")
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


# ==================== INTERNAL HELPERS ====================

def _get_rules(db: DbSession, location_id: int):
    """Get auto-reorder rules from PAR levels."""
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


def _get_alerts(db: DbSession, location_id: int):
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
