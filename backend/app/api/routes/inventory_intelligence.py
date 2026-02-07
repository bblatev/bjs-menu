"""Inventory Intelligence API — ABC Analysis, Turnover, Dead Stock, COGS, Food Cost Variance, EOQ, Snapshots, Cycle Count Scheduling.

Fills the gap vs MarketMan, Toast, Lightspeed, Revel for advanced inventory analytics.
"""

import logging
import math
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, and_, case, text, desc, asc

from app.db.session import DbSession
from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.product import Product
from app.models.location import Location
from app.models.recipe import Recipe, RecipeLine
from app.models.restaurant import Check, CheckItem

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== SCHEMAS ====================

class ABCItem(BaseModel):
    product_id: int
    product_name: str
    sku: Optional[str] = None
    category: str  # A, B, C
    total_value: float
    cumulative_pct: float
    annual_usage: float
    unit_cost: float

class ABCAnalysisResponse(BaseModel):
    location_id: int
    period_days: int
    total_inventory_value: float
    a_items: int
    b_items: int
    c_items: int
    a_value_pct: float
    b_value_pct: float
    c_value_pct: float
    items: List[ABCItem]

class TurnoverItem(BaseModel):
    product_id: int
    product_name: str
    sku: Optional[str] = None
    turnover_ratio: float
    days_on_hand: Optional[float] = None
    avg_stock: float
    total_usage: float
    status: str  # fast, normal, slow, dead

class TurnoverResponse(BaseModel):
    location_id: int
    period_days: int
    avg_turnover: float
    items: List[TurnoverItem]

class DeadStockItem(BaseModel):
    product_id: int
    product_name: str
    sku: Optional[str] = None
    current_qty: float
    current_value: float
    days_since_movement: int
    last_movement_date: Optional[str] = None
    last_movement_reason: Optional[str] = None

class DeadStockResponse(BaseModel):
    location_id: int
    threshold_days: int
    total_dead_value: float
    total_dead_items: int
    items: List[DeadStockItem]

class COGSResponse(BaseModel):
    location_id: int
    period_start: str
    period_end: str
    opening_stock_value: float
    purchases_value: float
    closing_stock_value: float
    cogs: float
    cogs_pct_of_revenue: Optional[float] = None
    revenue: Optional[float] = None
    by_category: List[Dict[str, Any]]

class FoodCostVarianceItem(BaseModel):
    product_id: int
    product_name: str
    theoretical_usage: float
    actual_usage: float
    variance: float
    variance_pct: float
    variance_value: float

class FoodCostVarianceResponse(BaseModel):
    location_id: int
    period_start: str
    period_end: str
    total_theoretical_cost: float
    total_actual_cost: float
    total_variance: float
    total_variance_pct: float
    items: List[FoodCostVarianceItem]

class EOQResponse(BaseModel):
    product_id: int
    product_name: str
    annual_demand: float
    ordering_cost: float
    holding_cost_pct: float
    unit_cost: float
    eoq: float
    orders_per_year: float
    reorder_point: float
    safety_stock: float
    total_annual_cost: float

class SnapshotCreate(BaseModel):
    location_id: int = 1
    name: Optional[str] = None
    notes: Optional[str] = None

class SnapshotResponse(BaseModel):
    id: int
    location_id: int
    name: str
    created_at: str
    total_items: int
    total_value: float
    notes: Optional[str] = None

class SnapshotCompareResponse(BaseModel):
    snapshot_a: Dict[str, Any]
    snapshot_b: Dict[str, Any]
    period_days: int
    total_value_change: float
    total_value_change_pct: float
    items_added: int
    items_removed: int
    items_changed: int
    details: List[Dict[str, Any]]

class CycleCountScheduleItem(BaseModel):
    product_id: int
    product_name: str
    abc_category: str
    frequency: str  # weekly, biweekly, monthly, quarterly
    next_count_date: str
    last_counted: Optional[str] = None

class CycleCountScheduleResponse(BaseModel):
    location_id: int
    total_items: int
    weekly_count: int
    biweekly_count: int
    monthly_count: int
    quarterly_count: int
    schedule: List[CycleCountScheduleItem]


# ==================== ENDPOINTS ====================

@router.get("/abc-analysis", response_model=ABCAnalysisResponse)
def get_abc_analysis(
    db: DbSession,
    location_id: int = Query(1),
    period_days: int = Query(90, ge=7, le=365),
    a_threshold: float = Query(0.80, ge=0.5, le=0.95),
    b_threshold: float = Query(0.95, ge=0.85, le=0.99),
):
    """ABC Analysis — classify inventory by value using Pareto principle.

    A items: top ~20% of items representing ~80% of value
    B items: next ~30% representing ~15% of value
    C items: remaining ~50% representing ~5% of value
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

    # Get usage value per product (qty consumed × unit cost)
    usage_data = (
        db.query(
            StockMovement.product_id,
            Product.name,
            Product.sku,
            Product.cost_price,
            func.sum(func.abs(StockMovement.qty_delta)).label("total_qty"),
        )
        .join(Product, Product.id == StockMovement.product_id)
        .filter(
            StockMovement.location_id == location_id,
            StockMovement.ts >= cutoff,
            StockMovement.reason.in_([
                MovementReason.SALE.value,
                MovementReason.WASTE.value,
            ]),
        )
        .group_by(StockMovement.product_id, Product.name, Product.sku, Product.cost_price)
        .all()
    )

    if not usage_data:
        return ABCAnalysisResponse(
            location_id=location_id, period_days=period_days,
            total_inventory_value=0, a_items=0, b_items=0, c_items=0,
            a_value_pct=0, b_value_pct=0, c_value_pct=0, items=[]
        )

    # Calculate total value per item
    items_with_value = []
    for row in usage_data:
        unit_cost = float(row.cost_price or 0)
        total_qty = float(row.total_qty or 0)
        total_value = total_qty * unit_cost
        items_with_value.append({
            "product_id": row.product_id,
            "product_name": row.name,
            "sku": row.sku,
            "annual_usage": total_qty * (365 / period_days),
            "unit_cost": unit_cost,
            "total_value": total_value,
        })

    # Sort by value descending
    items_with_value.sort(key=lambda x: x["total_value"], reverse=True)
    grand_total = sum(i["total_value"] for i in items_with_value)

    if grand_total == 0:
        grand_total = 1  # avoid division by zero

    # Classify
    cumulative = 0
    a_val = b_val = c_val = 0
    a_count = b_count = c_count = 0
    result_items = []
    for item in items_with_value:
        cumulative += item["total_value"]
        pct = cumulative / grand_total
        if pct <= a_threshold:
            cat = "A"
            a_val += item["total_value"]
            a_count += 1
        elif pct <= b_threshold:
            cat = "B"
            b_val += item["total_value"]
            b_count += 1
        else:
            cat = "C"
            c_val += item["total_value"]
            c_count += 1

        result_items.append(ABCItem(
            product_id=item["product_id"],
            product_name=item["product_name"],
            sku=item["sku"],
            category=cat,
            total_value=round(item["total_value"], 2),
            cumulative_pct=round(pct * 100, 1),
            annual_usage=round(item["annual_usage"], 2),
            unit_cost=round(item["unit_cost"], 2),
        ))

    return ABCAnalysisResponse(
        location_id=location_id, period_days=period_days,
        total_inventory_value=round(grand_total, 2),
        a_items=a_count, b_items=b_count, c_items=c_count,
        a_value_pct=round((a_val / grand_total) * 100, 1) if grand_total else 0,
        b_value_pct=round((b_val / grand_total) * 100, 1) if grand_total else 0,
        c_value_pct=round((c_val / grand_total) * 100, 1) if grand_total else 0,
        items=result_items,
    )


@router.get("/turnover", response_model=TurnoverResponse)
def get_inventory_turnover(
    db: DbSession,
    location_id: int = Query(1),
    period_days: int = Query(90, ge=7, le=365),
):
    """Inventory Turnover Ratio and Days on Hand per product.

    Turnover = Total Usage / Average Stock
    Days on Hand = period_days / Turnover (or stock / daily_usage)
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

    # Total outflow (sales + waste) per product
    usage = (
        db.query(
            StockMovement.product_id,
            func.sum(func.abs(StockMovement.qty_delta)).label("total_out"),
        )
        .filter(
            StockMovement.location_id == location_id,
            StockMovement.ts >= cutoff,
            StockMovement.reason.in_([
                MovementReason.SALE.value,
                MovementReason.WASTE.value,
                MovementReason.TRANSFER_OUT.value,
            ]),
        )
        .group_by(StockMovement.product_id)
        .all()
    )
    usage_map = {r.product_id: float(r.total_out) for r in usage}

    # Current stock
    stock = (
        db.query(StockOnHand.product_id, StockOnHand.qty)
        .filter(StockOnHand.location_id == location_id, StockOnHand.qty > 0)
        .all()
    )

    product_ids = set(usage_map.keys()) | {s.product_id for s in stock}
    if not product_ids:
        return TurnoverResponse(location_id=location_id, period_days=period_days, avg_turnover=0, items=[])

    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}

    items = []
    total_turnover = 0
    count = 0
    for pid in product_ids:
        p = products.get(pid)
        if not p:
            continue
        total_out = usage_map.get(pid, 0)
        current = float(next((s.qty for s in stock if s.product_id == pid), 0))
        avg_stock = (current + current) / 2  # simplified; ideally use period start+end
        if avg_stock <= 0:
            avg_stock = max(current, 0.01)

        turnover = total_out / avg_stock if avg_stock > 0 else 0
        doh = (period_days / turnover) if turnover > 0 else None

        if turnover == 0:
            status = "dead"
        elif turnover < 2:
            status = "slow"
        elif turnover < 8:
            status = "normal"
        else:
            status = "fast"

        items.append(TurnoverItem(
            product_id=pid, product_name=p.name, sku=p.sku,
            turnover_ratio=round(turnover, 2),
            days_on_hand=round(doh, 1) if doh else None,
            avg_stock=round(avg_stock, 2),
            total_usage=round(total_out, 2),
            status=status,
        ))
        total_turnover += turnover
        count += 1

    items.sort(key=lambda x: x.turnover_ratio, reverse=True)
    return TurnoverResponse(
        location_id=location_id, period_days=period_days,
        avg_turnover=round(total_turnover / max(count, 1), 2),
        items=items,
    )


@router.get("/dead-stock", response_model=DeadStockResponse)
def get_dead_stock(
    db: DbSession,
    location_id: int = Query(1),
    threshold_days: int = Query(30, ge=7, le=365),
):
    """Identify dead stock — items with no movement for N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_days)
    now = datetime.now(timezone.utc)

    # Get products with stock > 0
    on_hand = (
        db.query(StockOnHand)
        .filter(StockOnHand.location_id == location_id, StockOnHand.qty > 0)
        .all()
    )
    if not on_hand:
        return DeadStockResponse(
            location_id=location_id, threshold_days=threshold_days,
            total_dead_value=0, total_dead_items=0, items=[]
        )

    pids = [s.product_id for s in on_hand]
    stock_map = {s.product_id: s for s in on_hand}

    # Last movement per product
    last_move_subq = (
        db.query(
            StockMovement.product_id,
            func.max(StockMovement.ts).label("last_ts"),
        )
        .filter(
            StockMovement.location_id == location_id,
            StockMovement.product_id.in_(pids),
        )
        .group_by(StockMovement.product_id)
        .subquery()
    )

    last_moves = (
        db.query(last_move_subq.c.product_id, last_move_subq.c.last_ts)
        .all()
    )
    last_move_map = {r.product_id: r.last_ts for r in last_moves}

    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(pids)).all()}

    items = []
    total_dead_value = 0
    for pid in pids:
        last_ts = last_move_map.get(pid)
        if last_ts is not None and last_ts >= cutoff:
            continue  # active item

        p = products.get(pid)
        soh = stock_map.get(pid)
        if not p or not soh:
            continue

        qty = float(soh.qty)
        unit_cost = float(p.cost_price or 0)
        value = qty * unit_cost
        days_since = (now - last_ts).days if last_ts else 9999

        # Get the actual last movement reason
        last_reason = None
        if last_ts:
            lm = (
                db.query(StockMovement.reason)
                .filter(
                    StockMovement.product_id == pid,
                    StockMovement.location_id == location_id,
                    StockMovement.ts == last_ts,
                )
                .first()
            )
            if lm:
                last_reason = lm.reason

        items.append(DeadStockItem(
            product_id=pid, product_name=p.name, sku=p.sku,
            current_qty=round(qty, 2),
            current_value=round(value, 2),
            days_since_movement=days_since,
            last_movement_date=last_ts.isoformat() if last_ts else None,
            last_movement_reason=last_reason,
        ))
        total_dead_value += value

    items.sort(key=lambda x: x.current_value, reverse=True)
    return DeadStockResponse(
        location_id=location_id, threshold_days=threshold_days,
        total_dead_value=round(total_dead_value, 2),
        total_dead_items=len(items),
        items=items,
    )


@router.get("/cogs", response_model=COGSResponse)
def get_cogs_report(
    db: DbSession,
    location_id: int = Query(1),
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
):
    """Cost of Goods Sold (COGS) = Opening Stock + Purchases - Closing Stock.

    Standard restaurant accounting formula used by Toast, MarketMan, Lightspeed.
    """
    if not period_start:
        period_start = date.today() - timedelta(days=30)
    if not period_end:
        period_end = date.today()

    start_dt = datetime(period_start.year, period_start.month, period_start.day, tzinfo=timezone.utc)
    end_dt = datetime(period_end.year, period_end.month, period_end.day, 23, 59, 59, tzinfo=timezone.utc)

    # Opening stock value: sum(qty at period start × cost_price)
    # Approximation: current qty + all outflows - all inflows since start = qty at start
    products = db.query(Product).all()
    product_map = {p.id: p for p in products}

    # Current stock
    current_stock = {
        s.product_id: float(s.qty)
        for s in db.query(StockOnHand).filter(StockOnHand.location_id == location_id).all()
    }

    # Movements in period
    movements = (
        db.query(
            StockMovement.product_id,
            StockMovement.qty_delta,
            StockMovement.reason,
        )
        .filter(
            StockMovement.location_id == location_id,
            StockMovement.ts >= start_dt,
            StockMovement.ts <= end_dt,
        )
        .all()
    )

    # Calculate opening stock per product
    net_change = {}
    purchases = {}
    for m in movements:
        pid = m.product_id
        delta = float(m.qty_delta)
        net_change[pid] = net_change.get(pid, 0) + delta
        if m.reason in (MovementReason.PURCHASE.value, "purchase"):
            purchases[pid] = purchases.get(pid, 0) + delta

    # Opening = Closing - NetChange
    opening_total = 0
    closing_total = 0
    purchases_total = 0
    category_data: Dict[str, Dict[str, float]] = {}

    for p in products:
        cost = float(p.cost_price or 0)
        closing_qty = current_stock.get(p.id, 0)
        opening_qty = closing_qty - net_change.get(p.id, 0)
        purchase_qty = purchases.get(p.id, 0)

        opening_val = max(opening_qty, 0) * cost
        closing_val = max(closing_qty, 0) * cost
        purchase_val = max(purchase_qty, 0) * cost

        opening_total += opening_val
        closing_total += closing_val
        purchases_total += purchase_val

        cat = getattr(p, 'category', None) or "General"
        if cat not in category_data:
            category_data[cat] = {"opening": 0, "purchases": 0, "closing": 0}
        category_data[cat]["opening"] += opening_val
        category_data[cat]["purchases"] += purchase_val
        category_data[cat]["closing"] += closing_val

    cogs = opening_total + purchases_total - closing_total

    # Try to get revenue from checks
    revenue = None
    cogs_pct = None
    try:
        rev_result = (
            db.query(func.sum(Check.total))
            .filter(
                Check.opened_at >= start_dt,
                Check.opened_at <= end_dt,
                Check.status != "voided",
            )
            .scalar()
        )
        if rev_result:
            revenue = float(rev_result)
            cogs_pct = round((cogs / revenue) * 100, 1) if revenue > 0 else None
    except Exception:
        pass

    by_category = []
    for cat, vals in sorted(category_data.items()):
        cat_cogs = vals["opening"] + vals["purchases"] - vals["closing"]
        by_category.append({
            "category": cat,
            "opening": round(vals["opening"], 2),
            "purchases": round(vals["purchases"], 2),
            "closing": round(vals["closing"], 2),
            "cogs": round(cat_cogs, 2),
        })

    return COGSResponse(
        location_id=location_id,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        opening_stock_value=round(opening_total, 2),
        purchases_value=round(purchases_total, 2),
        closing_stock_value=round(closing_total, 2),
        cogs=round(cogs, 2),
        cogs_pct_of_revenue=cogs_pct,
        revenue=round(revenue, 2) if revenue else None,
        by_category=by_category,
    )


@router.get("/food-cost-variance", response_model=FoodCostVarianceResponse)
def get_food_cost_variance(
    db: DbSession,
    location_id: int = Query(1),
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
):
    """Theoretical vs Actual food cost variance.

    Theoretical = sum(recipe_qty × items_sold) per ingredient
    Actual = sum(stock movements: sales + waste) per ingredient
    """
    if not period_start:
        period_start = date.today() - timedelta(days=30)
    if not period_end:
        period_end = date.today()

    start_dt = datetime(period_start.year, period_start.month, period_start.day, tzinfo=timezone.utc)
    end_dt = datetime(period_end.year, period_end.month, period_end.day, 23, 59, 59, tzinfo=timezone.utc)

    # Get all recipes with their ingredient quantities
    recipes = db.query(Recipe).all()
    recipe_ingredients: Dict[int, List[Dict]] = {}  # recipe_id -> [{product_id, qty}]
    for r in recipes:
        lines = db.query(RecipeLine).filter(RecipeLine.recipe_id == r.id).all()
        recipe_ingredients[r.id] = [{"product_id": l.product_id, "qty": float(l.qty)} for l in lines]

    # Get items sold (from order lines) in period
    # Theoretical usage: for each sold item, find its recipe and multiply ingredients
    theoretical_usage: Dict[int, float] = {}  # product_id -> theoretical qty used

    try:
        # Use CheckItem which has menu_item_id and quantity
        check_items = (
            db.query(CheckItem.menu_item_id, func.sum(CheckItem.quantity).label("qty_sold"))
            .join(Check, Check.id == CheckItem.check_id)
            .filter(
                Check.opened_at >= start_dt,
                Check.opened_at <= end_dt,
                Check.status != "voided",
                CheckItem.status != "voided",
                CheckItem.menu_item_id.isnot(None),
            )
            .group_by(CheckItem.menu_item_id)
            .all()
        )

        for ci in check_items:
            # Find recipe for this menu item
            recipe = db.query(Recipe).filter(Recipe.pos_item_id == str(ci.menu_item_id)).first()
            if not recipe and ci.menu_item_id:
                # Try name match via product
                product = db.query(Product).filter(Product.id == ci.menu_item_id).first()
                if product:
                    recipe = db.query(Recipe).filter(Recipe.name == product.name).first()

            if recipe and recipe.id in recipe_ingredients:
                qty_sold = float(ci.qty_sold or 0)
                for ing in recipe_ingredients[recipe.id]:
                    pid = ing["product_id"]
                    theoretical_usage[pid] = theoretical_usage.get(pid, 0) + (ing["qty"] * qty_sold)
    except Exception as e:
        logger.warning(f"Could not compute theoretical usage: {e}")

    # Actual usage: stock movements (SALE + WASTE)
    actual_movements = (
        db.query(
            StockMovement.product_id,
            func.sum(func.abs(StockMovement.qty_delta)).label("actual_qty"),
        )
        .filter(
            StockMovement.location_id == location_id,
            StockMovement.ts >= start_dt,
            StockMovement.ts <= end_dt,
            StockMovement.reason.in_([MovementReason.SALE.value, MovementReason.WASTE.value]),
        )
        .group_by(StockMovement.product_id)
        .all()
    )
    actual_map = {r.product_id: float(r.actual_qty) for r in actual_movements}

    # Combine
    all_pids = set(theoretical_usage.keys()) | set(actual_map.keys())
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(all_pids)).all()} if all_pids else {}

    items = []
    total_theoretical = 0
    total_actual = 0
    for pid in all_pids:
        p = products.get(pid)
        if not p:
            continue
        cost = float(p.cost_price or 0)
        theo = theoretical_usage.get(pid, 0)
        actual = actual_map.get(pid, 0)
        variance = actual - theo
        variance_pct = ((variance / theo) * 100) if theo > 0 else 0
        variance_value = variance * cost

        total_theoretical += theo * cost
        total_actual += actual * cost

        items.append(FoodCostVarianceItem(
            product_id=pid,
            product_name=p.name,
            theoretical_usage=round(theo, 3),
            actual_usage=round(actual, 3),
            variance=round(variance, 3),
            variance_pct=round(variance_pct, 1),
            variance_value=round(variance_value, 2),
        ))

    items.sort(key=lambda x: abs(x.variance_value), reverse=True)
    total_variance = total_actual - total_theoretical
    total_variance_pct = ((total_variance / total_theoretical) * 100) if total_theoretical > 0 else 0

    return FoodCostVarianceResponse(
        location_id=location_id,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        total_theoretical_cost=round(total_theoretical, 2),
        total_actual_cost=round(total_actual, 2),
        total_variance=round(total_variance, 2),
        total_variance_pct=round(total_variance_pct, 1),
        items=items,
    )


@router.get("/eoq/{product_id}", response_model=EOQResponse)
def calculate_eoq(
    db: DbSession,
    product_id: int,
    ordering_cost: float = Query(25.0, ge=1, description="Cost per order placement"),
    holding_cost_pct: float = Query(0.25, ge=0.01, le=1.0, description="Annual holding cost as % of unit cost"),
    lead_time_days: int = Query(3, ge=1, le=60),
    safety_factor: float = Query(1.5, ge=1.0, le=3.0),
    period_days: int = Query(365, ge=30, le=730),
):
    """Economic Order Quantity (EOQ) — Wilson formula.

    EOQ = sqrt((2 × D × S) / H)
    Where D=annual demand, S=ordering cost, H=holding cost per unit
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

    # Annual demand
    total_usage = (
        db.query(func.sum(func.abs(StockMovement.qty_delta)))
        .filter(
            StockMovement.product_id == product_id,
            StockMovement.ts >= cutoff,
            StockMovement.reason.in_([MovementReason.SALE.value, MovementReason.WASTE.value]),
        )
        .scalar()
    )
    total_usage = float(total_usage or 0)
    annual_demand = total_usage * (365 / period_days)

    unit_cost = float(product.cost_price or 0)
    holding_cost = unit_cost * holding_cost_pct

    if annual_demand <= 0 or holding_cost <= 0:
        return EOQResponse(
            product_id=product_id, product_name=product.name,
            annual_demand=0, ordering_cost=ordering_cost,
            holding_cost_pct=holding_cost_pct, unit_cost=unit_cost,
            eoq=0, orders_per_year=0, reorder_point=0,
            safety_stock=0, total_annual_cost=0,
        )

    # Wilson EOQ formula
    eoq = math.sqrt((2 * annual_demand * ordering_cost) / holding_cost)

    orders_per_year = annual_demand / eoq if eoq > 0 else 0
    daily_demand = annual_demand / 365
    reorder_point = daily_demand * lead_time_days * safety_factor
    safety_stock = daily_demand * lead_time_days * (safety_factor - 1)

    total_annual_cost = (
        (annual_demand / eoq) * ordering_cost +
        (eoq / 2) * holding_cost
    )

    return EOQResponse(
        product_id=product_id, product_name=product.name,
        annual_demand=round(annual_demand, 2),
        ordering_cost=ordering_cost,
        holding_cost_pct=holding_cost_pct,
        unit_cost=unit_cost,
        eoq=round(eoq, 2),
        orders_per_year=round(orders_per_year, 1),
        reorder_point=round(reorder_point, 2),
        safety_stock=round(safety_stock, 2),
        total_annual_cost=round(total_annual_cost, 2),
    )


@router.post("/snapshots", response_model=SnapshotResponse)
def create_inventory_snapshot(
    db: DbSession,
    data: SnapshotCreate,
):
    """Take a point-in-time inventory snapshot for period comparison."""
    from fastapi import HTTPException
    # Validate location exists
    loc = db.query(Location).filter(Location.id == data.location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail=f"Location {data.location_id} not found")

    now = datetime.now(timezone.utc)
    name = data.name or f"Snapshot {now.strftime('%Y-%m-%d %H:%M')}"

    # Get all stock on hand
    stock = (
        db.query(StockOnHand, Product.name, Product.cost_price)
        .join(Product, Product.id == StockOnHand.product_id)
        .filter(StockOnHand.location_id == data.location_id)
        .all()
    )

    total_value = sum(float(s.StockOnHand.qty) * float(s.cost_price or 0) for s in stock)

    # Store snapshot as JSON in a simple table
    from sqlalchemy import Column, Integer, String, Text, DateTime as SADateTime, Numeric as SANumeric
    snapshot_data = [
        {
            "product_id": s.StockOnHand.product_id,
            "product_name": s.name,
            "qty": float(s.StockOnHand.qty),
            "cost_price": float(s.cost_price or 0),
            "value": float(s.StockOnHand.qty) * float(s.cost_price or 0),
        }
        for s in stock
    ]

    import json
    db.execute(
        text("""
            INSERT INTO inventory_snapshots (location_id, name, notes, snapshot_data, total_items, total_value, created_at)
            VALUES (:loc, :name, :notes, :data, :items, :value, :ts)
        """),
        {
            "loc": data.location_id,
            "name": name,
            "notes": data.notes,
            "data": json.dumps(snapshot_data),
            "items": len(snapshot_data),
            "value": round(total_value, 2),
            "ts": now,
        }
    )
    db.commit()

    # Get the ID
    result = db.execute(text("SELECT lastval()")).scalar()

    return SnapshotResponse(
        id=result,
        location_id=data.location_id,
        name=name,
        created_at=now.isoformat(),
        total_items=len(snapshot_data),
        total_value=round(total_value, 2),
        notes=data.notes,
    )


@router.get("/snapshots", response_model=List[SnapshotResponse])
def list_snapshots(
    db: DbSession,
    location_id: int = Query(1),
    limit: int = Query(20, ge=1, le=100),
):
    """List inventory snapshots."""
    rows = db.execute(
        text("SELECT id, location_id, name, notes, total_items, total_value, created_at FROM inventory_snapshots WHERE location_id = :loc ORDER BY created_at DESC LIMIT :lim"),
        {"loc": location_id, "lim": limit}
    ).fetchall()

    return [
        SnapshotResponse(
            id=r.id, location_id=r.location_id, name=r.name,
            created_at=r.created_at.isoformat() if r.created_at else "",
            total_items=r.total_items or 0,
            total_value=float(r.total_value or 0),
            notes=r.notes,
        )
        for r in rows
    ]


@router.get("/snapshots/compare", response_model=SnapshotCompareResponse)
def compare_snapshots(
    db: DbSession,
    snapshot_a_id: int = Query(...),
    snapshot_b_id: int = Query(...),
):
    """Compare two inventory snapshots."""
    import json

    row_a = db.execute(
        text("SELECT * FROM inventory_snapshots WHERE id = :id"), {"id": snapshot_a_id}
    ).fetchone()
    row_b = db.execute(
        text("SELECT * FROM inventory_snapshots WHERE id = :id"), {"id": snapshot_b_id}
    ).fetchone()

    if not row_a or not row_b:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    # JSONB is auto-deserialized by psycopg2; only parse if still a string
    raw_a = row_a.snapshot_data
    raw_b = row_b.snapshot_data
    if isinstance(raw_a, str):
        raw_a = json.loads(raw_a)
    if isinstance(raw_b, str):
        raw_b = json.loads(raw_b)

    data_a = {item["product_id"]: item for item in raw_a}
    data_b = {item["product_id"]: item for item in raw_b}

    all_pids = set(data_a.keys()) | set(data_b.keys())
    details = []
    items_added = items_removed = items_changed = 0
    total_val_a = float(row_a.total_value or 0)
    total_val_b = float(row_b.total_value or 0)

    for pid in sorted(all_pids):
        a = data_a.get(pid)
        b = data_b.get(pid)
        if a and not b:
            items_removed += 1
            details.append({
                "product_id": pid,
                "product_name": a["product_name"],
                "change": "removed",
                "qty_a": a["qty"], "qty_b": 0,
                "value_a": a["value"], "value_b": 0,
            })
        elif b and not a:
            items_added += 1
            details.append({
                "product_id": pid,
                "product_name": b["product_name"],
                "change": "added",
                "qty_a": 0, "qty_b": b["qty"],
                "value_a": 0, "value_b": b["value"],
            })
        elif a and b and a["qty"] != b["qty"]:
            items_changed += 1
            details.append({
                "product_id": pid,
                "product_name": a["product_name"],
                "change": "modified",
                "qty_a": a["qty"], "qty_b": b["qty"],
                "qty_diff": round(b["qty"] - a["qty"], 2),
                "value_a": a["value"], "value_b": b["value"],
                "value_diff": round(b["value"] - a["value"], 2),
            })

    period_days = abs((row_b.created_at - row_a.created_at).days) if row_a.created_at and row_b.created_at else 0
    val_change = total_val_b - total_val_a
    val_change_pct = ((val_change / total_val_a) * 100) if total_val_a > 0 else 0

    return SnapshotCompareResponse(
        snapshot_a={"id": snapshot_a_id, "name": row_a.name, "date": row_a.created_at.isoformat() if row_a.created_at else "", "total_value": total_val_a},
        snapshot_b={"id": snapshot_b_id, "name": row_b.name, "date": row_b.created_at.isoformat() if row_b.created_at else "", "total_value": total_val_b},
        period_days=period_days,
        total_value_change=round(val_change, 2),
        total_value_change_pct=round(val_change_pct, 1),
        items_added=items_added,
        items_removed=items_removed,
        items_changed=items_changed,
        details=details,
    )


@router.get("/cycle-count-schedule", response_model=CycleCountScheduleResponse)
def get_cycle_count_schedule(
    db: DbSession,
    location_id: int = Query(1),
    period_days: int = Query(90, ge=30, le=365),
):
    """Generate ABC-based cycle count schedule.

    A items: count weekly (high value, frequent movement)
    B items: count biweekly
    C items: count monthly
    Dead items: count quarterly
    """
    # First run ABC analysis (pass explicit values, not Query defaults)
    abc_response = get_abc_analysis(db, location_id=location_id, period_days=period_days, a_threshold=0.80, b_threshold=0.95)

    today = date.today()

    # Get last counted dates from inventory sessions
    try:
        from app.models.inventory import InventoryLine, InventorySession, SessionStatus
        last_counts = (
            db.query(
                InventoryLine.product_id,
                func.max(InventorySession.committed_at).label("last_counted"),
            )
            .join(InventorySession, InventorySession.id == InventoryLine.session_id)
            .filter(
                InventorySession.location_id == location_id,
                InventorySession.status == SessionStatus.COMMITTED,
            )
            .group_by(InventoryLine.product_id)
            .all()
        )
        last_count_map = {r.product_id: r.last_counted for r in last_counts}
    except Exception:
        last_count_map = {}

    schedule = []
    weekly = biweekly = monthly = quarterly = 0

    for item in abc_response.items:
        if item.category == "A":
            freq = "weekly"
            next_date = today + timedelta(days=7)
            weekly += 1
        elif item.category == "B":
            freq = "biweekly"
            next_date = today + timedelta(days=14)
            biweekly += 1
        else:
            freq = "monthly"
            next_date = today + timedelta(days=30)
            monthly += 1

        lc = last_count_map.get(item.product_id)
        schedule.append(CycleCountScheduleItem(
            product_id=item.product_id,
            product_name=item.product_name,
            abc_category=item.category,
            frequency=freq,
            next_count_date=next_date.isoformat(),
            last_counted=lc.isoformat() if lc else None,
        ))

    # Add dead stock as quarterly
    dead_response = get_dead_stock(db, location_id=location_id, threshold_days=60)  # type: ignore[arg-type]
    dead_pids = {i.product_id for i in dead_response.items}
    existing_pids = {i.product_id for i in schedule}
    for di in dead_response.items:
        if di.product_id not in existing_pids:
            quarterly += 1
            lc = last_count_map.get(di.product_id)
            schedule.append(CycleCountScheduleItem(
                product_id=di.product_id,
                product_name=di.product_name,
                abc_category="D",
                frequency="quarterly",
                next_count_date=(today + timedelta(days=90)).isoformat(),
                last_counted=lc.isoformat() if lc else None,
            ))

    return CycleCountScheduleResponse(
        location_id=location_id,
        total_items=len(schedule),
        weekly_count=weekly,
        biweekly_count=biweekly,
        monthly_count=monthly,
        quarterly_count=quarterly,
        schedule=schedule,
    )
