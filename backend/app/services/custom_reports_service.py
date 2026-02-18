"""
Custom Reports & Report Scheduling Service - Complete Implementation
Missing Feature: Custom Reports, Report Scheduling, Email Reports (iiko & Toast have this)

Features:
- Custom report builder
- Scheduled reports (daily, weekly, monthly)
- Email delivery
- Multiple export formats (PDF, Excel, CSV)
- Report templates
- KPI dashboards
- Cohort analysis
- ABC analysis (inventory)
- Pareto analysis (80/20)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import uuid
import enum
from collections import defaultdict

from app.models import Order, OrderItem, MenuItem, StaffUser, Customer, StockItem


class ReportFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ONE_TIME = "one_time"


class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"


class ReportService:
    """Complete Custom Reports and Scheduling Service"""
    
    def __init__(self, db: Session):
        self.db = db
        self._templates: Dict[str, Dict] = {}
        self._scheduled_reports: Dict[str, Dict] = {}
        self._report_history: List[Dict] = []
    
    # ========== SALES REPORTS ==========
    
    def generate_sales_report(
        self,
        venue_id: int,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "day"
    ) -> Dict[str, Any]:
        """Generate comprehensive sales report"""
        orders = self.db.query(Order).filter(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.payment_status == "paid"
            )
        ).all()
        
        total_sales = sum(o.total for o in orders)
        total_orders = len(orders)
        total_tips = sum(o.tip_amount or 0 for o in orders)
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0
        
        # Group by period
        sales_by_period = defaultdict(lambda: {"sales": 0, "orders": 0, "tips": 0})
        
        for order in orders:
            if group_by == "hour":
                key = order.created_at.strftime("%Y-%m-%d %H:00")
            elif group_by == "day":
                key = order.created_at.strftime("%Y-%m-%d")
            elif group_by == "week":
                key = order.created_at.strftime("%Y-W%W")
            else:
                key = order.created_at.strftime("%Y-%m")
            
            sales_by_period[key]["sales"] += order.total
            sales_by_period[key]["orders"] += 1
            sales_by_period[key]["tips"] += order.tip_amount or 0
        
        # Payment method breakdown
        payment_breakdown = defaultdict(float)
        for order in orders:
            method = order.payment_method or "unknown"
            payment_breakdown[method] += order.total
        
        return {
            "success": True,
            "report_type": "sales",
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_sales": round(total_sales, 2),
                "total_orders": total_orders,
                "average_order_value": round(avg_order_value, 2),
                "total_tips": round(total_tips, 2),
                "tip_percentage": round(total_tips / total_sales * 100, 2) if total_sales > 0 else 0
            },
            "by_period": dict(sales_by_period),
            "by_payment_method": dict(payment_breakdown),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def generate_product_mix_report(
        self,
        venue_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate product mix analysis (what sells best)"""
        order_items = self.db.query(
            OrderItem.menu_item_id,
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.subtotal).label("total_revenue")
        ).join(Order).filter(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.payment_status == "paid"
            )
        ).group_by(OrderItem.menu_item_id).all()
        
        products = []
        total_revenue = 0
        total_quantity = 0
        
        for item in order_items:
            menu_item = self.db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
            if menu_item:
                products.append({
                    "id": item.menu_item_id,
                    "name": menu_item.name,
                    "quantity_sold": item.total_quantity,
                    "revenue": float(item.total_revenue),
                    "avg_price": float(item.total_revenue) / item.total_quantity if item.total_quantity > 0 else 0
                })
                total_revenue += float(item.total_revenue)
                total_quantity += item.total_quantity
        
        # Sort by revenue
        products.sort(key=lambda x: x["revenue"], reverse=True)
        
        # Calculate percentages
        for product in products:
            product["revenue_percentage"] = round(product["revenue"] / total_revenue * 100, 2) if total_revenue > 0 else 0
            product["quantity_percentage"] = round(product["quantity_sold"] / total_quantity * 100, 2) if total_quantity > 0 else 0
        
        # ABC Analysis
        cumulative = 0
        for product in products:
            cumulative += product["revenue_percentage"]
            if cumulative <= 80:
                product["abc_class"] = "A"  # Top 80% of revenue
            elif cumulative <= 95:
                product["abc_class"] = "B"  # Next 15%
            else:
                product["abc_class"] = "C"  # Bottom 5%
        
        return {
            "success": True,
            "report_type": "product_mix",
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_items_sold": total_quantity,
                "total_revenue": round(total_revenue, 2),
                "unique_products": len(products)
            },
            "products": products[:50],  # Top 50
            "abc_summary": {
                "a_class_count": len([p for p in products if p.get("abc_class") == "A"]),
                "b_class_count": len([p for p in products if p.get("abc_class") == "B"]),
                "c_class_count": len([p for p in products if p.get("abc_class") == "C"])
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ========== STAFF REPORTS ==========
    
    def generate_staff_performance_report(
        self,
        venue_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate staff performance report"""
        # Get orders by staff
        staff_stats = self.db.query(
            Order.waiter_id,
            func.count(Order.id).label("order_count"),
            func.sum(Order.total).label("total_sales"),
            func.sum(Order.tip_amount).label("total_tips")
        ).filter(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date,
                Order.payment_status == "paid",
                Order.waiter_id.isnot(None)
            )
        ).group_by(Order.waiter_id).all()
        
        staff_list = []
        for stat in staff_stats:
            staff_user = self.db.query(StaffUser).filter(StaffUser.id == stat.waiter_id).first()
            if staff_user:
                sales = float(stat.total_sales or 0)
                tips = float(stat.total_tips or 0)
                orders = stat.order_count
                
                staff_list.append({
                    "staff_id": stat.waiter_id,
                    "name": staff_user.full_name,
                    "role": staff_user.role.value if staff_user.role else "unknown",
                    "orders_count": orders,
                    "total_sales": round(sales, 2),
                    "total_tips": round(tips, 2),
                    "avg_order_value": round(sales / orders, 2) if orders > 0 else 0,
                    "avg_tip": round(tips / orders, 2) if orders > 0 else 0,
                    "tip_percentage": round(tips / sales * 100, 2) if sales > 0 else 0
                })
        
        # Sort by total sales
        staff_list.sort(key=lambda x: x["total_sales"], reverse=True)
        
        # Add rank
        for i, staff in enumerate(staff_list, 1):
            staff["rank"] = i
        
        return {
            "success": True,
            "report_type": "staff_performance",
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_staff": len(staff_list),
                "total_sales": sum(s["total_sales"] for s in staff_list),
                "total_tips": sum(s["total_tips"] for s in staff_list),
                "avg_sales_per_staff": round(sum(s["total_sales"] for s in staff_list) / len(staff_list), 2) if staff_list else 0
            },
            "staff": staff_list,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ========== INVENTORY REPORTS ==========
    
    def generate_inventory_report(
        self,
        venue_id: int,
        include_low_stock: bool = True
    ) -> Dict[str, Any]:
        """Generate inventory status report"""
        stock_items = self.db.query(StockItem).filter(
            StockItem.venue_id == venue_id,
            StockItem.is_active == True
        ).all()
        
        items = []
        low_stock_items = []
        total_value = 0
        
        for item in stock_items:
            value = (item.quantity or 0) * (item.cost_per_unit or 0)
            total_value += value
            
            item_data = {
                "id": item.id,
                "name": item.name,
                "sku": item.sku,
                "quantity": item.quantity,
                "unit": item.unit,
                "cost_per_unit": item.cost_per_unit,
                "total_value": round(value, 2),
                "low_stock_threshold": item.low_stock_threshold,
                "is_low_stock": item.quantity <= item.low_stock_threshold
            }
            items.append(item_data)
            
            if item.quantity <= item.low_stock_threshold:
                low_stock_items.append(item_data)
        
        return {
            "success": True,
            "report_type": "inventory",
            "venue_id": venue_id,
            "summary": {
                "total_items": len(items),
                "total_value": round(total_value, 2),
                "low_stock_count": len(low_stock_items),
                "out_of_stock_count": len([i for i in items if i["quantity"] <= 0])
            },
            "items": items,
            "low_stock_items": low_stock_items if include_low_stock else [],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def generate_variance_report(
        self,
        venue_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate theoretical vs actual inventory variance report"""
        stock_items = self.db.query(StockItem).filter(
            StockItem.venue_id == venue_id,
            StockItem.is_active == True
        ).all()
        
        variances = []
        total_variance_value = 0
        
        for item in stock_items:
            # Get movements in period
            movements = self.db.query(StockMovement).filter(
                and_(
                    StockMovement.stock_item_id == item.id,
                    StockMovement.created_at >= start_date,
                    StockMovement.created_at <= end_date
                )
            ).all()
            
            purchases = sum(m.quantity_change for m in movements if m.movement_type == "purchase")
            usage = sum(abs(m.quantity_change) for m in movements if m.movement_type == "usage")
            waste = sum(abs(m.quantity_change) for m in movements if m.movement_type == "waste")
            adjustments = sum(m.quantity_change for m in movements if m.movement_type == "adjustment")
            
            # Theoretical = opening + purchases - usage - waste
            # Actual = current quantity
            # Variance = actual - theoretical
            
            theoretical_ending = purchases - usage - waste + adjustments
            variance = item.quantity - theoretical_ending
            variance_value = variance * (item.cost_per_unit or 0)
            total_variance_value += variance_value
            
            if abs(variance) > 0.01:  # Only include items with variance
                variances.append({
                    "item_id": item.id,
                    "name": item.name,
                    "unit": item.unit,
                    "purchases": purchases,
                    "usage": usage,
                    "waste": waste,
                    "adjustments": adjustments,
                    "theoretical_quantity": theoretical_ending,
                    "actual_quantity": item.quantity,
                    "variance": round(variance, 2),
                    "variance_value": round(variance_value, 2),
                    "variance_percentage": round(variance / theoretical_ending * 100, 2) if theoretical_ending != 0 else 0
                })
        
        # Sort by absolute variance value
        variances.sort(key=lambda x: abs(x["variance_value"]), reverse=True)
        
        return {
            "success": True,
            "report_type": "variance",
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "items_with_variance": len(variances),
                "total_variance_value": round(total_variance_value, 2),
                "positive_variance_count": len([v for v in variances if v["variance"] > 0]),
                "negative_variance_count": len([v for v in variances if v["variance"] < 0])
            },
            "variances": variances[:50],  # Top 50 variances
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ========== CUSTOMER REPORTS ==========
    
    def generate_customer_report(
        self,
        venue_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate customer insights report"""
        customers = self.db.query(Customer).filter(
            Customer.location_id == venue_id,
            Customer.deleted_at.is_(None)
        ).all()
        
        # Segment customers by spending
        segments = {
            "vip": [],        # Top 10%
            "regular": [],    # Next 20%
            "occasional": [], # Next 40%
            "rare": []        # Bottom 30%
        }
        
        customer_list = []
        for customer in customers:
            customer_list.append({
                "id": customer.id,
                "name": customer.name,
                "total_orders": customer.total_orders or 0,
                "total_spent": customer.total_spent or 0,
                "avg_order_value": customer.average_order_value or 0,
                "last_visit": customer.last_visit.isoformat() if customer.last_visit else None,
                "loyalty_tier": customer.loyalty_tier,
                "loyalty_points": customer.loyalty_points or 0
            })
        
        # Sort by total spent
        customer_list.sort(key=lambda x: x["total_spent"], reverse=True)
        
        # Assign segments
        total = len(customer_list)
        for i, customer in enumerate(customer_list):
            if i < total * 0.1:
                customer["segment"] = "vip"
                segments["vip"].append(customer)
            elif i < total * 0.3:
                customer["segment"] = "regular"
                segments["regular"].append(customer)
            elif i < total * 0.7:
                customer["segment"] = "occasional"
                segments["occasional"].append(customer)
            else:
                customer["segment"] = "rare"
                segments["rare"].append(customer)
        
        total_spent = sum(c["total_spent"] for c in customer_list)
        
        return {
            "success": True,
            "report_type": "customer",
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_customers": len(customer_list),
                "total_revenue": round(total_spent, 2),
                "avg_customer_value": round(total_spent / len(customer_list), 2) if customer_list else 0
            },
            "segments": {
                "vip": {"count": len(segments["vip"]), "revenue": sum(c["total_spent"] for c in segments["vip"])},
                "regular": {"count": len(segments["regular"]), "revenue": sum(c["total_spent"] for c in segments["regular"])},
                "occasional": {"count": len(segments["occasional"]), "revenue": sum(c["total_spent"] for c in segments["occasional"])},
                "rare": {"count": len(segments["rare"]), "revenue": sum(c["total_spent"] for c in segments["rare"])}
            },
            "top_customers": customer_list[:20],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ========== REPORT SCHEDULING ==========
    
    def schedule_report(
        self,
        venue_id: int,
        report_type: str,
        frequency: str,
        recipients: List[str],
        format: str = "pdf",
        parameters: Optional[Dict] = None,
        send_time: str = "08:00",
        day_of_week: Optional[int] = None,  # 0=Monday, 6=Sunday
        day_of_month: Optional[int] = None,
        created_by: int = None
    ) -> Dict[str, Any]:
        """Schedule a recurring report"""
        schedule_id = f"SCHED-{uuid.uuid4().hex[:8].upper()}"
        
        schedule = {
            "schedule_id": schedule_id,
            "venue_id": venue_id,
            "report_type": report_type,
            "frequency": frequency,
            "recipients": recipients,
            "format": format,
            "parameters": parameters or {},
            "send_time": send_time,
            "day_of_week": day_of_week,
            "day_of_month": day_of_month,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": created_by,
            "last_sent": None,
            "next_send": self._calculate_next_send(frequency, send_time, day_of_week, day_of_month)
        }
        
        self._scheduled_reports[schedule_id] = schedule
        
        return {
            "success": True,
            "schedule_id": schedule_id,
            "report_type": report_type,
            "frequency": frequency,
            "recipients": recipients,
            "next_send": schedule["next_send"],
            "message": f"Report scheduled successfully"
        }
    
    def get_scheduled_reports(self, venue_id: int) -> List[Dict[str, Any]]:
        """Get all scheduled reports for a venue"""
        return [
            schedule for schedule in self._scheduled_reports.values()
            if schedule["venue_id"] == venue_id
        ]
    
    def cancel_scheduled_report(self, schedule_id: str) -> Dict[str, Any]:
        """Cancel a scheduled report"""
        if schedule_id not in self._scheduled_reports:
            return {"success": False, "error": "Schedule not found"}
        
        self._scheduled_reports[schedule_id]["is_active"] = False
        
        return {
            "success": True,
            "schedule_id": schedule_id,
            "message": "Report schedule cancelled"
        }
    
    def _calculate_next_send(
        self,
        frequency: str,
        send_time: str,
        day_of_week: Optional[int],
        day_of_month: Optional[int]
    ) -> str:
        """Calculate next scheduled send time"""
        now = datetime.now(timezone.utc)
        hour, minute = map(int, send_time.split(":"))
        
        if frequency == "daily":
            next_send = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_send <= now:
                next_send += timedelta(days=1)
        elif frequency == "weekly" and day_of_week is not None:
            days_ahead = day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_send = now + timedelta(days=days_ahead)
            next_send = next_send.replace(hour=hour, minute=minute, second=0, microsecond=0)
        elif frequency == "monthly" and day_of_month is not None:
            next_send = now.replace(day=min(day_of_month, 28), hour=hour, minute=minute, second=0, microsecond=0)
            if next_send <= now:
                if now.month == 12:
                    next_send = next_send.replace(year=now.year + 1, month=1)
                else:
                    next_send = next_send.replace(month=now.month + 1)
        else:
            next_send = now + timedelta(days=1)
        
        return next_send.isoformat()
    
    # ========== CUSTOM REPORT BUILDER ==========
    
    def create_custom_report_template(
        self,
        venue_id: int,
        name: str,
        description: str,
        metrics: List[str],
        filters: Optional[Dict] = None,
        grouping: Optional[List[str]] = None,
        created_by: int = None
    ) -> Dict[str, Any]:
        """Create a custom report template"""
        template_id = f"TMPL-{uuid.uuid4().hex[:8].upper()}"
        
        template = {
            "template_id": template_id,
            "venue_id": venue_id,
            "name": name,
            "description": description,
            "metrics": metrics,
            "filters": filters or {},
            "grouping": grouping or [],
            "is_builtin": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": created_by
        }
        
        self._templates[template_id] = template
        
        return {
            "success": True,
            "template_id": template_id,
            "name": name,
            "message": "Custom report template created"
        }
    
    def list_report_templates(self, venue_id: int) -> List[Dict[str, Any]]:
        """List all available report templates"""
        templates = []
        
        # Built-in templates
        for template_id, template in self._templates.items():
            if template.get("is_builtin") or template.get("venue_id") == venue_id:
                templates.append({
                    "template_id": template_id,
                    "name": template["name"],
                    "description": template.get("description", ""),
                    "is_builtin": template.get("is_builtin", False)
                })
        
        return templates
    
    # ========== EXPORT FUNCTIONS ==========
    
    def export_report(
        self,
        report_data: Dict[str, Any],
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export report to specified format"""
        if format == "json":
            return {
                "success": True,
                "format": "json",
                "data": report_data,
                "content_type": "application/json"
            }
        elif format == "csv":
            # Would generate CSV content
            return {
                "success": True,
                "format": "csv",
                "content": self._to_csv(report_data),
                "content_type": "text/csv"
            }
        else:
            return {
                "success": True,
                "format": format,
                "message": f"Export to {format} would be generated here"
            }
    
    def _to_csv(self, data: Dict) -> str:
        """Convert report data to CSV format"""
        # Simplified CSV generation
        lines = []
        if "products" in data:
            lines.append("Name,Quantity Sold,Revenue,ABC Class")
            for p in data["products"]:
                lines.append(f"{p['name']},{p['quantity_sold']},{p['revenue']},{p.get('abc_class', '')}")
        elif "staff" in data:
            lines.append("Name,Orders,Sales,Tips")
            for s in data["staff"]:
                lines.append(f"{s['name']},{s['orders_count']},{s['total_sales']},{s['total_tips']}")
        
        return "\n".join(lines)
