"""Virtual Brands / Ghost Kitchen Service."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import VirtualBrand


class VirtualBrandsService:
    """Service for virtual/ghost kitchen brand management."""

    def __init__(self, db: Session):
        self.db = db

    def create_brand(
        self,
        parent_location_id: int,
        brand_name: str,
        brand_slug: str,
        delivery_platforms: List[str],
        logo_url: Optional[str] = None,
        description: Optional[str] = None,
        cuisine_type: Optional[str] = None,
        menu_ids: Optional[List[int]] = None,
        operating_hours: Optional[Dict[str, Any]] = None,
    ) -> VirtualBrand:
        """Create a new virtual brand."""
        brand = VirtualBrand(
            parent_location_id=parent_location_id,
            brand_name=brand_name,
            brand_slug=brand_slug,
            logo_url=logo_url,
            description=description,
            cuisine_type=cuisine_type,
            menu_ids=menu_ids,
            delivery_platforms=delivery_platforms,
            operating_hours=operating_hours,
            is_active=True,
        )
        self.db.add(brand)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def get_brands(
        self,
        parent_location_id: int,
        active_only: bool = True,
    ) -> List[VirtualBrand]:
        """Get virtual brands for a location."""
        query = select(VirtualBrand).where(
            VirtualBrand.parent_location_id == parent_location_id
        )

        if active_only:
            query = query.where(VirtualBrand.is_active == True)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_brand(
        self,
        brand_id: int,
    ) -> Optional[VirtualBrand]:
        """Get a virtual brand by ID."""
        return self.db.get(VirtualBrand, brand_id)

    def get_brand_by_slug(
        self,
        brand_slug: str,
    ) -> Optional[VirtualBrand]:
        """Get a virtual brand by slug."""
        query = select(VirtualBrand).where(VirtualBrand.brand_slug == brand_slug)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def update_brand(
        self,
        brand_id: int,
        **updates,
    ) -> VirtualBrand:
        """Update a virtual brand."""
        brand = self.db.get(VirtualBrand, brand_id)
        if not brand:
            raise ValueError(f"Brand {brand_id} not found")

        for key, value in updates.items():
            if hasattr(brand, key) and key not in ["id", "total_orders", "total_revenue"]:
                setattr(brand, key, value)

        self.db.commit()
        self.db.refresh(brand)
        return brand

    def record_order(
        self,
        brand_id: int,
        order_total: Decimal,
        platform: str,
        rating: Optional[float] = None,
    ) -> VirtualBrand:
        """Record an order for a virtual brand."""
        brand = self.db.get(VirtualBrand, brand_id)
        if not brand:
            raise ValueError(f"Brand {brand_id} not found")

        brand.total_orders += 1
        brand.total_revenue += order_total

        # Update rolling average rating
        if rating:
            if brand.avg_rating:
                # Rolling average
                brand.avg_rating = (brand.avg_rating * 0.95) + (rating * 0.05)
            else:
                brand.avg_rating = rating

        self.db.commit()
        self.db.refresh(brand)
        return brand

    def get_performance(
        self,
        brand_id: int,
    ) -> Dict[str, Any]:
        """Get performance metrics for a virtual brand."""
        brand = self.db.get(VirtualBrand, brand_id)
        if not brand:
            raise ValueError(f"Brand {brand_id} not found")

        avg_order_value = (
            brand.total_revenue / brand.total_orders
            if brand.total_orders > 0 else Decimal("0")
        )

        return {
            "brand_id": brand_id,
            "brand_name": brand.brand_name,
            "orders_today": 0,  # Would calculate from orders table
            "revenue_today": Decimal("0"),
            "orders_this_week": 0,
            "revenue_this_week": Decimal("0"),
            "total_orders": brand.total_orders,
            "total_revenue": float(brand.total_revenue),
            "avg_order_value": float(avg_order_value),
            "avg_rating": brand.avg_rating,
            "top_items": [],  # Would calculate from orders
            "platform_breakdown": {
                platform: {"orders": 0, "revenue": 0}
                for platform in brand.delivery_platforms
            },
        }

    def get_all_brands_performance(
        self,
        parent_location_id: int,
    ) -> Dict[str, Any]:
        """Get performance summary for all brands at a location."""
        brands = self.get_brands(parent_location_id)

        total_orders = sum(b.total_orders for b in brands)
        total_revenue = sum(b.total_revenue for b in brands)

        brand_data = []
        for brand in brands:
            avg_order = (
                brand.total_revenue / brand.total_orders
                if brand.total_orders > 0 else Decimal("0")
            )
            brand_data.append({
                "id": brand.id,
                "name": brand.brand_name,
                "cuisine": brand.cuisine_type,
                "orders": brand.total_orders,
                "revenue": float(brand.total_revenue),
                "avg_order_value": float(avg_order),
                "rating": brand.avg_rating,
                "platforms": brand.delivery_platforms,
                "is_active": brand.is_active,
            })

        # Sort by revenue
        brand_data.sort(key=lambda x: x["revenue"], reverse=True)

        return {
            "total_brands": len(brands),
            "active_brands": sum(1 for b in brands if b.is_active),
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "brands": brand_data,
        }

    def toggle_active(
        self,
        brand_id: int,
    ) -> VirtualBrand:
        """Toggle brand active status."""
        brand = self.db.get(VirtualBrand, brand_id)
        if not brand:
            raise ValueError(f"Brand {brand_id} not found")

        brand.is_active = not brand.is_active

        self.db.commit()
        self.db.refresh(brand)
        return brand

    def update_operating_hours(
        self,
        brand_id: int,
        operating_hours: Dict[str, Any],
    ) -> VirtualBrand:
        """Update operating hours for a brand."""
        return self.update_brand(brand_id, operating_hours=operating_hours)

    def add_platform(
        self,
        brand_id: int,
        platform: str,
    ) -> VirtualBrand:
        """Add a delivery platform to a brand."""
        brand = self.db.get(VirtualBrand, brand_id)
        if not brand:
            raise ValueError(f"Brand {brand_id} not found")

        if platform not in brand.delivery_platforms:
            brand.delivery_platforms = brand.delivery_platforms + [platform]
            self.db.commit()
            self.db.refresh(brand)

        return brand

    def remove_platform(
        self,
        brand_id: int,
        platform: str,
    ) -> VirtualBrand:
        """Remove a delivery platform from a brand."""
        brand = self.db.get(VirtualBrand, brand_id)
        if not brand:
            raise ValueError(f"Brand {brand_id} not found")

        if platform in brand.delivery_platforms:
            brand.delivery_platforms = [p for p in brand.delivery_platforms if p != platform]
            self.db.commit()
            self.db.refresh(brand)

        return brand
