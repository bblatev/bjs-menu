"""Shelf Life & Expiration Tracking Service."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import ProductShelfLife, InventoryBatch, ExpirationAlert


class ShelfLifeService:
    """Service for shelf life and expiration tracking."""

    def __init__(self, db: Session):
        self.db = db

    def create_shelf_life_config(
        self,
        product_id: int,
        shelf_life_days: int,
        use_by_type: str = "use_by",
        storage_temp_min: Optional[float] = None,
        storage_temp_max: Optional[float] = None,
        requires_refrigeration: bool = False,
        alert_days_before: int = 3,
        markdown_days_before: Optional[int] = None,
        markdown_percent: Optional[float] = None,
    ) -> ProductShelfLife:
        """Create shelf life configuration for a product."""
        config = ProductShelfLife(
            product_id=product_id,
            shelf_life_days=shelf_life_days,
            use_by_type=use_by_type,
            storage_temp_min=storage_temp_min,
            storage_temp_max=storage_temp_max,
            requires_refrigeration=requires_refrigeration,
            alert_days_before=alert_days_before,
            markdown_days_before=markdown_days_before,
            markdown_percent=markdown_percent,
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def get_shelf_life_config(
        self,
        product_id: int,
    ) -> Optional[ProductShelfLife]:
        """Get shelf life configuration for a product."""
        query = select(ProductShelfLife).where(ProductShelfLife.product_id == product_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def create_batch(
        self,
        product_id: int,
        location_id: int,
        batch_number: str,
        received_quantity: Decimal,
        received_date: date,
        expiration_date: date,
        unit_cost: Decimal,
        lot_number: Optional[str] = None,
        production_date: Optional[date] = None,
        current_quantity: Optional[Decimal] = None,
    ) -> InventoryBatch:
        """Create a new inventory batch."""
        batch = InventoryBatch(
            product_id=product_id,
            location_id=location_id,
            batch_number=batch_number,
            lot_number=lot_number,
            received_quantity=received_quantity,
            current_quantity=current_quantity if current_quantity is not None else received_quantity,
            received_date=received_date,
            production_date=production_date,
            expiration_date=expiration_date,
            unit_cost=unit_cost,
            is_expired=expiration_date < date.today(),
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)

        # Generate alerts if needed
        self._check_and_create_alerts(batch)

        return batch

    def _check_and_create_alerts(
        self,
        batch: InventoryBatch,
    ) -> None:
        """Check if alerts are needed for a batch."""
        config = self.get_shelf_life_config(batch.product_id)
        if not config:
            return

        days_until_expiry = (batch.expiration_date - date.today()).days

        if days_until_expiry <= 0:
            self._create_alert(batch, "expired", days_until_expiry)
        elif days_until_expiry <= config.alert_days_before:
            self._create_alert(batch, "approaching_expiry", days_until_expiry)

        if config.markdown_days_before and days_until_expiry <= config.markdown_days_before:
            self._create_alert(batch, "markdown_required", days_until_expiry)

    def _create_alert(
        self,
        batch: InventoryBatch,
        alert_type: str,
        days_until_expiry: int,
    ) -> ExpirationAlert:
        """Create an expiration alert."""
        value_at_risk = batch.current_quantity * batch.unit_cost

        alert = ExpirationAlert(
            batch_id=batch.id,
            location_id=batch.location_id,
            alert_type=alert_type,
            days_until_expiry=days_until_expiry,
            quantity_affected=batch.current_quantity,
            value_at_risk=value_at_risk,
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def get_batches(
        self,
        location_id: int,
        product_id: Optional[int] = None,
        include_expired: bool = False,
        include_empty: bool = False,
    ) -> List[InventoryBatch]:
        """Get inventory batches for a location."""
        query = select(InventoryBatch).where(
            InventoryBatch.location_id == location_id
        )

        if product_id:
            query = query.where(InventoryBatch.product_id == product_id)

        if not include_expired:
            query = query.where(InventoryBatch.is_expired == False)

        if not include_empty:
            query = query.where(InventoryBatch.current_quantity > 0)

        query = query.order_by(InventoryBatch.expiration_date)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_expiring_soon(
        self,
        location_id: int,
        days: int = 7,
    ) -> List[InventoryBatch]:
        """Get batches expiring within specified days."""
        cutoff_date = date.today() + timedelta(days=days)

        query = select(InventoryBatch).where(
            and_(
                InventoryBatch.location_id == location_id,
                InventoryBatch.expiration_date <= cutoff_date,
                InventoryBatch.expiration_date >= date.today(),
                InventoryBatch.current_quantity > 0,
                InventoryBatch.is_expired == False,
            )
        ).order_by(InventoryBatch.expiration_date)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_expiration_summary(
        self,
        location_id: int,
    ) -> Dict[str, Any]:
        """Get expiration summary for a location."""
        today = date.today()

        # Expiring today
        today_query = select(func.count(InventoryBatch.id)).where(
            and_(
                InventoryBatch.location_id == location_id,
                InventoryBatch.expiration_date == today,
                InventoryBatch.current_quantity > 0,
            )
        )
        today_result = self.db.execute(today_query)
        expiring_today = today_result.scalar() or 0

        # Expiring in 3 days
        three_days = today + timedelta(days=3)
        three_query = select(func.count(InventoryBatch.id)).where(
            and_(
                InventoryBatch.location_id == location_id,
                InventoryBatch.expiration_date <= three_days,
                InventoryBatch.expiration_date >= today,
                InventoryBatch.current_quantity > 0,
            )
        )
        three_result = self.db.execute(three_query)
        expiring_3_days = three_result.scalar() or 0

        # Expiring in 7 days
        seven_days = today + timedelta(days=7)
        seven_query = select(func.count(InventoryBatch.id)).where(
            and_(
                InventoryBatch.location_id == location_id,
                InventoryBatch.expiration_date <= seven_days,
                InventoryBatch.expiration_date >= today,
                InventoryBatch.current_quantity > 0,
            )
        )
        seven_result = self.db.execute(seven_query)
        expiring_7_days = seven_result.scalar() or 0

        # Total value at risk (within 7 days)
        value_query = select(
            func.sum(InventoryBatch.current_quantity * InventoryBatch.unit_cost)
        ).where(
            and_(
                InventoryBatch.location_id == location_id,
                InventoryBatch.expiration_date <= seven_days,
                InventoryBatch.expiration_date >= today,
                InventoryBatch.current_quantity > 0,
            )
        )
        value_result = self.db.execute(value_query)
        total_value_at_risk = value_result.scalar() or Decimal("0")

        # Get batches requiring action
        batches = self.get_expiring_soon(location_id, days=3)

        return {
            "expiring_today": expiring_today,
            "expiring_3_days": expiring_3_days,
            "expiring_7_days": expiring_7_days,
            "total_value_at_risk": float(total_value_at_risk),
            "batches_requiring_action": batches,
        }

    def deduct_from_batch(
        self,
        batch_id: int,
        quantity: Decimal,
    ) -> InventoryBatch:
        """Deduct quantity from a batch (FIFO)."""
        batch = self.db.get(InventoryBatch, batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        if quantity > batch.current_quantity:
            raise ValueError(f"Insufficient quantity. Available: {batch.current_quantity}")

        batch.current_quantity -= quantity
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def record_action(
        self,
        alert_id: int,
        action_taken: str,
        action_by_id: int,
    ) -> ExpirationAlert:
        """Record action taken on an expiration alert."""
        alert = self.db.get(ExpirationAlert, alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.action_taken = action_taken
        alert.action_date = datetime.utcnow()
        alert.action_by_id = action_by_id
        alert.acknowledged = True

        self.db.commit()
        self.db.refresh(alert)
        return alert

    def quarantine_batch(
        self,
        batch_id: int,
        reason: str,
    ) -> InventoryBatch:
        """Quarantine a batch."""
        batch = self.db.get(InventoryBatch, batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        batch.is_quarantined = True
        batch.quarantine_reason = reason

        self.db.commit()
        self.db.refresh(batch)
        return batch

    def get_alerts(
        self,
        location_id: int,
        acknowledged: Optional[bool] = None,
        alert_type: Optional[str] = None,
    ) -> List[ExpirationAlert]:
        """Get expiration alerts."""
        query = select(ExpirationAlert).where(
            ExpirationAlert.location_id == location_id
        )

        if acknowledged is not None:
            query = query.where(ExpirationAlert.acknowledged == acknowledged)
        if alert_type:
            query = query.where(ExpirationAlert.alert_type == alert_type)

        query = query.order_by(ExpirationAlert.created_at.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())
