"""Multi-Provider Delivery Dispatch Service - Smart routing."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import DeliveryProvider, DeliveryDispatch


class DeliveryDispatchService:
    """Service for smart multi-provider delivery dispatch."""

    def __init__(self, db: Session):
        self.db = db

    def create_provider(
        self,
        location_id: int,
        provider_name: str,
        base_fee: Decimal = Decimal("0"),
        per_mile_fee: Decimal = Decimal("0"),
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        merchant_id: Optional[str] = None,
        commission_percent: Optional[float] = None,
        priority_rank: int = 1,
    ) -> DeliveryProvider:
        """Create a delivery provider configuration."""
        provider = DeliveryProvider(
            location_id=location_id,
            provider_name=provider_name,
            api_key=api_key,
            api_secret=api_secret,
            merchant_id=merchant_id,
            base_fee=base_fee,
            per_mile_fee=per_mile_fee,
            commission_percent=commission_percent,
            priority_rank=priority_rank,
            is_active=True,
        )
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)
        return provider

    def get_providers(
        self,
        location_id: int,
        active_only: bool = True,
    ) -> List[DeliveryProvider]:
        """Get delivery providers for a location."""
        query = select(DeliveryProvider).where(
            DeliveryProvider.location_id == location_id
        )

        if active_only:
            query = query.where(DeliveryProvider.is_active == True)

        query = query.order_by(DeliveryProvider.priority_rank)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_quotes(
        self,
        location_id: int,
        delivery_address: str,
        distance_miles: float,
    ) -> List[Dict[str, Any]]:
        """Get delivery quotes from all active providers."""
        providers = self.get_providers(location_id)
        quotes = []

        for provider in providers:
            # Calculate fee
            fee = provider.base_fee + (provider.per_mile_fee * Decimal(str(distance_miles)))

            # Estimate ETA based on historical data or default
            eta = provider.avg_delivery_time_minutes or (15 + distance_miles * 5)

            quotes.append({
                "provider_id": provider.id,
                "provider_name": provider.provider_name,
                "estimated_fee": float(fee),
                "estimated_eta_minutes": int(eta),
                "availability": True,  # Would check actual availability via API
                "reliability_score": provider.reliability_score or 0.9,
            })

        return sorted(quotes, key=lambda x: x["estimated_fee"])

    def dispatch_order(
        self,
        order_id: int,
        location_id: int,
        delivery_address: str,
        distance_miles: float = 3.0,
        strategy: str = "cost_optimal",
        preferred_provider_id: Optional[int] = None,
    ) -> DeliveryDispatch:
        """Dispatch an order to a delivery provider."""
        quotes = self.get_quotes(location_id, delivery_address, distance_miles)

        if not quotes:
            raise ValueError("No delivery providers available")

        # Select provider based on strategy
        selected_quote = None

        if preferred_provider_id:
            for q in quotes:
                if q["provider_id"] == preferred_provider_id:
                    selected_quote = q
                    break

        if not selected_quote:
            if strategy == "cost_optimal":
                selected_quote = min(quotes, key=lambda x: x["estimated_fee"])
            elif strategy == "fastest":
                selected_quote = min(quotes, key=lambda x: x["estimated_eta_minutes"])
            elif strategy == "reliability":
                selected_quote = max(quotes, key=lambda x: x.get("reliability_score", 0))
            else:
                # Load balancing - rotate through providers
                selected_quote = quotes[0]

        dispatch = DeliveryDispatch(
            order_id=order_id,
            location_id=location_id,
            selected_provider_id=selected_quote["provider_id"],
            dispatch_reason=strategy,
            provider_quotes={q["provider_name"]: {"fee": q["estimated_fee"], "eta": q["estimated_eta_minutes"]} for q in quotes},
            quoted_fee=Decimal(str(selected_quote["estimated_fee"])),
            dispatched_at=datetime.utcnow(),
        )
        self.db.add(dispatch)
        self.db.commit()
        self.db.refresh(dispatch)
        return dispatch

    def update_dispatch_status(
        self,
        dispatch_id: int,
        driver_assigned_at: Optional[datetime] = None,
        picked_up_at: Optional[datetime] = None,
        delivered_at: Optional[datetime] = None,
        actual_fee: Optional[Decimal] = None,
    ) -> DeliveryDispatch:
        """Update dispatch status with tracking events."""
        dispatch = self.db.get(DeliveryDispatch, dispatch_id)
        if not dispatch:
            raise ValueError(f"Dispatch {dispatch_id} not found")

        if driver_assigned_at:
            dispatch.driver_assigned_at = driver_assigned_at
        if picked_up_at:
            dispatch.picked_up_at = picked_up_at
        if delivered_at:
            dispatch.delivered_at = delivered_at
        if actual_fee is not None:
            dispatch.actual_fee = actual_fee

        self.db.commit()
        self.db.refresh(dispatch)

        # Update provider metrics if delivered
        if delivered_at and dispatch.dispatched_at:
            delivery_time = (delivered_at - dispatch.dispatched_at).total_seconds() / 60
            self._update_provider_metrics(
                dispatch.selected_provider_id,
                delivery_time,
            )

        return dispatch

    def _update_provider_metrics(
        self,
        provider_id: int,
        delivery_time_minutes: float,
    ) -> None:
        """Update provider performance metrics."""
        provider = self.db.get(DeliveryProvider, provider_id)
        if not provider:
            return

        # Rolling average
        current_avg = provider.avg_delivery_time_minutes or delivery_time_minutes
        provider.avg_delivery_time_minutes = (current_avg * 0.9) + (delivery_time_minutes * 0.1)

        self.db.commit()

    def get_dispatch(
        self,
        order_id: int,
    ) -> Optional[DeliveryDispatch]:
        """Get dispatch for an order."""
        query = select(DeliveryDispatch).where(DeliveryDispatch.order_id == order_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def get_dispatches(
        self,
        location_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[DeliveryDispatch]:
        """Get dispatches for a location."""
        query = select(DeliveryDispatch).where(
            DeliveryDispatch.location_id == location_id
        )

        if start_date:
            query = query.where(DeliveryDispatch.dispatched_at >= start_date)
        if end_date:
            query = query.where(DeliveryDispatch.dispatched_at <= end_date)

        query = query.order_by(DeliveryDispatch.dispatched_at.desc()).limit(limit)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_stats(
        self,
        location_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get delivery dispatch statistics."""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Overall stats
        query = select(
            func.count(DeliveryDispatch.id).label("total_dispatches"),
            func.sum(DeliveryDispatch.quoted_fee).label("total_quoted"),
            func.sum(DeliveryDispatch.actual_fee).label("total_actual"),
        ).where(
            and_(
                DeliveryDispatch.location_id == location_id,
                DeliveryDispatch.dispatched_at >= start_date,
            )
        )

        result = self.db.execute(query)
        stats = result.first()

        # By provider
        provider_query = select(
            DeliveryDispatch.selected_provider_id,
            func.count(DeliveryDispatch.id).label("count"),
            func.sum(DeliveryDispatch.actual_fee).label("total_fees"),
        ).where(
            and_(
                DeliveryDispatch.location_id == location_id,
                DeliveryDispatch.dispatched_at >= start_date,
            )
        ).group_by(DeliveryDispatch.selected_provider_id)

        provider_result = self.db.execute(provider_query)
        by_provider = {
            row.selected_provider_id: {
                "count": row.count,
                "total_fees": float(row.total_fees or 0),
            }
            for row in provider_result.all()
        }

        return {
            "period_days": days,
            "total_dispatches": stats.total_dispatches or 0,
            "total_quoted_fees": float(stats.total_quoted or 0),
            "total_actual_fees": float(stats.total_actual or 0),
            "by_provider": by_provider,
        }

    def update_provider(
        self,
        provider_id: int,
        **updates,
    ) -> DeliveryProvider:
        """Update provider configuration."""
        provider = self.db.get(DeliveryProvider, provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        for key, value in updates.items():
            if hasattr(provider, key):
                setattr(provider, key, value)

        self.db.commit()
        self.db.refresh(provider)
        return provider
