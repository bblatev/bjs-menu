"""
P&L Analysis Service
Provides SpotOn Profit Assist-like financial analysis

Features:
- Automated P&L snapshot generation
- Cost saving opportunity detection
- Trend analysis and benchmarking
- AI-powered recommendations
- Real-time profit tracking
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, timedelta, date
from decimal import Decimal
import logging

from app.models import Order, OrderItem, MenuItem, StaffUser
from app.models.gap_features_models import PLSnapshot, SavingOpportunity

logger = logging.getLogger(__name__)


class CostData:
    """Container for cost breakdown data"""
    def __init__(
        self,
        food: float = 0,
        beverage: float = 0,
        labor: float = 0,
        operating: float = 0
    ):
        self.food = food
        self.beverage = beverage
        self.labor = labor
        self.operating = operating
        self.total = food + beverage + labor + operating

    @property
    def food_cost_pct(self) -> float:
        return 0

    @property
    def beverage_cost_pct(self) -> float:
        return 0


class LaborData:
    """Container for labor cost data"""
    def __init__(
        self,
        total: float = 0,
        regular_hours: float = 0,
        overtime_hours: float = 0,
        hourly_cost: float = 0,
        staff_count: int = 0
    ):
        self.total = total
        self.regular_hours = regular_hours
        self.overtime_hours = overtime_hours
        self.hourly_cost = hourly_cost
        self.staff_count = staff_count
        self.cost_pct = 0


class PLAnalysisResult:
    """Result container for P&L analysis"""
    def __init__(
        self,
        metrics: Dict,
        insights: List[str],
        opportunities: List['SavingOpportunityData'],
        trend_data: Dict
    ):
        self.metrics = metrics
        self.insights = insights
        self.opportunities = opportunities
        self.trend_data = trend_data

    def to_dict(self) -> Dict:
        return {
            "metrics": self.metrics,
            "insights": self.insights,
            "opportunities": [o.to_dict() for o in self.opportunities],
            "trend_data": self.trend_data
        }


class SavingOpportunityData:
    """Data class for saving opportunity"""
    def __init__(
        self,
        category: str,
        title: str,
        current_value: float,
        target_value: float,
        potential_savings: float,
        recommendations: List[str]
    ):
        self.category = category
        self.title = title
        self.current_value = current_value
        self.target_value = target_value
        self.potential_savings = potential_savings
        self.recommendations = recommendations

    def to_dict(self) -> Dict:
        return {
            "category": self.category,
            "title": self.title,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "potential_savings": self.potential_savings,
            "recommendations": self.recommendations
        }


# Industry benchmarks
INDUSTRY_BENCHMARKS = {
    "food_cost_pct": {"target": 28, "warning": 32, "critical": 35},
    "beverage_cost_pct": {"target": 20, "warning": 25, "critical": 28},
    "labor_cost_pct": {"target": 30, "warning": 35, "critical": 40},
    "prime_cost_pct": {"target": 60, "warning": 65, "critical": 70},
    "net_margin_pct": {"target": 10, "warning": 5, "critical": 0}
}


class PLAnalysisService:
    """
    AI-powered P&L analysis service
    Competitor to SpotOn Profit Assist
    """

    def __init__(self, db: Session):
        self.db = db

    async def analyze_profitability(
        self,
        venue_id: int,
        period: str = "last_30_days"
    ) -> PLAnalysisResult:
        """
        Comprehensive P&L analysis with AI insights

        Args:
            venue_id: Venue to analyze
            period: Time period (last_7_days, last_30_days, last_quarter, ytd)
        """
        # Determine date range
        start_date, end_date = self._get_date_range(period)

        # Gather financial data
        revenue = await self._get_revenue_data(venue_id, start_date, end_date)
        costs = await self._get_cost_data(venue_id, start_date, end_date, revenue)
        labor = await self._get_labor_costs(venue_id, start_date, end_date, revenue)

        # Calculate key metrics
        metrics = self._calculate_metrics(revenue, costs, labor)

        # Generate AI insights
        insights = await self._generate_insights(metrics, venue_id)

        # Find saving opportunities
        opportunities = await self._find_saving_opportunities(venue_id, metrics, costs, labor)

        # Get trend data
        trend_data = await self._get_trend_data(venue_id)

        return PLAnalysisResult(
            metrics=metrics,
            insights=insights,
            opportunities=opportunities,
            trend_data=trend_data
        )

    def _get_date_range(self, period: str) -> Tuple[date, date]:
        """Convert period string to date range"""
        today = date.today()

        if period == "last_7_days":
            return (today - timedelta(days=7), today)
        elif period == "last_30_days":
            return (today - timedelta(days=30), today)
        elif period == "last_quarter":
            return (today - timedelta(days=90), today)
        elif period == "ytd":
            return (date(today.year, 1, 1), today)
        elif period == "last_month":
            first_of_this_month = today.replace(day=1)
            last_of_last_month = first_of_this_month - timedelta(days=1)
            first_of_last_month = last_of_last_month.replace(day=1)
            return (first_of_last_month, last_of_last_month)
        else:
            return (today - timedelta(days=30), today)

    async def _get_revenue_data(
        self,
        venue_id: int,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Get revenue data for the period"""
        result = self.db.query(
            func.sum(Order.total).label('gross_revenue'),
            func.sum(Order.subtotal).label('net_revenue'),
            func.sum(Order.discount).label('total_discounts'),
            func.sum(Order.tip_amount).label('total_tips'),
            func.count(Order.id).label('order_count'),
            func.sum(Order.guest_count).label('guest_count')
        ).filter(
            Order.venue_id == venue_id,
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date,
            Order.status != 'cancelled'
        ).first()

        gross = float(result.gross_revenue or 0)
        net = float(result.net_revenue or 0)
        discounts = float(result.total_discounts or 0)
        tips = float(result.total_tips or 0)
        orders = result.order_count or 0
        guests = result.guest_count or 0

        return {
            "gross_revenue": gross,
            "net_revenue": net if net > 0 else gross,
            "total_discounts": discounts,
            "total_tips": tips,
            "order_count": orders,
            "guest_count": guests,
            "avg_ticket": gross / orders if orders > 0 else 0,
            "avg_per_guest": gross / guests if guests > 0 else 0
        }

    async def _get_cost_data(
        self,
        venue_id: int,
        start_date: date,
        end_date: date,
        revenue: Dict
    ) -> CostData:
        """
        Get cost data for the period

        In a full implementation, this would pull from:
        - Inventory/purchase order data for COGS
        - Recipe costs for food cost
        - Supplier invoices

        For now, we estimate based on industry averages and item costs
        """
        # Get item costs from menu items sold
        item_costs = self.db.query(
            func.sum(
                OrderItem.quantity * func.coalesce(MenuItem.cost, MenuItem.price * 0.3)
            ).label('estimated_food_cost')
        ).join(
            MenuItem, OrderItem.menu_item_id == MenuItem.id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            Order.venue_id == venue_id,
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date,
            Order.status != 'cancelled'
        ).first()

        estimated_food_cost = float(item_costs.estimated_food_cost or 0)

        # If no cost data, estimate at 30% of revenue
        if estimated_food_cost == 0:
            estimated_food_cost = revenue["gross_revenue"] * 0.30

        # Estimate beverage at 20% of revenue (restaurants typically)
        # In production, would separate food vs beverage items
        estimated_beverage_cost = revenue["gross_revenue"] * 0.05

        # Operating expenses (rent, utilities, etc.) - estimated at 15%
        operating_expenses = revenue["gross_revenue"] * 0.15

        costs = CostData(
            food=estimated_food_cost * 0.85,  # Assume 85% is food
            beverage=estimated_food_cost * 0.15 + estimated_beverage_cost,
            operating=operating_expenses
        )

        return costs

    async def _get_labor_costs(
        self,
        venue_id: int,
        start_date: date,
        end_date: date,
        revenue: Dict
    ) -> LaborData:
        """
        Get labor cost data for the period

        In production, this would pull from:
        - Time clock entries
        - Payroll data
        - Shift schedules

        For now, estimate based on staff count and industry averages
        """
        # Get active staff count
        staff_count = self.db.query(func.count(StaffUser.id)).filter(
            StaffUser.venue_id == venue_id,
            StaffUser.active == True
        ).scalar() or 0

        # Estimate labor costs
        # Average hourly wage in Bulgaria: ~6-8 BGN/hr for restaurant staff
        # Assuming full-time equivalent calculation
        days_in_period = (end_date - start_date).days + 1
        avg_hours_per_day = 8
        avg_hourly_wage = 15  # BGN or whatever currency

        estimated_labor = staff_count * days_in_period * avg_hours_per_day * avg_hourly_wage * 0.5  # Assume 50% utilization

        # If revenue exists, estimate labor at ~30% of revenue as fallback
        if revenue["gross_revenue"] > 0:
            industry_estimate = revenue["gross_revenue"] * 0.30
            # Use the lower of the two estimates
            estimated_labor = min(estimated_labor, industry_estimate) if estimated_labor > 0 else industry_estimate

        labor = LaborData(
            total=estimated_labor,
            regular_hours=staff_count * days_in_period * avg_hours_per_day * 0.5,
            overtime_hours=0,
            hourly_cost=avg_hourly_wage,
            staff_count=staff_count
        )

        if revenue["gross_revenue"] > 0:
            labor.cost_pct = (labor.total / revenue["gross_revenue"]) * 100

        return labor

    def _calculate_metrics(
        self,
        revenue: Dict,
        costs: CostData,
        labor: LaborData
    ) -> Dict:
        """Calculate all P&L metrics"""
        gross = revenue["gross_revenue"]

        if gross == 0:
            return {
                "gross_revenue": 0,
                "net_revenue": 0,
                "food_cost": 0,
                "food_cost_pct": 0,
                "beverage_cost": 0,
                "beverage_cost_pct": 0,
                "labor_cost": 0,
                "labor_cost_pct": 0,
                "prime_cost": 0,
                "prime_cost_pct": 0,
                "operating_expenses": 0,
                "net_profit": 0,
                "net_margin_pct": 0,
                "order_count": revenue["order_count"],
                "avg_ticket": 0,
                "guest_count": revenue["guest_count"]
            }

        prime_cost = costs.food + costs.beverage + labor.total
        net_profit = gross - costs.total - labor.total

        return {
            "gross_revenue": gross,
            "net_revenue": revenue["net_revenue"],
            "food_cost": costs.food,
            "food_cost_pct": (costs.food / gross) * 100,
            "beverage_cost": costs.beverage,
            "beverage_cost_pct": (costs.beverage / gross) * 100,
            "labor_cost": labor.total,
            "labor_cost_pct": (labor.total / gross) * 100,
            "prime_cost": prime_cost,
            "prime_cost_pct": (prime_cost / gross) * 100,
            "operating_expenses": costs.operating,
            "net_profit": net_profit,
            "net_margin_pct": (net_profit / gross) * 100,
            "order_count": revenue["order_count"],
            "avg_ticket": revenue["avg_ticket"],
            "guest_count": revenue["guest_count"],
            "total_discounts": revenue["total_discounts"],
            "total_tips": revenue["total_tips"]
        }

    async def _generate_insights(self, metrics: Dict, venue_id: int) -> List[str]:
        """Generate AI-powered insights based on metrics"""
        insights = []

        # Check food cost
        food_cost_pct = metrics.get("food_cost_pct", 0)
        if food_cost_pct > INDUSTRY_BENCHMARKS["food_cost_pct"]["critical"]:
            insights.append(
                f"⚠️ Food cost is critically high at {food_cost_pct:.1f}% "
                f"(target: {INDUSTRY_BENCHMARKS['food_cost_pct']['target']}%). "
                "Review portion sizes and supplier pricing immediately."
            )
        elif food_cost_pct > INDUSTRY_BENCHMARKS["food_cost_pct"]["warning"]:
            insights.append(
                f"Food cost at {food_cost_pct:.1f}% is above optimal range. "
                "Consider reviewing high-cost menu items."
            )

        # Check labor cost
        labor_cost_pct = metrics.get("labor_cost_pct", 0)
        if labor_cost_pct > INDUSTRY_BENCHMARKS["labor_cost_pct"]["critical"]:
            insights.append(
                f"⚠️ Labor cost is critically high at {labor_cost_pct:.1f}%. "
                "Review scheduling and consider cross-training staff."
            )
        elif labor_cost_pct > INDUSTRY_BENCHMARKS["labor_cost_pct"]["warning"]:
            insights.append(
                f"Labor cost at {labor_cost_pct:.1f}% could be optimized. "
                "Analyze peak hours vs staffing levels."
            )

        # Check prime cost
        prime_cost_pct = metrics.get("prime_cost_pct", 0)
        if prime_cost_pct > INDUSTRY_BENCHMARKS["prime_cost_pct"]["critical"]:
            insights.append(
                f"⚠️ Prime cost ({prime_cost_pct:.1f}%) exceeds healthy threshold. "
                "This is squeezing your profit margin significantly."
            )

        # Positive insights
        net_margin = metrics.get("net_margin_pct", 0)
        if net_margin > INDUSTRY_BENCHMARKS["net_margin_pct"]["target"]:
            insights.append(
                f"✅ Net profit margin of {net_margin:.1f}% is healthy. "
                "Keep monitoring to maintain this performance."
            )

        # Average ticket insight
        avg_ticket = metrics.get("avg_ticket", 0)
        if avg_ticket > 0:
            insights.append(
                f"Average ticket: ${avg_ticket:.2f}. Consider upselling strategies to increase this."
            )

        return insights

    async def _find_saving_opportunities(
        self,
        venue_id: int,
        metrics: Dict,
        costs: CostData,
        labor: LaborData
    ) -> List[SavingOpportunityData]:
        """Find actionable cost saving opportunities"""
        opportunities = []
        gross = metrics.get("gross_revenue", 0)

        if gross == 0:
            return opportunities

        # Food cost opportunity
        food_cost_pct = metrics.get("food_cost_pct", 0)
        if food_cost_pct > INDUSTRY_BENCHMARKS["food_cost_pct"]["target"]:
            target_cost = gross * (INDUSTRY_BENCHMARKS["food_cost_pct"]["target"] / 100)
            potential_savings = costs.food - target_cost

            if potential_savings > 0:
                opportunities.append(SavingOpportunityData(
                    category="food_cost",
                    title="Food Cost Optimization",
                    current_value=food_cost_pct,
                    target_value=INDUSTRY_BENCHMARKS["food_cost_pct"]["target"],
                    potential_savings=potential_savings,
                    recommendations=[
                        "Review portion sizes for top 10 cost items",
                        "Negotiate bulk pricing with suppliers",
                        "Implement waste tracking and reduction program",
                        "Consider seasonal menu items to leverage lower-cost ingredients",
                        "Audit inventory for spoilage and theft"
                    ]
                ))

        # Labor cost opportunity
        labor_cost_pct = metrics.get("labor_cost_pct", 0)
        if labor_cost_pct > INDUSTRY_BENCHMARKS["labor_cost_pct"]["target"]:
            target_labor = gross * (INDUSTRY_BENCHMARKS["labor_cost_pct"]["target"] / 100)
            potential_savings = labor.total - target_labor

            if potential_savings > 0:
                opportunities.append(SavingOpportunityData(
                    category="labor",
                    title="Labor Cost Optimization",
                    current_value=labor_cost_pct,
                    target_value=INDUSTRY_BENCHMARKS["labor_cost_pct"]["target"],
                    potential_savings=potential_savings,
                    recommendations=[
                        "Align staffing levels with demand forecasts",
                        "Cross-train employees for flexibility",
                        "Review overtime hours and causes",
                        "Consider technology to improve efficiency",
                        "Optimize shift scheduling based on sales patterns"
                    ]
                ))

        # Menu optimization opportunity
        underperforming = await self._get_underperforming_items(venue_id)
        if underperforming:
            opportunities.append(SavingOpportunityData(
                category="menu_optimization",
                title=f"{len(underperforming)} Menu Items Need Attention",
                current_value=len(underperforming),
                target_value=0,
                potential_savings=len(underperforming) * 100,  # Rough estimate
                recommendations=[
                    f"Review and potentially remove: {', '.join([i['name'] for i in underperforming[:3]])}",
                    "Consider repositioning slow items on the menu",
                    "Train staff to recommend alternatives",
                    "Adjust pricing or portions for low-margin items"
                ]
            ))

        # Discount opportunity
        discounts = metrics.get("total_discounts", 0)
        discount_pct = (discounts / gross) * 100 if gross > 0 else 0
        if discount_pct > 5:  # More than 5% in discounts
            opportunities.append(SavingOpportunityData(
                category="discounts",
                title="High Discount Rate",
                current_value=discount_pct,
                target_value=3.0,
                potential_savings=discounts - (gross * 0.03),
                recommendations=[
                    "Review discount authorization policies",
                    "Analyze which items are most frequently discounted",
                    "Train staff on proper discount procedures",
                    "Consider loyalty programs instead of ad-hoc discounts"
                ]
            ))

        return opportunities

    async def _get_underperforming_items(self, venue_id: int) -> List[Dict]:
        """Get menu items that are underperforming"""
        # Items ordered less than 5 times in 30 days with below-average margin
        thirty_days_ago = date.today() - timedelta(days=30)

        items = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            MenuItem.cost,
            func.count(OrderItem.id).label('order_count')
        ).outerjoin(
            OrderItem, MenuItem.id == OrderItem.menu_item_id
        ).outerjoin(
            Order, and_(
                OrderItem.order_id == Order.id,
                Order.created_at >= thirty_days_ago,
                Order.status != 'cancelled'
            )
        ).filter(
            MenuItem.venue_id == venue_id,
            MenuItem.available == True
        ).group_by(
            MenuItem.id, MenuItem.name, MenuItem.price, MenuItem.cost
        ).having(
            func.count(OrderItem.id) < 5
        ).all()

        result = []
        for item in items[:10]:
            name = item.name.get('en', item.name.get('bg', 'Unknown')) if isinstance(item.name, dict) else str(item.name)
            result.append({
                "id": item.id,
                "name": name,
                "price": item.price,
                "orders": item.order_count
            })

        return result

    async def _get_trend_data(self, venue_id: int) -> Dict:
        """Get historical trend data for charts"""
        # Get weekly data for the last 8 weeks
        weeks = []
        today = date.today()

        for i in range(8):
            week_end = today - timedelta(days=i * 7)
            week_start = week_end - timedelta(days=6)

            result = self.db.query(
                func.sum(Order.total).label('revenue'),
                func.count(Order.id).label('orders')
            ).filter(
                Order.venue_id == venue_id,
                func.date(Order.created_at) >= week_start,
                func.date(Order.created_at) <= week_end,
                Order.status != 'cancelled'
            ).first()

            weeks.append({
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "revenue": float(result.revenue or 0),
                "orders": result.orders or 0
            })

        weeks.reverse()  # Chronological order

        return {
            "weekly_revenue": weeks,
            "labels": [w["week_start"] for w in weeks],
            "revenue_values": [w["revenue"] for w in weeks],
            "order_values": [w["orders"] for w in weeks]
        }

    async def create_snapshot(
        self,
        venue_id: int,
        period_type: str,
        start_date: date,
        end_date: date
    ) -> PLSnapshot:
        """Create and save a P&L snapshot"""
        # Get analysis
        period_map = {
            "daily": "last_7_days",
            "weekly": "last_7_days",
            "monthly": "last_30_days"
        }
        analysis = await self.analyze_profitability(venue_id, period_map.get(period_type, "last_30_days"))

        # Create snapshot
        snapshot = PLSnapshot(
            venue_id=venue_id,
            period_type=period_type,
            period_start=start_date,
            period_end=end_date,
            gross_revenue=Decimal(str(analysis.metrics["gross_revenue"])),
            net_revenue=Decimal(str(analysis.metrics["net_revenue"])),
            food_cost=Decimal(str(analysis.metrics["food_cost"])),
            food_cost_pct=Decimal(str(analysis.metrics["food_cost_pct"])),
            beverage_cost=Decimal(str(analysis.metrics["beverage_cost"])),
            beverage_cost_pct=Decimal(str(analysis.metrics["beverage_cost_pct"])),
            labor_cost=Decimal(str(analysis.metrics["labor_cost"])),
            labor_cost_pct=Decimal(str(analysis.metrics["labor_cost_pct"])),
            prime_cost=Decimal(str(analysis.metrics["prime_cost"])),
            prime_cost_pct=Decimal(str(analysis.metrics["prime_cost_pct"])),
            operating_expenses=Decimal(str(analysis.metrics["operating_expenses"])),
            net_profit=Decimal(str(analysis.metrics["net_profit"])),
            net_margin_pct=Decimal(str(analysis.metrics["net_margin_pct"])),
            order_count=analysis.metrics["order_count"],
            avg_ticket=Decimal(str(analysis.metrics["avg_ticket"])),
            guest_count=analysis.metrics["guest_count"],
            metadata={"insights": analysis.insights}
        )

        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)

        return snapshot

    async def save_opportunity(
        self,
        venue_id: int,
        opportunity: SavingOpportunityData
    ) -> SavingOpportunity:
        """Save a saving opportunity to the database"""
        db_opportunity = SavingOpportunity(
            venue_id=venue_id,
            category=opportunity.category,
            title=opportunity.title,
            current_value=Decimal(str(opportunity.current_value)),
            target_value=Decimal(str(opportunity.target_value)),
            potential_savings=Decimal(str(opportunity.potential_savings)),
            recommendations=opportunity.recommendations
        )

        self.db.add(db_opportunity)
        self.db.commit()
        self.db.refresh(db_opportunity)

        return db_opportunity

    async def get_snapshots(
        self,
        venue_id: int,
        period_type: Optional[str] = None,
        limit: int = 30
    ) -> List[PLSnapshot]:
        """Get P&L snapshots for a venue"""
        query = self.db.query(PLSnapshot).filter(
            PLSnapshot.venue_id == venue_id
        )

        if period_type:
            query = query.filter(PLSnapshot.period_type == period_type)

        return query.order_by(desc(PLSnapshot.period_start)).limit(limit).all()

    async def get_opportunities(
        self,
        venue_id: int,
        status: Optional[str] = None
    ) -> List[SavingOpportunity]:
        """Get saving opportunities for a venue"""
        query = self.db.query(SavingOpportunity).filter(
            SavingOpportunity.venue_id == venue_id
        )

        if status:
            query = query.filter(SavingOpportunity.status == status)

        return query.order_by(desc(SavingOpportunity.potential_savings)).all()

    async def update_opportunity_status(
        self,
        opportunity_id: int,
        status: str,
        actual_savings: Optional[float] = None
    ) -> SavingOpportunity:
        """Update the status of a saving opportunity"""
        opportunity = self.db.query(SavingOpportunity).filter(
            SavingOpportunity.id == opportunity_id
        ).first()

        if opportunity:
            opportunity.status = status
            if status == "completed":
                opportunity.completed_at = datetime.utcnow()
                if actual_savings is not None:
                    opportunity.actual_savings = Decimal(str(actual_savings))
            self.db.commit()
            self.db.refresh(opportunity)

        return opportunity

    async def get_comparison(
        self,
        venue_id: int,
        current_period: str,
        comparison_period: str
    ) -> Dict:
        """Compare two periods"""
        current = await self.analyze_profitability(venue_id, current_period)
        previous = await self.analyze_profitability(venue_id, comparison_period)

        def calc_change(current_val: float, previous_val: float) -> Dict:
            if previous_val == 0:
                return {"value": current_val, "change": 0, "change_pct": 0}
            change = current_val - previous_val
            change_pct = (change / previous_val) * 100
            return {"value": current_val, "change": change, "change_pct": change_pct}

        return {
            "current_period": current_period,
            "comparison_period": comparison_period,
            "metrics": {
                "revenue": calc_change(
                    current.metrics["gross_revenue"],
                    previous.metrics["gross_revenue"]
                ),
                "orders": calc_change(
                    current.metrics["order_count"],
                    previous.metrics["order_count"]
                ),
                "avg_ticket": calc_change(
                    current.metrics["avg_ticket"],
                    previous.metrics["avg_ticket"]
                ),
                "food_cost_pct": calc_change(
                    current.metrics["food_cost_pct"],
                    previous.metrics["food_cost_pct"]
                ),
                "labor_cost_pct": calc_change(
                    current.metrics["labor_cost_pct"],
                    previous.metrics["labor_cost_pct"]
                ),
                "net_margin_pct": calc_change(
                    current.metrics["net_margin_pct"],
                    previous.metrics["net_margin_pct"]
                )
            }
        }
