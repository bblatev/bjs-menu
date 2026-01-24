"""Allergen Cross-Contact Alert Service."""

from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import AllergenProfile, AllergenAlert


class AllergenService:
    """Service for allergen management and cross-contact alerts."""

    COMMON_ALLERGENS = [
        "gluten", "dairy", "eggs", "peanuts", "tree_nuts",
        "soy", "fish", "shellfish", "sesame"
    ]

    def __init__(self, db: Session):
        self.db = db

    def create_profile(
        self,
        product_id: int,
        contains_gluten: bool = False,
        contains_dairy: bool = False,
        contains_eggs: bool = False,
        contains_peanuts: bool = False,
        contains_tree_nuts: bool = False,
        contains_soy: bool = False,
        contains_fish: bool = False,
        contains_shellfish: bool = False,
        contains_sesame: bool = False,
        may_contain: Optional[List[str]] = None,
        prepared_on_shared_equipment: bool = False,
        other_allergens: Optional[List[str]] = None,
        dietary_flags: Optional[List[str]] = None,
    ) -> AllergenProfile:
        """Create an allergen profile for a product."""
        profile = AllergenProfile(
            product_id=product_id,
            contains_gluten=contains_gluten,
            contains_dairy=contains_dairy,
            contains_eggs=contains_eggs,
            contains_peanuts=contains_peanuts,
            contains_tree_nuts=contains_tree_nuts,
            contains_soy=contains_soy,
            contains_fish=contains_fish,
            contains_shellfish=contains_shellfish,
            contains_sesame=contains_sesame,
            may_contain=may_contain,
            prepared_on_shared_equipment=prepared_on_shared_equipment,
            other_allergens=other_allergens,
            dietary_flags=dietary_flags,
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_profile(
        self,
        product_id: int,
    ) -> Optional[AllergenProfile]:
        """Get allergen profile for a product."""
        query = select(AllergenProfile).where(AllergenProfile.product_id == product_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_product_allergens(
        self,
        product_id: int,
    ) -> List[str]:
        """Get list of allergens for a product."""
        profile = self.get_profile(product_id)
        if not profile:
            return []

        allergens = []
        if profile.contains_gluten:
            allergens.append("gluten")
        if profile.contains_dairy:
            allergens.append("dairy")
        if profile.contains_eggs:
            allergens.append("eggs")
        if profile.contains_peanuts:
            allergens.append("peanuts")
        if profile.contains_tree_nuts:
            allergens.append("tree_nuts")
        if profile.contains_soy:
            allergens.append("soy")
        if profile.contains_fish:
            allergens.append("fish")
        if profile.contains_shellfish:
            allergens.append("shellfish")
        if profile.contains_sesame:
            allergens.append("sesame")

        if profile.other_allergens:
            allergens.extend(profile.other_allergens)

        return allergens

    def check_order(
        self,
        order_items: List[int],
        customer_allergens: List[str],
    ) -> Dict[str, Any]:
        """Check order items against customer allergens."""
        conflicts = []
        warnings = []
        is_safe = True

        for item_id in order_items:
            profile = self.get_profile(item_id)
            if not profile:
                continue

            item_allergens = self.get_product_allergens(item_id)

            # Check direct conflicts
            for allergen in customer_allergens:
                if allergen.lower() in [a.lower() for a in item_allergens]:
                    conflicts.append({
                        "item_id": item_id,
                        "allergen": allergen,
                        "type": "contains",
                    })
                    is_safe = False

            # Check may contain
            if profile.may_contain:
                for allergen in customer_allergens:
                    if allergen.lower() in [a.lower() for a in profile.may_contain]:
                        warnings.append({
                            "item_id": item_id,
                            "allergen": allergen,
                            "type": "may_contain",
                        })

            # Check shared equipment
            if profile.prepared_on_shared_equipment:
                warnings.append({
                    "item_id": item_id,
                    "type": "shared_equipment",
                    "message": "Prepared on shared equipment",
                })

        recommendations = []
        if conflicts:
            recommendations.append("Remove items containing allergens")
        if warnings:
            recommendations.append("Inform kitchen about allergen concerns")
            recommendations.append("Request dedicated prep area if available")

        return {
            "is_safe": is_safe,
            "conflicts": conflicts,
            "warnings": warnings,
            "recommendations": recommendations,
        }

    def create_alert(
        self,
        order_id: int,
        location_id: int,
        allergens_flagged: List[str],
        alert_message: str,
        severity: str = "warning",
        special_prep_required: bool = False,
        prep_instructions: Optional[str] = None,
    ) -> AllergenAlert:
        """Create an allergen alert for kitchen."""
        alert = AllergenAlert(
            order_id=order_id,
            location_id=location_id,
            allergens_flagged=allergens_flagged,
            alert_message=alert_message,
            severity=severity,
            special_prep_required=special_prep_required,
            prep_instructions=prep_instructions,
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def acknowledge_alert(
        self,
        alert_id: int,
        acknowledged_by_id: int,
    ) -> AllergenAlert:
        """Acknowledge an allergen alert."""
        alert = self.db.get(AllergenAlert, alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.acknowledged = True
        alert.acknowledged_by_id = acknowledged_by_id
        alert.acknowledged_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(alert)
        return alert

    def get_alerts(
        self,
        location_id: int,
        acknowledged: Optional[bool] = None,
    ) -> List[AllergenAlert]:
        """Get allergen alerts for a location."""
        query = select(AllergenAlert).where(
            AllergenAlert.location_id == location_id
        )

        if acknowledged is not None:
            query = query.where(AllergenAlert.acknowledged == acknowledged)

        query = query.order_by(AllergenAlert.created_at.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def update_profile(
        self,
        product_id: int,
        **updates,
    ) -> AllergenProfile:
        """Update allergen profile."""
        profile = self.get_profile(product_id)
        if not profile:
            raise ValueError(f"Profile for product {product_id} not found")

        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def bulk_check(
        self,
        product_ids: List[int],
    ) -> Dict[int, List[str]]:
        """Check allergens for multiple products."""
        result = {}
        for product_id in product_ids:
            allergens = self.get_product_allergens(product_id)
            result[product_id] = allergens
        return result
