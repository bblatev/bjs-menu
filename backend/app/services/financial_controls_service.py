"""
Financial Controls Service - Section T
Prime cost tracking, abuse detection, and financial analytics
"""
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import uuid


class FinancialControlsService:
    """Service for financial controls, prime cost tracking, and abuse detection."""
    
    # ==================== PRIME COST TRACKING ====================
    
    @staticmethod
    def record_prime_cost(
        db: Session,
        venue_id: int,
        period_date: date,
        food_cost: Decimal,
        beverage_cost: Decimal,
        labor_cost: Decimal,
        revenue: Decimal,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record prime cost data for a period.
        Prime Cost = Food Cost + Beverage Cost + Labor Cost
        Prime Cost Percentage = Prime Cost / Revenue * 100
        """
        from app.models.advanced_features_v9 import PrimeCostTracking
        
        total_prime_cost = food_cost + beverage_cost + labor_cost
        prime_cost_percentage = (total_prime_cost / revenue * 100) if revenue > 0 else Decimal("0")
        food_cost_percentage = (food_cost / revenue * 100) if revenue > 0 else Decimal("0")
        beverage_cost_percentage = (beverage_cost / revenue * 100) if revenue > 0 else Decimal("0")
        labor_cost_percentage = (labor_cost / revenue * 100) if revenue > 0 else Decimal("0")
        
        # Check if record already exists for this period
        existing = db.query(PrimeCostTracking).filter(
            PrimeCostTracking.venue_id == venue_id,
            PrimeCostTracking.period_date == period_date
        ).first()
        
        if existing:
            existing.food_cost = food_cost
            existing.beverage_cost = beverage_cost
            existing.labor_cost = labor_cost
            existing.total_prime_cost = total_prime_cost
            existing.revenue = revenue
            existing.prime_cost_percentage = prime_cost_percentage
            existing.food_cost_percentage = food_cost_percentage
            existing.beverage_cost_percentage = beverage_cost_percentage
            existing.labor_cost_percentage = labor_cost_percentage
            existing.notes = notes
            existing.updated_at = datetime.now(timezone.utc)
            record = existing
        else:
            record = PrimeCostTracking(
                venue_id=venue_id,
                period_date=period_date,
                food_cost=food_cost,
                beverage_cost=beverage_cost,
                labor_cost=labor_cost,
                total_prime_cost=total_prime_cost,
                revenue=revenue,
                prime_cost_percentage=prime_cost_percentage,
                food_cost_percentage=food_cost_percentage,
                beverage_cost_percentage=beverage_cost_percentage,
                labor_cost_percentage=labor_cost_percentage,
                notes=notes
            )
            db.add(record)
        
        db.commit()
        db.refresh(record)
        
        # Determine health status
        status = "healthy"
        if prime_cost_percentage > Decimal("70"):
            status = "critical"
        elif prime_cost_percentage > Decimal("65"):
            status = "warning"
        
        return {
            "id": record.id,
            "period_date": str(period_date),
            "food_cost": float(food_cost),
            "beverage_cost": float(beverage_cost),
            "labor_cost": float(labor_cost),
            "total_prime_cost": float(total_prime_cost),
            "revenue": float(revenue),
            "prime_cost_percentage": float(prime_cost_percentage),
            "food_cost_percentage": float(food_cost_percentage),
            "beverage_cost_percentage": float(beverage_cost_percentage),
            "labor_cost_percentage": float(labor_cost_percentage),
            "status": status,
            "target_prime_cost": 60.0,
            "variance_from_target": float(prime_cost_percentage - Decimal("60"))
        }
    
    @staticmethod
    def get_prime_cost_dashboard(
        db: Session,
        venue_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get prime cost dashboard with trends and analysis."""
        from app.models.advanced_features_v9 import PrimeCostTracking
        from datetime import datetime as dt

        start_dt = dt.combine(start_date, dt.min.time())
        end_dt = dt.combine(end_date, dt.max.time())

        records = db.query(PrimeCostTracking).filter(
            PrimeCostTracking.venue_id == venue_id,
            PrimeCostTracking.tracking_date >= start_dt,
            PrimeCostTracking.tracking_date <= end_dt
        ).order_by(PrimeCostTracking.tracking_date).all()

        if not records:
            return {
                "venue_id": venue_id,
                "period": {"start": str(start_date), "end": str(end_date)},
                "message": "No data for this period",
                "data": []
            }

        # Calculate aggregates
        total_food_cost = sum(r.food_cost or 0 for r in records)
        total_labor_cost = sum(r.labor_cost or 0 for r in records)
        total_revenue = sum(r.total_revenue or 0 for r in records)
        total_prime_cost = sum(r.prime_cost or 0 for r in records)

        avg_prime_cost_pct = (total_prime_cost / total_revenue * 100) if total_revenue > 0 else 0

        # Trend analysis
        trend_data = []
        for r in records:
            trend_data.append({
                "date": str(r.tracking_date.date()) if r.tracking_date else None,
                "prime_cost_percentage": float(r.prime_cost_percent or 0),
                "food_pct": float(r.food_cost_percent or 0),
                "labor_pct": float(r.labor_cost_percent or 0)
            })

        # Calculate trend direction
        if len(records) >= 2:
            first_half = records[:len(records)//2]
            second_half = records[len(records)//2:]
            first_avg = sum(r.prime_cost_percent or 0 for r in first_half) / len(first_half)
            second_avg = sum(r.prime_cost_percent or 0 for r in second_half) / len(second_half)
            trend = "improving" if second_avg < first_avg else "worsening" if second_avg > first_avg else "stable"
        else:
            trend = "insufficient_data"

        return {
            "venue_id": venue_id,
            "period": {"start": str(start_date), "end": str(end_date)},
            "summary": {
                "total_food_cost": float(total_food_cost),
                "total_labor_cost": float(total_labor_cost),
                "total_prime_cost": float(total_prime_cost),
                "total_revenue": float(total_revenue),
                "average_prime_cost_percentage": float(avg_prime_cost_pct),
                "target_percentage": 60.0,
                "variance_from_target": float(avg_prime_cost_pct - 60)
            },
            "trend": trend,
            "trend_data": trend_data,
            "recommendations": FinancialControlsService._generate_cost_recommendations(
                float(total_food_cost / total_revenue * 100) if total_revenue > 0 else 0,
                0,  # beverage not tracked separately
                float(total_labor_cost / total_revenue * 100) if total_revenue > 0 else 0
            )
        }
    
    @staticmethod
    def _generate_cost_recommendations(food_pct: float, bev_pct: float, labor_pct: float) -> List[str]:
        """Generate recommendations based on cost percentages."""
        recommendations = []
        
        if food_pct > 32:
            recommendations.append(f"Food cost at {food_pct:.1f}% exceeds 32% target. Review portion sizes and supplier pricing.")
        if bev_pct > 25:
            recommendations.append(f"Beverage cost at {bev_pct:.1f}% exceeds 25% target. Check pour accuracy and pricing.")
        if labor_pct > 30:
            recommendations.append(f"Labor cost at {labor_pct:.1f}% exceeds 30% target. Review scheduling efficiency.")
        
        if not recommendations:
            recommendations.append("All cost categories within target ranges. Maintain current practices.")
        
        return recommendations
    
    # ==================== ABUSE DETECTION ====================
    
    @staticmethod
    def get_or_create_abuse_config(
        db: Session,
        venue_id: int
    ) -> Dict[str, Any]:
        """Get or create abuse detection configuration."""
        from app.models.advanced_features_v9 import AbuseDetectionConfig
        
        config = db.query(AbuseDetectionConfig).filter(
            AbuseDetectionConfig.venue_id == venue_id
        ).first()
        
        if not config:
            config = AbuseDetectionConfig(
                venue_id=venue_id,
                enabled=True,
                refund_threshold_count=5,
                refund_threshold_period_hours=24,
                refund_threshold_amount=Decimal("100.00"),
                discount_threshold_count=10,
                discount_threshold_period_hours=8,
                discount_threshold_percentage=Decimal("50.0"),
                void_threshold_count=8,
                void_threshold_period_hours=8,
                suspicious_time_start="22:00",
                suspicious_time_end="06:00",
                alert_manager=True,
                alert_email=None,
                auto_lock_on_critical=False
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        
        return {
            "id": config.id,
            "venue_id": config.venue_id,
            "enabled": config.enabled,
            "thresholds": {
                "refunds": {
                    "count": config.refund_threshold_count,
                    "period_hours": config.refund_threshold_period_hours,
                    "amount": float(config.refund_threshold_amount)
                },
                "discounts": {
                    "count": config.discount_threshold_count,
                    "period_hours": config.discount_threshold_period_hours,
                    "max_percentage": float(config.discount_threshold_percentage)
                },
                "voids": {
                    "count": config.void_threshold_count,
                    "period_hours": config.void_threshold_period_hours
                }
            },
            "suspicious_hours": {
                "start": config.suspicious_time_start,
                "end": config.suspicious_time_end
            },
            "actions": {
                "alert_manager": config.alert_manager,
                "alert_email": config.alert_email,
                "auto_lock_on_critical": config.auto_lock_on_critical
            }
        }
    
    @staticmethod
    def update_abuse_config(
        db: Session,
        venue_id: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update abuse detection configuration."""
        from app.models.advanced_features_v9 import AbuseDetectionConfig
        
        config = db.query(AbuseDetectionConfig).filter(
            AbuseDetectionConfig.venue_id == venue_id
        ).first()
        
        if not config:
            raise ValueError(f"No abuse config found for venue {venue_id}")
        
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        config.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(config)
        
        return FinancialControlsService.get_or_create_abuse_config(db, venue_id)
    
    @staticmethod
    def check_for_abuse(
        db: Session,
        venue_id: int,
        staff_id: int,
        action_type: str,  # "refund", "discount", "void"
        amount: Decimal,
        order_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if an action triggers abuse detection.
        Returns alert if suspicious activity detected.
        """
        from app.models.advanced_features_v9 import AbuseDetectionConfig, AbuseAlert
        
        config = db.query(AbuseDetectionConfig).filter(
            AbuseDetectionConfig.venue_id == venue_id
        ).first()
        
        if not config or not config.enabled:
            return {"alert_triggered": False, "message": "Abuse detection not enabled"}
        
        now = datetime.now(timezone.utc)
        alerts_triggered = []
        severity = "low"
        
        # Check based on action type
        if action_type == "refund":
            period_start = now - timedelta(hours=config.refund_threshold_period_hours)
            
            # Count recent refunds by this staff member
            recent_count = db.query(AbuseAlert).filter(
                AbuseAlert.venue_id == venue_id,
                AbuseAlert.staff_id == staff_id,
                AbuseAlert.alert_type == "refund",
                AbuseAlert.created_at >= period_start
            ).count()
            
            if recent_count + 1 >= config.refund_threshold_count:
                alerts_triggered.append(f"Refund count threshold exceeded ({recent_count + 1}/{config.refund_threshold_count})")
                severity = "high"
            
            if amount >= config.refund_threshold_amount:
                alerts_triggered.append(f"Large refund amount: {amount}")
                severity = "critical" if severity == "high" else "medium"
        
        elif action_type == "discount":
            period_start = now - timedelta(hours=config.discount_threshold_period_hours)
            
            recent_count = db.query(AbuseAlert).filter(
                AbuseAlert.venue_id == venue_id,
                AbuseAlert.staff_id == staff_id,
                AbuseAlert.alert_type == "discount",
                AbuseAlert.created_at >= period_start
            ).count()
            
            if recent_count + 1 >= config.discount_threshold_count:
                alerts_triggered.append(f"Discount count threshold exceeded ({recent_count + 1}/{config.discount_threshold_count})")
                severity = "high"
        
        elif action_type == "void":
            period_start = now - timedelta(hours=config.void_threshold_period_hours)
            
            recent_count = db.query(AbuseAlert).filter(
                AbuseAlert.venue_id == venue_id,
                AbuseAlert.staff_id == staff_id,
                AbuseAlert.alert_type == "void",
                AbuseAlert.created_at >= period_start
            ).count()
            
            if recent_count + 1 >= config.void_threshold_count:
                alerts_triggered.append(f"Void count threshold exceeded ({recent_count + 1}/{config.void_threshold_count})")
                severity = "high"
        
        # Check for suspicious hours
        current_time = now.strftime("%H:%M")
        if config.suspicious_time_start and config.suspicious_time_end:
            if config.suspicious_time_start <= current_time or current_time <= config.suspicious_time_end:
                alerts_triggered.append(f"Action during suspicious hours ({current_time})")
                severity = "medium" if severity == "low" else severity
        
        if alerts_triggered:
            # Create alert record
            alert = AbuseAlert(
                venue_id=venue_id,
                staff_id=staff_id,
                alert_type=action_type,
                severity=severity,
                description="; ".join(alerts_triggered),
                amount=amount,
                order_id=order_id,
                reason=reason,
                status="pending",
                auto_flagged=True
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            return {
                "alert_triggered": True,
                "alert_id": alert.id,
                "severity": severity,
                "reasons": alerts_triggered,
                "action_allowed": severity != "critical" or not config.auto_lock_on_critical,
                "requires_manager_approval": severity in ["high", "critical"]
            }
        
        return {"alert_triggered": False, "message": "No suspicious activity detected"}
    
    @staticmethod
    def get_pending_alerts(
        db: Session,
        venue_id: int,
        severity: Optional[str] = None,
        staff_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get pending abuse alerts for investigation."""
        from app.models.advanced_features_v9 import AbuseAlert
        
        query = db.query(AbuseAlert).filter(
            AbuseAlert.venue_id == venue_id,
            AbuseAlert.status == "pending"
        )
        
        if severity:
            query = query.filter(AbuseAlert.severity == severity)
        if staff_id:
            query = query.filter(AbuseAlert.staff_id == staff_id)
        
        alerts = query.order_by(AbuseAlert.created_at.desc()).all()
        
        return [{
            "id": a.id,
            "staff_id": a.staff_id,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "description": a.description,
            "amount": float(a.amount) if a.amount else None,
            "order_id": a.order_id,
            "reason": a.reason,
            "created_at": a.created_at.isoformat(),
            "auto_flagged": a.auto_flagged
        } for a in alerts]
    
    @staticmethod
    def investigate_alert(
        db: Session,
        alert_id: int,
        investigator_id: int,
        status: str,  # "investigating", "confirmed", "dismissed"
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update alert investigation status."""
        from app.models.advanced_features_v9 import AbuseAlert
        
        alert = db.query(AbuseAlert).filter(AbuseAlert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        
        alert.status = status
        alert.investigated_by = investigator_id
        alert.investigated_at = datetime.now(timezone.utc)
        alert.investigation_notes = notes
        alert.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(alert)
        
        return {
            "id": alert.id,
            "status": alert.status,
            "investigated_by": alert.investigated_by,
            "investigated_at": alert.investigated_at.isoformat(),
            "notes": alert.investigation_notes
        }
    
    @staticmethod
    def get_abuse_analytics(
        db: Session,
        venue_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get abuse analytics for a period."""
        from app.models.advanced_features_v9 import AbuseAlert
        
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        alerts = db.query(AbuseAlert).filter(
            AbuseAlert.venue_id == venue_id,
            AbuseAlert.created_at >= start_dt,
            AbuseAlert.created_at <= end_dt
        ).all()
        
        # Group by type
        by_type = {}
        by_severity = {}
        by_staff = {}
        total_amount = Decimal("0")
        
        for alert in alerts:
            by_type[alert.alert_type] = by_type.get(alert.alert_type, 0) + 1
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
            by_staff[alert.staff_id] = by_staff.get(alert.staff_id, 0) + 1
            if alert.amount:
                total_amount += alert.amount
        
        # Find repeat offenders (3+ alerts)
        repeat_offenders = [staff_id for staff_id, count in by_staff.items() if count >= 3]
        
        return {
            "venue_id": venue_id,
            "period": {"start": str(start_date), "end": str(end_date)},
            "total_alerts": len(alerts),
            "by_type": by_type,
            "by_severity": by_severity,
            "by_staff": by_staff,
            "total_amount_flagged": float(total_amount),
            "repeat_offenders": repeat_offenders,
            "confirmed_count": sum(1 for a in alerts if a.status == "confirmed"),
            "dismissed_count": sum(1 for a in alerts if a.status == "dismissed"),
            "pending_count": sum(1 for a in alerts if a.status == "pending")
        }
    
    # ==================== PROFIT MARGIN TRACKING ====================
    
    @staticmethod
    def calculate_item_profitability(
        db: Session,
        venue_id: int,
        menu_item_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Calculate profitability metrics for a menu item."""
        from app.models import MenuItem, Order, OrderItem

        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Get menu item details
        item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
        if not item:
            return {"error": "Menu item not found", "menu_item_id": menu_item_id}

        # Get sales data for this item
        sales_data = db.query(
            func.sum(OrderItem.quantity).label('total_qty'),
            func.sum(OrderItem.price * OrderItem.quantity).label('total_revenue')
        ).join(Order).filter(
            OrderItem.menu_item_id == menu_item_id,
            Order.venue_id == venue_id,
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.status != 'cancelled'
        ).first()

        units_sold = int(sales_data.total_qty or 0)
        gross_revenue = float(sales_data.total_revenue or 0)

        # Calculate cost of goods
        item_cost = float(item.cost) if item.cost else 0
        cost_of_goods = item_cost * units_sold

        # Calculate profit metrics
        gross_profit = gross_revenue - cost_of_goods
        gross_margin_pct = (gross_profit / gross_revenue * 100) if gross_revenue > 0 else 0

        # Contribution margin (profit per unit)
        contribution_margin = (float(item.price) - item_cost) if item.price else 0

        # Generate recommendation
        if units_sold == 0:
            recommendation = "No sales in period - consider promotion or removal"
        elif gross_margin_pct < 30:
            recommendation = "Low margin - review pricing or ingredient costs"
        elif gross_margin_pct > 70 and units_sold < 10:
            recommendation = "High margin but low volume - promote this item"
        elif gross_margin_pct > 60:
            recommendation = "Strong performer - maintain current strategy"
        else:
            recommendation = "Average performance - monitor trends"

        return {
            "menu_item_id": menu_item_id,
            "item_name": item.name,
            "period": {"start": str(start_date), "end": str(end_date)},
            "units_sold": units_sold,
            "unit_price": float(item.price) if item.price else 0,
            "unit_cost": item_cost,
            "gross_revenue": round(gross_revenue, 2),
            "cost_of_goods": round(cost_of_goods, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin_percentage": round(gross_margin_pct, 1),
            "contribution_margin": round(contribution_margin, 2),
            "recommendation": recommendation
        }

    @staticmethod
    def get_profit_leaderboard(
        db: Session,
        venue_id: int,
        start_date: date,
        end_date: date,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get top and bottom performing items by profitability."""
        from app.models import MenuItem, Order, OrderItem

        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Get all menu items with their sales and calculate profitability
        items = db.query(MenuItem).filter(
            MenuItem.venue_id == venue_id,
            MenuItem.is_active == True
        ).all()

        item_profits = []
        for item in items:
            # Get sales data
            sales_data = db.query(
                func.sum(OrderItem.quantity).label('total_qty'),
                func.sum(OrderItem.price * OrderItem.quantity).label('total_revenue')
            ).join(Order).filter(
                OrderItem.menu_item_id == item.id,
                Order.venue_id == venue_id,
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status != 'cancelled'
            ).first()

            units_sold = int(sales_data.total_qty or 0)
            gross_revenue = float(sales_data.total_revenue or 0)
            item_cost = float(item.cost) if item.cost else 0
            cost_of_goods = item_cost * units_sold
            gross_profit = gross_revenue - cost_of_goods
            margin_pct = (gross_profit / gross_revenue * 100) if gross_revenue > 0 else 0

            if units_sold > 0:  # Only include items with sales
                item_profits.append({
                    "menu_item_id": item.id,
                    "item_name": item.name,
                    "units_sold": units_sold,
                    "gross_revenue": round(gross_revenue, 2),
                    "gross_profit": round(gross_profit, 2),
                    "margin_percentage": round(margin_pct, 1)
                })

        # Sort by gross profit
        item_profits.sort(key=lambda x: x["gross_profit"], reverse=True)

        # Get top and bottom performers
        top_performers = item_profits[:limit]
        bottom_performers = list(reversed(item_profits[-limit:])) if len(item_profits) > limit else []

        # Generate recommendations
        recommendations = []
        if top_performers:
            top_item = top_performers[0]
            recommendations.append(f"Top performer: {top_item['item_name']} with ${top_item['gross_profit']:.2f} profit")

        low_margin_items = [p for p in item_profits if p["margin_percentage"] < 30]
        if low_margin_items:
            recommendations.append(f"{len(low_margin_items)} items have margins below 30% - review pricing")

        high_margin_low_volume = [p for p in item_profits if p["margin_percentage"] > 60 and p["units_sold"] < 5]
        if high_margin_low_volume:
            recommendations.append(f"{len(high_margin_low_volume)} high-margin items have low sales - consider promotions")

        return {
            "venue_id": venue_id,
            "period": {"start": str(start_date), "end": str(end_date)},
            "items_analyzed": len(item_profits),
            "total_profit": round(sum(p["gross_profit"] for p in item_profits), 2),
            "top_performers": top_performers,
            "bottom_performers": bottom_performers,
            "recommendations": recommendations
        }


# Class aliases for backwards compatibility with endpoint imports
PrimeCostService = FinancialControlsService
AbuseDetectionService = FinancialControlsService

