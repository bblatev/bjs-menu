"""Auto Prep List Generation Service."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import PrepList, PrepListItem


class PrepListService:
    """Service for auto-generating prep lists."""

    def __init__(self, db: Session):
        self.db = db

    def create_prep_list(
        self,
        location_id: int,
        prep_date: date,
        generated_from: str = "manual",
        station: Optional[str] = None,
        forecast_covers: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
    ) -> PrepList:
        """Create a new prep list."""
        prep_list = PrepList(
            location_id=location_id,
            prep_date=prep_date,
            station=station,
            generated_from=generated_from,
            forecast_covers=forecast_covers,
            status="pending",
            assigned_to_id=assigned_to_id,
        )
        self.db.add(prep_list)
        self.db.commit()
        self.db.refresh(prep_list)
        return prep_list

    def add_item(
        self,
        prep_list_id: int,
        product_id: int,
        required_quantity: Decimal,
        unit: str,
        current_stock: Decimal,
        notes: Optional[str] = None,
        priority: int = 1,
    ) -> PrepListItem:
        """Add an item to a prep list."""
        to_prep = max(Decimal("0"), required_quantity - current_stock)

        item = PrepListItem(
            prep_list_id=prep_list_id,
            product_id=product_id,
            required_quantity=required_quantity,
            unit=unit,
            current_stock=current_stock,
            to_prep_quantity=to_prep,
            notes=notes,
            priority=priority,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def generate_from_forecast(
        self,
        location_id: int,
        prep_date: date,
        forecast_covers: int,
        station: Optional[str] = None,
        par_levels: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate a prep list based on forecasted covers."""
        # Create the prep list
        prep_list = self.create_prep_list(
            location_id=location_id,
            prep_date=prep_date,
            generated_from="forecast",
            station=station,
            forecast_covers=forecast_covers,
        )

        # If no par levels provided, use defaults
        if not par_levels:
            # Default par levels based on typical prep items
            par_levels = {
                1: {"name": "Prep Item 1", "per_cover": Decimal("0.5"), "unit": "oz", "current": Decimal("50")},
                2: {"name": "Prep Item 2", "per_cover": Decimal("0.25"), "unit": "each", "current": Decimal("100")},
                3: {"name": "Prep Item 3", "per_cover": Decimal("1.0"), "unit": "oz", "current": Decimal("200")},
            }

        items = []
        warnings = []

        for product_id, data in par_levels.items():
            # Calculate required quantity based on covers
            per_cover = data.get("per_cover", Decimal("0.5"))
            required = per_cover * forecast_covers
            current = data.get("current", Decimal("0"))

            # Add buffer (20%)
            required_with_buffer = required * Decimal("1.2")

            if required_with_buffer > current:
                item = self.add_item(
                    prep_list_id=prep_list.id,
                    product_id=product_id,
                    required_quantity=required_with_buffer,
                    unit=data.get("unit", "each"),
                    current_stock=current,
                    priority=1 if required_with_buffer / current > 2 else 2 if current else 3,
                )
                items.append(item)

            # Check for critical shortages
            if current < required * Decimal("0.5"):
                warnings.append(f"Critical shortage: Product {product_id} needs immediate prep")

        return {
            "prep_list": prep_list,
            "items": items,
            "warnings": warnings,
        }

    def generate_from_par_level(
        self,
        location_id: int,
        prep_date: date,
        station: Optional[str] = None,
        current_levels: Dict[int, Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate prep list based on par levels vs current stock."""
        prep_list = self.create_prep_list(
            location_id=location_id,
            prep_date=prep_date,
            generated_from="par_level",
            station=station,
        )

        items = []
        warnings = []

        if not current_levels:
            current_levels = {}

        for product_id, data in current_levels.items():
            par_level = data.get("par_level", Decimal("100"))
            current = data.get("current", Decimal("0"))
            unit = data.get("unit", "each")

            if current < par_level:
                item = self.add_item(
                    prep_list_id=prep_list.id,
                    product_id=product_id,
                    required_quantity=par_level,
                    unit=unit,
                    current_stock=current,
                    priority=1 if current == 0 else 2 if current < par_level * Decimal("0.3") else 3,
                )
                items.append(item)

        return {
            "prep_list": prep_list,
            "items": items,
            "warnings": warnings,
        }

    def get_prep_lists(
        self,
        location_id: int,
        prep_date: Optional[date] = None,
        status: Optional[str] = None,
        station: Optional[str] = None,
    ) -> List[PrepList]:
        """Get prep lists with filters."""
        query = select(PrepList).where(PrepList.location_id == location_id)

        if prep_date:
            query = query.where(PrepList.prep_date == prep_date)
        if status:
            query = query.where(PrepList.status == status)
        if station:
            query = query.where(PrepList.station == station)

        query = query.order_by(PrepList.prep_date.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_prep_list_items(
        self,
        prep_list_id: int,
    ) -> List[PrepListItem]:
        """Get items for a prep list."""
        query = select(PrepListItem).where(
            PrepListItem.prep_list_id == prep_list_id
        ).order_by(PrepListItem.priority, PrepListItem.id)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def start_prep_list(
        self,
        prep_list_id: int,
    ) -> PrepList:
        """Mark a prep list as in progress."""
        prep_list = self.db.get(PrepList, prep_list_id)
        if not prep_list:
            raise ValueError(f"Prep list {prep_list_id} not found")

        prep_list.status = "in_progress"
        prep_list.started_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(prep_list)
        return prep_list

    def complete_item(
        self,
        item_id: int,
        actual_prepped: Decimal,
    ) -> PrepListItem:
        """Mark an item as completed."""
        item = self.db.get(PrepListItem, item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        item.actual_prepped = actual_prepped
        item.completed = True
        item.completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(item)
        return item

    def complete_prep_list(
        self,
        prep_list_id: int,
    ) -> PrepList:
        """Mark a prep list as completed."""
        prep_list = self.db.get(PrepList, prep_list_id)
        if not prep_list:
            raise ValueError(f"Prep list {prep_list_id} not found")

        prep_list.status = "completed"
        prep_list.completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(prep_list)
        return prep_list

    def assign_prep_list(
        self,
        prep_list_id: int,
        assigned_to_id: int,
    ) -> PrepList:
        """Assign a prep list to an employee."""
        prep_list = self.db.get(PrepList, prep_list_id)
        if not prep_list:
            raise ValueError(f"Prep list {prep_list_id} not found")

        prep_list.assigned_to_id = assigned_to_id

        self.db.commit()
        self.db.refresh(prep_list)
        return prep_list

    def get_progress(
        self,
        prep_list_id: int,
    ) -> Dict[str, Any]:
        """Get progress for a prep list."""
        prep_list = self.db.get(PrepList, prep_list_id)
        if not prep_list:
            raise ValueError(f"Prep list {prep_list_id} not found")

        items = self.get_prep_list_items(prep_list_id)
        total = len(items)
        completed = sum(1 for i in items if i.completed)

        return {
            "prep_list_id": prep_list_id,
            "status": prep_list.status,
            "total_items": total,
            "completed_items": completed,
            "progress_percent": (completed / total * 100) if total > 0 else 0,
            "started_at": prep_list.started_at,
            "completed_at": prep_list.completed_at,
        }
