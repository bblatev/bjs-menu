"""Tips Pooling & Distribution Service."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import TipPoolConfiguration, TipPoolDistribution


class TipPoolingService:
    """Service for tip pooling and distribution."""

    def __init__(self, db: Session):
        self.db = db

    def create_configuration(
        self,
        location_id: int,
        name: str,
        pool_type: str,
        distribution_rules: Dict[str, Any],
        exclude_management: bool = True,
        minimum_hours_to_participate: Optional[float] = None,
    ) -> TipPoolConfiguration:
        """Create a tip pool configuration."""
        config = TipPoolConfiguration(
            location_id=location_id,
            name=name,
            pool_type=pool_type,
            distribution_rules=distribution_rules,
            exclude_management=exclude_management,
            minimum_hours_to_participate=minimum_hours_to_participate,
            is_active=True,
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def get_configuration(
        self,
        location_id: int,
    ) -> Optional[TipPoolConfiguration]:
        """Get active tip pool configuration for a location."""
        query = select(TipPoolConfiguration).where(
            and_(
                TipPoolConfiguration.location_id == location_id,
                TipPoolConfiguration.is_active == True,
            )
        )
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def calculate_distribution(
        self,
        configuration_id: int,
        total_tips: Decimal,
        employee_hours: Dict[int, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calculate tip distribution for employees."""
        config = self.db.get(TipPoolConfiguration, configuration_id)
        if not config:
            raise ValueError(f"Configuration {configuration_id} not found")

        distributions = []
        warnings = []

        # Filter employees based on minimum hours
        eligible_employees = {}
        for emp_id, data in employee_hours.items():
            hours = data.get("hours", 0)
            role = data.get("role", "server")
            is_management = data.get("is_management", False)

            if config.exclude_management and is_management:
                continue

            if config.minimum_hours_to_participate and hours < config.minimum_hours_to_participate:
                warnings.append(f"Employee {emp_id} has only {hours} hours, minimum is {config.minimum_hours_to_participate}")
                continue

            eligible_employees[emp_id] = {"hours": hours, "role": role}

        if not eligible_employees:
            raise ValueError("No eligible employees for tip distribution")

        if config.pool_type == "percentage":
            # Distribute based on role percentages
            role_pools = {}
            for emp_id, data in eligible_employees.items():
                role = data["role"]
                if role not in role_pools:
                    role_pools[role] = []
                role_pools[role].append(emp_id)

            for role, emp_ids in role_pools.items():
                role_percent = config.distribution_rules.get(role, 0)
                role_pool = total_tips * Decimal(str(role_percent)) / 100
                per_person = role_pool / len(emp_ids) if emp_ids else Decimal("0")

                for emp_id in emp_ids:
                    distributions.append({
                        "employee_id": emp_id,
                        "amount": float(per_person),
                        "hours": eligible_employees[emp_id]["hours"],
                        "role": role,
                    })

        elif config.pool_type == "hours_worked":
            # Distribute proportional to hours worked
            total_hours = sum(d["hours"] for d in eligible_employees.values())
            for emp_id, data in eligible_employees.items():
                share = Decimal(str(data["hours"])) / Decimal(str(total_hours))
                amount = total_tips * share
                distributions.append({
                    "employee_id": emp_id,
                    "amount": float(amount),
                    "hours": data["hours"],
                    "role": data["role"],
                })

        elif config.pool_type == "points":
            # Points-based system
            points_per_role = config.distribution_rules.get("points_per_role", {})
            total_points = 0
            employee_points = {}

            for emp_id, data in eligible_employees.items():
                role = data["role"]
                points = points_per_role.get(role, 1) * data["hours"]
                employee_points[emp_id] = points
                total_points += points

            for emp_id, points in employee_points.items():
                share = Decimal(str(points)) / Decimal(str(total_points))
                amount = total_tips * share
                distributions.append({
                    "employee_id": emp_id,
                    "amount": float(amount),
                    "hours": eligible_employees[emp_id]["hours"],
                    "role": eligible_employees[emp_id]["role"],
                    "points": points,
                })

        # Verify total matches
        total_distributed = sum(d["amount"] for d in distributions)
        if abs(total_distributed - float(total_tips)) > 0.01:
            warnings.append(f"Rounding difference: ${float(total_tips) - total_distributed:.2f}")

        return {
            "configuration_id": configuration_id,
            "total_tips": float(total_tips),
            "distributions": distributions,
            "validation_warnings": warnings,
        }

    def create_distribution(
        self,
        configuration_id: int,
        location_id: int,
        distribution_date: date,
        pay_period_start: date,
        pay_period_end: date,
        total_tips_collected: Decimal,
        employee_distributions: List[Dict[str, Any]],
        approved_by_id: Optional[int] = None,
    ) -> TipPoolDistribution:
        """Create a finalized tip distribution record."""
        total_distributed = sum(Decimal(str(d["amount"])) for d in employee_distributions)

        distribution = TipPoolDistribution(
            configuration_id=configuration_id,
            location_id=location_id,
            distribution_date=distribution_date,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            total_tips_collected=total_tips_collected,
            total_tips_distributed=total_distributed,
            employee_distributions=employee_distributions,
            approved_by_id=approved_by_id,
            approved_at=datetime.utcnow() if approved_by_id else None,
        )
        self.db.add(distribution)
        self.db.commit()
        self.db.refresh(distribution)
        return distribution

    def get_distributions(
        self,
        location_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[TipPoolDistribution]:
        """Get tip distributions for a location."""
        query = select(TipPoolDistribution).where(
            TipPoolDistribution.location_id == location_id
        )

        if start_date:
            query = query.where(TipPoolDistribution.distribution_date >= start_date)
        if end_date:
            query = query.where(TipPoolDistribution.distribution_date <= end_date)

        query = query.order_by(TipPoolDistribution.distribution_date.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def approve_distribution(
        self,
        distribution_id: int,
        approved_by_id: int,
    ) -> TipPoolDistribution:
        """Approve a tip distribution."""
        distribution = self.db.get(TipPoolDistribution, distribution_id)
        if not distribution:
            raise ValueError(f"Distribution {distribution_id} not found")

        distribution.approved_by_id = approved_by_id
        distribution.approved_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(distribution)
        return distribution

    def get_employee_tips(
        self,
        employee_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get tip history for an employee."""
        query = select(TipPoolDistribution)

        if start_date:
            query = query.where(TipPoolDistribution.distribution_date >= start_date)
        if end_date:
            query = query.where(TipPoolDistribution.distribution_date <= end_date)

        result = self.db.execute(query)
        distributions = list(result.scalars().all())

        employee_tips = []
        total = Decimal("0")

        for dist in distributions:
            for emp_dist in dist.employee_distributions:
                if emp_dist.get("employee_id") == employee_id:
                    amount = Decimal(str(emp_dist.get("amount", 0)))
                    employee_tips.append({
                        "date": dist.distribution_date.isoformat(),
                        "period_start": dist.pay_period_start.isoformat(),
                        "period_end": dist.pay_period_end.isoformat(),
                        "amount": float(amount),
                        "hours": emp_dist.get("hours"),
                    })
                    total += amount

        return {
            "employee_id": employee_id,
            "total_tips": float(total),
            "distributions": employee_tips,
        }
