"""Vendor Scorecard Service."""

from datetime import date
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import VendorScorecard


class VendorScorecardService:
    """Service for vendor performance scorecards."""

    def __init__(self, db: Session):
        self.db = db

    def create_scorecard(
        self,
        supplier_id: int,
        period_start: date,
        period_end: date,
        quality_score: float,
        defect_rate: float,
        on_time_delivery_rate: float,
        fill_rate: float,
        avg_lead_time_days: float,
        price_competitiveness: float,
        price_stability: float,
        responsiveness_score: float,
        issue_resolution_time_hours: Optional[float] = None,
        food_safety_score: Optional[float] = None,
        certifications_valid: bool = True,
    ) -> VendorScorecard:
        """Create a vendor scorecard."""
        # Calculate overall score (weighted average)
        weights = {
            "quality": 0.25,
            "delivery": 0.20,
            "fill_rate": 0.15,
            "price": 0.15,
            "responsiveness": 0.15,
            "food_safety": 0.10,
        }

        overall = (
            quality_score * weights["quality"] +
            on_time_delivery_rate * weights["delivery"] +
            fill_rate * weights["fill_rate"] +
            price_competitiveness * weights["price"] +
            responsiveness_score * weights["responsiveness"] +
            (food_safety_score or 80) * weights["food_safety"]
        )

        # Determine tier
        if overall >= 90 and certifications_valid:
            tier = "preferred"
        elif overall >= 75:
            tier = "approved"
        elif overall >= 60:
            tier = "probation"
        else:
            tier = "suspended"

        scorecard = VendorScorecard(
            supplier_id=supplier_id,
            period_start=period_start,
            period_end=period_end,
            quality_score=quality_score,
            defect_rate=defect_rate,
            on_time_delivery_rate=on_time_delivery_rate,
            fill_rate=fill_rate,
            avg_lead_time_days=avg_lead_time_days,
            price_competitiveness=price_competitiveness,
            price_stability=price_stability,
            responsiveness_score=responsiveness_score,
            issue_resolution_time_hours=issue_resolution_time_hours,
            food_safety_score=food_safety_score,
            certifications_valid=certifications_valid,
            overall_score=overall,
            tier=tier,
        )
        self.db.add(scorecard)
        self.db.commit()
        self.db.refresh(scorecard)
        return scorecard

    def get_scorecard(
        self,
        supplier_id: int,
        period_start: Optional[date] = None,
    ) -> Optional[VendorScorecard]:
        """Get the latest scorecard for a supplier."""
        query = select(VendorScorecard).where(
            VendorScorecard.supplier_id == supplier_id
        )

        if period_start:
            query = query.where(VendorScorecard.period_start == period_start)

        query = query.order_by(VendorScorecard.period_end.desc()).limit(1)

        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_scorecards(
        self,
        supplier_id: Optional[int] = None,
        tier: Optional[str] = None,
    ) -> List[VendorScorecard]:
        """Get scorecards with filters."""
        query = select(VendorScorecard)

        if supplier_id:
            query = query.where(VendorScorecard.supplier_id == supplier_id)
        if tier:
            query = query.where(VendorScorecard.tier == tier)

        query = query.order_by(VendorScorecard.period_end.desc())

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_scorecard_history(
        self,
        supplier_id: int,
        periods: int = 4,
    ) -> List[VendorScorecard]:
        """Get scorecard history for a supplier."""
        query = select(VendorScorecard).where(
            VendorScorecard.supplier_id == supplier_id
        ).order_by(VendorScorecard.period_end.desc()).limit(periods)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def compare_vendors(
        self,
        supplier_ids: List[int],
    ) -> Dict[str, Any]:
        """Compare multiple vendors."""
        scorecards = []
        for supplier_id in supplier_ids:
            scorecard = self.get_scorecard(supplier_id)
            if scorecard:
                scorecards.append(scorecard)

        if not scorecards:
            return {
                "vendors": [],
                "category_averages": {},
                "top_performer": None,
                "at_risk_vendors": [],
            }

        # Calculate averages
        metrics = [
            "quality_score", "on_time_delivery_rate", "fill_rate",
            "price_competitiveness", "responsiveness_score", "overall_score"
        ]

        averages = {}
        for metric in metrics:
            values = [getattr(s, metric) for s in scorecards if getattr(s, metric) is not None]
            averages[metric] = sum(values) / len(values) if values else 0

        # Find top performer
        top = max(scorecards, key=lambda s: s.overall_score)

        # Find at-risk vendors
        at_risk = [s.supplier_id for s in scorecards if s.tier in ["probation", "suspended"]]

        return {
            "vendors": scorecards,
            "category_averages": averages,
            "top_performer": top.supplier_id,
            "at_risk_vendors": at_risk,
        }

    def get_tier_summary(
        self,
    ) -> Dict[str, int]:
        """Get count of vendors by tier."""
        # Get most recent scorecard for each supplier
        subquery = (
            select(
                VendorScorecard.supplier_id,
                VendorScorecard.tier,
            )
            .distinct(VendorScorecard.supplier_id)
            .order_by(VendorScorecard.supplier_id, VendorScorecard.period_end.desc())
        ).subquery()

        # This is a simplified version - would need window functions for proper implementation
        query = select(VendorScorecard).order_by(VendorScorecard.period_end.desc())
        result = self.db.execute(query)
        scorecards = list(result.scalars().all())

        # Get latest per supplier
        latest_by_supplier = {}
        for sc in scorecards:
            if sc.supplier_id not in latest_by_supplier:
                latest_by_supplier[sc.supplier_id] = sc

        tiers = {"preferred": 0, "approved": 0, "probation": 0, "suspended": 0}
        for sc in latest_by_supplier.values():
            if sc.tier in tiers:
                tiers[sc.tier] += 1

        return tiers

    def generate_improvement_plan(
        self,
        supplier_id: int,
    ) -> Dict[str, Any]:
        """Generate improvement recommendations for a vendor."""
        scorecard = self.get_scorecard(supplier_id)
        if not scorecard:
            raise ValueError(f"No scorecard found for supplier {supplier_id}")

        recommendations = []
        priority_areas = []

        if scorecard.quality_score < 80:
            priority_areas.append("quality")
            recommendations.append("Implement stricter quality control measures")
            recommendations.append("Request quality certifications and audit reports")

        if scorecard.on_time_delivery_rate < 90:
            priority_areas.append("delivery")
            recommendations.append("Review delivery logistics and backup plans")
            recommendations.append("Consider safety stock agreements")

        if scorecard.fill_rate < 95:
            priority_areas.append("fill_rate")
            recommendations.append("Improve inventory management communication")
            recommendations.append("Set up automatic low-stock alerts")

        if scorecard.price_competitiveness < 70:
            priority_areas.append("pricing")
            recommendations.append("Renegotiate pricing terms")
            recommendations.append("Explore volume discount opportunities")

        if scorecard.responsiveness_score < 75:
            priority_areas.append("responsiveness")
            recommendations.append("Establish dedicated account management")
            recommendations.append("Set up SLA for response times")

        if not scorecard.certifications_valid:
            recommendations.append("URGENT: Obtain valid food safety certifications")

        return {
            "supplier_id": supplier_id,
            "current_tier": scorecard.tier,
            "overall_score": scorecard.overall_score,
            "priority_areas": priority_areas,
            "recommendations": recommendations,
            "target_tier": "approved" if scorecard.tier == "probation" else "preferred",
        }
