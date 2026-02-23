"""Shelf life tracking and expiry management service."""

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session


class ShelfLifeService:
    """Tracks product shelf life, expiry dates, and FIFO recommendations."""

    @staticmethod
    def get_shelf_life_items(db: Session, venue_id: int, status: Optional[str] = None):
        """Get all tracked shelf life items."""
        from app.models.v99_models import ShelfLifeItem

        query = db.query(ShelfLifeItem).filter(ShelfLifeItem.venue_id == venue_id)
        if status:
            query = query.filter(ShelfLifeItem.status == status)

        items = query.order_by(ShelfLifeItem.expiry_date.asc()).all()

        today = date.today()
        results = []
        for item in items:
            days_remaining = (item.expiry_date - today).days
            computed_status = item.status
            if days_remaining < 0:
                computed_status = "expired"
            elif days_remaining <= 1:
                computed_status = "expiring"
            elif days_remaining <= 3:
                computed_status = "use_soon"

            results.append({
                "id": item.id,
                "product_name": item.product_name,
                "product_id": item.product_id,
                "batch_id": item.batch_id,
                "received_date": str(item.received_date),
                "expiry_date": str(item.expiry_date),
                "days_remaining": max(days_remaining, 0),
                "quantity": item.quantity,
                "unit": item.unit,
                "storage_location": item.storage_location,
                "status": computed_status,
            })
        return results

    @staticmethod
    def get_expiring_soon(db: Session, venue_id: int, days: int = 3):
        """Get items expiring within N days."""
        from app.models.v99_models import ShelfLifeItem

        cutoff = date.today() + timedelta(days=days)
        items = db.query(ShelfLifeItem).filter(
            ShelfLifeItem.venue_id == venue_id,
            ShelfLifeItem.expiry_date <= cutoff,
            ShelfLifeItem.status != "discarded",
        ).order_by(ShelfLifeItem.expiry_date.asc()).all()

        return [
            {
                "id": item.id,
                "product_name": item.product_name,
                "expiry_date": str(item.expiry_date),
                "days_remaining": max((item.expiry_date - date.today()).days, 0),
                "quantity": item.quantity,
                "unit": item.unit,
                "storage_location": item.storage_location,
            }
            for item in items
        ]

    @staticmethod
    def add_item(db: Session, venue_id: int, data: dict):
        """Add a new shelf life tracked item."""
        from app.models.v99_models import ShelfLifeItem

        item = ShelfLifeItem(
            venue_id=venue_id,
            product_id=data.get("product_id"),
            product_name=data["product_name"],
            batch_id=data.get("batch_id"),
            received_date=data.get("received_date", date.today()),
            expiry_date=data["expiry_date"],
            quantity=data.get("quantity", 0),
            unit=data.get("unit"),
            storage_location=data.get("storage_location"),
            status="fresh",
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"id": item.id, "product_name": item.product_name, "status": "fresh"}

    @staticmethod
    def discard_item(db: Session, item_id: int, staff_id: int):
        """Mark an item as discarded."""
        from app.models.v99_models import ShelfLifeItem

        item = db.query(ShelfLifeItem).filter(ShelfLifeItem.id == item_id).first()
        if not item:
            return None

        item.status = "discarded"
        item.discarded_at = datetime.now(timezone.utc)
        item.discarded_by = staff_id
        db.commit()
        return {"id": item.id, "status": "discarded"}

    @staticmethod
    def get_waste_prediction(db: Session, venue_id: int):
        """Predict potential waste from expiring items."""
        from app.models.v99_models import ShelfLifeItem

        cutoff = date.today() + timedelta(days=7)
        items = db.query(ShelfLifeItem).filter(
            ShelfLifeItem.venue_id == venue_id,
            ShelfLifeItem.expiry_date <= cutoff,
            ShelfLifeItem.status.in_(["fresh", "use_soon", "expiring"]),
        ).all()

        total_at_risk = len(items)
        categories = {}
        for item in items:
            loc = item.storage_location or "unknown"
            categories.setdefault(loc, 0)
            categories[loc] += 1

        return {
            "items_at_risk": total_at_risk,
            "by_location": categories,
            "recommendation": "Prioritize use of items expiring within 3 days in daily specials",
        }
