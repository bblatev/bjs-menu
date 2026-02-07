"""Price tracking API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.invoice import PriceAlert as PriceAlertModel, PriceHistory as PriceHistoryModel
from app.models.operations import AppSetting

router = APIRouter()


@router.get("/alerts")
async def get_price_alerts(db: DbSession, date_range: str = Query("week"), acknowledged: bool = Query(None)):
    """Get price alerts."""
    query = db.query(PriceAlertModel).filter(PriceAlertModel.is_active == True)
    alerts = query.order_by(PriceAlertModel.created_at.desc()).all()
    result = []
    for a in alerts:
        result.append({
            "id": str(a.id),
            "ingredient": a.product.name if a.product else "Unknown",
            "supplier": a.supplier.name if a.supplier else "Unknown",
            "old_price": float(a.threshold_amount or 0),
            "new_price": float(a.max_price or 0),
            "change_pct": float(a.threshold_percent or 0),
            "detected_at": a.last_triggered_at.isoformat() if a.last_triggered_at else a.created_at.isoformat() if a.created_at else None,
            "acknowledged": not a.is_active,
            "alert_type": a.alert_type,
        })
    return result


@router.post("/alerts/acknowledge-all")
async def acknowledge_all_alerts(db: DbSession):
    """Acknowledge all alerts."""
    count = db.query(PriceAlertModel).filter(PriceAlertModel.is_active == True).update({"is_active": False})
    db.commit()
    return {"success": True, "acknowledged_count": count}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, db: DbSession):
    """Acknowledge a specific alert."""
    alert = db.query(PriceAlertModel).filter(PriceAlertModel.id == int(alert_id)).first()
    if alert:
        alert.is_active = False
        db.commit()
    return {"success": True}


@router.get("/alert-rules")
async def get_alert_rules(db: DbSession):
    """Get price alert rules."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "price_tracker",
        AppSetting.key == "alert_rules",
    ).first()
    if setting and setting.value:
        return setting.value
    return []


@router.post("/alert-rules")
async def create_alert_rule(rule: dict, db: DbSession):
    """Create an alert rule."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "price_tracker",
        AppSetting.key == "alert_rules",
    ).first()
    rules = setting.value if setting and setting.value else []
    new_id = str(len(rules) + 1)
    rule["id"] = new_id
    rules.append(rule)
    if setting:
        setting.value = rules
    else:
        setting = AppSetting(category="price_tracker", key="alert_rules", value=rules)
        db.add(setting)
    db.commit()
    return {"success": True, "id": new_id}


@router.put("/alert-rules/{rule_id}")
async def update_alert_rule(rule_id: str, rule: dict, db: DbSession):
    """Update an alert rule."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "price_tracker",
        AppSetting.key == "alert_rules",
    ).first()
    if not setting or not setting.value:
        return {"success": False}
    rules = setting.value
    for i, r in enumerate(rules):
        if r.get("id") == rule_id:
            rule["id"] = rule_id
            rules[i] = rule
            setting.value = rules
            db.commit()
            return {"success": True}
    return {"success": False}


@router.delete("/alert-rules/{rule_id}")
async def delete_alert_rule(rule_id: str, db: DbSession):
    """Delete an alert rule."""
    setting = db.query(AppSetting).filter(
        AppSetting.category == "price_tracker",
        AppSetting.key == "alert_rules",
    ).first()
    if setting and setting.value:
        setting.value = [r for r in setting.value if r.get("id") != rule_id]
        db.commit()
    return {"success": True}


@router.get("/history")
async def get_price_history(db: DbSession, date_range: str = Query("30d")):
    """Get price history for tracked items."""
    from app.models.product import Product
    from app.models.supplier import Supplier

    # Group price history by product
    products_with_history = (
        db.query(PriceHistoryModel.product_id)
        .group_by(PriceHistoryModel.product_id)
        .all()
    )
    result = []
    for (product_id,) in products_with_history:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            continue
        entries = (
            db.query(PriceHistoryModel)
            .filter(PriceHistoryModel.product_id == product_id)
            .order_by(PriceHistoryModel.recorded_at.desc())
            .limit(20)
            .all()
        )
        if not entries:
            continue
        prices = [{"date": e.recorded_at.strftime("%Y-%m-%d") if e.recorded_at else None, "price": float(e.price)} for e in entries]
        price_values = [float(e.price) for e in entries]
        current_price = price_values[0] if price_values else 0
        avg_price = sum(price_values) / len(price_values) if price_values else 0
        min_price = min(price_values) if price_values else 0
        max_price = max(price_values) if price_values else 0
        volatility = round(((max_price - min_price) / avg_price * 100) if avg_price > 0 else 0, 1)

        supplier = entries[0].supplier if entries[0].supplier else None
        result.append({
            "id": product_id,
            "itemName": product.name,
            "category": product.category or "Other",
            "supplier": supplier.name if supplier else "Unknown",
            "prices": prices,
            "currentPrice": current_price,
            "avgPrice": round(avg_price, 2),
            "minPrice": min_price,
            "maxPrice": max_price,
            "volatility": volatility,
        })
    return result


@router.get("/supplier-comparisons")
async def get_supplier_comparisons(db: DbSession):
    """Compare prices across suppliers for same items."""
    from app.models.product import Product
    from sqlalchemy import distinct

    # Find products with multiple suppliers
    product_ids = (
        db.query(PriceHistoryModel.product_id)
        .group_by(PriceHistoryModel.product_id)
        .having(func.count(distinct(PriceHistoryModel.supplier_id)) > 1)
        .all()
    )
    result = []
    for (product_id,) in product_ids:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            continue
        # Get latest price per supplier
        from sqlalchemy import desc
        supplier_prices = (
            db.query(PriceHistoryModel)
            .filter(PriceHistoryModel.product_id == product_id)
            .order_by(PriceHistoryModel.recorded_at.desc())
            .all()
        )
        seen_suppliers = {}
        for sp in supplier_prices:
            if sp.supplier_id not in seen_suppliers:
                seen_suppliers[sp.supplier_id] = sp
        suppliers = []
        for sp in seen_suppliers.values():
            suppliers.append({
                "name": sp.supplier.name if sp.supplier else "Unknown",
                "price": float(sp.price),
                "lastUpdated": sp.recorded_at.strftime("%Y-%m-%d") if sp.recorded_at else None,
            })
        prices = [s["price"] for s in suppliers]
        best_price = min(prices) if prices else 0
        result.append({
            "itemName": product.name,
            "category": product.category or "Other",
            "suppliers": suppliers,
            "bestPrice": best_price,
            "currentSupplier": suppliers[0]["name"] if suppliers else None,
            "potentialSavings": round(max(prices) - best_price, 2) if len(prices) > 1 else 0,
        })
    return result


@router.get("/category-trends")
async def get_category_trends(db: DbSession, date_range: str = Query("30d")):
    """Get price trends by category."""
    from app.models.product import Product
    # Compute from price history records
    entries = db.query(PriceHistoryModel).order_by(PriceHistoryModel.recorded_at.desc()).limit(500).all()
    if not entries:
        return []
    categories = {}
    for e in entries:
        product = db.query(Product).filter(Product.id == e.product_id).first()
        cat = product.category if product else "Other"
        if cat not in categories:
            categories[cat] = {"prices": [], "items": set()}
        categories[cat]["prices"].append(float(e.price))
        categories[cat]["items"].add(e.product_id)
    result = []
    for cat, data in categories.items():
        avg_price = sum(data["prices"]) / len(data["prices"]) if data["prices"] else 0
        result.append({
            "category": cat,
            "currentAvg": round(avg_price, 2),
            "previousAvg": round(avg_price, 2),
            "changePercent": 0,
            "itemCount": len(data["items"]),
            "topMover": None,
            "topMoverChange": 0,
        })
    return result


@router.get("/budget-impacts")
async def get_budget_impacts(db: DbSession, date_range: str = Query("30d")):
    """Get budget impact analysis from price changes."""
    # Compute from price alerts
    alerts = db.query(PriceAlertModel).filter(PriceAlertModel.is_active == True).all()
    if not alerts:
        return []
    # Group by product category
    from app.models.product import Product
    impacts = {}
    for a in alerts:
        product = db.query(Product).filter(Product.id == a.product_id).first()
        cat = product.category if product else "Other"
        if cat not in impacts:
            impacts[cat] = {"budgeted": 0, "projected": 0}
        impacts[cat]["projected"] += float(a.threshold_amount or 0)
    result = []
    for cat, data in impacts.items():
        variance = data["projected"] - data["budgeted"]
        result.append({
            "category": cat,
            "budgeted": data["budgeted"],
            "projected": data["projected"],
            "variance": variance,
            "variancePercent": round((variance / data["budgeted"]) * 100, 1) if data["budgeted"] > 0 else 0,
        })
    return result
