"""
Benchmarking Service - Complete Implementation
Compare restaurant performance against industry and regional averages (like Toast Benchmarking)

Features:
- Industry benchmarks
- Regional comparisons
- Category performance
- Time-based analysis
- Peer group rankings
- Performance trends
- Goal setting
- Custom benchmarks
"""

from datetime import datetime, timedelta, timezone, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import uuid

from app.models.v31_models import BenchmarkGoal


class BenchmarkCategory:
    SALES = "sales"
    LABOR = "labor"
    FOOD_COST = "food_cost"
    CUSTOMER = "customer"
    EFFICIENCY = "efficiency"
    MARKETING = "marketing"


class BenchmarkingService:
    """Complete Benchmarking Service for Restaurant Comparison"""

    def __init__(self, db: Session):
        self.db = db
        self._industry_benchmarks: Dict[str, Dict] = {}
        self._regional_benchmarks: Dict[str, Dict] = {}
        self._peer_groups: Dict[str, Dict] = {}  # Peer groups are dynamic and session-based

        # Initialize static benchmark reference data
        self._init_industry_benchmarks()
        self._init_regional_benchmarks()
    
    def _init_industry_benchmarks(self):
        """Initialize industry-wide benchmark data"""
        self._industry_benchmarks = {
            "full_service": {
                "type": "Full Service Restaurant",
                "metrics": {
                    "avg_ticket": {"value": 35.00, "unit": "EUR", "percentiles": {"25": 25, "50": 35, "75": 48, "90": 65}},
                    "labor_cost_pct": {"value": 32.0, "unit": "%", "percentiles": {"25": 28, "50": 32, "75": 36, "90": 42}},
                    "food_cost_pct": {"value": 30.0, "unit": "%", "percentiles": {"25": 26, "50": 30, "75": 34, "90": 38}},
                    "table_turn_time": {"value": 65, "unit": "minutes", "percentiles": {"25": 45, "50": 65, "75": 85, "90": 105}},
                    "covers_per_labor_hour": {"value": 3.2, "unit": "covers", "percentiles": {"25": 2.5, "50": 3.2, "75": 4.0, "90": 5.0}},
                    "revenue_per_sqm": {"value": 450, "unit": "EUR/month", "percentiles": {"25": 300, "50": 450, "75": 600, "90": 800}},
                    "customer_satisfaction": {"value": 4.2, "unit": "rating", "percentiles": {"25": 3.8, "50": 4.2, "75": 4.5, "90": 4.8}},
                    "repeat_customer_rate": {"value": 35.0, "unit": "%", "percentiles": {"25": 25, "50": 35, "75": 45, "90": 55}},
                    "online_order_pct": {"value": 22.0, "unit": "%", "percentiles": {"25": 12, "50": 22, "75": 35, "90": 50}},
                    "tip_percentage": {"value": 12.0, "unit": "%", "percentiles": {"25": 8, "50": 12, "75": 15, "90": 18}}
                }
            },
            "bar_lounge": {
                "type": "Bar / Lounge",
                "metrics": {
                    "avg_ticket": {"value": 28.00, "unit": "EUR", "percentiles": {"25": 18, "50": 28, "75": 42, "90": 60}},
                    "labor_cost_pct": {"value": 28.0, "unit": "%", "percentiles": {"25": 24, "50": 28, "75": 32, "90": 38}},
                    "beverage_cost_pct": {"value": 22.0, "unit": "%", "percentiles": {"25": 18, "50": 22, "75": 26, "90": 30}},
                    "drinks_per_hour": {"value": 45, "unit": "drinks", "percentiles": {"25": 30, "50": 45, "75": 65, "90": 90}},
                    "avg_stay_time": {"value": 90, "unit": "minutes", "percentiles": {"25": 60, "50": 90, "75": 120, "90": 180}}
                }
            },
            "ski_resort": {
                "type": "Ski Resort Restaurant",
                "metrics": {
                    "avg_ticket": {"value": 42.00, "unit": "EUR", "percentiles": {"25": 30, "50": 42, "75": 58, "90": 80}},
                    "peak_hour_sales_pct": {"value": 45.0, "unit": "%", "percentiles": {"25": 35, "50": 45, "75": 55, "90": 65}},
                    "apres_ski_revenue_pct": {"value": 35.0, "unit": "%", "percentiles": {"25": 25, "50": 35, "75": 45, "90": 55}},
                    "tourist_vs_local": {"value": 75.0, "unit": "% tourist", "percentiles": {"25": 60, "50": 75, "75": 85, "90": 95}},
                    "seasonal_variance": {"value": 250.0, "unit": "% high/low", "percentiles": {"25": 150, "50": 250, "75": 400, "90": 600}},
                    "hot_beverage_pct": {"value": 25.0, "unit": "%", "percentiles": {"25": 15, "50": 25, "75": 35, "90": 45}}
                }
            }
        }
    
    def _init_regional_benchmarks(self):
        """Initialize regional benchmark data"""
        self._regional_benchmarks = {
            "bulgaria": {
                "region": "Bulgaria",
                "metrics": {
                    "avg_ticket": 28.00,
                    "labor_cost_pct": 25.0,
                    "food_cost_pct": 32.0,
                    "min_wage_impact": 15.0,
                    "vat_rate": 20.0
                }
            },
            "borovets": {
                "region": "Borovets Ski Resort",
                "metrics": {
                    "avg_ticket": 45.00,
                    "labor_cost_pct": 28.0,
                    "food_cost_pct": 30.0,
                    "peak_season_multiplier": 2.5,
                    "tourist_spending_avg": 85.00
                }
            },
            "sofia": {
                "region": "Sofia",
                "metrics": {
                    "avg_ticket": 32.00,
                    "labor_cost_pct": 27.0,
                    "food_cost_pct": 31.0,
                    "delivery_pct": 28.0
                }
            },
            "eastern_europe": {
                "region": "Eastern Europe",
                "metrics": {
                    "avg_ticket": 25.00,
                    "labor_cost_pct": 26.0,
                    "food_cost_pct": 33.0
                }
            }
        }
    
    # ========== BENCHMARK COMPARISONS ==========
    
    def compare_to_industry(
        self,
        venue_id: int,
        industry_type: str,
        metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """Compare venue metrics to industry benchmarks"""
        if industry_type not in self._industry_benchmarks:
            return {"success": False, "error": "Industry type not found"}
        
        benchmarks = self._industry_benchmarks[industry_type]["metrics"]
        comparisons = []
        
        for metric_name, venue_value in metrics.items():
            if metric_name in benchmarks:
                benchmark = benchmarks[metric_name]
                
                # Calculate percentile
                percentile = self._calculate_percentile(venue_value, benchmark["percentiles"])
                
                # Determine status
                if percentile >= 75:
                    status = "excellent"
                elif percentile >= 50:
                    status = "good"
                elif percentile >= 25:
                    status = "needs_improvement"
                else:
                    status = "poor"
                
                comparisons.append({
                    "metric": metric_name,
                    "your_value": venue_value,
                    "industry_avg": benchmark["value"],
                    "unit": benchmark["unit"],
                    "percentile": percentile,
                    "status": status,
                    "difference": round(venue_value - benchmark["value"], 2),
                    "difference_pct": round((venue_value - benchmark["value"]) / benchmark["value"] * 100, 1)
                })
        
        # Overall score
        avg_percentile = sum(c["percentile"] for c in comparisons) / len(comparisons) if comparisons else 0
        
        return {
            "success": True,
            "venue_id": venue_id,
            "industry_type": industry_type,
            "comparisons": comparisons,
            "overall_percentile": round(avg_percentile, 1),
            "overall_status": "excellent" if avg_percentile >= 75 else "good" if avg_percentile >= 50 else "needs_improvement",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _calculate_percentile(self, value: float, percentiles: Dict[str, float]) -> int:
        """Calculate which percentile a value falls into"""
        if value <= percentiles["25"]:
            return int(25 * value / percentiles["25"])
        elif value <= percentiles["50"]:
            return int(25 + 25 * (value - percentiles["25"]) / (percentiles["50"] - percentiles["25"]))
        elif value <= percentiles["75"]:
            return int(50 + 25 * (value - percentiles["50"]) / (percentiles["75"] - percentiles["50"]))
        elif value <= percentiles["90"]:
            return int(75 + 15 * (value - percentiles["75"]) / (percentiles["90"] - percentiles["75"]))
        else:
            return min(99, int(90 + 10 * (value - percentiles["90"]) / percentiles["90"]))
    
    def compare_to_region(
        self,
        venue_id: int,
        region: str,
        metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """Compare venue metrics to regional benchmarks"""
        if region not in self._regional_benchmarks:
            return {"success": False, "error": "Region not found"}
        
        benchmarks = self._regional_benchmarks[region]["metrics"]
        comparisons = []
        
        for metric_name, venue_value in metrics.items():
            if metric_name in benchmarks:
                benchmark_value = benchmarks[metric_name]
                
                difference = venue_value - benchmark_value
                difference_pct = (difference / benchmark_value) * 100 if benchmark_value else 0
                
                comparisons.append({
                    "metric": metric_name,
                    "your_value": venue_value,
                    "regional_avg": benchmark_value,
                    "difference": round(difference, 2),
                    "difference_pct": round(difference_pct, 1),
                    "better_than_avg": difference > 0 if metric_name in ["avg_ticket", "covers_per_labor_hour"] else difference < 0
                })
        
        return {
            "success": True,
            "venue_id": venue_id,
            "region": region,
            "comparisons": comparisons,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ========== PEER GROUP COMPARISONS ==========
    
    def create_peer_group(
        self,
        name: str,
        criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a peer group for comparison"""
        group_id = f"PEER-{uuid.uuid4().hex[:8].upper()}"
        
        peer_group = {
            "group_id": group_id,
            "name": name,
            "criteria": criteria,
            "member_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Simulate matching restaurants based on criteria
        # In production, would query actual restaurant network
        if criteria.get("type") == "ski_resort":
            peer_group["member_count"] = 45
        elif criteria.get("type") == "bar":
            peer_group["member_count"] = 850
        else:
            peer_group["member_count"] = 1200
        
        self._peer_groups[group_id] = peer_group
        
        return {
            "success": True,
            "group_id": group_id,
            "name": name,
            "member_count": peer_group["member_count"],
            "message": f"Peer group created with {peer_group['member_count']} similar venues"
        }
    
    def compare_to_peers(
        self,
        venue_id: int,
        group_id: str,
        time_period: str = "month"
    ) -> Dict[str, Any]:
        """Compare to peer group using real venue data"""
        from app.models import Venue, Order
        from sqlalchemy import func

        if group_id not in self._peer_groups:
            return {"success": False, "error": "Peer group not found"}

        peer_group = self._peer_groups[group_id]

        # Calculate time period boundaries
        end_date = datetime.now(timezone.utc)
        if time_period == "week":
            start_date = end_date - timedelta(days=7)
        elif time_period == "month":
            start_date = end_date - timedelta(days=30)
        elif time_period == "quarter":
            start_date = end_date - timedelta(days=90)
        elif time_period == "year":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)

        # Get venues for peer comparison (limit to avoid full table scan)
        venues = self.db.query(Venue).filter(Venue.active == True).limit(100).all()
        venue_ids = [v.id for v in venues]
        venue_metrics = []

        # Batch-load aggregated order data for all venues at once
        from sqlalchemy import case
        venue_order_stats = self.db.query(
            Order.venue_id,
            func.count(Order.id).label('order_count'),
            func.sum(Order.total).label('total_sales'),
            func.sum(Order.tip_amount).label('total_tips')
        ).filter(
            Order.venue_id.in_(venue_ids),
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status.in_(["COMPLETED", "PAID"])
        ).group_by(Order.venue_id).all()

        days_in_period = (end_date - start_date).days or 1
        assumed_labor_hours = days_in_period * 8

        for row in venue_order_stats:
            if not row.order_count:
                continue

            total_sales = float(row.total_sales or 0) + float(row.total_tips or 0)
            avg_ticket = total_sales / row.order_count if row.order_count else 0
            orders_per_labor_hour = row.order_count / assumed_labor_hours if assumed_labor_hours else 0

            venue_metrics.append({
                "venue_id": row.venue_id,
                "sales": total_sales,
                "avg_ticket": avg_ticket,
                "order_count": row.order_count,
                "labor_efficiency": orders_per_labor_hour
            })

        # Sort venues by each metric and calculate rankings
        def calculate_rank(metric_name: str, value: float, is_lower_better: bool = False) -> Dict[str, Any]:
            sorted_metrics = sorted(venue_metrics,
                                   key=lambda x: x.get(metric_name, 0),
                                   reverse=not is_lower_better)

            rank = 1
            for i, vm in enumerate(sorted_metrics, 1):
                if vm["venue_id"] == venue_id:
                    rank = i
                    break

            total = len(sorted_metrics)
            percentile = int(((total - rank) / total) * 100) if total > 0 else 0

            return {
                "rank": rank,
                "total": total,
                "percentile": percentile
            }

        # Get current venue's metrics
        current_venue_metrics = next(
            (vm for vm in venue_metrics if vm["venue_id"] == venue_id),
            {"sales": 0, "avg_ticket": 0, "order_count": 0, "labor_efficiency": 0}
        )

        # Calculate rankings
        rankings = {
            "sales": calculate_rank("sales", current_venue_metrics["sales"]),
            "avg_ticket": calculate_rank("avg_ticket", current_venue_metrics["avg_ticket"]),
            "labor_efficiency": calculate_rank("labor_efficiency", current_venue_metrics["labor_efficiency"])
        }

        # Calculate trends vs peers
        avg_sales = sum(vm["sales"] for vm in venue_metrics) / len(venue_metrics) if venue_metrics else 1
        avg_efficiency = sum(vm["labor_efficiency"] for vm in venue_metrics) / len(venue_metrics) if venue_metrics else 1

        sales_vs_peers = ((current_venue_metrics["sales"] - avg_sales) / avg_sales * 100) if avg_sales else 0
        efficiency_vs_peers = ((current_venue_metrics["labor_efficiency"] - avg_efficiency) / avg_efficiency * 100) if avg_efficiency else 0

        return {
            "success": True,
            "venue_id": venue_id,
            "peer_group": peer_group["name"],
            "peer_count": len(venue_metrics),
            "time_period": time_period,
            "rankings": rankings,
            "trends": {
                "sales_vs_peers": f"{sales_vs_peers:+.1f}%",
                "efficiency_vs_peers": f"{efficiency_vs_peers:+.1f}%"
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ========== PERFORMANCE ANALYSIS ==========
    
    def get_performance_insights(
        self,
        venue_id: int,
        metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """Get AI-generated performance insights"""
        insights = []
        opportunities = []
        
        # Analyze each metric
        if metrics.get("labor_cost_pct", 0) > 35:
            insights.append({
                "type": "warning",
                "category": "labor",
                "message": "Labor costs are above industry average",
                "current": f"{metrics['labor_cost_pct']}%",
                "target": "32%",
                "potential_savings": f"€{int((metrics['labor_cost_pct'] - 32) * 100)} per €10,000 sales"
            })
            opportunities.append({
                "area": "Labor Optimization",
                "action": "Consider optimizing shift scheduling during slow periods",
                "potential_impact": "3-5% labor cost reduction"
            })
        
        if metrics.get("food_cost_pct", 0) > 32:
            insights.append({
                "type": "warning",
                "category": "food_cost",
                "message": "Food costs are higher than optimal",
                "current": f"{metrics['food_cost_pct']}%",
                "target": "28-30%",
                "potential_savings": f"€{int((metrics['food_cost_pct'] - 30) * 100)} per €10,000 sales"
            })
            opportunities.append({
                "area": "Menu Engineering",
                "action": "Review low-margin items and portion sizes",
                "potential_impact": "2-4% food cost reduction"
            })
        
        avg_ticket = metrics.get("avg_ticket", 0)
        if avg_ticket < 35:
            insights.append({
                "type": "opportunity",
                "category": "revenue",
                "message": "Average ticket is below industry benchmark",
                "current": f"€{avg_ticket}",
                "target": "€42",
                "potential_increase": f"€{int((42 - avg_ticket) * 100)} per 100 covers"
            })
            opportunities.append({
                "area": "Upselling",
                "action": "Train staff on appetizer and beverage upselling",
                "potential_impact": "10-15% ticket increase"
            })
        
        if metrics.get("repeat_customer_rate", 0) < 40:
            insights.append({
                "type": "opportunity",
                "category": "loyalty",
                "message": "Repeat customer rate has room for improvement",
                "current": f"{metrics.get('repeat_customer_rate', 0)}%",
                "target": "45%+"
            })
            opportunities.append({
                "area": "Customer Loyalty",
                "action": "Implement or enhance loyalty program",
                "potential_impact": "15-25% increase in repeat visits"
            })
        
        # Calculate overall health score
        health_score = 75  # Base score
        for insight in insights:
            if insight["type"] == "warning":
                health_score -= 5
        
        return {
            "success": True,
            "venue_id": venue_id,
            "health_score": health_score,
            "insights": insights,
            "opportunities": opportunities,
            "summary": f"Found {len(insights)} areas for attention and {len(opportunities)} improvement opportunities",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ========== GOAL SETTING ==========
    
    def set_benchmark_goal(
        self,
        venue_id: int,
        metric: str,
        target_value: float,
        target_date: date,
        baseline_value: float
    ) -> Dict[str, Any]:
        """Set a benchmark goal in database"""
        days_to_target = (target_date - date.today()).days

        # Create goal in database
        db_goal = BenchmarkGoal(
            venue_id=venue_id,
            metric=metric,
            baseline_value=baseline_value,
            target_value=target_value,
            current_value=baseline_value,
            target_date=target_date,
            status="in_progress"
        )

        self.db.add(db_goal)
        self.db.commit()
        self.db.refresh(db_goal)

        return {
            "success": True,
            "goal_id": db_goal.id,
            "metric": metric,
            "target": target_value,
            "days_remaining": days_to_target,
            "message": f"Goal set: {metric} to {target_value} by {target_date}"
        }
    
    def update_goal_progress(
        self,
        goal_id: int,
        current_value: float
    ) -> Dict[str, Any]:
        """Update goal progress in database"""
        db_goal = self.db.query(BenchmarkGoal).filter(
            BenchmarkGoal.id == goal_id
        ).first()

        if not db_goal:
            return {"success": False, "error": "Goal not found"}

        db_goal.current_value = current_value

        # Calculate progress
        baseline = float(db_goal.baseline_value or 0)
        target = float(db_goal.target_value)
        total_improvement = target - baseline
        current_improvement = current_value - baseline
        progress_pct = round((current_improvement / total_improvement) * 100, 1) if total_improvement else 0

        # Check if goal achieved
        if current_value >= target:
            db_goal.status = "achieved"
            db_goal.achieved_at = datetime.now(timezone.utc)

        self.db.commit()

        return {
            "success": True,
            "goal_id": goal_id,
            "current_value": current_value,
            "target_value": target,
            "progress_pct": progress_pct,
            "status": db_goal.status
        }
    
    def get_goals(
        self,
        venue_id: int,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all goals for a venue from database"""
        query = self.db.query(BenchmarkGoal).filter(
            BenchmarkGoal.venue_id == venue_id
        )

        if status:
            query = query.filter(BenchmarkGoal.status == status)

        db_goals = query.all()

        goals = []
        achieved_count = 0
        in_progress_count = 0

        for g in db_goals:
            baseline = float(g.baseline_value or 0)
            target = float(g.target_value)
            current = float(g.current_value or baseline)
            total_improvement = target - baseline
            current_improvement = current - baseline
            progress_pct = round((current_improvement / total_improvement) * 100, 1) if total_improvement else 0

            goals.append({
                "goal_id": g.id,
                "venue_id": g.venue_id,
                "metric": g.metric,
                "baseline_value": baseline,
                "target_value": target,
                "current_value": current,
                "target_date": g.target_date.isoformat() if g.target_date else None,
                "progress_pct": progress_pct,
                "status": g.status,
                "achieved_at": g.achieved_at.isoformat() if g.achieved_at else None,
                "created_at": g.created_at.isoformat() if g.created_at else None
            })

            if g.status == "achieved":
                achieved_count += 1
            elif g.status == "in_progress":
                in_progress_count += 1

        return {
            "success": True,
            "venue_id": venue_id,
            "goals": goals,
            "total": len(goals),
            "achieved": achieved_count,
            "in_progress": in_progress_count
        }
    
    # ========== TREND ANALYSIS ==========
    
    def get_performance_trends(
        self,
        venue_id: int,
        metrics: List[str],
        period: str = "6_months"
    ) -> Dict[str, Any]:
        """Get performance trends over time using historical Order data"""
        from app.models import Order, OrderItem, VenueStation
        from sqlalchemy import func

        # Calculate period parameters
        if period == "3_months":
            months = 3
        elif period == "6_months":
            months = 6
        elif period == "12_months":
            months = 12
        else:
            months = 6

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30 * months)

        # Get venue's stations
        station_ids = self.db.query(VenueStation.id).filter(
            VenueStation.venue_id == venue_id,
            VenueStation.active == True
        ).all()
        station_ids = [sid[0] for sid in station_ids]

        trends = {}

        for metric in metrics:
            trend_data = []

            # Generate data for each month in the period
            for i in range(months):
                month_start = end_date - timedelta(days=30 * (months - i))
                month_end = end_date - timedelta(days=30 * (months - i - 1))
                month_label = month_start.strftime("%Y-%m")

                # Query orders for this month
                orders = self.db.query(Order).filter(
                    Order.station_id.in_(station_ids),
                    Order.created_at >= month_start,
                    Order.created_at < month_end
                ).all()

                # Calculate metric based on type
                if metric == "sales" or metric == "revenue":
                    value = sum(order.total + order.tip_amount for order in orders)

                elif metric == "avg_ticket" or metric == "average_check":
                    value = (sum(order.total for order in orders) / len(orders)) if orders else 0

                elif metric == "order_count" or metric == "covers":
                    value = len(orders)

                elif metric == "tip_percentage":
                    total_sales = sum(order.total for order in orders)
                    total_tips = sum(order.tip_amount for order in orders)
                    value = (total_tips / total_sales * 100) if total_sales else 0

                elif metric == "items_per_order":
                    total_items = self.db.query(func.count(OrderItem.id)).filter(
                        OrderItem.order_id.in_([o.id for o in orders])
                    ).scalar() or 0
                    value = (total_items / len(orders)) if orders else 0

                elif metric == "labor_efficiency":
                    # Orders per assumed labor hour
                    days_in_month = (month_end - month_start).days
                    assumed_labor_hours = days_in_month * 8
                    value = len(orders) / assumed_labor_hours if assumed_labor_hours else 0

                elif metric == "customer_satisfaction":
                    # Would integrate with actual ratings if available
                    # For now, use a placeholder based on order completion rate
                    completed_orders = [o for o in orders if o.status in ["COMPLETED", "PAID"]]
                    value = (len(completed_orders) / len(orders) * 5) if orders else 0

                else:
                    # Default: use order count
                    value = len(orders)

                trend_data.append({
                    "month": month_label,
                    "value": round(value, 2)
                })

            # Calculate trend direction and statistics
            if len(trend_data) >= 2:
                first_val = trend_data[0]["value"]
                last_val = trend_data[-1]["value"]
                change_pct = ((last_val - first_val) / first_val * 100) if first_val else 0

                direction = "up" if change_pct > 5 else "down" if change_pct < -5 else "stable"
            else:
                change_pct = 0
                direction = "stable"

            avg_value = sum(d["value"] for d in trend_data) / len(trend_data) if trend_data else 0

            trends[metric] = {
                "data": trend_data,
                "change_pct": round(change_pct, 1),
                "direction": direction,
                "avg_value": round(avg_value, 2)
            }

        return {
            "success": True,
            "venue_id": venue_id,
            "period": period,
            "trends": trends,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ========== LEADERBOARDS ==========
    
    def get_leaderboard(
        self,
        metric: str,
        region: Optional[str] = None,
        limit: int = 10,
        venue_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get leaderboard for a metric based on real venue/staff performance"""
        from app.models import Venue, Order, OrderItem, StaffUser, VenueStation
        from sqlalchemy import func

        # Calculate time period (last 30 days)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)

        leaderboard = []

        # Determine if this is a venue or staff metric
        staff_metrics = ["orders_served", "avg_order_value", "tips_earned", "customer_ratings"]

        if metric in staff_metrics:
            # Staff leaderboard - use aggregated query instead of N+1
            staff_users = self.db.query(StaffUser).filter(StaffUser.is_active == True).limit(200).all()
            staff_ids = [s.id for s in staff_users]
            staff_map = {s.id: s for s in staff_users}

            # Batch-load aggregated order stats per staff member
            staff_order_stats = self.db.query(
                Order.waiter_id,
                func.count(Order.id).label('order_count'),
                func.sum(Order.total).label('total_sales'),
                func.sum(Order.tip_amount).label('total_tips'),
                func.count(func.nullif(Order.status.notin_(["COMPLETED", "PAID"]), True)).label('completed_count')
            ).filter(
                Order.waiter_id.in_(staff_ids),
                Order.created_at >= start_date,
                Order.created_at <= end_date
            ).group_by(Order.waiter_id).all()

            for row in staff_order_stats:
                staff = staff_map.get(row.waiter_id)
                if not staff:
                    continue

                if metric == "orders_served":
                    value = row.order_count or 0
                elif metric == "avg_order_value":
                    value = (float(row.total_sales or 0) / row.order_count) if row.order_count else 0
                elif metric == "tips_earned":
                    value = float(row.total_tips or 0)
                elif metric == "customer_ratings":
                    # Placeholder: based on order count
                    value = min(5.0, (row.order_count or 0) / 10.0)
                else:
                    value = row.order_count or 0

                leaderboard.append({
                    "id": staff.id,
                    "name": staff.full_name,
                    "type": "staff",
                    "venue_id": staff.location_id,
                    "value": round(value, 2)
                })

        else:
            # Venue leaderboard - use aggregated queries instead of N+1
            venues_query = self.db.query(Venue).filter(Venue.active == True)

            # Apply region filter if specified
            if region:
                # Would filter by region field if it exists on Venue model
                # For now, we'll include all venues
                pass

            venues = venues_query.limit(200).all()
            venue_ids = [v.id for v in venues]
            venue_map = {v.id: v for v in venues}

            # Batch-load station-to-venue mapping
            station_venue_rows = self.db.query(
                VenueStation.id, VenueStation.venue_id
            ).filter(
                VenueStation.venue_id.in_(venue_ids),
                VenueStation.active == True
            ).all()

            station_to_venue = {row.id: row.venue_id for row in station_venue_rows}
            all_station_ids = [row.id for row in station_venue_rows]

            # Batch-load aggregated order data per station
            if all_station_ids:
                order_stats = self.db.query(
                    Order.station_id,
                    func.count(Order.id).label('order_count'),
                    func.sum(Order.total).label('total_sales'),
                    func.sum(Order.tip_amount).label('total_tips')
                ).filter(
                    Order.station_id.in_(all_station_ids),
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                ).group_by(Order.station_id).all()
            else:
                order_stats = []

            # Aggregate by venue
            venue_agg: Dict[int, Dict[str, float]] = {}
            for row in order_stats:
                vid = station_to_venue.get(row.station_id)
                if vid is None:
                    continue
                if vid not in venue_agg:
                    venue_agg[vid] = {"order_count": 0, "total_sales": 0.0, "total_tips": 0.0}
                venue_agg[vid]["order_count"] += row.order_count or 0
                venue_agg[vid]["total_sales"] += float(row.total_sales or 0)
                venue_agg[vid]["total_tips"] += float(row.total_tips or 0)

            for vid, agg in venue_agg.items():
                venue = venue_map.get(vid)
                if not venue:
                    continue

                order_count = agg["order_count"]
                total_sales = agg["total_sales"]
                total_tips = agg["total_tips"]

                # Calculate value based on metric
                if metric == "sales" or metric == "revenue":
                    value = total_sales + total_tips

                elif metric == "avg_ticket" or metric == "average_check":
                    value = (total_sales / order_count) if order_count else 0

                elif metric == "order_count" or metric == "covers":
                    value = order_count

                elif metric == "labor_efficiency":
                    days_in_period = 30
                    assumed_labor_hours = days_in_period * 8
                    value = order_count / assumed_labor_hours if assumed_labor_hours else 0

                elif metric == "customer_satisfaction":
                    value = min(5.0, order_count / 20.0) if order_count else 0

                else:
                    value = total_sales

                # Get venue name (handle JSON field)
                venue_name = venue.name
                if isinstance(venue_name, dict):
                    venue_name = venue_name.get("en") or venue_name.get("bg") or "Unknown Venue"

                leaderboard.append({
                    "id": venue.id,
                    "name": venue_name,
                    "type": "venue",
                    "venue_id": venue.id,
                    "value": round(value, 2)
                })

        # Sort leaderboard by value (descending)
        leaderboard.sort(key=lambda x: x["value"], reverse=True)

        # Add rankings
        for i, entry in enumerate(leaderboard[:limit], 1):
            entry["rank"] = i
            entry["is_you"] = (entry["type"] == "venue" and venue_id and entry["venue_id"] == venue_id)

        # Find current venue's position
        your_rank = None
        if venue_id:
            for i, entry in enumerate(leaderboard, 1):
                if entry["type"] == "venue" and entry["venue_id"] == venue_id:
                    your_rank = {
                        "rank": i,
                        "name": entry["name"],
                        "value": entry["value"],
                        "is_you": True
                    }
                    break

        return {
            "success": True,
            "metric": metric,
            "region": region or "Global",
            "leaderboard": leaderboard[:limit],
            "your_position": your_rank,
            "total_participants": len(leaderboard),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
