"""Menu Engineering & Analytics Service - Lightspeed style."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from collections import defaultdict

from app.models.analytics import MenuAnalysis, ServerPerformance, DailyMetrics, MenuQuadrant
from app.models.product import Product
from app.models.pos import PosSalesLine
from app.models.recipe import Recipe, RecipeLine


class MenuEngineeringService:
    """Analyze menu performance and provide optimization recommendations."""

    def __init__(self, db: Session):
        self.db = db

    def analyze_menu(
        self,
        location_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None
    ) -> List[MenuAnalysis]:
        """
        Perform menu engineering analysis.
        Classifies items into quadrants based on popularity and profitability.
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Get sales data
        sales_query = self.db.query(
            PosSalesLine.pos_item_id,
            PosSalesLine.name,
            func.sum(PosSalesLine.qty).label("quantity_sold"),
            func.count(PosSalesLine.id).label("order_count")
        ).filter(
            PosSalesLine.ts >= start_date,
            PosSalesLine.ts <= end_date,
            PosSalesLine.is_refund == False
        )

        if location_id:
            sales_query = sales_query.filter(PosSalesLine.location_id == location_id)

        sales_query = sales_query.group_by(PosSalesLine.pos_item_id, PosSalesLine.name)
        sales_data = sales_query.all()

        if not sales_data:
            return []

        # Get products with costs
        products = {p.id: p for p in self.db.query(Product).all()}

        # Calculate totals for averages
        total_quantity = sum(s.quantity_sold or 0 for s in sales_data)
        total_items = len(sales_data)

        # Average popularity threshold
        avg_popularity = total_quantity / total_items if total_items > 0 else 0

        # Calculate metrics for each item
        analyses = []
        all_margins = []

        for sale in sales_data:
            product = products.get(sale.pos_item_id)
            if not product:
                continue

            # Get recipe cost if available
            recipe_cost = self._get_recipe_cost(sale.pos_item_id)
            cost_per_item = recipe_cost or product.cost_price or 0

            # Calculate metrics
            revenue = (sale.quantity_sold or 0) * (product.sell_price or 0)
            cost = (sale.quantity_sold or 0) * cost_per_item
            profit = revenue - cost

            food_cost_percent = (cost / revenue * 100) if revenue > 0 else 0
            profit_margin = (profit / revenue * 100) if revenue > 0 else 0
            contribution_margin = (product.sell_price or 0) - cost_per_item

            all_margins.append(contribution_margin)

            analyses.append({
                "product_id": sale.pos_item_id,
                "product_name": sale.name,
                "quantity_sold": sale.quantity_sold or 0,
                "revenue": revenue,
                "cost": cost,
                "profit": profit,
                "food_cost_percent": food_cost_percent,
                "profit_margin": profit_margin,
                "contribution_margin": contribution_margin,
                "popularity_index": (sale.quantity_sold or 0) / total_quantity * 100 if total_quantity > 0 else 0
            })

        # Calculate average contribution margin for classification
        avg_margin = sum(all_margins) / len(all_margins) if all_margins else 0

        # Classify into quadrants and create/update records
        results = []
        for item in analyses:
            is_popular = item["quantity_sold"] >= avg_popularity * 0.7  # 70% rule
            is_profitable = item["contribution_margin"] >= avg_margin

            # Determine quadrant
            if is_popular and is_profitable:
                quadrant = MenuQuadrant.STAR
                action = "keep"
                reason = "High performer - maintain quality and consistency"
            elif not is_popular and is_profitable:
                quadrant = MenuQuadrant.PUZZLE
                action = "promote"
                reason = "Hidden gem - increase visibility through marketing"
            elif is_popular and not is_profitable:
                quadrant = MenuQuadrant.PLOW_HORSE
                action = "increase_price"
                reason = "Popular but low margin - consider price increase or portion adjustment"
            else:
                quadrant = MenuQuadrant.DOG
                action = "remove"
                reason = "Underperformer - consider removing or reformulating"

            # Calculate recommended price for low-margin items
            recommended_price = None
            if quadrant in [MenuQuadrant.PLOW_HORSE, MenuQuadrant.DOG]:
                target_margin = 0.65  # Target 65% margin
                if item["cost"] > 0:
                    recommended_price = (item["cost"] / item["quantity_sold"]) / (1 - target_margin)

            # Create analysis record
            analysis = MenuAnalysis(
                product_id=item["product_id"],
                location_id=location_id,
                analysis_period_start=start_date,
                analysis_period_end=end_date,
                quantity_sold=item["quantity_sold"],
                total_revenue=item["revenue"],
                total_cost=item["cost"],
                total_profit=item["profit"],
                food_cost_percent=item["food_cost_percent"],
                profit_margin_percent=item["profit_margin"],
                contribution_margin=item["contribution_margin"],
                popularity_index=item["popularity_index"],
                profitability_index=(item["contribution_margin"] / avg_margin * 100) if avg_margin > 0 else 0,
                quadrant=quadrant,
                recommended_action=action,
                recommended_price=recommended_price,
                recommendation_reason=reason
            )

            self.db.add(analysis)
            results.append(analysis)

        self.db.commit()
        return results

    def generate_recommendations(self, analyses: List[MenuAnalysis]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations from menu analysis."""
        recommendations = []

        for analysis in analyses:
            if analysis.quadrant == MenuQuadrant.PUZZLE:
                recommendations.append({
                    "product_id": analysis.product_id,
                    "type": "promote",
                    "message": f"Consider promoting this high-margin item to increase sales",
                    "priority": "medium"
                })
            elif analysis.quadrant == MenuQuadrant.PLOW_HORSE:
                recommendations.append({
                    "product_id": analysis.product_id,
                    "type": "price_increase",
                    "message": f"Consider increasing price or reducing costs to improve margin",
                    "priority": "high"
                })
            elif analysis.quadrant == MenuQuadrant.DOG:
                recommendations.append({
                    "product_id": analysis.product_id,
                    "type": "remove",
                    "message": f"Consider removing or reformulating this underperforming item",
                    "priority": "low"
                })

        return recommendations

    def _get_recipe_cost(self, product_id: int) -> Optional[float]:
        """Get the cost of a recipe if one exists."""
        recipe = self.db.query(Recipe).filter(Recipe.product_id == product_id).first()
        if not recipe:
            return None

        total_cost = 0
        for line in recipe.lines:
            if line.ingredient_id:
                ingredient = self.db.query(Product).filter(Product.id == line.ingredient_id).first()
                if ingredient and ingredient.cost_price:
                    total_cost += ingredient.cost_price * (line.quantity or 0)

        return total_cost if total_cost > 0 else None

    def get_menu_quadrant_summary(
        self,
        location_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get summary of menu items by quadrant."""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(MenuAnalysis).filter(
            MenuAnalysis.analysis_period_start >= start_date
        )

        if location_id:
            query = query.filter(MenuAnalysis.location_id == location_id)

        analyses = query.all()

        summary = {
            "stars": {"count": 0, "revenue": 0, "items": []},
            "puzzles": {"count": 0, "revenue": 0, "items": []},
            "plow_horses": {"count": 0, "revenue": 0, "items": []},
            "dogs": {"count": 0, "revenue": 0, "items": []},
            "total_revenue": 0,
            "total_items": len(analyses)
        }

        quadrant_map = {
            MenuQuadrant.STAR: "stars",
            MenuQuadrant.PUZZLE: "puzzles",
            MenuQuadrant.PLOW_HORSE: "plow_horses",
            MenuQuadrant.DOG: "dogs"
        }

        for analysis in analyses:
            key = quadrant_map.get(analysis.quadrant)
            if key:
                summary[key]["count"] += 1
                summary[key]["revenue"] += analysis.total_revenue or 0
                summary[key]["items"].append({
                    "product_id": analysis.product_id,
                    "revenue": analysis.total_revenue,
                    "profit": analysis.total_profit,
                    "action": analysis.recommended_action
                })
            summary["total_revenue"] += analysis.total_revenue or 0

        return summary


class ServerPerformanceService:
    """Analyze server/staff performance metrics."""

    def __init__(self, db: Session):
        self.db = db

    def analyze_server_performance(
        self,
        location_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ServerPerformance]:
        """Analyze performance metrics for all servers."""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # This would need integration with the main POS to get server data
        # For now, create a framework that can be extended

        # Get sales grouped by server (assuming we have server info)
        # In real implementation, this would join with orders table that has server_id

        results = []

        # Calculate averages for comparison
        # This is a placeholder - actual implementation needs order/server data

        return results

    def get_server_scorecard(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get performance scorecard for a specific server."""
        start_date = datetime.utcnow() - timedelta(days=days)

        perf = self.db.query(ServerPerformance).filter(
            ServerPerformance.user_id == user_id,
            ServerPerformance.period_start >= start_date
        ).order_by(ServerPerformance.period_end.desc()).first()

        if not perf:
            return {"message": "No performance data available"}

        # Calculate grades
        grades = {}

        # Revenue grade
        if perf.vs_avg_ticket:
            if perf.vs_avg_ticket >= 10:
                grades["revenue"] = "A"
            elif perf.vs_avg_ticket >= 0:
                grades["revenue"] = "B"
            elif perf.vs_avg_ticket >= -10:
                grades["revenue"] = "C"
            else:
                grades["revenue"] = "D"

        # Upsell grade
        avg_attach = (
            (perf.appetizer_attach_rate or 0) +
            (perf.dessert_attach_rate or 0) +
            (perf.drink_attach_rate or 0)
        ) / 3
        if avg_attach >= 40:
            grades["upselling"] = "A"
        elif avg_attach >= 30:
            grades["upselling"] = "B"
        elif avg_attach >= 20:
            grades["upselling"] = "C"
        else:
            grades["upselling"] = "D"

        return {
            "user_id": user_id,
            "period_start": perf.period_start,
            "period_end": perf.period_end,
            "metrics": {
                "total_orders": perf.total_orders,
                "total_revenue": perf.total_revenue,
                "total_tips": perf.total_tips,
                "avg_ticket": perf.avg_ticket_size,
                "avg_tip_percent": perf.avg_tip_percent
            },
            "upselling": {
                "appetizers": perf.appetizer_attach_rate,
                "desserts": perf.dessert_attach_rate,
                "drinks": perf.drink_attach_rate
            },
            "rankings": {
                "by_revenue": perf.rank_by_revenue,
                "by_tips": perf.rank_by_tips,
                "by_upsell": perf.rank_by_upsell
            },
            "grades": grades,
            "coaching_notes": perf.coaching_notes
        }

    def get_improvement_suggestions(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate improvement suggestions based on server performance data."""
        suggestions = []

        for r in results:
            if r.get("avg_ticket", 0) < r.get("team_avg_ticket", 0):
                suggestions.append({
                    "user_id": r.get("user_id"),
                    "type": "upselling",
                    "message": "Focus on upselling to increase average ticket size"
                })
            if r.get("tip_percentage", 0) < 15:
                suggestions.append({
                    "user_id": r.get("user_id"),
                    "type": "service",
                    "message": "Review service quality to improve tip percentage"
                })

        return suggestions


class DailyMetricsService:
    """Calculate and store daily business metrics."""

    def __init__(self, db: Session):
        self.db = db

    def calculate_daily_metrics(
        self,
        date: datetime,
        location_id: Optional[int] = None
    ) -> DailyMetrics:
        """Calculate metrics for a specific day."""
        start = datetime(date.year, date.month, date.day, 0, 0, 0)
        end = start + timedelta(days=1)

        # Query sales for the day
        sales_query = self.db.query(
            func.count(PosSalesLine.id).label("order_count"),
            func.sum(PosSalesLine.qty).label("total_items"),
        ).filter(
            PosSalesLine.ts >= start,
            PosSalesLine.ts < end,
            PosSalesLine.is_refund == False
        )

        if location_id:
            sales_query = sales_query.filter(PosSalesLine.location_id == location_id)

        sales = sales_query.first()

        # Get or create daily metrics record
        metrics = self.db.query(DailyMetrics).filter(
            DailyMetrics.date == start,
            DailyMetrics.location_id == location_id
        ).first()

        if not metrics:
            metrics = DailyMetrics(
                date=start,
                location_id=location_id
            )
            self.db.add(metrics)

        # Update metrics
        metrics.total_orders = sales.order_count or 0

        # Calculate comparisons
        last_week = self.db.query(DailyMetrics).filter(
            DailyMetrics.date == start - timedelta(days=7),
            DailyMetrics.location_id == location_id
        ).first()

        if last_week and last_week.total_revenue > 0:
            metrics.vs_last_week = (
                (metrics.total_revenue - last_week.total_revenue) /
                last_week.total_revenue * 100
            )

        metrics.calculated_at = datetime.utcnow()

        self.db.commit()
        return metrics

    def get_metrics_summary(
        self,
        location_id: Optional[int] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get summary of daily metrics for a period."""
        start_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(DailyMetrics).filter(
            DailyMetrics.date >= start_date
        )

        if location_id:
            query = query.filter(DailyMetrics.location_id == location_id)

        metrics = query.order_by(DailyMetrics.date).all()

        if not metrics:
            return {"message": "No metrics available"}

        return {
            "period_start": start_date,
            "period_end": datetime.utcnow(),
            "total_revenue": sum(m.total_revenue or 0 for m in metrics),
            "total_orders": sum(m.total_orders or 0 for m in metrics),
            "avg_daily_revenue": sum(m.total_revenue or 0 for m in metrics) / len(metrics),
            "avg_daily_orders": sum(m.total_orders or 0 for m in metrics) / len(metrics),
            "daily_breakdown": [
                {
                    "date": m.date,
                    "revenue": m.total_revenue,
                    "orders": m.total_orders,
                    "vs_last_week": m.vs_last_week
                }
                for m in metrics
            ]
        }
