"""Stock Alert Service - Unified alert logic for low stock, out of stock, and expiring items.

Consolidates the duplicated alert generation logic that was previously in both:
- app/api/routes/stock.py (GET /alerts/)
- app/api/routes/stock_management.py (GET /alerts)

Usage:
    from app.services.stock_alert_service import StockAlertService

    result = StockAlertService.get_alerts(db, location_id=1)
"""

import logging
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.models.stock import StockOnHand
from app.models.product import Product

logger = logging.getLogger(__name__)


class StockAlertService:
    """Generates stock alerts: out-of-stock, low stock, below minimum, and expiring soon."""

    @staticmethod
    def get_alerts(
        db: Session,
        location_id: Optional[int] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Query StockOnHand joined with Product and generate stock alerts.

        Args:
            db: SQLAlchemy database session.
            location_id: Filter by location. If None, alerts for all locations.
            severity: Filter by severity level (critical, warning, info). If None, return all.
            limit: Maximum number of alerts to return.

        Returns:
            Dict with keys: alerts, total, critical, warnings.
        """
        alerts: List[Dict[str, Any]] = []

        # Build stock query, optionally filtered by location
        stock_query = db.query(StockOnHand)
        if location_id is not None:
            stock_query = stock_query.filter(StockOnHand.location_id == location_id)

        stock_items = stock_query.all()

        for s in stock_items:
            product = db.query(Product).filter(Product.id == s.product_id).first()
            if not product:
                continue

            if s.qty <= 0:
                alerts.append({
                    "type": "out_of_stock",
                    "severity": "critical",
                    "product_id": product.id,
                    "product_name": product.name,
                    "current_qty": float(s.qty),
                    "par_level": float(product.par_level) if product.par_level else None,
                    "unit": product.unit,
                    "message": f"{product.name} is out of stock",
                })
            elif product.par_level and s.qty < product.par_level:
                alerts.append({
                    "type": "low_stock",
                    "severity": "warning",
                    "product_id": product.id,
                    "product_name": product.name,
                    "current_qty": float(s.qty),
                    "par_level": float(product.par_level),
                    "unit": product.unit,
                    "message": f"{product.name} is below par level ({s.qty}/{product.par_level} {product.unit})",
                })
            elif product.min_stock and s.qty < product.min_stock:
                alerts.append({
                    "type": "below_minimum",
                    "severity": "warning",
                    "product_id": product.id,
                    "product_name": product.name,
                    "current_qty": float(s.qty),
                    "min_stock": float(product.min_stock),
                    "unit": product.unit,
                    "message": f"{product.name} is below minimum stock",
                })

        # Expiring soon alerts (batch tracking, optional dependency)
        try:
            from app.models.advanced_features import InventoryBatch

            batch_query = db.query(InventoryBatch).filter(
                InventoryBatch.is_expired == False,
                InventoryBatch.current_quantity > 0,
                InventoryBatch.expiration_date <= date.today() + timedelta(days=7),
            )
            if location_id is not None:
                batch_query = batch_query.filter(InventoryBatch.location_id == location_id)

            expiring = batch_query.all()

            for batch in expiring:
                product = db.query(Product).filter(Product.id == batch.product_id).first()
                days_left = (batch.expiration_date - date.today()).days if batch.expiration_date else None
                alerts.append({
                    "type": "expiring_soon" if days_left and days_left > 0 else "expired",
                    "severity": "critical" if days_left and days_left <= 0 else "warning",
                    "product_id": batch.product_id,
                    "product_name": product.name if product else f"Product {batch.product_id}",
                    "batch_number": batch.batch_number,
                    "expiration_date": batch.expiration_date.isoformat() if batch.expiration_date else None,
                    "days_remaining": days_left,
                    "quantity": float(batch.current_quantity),
                    "message": f"Batch {batch.batch_number} expires in {days_left} days" if days_left and days_left > 0 else f"Batch {batch.batch_number} has expired",
                })
        except Exception as e:
            logger.debug(f"Optional: query expiring batch alerts: {e}")

        # Filter by severity if requested
        if severity is not None:
            alerts = [a for a in alerts if a["severity"] == severity]

        # Sort by severity (critical first, then warning, then info)
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda x: severity_order.get(x["severity"], 99))

        # Apply limit
        alerts = alerts[:limit]

        return {
            "alerts": alerts,
            "total": len(alerts),
            "critical": len([a for a in alerts if a["severity"] == "critical"]),
            "warnings": len([a for a in alerts if a["severity"] == "warning"]),
        }
