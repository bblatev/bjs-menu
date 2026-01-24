"""ESG & Sustainability Reporting Service."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import SustainabilityMetric, ESGReport


class SustainabilityService:
    """Service for ESG and sustainability reporting."""

    def __init__(self, db: Session):
        self.db = db

    def record_daily_metrics(
        self,
        location_id: int,
        date: date,
        carbon_kg: Decimal = Decimal("0"),
        food_waste_kg: Decimal = Decimal("0"),
        food_donated_kg: Decimal = Decimal("0"),
        food_composted_kg: Decimal = Decimal("0"),
        landfill_kg: Decimal = Decimal("0"),
        energy_kwh: Optional[Decimal] = None,
        water_liters: Optional[Decimal] = None,
        single_use_plastic_items: int = 0,
        recyclable_packaging_percent: Optional[float] = None,
        local_sourcing_percent: Optional[float] = None,
        organic_percent: Optional[float] = None,
        covers: Optional[int] = None,
    ) -> SustainabilityMetric:
        """Record daily sustainability metrics."""
        # Check for existing record
        query = select(SustainabilityMetric).where(
            and_(
                SustainabilityMetric.location_id == location_id,
                SustainabilityMetric.date == date,
            )
        )
        result = self.db.execute(query)
        metric = result.scalar_one_or_none()

        carbon_per_cover = None
        if covers and covers > 0:
            carbon_per_cover = carbon_kg / covers

        if metric:
            # Update existing
            metric.carbon_kg = carbon_kg
            metric.carbon_per_cover = carbon_per_cover
            metric.food_waste_kg = food_waste_kg
            metric.food_donated_kg = food_donated_kg
            metric.food_composted_kg = food_composted_kg
            metric.landfill_kg = landfill_kg
            metric.energy_kwh = energy_kwh
            metric.water_liters = water_liters
            metric.single_use_plastic_items = single_use_plastic_items
            metric.recyclable_packaging_percent = recyclable_packaging_percent
            metric.local_sourcing_percent = local_sourcing_percent
            metric.organic_percent = organic_percent
        else:
            metric = SustainabilityMetric(
                location_id=location_id,
                date=date,
                carbon_kg=carbon_kg,
                carbon_per_cover=carbon_per_cover,
                food_waste_kg=food_waste_kg,
                food_donated_kg=food_donated_kg,
                food_composted_kg=food_composted_kg,
                landfill_kg=landfill_kg,
                energy_kwh=energy_kwh,
                water_liters=water_liters,
                single_use_plastic_items=single_use_plastic_items,
                recyclable_packaging_percent=recyclable_packaging_percent,
                local_sourcing_percent=local_sourcing_percent,
                organic_percent=organic_percent,
            )
            self.db.add(metric)

        self.db.commit()
        self.db.refresh(metric)
        return metric

    def get_metrics(
        self,
        location_id: int,
        start_date: date,
        end_date: date,
    ) -> List[SustainabilityMetric]:
        """Get sustainability metrics for a period."""
        query = select(SustainabilityMetric).where(
            and_(
                SustainabilityMetric.location_id == location_id,
                SustainabilityMetric.date >= start_date,
                SustainabilityMetric.date <= end_date,
            )
        ).order_by(SustainabilityMetric.date)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def generate_report(
        self,
        location_id: Optional[int],
        report_period: str,
        period_start: date,
        period_end: date,
        carbon_target_kg: Optional[Decimal] = None,
        waste_target_kg: Optional[Decimal] = None,
    ) -> ESGReport:
        """Generate an ESG report for a period."""
        # Aggregate metrics
        query = select(
            func.sum(SustainabilityMetric.carbon_kg).label("total_carbon"),
            func.sum(SustainabilityMetric.food_waste_kg).label("total_waste"),
            func.sum(SustainabilityMetric.food_donated_kg).label("total_donated"),
            func.sum(SustainabilityMetric.food_composted_kg).label("total_composted"),
            func.sum(SustainabilityMetric.landfill_kg).label("total_landfill"),
        ).where(
            and_(
                SustainabilityMetric.date >= period_start,
                SustainabilityMetric.date <= period_end,
            )
        )

        if location_id:
            query = query.where(SustainabilityMetric.location_id == location_id)

        result = self.db.execute(query)
        totals = result.first()

        total_carbon = totals.total_carbon or Decimal("0")
        total_waste = totals.total_waste or Decimal("0")
        total_diverted = (totals.total_donated or Decimal("0")) + (totals.total_composted or Decimal("0"))

        waste_diversion_rate = float(total_diverted / total_waste * 100) if total_waste > 0 else 0

        # Calculate vs targets
        carbon_vs_target = None
        waste_vs_target = None

        if carbon_target_kg:
            carbon_vs_target = float((total_carbon / carbon_target_kg - 1) * 100)

        if waste_target_kg:
            waste_vs_target = float((total_waste / waste_target_kg - 1) * 100)

        report = ESGReport(
            location_id=location_id,
            report_period=report_period,
            period_start=period_start,
            period_end=period_end,
            total_carbon_kg=total_carbon,
            total_waste_kg=total_waste,
            waste_diversion_rate=waste_diversion_rate,
            carbon_target_kg=carbon_target_kg,
            waste_target_kg=waste_target_kg,
            carbon_vs_target_percent=carbon_vs_target,
            waste_vs_target_percent=waste_vs_target,
            status="draft",
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_reports(
        self,
        location_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[ESGReport]:
        """Get ESG reports."""
        query = select(ESGReport)

        if location_id:
            query = query.where(ESGReport.location_id == location_id)
        if status:
            query = query.where(ESGReport.status == status)

        query = query.order_by(ESGReport.period_start.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def publish_report(
        self,
        report_id: int,
    ) -> ESGReport:
        """Publish an ESG report."""
        report = self.db.get(ESGReport, report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")

        report.status = "published"
        report.published_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(report)
        return report

    def get_dashboard(
        self,
        location_id: int,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get sustainability dashboard data."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        metrics = self.get_metrics(location_id, start_date, end_date)

        if not metrics:
            return {
                "carbon_footprint": {"total": 0, "daily_avg": 0},
                "waste_metrics": {"total": 0, "diversion_rate": 0},
                "sustainability_score": 0,
                "vs_previous_period": {},
                "targets": {},
                "recommendations": ["Start tracking sustainability metrics"],
            }

        total_carbon = sum(m.carbon_kg for m in metrics)
        total_waste = sum(m.food_waste_kg for m in metrics)
        total_donated = sum(m.food_donated_kg for m in metrics)
        total_composted = sum(m.food_composted_kg for m in metrics)
        total_landfill = sum(m.landfill_kg for m in metrics)

        diversion_rate = ((total_donated + total_composted) / total_waste * 100) if total_waste > 0 else 0

        # Calculate sustainability score (simplified)
        score = 50  # Base score
        if diversion_rate > 50:
            score += 20
        if diversion_rate > 75:
            score += 10

        # Check local sourcing
        local_avg = sum(m.local_sourcing_percent or 0 for m in metrics) / len(metrics) if metrics else 0
        if local_avg > 30:
            score += 10
        if local_avg > 50:
            score += 10

        # Calculate vs previous period
        prev_start = start_date - timedelta(days=days)
        prev_metrics = self.get_metrics(location_id, prev_start, start_date - timedelta(days=1))

        vs_previous = {}
        if prev_metrics:
            prev_carbon = sum(m.carbon_kg for m in prev_metrics)
            prev_waste = sum(m.food_waste_kg for m in prev_metrics)

            if prev_carbon > 0:
                vs_previous["carbon_change"] = float((total_carbon - prev_carbon) / prev_carbon * 100)
            if prev_waste > 0:
                vs_previous["waste_change"] = float((total_waste - prev_waste) / prev_waste * 100)

        # Recommendations
        recommendations = []
        if diversion_rate < 50:
            recommendations.append("Increase food donation and composting programs")
        if local_avg < 30:
            recommendations.append("Source more ingredients from local suppliers")
        if total_landfill > total_waste * Decimal("0.3"):
            recommendations.append("Reduce landfill waste through better sorting")

        return {
            "carbon_footprint": {
                "total": float(total_carbon),
                "daily_avg": float(total_carbon / len(metrics)) if metrics else 0,
            },
            "waste_metrics": {
                "total": float(total_waste),
                "donated": float(total_donated),
                "composted": float(total_composted),
                "landfill": float(total_landfill),
                "diversion_rate": diversion_rate,
            },
            "sustainability_score": min(100, score),
            "vs_previous_period": vs_previous,
            "targets": {},
            "recommendations": recommendations or ["Keep up the good work!"],
        }
