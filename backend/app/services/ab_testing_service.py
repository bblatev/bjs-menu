"""
A/B Testing & Experimentation Service
Implements menu experiments, pricing tests, and feature flags
Competitor: Toast Menu A/B Testing, Square Menu Optimization
"""

import random
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import Session

from app.models.gap_features_models import (
    ABExperiment, ExperimentAssignment, ExperimentStatus
)


class ABTestingService:
    """
    Service for A/B testing menu items, pricing, and features.
    Uses consistent hashing for user assignment.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== EXPERIMENT MANAGEMENT ====================

    async def create_experiment(
        self,
        venue_id: UUID,
        name: str,
        description: str,
        experiment_type: str,  # 'menu_item', 'pricing', 'promotion', 'feature', 'upsell'
        variants: List[Dict[str, Any]],
        target_metric: str,  # 'conversion_rate', 'avg_order_value', 'item_sales', 'revenue'
        traffic_percentage: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        created_by: Optional[UUID] = None
    ) -> ABExperiment:
        """Create a new A/B experiment."""
        # Validate variants
        total_weight = sum(v.get("weight", 50) for v in variants)
        if total_weight != 100:
            raise ValueError("Variant weights must sum to 100")

        experiment = ABExperiment(
            id=uuid4(),
            venue_id=venue_id,
            name=name,
            description=description,
            experiment_type=experiment_type,
            variants=variants,
            target_metric=target_metric,
            traffic_percentage=traffic_percentage,
            status=ExperimentStatus.DRAFT,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    async def start_experiment(self, experiment_id: UUID) -> ABExperiment:
        """Start an experiment."""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError("Experiment not found")

        if experiment.status != ExperimentStatus.DRAFT:
            raise ValueError(f"Cannot start experiment with status {experiment.status}")

        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    async def pause_experiment(self, experiment_id: UUID) -> ABExperiment:
        """Pause a running experiment."""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError("Experiment not found")

        if experiment.status != ExperimentStatus.RUNNING:
            raise ValueError("Can only pause running experiments")

        experiment.status = ExperimentStatus.PAUSED
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    async def resume_experiment(self, experiment_id: UUID) -> ABExperiment:
        """Resume a paused experiment."""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError("Experiment not found")

        if experiment.status != ExperimentStatus.PAUSED:
            raise ValueError("Can only resume paused experiments")

        experiment.status = ExperimentStatus.RUNNING
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    async def complete_experiment(
        self,
        experiment_id: UUID,
        winner_variant: Optional[str] = None
    ) -> ABExperiment:
        """Complete an experiment and optionally declare a winner."""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError("Experiment not found")

        experiment.status = ExperimentStatus.COMPLETED
        experiment.ended_at = datetime.now(timezone.utc)
        experiment.winner_variant = winner_variant
        self.db.commit()
        self.db.refresh(experiment)
        return experiment

    async def get_experiment(self, experiment_id: UUID) -> Optional[ABExperiment]:
        """Get experiment by ID."""
        result = self.db.execute(
            select(ABExperiment).where(ABExperiment.id == experiment_id)
        )
        return result.scalar_one_or_none()

    async def list_experiments(
        self,
        venue_id: UUID,
        status: Optional[str] = None,
        experiment_type: Optional[str] = None
    ) -> List[ABExperiment]:
        """List experiments for a venue."""
        query = select(ABExperiment).where(ABExperiment.venue_id == venue_id)

        if status:
            query = query.where(ABExperiment.status == ExperimentStatus(status))
        if experiment_type:
            query = query.where(ABExperiment.experiment_type == experiment_type)

        query = query.order_by(desc(ABExperiment.created_at))

        result = self.db.execute(query)
        return list(result.scalars().all())

    # ==================== USER ASSIGNMENT ====================

    async def get_user_variant(
        self,
        experiment_id: UUID,
        user_id: str,  # Can be customer_id, session_id, or order_id
        user_type: str = "customer"  # 'customer', 'session', 'order'
    ) -> Optional[Dict[str, Any]]:
        """
        Get the variant assigned to a user for an experiment.
        Uses consistent hashing for deterministic assignment.
        """
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            return None

        if experiment.status != ExperimentStatus.RUNNING:
            return None

        # Check traffic percentage
        hash_value = self._get_hash_value(f"{experiment_id}:{user_id}")
        if (hash_value % 100) >= experiment.traffic_percentage:
            return None  # User not in experiment

        # Check for existing assignment
        result = self.db.execute(
            select(ExperimentAssignment).where(
                and_(
                    ExperimentAssignment.experiment_id == experiment_id,
                    ExperimentAssignment.user_id == user_id
                )
            )
        )
        assignment = result.scalar_one_or_none()

        if assignment:
            # Return existing variant
            for variant in experiment.variants:
                if variant.get("id") == assignment.variant_id:
                    return variant
            return None

        # Assign new variant based on consistent hash
        variant = self._select_variant(experiment.variants, user_id, str(experiment_id))

        # Record assignment
        new_assignment = ExperimentAssignment(
            id=uuid4(),
            experiment_id=experiment_id,
            user_id=user_id,
            user_type=user_type,
            variant_id=variant.get("id"),
            assigned_at=datetime.now(timezone.utc)
        )
        self.db.add(new_assignment)
        self.db.commit()

        return variant

    def _get_hash_value(self, key: str) -> int:
        """Get a consistent hash value for a key."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def _select_variant(
        self,
        variants: List[Dict[str, Any]],
        user_id: str,
        salt: str
    ) -> Dict[str, Any]:
        """Select a variant using weighted consistent hashing."""
        hash_value = self._get_hash_value(f"{salt}:{user_id}")
        normalized = hash_value % 100

        cumulative = 0
        for variant in variants:
            cumulative += variant.get("weight", 50)
            if normalized < cumulative:
                return variant

        return variants[-1]

    # ==================== METRICS & ANALYSIS ====================

    async def record_conversion(
        self,
        experiment_id: UUID,
        user_id: str,
        metric_name: str,
        metric_value: float,
        order_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record a conversion event for an experiment."""
        # Get assignment
        result = self.db.execute(
            select(ExperimentAssignment).where(
                and_(
                    ExperimentAssignment.experiment_id == experiment_id,
                    ExperimentAssignment.user_id == user_id
                )
            )
        )
        assignment = result.scalar_one_or_none()

        if not assignment:
            return False

        assignment.converted = True
        assignment.converted_at = datetime.now(timezone.utc)
        assignment.conversion_value = metric_value
        assignment.conversion_metadata = metadata or {}

        self.db.commit()
        return True

    async def get_experiment_results(
        self,
        experiment_id: UUID
    ) -> Dict[str, Any]:
        """Get statistical results for an experiment."""
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError("Experiment not found")

        results = {
            "experiment_id": str(experiment_id),
            "experiment_name": experiment.name,
            "status": experiment.status.value,
            "target_metric": experiment.target_metric,
            "variants": [],
            "statistical_significance": False,
            "winner": experiment.winner_variant,
            "started_at": experiment.started_at.isoformat() if experiment.started_at else None,
            "ended_at": experiment.ended_at.isoformat() if experiment.ended_at else None
        }

        for variant in experiment.variants:
            variant_id = variant.get("id")

            # Get assignment stats
            result = self.db.execute(
                select(
                    func.count(ExperimentAssignment.id).label("total"),
                    func.sum(
                        func.cast(ExperimentAssignment.converted, func.Integer)
                    ).label("conversions"),
                    func.avg(ExperimentAssignment.conversion_value).label("avg_value"),
                    func.sum(ExperimentAssignment.conversion_value).label("total_value")
                ).where(
                    and_(
                        ExperimentAssignment.experiment_id == experiment_id,
                        ExperimentAssignment.variant_id == variant_id
                    )
                )
            )
            row = result.one()

            total = row.total or 0
            conversions = row.conversions or 0
            avg_value = float(row.avg_value or 0)
            total_value = float(row.total_value or 0)

            conversion_rate = (conversions / total * 100) if total > 0 else 0

            results["variants"].append({
                "id": variant_id,
                "name": variant.get("name"),
                "weight": variant.get("weight"),
                "participants": total,
                "conversions": conversions,
                "conversion_rate": round(conversion_rate, 2),
                "avg_conversion_value": round(avg_value, 2),
                "total_value": round(total_value, 2)
            })

        # Calculate statistical significance
        if len(results["variants"]) >= 2:
            results["statistical_significance"] = self._calculate_significance(
                results["variants"]
            )

        return results

    def _calculate_significance(
        self,
        variants: List[Dict[str, Any]]
    ) -> bool:
        """
        Calculate if results are statistically significant.
        Uses Z-test for proportions.
        """
        if len(variants) < 2:
            return False

        # Get control and treatment
        control = variants[0]
        treatment = variants[1]

        n1 = control["participants"]
        n2 = treatment["participants"]

        if n1 < 100 or n2 < 100:
            return False  # Not enough samples

        p1 = control["conversion_rate"] / 100
        p2 = treatment["conversion_rate"] / 100

        # Pooled probability
        p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)

        if p_pool == 0 or p_pool == 1:
            return False

        # Standard error
        se = (p_pool * (1 - p_pool) * (1/n1 + 1/n2)) ** 0.5

        if se == 0:
            return False

        # Z-score
        z = abs(p2 - p1) / se

        # 95% confidence level = z > 1.96
        return z > 1.96


class ReviewAutomationService:
    """
    Service for automating review collection and reputation management.
    Competitor: Toast Reputation, Popmenu Reviews
    """

    def __init__(self, db: Session):
        self.db = db

    async def create_review_link(
        self,
        venue_id: UUID,
        platform: str,  # 'google', 'yelp', 'tripadvisor', 'facebook'
        link_url: str
    ) -> Dict[str, Any]:
        """Create a review link for a platform."""
        from app.models.gap_features_models import ReviewLink

        # Check if link already exists
        result = self.db.execute(
            select(ReviewLink).where(
                and_(
                    ReviewLink.venue_id == venue_id,
                    ReviewLink.platform == platform
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.link_url = link_url
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            return {
                "id": str(existing.id),
                "platform": platform,
                "link_url": link_url
            }

        link = ReviewLink(
            id=uuid4(),
            venue_id=venue_id,
            platform=platform,
            link_url=link_url,
            click_count=0,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(link)
        self.db.commit()

        return {
            "id": str(link.id),
            "platform": platform,
            "link_url": link_url
        }

    async def get_review_links(
        self,
        venue_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get all review links for a venue."""
        from app.models.gap_features_models import ReviewLink

        result = self.db.execute(
            select(ReviewLink).where(ReviewLink.venue_id == venue_id)
        )
        links = result.scalars().all()

        return [
            {
                "id": str(l.id),
                "platform": l.platform,
                "link_url": l.link_url,
                "click_count": l.click_count
            }
            for l in links
        ]

    async def send_review_request(
        self,
        venue_id: UUID,
        order_id: UUID,
        customer_id: UUID,
        method: str = "email",  # 'email', 'sms', 'both'
        delay_hours: int = 2
    ) -> Dict[str, Any]:
        """Send a review request to a customer."""
        from app.models.gap_features_models import ReviewRequest

        # Check if request already sent for this order
        result = self.db.execute(
            select(ReviewRequest).where(
                and_(
                    ReviewRequest.order_id == order_id,
                    ReviewRequest.customer_id == customer_id
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return {
                "id": str(existing.id),
                "status": "already_sent",
                "sent_at": existing.sent_at.isoformat() if existing.sent_at else None
            }

        # Create review request
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=delay_hours)

        request = ReviewRequest(
            id=uuid4(),
            venue_id=venue_id,
            order_id=order_id,
            customer_id=customer_id,
            method=method,
            status="scheduled",
            scheduled_at=scheduled_at,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(request)
        self.db.commit()

        return {
            "id": str(request.id),
            "status": "scheduled",
            "scheduled_at": scheduled_at.isoformat()
        }

    async def process_pending_requests(
        self,
        venue_id: UUID
    ) -> Dict[str, Any]:
        """Process pending review requests that are due."""
        from app.models.gap_features_models import ReviewRequest

        now = datetime.now(timezone.utc)

        result = self.db.execute(
            select(ReviewRequest).where(
                and_(
                    ReviewRequest.venue_id == venue_id,
                    ReviewRequest.status == "scheduled",
                    ReviewRequest.scheduled_at <= now
                )
            )
        )
        requests = result.scalars().all()

        sent = 0
        failed = 0

        for request in requests:
            try:
                # Get customer info
                customer = await self._get_customer(request.customer_id)
                if not customer:
                    request.status = "failed"
                    request.error_message = "Customer not found"
                    failed += 1
                    continue

                # Get review links
                links = await self.get_review_links(venue_id)
                if not links:
                    request.status = "failed"
                    request.error_message = "No review links configured"
                    failed += 1
                    continue

                # Send based on method
                if request.method in ["email", "both"]:
                    if customer.get("email"):
                        await self._send_review_email(
                            customer["email"],
                            customer.get("name", "Valued Customer"),
                            links
                        )

                if request.method in ["sms", "both"]:
                    if customer.get("phone"):
                        await self._send_review_sms(
                            customer["phone"],
                            links
                        )

                request.status = "sent"
                request.sent_at = now
                sent += 1

            except Exception as e:
                request.status = "failed"
                request.error_message = str(e)
                failed += 1

        self.db.commit()

        return {
            "processed": sent + failed,
            "sent": sent,
            "failed": failed
        }

    async def _get_customer(self, customer_id: UUID) -> Optional[Dict[str, Any]]:
        """Get customer info."""
        from app.models.customers import Customer

        result = self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            return None

        return {
            "id": str(customer.id),
            "name": customer.name,
            "email": getattr(customer, 'email', None),
            "phone": getattr(customer, 'phone', None)
        }

    async def _send_review_email(
        self,
        email: str,
        name: str,
        links: List[Dict[str, Any]]
    ) -> None:
        """Send review request email."""
        # This would integrate with email service
        pass

    async def _send_review_sms(
        self,
        phone: str,
        links: List[Dict[str, Any]]
    ) -> None:
        """Send review request SMS."""
        # This would integrate with SMS service
        pass

    async def track_link_click(
        self,
        link_id: UUID
    ) -> bool:
        """Track a review link click."""
        from app.models.gap_features_models import ReviewLink

        result = self.db.execute(
            select(ReviewLink).where(ReviewLink.id == link_id)
        )
        link = result.scalar_one_or_none()

        if link:
            link.click_count = (link.click_count or 0) + 1
            link.last_clicked_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        return False

    async def get_review_analytics(
        self,
        venue_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get review request analytics."""
        from app.models.gap_features_models import ReviewRequest
        from sqlalchemy import case, Integer

        result = self.db.execute(
            select(
                func.count(ReviewRequest.id).label("total"),
                func.sum(
                    case((ReviewRequest.status == "sent", 1), else_=0)
                ).label("sent"),
                func.sum(
                    case((ReviewRequest.status == "failed", 1), else_=0)
                ).label("failed")
            ).where(
                and_(
                    ReviewRequest.venue_id == venue_id,
                    ReviewRequest.created_at >= start_date,
                    ReviewRequest.created_at <= end_date
                )
            )
        )
        row = result.one()

        # Get link clicks
        from app.models.gap_features_models import ReviewLink
        result = self.db.execute(
            select(
                ReviewLink.platform,
                func.sum(ReviewLink.click_count).label("clicks")
            ).where(
                ReviewLink.venue_id == venue_id
            ).group_by(ReviewLink.platform)
        )
        clicks_by_platform = {r.platform: r.clicks for r in result.all()}

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "requests": {
                "total": row.total or 0,
                "sent": row.sent or 0,
                "failed": row.failed or 0
            },
            "clicks_by_platform": clicks_by_platform
        }
