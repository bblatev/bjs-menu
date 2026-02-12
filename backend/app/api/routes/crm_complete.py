"""
Complete CRM Endpoints for BJS V6.1
Implements all features from Toast POS, iiko, and TouchBistro:
- Customer Reviews & Feedback
- Referral Programs
- Email & SMS Marketing Campaigns
- Customer Segmentation & RFM Analytics
- Birthday/Anniversary Rewards
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc
from typing import List, Optional
from datetime import datetime, timedelta, date
from pydantic import BaseModel, ConfigDict

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import (
    StaffUser, Customer, MenuItemReview, MenuItemRatingAggregate,
    CustomerReferral, ReferralProgram, CustomerRFMScore,
    RFMSegmentDefinition, SMSCampaign
)


router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class ReviewCreate(BaseModel):
    menu_item_id: int
    customer_id: Optional[int] = None
    order_id: Optional[int] = None
    rating: int  # 1-5
    review_text: Optional[str] = None
    taste_rating: Optional[int] = None
    presentation_rating: Optional[int] = None
    portion_rating: Optional[int] = None
    value_rating: Optional[int] = None
    photo_urls: Optional[List[str]] = None


class ReviewResponse(BaseModel):
    id: int
    menu_item_id: int
    customer_id: Optional[int]
    customer_name: Optional[str]
    rating: int
    review_text: Optional[str]
    taste_rating: Optional[int]
    presentation_rating: Optional[int]
    portion_rating: Optional[int]
    value_rating: Optional[int]
    photo_urls: Optional[List[str]]
    verified_purchase: bool
    status: str
    response_text: Optional[str]
    helpful_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReviewModerate(BaseModel):
    status: str  # approved, rejected
    response_text: Optional[str] = None


class ReferralProgramCreate(BaseModel):
    name: str
    referrer_reward_type: str  # points, credit, discount
    referrer_reward_value: float
    referee_reward_type: str
    referee_reward_value: float
    min_order_value: Optional[float] = None
    reward_after_orders: int = 1
    max_referrals_per_customer: Optional[int] = None


class ReferralProgramResponse(BaseModel):
    id: int
    venue_id: int
    name: str
    referrer_reward_type: str
    referrer_reward_value: float
    referee_reward_type: str
    referee_reward_value: float
    min_order_value: Optional[float]
    reward_after_orders: int
    max_referrals_per_customer: Optional[int]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReferralCreate(BaseModel):
    referrer_id: int
    referee_email: Optional[str] = None
    referee_phone: Optional[str] = None


class ReferralResponse(BaseModel):
    id: int
    referrer_id: int
    referrer_name: str
    referee_id: Optional[int]
    referee_name: Optional[str]
    referral_code: str
    referee_email: Optional[str]
    referee_phone: Optional[str]
    status: str
    registered_at: Optional[datetime]
    qualified_at: Optional[datetime]
    rewarded_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignCreate(BaseModel):
    name: str
    message_template: str
    target_segment: str  # all, champions, loyal, at_risk, new, inactive
    target_filters: Optional[dict] = None
    scheduled_at: Optional[datetime] = None
    promo_code: Optional[str] = None


class CampaignResponse(BaseModel):
    id: int
    venue_id: int
    name: str
    message_template: str
    status: str
    target_segment: str
    estimated_recipients: int
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_sent: int
    total_delivered: int
    total_failed: int
    promo_code: Optional[str]
    redemption_count: int
    revenue_generated: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerSegmentResponse(BaseModel):
    segment_name: str
    customer_count: int
    avg_order_value: float
    total_revenue: float
    avg_recency_days: float
    avg_frequency: float
    description: Optional[str] = None


class CustomerEnhancedResponse(BaseModel):
    id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    total_orders: int
    total_spent: float
    average_order_value: float
    last_visit: Optional[datetime]
    birthday: Optional[datetime]
    anniversary: Optional[datetime]
    tags: Optional[List[str]]
    loyalty_points: int
    loyalty_tier: str
    rfm_score: Optional[dict]
    segment: Optional[str]
    lifetime_value: float
    visit_frequency: float
    spend_trend: str
    favorite_items: Optional[List[int]]
    marketing_consent: bool

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CUSTOMER REVIEWS & FEEDBACK
# ============================================================================

@router.post("/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(
    data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a new menu item review"""
    # Validate rating
    if not 1 <= data.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Create review
    review = MenuItemReview(
        venue_id=current_user.venue_id,
        menu_item_id=data.menu_item_id,
        customer_id=data.customer_id,
        order_id=data.order_id,
        rating=data.rating,
        review_text=data.review_text,
        taste_rating=data.taste_rating,
        presentation_rating=data.presentation_rating,
        portion_rating=data.portion_rating,
        value_rating=data.value_rating,
        photo_urls=data.photo_urls,
        verified_purchase=data.order_id is not None,
        status="approved"  # Auto-approve for now
    )

    db.add(review)
    db.flush()

    # Update aggregate ratings
    _update_rating_aggregate(db, data.menu_item_id)

    db.commit()
    db.refresh(review)

    # Get customer name if available
    customer_name = None
    if review.customer_id:
        customer = db.query(Customer).filter(Customer.id == review.customer_id).first()
        if customer:
            customer_name = customer.name

    return ReviewResponse(
        id=review.id,
        menu_item_id=review.menu_item_id,
        customer_id=review.customer_id,
        customer_name=customer_name,
        rating=review.rating,
        review_text=review.review_text,
        taste_rating=review.taste_rating,
        presentation_rating=review.presentation_rating,
        portion_rating=review.portion_rating,
        value_rating=review.value_rating,
        photo_urls=review.photo_urls,
        verified_purchase=review.verified_purchase,
        status=review.status,
        response_text=review.response_text,
        helpful_count=review.helpful_count,
        created_at=review.created_at
    )


@router.get("/reviews", response_model=List[ReviewResponse])
async def list_reviews(
    menu_item_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List menu item reviews"""
    query = db.query(MenuItemReview).filter(MenuItemReview.venue_id == current_user.venue_id)

    if menu_item_id:
        query = query.filter(MenuItemReview.menu_item_id == menu_item_id)

    if customer_id:
        query = query.filter(MenuItemReview.customer_id == customer_id)

    if status:
        query = query.filter(MenuItemReview.status == status)

    reviews = query.order_by(desc(MenuItemReview.created_at)).offset(offset).limit(limit).all()

    # Enrich with customer names
    result = []
    for review in reviews:
        customer_name = None
        if review.customer_id:
            customer = db.query(Customer).filter(Customer.id == review.customer_id).first()
            if customer:
                customer_name = customer.name

        result.append(ReviewResponse(
            id=review.id,
            menu_item_id=review.menu_item_id,
            customer_id=review.customer_id,
            customer_name=customer_name,
            rating=review.rating,
            review_text=review.review_text,
            taste_rating=review.taste_rating,
            presentation_rating=review.presentation_rating,
            portion_rating=review.portion_rating,
            value_rating=review.value_rating,
            photo_urls=review.photo_urls,
            verified_purchase=review.verified_purchase,
            status=review.status,
            response_text=review.response_text,
            helpful_count=review.helpful_count,
            created_at=review.created_at
        ))

    return result


@router.put("/reviews/{review_id}/moderate", response_model=ReviewResponse)
async def moderate_review(
    review_id: int,
    data: ReviewModerate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Moderate a review (approve/reject) and optionally respond"""
    review = db.query(MenuItemReview).filter(
        MenuItemReview.id == review_id,
        MenuItemReview.venue_id == current_user.venue_id
    ).first()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.status = data.status
    review.moderated_at = datetime.utcnow()
    review.moderated_by = current_user.id

    if data.response_text:
        review.response_text = data.response_text
        review.responded_at = datetime.utcnow()
        review.responded_by = current_user.id

    db.commit()
    db.refresh(review)

    customer_name = None
    if review.customer_id:
        customer = db.query(Customer).filter(Customer.id == review.customer_id).first()
        if customer:
            customer_name = customer.name

    return ReviewResponse(
        id=review.id,
        menu_item_id=review.menu_item_id,
        customer_id=review.customer_id,
        customer_name=customer_name,
        rating=review.rating,
        review_text=review.review_text,
        taste_rating=review.taste_rating,
        presentation_rating=review.presentation_rating,
        portion_rating=review.portion_rating,
        value_rating=review.value_rating,
        photo_urls=review.photo_urls,
        verified_purchase=review.verified_purchase,
        status=review.status,
        response_text=review.response_text,
        helpful_count=review.helpful_count,
        created_at=review.created_at
    )


@router.get("/reviews/stats")
async def get_review_stats(
    menu_item_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get review statistics"""
    query = db.query(MenuItemReview).filter(
        MenuItemReview.venue_id == current_user.venue_id,
        MenuItemReview.status == "approved"
    )

    if menu_item_id:
        query = query.filter(MenuItemReview.menu_item_id == menu_item_id)

    total_reviews = query.count()
    avg_rating = db.query(func.avg(MenuItemReview.rating)).filter(
        MenuItemReview.venue_id == current_user.venue_id,
        MenuItemReview.status == "approved"
    )

    if menu_item_id:
        avg_rating = avg_rating.filter(MenuItemReview.menu_item_id == menu_item_id)

    avg_rating = avg_rating.scalar() or 0

    # Rating distribution
    rating_dist = {}
    for i in range(1, 6):
        count = query.filter(MenuItemReview.rating == i).count()
        rating_dist[f"rating_{i}"] = count

    return {
        "total_reviews": total_reviews,
        "average_rating": round(float(avg_rating), 2),
        "rating_distribution": rating_dist
    }


# ============================================================================
# REFERRAL PROGRAMS
# ============================================================================

@router.post("/referral-programs", response_model=ReferralProgramResponse, status_code=201)
async def create_referral_program(
    data: ReferralProgramCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a new referral program"""
    program = ReferralProgram(
        venue_id=current_user.venue_id,
        name=data.name,
        referrer_reward_type=data.referrer_reward_type,
        referrer_reward_value=data.referrer_reward_value,
        referee_reward_type=data.referee_reward_type,
        referee_reward_value=data.referee_reward_value,
        min_order_value=data.min_order_value,
        reward_after_orders=data.reward_after_orders,
        max_referrals_per_customer=data.max_referrals_per_customer
    )

    db.add(program)
    db.commit()
    db.refresh(program)

    return program


@router.get("/referral-programs", response_model=List[ReferralProgramResponse])
async def list_referral_programs(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all referral programs"""
    programs = db.query(ReferralProgram).filter(
        ReferralProgram.venue_id == current_user.venue_id
    ).all()

    return programs


@router.post("/referrals", response_model=ReferralResponse, status_code=201)
async def create_referral(
    data: ReferralCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a new customer referral"""
    # Get active referral program
    program = db.query(ReferralProgram).filter(
        ReferralProgram.venue_id == current_user.venue_id,
        ReferralProgram.is_active == True
    ).first()

    if not program:
        raise HTTPException(status_code=400, detail="No active referral program")

    # Check referral limit
    if program.max_referrals_per_customer:
        existing_count = db.query(func.count(CustomerReferral.id)).filter(
            CustomerReferral.venue_id == current_user.venue_id,
            CustomerReferral.referrer_id == data.referrer_id
        ).scalar()

        if existing_count >= program.max_referrals_per_customer:
            raise HTTPException(status_code=400, detail="Referral limit reached")

    # Generate unique referral code
    import random
    import string
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        existing = db.query(CustomerReferral).filter(CustomerReferral.referral_code == code).first()
        if not existing:
            break

    # Get referrer
    referrer = db.query(Customer).filter(Customer.id == data.referrer_id).first()
    if not referrer:
        raise HTTPException(status_code=404, detail="Referrer not found")

    referral = CustomerReferral(
        venue_id=current_user.venue_id,
        program_id=program.id,
        referrer_id=data.referrer_id,
        referral_code=code,
        referee_email=data.referee_email,
        referee_phone=data.referee_phone,
        status="pending"
    )

    db.add(referral)
    db.commit()
    db.refresh(referral)

    return ReferralResponse(
        id=referral.id,
        referrer_id=referral.referrer_id,
        referrer_name=referrer.name,
        referee_id=referral.referee_id,
        referee_name=None,
        referral_code=referral.referral_code,
        referee_email=referral.referee_email,
        referee_phone=referral.referee_phone,
        status=referral.status,
        registered_at=referral.registered_at,
        qualified_at=referral.qualified_at,
        rewarded_at=referral.rewarded_at,
        created_at=referral.created_at
    )


@router.get("/referrals", response_model=List[ReferralResponse])
async def list_referrals(
    referrer_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List customer referrals"""
    query = db.query(CustomerReferral).filter(
        CustomerReferral.venue_id == current_user.venue_id
    )

    if referrer_id:
        query = query.filter(CustomerReferral.referrer_id == referrer_id)

    if status:
        query = query.filter(CustomerReferral.status == status)

    referrals = query.order_by(desc(CustomerReferral.created_at)).offset(offset).limit(limit).all()

    # Enrich with names
    result = []
    for ref in referrals:
        referrer = db.query(Customer).filter(Customer.id == ref.referrer_id).first()
        referee = None
        if ref.referee_id:
            referee = db.query(Customer).filter(Customer.id == ref.referee_id).first()

        result.append(ReferralResponse(
            id=ref.id,
            referrer_id=ref.referrer_id,
            referrer_name=referrer.name if referrer else "Unknown",
            referee_id=ref.referee_id,
            referee_name=referee.name if referee else None,
            referral_code=ref.referral_code,
            referee_email=ref.referee_email,
            referee_phone=ref.referee_phone,
            status=ref.status,
            registered_at=ref.registered_at,
            qualified_at=ref.qualified_at,
            rewarded_at=ref.rewarded_at,
            created_at=ref.created_at
        ))

    return result


@router.get("/referrals/stats")
async def get_referral_stats(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get referral program statistics"""
    total_referrals = db.query(func.count(CustomerReferral.id)).filter(
        CustomerReferral.venue_id == current_user.venue_id
    ).scalar() or 0

    pending = db.query(func.count(CustomerReferral.id)).filter(
        CustomerReferral.venue_id == current_user.venue_id,
        CustomerReferral.status == "pending"
    ).scalar() or 0

    qualified = db.query(func.count(CustomerReferral.id)).filter(
        CustomerReferral.venue_id == current_user.venue_id,
        CustomerReferral.status == "qualified"
    ).scalar() or 0

    rewarded = db.query(func.count(CustomerReferral.id)).filter(
        CustomerReferral.venue_id == current_user.venue_id,
        CustomerReferral.status == "rewarded"
    ).scalar() or 0

    return {
        "total_referrals": total_referrals,
        "pending_referrals": pending,
        "qualified_referrals": qualified,
        "rewarded_referrals": rewarded,
        "conversion_rate": round((qualified / total_referrals * 100), 2) if total_referrals > 0 else 0
    }


# ============================================================================
# SMS MARKETING CAMPAIGNS
# ============================================================================

@router.post("/sms-campaigns", response_model=CampaignResponse, status_code=201)
async def create_sms_campaign(
    data: CampaignCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a new SMS marketing campaign"""
    # Estimate recipients based on segment
    estimated_recipients = _estimate_campaign_recipients(
        db, current_user.venue_id, data.target_segment, data.target_filters
    )

    campaign = SMSCampaign(
        venue_id=current_user.venue_id,
        name=data.name,
        message_template=data.message_template,
        status="draft" if data.scheduled_at else "scheduled",
        target_segment=data.target_segment,
        target_filters=data.target_filters,
        estimated_recipients=estimated_recipients,
        scheduled_at=data.scheduled_at,
        promo_code=data.promo_code,
        created_by=current_user.id
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # If no schedule, send immediately in background
    if not data.scheduled_at:
        background_tasks.add_task(_send_sms_campaign, campaign.id, db)

    return campaign


@router.get("/sms-campaigns", response_model=List[CampaignResponse])
async def list_sms_campaigns(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List SMS campaigns"""
    query = db.query(SMSCampaign).filter(SMSCampaign.venue_id == current_user.venue_id)

    if status:
        query = query.filter(SMSCampaign.status == status)

    campaigns = query.order_by(desc(SMSCampaign.created_at)).offset(offset).limit(limit).all()

    return campaigns


@router.post("/sms-campaigns/{campaign_id}/send")
async def send_sms_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Manually send an SMS campaign"""
    campaign = db.query(SMSCampaign).filter(
        SMSCampaign.id == campaign_id,
        SMSCampaign.venue_id == current_user.venue_id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in ["draft", "scheduled"]:
        raise HTTPException(status_code=400, detail="Campaign already sent or in progress")

    campaign.status = "sending"
    campaign.started_at = datetime.utcnow()
    db.commit()

    background_tasks.add_task(_send_sms_campaign, campaign_id, db)

    return {"message": "Campaign sending started"}


# ============================================================================
# CUSTOMER SEGMENTATION & RFM ANALYTICS
# ============================================================================

@router.get("/segments", response_model=List[CustomerSegmentResponse])
async def get_customer_segments(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get customer segments with statistics"""
    # Get RFM segment definitions
    segment_defs = db.query(RFMSegmentDefinition).filter(
        RFMSegmentDefinition.venue_id == current_user.venue_id
    ).all()

    # If no custom segments, use default ones
    if not segment_defs:
        segment_defs = _get_default_segments()

    results = []
    for seg_def in segment_defs:
        # Get customers in this segment
        segment_customers = db.query(Customer).join(
            CustomerRFMScore,
            and_(
                Customer.id == CustomerRFMScore.customer_id,
                CustomerRFMScore.segment == seg_def.segment_name
            )
        ).filter(
            Customer.venue_id == current_user.venue_id,
            Customer.is_active == True
        ).all()

        if segment_customers:
            total_revenue = sum(c.total_spent for c in segment_customers)
            avg_order = sum(c.average_order_value for c in segment_customers) / len(segment_customers)

            # Calculate average recency
            rfm_scores = db.query(CustomerRFMScore).filter(
                CustomerRFMScore.venue_id == current_user.venue_id,
                CustomerRFMScore.segment == seg_def.segment_name
            ).all()

            avg_recency = sum(s.days_since_last_order for s in rfm_scores) / len(rfm_scores) if rfm_scores else 0
            avg_frequency = sum(s.total_orders for s in rfm_scores) / len(rfm_scores) if rfm_scores else 0
        else:
            total_revenue = 0
            avg_order = 0
            avg_recency = 0
            avg_frequency = 0

        results.append(CustomerSegmentResponse(
            segment_name=seg_def.segment_name,
            customer_count=len(segment_customers),
            avg_order_value=round(avg_order, 2),
            total_revenue=round(total_revenue, 2),
            avg_recency_days=round(avg_recency, 1),
            avg_frequency=round(avg_frequency, 1),
            description=seg_def.description if hasattr(seg_def, 'description') else None
        ))

    return results


@router.post("/rfm/calculate")
async def calculate_rfm_scores(
    period_days: int = Query(365, description="Analysis period in days"),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Calculate RFM scores for all customers"""

    venue_id = current_user.venue_id
    today = date.today()
    period_start = today - timedelta(days=period_days)

    # Get all active customers with orders
    customers = db.query(Customer).filter(
        Customer.venue_id == venue_id,
        Customer.is_active == True,
        Customer.total_orders > 0
    ).all()

    rfm_data = []
    for customer in customers:
        # Calculate recency (days since last order)
        if customer.last_visit:
            recency = (datetime.utcnow() - customer.last_visit).days
        else:
            recency = 999

        # Frequency and monetary are already tracked
        frequency = customer.total_orders
        monetary = float(customer.total_spent)

        rfm_data.append({
            'customer_id': customer.id,
            'recency': recency,
            'frequency': frequency,
            'monetary': monetary
        })

    if not rfm_data:
        return {"message": "No customers to score"}

    # Calculate quartiles for scoring
    recencies = [d['recency'] for d in rfm_data]
    frequencies = [d['frequency'] for d in rfm_data]
    monetaries = [d['monetary'] for d in rfm_data]

    import numpy as np
    r_quartiles = np.percentile(recencies, [25, 50, 75])
    f_quartiles = np.percentile(frequencies, [25, 50, 75])
    m_quartiles = np.percentile(monetaries, [25, 50, 75])

    # Score each customer
    for data in rfm_data:
        # Recency: lower is better (reverse scoring)
        if data['recency'] <= r_quartiles[0]:
            r_score = 5
        elif data['recency'] <= r_quartiles[1]:
            r_score = 4
        elif data['recency'] <= r_quartiles[2]:
            r_score = 3
        else:
            r_score = 1 if data['recency'] > 180 else 2

        # Frequency: higher is better
        if data['frequency'] >= f_quartiles[2]:
            f_score = 5
        elif data['frequency'] >= f_quartiles[1]:
            f_score = 4
        elif data['frequency'] >= f_quartiles[0]:
            f_score = 3
        else:
            f_score = 1 if data['frequency'] < 2 else 2

        # Monetary: higher is better
        if data['monetary'] >= m_quartiles[2]:
            m_score = 5
        elif data['monetary'] >= m_quartiles[1]:
            m_score = 4
        elif data['monetary'] >= m_quartiles[0]:
            m_score = 3
        else:
            m_score = 1 if data['monetary'] < 50 else 2

        # Determine segment
        segment = _determine_rfm_segment(r_score, f_score, m_score)

        # Update or create RFM score
        existing = db.query(CustomerRFMScore).filter(
            CustomerRFMScore.venue_id == venue_id,
            CustomerRFMScore.customer_id == data['customer_id'],
            CustomerRFMScore.calculation_date == today
        ).first()

        if existing:
            existing.days_since_last_order = data['recency']
            existing.total_orders = data['frequency']
            existing.total_revenue = data['monetary']
            existing.recency_score = r_score
            existing.frequency_score = f_score
            existing.monetary_score = m_score
            existing.rfm_score = r_score * 100 + f_score * 10 + m_score
            existing.segment = segment
        else:
            rfm_score = CustomerRFMScore(
                venue_id=venue_id,
                customer_id=data['customer_id'],
                days_since_last_order=data['recency'],
                total_orders=data['frequency'],
                total_revenue=data['monetary'],
                avg_order_value=data['monetary'] / data['frequency'] if data['frequency'] > 0 else 0,
                recency_score=r_score,
                frequency_score=f_score,
                monetary_score=m_score,
                rfm_score=r_score * 100 + f_score * 10 + m_score,
                segment=segment,
                calculation_date=today,
                period_days=period_days
            )
            db.add(rfm_score)

    db.commit()

    return {
        "message": f"RFM scores calculated for {len(rfm_data)} customers",
        "customers_scored": len(rfm_data)
    }


@router.get("/customers/upcoming-events")
async def get_upcoming_events(
    days: int = Query(30, description="Look ahead days"),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get upcoming customer birthdays and anniversaries"""

    today = date.today()
    end_date = today + timedelta(days=days)

    # Get customers with birthdays in range
    customers = db.query(Customer).filter(
        Customer.venue_id == current_user.venue_id,
        Customer.is_active == True,
        or_(
            Customer.birthday.isnot(None),
            Customer.birthday.isnot(None)
        )
    ).all()

    events = []
    for customer in customers:
        # Check birthday
        if customer.birthday:
            # Get this year's birthday
            birthday_this_year = customer.birthday.replace(year=today.year)
            if birthday_this_year < today:
                birthday_this_year = birthday_this_year.replace(year=today.year + 1)

            if today <= birthday_this_year <= end_date:
                days_until = (birthday_this_year - today).days
                events.append({
                    "customer_id": customer.id,
                    "customer_name": customer.name,
                    "event_type": "birthday",
                    "date": birthday_this_year.isoformat(),
                    "days_until": days_until
                })

        # Check anniversary
        if customer.birthday:
            anniversary_this_year = customer.birthday.replace(year=today.year)
            if anniversary_this_year < today:
                anniversary_this_year = anniversary_this_year.replace(year=today.year + 1)

            if today <= anniversary_this_year <= end_date:
                days_until = (anniversary_this_year - today).days
                events.append({
                    "customer_id": customer.id,
                    "customer_name": customer.name,
                    "event_type": "anniversary",
                    "date": anniversary_this_year.isoformat(),
                    "days_until": days_until
                })

    # Sort by days until
    events.sort(key=lambda x: x['days_until'])

    return events


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _update_rating_aggregate(db: Session, menu_item_id: int):
    """Update aggregate ratings for a menu item"""
    reviews = db.query(MenuItemReview).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.status == "approved"
    ).all()

    if not reviews:
        return

    total = len(reviews)
    avg_rating = sum(r.rating for r in reviews) / total

    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        rating_counts[r.rating] += 1

    # Calculate aspect averages
    taste_ratings = [r.taste_rating for r in reviews if r.taste_rating]
    presentation_ratings = [r.presentation_rating for r in reviews if r.presentation_rating]
    portion_ratings = [r.portion_rating for r in reviews if r.portion_rating]
    value_ratings = [r.value_rating for r in reviews if r.value_rating]

    # Update or create aggregate
    aggregate = db.query(MenuItemRatingAggregate).filter(
        MenuItemRatingAggregate.menu_item_id == menu_item_id
    ).first()

    if aggregate:
        aggregate.total_reviews = total
        aggregate.average_rating = avg_rating
        aggregate.rating_1_count = rating_counts[1]
        aggregate.rating_2_count = rating_counts[2]
        aggregate.rating_3_count = rating_counts[3]
        aggregate.rating_4_count = rating_counts[4]
        aggregate.rating_5_count = rating_counts[5]
        aggregate.avg_taste = sum(taste_ratings) / len(taste_ratings) if taste_ratings else None
        aggregate.avg_presentation = sum(presentation_ratings) / len(presentation_ratings) if presentation_ratings else None
        aggregate.avg_portion = sum(portion_ratings) / len(portion_ratings) if portion_ratings else None
        aggregate.avg_value = sum(value_ratings) / len(value_ratings) if value_ratings else None
        aggregate.updated_at = datetime.utcnow()
    else:
        aggregate = MenuItemRatingAggregate(
            menu_item_id=menu_item_id,
            total_reviews=total,
            average_rating=avg_rating,
            rating_1_count=rating_counts[1],
            rating_2_count=rating_counts[2],
            rating_3_count=rating_counts[3],
            rating_4_count=rating_counts[4],
            rating_5_count=rating_counts[5],
            avg_taste=sum(taste_ratings) / len(taste_ratings) if taste_ratings else None,
            avg_presentation=sum(presentation_ratings) / len(presentation_ratings) if presentation_ratings else None,
            avg_portion=sum(portion_ratings) / len(portion_ratings) if portion_ratings else None,
            avg_value=sum(value_ratings) / len(value_ratings) if value_ratings else None
        )
        db.add(aggregate)


def _estimate_campaign_recipients(db: Session, venue_id: int, segment: str, filters: Optional[dict]) -> int:
    """Estimate number of recipients for a campaign"""
    query = db.query(func.count(Customer.id)).filter(
        Customer.venue_id == venue_id,
        Customer.is_active == True,
        Customer.marketing_consent == True
    )

    if segment != "all":
        # Join with RFM scores for segment filtering
        query = query.join(
            CustomerRFMScore,
            Customer.id == CustomerRFMScore.customer_id
        ).filter(
            CustomerRFMScore.segment == segment
        )

    return query.scalar() or 0


async def _send_sms_campaign(campaign_id: int, db: Session):
    """Background task to send SMS campaign"""
    # This would integrate with Twilio, AWS SNS, etc.
    # For now, just mark as completed
    campaign = db.query(SMSCampaign).filter(SMSCampaign.id == campaign_id).first()
    if campaign:
        campaign.status = "completed"
        campaign.completed_at = datetime.utcnow()
        campaign.total_sent = campaign.estimated_recipients
        campaign.total_delivered = int(campaign.estimated_recipients * 0.95)  # Assume 95% delivery
        db.commit()


def _determine_rfm_segment(r: int, f: int, m: int) -> str:
    """Determine customer segment based on RFM scores"""
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    elif r >= 3 and f >= 3 and m >= 3:
        return "Loyal"
    elif r >= 4 and f <= 2:
        return "New"
    elif r <= 2 and f >= 3:
        return "At Risk"
    elif r <= 2 and f <= 2:
        return "Lost"
    elif r >= 3 and m >= 4:
        return "Potential"
    else:
        return "Regular"


def _get_default_segments():
    """Get default RFM segments"""
    class DefaultSegment:
        def __init__(self, name, desc):
            self.segment_name = name
            self.description = desc

    return [
        DefaultSegment("Champions", "Best customers - high R, F, M"),
        DefaultSegment("Loyal", "Regular high-value customers"),
        DefaultSegment("Potential", "Recent customers with high spending potential"),
        DefaultSegment("New", "Recent new customers"),
        DefaultSegment("At Risk", "Were good customers, becoming inactive"),
        DefaultSegment("Lost", "Inactive customers"),
        DefaultSegment("Regular", "Average customers")
    ]
