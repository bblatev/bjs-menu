"""Menu Engineering routes - analyzes real menu items and order data."""

from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query
from sqlalchemy import func

from app.db.session import DbSession
from app.models.restaurant import MenuItem as MenuItemModel, GuestOrder

router = APIRouter()


def _build_engineering_items(db: DbSession, days: int = 30):
    """Build menu engineering analysis from real menu items and order data."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    items = db.query(MenuItemModel).filter(MenuItemModel.available == True).all()
    if not items:
        return []

    # Count sold items from GuestOrder.items JSON
    orders = db.query(GuestOrder).filter(GuestOrder.created_at >= cutoff).all()
    sold_counts = {}
    for order in orders:
        if not order.items:
            continue
        for oi in order.items:
            item_id = oi.get("menu_item_id") or oi.get("id")
            qty = oi.get("quantity", 1)
            if item_id:
                sold_counts[item_id] = sold_counts.get(item_id, 0) + qty

    # Calculate metrics per item
    total_sold = sum(sold_counts.values()) if sold_counts else 1

    # First pass: compute per-item metrics
    item_metrics = []
    for item in items:
        price = float(item.price or 0)
        cost = float(item.base_price or 0)
        food_cost_pct = (cost / price * 100) if price > 0 else 0
        profit_margin = 100 - food_cost_pct
        sold = sold_counts.get(item.id, 0)
        revenue = price * sold
        profit = (price - cost) * sold
        popularity = min(100, int((sold / total_sold) * 100 * len(items))) if total_sold > 0 else 0
        item_metrics.append({
            "item": item, "food_cost_pct": food_cost_pct, "profit_margin": profit_margin,
            "sold": sold, "revenue": revenue, "profit": profit, "popularity": popularity,
            "price": price, "cost": cost,
        })

    # Compute averages from actual data for quadrant classification
    avg_food_cost = (sum(m["food_cost_pct"] for m in item_metrics) / len(item_metrics)) if item_metrics else 0
    avg_popularity = (sum(m["popularity"] for m in item_metrics) / len(item_metrics)) if item_metrics else 0

    result = []
    for m in item_metrics:
        item = m["item"]
        food_cost_pct = m["food_cost_pct"]
        popularity = m["popularity"]

        high_profit = food_cost_pct < avg_food_cost
        high_popularity = popularity >= avg_popularity

        if high_profit and high_popularity:
            quadrant = "star"
        elif high_profit and not high_popularity:
            quadrant = "puzzle"
        elif not high_profit and high_popularity:
            quadrant = "plow_horse"
        else:
            quadrant = "dog"

        # Recommendations based on quadrant
        recs = {
            "star": ["Keep promoting", "Consider combo deals"],
            "puzzle": ["Increase visibility on menu", "Promote with specials"],
            "plow_horse": ["Review portion size", "Consider price increase"],
            "dog": ["Consider removing from menu", "Rebrand or reposition"],
        }

        result.append({
            "id": item.id,
            "name": item.name,
            "category": item.category or "Uncategorized",
            "price": m["price"],
            "food_cost": m["cost"],
            "food_cost_percentage": round(food_cost_pct, 1),
            "profit_margin": round(m["profit_margin"], 1),
            "popularity_score": popularity,
            "sold_count": m["sold"],
            "revenue": round(m["revenue"], 2),
            "profit": round(m["profit"], 2),
            "quadrant": quadrant,
            "trend": "stable",
            "recommendations": recs.get(quadrant, []),
        })

    return result


@router.get("/analysis")
def get_menu_analysis(
    db: DbSession,
    days: int = Query(30),
):
    """Get overall menu engineering analysis."""
    eng_items = _build_engineering_items(db, days)
    total_items = len(eng_items)

    quadrant_counts = {}
    for item in eng_items:
        q = item["quadrant"]
        quadrant_counts[q] = quadrant_counts.get(q, 0) + 1

    total_revenue = sum(i["revenue"] for i in eng_items)
    total_profit = sum(i["profit"] for i in eng_items)
    food_costs = [i["food_cost_percentage"] for i in eng_items if i["food_cost_percentage"] > 0]
    avg_food_cost = sum(food_costs) / len(food_costs) if food_costs else 0

    return {
        "summary": {
            "total_items": total_items,
            "average_food_cost_percentage": round(avg_food_cost, 1),
            "average_profit_margin": round(100 - avg_food_cost, 1),
            "total_revenue": round(total_revenue, 2),
            "total_profit": round(total_profit, 2),
        },
        "quadrant_distribution": quadrant_counts,
        "top_performers": [i for i in eng_items if i["quadrant"] == "star"][:5],
        "needs_attention": [i for i in eng_items if i["quadrant"] == "dog"][:5],
        "analysis_period_days": days,
    }


@router.get("/items")
def get_menu_items(
    db: DbSession,
    days: int = Query(30),
    category: Optional[str] = None,
):
    """Get menu items with engineering analysis."""
    eng_items = _build_engineering_items(db, days)

    if category and category != "all":
        eng_items = [i for i in eng_items if i["category"].lower() == category.lower()]

    return {"items": eng_items}


@router.get("/categories")
def get_category_analysis(
    db: DbSession,
    days: int = Query(30),
):
    """Get category-level analysis."""
    eng_items = _build_engineering_items(db, days)

    categories = {}
    for item in eng_items:
        cat = item["category"]
        if cat not in categories:
            categories[cat] = {
                "category": cat,
                "items_count": 0,
                "total_revenue": 0,
                "total_profit": 0,
                "food_costs": [],
                "stars": 0,
                "puzzles": 0,
                "plow_horses": 0,
                "dogs": 0,
            }
        categories[cat]["items_count"] += 1
        categories[cat]["total_revenue"] += item["revenue"]
        categories[cat]["total_profit"] += item["profit"]
        categories[cat]["food_costs"].append(item["food_cost_percentage"])

        if item["quadrant"] == "star":
            categories[cat]["stars"] += 1
        elif item["quadrant"] == "puzzle":
            categories[cat]["puzzles"] += 1
        elif item["quadrant"] == "plow_horse":
            categories[cat]["plow_horses"] += 1
        else:
            categories[cat]["dogs"] += 1

    result = []
    for cat_data in categories.values():
        avg_food_cost = sum(cat_data["food_costs"]) / len(cat_data["food_costs"]) if cat_data["food_costs"] else 0
        total = cat_data["items_count"]
        score = int(((cat_data["stars"] * 100 + cat_data["puzzles"] * 70 + cat_data["plow_horses"] * 50 + cat_data["dogs"] * 20) / total) if total > 0 else 50)

        result.append({
            "category": cat_data["category"],
            "items_count": cat_data["items_count"],
            "total_revenue": round(cat_data["total_revenue"], 2),
            "total_profit": round(cat_data["total_profit"], 2),
            "avg_food_cost": round(avg_food_cost, 1),
            "stars": cat_data["stars"],
            "puzzles": cat_data["puzzles"],
            "plow_horses": cat_data["plow_horses"],
            "dogs": cat_data["dogs"],
            "optimization_score": score,
        })

    return {"categories": result}


@router.get("/pricing-recommendations")
def get_pricing_recommendations(
    db: DbSession,
    days: int = Query(30),
):
    """Get pricing optimization recommendations based on real data."""
    eng_items = _build_engineering_items(db, days)

    recommendations = []
    for item in eng_items:
        price = item["price"]
        fcp = item["food_cost_percentage"]
        if price <= 0:
            continue

        # Recommend price increases for high food cost items that are popular
        if fcp > 32 and item["popularity_score"] >= 50:
            increase_pct = min(12.0, (fcp - 28) * 1.5)
            new_price = round(price * (1 + increase_pct / 100), 2)
            monthly_profit = round((new_price - price) * item["sold_count"], 2)
            recommendations.append({
                "item_id": item["id"],
                "item_name": item["name"],
                "current_price": price,
                "recommended_price": new_price,
                "change_percentage": round(increase_pct, 1),
                "reason": f"Food cost at {fcp}% with strong popularity - price elasticity allows increase",
                "expected_impact": f"+${monthly_profit}/mo profit",
            })
        # Recommend increases for underpriced low food cost puzzles
        elif fcp < 25 and item["quadrant"] == "puzzle":
            increase_pct = 8.0
            new_price = round(price * 1.08, 2)
            monthly_profit = round((new_price - price) * item["sold_count"], 2)
            recommendations.append({
                "item_id": item["id"],
                "item_name": item["name"],
                "current_price": price,
                "recommended_price": new_price,
                "change_percentage": increase_pct,
                "reason": "Excellent food cost ratio, underpriced for market",
                "expected_impact": f"+${monthly_profit}/mo profit",
            })

    # Sort by expected impact descending
    recommendations.sort(key=lambda r: r["change_percentage"], reverse=True)

    return {"recommendations": recommendations[:10]}
