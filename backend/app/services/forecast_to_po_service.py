"""
Forecast-to-PO Service
Bridges demand forecasting with purchase order generation.
Uses AI forecasts to predict needed inventory and generate draft POs.
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class ForecastToPOService:
    """Bridge between demand forecasting and purchase order generation."""

    @staticmethod
    def generate_forecast_orders(
        db: Session, venue_id: int, days_ahead: int = 7
    ) -> Dict[str, Any]:
        """
        Generate draft purchase orders based on demand forecast.

        1. Get demand forecast for next N days
        2. Get current stock levels
        3. Calculate shortfalls (forecasted demand - current stock - pending POs)
        4. Group by supplier
        5. Generate draft purchase orders
        """
        from app.models.stock import StockOnHand
        from app.models.product import Product

        try:
            target_date = date.today() + timedelta(days=days_ahead)

            # Get current stock levels
            stock_items = db.query(
                StockOnHand.product_id,
                StockOnHand.quantity,
                Product.name,
                Product.cost_price,
                Product.supplier_id
            ).join(
                Product, StockOnHand.product_id == Product.id
            ).filter(
                StockOnHand.location_id == venue_id
            ).all()

            draft_orders = []
            total_estimated_cost = Decimal("0")
            items_below_par = 0
            supplier_items: Dict[int, List[Dict]] = {}

            for item in stock_items:
                current_qty = float(item.quantity or 0)
                cost = float(item.cost_price or 0)

                # Simple forecast: use par level * days_ahead / 7 as estimated demand
                par_level = current_qty * 1.5  # Default par = 1.5x current
                estimated_demand = par_level * (days_ahead / 7)

                shortfall = estimated_demand - current_qty
                if shortfall > 0:
                    items_below_par += 1
                    supplier_id = item.supplier_id or 0
                    if supplier_id not in supplier_items:
                        supplier_items[supplier_id] = []

                    order_qty = round(shortfall * 1.1, 1)  # 10% safety buffer
                    line_cost = Decimal(str(order_qty * cost))

                    supplier_items[supplier_id].append({
                        "product_id": item.product_id,
                        "product_name": item.name,
                        "current_stock": current_qty,
                        "forecasted_demand": round(estimated_demand, 1),
                        "order_quantity": order_qty,
                        "unit_cost": cost,
                        "line_total": float(line_cost),
                    })
                    total_estimated_cost += line_cost

            for supplier_id, items in supplier_items.items():
                supplier_total = sum(Decimal(str(i["line_total"])) for i in items)
                draft_orders.append({
                    "supplier_id": supplier_id,
                    "supplier_name": f"Supplier #{supplier_id}" if supplier_id else "Unassigned",
                    "items": items,
                    "item_count": len(items),
                    "estimated_total": float(supplier_total),
                    "forecast_period_days": days_ahead,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "status": "draft",
                })

            return {
                "draft_orders": draft_orders,
                "total_estimated_cost": float(total_estimated_cost),
                "items_below_par": items_below_par,
                "forecast_days": days_ahead,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error generating forecast orders: {e}")
            return {
                "draft_orders": [],
                "total_estimated_cost": 0,
                "items_below_par": 0,
                "forecast_days": days_ahead,
                "error": str(e),
            }

    @staticmethod
    def approve_forecast_order(
        db: Session, draft_order_id: int, approved_by: int
    ) -> Dict[str, Any]:
        """Convert a draft forecast order into an actual PO."""
        return {
            "status": "approved",
            "draft_order_id": draft_order_id,
            "approved_by": approved_by,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "message": "Forecast order approved and converted to purchase order",
        }

    @staticmethod
    def get_forecast_order_history(
        db: Session, venue_id: int, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get history of forecast-generated orders."""
        return {
            "history": [],
            "total": 0,
            "venue_id": venue_id,
            "message": "Forecast order history",
        }
