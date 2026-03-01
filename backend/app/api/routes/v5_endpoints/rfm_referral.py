"""V5 sub-module: RFM Analytics & Referral Program"""
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

# ==================== RFM ANALYTICS ====================

def _calculate_rfm_score(value: float, thresholds: List[float], inverse: bool = False) -> int:
    """Calculate RFM score (1-5) based on value and thresholds.

    Args:
        value: The raw value to score
        thresholds: List of 4 threshold values defining score boundaries
        inverse: If True, lower values get higher scores (used for Recency)

    Returns:
        Score from 1-5
    """
    if inverse:
        # For recency: fewer days = higher score
        if value <= thresholds[0]:
            return 5
        elif value <= thresholds[1]:
            return 4
        elif value <= thresholds[2]:
            return 3
        elif value <= thresholds[3]:
            return 2
        else:
            return 1
    else:
        # For frequency/monetary: higher values = higher score
        if value >= thresholds[3]:
            return 5
        elif value >= thresholds[2]:
            return 4
        elif value >= thresholds[1]:
            return 3
        elif value >= thresholds[0]:
            return 2
        else:
            return 1


def _get_rfm_segment(recency_score: int, frequency_score: int, monetary_score: int) -> str:
    """Determine RFM segment based on scores."""
    # Combined score for segmentation
    avg_score = (recency_score + frequency_score + monetary_score) / 3

    # Champions: High in all three
    if recency_score >= 4 and frequency_score >= 4 and monetary_score >= 4:
        return "Champions"

    # Loyal Customers: High frequency and monetary, good recency
    if frequency_score >= 4 and monetary_score >= 3 and recency_score >= 3:
        return "Loyal Customers"

    # Potential Loyalists: Recent customers with moderate frequency
    if recency_score >= 4 and frequency_score >= 2 and frequency_score <= 3:
        return "Potential Loyalists"

    # New Customers: Very recent but low frequency
    if recency_score >= 4 and frequency_score <= 2:
        return "New Customers"

    # At Risk: Previously good customers who haven't visited recently
    if recency_score <= 2 and frequency_score >= 3:
        return "At Risk"

    # Can't Lose: High value but haven't visited in a while
    if recency_score <= 2 and monetary_score >= 4:
        return "Can't Lose"

    # Hibernating: Low recency and low frequency
    if recency_score <= 2 and frequency_score <= 2:
        return "Lost"

    # About to Sleep: Below average recency
    if recency_score <= 3 and avg_score <= 3:
        return "About to Sleep"

    # Default
    return "Need Attention"


@router.get("/rfm/customer/{customer_id}")
@limiter.limit("60/minute")
async def get_customer_rfm(
    request: Request,
    customer_id: int,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get RFM score for customer - calculated from actual order data"""
    # Get customer
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.location_id == venue_id
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Calculate RFM values from orders
    orders = db.query(Order).filter(
        Order.customer_id == customer_id,
        Order.venue_id == venue_id
    ).all()

    now = datetime.now(timezone.utc)

    if not orders:
        # No orders - return lowest scores
        return {
            "customer_id": customer_id,
            "customer_name": customer.name,
            "recency_days": None,
            "frequency_count": 0,
            "monetary_total": 0.0,
            "recency_score": 1,
            "frequency_score": 1,
            "monetary_score": 1,
            "rfm_score": 111,
            "segment": "Lost"
        }

    # Recency: Days since last order
    last_order_date = max(o.created_at for o in orders if o.created_at)
    recency_days = (now - last_order_date.replace(tzinfo=None)).days if last_order_date else 365

    # Frequency: Total order count
    frequency_count = len(orders)

    # Monetary: Total spent
    monetary_total = sum(o.total or 0 for o in orders)

    # Calculate scores using typical restaurant thresholds
    # Recency thresholds (days): 7, 30, 60, 90
    recency_score = _calculate_rfm_score(recency_days, [7, 30, 60, 90], inverse=True)

    # Frequency thresholds (orders): 2, 5, 10, 20
    frequency_score = _calculate_rfm_score(frequency_count, [2, 5, 10, 20], inverse=False)

    # Monetary thresholds (BGN): 50, 150, 400, 1000
    monetary_score = _calculate_rfm_score(monetary_total, [50, 150, 400, 1000], inverse=False)

    # Combined RFM score (e.g., 434 means R=4, F=3, M=4)
    rfm_score = recency_score * 100 + frequency_score * 10 + monetary_score

    # Determine segment
    segment = _get_rfm_segment(recency_score, frequency_score, monetary_score)

    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "recency_days": recency_days,
        "frequency_count": frequency_count,
        "monetary_total": round(monetary_total, 2),
        "recency_score": recency_score,
        "frequency_score": frequency_score,
        "monetary_score": monetary_score,
        "rfm_score": rfm_score,
        "segment": segment
    }


@router.get("/rfm/segments")
@limiter.limit("60/minute")
async def get_rfm_segments(
    request: Request,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get all RFM segments with counts - calculated from actual customer/order data"""
    # Get all customers for this venue
    customers = db.query(Customer).filter(
        Customer.location_id == venue_id,
        Customer.deleted_at.is_(None)
    ).all()

    now = datetime.now(timezone.utc)
    segment_counts: Dict[str, int] = {}

    for customer in customers:
        # Get orders for this customer
        orders = db.query(Order).filter(
            Order.customer_id == customer.id,
            Order.venue_id == venue_id
        ).all()

        if not orders:
            segment = "Lost"
        else:
            # Calculate RFM values
            last_order_date = max(o.created_at for o in orders if o.created_at)
            recency_days = (now - last_order_date.replace(tzinfo=None)).days if last_order_date else 365
            frequency_count = len(orders)
            monetary_total = sum(o.total or 0 for o in orders)

            # Calculate scores
            recency_score = _calculate_rfm_score(recency_days, [7, 30, 60, 90], inverse=True)
            frequency_score = _calculate_rfm_score(frequency_count, [2, 5, 10, 20], inverse=False)
            monetary_score = _calculate_rfm_score(monetary_total, [50, 150, 400, 1000], inverse=False)

            segment = _get_rfm_segment(recency_score, frequency_score, monetary_score)

        segment_counts[segment] = segment_counts.get(segment, 0) + 1

    return {
        "segments": segment_counts,
        "total_customers": len(customers)
    }


@router.get("/rfm/segment/{segment}/customers")
@limiter.limit("60/minute")
async def get_segment_customers(
    request: Request,
    segment: str,
    venue_id: int = Query(1),
    limit: int = Query(100),
    db: Session = Depends(get_db)
):
    """Get customers in segment - calculated from actual order data"""
    # Get all customers for this venue
    customers = db.query(Customer).filter(
        Customer.location_id == venue_id,
        Customer.deleted_at.is_(None)
    ).all()

    now = datetime.now(timezone.utc)
    segment_customers = []

    for customer in customers:
        # Get orders for this customer
        orders = db.query(Order).filter(
            Order.customer_id == customer.id,
            Order.venue_id == venue_id
        ).all()

        if not orders:
            customer_segment = "Lost"
            rfm_score = 111
            recency_days = None
            frequency_count = 0
            monetary_total = 0.0
        else:
            # Calculate RFM values
            last_order_date = max(o.created_at for o in orders if o.created_at)
            recency_days = (now - last_order_date.replace(tzinfo=None)).days if last_order_date else 365
            frequency_count = len(orders)
            monetary_total = sum(o.total or 0 for o in orders)

            # Calculate scores
            recency_score = _calculate_rfm_score(recency_days, [7, 30, 60, 90], inverse=True)
            frequency_score = _calculate_rfm_score(frequency_count, [2, 5, 10, 20], inverse=False)
            monetary_score = _calculate_rfm_score(monetary_total, [50, 150, 400, 1000], inverse=False)

            rfm_score = recency_score * 100 + frequency_score * 10 + monetary_score
            customer_segment = _get_rfm_segment(recency_score, frequency_score, monetary_score)

        # Check if customer belongs to requested segment
        if customer_segment.lower() == segment.lower() or segment.lower() == "all":
            segment_customers.append({
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "rfm_score": rfm_score,
                "recency_days": recency_days,
                "frequency_count": frequency_count,
                "monetary_total": round(monetary_total, 2) if monetary_total else 0.0
            })

            if len(segment_customers) >= limit:
                break

    # Sort by RFM score descending
    segment_customers.sort(key=lambda x: x["rfm_score"], reverse=True)

    return {
        "segment": segment,
        "customers": segment_customers[:limit]
    }


@router.get("/rfm/segment/{segment}/recommendations")
@limiter.limit("60/minute")
async def get_segment_recommendations(request: Request, segment: str):
    """Get marketing recommendations for segment"""
    # Segment-specific marketing strategies
    recommendations = {
        "champions": {
            "segment": "Champions",
            "strategy": "Reward and retain - these are your best customers",
            "actions": [
                "Offer exclusive VIP rewards and early access",
                "Create referral programs with premium incentives",
                "Invite to special events and tastings",
                "Personalized thank-you messages from management"
            ],
            "suggested_offers": [
                "Exclusive members-only dishes",
                "Complimentary dessert on visits",
                "Priority reservations"
            ]
        },
        "loyal customers": {
            "segment": "Loyal Customers",
            "strategy": "Upsell and increase engagement",
            "actions": [
                "Introduce loyalty program upgrades",
                "Cross-sell new menu items",
                "Encourage trying premium options",
                "Ask for reviews and testimonials"
            ],
            "suggested_offers": [
                "20% off on premium items",
                "Double loyalty points this month",
                "Free appetizer with main course"
            ]
        },
        "potential loyalists": {
            "segment": "Potential Loyalists",
            "strategy": "Build loyalty before they drift away",
            "actions": [
                "Enroll in loyalty program",
                "Offer membership benefits",
                "Send personalized recommendations",
                "Regular engagement emails"
            ],
            "suggested_offers": [
                "Welcome to loyalty bonus points",
                "15% off next 3 visits",
                "Free drink with meal"
            ]
        },
        "new customers": {
            "segment": "New Customers",
            "strategy": "Onboard and educate about your offerings",
            "actions": [
                "Send welcome series emails",
                "Introduce loyalty program",
                "Showcase bestsellers and signature dishes",
                "Follow up after first visit"
            ],
            "suggested_offers": [
                "Welcome discount 10% off",
                "Free dessert on second visit",
                "Join loyalty program bonus"
            ]
        },
        "at risk": {
            "segment": "At Risk",
            "strategy": "Reactivate before they leave",
            "actions": [
                "Send win-back campaigns urgently",
                "Call or message personally",
                "Ask for feedback on last experience",
                "Offer significant incentive to return"
            ],
            "suggested_offers": [
                "We miss you - 30% off return visit",
                "Free main course on us",
                "Exclusive comeback offer"
            ]
        },
        "can't lose": {
            "segment": "Can't Lose",
            "strategy": "Urgent reactivation - high-value customers at risk",
            "actions": [
                "Personal outreach from manager",
                "VIP win-back campaign",
                "Investigate if there was an issue",
                "Offer premium incentives"
            ],
            "suggested_offers": [
                "Complimentary meal for two",
                "40% off your next visit",
                "Personal invitation from chef"
            ]
        },
        "lost": {
            "segment": "Lost",
            "strategy": "Attempt reactivation with strong offers",
            "actions": [
                "Send reactivation campaign",
                "Highlight what's new since their last visit",
                "Offer significant discount",
                "Consider removing from active lists after attempts"
            ],
            "suggested_offers": [
                "50% off comeback special",
                "Free meal on your return",
                "See what you've been missing"
            ]
        },
        "about to sleep": {
            "segment": "About to Sleep",
            "strategy": "Reactivate before they become lost",
            "actions": [
                "Send reminder campaigns",
                "Highlight new menu items",
                "Offer time-limited discount",
                "Engagement through events"
            ],
            "suggested_offers": [
                "25% off this week only",
                "New dishes you'll love",
                "Double points weekend"
            ]
        },
        "need attention": {
            "segment": "Need Attention",
            "strategy": "Understand and engage",
            "actions": [
                "Send survey to understand preferences",
                "Personalized recommendations",
                "Moderate incentives to increase frequency",
                "Regular newsletters"
            ],
            "suggested_offers": [
                "15% off your favorites",
                "Try something new - 20% off",
                "Loyalty program introduction"
            ]
        }
    }

    # Normalize segment name for lookup
    segment_lower = segment.lower()

    if segment_lower in recommendations:
        return recommendations[segment_lower]

    # Default recommendation for unknown segments
    return {
        "segment": segment,
        "strategy": "Analyze and engage appropriately",
        "actions": [
            "Review customer data for insights",
            "Send targeted marketing campaign",
            "Offer moderate incentives",
            "Track response rates"
        ],
        "suggested_offers": [
            "15% discount",
            "Free appetizer",
            "Loyalty points bonus"
        ]
    }

# ==================== REFERRAL PROGRAM ====================

@router.post("/referral/programs")
@limiter.limit("30/minute")
async def create_referral_program(
    request: Request,
    venue_id: int = Query(1),
    name: str = Body(...),
    referrer_reward_type: str = Body("credit"),
    referrer_reward_value: float = Body(...),
    referee_reward_type: str = Body("discount"),
    referee_reward_value: float = Body(...),
    min_order_value: Optional[float] = Body(None),
    reward_after_orders: int = Body(1),
    max_referrals_per_customer: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Create referral program"""
    program = ReferralProgram(
        venue_id=venue_id,
        name=name,
        referrer_reward_type=referrer_reward_type,
        referrer_reward_value=Decimal(str(referrer_reward_value)),
        referee_reward_type=referee_reward_type,
        referee_reward_value=Decimal(str(referee_reward_value)),
        min_order_value=Decimal(str(min_order_value)) if min_order_value else None,
        reward_after_orders=reward_after_orders,
        max_referrals_per_customer=max_referrals_per_customer,
        is_active=True
    )
    db.add(program)
    db.commit()
    db.refresh(program)

    return {
        "id": program.id,
        "venue_id": program.venue_id,
        "name": program.name,
        "referrer_reward_type": program.referrer_reward_type,
        "referrer_reward_value": float(program.referrer_reward_value),
        "referee_reward_type": program.referee_reward_type,
        "referee_reward_value": float(program.referee_reward_value),
        "min_order_value": float(program.min_order_value) if program.min_order_value else None,
        "reward_after_orders": program.reward_after_orders,
        "max_referrals_per_customer": program.max_referrals_per_customer,
        "is_active": program.is_active,
        "created_at": program.created_at.isoformat() if program.created_at else None
    }


@router.get("/referral/programs")
@limiter.limit("60/minute")
async def list_referral_programs(
    request: Request,
    venue_id: int = Query(1),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """List all referral programs for a venue"""
    query = db.query(ReferralProgram).filter(ReferralProgram.venue_id == venue_id)

    if is_active is not None:
        query = query.filter(ReferralProgram.is_active == is_active)

    programs = query.all()

    return {
        "programs": [
            {
                "id": p.id,
                "name": p.name,
                "referrer_reward_type": p.referrer_reward_type,
                "referrer_reward_value": float(p.referrer_reward_value) if p.referrer_reward_value else 0,
                "referee_reward_type": p.referee_reward_type,
                "referee_reward_value": float(p.referee_reward_value) if p.referee_reward_value else 0,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in programs
        ],
        "total": len(programs)
    }


@router.post("/referral/generate-code")
@limiter.limit("30/minute")
async def generate_referral_code(
    request: Request,
    program_id: int = Body(...),
    customer_id: int = Body(...),
    referee_email: Optional[str] = Body(None),
    referee_phone: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Generate referral code for customer"""
    # Verify program exists and is active
    program = db.query(ReferralProgram).filter(
        ReferralProgram.id == program_id,
        ReferralProgram.is_active == True
    ).first()

    if not program:
        raise HTTPException(status_code=404, detail="Referral program not found or inactive")

    # Verify customer exists
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Check if customer has reached max referrals limit
    if program.max_referrals_per_customer:
        existing_referrals = db.query(CustomerReferral).filter(
            CustomerReferral.program_id == program_id,
            CustomerReferral.referrer_id == customer_id
        ).count()

        if existing_referrals >= program.max_referrals_per_customer:
            raise HTTPException(
                status_code=400,
                detail=f"Customer has reached maximum referrals limit ({program.max_referrals_per_customer})"
            )

    # Generate unique referral code
    while True:
        code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
        existing = db.query(CustomerReferral).filter(CustomerReferral.referral_code == code).first()
        if not existing:
            break

    # Create referral record
    referral = CustomerReferral(
        venue_id=program.venue_id,
        program_id=program_id,
        referrer_id=customer_id,
        referral_code=code,
        referee_email=referee_email,
        referee_phone=referee_phone,
        status="pending"
    )
    db.add(referral)
    db.commit()
    db.refresh(referral)

    return {
        "referral_id": referral.id,
        "referral_code": code,
        "share_url": f"https://bjsbar.bg/ref/{code}",
        "program_name": program.name,
        "referee_reward": {
            "type": program.referee_reward_type,
            "value": float(program.referee_reward_value) if program.referee_reward_value else 0
        },
        "referrer_reward": {
            "type": program.referrer_reward_type,
            "value": float(program.referrer_reward_value) if program.referrer_reward_value else 0
        }
    }


@router.post("/referral/validate")
@limiter.limit("30/minute")
async def validate_referral_code(
    request: Request,
    validation: ReferralCodeValidation,
    db: Session = Depends(get_db)
):
    """Validate a referral code and register referee"""
    # Find the referral by code
    referral = db.query(CustomerReferral).filter(
        CustomerReferral.referral_code == validation.code
    ).first()

    if not referral:
        return {
            "valid": False,
            "code": validation.code,
            "error": "Invalid referral code"
        }

    # Check if referral is still pending (not already used)
    if referral.status != "pending":
        return {
            "valid": False,
            "code": validation.code,
            "error": f"Referral code already used (status: {referral.status})"
        }

    # Check if referee is trying to use their own code
    if referral.referrer_id == validation.referee_customer_id:
        return {
            "valid": False,
            "code": validation.code,
            "error": "Cannot use your own referral code"
        }

    # Get the program details
    program = db.query(ReferralProgram).filter(
        ReferralProgram.id == referral.program_id
    ).first()

    if not program or not program.is_active:
        return {
            "valid": False,
            "code": validation.code,
            "error": "Referral program is no longer active"
        }

    # Update referral with referee info
    referral.referee_id = validation.referee_customer_id
    referral.status = "registered"
    referral.registered_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "valid": True,
        "code": validation.code,
        "referral_id": referral.id,
        "program_name": program.name,
        "referee_reward": {
            "type": program.referee_reward_type,
            "value": float(program.referee_reward_value) if program.referee_reward_value else 0
        },
        "min_order_value": float(program.min_order_value) if program.min_order_value else None,
        "message": "Referral code validated. Complete a qualifying order to receive your reward."
    }


@router.post("/referral/{referral_id}/qualify")
@limiter.limit("30/minute")
async def qualify_referral(
    request: Request,
    referral_id: int,
    order_id: int = Body(...),
    db: Session = Depends(get_db)
):
    """Mark a referral as qualified after referee completes qualifying order"""
    referral = db.query(CustomerReferral).filter(CustomerReferral.id == referral_id).first()

    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    if referral.status not in ["pending", "registered"]:
        raise HTTPException(status_code=400, detail=f"Referral cannot be qualified (current status: {referral.status})")

    # Get the program to check min order value
    program = db.query(ReferralProgram).filter(ReferralProgram.id == referral.program_id).first()

    if program and program.min_order_value:
        # Verify order meets minimum value
        order = db.query(Order).filter(Order.id == order_id).first()
        if order and order.total_amount < float(program.min_order_value):
            raise HTTPException(
                status_code=400,
                detail=f"Order value must be at least {program.min_order_value} to qualify"
            )

    referral.status = "qualified"
    referral.qualified_at = datetime.now(timezone.utc)
    referral.qualifying_order_id = order_id
    db.commit()

    return {
        "referral_id": referral.id,
        "status": "qualified",
        "qualified_at": referral.qualified_at.isoformat(),
        "message": "Referral qualified. Rewards can now be issued."
    }


@router.post("/referral/{referral_id}/issue-rewards")
@limiter.limit("30/minute")
async def issue_referral_rewards(
    request: Request,
    referral_id: int,
    db: Session = Depends(get_db)
):
    """Issue rewards to both referrer and referee"""
    referral = db.query(CustomerReferral).filter(CustomerReferral.id == referral_id).first()

    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    if referral.status != "qualified":
        raise HTTPException(status_code=400, detail="Referral must be qualified before issuing rewards")

    program = db.query(ReferralProgram).filter(ReferralProgram.id == referral.program_id).first()

    rewards_issued = []

    # Issue referrer reward
    if not referral.referrer_reward_issued and program.referrer_reward_value:
        referrer = db.query(Customer).filter(Customer.id == referral.referrer_id).first()
        if referrer:
            if program.referrer_reward_type == "points":
                referrer.loyalty_points = (referrer.loyalty_points or 0) + int(program.referrer_reward_value)
            # For credit/discount types, you would typically create a credit record
            # Here we'll add to loyalty points as a simplified implementation
            referral.referrer_reward_issued = True
            rewards_issued.append({
                "recipient": "referrer",
                "customer_id": referrer.id,
                "reward_type": program.referrer_reward_type,
                "reward_value": float(program.referrer_reward_value)
            })

    # Issue referee reward
    if not referral.referee_reward_issued and referral.referee_id and program.referee_reward_value:
        referee = db.query(Customer).filter(Customer.id == referral.referee_id).first()
        if referee:
            if program.referee_reward_type == "points":
                referee.loyalty_points = (referee.loyalty_points or 0) + int(program.referee_reward_value)
            referral.referee_reward_issued = True
            rewards_issued.append({
                "recipient": "referee",
                "customer_id": referee.id,
                "reward_type": program.referee_reward_type,
                "reward_value": float(program.referee_reward_value)
            })

    if rewards_issued:
        referral.status = "rewarded"
        referral.rewarded_at = datetime.now(timezone.utc)
        db.commit()

    return {
        "referral_id": referral.id,
        "status": referral.status,
        "rewards_issued": rewards_issued,
        "referrer_reward_issued": referral.referrer_reward_issued,
        "referee_reward_issued": referral.referee_reward_issued
    }


@router.get("/referral/customer/{customer_id}/stats")
@limiter.limit("60/minute")
async def get_customer_referrals(
    request: Request,
    customer_id: int,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get customer's referral statistics"""
    # Get all referrals where customer is the referrer
    referrals = db.query(CustomerReferral).filter(
        CustomerReferral.referrer_id == customer_id,
        CustomerReferral.venue_id == venue_id
    ).all()

    total_referrals = len(referrals)
    pending = sum(1 for r in referrals if r.status == "pending")
    registered = sum(1 for r in referrals if r.status == "registered")
    qualified = sum(1 for r in referrals if r.status == "qualified")
    rewarded = sum(1 for r in referrals if r.status == "rewarded")

    # Calculate total rewards earned
    total_rewards = Decimal("0")
    for r in referrals:
        if r.referrer_reward_issued:
            program = db.query(ReferralProgram).filter(ReferralProgram.id == r.program_id).first()
            if program and program.referrer_reward_value:
                total_rewards += program.referrer_reward_value

    # Get recent referrals
    recent_referrals = sorted(referrals, key=lambda x: x.created_at or datetime.min, reverse=True)[:5]

    return {
        "customer_id": customer_id,
        "total_referrals": total_referrals,
        "pending": pending,
        "registered": registered,
        "qualified": qualified,
        "rewarded": rewarded,
        "successful": qualified + rewarded,
        "rewards_earned": float(total_rewards),
        "recent_referrals": [
            {
                "referral_code": r.referral_code,
                "status": r.status,
                "referee_email": r.referee_email,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "qualified_at": r.qualified_at.isoformat() if r.qualified_at else None
            }
            for r in recent_referrals
        ]
    }


@router.get("/referral/program/{program_id}/stats")
@limiter.limit("60/minute")
async def get_program_stats(
    request: Request,
    program_id: int,
    db: Session = Depends(get_db)
):
    """Get statistics for a referral program"""
    program = db.query(ReferralProgram).filter(ReferralProgram.id == program_id).first()

    if not program:
        raise HTTPException(status_code=404, detail="Referral program not found")

    referrals = db.query(CustomerReferral).filter(CustomerReferral.program_id == program_id).all()

    total = len(referrals)
    by_status = {}
    for r in referrals:
        by_status[r.status] = by_status.get(r.status, 0) + 1

    # Calculate total rewards issued
    total_referrer_rewards = sum(
        float(program.referrer_reward_value) for r in referrals
        if r.referrer_reward_issued and program.referrer_reward_value
    )
    total_referee_rewards = sum(
        float(program.referee_reward_value) for r in referrals
        if r.referee_reward_issued and program.referee_reward_value
    )

    # Unique referrers
    unique_referrers = len(set(r.referrer_id for r in referrals))

    return {
        "program_id": program_id,
        "program_name": program.name,
        "is_active": program.is_active,
        "total_referrals": total,
        "by_status": by_status,
        "unique_referrers": unique_referrers,
        "conversion_rate": round((by_status.get("rewarded", 0) + by_status.get("qualified", 0)) / total * 100, 2) if total > 0 else 0,
        "total_rewards_issued": {
            "referrer_rewards": total_referrer_rewards,
            "referee_rewards": total_referee_rewards,
            "total": total_referrer_rewards + total_referee_rewards
        }
    }

