"""Menu Engineering routes."""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter
from pydantic import BaseModel

from app.db.session import DbSession

router = APIRouter()


class MenuItem(BaseModel):
    """Menu item with engineering data."""
    id: int
    name: str
    category: str
    price: float
    food_cost: float
    food_cost_percentage: float
    profit_margin: float
    popularity_score: float
    sold_count: int
    revenue: float
    profit: float
    quadrant: str  # star, puzzle, plow_horse, dog
    trend: str  # up, down, stable
    recommendations: List[str]


class CategoryAnalysis(BaseModel):
    """Category analysis data."""
    category: str
    items_count: int
    total_revenue: float
    total_profit: float
    avg_food_cost: float
    stars: int
    puzzles: int
    plow_horses: int
    dogs: int
    optimization_score: int


class PricingRecommendation(BaseModel):
    """Pricing recommendation."""
    item_id: int
    item_name: str
    current_price: float
    recommended_price: float
    change_percentage: float
    reason: str
    expected_impact: str


# Sample menu data for demonstration
_sample_items = [
    {"id": 1, "name": "Classic Burger", "category": "Main", "price": 15.99, "food_cost": 4.50, "food_cost_percentage": 28.1, "profit_margin": 71.9, "popularity_score": 85, "sold_count": 245, "revenue": 3917.55, "profit": 2815.55, "quadrant": "star", "trend": "up", "recommendations": ["Keep promoting", "Consider combo deals"]},
    {"id": 2, "name": "Caesar Salad", "category": "Salads", "price": 11.99, "food_cost": 2.80, "food_cost_percentage": 23.4, "profit_margin": 76.6, "popularity_score": 65, "sold_count": 120, "revenue": 1438.80, "profit": 1102.80, "quadrant": "puzzle", "trend": "stable", "recommendations": ["Increase visibility on menu", "Add protein options"]},
    {"id": 3, "name": "Fish & Chips", "category": "Main", "price": 16.99, "food_cost": 6.20, "food_cost_percentage": 36.5, "profit_margin": 63.5, "popularity_score": 78, "sold_count": 180, "revenue": 3058.20, "profit": 1941.20, "quadrant": "plow_horse", "trend": "down", "recommendations": ["Review portion size", "Consider price increase"]},
    {"id": 4, "name": "Margherita Pizza", "category": "Pizza", "price": 14.99, "food_cost": 3.50, "food_cost_percentage": 23.3, "profit_margin": 76.7, "popularity_score": 90, "sold_count": 320, "revenue": 4796.80, "profit": 3676.80, "quadrant": "star", "trend": "up", "recommendations": ["Feature as signature item", "Train staff on upsells"]},
    {"id": 5, "name": "Veggie Wrap", "category": "Main", "price": 12.99, "food_cost": 3.80, "food_cost_percentage": 29.3, "profit_margin": 70.7, "popularity_score": 35, "sold_count": 45, "revenue": 584.55, "profit": 413.05, "quadrant": "dog", "trend": "down", "recommendations": ["Consider removing from menu", "Rebrand or reposition"]},
    {"id": 6, "name": "BBQ Ribs", "category": "Main", "price": 24.99, "food_cost": 9.50, "food_cost_percentage": 38.0, "profit_margin": 62.0, "popularity_score": 72, "sold_count": 95, "revenue": 2374.05, "profit": 1471.05, "quadrant": "plow_horse", "trend": "stable", "recommendations": ["Negotiate better supplier prices", "Adjust portion size"]},
    {"id": 7, "name": "Chicken Wings", "category": "Appetizers", "price": 12.99, "food_cost": 3.20, "food_cost_percentage": 24.6, "profit_margin": 75.4, "popularity_score": 88, "sold_count": 280, "revenue": 3637.20, "profit": 2741.20, "quadrant": "star", "trend": "up", "recommendations": ["Offer variety of sauces", "Happy hour special"]},
    {"id": 8, "name": "Lobster Roll", "category": "Main", "price": 28.99, "food_cost": 14.00, "food_cost_percentage": 48.3, "profit_margin": 51.7, "popularity_score": 45, "sold_count": 35, "revenue": 1014.65, "profit": 524.65, "quadrant": "dog", "trend": "down", "recommendations": ["High food cost - review pricing", "Seasonal special only"]},
    {"id": 9, "name": "Nachos Supreme", "category": "Appetizers", "price": 14.99, "food_cost": 3.50, "food_cost_percentage": 23.3, "profit_margin": 76.7, "popularity_score": 82, "sold_count": 195, "revenue": 2923.05, "profit": 2241.05, "quadrant": "star", "trend": "stable", "recommendations": ["Bundle with drinks", "Perfect portion size"]},
    {"id": 10, "name": "House Wine", "category": "Drinks", "price": 8.00, "food_cost": 2.00, "food_cost_percentage": 25.0, "profit_margin": 75.0, "popularity_score": 55, "sold_count": 150, "revenue": 1200.00, "profit": 900.00, "quadrant": "puzzle", "trend": "stable", "recommendations": ["Train servers on wine pairing", "Wine of the day promo"]},
    {"id": 11, "name": "Grilled Salmon", "category": "Main", "price": 22.99, "food_cost": 8.50, "food_cost_percentage": 37.0, "profit_margin": 63.0, "popularity_score": 68, "sold_count": 110, "revenue": 2528.90, "profit": 1593.90, "quadrant": "plow_horse", "trend": "up", "recommendations": ["Highlight health benefits", "Premium plating"]},
    {"id": 12, "name": "Chocolate Cake", "category": "Desserts", "price": 7.99, "food_cost": 1.80, "food_cost_percentage": 22.5, "profit_margin": 77.5, "popularity_score": 70, "sold_count": 130, "revenue": 1038.70, "profit": 804.70, "quadrant": "puzzle", "trend": "stable", "recommendations": ["Suggest with coffee", "After dinner special"]},
]


@router.get("/items")
def get_menu_items(
    db: DbSession,
    days: int = 30,
    category: Optional[str] = None,
):
    """Get menu items with engineering analysis."""
    items = _sample_items.copy()

    if category and category != "all":
        items = [i for i in items if i["category"].lower() == category.lower()]

    return {"items": items}


@router.get("/categories")
def get_category_analysis(
    db: DbSession,
    days: int = 30,
):
    """Get category-level analysis."""
    # Group items by category
    categories = {}
    for item in _sample_items:
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
        # Calculate optimization score based on quadrant distribution
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
    days: int = 30,
):
    """Get pricing optimization recommendations."""
    recommendations = [
        {
            "item_id": 3,
            "item_name": "Fish & Chips",
            "current_price": 16.99,
            "recommended_price": 18.49,
            "change_percentage": 8.8,
            "reason": "High food cost (36.5%) with strong popularity - price elasticity allows increase",
            "expected_impact": "+$270/mo profit"
        },
        {
            "item_id": 6,
            "item_name": "BBQ Ribs",
            "current_price": 24.99,
            "recommended_price": 26.99,
            "change_percentage": 8.0,
            "reason": "Food cost at 38%, popular item can sustain modest increase",
            "expected_impact": "+$190/mo profit"
        },
        {
            "item_id": 11,
            "item_name": "Grilled Salmon",
            "current_price": 22.99,
            "recommended_price": 24.99,
            "change_percentage": 8.7,
            "reason": "Premium perception allows pricing adjustment, trending upward",
            "expected_impact": "+$220/mo profit"
        },
        {
            "item_id": 10,
            "item_name": "House Wine",
            "current_price": 8.00,
            "recommended_price": 9.00,
            "change_percentage": 12.5,
            "reason": "Below market average, good margin potential",
            "expected_impact": "+$150/mo profit"
        },
        {
            "item_id": 2,
            "item_name": "Caesar Salad",
            "current_price": 11.99,
            "recommended_price": 12.99,
            "change_percentage": 8.3,
            "reason": "Excellent food cost ratio, underpriced for market",
            "expected_impact": "+$120/mo profit"
        },
    ]

    return {"recommendations": recommendations}
