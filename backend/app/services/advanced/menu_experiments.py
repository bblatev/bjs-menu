"""Menu A/B Testing Experiments Service."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
import random
import math

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import MenuExperiment, MenuExperimentResult


class MenuExperimentsService:
    """Service for A/B menu testing experiments."""

    def __init__(self, db: Session):
        self.db = db

    def create_experiment(
        self,
        name: str,
        experiment_type: str,
        control_variant: Dict[str, Any],
        test_variants: List[Dict[str, Any]],
        traffic_split: Dict[str, int],
        start_date: date,
        location_id: Optional[int] = None,
        description: Optional[str] = None,
        end_date: Optional[date] = None,
    ) -> MenuExperiment:
        """Create a new menu experiment."""
        # Validate traffic split sums to 100
        total_split = sum(traffic_split.values())
        if total_split != 100:
            raise ValueError(f"Traffic split must sum to 100, got {total_split}")

        experiment = MenuExperiment(
            location_id=location_id,
            name=name,
            description=description,
            experiment_type=experiment_type,
            control_variant=control_variant,
            test_variants=test_variants,
            traffic_split=traffic_split,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
        )
        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    def get_experiment(
        self,
        experiment_id: int,
    ) -> Optional[MenuExperiment]:
        """Get an experiment by ID."""
        return self.db.get(MenuExperiment, experiment_id)

    def get_active_experiments(
        self,
        location_id: Optional[int] = None,
    ) -> List[MenuExperiment]:
        """Get all active experiments."""
        query = select(MenuExperiment).where(
            and_(
                MenuExperiment.is_active == True,
                MenuExperiment.start_date <= date.today(),
                (MenuExperiment.end_date.is_(None)) | (MenuExperiment.end_date >= date.today()),
            )
        )

        if location_id:
            query = query.where(
                (MenuExperiment.location_id == location_id) |
                (MenuExperiment.location_id.is_(None))
            )

        result = self.db.execute(query)
        return list(result.scalars().all())

    def assign_variant(
        self,
        experiment: MenuExperiment,
        user_id: Optional[int] = None,
    ) -> str:
        """Assign a variant to a user based on traffic split."""
        # Use user_id for consistent assignment if provided
        if user_id:
            random.seed(hash(f"{experiment.id}_{user_id}"))

        roll = random.randint(1, 100)
        cumulative = 0

        for variant, percentage in experiment.traffic_split.items():
            cumulative += percentage
            if roll <= cumulative:
                return variant

        return "control"

    def record_impression(
        self,
        experiment_id: int,
        variant_name: str,
        date_val: Optional[date] = None,
    ) -> MenuExperimentResult:
        """Record an impression for a variant."""
        if date_val is None:
            date_val = date.today()

        # Get or create result record
        query = select(MenuExperimentResult).where(
            and_(
                MenuExperimentResult.experiment_id == experiment_id,
                MenuExperimentResult.variant_name == variant_name,
                MenuExperimentResult.date == date_val,
            )
        )
        result = self.db.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            record = MenuExperimentResult(
                experiment_id=experiment_id,
                variant_name=variant_name,
                date=date_val,
                impressions=0,
                clicks=0,
                orders=0,
                revenue=Decimal("0"),
            )
            self.db.add(record)

        record.impressions += 1
        self.db.commit()
        self.db.refresh(record)
        return record

    def record_conversion(
        self,
        experiment_id: int,
        variant_name: str,
        revenue: Decimal,
        date_val: Optional[date] = None,
    ) -> MenuExperimentResult:
        """Record a conversion (order) for a variant."""
        if date_val is None:
            date_val = date.today()

        query = select(MenuExperimentResult).where(
            and_(
                MenuExperimentResult.experiment_id == experiment_id,
                MenuExperimentResult.variant_name == variant_name,
                MenuExperimentResult.date == date_val,
            )
        )
        result = self.db.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            record = MenuExperimentResult(
                experiment_id=experiment_id,
                variant_name=variant_name,
                date=date_val,
                impressions=0,
                clicks=0,
                orders=0,
                revenue=Decimal("0"),
            )
            self.db.add(record)

        record.orders += 1
        record.revenue += revenue

        # Update calculated fields
        if record.impressions > 0:
            record.conversion_rate = record.orders / record.impressions
        if record.orders > 0:
            record.avg_order_value = record.revenue / record.orders

        self.db.commit()
        self.db.refresh(record)
        return record

    def get_experiment_results(
        self,
        experiment_id: int,
    ) -> List[MenuExperimentResult]:
        """Get all results for an experiment."""
        query = select(MenuExperimentResult).where(
            MenuExperimentResult.experiment_id == experiment_id
        ).order_by(MenuExperimentResult.date)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def analyze_experiment(
        self,
        experiment_id: int,
    ) -> Dict[str, Any]:
        """Analyze experiment results and determine winner."""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Aggregate results by variant
        query = select(
            MenuExperimentResult.variant_name,
            func.sum(MenuExperimentResult.impressions).label("total_impressions"),
            func.sum(MenuExperimentResult.orders).label("total_orders"),
            func.sum(MenuExperimentResult.revenue).label("total_revenue"),
        ).where(
            MenuExperimentResult.experiment_id == experiment_id
        ).group_by(MenuExperimentResult.variant_name)

        result = self.db.execute(query)
        variant_data = {
            row.variant_name: {
                "impressions": row.total_impressions or 0,
                "orders": row.total_orders or 0,
                "revenue": float(row.total_revenue or 0),
                "conversion_rate": (row.total_orders / row.total_impressions * 100)
                    if row.total_impressions else 0,
            }
            for row in result.all()
        }

        # Calculate statistical significance
        control_data = variant_data.get("control", {"conversion_rate": 0, "impressions": 0})

        best_variant = None
        best_lift = 0
        lift_vs_control = {}

        for variant, data in variant_data.items():
            if variant == "control":
                continue

            if control_data["conversion_rate"] > 0:
                lift = ((data["conversion_rate"] - control_data["conversion_rate"]) /
                       control_data["conversion_rate"] * 100)
            else:
                lift = 0

            lift_vs_control[variant] = lift

            if lift > best_lift:
                best_lift = lift
                best_variant = variant

        # Simple statistical significance calculation (would use proper stats in production)
        significance = self._calculate_significance(control_data, variant_data)

        # Update experiment with winner if significant
        winner = None
        recommendation = "Continue experiment - need more data"

        if significance >= 0.95:
            if best_lift > 5:  # At least 5% lift
                winner = best_variant
                recommendation = f"Implement {best_variant} - {best_lift:.1f}% lift with {significance*100:.1f}% confidence"
            else:
                winner = "control"
                recommendation = "Keep control - no significant improvement from variants"

            experiment.winner_variant = winner
            experiment.statistical_significance = significance
            self.db.commit()

        return {
            "experiment_id": experiment_id,
            "variants": [
                {"name": name, **data}
                for name, data in variant_data.items()
            ],
            "winner": winner,
            "statistical_significance": significance,
            "lift_vs_control": lift_vs_control,
            "recommendation": recommendation,
        }

    def _calculate_significance(
        self,
        control: Dict[str, Any],
        variants: Dict[str, Dict[str, Any]],
    ) -> float:
        """Calculate statistical significance (simplified z-test)."""
        if control["impressions"] < 100:
            return 0.0

        # Find the best performing variant
        best_variant = None
        best_conv = control["conversion_rate"]

        for name, data in variants.items():
            if name == "control":
                continue
            if data["conversion_rate"] > best_conv:
                best_conv = data["conversion_rate"]
                best_variant = name

        if not best_variant:
            return 0.0

        # Simplified significance based on sample size and effect
        n1 = control["impressions"]
        n2 = variants[best_variant]["impressions"]

        if n1 < 50 or n2 < 50:
            return 0.0

        p1 = control["conversion_rate"] / 100
        p2 = variants[best_variant]["conversion_rate"] / 100

        # Pooled proportion
        p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)

        if p_pool == 0 or p_pool == 1:
            return 0.0

        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))

        if se == 0:
            return 0.0

        # Z-score
        z = abs(p2 - p1) / se

        # Convert to approximate confidence level
        if z >= 2.576:
            return 0.99
        elif z >= 1.96:
            return 0.95
        elif z >= 1.645:
            return 0.90
        elif z >= 1.28:
            return 0.80
        else:
            return min(0.5 + z * 0.15, 0.79)

    def end_experiment(
        self,
        experiment_id: int,
        winner_variant: Optional[str] = None,
    ) -> MenuExperiment:
        """End an experiment."""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment.is_active = False
        experiment.end_date = date.today()

        if winner_variant:
            experiment.winner_variant = winner_variant

        self.db.commit()
        self.db.refresh(experiment)
        return experiment
