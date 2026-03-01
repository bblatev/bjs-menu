"""V5 sub-module: Benchmarking & Reservation Deposits"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from datetime import datetime, date, timezone, time, timedelta
from decimal import Decimal
from pydantic import BaseModel
import secrets

from app.db.session import get_db
from app.models import (
    MarketingCampaign, Customer, Order, MenuItem, StaffUser, OrderItem,
    Reservation, ReservationDeposit, DepositStatus, VenueSettings,
    Promotion, PromotionUsage, Table, StaffShift
)
from app.models.missing_features_models import (
    CateringEvent, CateringEventStatus, CateringOrderItem, CateringInvoice,
    CustomerReferral, VIPTier, CustomerVIPStatus, GuestbookEntry,
    Chargeback, ChargebackStatus, TaxReport, MenuPairing,
    CustomerDisplay, CustomerDisplayContent, FundraisingCampaign, FundraisingDonation,
    TableBlock, EmployeeBreak,
    ShiftTradeRequest as ShiftTradeRequestModel, EmployeeOnboarding,
    OnboardingChecklist, OnboardingTask, OnboardingTaskCompletion,
    IngredientPriceHistory, PriceAlertNotification, MenuItemReview,
    PrepTimePrediction
)
from app.models.operations import ReferralProgram
from app.models.invoice import PriceAlert
from app.models.core_business_models import SMSMessage
from app.models import StockItem
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from app.core.rate_limit import limiter
from app.api.routes.v5_endpoints._schemas import *

router = APIRouter()

# ==================== BENCHMARKING ====================

# Industry benchmark constants (these would typically come from external data sources)
INDUSTRY_BENCHMARKS = {
    "avg_ticket": 45.00,  # Industry average ticket in BGN
    "table_turn_time": 55,  # Industry average table turn time in minutes
    "labor_cost_pct": 32,  # Industry average labor cost percentage
    "items_per_order": 3.2,  # Industry average items per order
    "order_completion_rate": 95,  # Industry average order completion rate %
}


def _get_period_date_range(period: str) -> tuple:
    """Calculate date range based on period type"""
    today = date.today()
    if period == "week":
        start_date = today - relativedelta(weeks=1)
    elif period == "month":
        start_date = today.replace(day=1)
    elif period == "quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=quarter_start_month, day=1)
    elif period == "year":
        start_date = today.replace(month=1, day=1)
    else:
        start_date = today - relativedelta(months=1)
    return start_date, today


def _calculate_percentile(venue_value: float, industry_avg: float, higher_is_better: bool = True) -> int:
    """Calculate approximate percentile based on venue vs industry average"""
    if industry_avg == 0:
        return 50
    ratio = venue_value / industry_avg
    if higher_is_better:
        # If venue is 20% above industry, roughly 70th percentile
        percentile = int(50 + (ratio - 1) * 100)
    else:
        # For metrics where lower is better (like turn time, labor cost)
        percentile = int(50 + (1 - ratio) * 100)
    return max(1, min(99, percentile))


@router.get("/benchmarking/summary")
@limiter.limit("60/minute")
async def get_benchmark_summary(
    request: Request,
    venue_id: int = Query(1),
    period: str = Query("month"),
    db: Session = Depends(get_db)
):
    """Get benchmark summary comparing to industry using real database metrics"""
    try:
        start_date, end_date = _get_period_date_range(period)

        # Calculate average ticket from orders
        avg_ticket_result = db.query(func.avg(Order.total)).filter(
            Order.venue_id == venue_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status != "cancelled"
        ).scalar()
        avg_ticket = float(avg_ticket_result) if avg_ticket_result else 0.0

        # If no data at all, return empty-state response
        if avg_ticket == 0.0:
            order_count = db.query(func.count(Order.id)).filter(
                Order.venue_id == venue_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date,
            ).scalar() or 0
            if order_count == 0:
                return {
                    "venue_id": venue_id,
                    "period": period,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "overall_score": 0,
                    "metrics": [],
                    "message": "No data available for the selected period"
                }

        # Calculate average table turn time (time from order creation to payment)
        turn_time_result = db.query(
            func.avg(
                func.extract('epoch', Order.payment_date) - func.extract('epoch', Order.created_at)
            ) / 60  # Convert to minutes
        ).filter(
            Order.venue_id == venue_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.payment_date.isnot(None),
            Order.order_type == "dine-in"
        ).scalar()
        table_turn_time = float(turn_time_result) if turn_time_result else 0.0

        # Calculate labor cost percentage
        total_revenue = float(db.query(func.sum(Order.total)).filter(
            Order.venue_id == venue_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status != "cancelled"
        ).scalar() or 0)

        active_staff_count = db.query(func.count(StaffUser.id)).filter(
            StaffUser.location_id == venue_id,
            StaffUser.is_active == True
        ).scalar() or 0

        days_in_period = (end_date - start_date).days or 1
        estimated_labor_cost = active_staff_count * 8 * days_in_period * 15
        labor_cost_pct = (estimated_labor_cost / total_revenue * 100) if total_revenue > 0 else 0

        # Build metrics comparison
        metrics = [
            {
                "metric": "avg_ticket",
                "venue": round(avg_ticket, 2),
                "industry_avg": INDUSTRY_BENCHMARKS["avg_ticket"],
                "percentile": _calculate_percentile(avg_ticket, INDUSTRY_BENCHMARKS["avg_ticket"], higher_is_better=True)
            },
            {
                "metric": "table_turn_time",
                "venue": round(table_turn_time, 0),
                "industry_avg": INDUSTRY_BENCHMARKS["table_turn_time"],
                "percentile": _calculate_percentile(table_turn_time, INDUSTRY_BENCHMARKS["table_turn_time"], higher_is_better=False)
            },
            {
                "metric": "labor_cost_pct",
                "venue": round(labor_cost_pct, 1),
                "industry_avg": INDUSTRY_BENCHMARKS["labor_cost_pct"],
                "percentile": _calculate_percentile(labor_cost_pct, INDUSTRY_BENCHMARKS["labor_cost_pct"], higher_is_better=False)
            }
        ]

        # Calculate overall score (weighted average of percentiles)
        overall_score = sum(m["percentile"] for m in metrics) // len(metrics) if metrics else 0

        return {
            "venue_id": venue_id,
            "period": period,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "overall_score": overall_score,
            "metrics": metrics
        }
    except Exception as e:
        return {
            "venue_id": venue_id,
            "period": period,
            "overall_score": 0,
            "metrics": [],
            "error": str(e),
            "message": "Failed to compute benchmarks"
        }


@router.get("/benchmarking/peers")
@limiter.limit("60/minute")
async def get_peer_comparison(
    request: Request,
    venue_id: int = Query(1),
    comparison_group: str = Query("region"),
    db: Session = Depends(get_db)
):
    """Compare against peer group using real database metrics"""
    # Get all venues for peer comparison (in real implementation, would filter by region/type)
    # For now, comparing against all other venues in the system

    # Calculate metrics for all venues
    venue_metrics = db.query(
        Order.venue_id,
        func.avg(Order.total).label("avg_ticket"),
        func.count(Order.id).label("order_count"),
        func.sum(Order.total).label("total_revenue")
    ).filter(
        Order.status != "cancelled",
        Order.created_at >= date.today() - relativedelta(months=1)
    ).group_by(Order.venue_id).all()

    peer_count = len(venue_metrics)

    # Find current venue's metrics and rank
    venue_data = None
    venue_rank = 0
    sorted_by_revenue = sorted(venue_metrics, key=lambda x: x.total_revenue or 0, reverse=True)

    for idx, vm in enumerate(sorted_by_revenue, 1):
        if vm.venue_id == venue_id:
            venue_rank = idx
            venue_data = vm
            break

    # Calculate peer averages
    if venue_metrics:
        peer_avg_ticket = sum(v.avg_ticket or 0 for v in venue_metrics) / peer_count
        peer_avg_orders = sum(v.order_count or 0 for v in venue_metrics) / peer_count
        peer_avg_revenue = sum(v.total_revenue or 0 for v in venue_metrics) / peer_count
    else:
        peer_avg_ticket = 0
        peer_avg_orders = 0
        peer_avg_revenue = 0

    metrics = {
        "avg_ticket": {
            "venue": round(float(venue_data.avg_ticket), 2) if venue_data and venue_data.avg_ticket else 0,
            "peer_avg": round(peer_avg_ticket, 2)
        },
        "order_count": {
            "venue": venue_data.order_count if venue_data else 0,
            "peer_avg": round(peer_avg_orders, 0)
        },
        "total_revenue": {
            "venue": round(float(venue_data.total_revenue), 2) if venue_data and venue_data.total_revenue else 0,
            "peer_avg": round(peer_avg_revenue, 2)
        }
    }

    return {
        "venue_id": venue_id,
        "comparison_group": comparison_group,
        "peer_count": peer_count,
        "your_rank": venue_rank,
        "metrics": metrics
    }


@router.get("/benchmarking/trends/{metric}")
@limiter.limit("60/minute")
async def get_benchmark_trends(
    request: Request,
    metric: str,
    venue_id: int = Query(1),
    periods: int = Query(12),
    db: Session = Depends(get_db)
):
    """Get historical benchmark trends from real database data"""
    trends = []
    today = date.today()

    for i in range(periods - 1, -1, -1):
        period_date = today - relativedelta(months=i)
        period_start = period_date.replace(day=1)
        _, last_day = monthrange(period_date.year, period_date.month)
        period_end = period_date.replace(day=last_day)

        period_label = period_start.strftime("%Y-%m")

        if metric == "avg_ticket":
            value = db.query(func.avg(Order.total)).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end,
                Order.status != "cancelled"
            ).scalar()
            venue_value = round(float(value), 2) if value else 0
            industry_value = INDUSTRY_BENCHMARKS["avg_ticket"]

        elif metric == "order_count":
            value = db.query(func.count(Order.id)).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end,
                Order.status != "cancelled"
            ).scalar()
            venue_value = value or 0
            industry_value = 500  # Estimated industry average orders per month

        elif metric == "revenue":
            value = db.query(func.sum(Order.total)).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end,
                Order.status != "cancelled"
            ).scalar()
            venue_value = round(float(value), 2) if value else 0
            industry_value = 25000  # Estimated industry average revenue per month

        elif metric == "items_per_order":
            # Calculate average items per order
            subq = db.query(
                OrderItem.order_id,
                func.sum(OrderItem.quantity).label("total_items")
            ).join(Order).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end,
                Order.status != "cancelled"
            ).group_by(OrderItem.order_id).subquery()

            value = db.query(func.avg(subq.c.total_items)).scalar()
            venue_value = round(float(value), 2) if value else 0
            industry_value = INDUSTRY_BENCHMARKS["items_per_order"]

        elif metric == "top_item_sales":
            # Get total quantity of top selling item
            top_item = db.query(
                func.sum(OrderItem.quantity).label("qty")
            ).join(Order).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end,
                Order.status != "cancelled"
            ).group_by(OrderItem.menu_item_id).order_by(
                func.sum(OrderItem.quantity).desc()
            ).first()
            venue_value = top_item.qty if top_item else 0
            industry_value = 150  # Estimated industry average for top item

        else:
            # Default to order count for unknown metrics
            value = db.query(func.count(Order.id)).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end
            ).scalar()
            venue_value = value or 0
            industry_value = 500

        trends.append({
            "period": period_label,
            "venue": venue_value,
            "industry": industry_value
        })

    return {
        "metric": metric,
        "venue_id": venue_id,
        "trends": trends
    }


@router.get("/benchmarking/recommendations")
@limiter.limit("60/minute")
async def get_improvement_recommendations(
    request: Request,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get data-driven improvement recommendations based on actual performance"""
    recommendations = []
    start_date = date.today() - relativedelta(months=1)

    # Get current metrics
    avg_ticket = db.query(func.avg(Order.total)).filter(
        Order.venue_id == venue_id,
        Order.created_at >= start_date,
        Order.status != "cancelled"
    ).scalar() or 0

    # Get average items per order
    items_per_order_subq = db.query(
        OrderItem.order_id,
        func.sum(OrderItem.quantity).label("total_items")
    ).join(Order).filter(
        Order.venue_id == venue_id,
        Order.created_at >= start_date,
        Order.status != "cancelled"
    ).group_by(OrderItem.order_id).subquery()

    avg_items = db.query(func.avg(items_per_order_subq.c.total_items)).scalar() or 0

    # Get total orders count
    order_count = db.query(func.count(Order.id)).filter(
        Order.venue_id == venue_id,
        Order.created_at >= start_date,
        Order.status != "cancelled"
    ).scalar() or 0

    # Get top selling items
    top_items = db.query(
        MenuItem.id,
        func.sum(OrderItem.quantity).label("qty")
    ).join(OrderItem, MenuItem.id == OrderItem.menu_item_id).join(
        Order
    ).filter(
        Order.venue_id == venue_id,
        Order.created_at >= start_date,
        Order.status != "cancelled"
    ).group_by(MenuItem.id).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(5).all()

    # Generate recommendations based on metrics
    if float(avg_ticket) < INDUSTRY_BENCHMARKS["avg_ticket"]:
        gap = INDUSTRY_BENCHMARKS["avg_ticket"] - float(avg_ticket)
        recommendations.append({
            "metric": "avg_ticket",
            "current_value": round(float(avg_ticket), 2),
            "industry_avg": INDUSTRY_BENCHMARKS["avg_ticket"],
            "recommendation": "Implement upselling prompts for high-margin items",
            "potential_impact": f"{round(gap / float(avg_ticket) * 100 if avg_ticket else 0, 1)}% revenue increase per order"
        })

    if float(avg_items) < INDUSTRY_BENCHMARKS["items_per_order"]:
        recommendations.append({
            "metric": "items_per_order",
            "current_value": round(float(avg_items), 2),
            "industry_avg": INDUSTRY_BENCHMARKS["items_per_order"],
            "recommendation": "Add combo deals and bundle suggestions at checkout",
            "potential_impact": f"Increase items per order by {round(INDUSTRY_BENCHMARKS['items_per_order'] - float(avg_items), 1)}"
        })

    if order_count < 500:  # Below estimated industry average
        recommendations.append({
            "metric": "order_volume",
            "current_value": order_count,
            "industry_avg": 500,
            "recommendation": "Launch targeted marketing campaigns to increase foot traffic",
            "potential_impact": f"Potential to increase orders by {500 - order_count} per month"
        })

    # If venue is doing well, suggest maintenance recommendations
    if not recommendations:
        recommendations.append({
            "metric": "overall_performance",
            "current_value": "Above average",
            "industry_avg": "N/A",
            "recommendation": "Maintain current strategies and explore premium offerings",
            "potential_impact": "Sustain competitive advantage"
        })

    # Add top items analysis
    if top_items:
        recommendations.append({
            "metric": "menu_optimization",
            "current_value": f"Top 5 items: {len(top_items)} identified",
            "industry_avg": "N/A",
            "recommendation": "Focus promotion on top-selling items and consider expanding similar offerings",
            "potential_impact": "10-15% revenue optimization"
        })

    return {
        "venue_id": venue_id,
        "analysis_period": f"{start_date.isoformat()} to {date.today().isoformat()}",
        "recommendations": recommendations
    }

# ==================== RESERVATION DEPOSITS ====================

@router.post("/reservations/{reservation_id}/deposit")
@limiter.limit("30/minute")
async def create_deposit_request(
    request: Request,
    reservation_id: int,
    deposit: DepositRequest,
    db: Session = Depends(get_db)
):
    """Create deposit request for reservation"""
    # Verify reservation exists
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Generate unique payment link
    payment_token = secrets.token_urlsafe(16)
    payment_link = f"https://bjsbar.bg/pay/{payment_token}"

    # Create deposit record
    new_deposit = ReservationDeposit(
        venue_id=reservation.venue_id,
        reservation_id=reservation_id,
        amount=Decimal(str(deposit.amount)),
        currency=deposit.currency,
        status=DepositStatus.pending,
        payment_link=payment_link
    )

    db.add(new_deposit)
    db.commit()
    db.refresh(new_deposit)

    return {
        "id": new_deposit.id,
        "reservation_id": new_deposit.reservation_id,
        "amount": float(new_deposit.amount),
        "currency": new_deposit.currency,
        "status": new_deposit.status.value,
        "payment_link": new_deposit.payment_link,
        "created_at": new_deposit.created_at.isoformat() if new_deposit.created_at else None
    }


@router.get("/deposits/settings")
@limiter.limit("60/minute")
async def get_deposit_settings(
    request: Request,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get deposit settings for venue"""
    venue_settings = db.query(VenueSettings).filter(VenueSettings.venue_id == venue_id).first()

    default_settings = {
        "deposits_enabled": True,
        "default_amount": 50.00,
        "min_party_size": 6,
        "required_peak_hours": True,
        "peak_hours_start": "18:00",
        "peak_hours_end": "22:00",
        "weekend_required": True,
        "currency": "BGN"
    }

    if venue_settings and venue_settings.settings_data:
        deposit_settings = venue_settings.settings_data.get("deposit_settings", {})
        return {**default_settings, **deposit_settings, "venue_id": venue_id}

    return {**default_settings, "venue_id": venue_id}


@router.put("/deposits/settings")
@limiter.limit("30/minute")
async def update_deposit_settings(
    request: Request,
    venue_id: int = Query(1),
    deposits_enabled: Optional[bool] = Body(None),
    default_amount: Optional[float] = Body(None),
    min_party_size: Optional[int] = Body(None),
    required_peak_hours: Optional[bool] = Body(None),
    peak_hours_start: Optional[str] = Body(None),
    peak_hours_end: Optional[str] = Body(None),
    weekend_required: Optional[bool] = Body(None),
    currency: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Update deposit settings for venue"""
    venue_settings = db.query(VenueSettings).filter(VenueSettings.venue_id == venue_id).first()

    if not venue_settings:
        venue_settings = VenueSettings(venue_id=venue_id, settings_data={})
        db.add(venue_settings)

    current_settings = venue_settings.settings_data or {}
    deposit_settings = current_settings.get("deposit_settings", {
        "deposits_enabled": True,
        "default_amount": 50.00,
        "min_party_size": 6,
        "required_peak_hours": True,
        "peak_hours_start": "18:00",
        "peak_hours_end": "22:00",
        "weekend_required": True,
        "currency": "BGN"
    })

    if deposits_enabled is not None:
        deposit_settings["deposits_enabled"] = deposits_enabled
    if default_amount is not None:
        deposit_settings["default_amount"] = default_amount
    if min_party_size is not None:
        deposit_settings["min_party_size"] = min_party_size
    if required_peak_hours is not None:
        deposit_settings["required_peak_hours"] = required_peak_hours
    if peak_hours_start is not None:
        deposit_settings["peak_hours_start"] = peak_hours_start
    if peak_hours_end is not None:
        deposit_settings["peak_hours_end"] = peak_hours_end
    if weekend_required is not None:
        deposit_settings["weekend_required"] = weekend_required
    if currency is not None:
        deposit_settings["currency"] = currency

    current_settings["deposit_settings"] = deposit_settings
    venue_settings.settings_data = current_settings

    db.commit()
    db.refresh(venue_settings)

    return {**deposit_settings, "venue_id": venue_id}


@router.get("/deposits/{deposit_id}")
@limiter.limit("60/minute")
async def get_deposit(
    request: Request,
    deposit_id: int,
    db: Session = Depends(get_db)
):
    """Get deposit details"""
    deposit = db.query(ReservationDeposit).filter(ReservationDeposit.id == deposit_id).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    return {
        "id": deposit.id,
        "reservation_id": deposit.reservation_id,
        "venue_id": deposit.venue_id,
        "amount": float(deposit.amount),
        "currency": deposit.currency,
        "status": deposit.status.value,
        "payment_link": deposit.payment_link,
        "payment_method": deposit.payment_method,
        "transaction_id": deposit.transaction_id,
        "collected_at": deposit.collected_at.isoformat() if deposit.collected_at else None,
        "order_id": deposit.order_id,
        "applied_at": deposit.applied_at.isoformat() if deposit.applied_at else None,
        "amount_applied": float(deposit.amount_applied) if deposit.amount_applied else None,
        "refund_reason": deposit.refund_reason,
        "refunded_at": deposit.refunded_at.isoformat() if deposit.refunded_at else None,
        "created_at": deposit.created_at.isoformat() if deposit.created_at else None,
        "updated_at": deposit.updated_at.isoformat() if deposit.updated_at else None
    }


@router.post("/deposits/{deposit_id}/collect")
@limiter.limit("30/minute")
async def collect_deposit(
    request: Request,
    deposit_id: int,
    payment_method: str = Body(...),
    transaction_id: str = Body(...),
    staff_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Record deposit collection"""
    deposit = db.query(ReservationDeposit).filter(ReservationDeposit.id == deposit_id).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    if deposit.status != DepositStatus.pending:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot collect deposit with status '{deposit.status.value}'. Only pending deposits can be collected."
        )

    # Update deposit record
    deposit.status = DepositStatus.collected
    deposit.payment_method = payment_method
    deposit.transaction_id = transaction_id
    deposit.collected_at = datetime.now(timezone.utc)
    deposit.collected_by = staff_id

    db.commit()
    db.refresh(deposit)

    return {
        "deposit_id": deposit.id,
        "reservation_id": deposit.reservation_id,
        "amount": float(deposit.amount),
        "status": deposit.status.value,
        "payment_method": deposit.payment_method,
        "transaction_id": deposit.transaction_id,
        "collected_at": deposit.collected_at.isoformat() if deposit.collected_at else None
    }


@router.post("/deposits/{deposit_id}/apply")
@limiter.limit("30/minute")
async def apply_deposit_to_order(
    request: Request,
    deposit_id: int,
    order_id: int = Body(...),
    amount: Optional[float] = Body(None),
    db: Session = Depends(get_db)
):
    """Apply deposit to final bill"""
    deposit = db.query(ReservationDeposit).filter(ReservationDeposit.id == deposit_id).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    if deposit.status != DepositStatus.collected:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot apply deposit with status '{deposit.status.value}'. Only collected deposits can be applied."
        )

    # Verify order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Determine amount to apply (default to full deposit amount)
    amount_to_apply = Decimal(str(amount)) if amount else deposit.amount

    if amount_to_apply > deposit.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot apply more than deposit amount ({float(deposit.amount)})"
        )

    # Update deposit record
    deposit.status = DepositStatus.applied
    deposit.order_id = order_id
    deposit.applied_at = datetime.now(timezone.utc)
    deposit.amount_applied = amount_to_apply

    db.commit()
    db.refresh(deposit)

    return {
        "deposit_id": deposit.id,
        "reservation_id": deposit.reservation_id,
        "order_id": deposit.order_id,
        "amount_applied": float(deposit.amount_applied),
        "status": deposit.status.value,
        "applied_at": deposit.applied_at.isoformat() if deposit.applied_at else None
    }


@router.post("/deposits/{deposit_id}/refund")
@limiter.limit("30/minute")
async def refund_deposit(
    request: Request,
    deposit_id: int,
    reason: str = Body(...),
    staff_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Refund a deposit"""
    deposit = db.query(ReservationDeposit).filter(ReservationDeposit.id == deposit_id).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    if deposit.status not in [DepositStatus.pending, DepositStatus.collected]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot refund deposit with status '{deposit.status.value}'. Only pending or collected deposits can be refunded."
        )

    # Update deposit record
    deposit.status = DepositStatus.refunded
    deposit.refund_reason = reason
    deposit.refunded_at = datetime.now(timezone.utc)
    deposit.refunded_by = staff_id

    db.commit()
    db.refresh(deposit)

    return {
        "deposit_id": deposit.id,
        "reservation_id": deposit.reservation_id,
        "amount": float(deposit.amount),
        "status": deposit.status.value,
        "reason": deposit.refund_reason,
        "refunded_at": deposit.refunded_at.isoformat() if deposit.refunded_at else None
    }


@router.get("/reservations/{reservation_id}/deposits")
@limiter.limit("60/minute")
async def get_reservation_deposits(
    request: Request,
    reservation_id: int,
    db: Session = Depends(get_db)
):
    """Get all deposits for a reservation"""
    # Verify reservation exists
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    deposits = db.query(ReservationDeposit).filter(
        ReservationDeposit.reservation_id == reservation_id
    ).order_by(ReservationDeposit.created_at.desc()).all()

    return {
        "reservation_id": reservation_id,
        "deposits": [
            {
                "id": d.id,
                "amount": float(d.amount),
                "currency": d.currency,
                "status": d.status.value,
                "payment_method": d.payment_method,
                "collected_at": d.collected_at.isoformat() if d.collected_at else None,
                "order_id": d.order_id,
                "applied_at": d.applied_at.isoformat() if d.applied_at else None,
                "amount_applied": float(d.amount_applied) if d.amount_applied else None,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in deposits
        ],
        "total_deposited": float(sum(d.amount for d in deposits if d.status == DepositStatus.collected)),
        "total_applied": float(sum(d.amount_applied or 0 for d in deposits if d.status == DepositStatus.applied))
    }

