"""Bluetooth Scale Integration Service - WISK style."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.analytics import BottleWeight, ScaleReading
from app.models.product import Product
from app.models.inventory import InventorySession, InventoryLine


# Default alcohol densities (g/ml)
ALCOHOL_DENSITIES = {
    "vodka": 0.95,
    "whiskey": 0.94,
    "bourbon": 0.94,
    "scotch": 0.94,
    "rum": 0.94,
    "tequila": 0.93,
    "gin": 0.95,
    "brandy": 0.93,
    "cognac": 0.93,
    "liqueur": 1.05,
    "cream_liqueur": 1.08,
    "wine": 0.99,
    "champagne": 0.99,
    "beer": 1.01,
    "vermouth": 1.02,
    "default": 0.95
}


class ScaleService:
    """Handle Bluetooth scale readings and bottle weight calculations."""

    def __init__(self, db: Session):
        self.db = db

    def process_scale_reading(
        self,
        product_id: int,
        weight_grams: float,
        session_id: Optional[int] = None,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a scale reading and calculate remaining volume.
        Uses bottle weight database for accurate calculations.
        """
        # Get product
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"error": "Product not found"}

        # Get bottle weight data
        bottle_weight = self.db.query(BottleWeight).filter(
            BottleWeight.product_id == product_id
        ).first()

        # Calculate remaining amount
        if bottle_weight and bottle_weight.empty_weight and bottle_weight.full_weight:
            # Use precise calculation with known weights
            remaining_percent, remaining_ml = self._calculate_with_weights(
                weight_grams,
                bottle_weight.full_weight,
                bottle_weight.empty_weight,
                bottle_weight.volume_ml
            )
        else:
            # Fallback to density-based calculation
            # Note: Product model doesn't have category, use default density
            density = ALCOHOL_DENSITIES["default"]

            # Estimate volume based on typical bottle sizes
            estimated_volume = 750  # Default 750ml
            remaining_percent, remaining_ml = self._calculate_with_density(
                weight_grams,
                density,
                estimated_volume
            )

        # Save reading
        reading = ScaleReading(
            session_id=session_id,
            product_id=product_id,
            bottle_weight_id=bottle_weight.id if bottle_weight else None,
            weight_grams=weight_grams,
            calculated_remaining_ml=remaining_ml,
            calculated_remaining_percent=remaining_percent,
            reading_method="scale",
            scale_device_id=device_id,
            scale_device_name=device_name
        )
        self.db.add(reading)
        self.db.commit()

        return {
            "product_id": product_id,
            "product_name": product.name,
            "weight_grams": weight_grams,
            "remaining_percent": round(remaining_percent, 1),
            "remaining_ml": round(remaining_ml, 1),
            "reading_id": reading.id,
            "method": "precise" if bottle_weight else "estimated",
            "confidence": 0.99 if bottle_weight else 0.85
        }

    def _calculate_with_weights(
        self,
        current_weight: float,
        full_weight: float,
        empty_weight: float,
        volume_ml: Optional[int]
    ) -> tuple:
        """Calculate remaining using known bottle weights."""
        if full_weight <= empty_weight:
            return 0.0, 0.0

        # Calculate percentage remaining
        liquid_weight = full_weight - empty_weight
        remaining_weight = current_weight - empty_weight

        if remaining_weight < 0:
            remaining_weight = 0

        remaining_percent = (remaining_weight / liquid_weight) * 100

        # Calculate ml if volume known
        remaining_ml = 0
        if volume_ml:
            remaining_ml = (remaining_percent / 100) * volume_ml
        else:
            # Estimate ml from weight (assuming ~0.95 density)
            remaining_ml = remaining_weight / 0.95

        return min(remaining_percent, 100), remaining_ml

    def _calculate_with_density(
        self,
        current_weight: float,
        density: float,
        estimated_volume: int
    ) -> tuple:
        """Calculate remaining using alcohol density."""
        # Estimate empty bottle weight (typically 400-600g for 750ml)
        estimated_empty = 500

        remaining_weight = current_weight - estimated_empty
        if remaining_weight < 0:
            remaining_weight = 0

        # Calculate ml from weight
        remaining_ml = remaining_weight / density

        # Calculate percentage
        remaining_percent = (remaining_ml / estimated_volume) * 100

        return min(remaining_percent, 100), remaining_ml

    def record_visual_estimate(
        self,
        product_id: int,
        estimated_percent: float,
        session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Record a visual estimate of bottle fill level."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"error": "Product not found"}

        # Get bottle volume for ml calculation
        bottle_weight = self.db.query(BottleWeight).filter(
            BottleWeight.product_id == product_id
        ).first()

        volume_ml = bottle_weight.volume_ml if bottle_weight else 750
        remaining_ml = (estimated_percent / 100) * volume_ml

        reading = ScaleReading(
            session_id=session_id,
            product_id=product_id,
            bottle_weight_id=bottle_weight.id if bottle_weight else None,
            weight_grams=0,  # Visual estimate, no weight
            calculated_remaining_ml=remaining_ml,
            calculated_remaining_percent=estimated_percent,
            reading_method="visual"
        )
        self.db.add(reading)
        self.db.commit()

        return {
            "product_id": product_id,
            "product_name": product.name,
            "weight_grams": 0.0,
            "remaining_percent": estimated_percent,
            "remaining_ml": round(remaining_ml, 1),
            "reading_id": reading.id,
            "method": "visual",
            "confidence": 0.7
        }


class BottleWeightDatabaseService:
    """Manage bottle weight database."""

    def __init__(self, db: Session):
        self.db = db

    def add_bottle_weight(
        self,
        product_id: int,
        full_weight: float,
        empty_weight: float,
        volume_ml: int,
        barcode: Optional[str] = None,
        brand: Optional[str] = None,
        alcohol_category: Optional[str] = None,
        source: str = "manual"
    ) -> BottleWeight:
        """Add or update bottle weight entry."""
        # Check if entry exists
        existing = self.db.query(BottleWeight).filter(
            BottleWeight.product_id == product_id
        ).first()

        if existing:
            existing.full_weight = full_weight
            existing.empty_weight = empty_weight
            existing.volume_ml = volume_ml
            existing.barcode = barcode or existing.barcode
            existing.brand = brand or existing.brand
            existing.alcohol_category = alcohol_category or existing.alcohol_category
            existing.verification_count += 1
            existing.updated_at = datetime.now(timezone.utc)
            bottle = existing
        else:
            product = self.db.query(Product).filter(Product.id == product_id).first()
            bottle = BottleWeight(
                product_id=product_id,
                product_name=product.name if product else "",
                barcode=barcode,
                brand=brand,
                full_weight=full_weight,
                empty_weight=empty_weight,
                volume_ml=volume_ml,
                alcohol_category=alcohol_category,
                density=ALCOHOL_DENSITIES.get(alcohol_category or "default"),
                source=source
            )
            self.db.add(bottle)

        self.db.commit()
        return bottle

    def get_bottle_weight(
        self,
        product_id: Optional[int] = None,
        barcode: Optional[str] = None
    ) -> Optional[BottleWeight]:
        """Get bottle weight entry by product ID or barcode."""
        query = self.db.query(BottleWeight)

        if product_id:
            query = query.filter(BottleWeight.product_id == product_id)
        elif barcode:
            query = query.filter(BottleWeight.barcode == barcode)
        else:
            return None

        return query.first()

    def search_bottle_database(
        self,
        search_term: str,
        limit: int = 20
    ) -> List[BottleWeight]:
        """Search bottle weight database."""
        return self.db.query(BottleWeight).filter(
            func.lower(BottleWeight.product_name).contains(search_term.lower()) |
            func.lower(BottleWeight.brand).contains(search_term.lower())
        ).limit(limit).all()

    def get_products_without_weights(self) -> List[Product]:
        """Get products that don't have bottle weight data."""
        subquery = self.db.query(BottleWeight.product_id)

        # Note: Product model doesn't have category field, return all products without weights
        return self.db.query(Product).filter(
            Product.id.notin_(subquery),
            Product.active == True
        ).all()

    def import_from_wisk_format(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Import bottle weights from WISK-compatible format."""
        imported = 0
        errors = []

        for item in data:
            try:
                # Try to match product
                product = None
                if item.get("barcode"):
                    product = self.db.query(Product).filter(
                        Product.barcode == item["barcode"]
                    ).first()

                if not product and item.get("name"):
                    product = self.db.query(Product).filter(
                        func.lower(Product.name).contains(item["name"].lower()[:20])
                    ).first()

                if not product:
                    # Create placeholder if no match
                    product_id = None
                else:
                    product_id = product.id

                bottle = BottleWeight(
                    product_id=product_id,
                    product_name=item.get("name", ""),
                    brand=item.get("brand"),
                    barcode=item.get("barcode"),
                    full_weight=item.get("full_weight", 0),
                    empty_weight=item.get("empty_weight", 0),
                    volume_ml=item.get("volume_ml"),
                    alcohol_category=item.get("category"),
                    source="import"
                )
                self.db.add(bottle)
                imported += 1

            except Exception as e:
                errors.append({"item": item.get("name"), "error": str(e)})

        self.db.commit()

        return {
            "imported": imported,
            "errors": len(errors),
            "error_details": errors[:10]  # First 10 errors
        }


class InventoryCountingService:
    """Combine scale readings with inventory counting."""

    def __init__(self, db: Session):
        self.db = db
        self.scale_service = ScaleService(db)

    def count_partial_bottle(
        self,
        session_id: int,
        product_id: int,
        weight_grams: Optional[float] = None,
        visual_percent: Optional[float] = None,
        full_bottles: int = 0
    ) -> Dict[str, Any]:
        """
        Count inventory including partial bottles.
        Combines full bottle count with partial bottle measurement.
        """
        session = self.db.query(InventorySession).filter(
            InventorySession.id == session_id
        ).first()

        if not session:
            return {"error": "Session not found"}

        # Calculate partial bottle amount
        partial_amount = 0
        reading_result = None

        if weight_grams is not None:
            # Use scale
            reading_result = self.scale_service.process_scale_reading(
                product_id=product_id,
                weight_grams=weight_grams,
                session_id=session_id
            )
            partial_amount = reading_result.get("remaining_percent", 0) / 100

        elif visual_percent is not None:
            # Use visual estimate
            reading_result = self.scale_service.record_visual_estimate(
                product_id=product_id,
                estimated_percent=visual_percent,
                session_id=session_id
            )
            partial_amount = visual_percent / 100

        # Total count = full bottles + partial
        total_count = full_bottles + partial_amount

        # Check for existing inventory line
        existing_line = self.db.query(InventoryLine).filter(
            InventoryLine.session_id == session_id,
            InventoryLine.product_id == product_id
        ).first()

        if existing_line:
            existing_line.counted_qty = total_count
            existing_line.method = "SCALE" if weight_grams else "VISUAL"
            existing_line.counted_at = datetime.now(timezone.utc)
        else:
            line = InventoryLine(
                session_id=session_id,
                product_id=product_id,
                counted_qty=total_count,
                method="SCALE" if weight_grams else "VISUAL",
                confidence=reading_result.get("confidence", 0.8) if reading_result else 0.8
            )
            self.db.add(line)

        self.db.commit()

        return {
            "session_id": session_id,
            "product_id": product_id,
            "full_bottles": full_bottles,
            "partial_amount": round(partial_amount, 2),
            "total_count": round(total_count, 2),
            "reading": reading_result
        }

    def get_session_summary(self, session_id: int) -> Dict[str, Any]:
        """Get summary of inventory counting session including scale readings."""
        session = self.db.query(InventorySession).filter(
            InventorySession.id == session_id
        ).first()

        if not session:
            return {"error": "Session not found"}

        lines = self.db.query(InventoryLine).filter(
            InventoryLine.session_id == session_id
        ).all()

        readings = self.db.query(ScaleReading).filter(
            ScaleReading.session_id == session_id
        ).all()

        return {
            "session_id": session_id,
            "status": session.status,
            "total_items": len(lines),
            "scale_readings": len([r for r in readings if r.reading_method == "scale"]),
            "visual_estimates": len([r for r in readings if r.reading_method == "visual"]),
            "items": [
                {
                    "product_id": line.product_id,
                    "counted_qty": line.counted_qty,
                    "method": line.method,
                    "confidence": line.confidence
                }
                for line in lines
            ]
        }
