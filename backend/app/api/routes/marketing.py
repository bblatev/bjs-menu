"""Marketing Automation routes - SpotOn style."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from app.db.session import DbSession
from app.models.marketing import (
    MarketingCampaign, CustomerSegment, AutomatedTrigger,
    LoyaltyProgram, CustomerLoyalty, MenuRecommendation
)
from app.services.marketing_service import (
    MarketingAutomationService, AutomatedTriggerService,
    MenuRecommendationService, LoyaltyService
)
from app.schemas.marketing import (
    CampaignCreate, CampaignUpdate, CampaignResponse, CampaignStats,
    SegmentCreate, SegmentUpdate, SegmentResponse, SegmentPreview,
    TriggerCreate, TriggerUpdate, TriggerResponse,
    LoyaltyProgramCreate, LoyaltyProgramResponse,
    CustomerLoyaltyResponse, LoyaltyTransaction, LoyaltyRedemption, LoyaltyRedemptionResponse,
    MenuRecommendationResponse, CustomerRecommendations,
    AICampaignRequest, AICampaignResponse
)

router = APIRouter()


# Marketing Campaigns

@router.get("/campaigns/", response_model=List[CampaignResponse])
def list_campaigns(
    db: DbSession,
    status: Optional[str] = None,
    campaign_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """List marketing campaigns."""
    query = db.query(MarketingCampaign)
    if status:
        query = query.filter(MarketingCampaign.status == status)
    if campaign_type:
        query = query.filter(MarketingCampaign.campaign_type == campaign_type)
    return query.order_by(MarketingCampaign.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
def get_campaign(db: DbSession, campaign_id: int):
    """Get campaign by ID."""
    campaign = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/campaigns/", response_model=CampaignResponse)
def create_campaign(db: DbSession, campaign: CampaignCreate):
    """Create a new marketing campaign."""
    db_campaign = MarketingCampaign(**campaign.model_dump())
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    db: DbSession,
    campaign_id: int,
    campaign: CampaignUpdate,
):
    """Update a campaign."""
    db_campaign = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    for key, value in campaign.model_dump(exclude_unset=True).items():
        setattr(db_campaign, key, value)

    db.commit()
    db.refresh(db_campaign)
    return db_campaign


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    db: DbSession,
    campaign_id: int,
    background_tasks: BackgroundTasks,
):
    """Send a marketing campaign."""
    service = MarketingAutomationService(db)
    result = await service.send_campaign(campaign_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/campaigns/{campaign_id}/stats", response_model=CampaignStats)
def get_campaign_stats(db: DbSession, campaign_id: int):
    """Get campaign statistics."""
    campaign = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    sent = campaign.total_sent or 0
    opened = campaign.total_opened or 0
    clicked = campaign.total_clicked or 0
    open_rate = (opened / sent * 100) if sent > 0 else 0
    click_rate = (clicked / sent * 100) if sent > 0 else 0

    return CampaignStats(
        campaign_id=campaign.id,
        total_sent=sent,
        total_delivered=campaign.total_delivered or sent,
        total_opened=opened,
        open_rate=open_rate,
        total_clicked=clicked,
        click_rate=click_rate,
        total_unsubscribed=0,
        total_revenue=campaign.total_revenue or 0,
        roi=float(campaign.total_revenue or 0) / 100 if campaign.total_revenue else 0
    )


@router.post("/campaigns/generate-ai", response_model=AICampaignResponse)
async def generate_ai_campaign(
    db: DbSession,
    request: AICampaignRequest,
):
    """Generate campaign content using AI."""
    service = MarketingAutomationService(db)
    result = await service.generate_ai_campaign(
        campaign_type=request.campaign_type,
        target_segment=request.target_segment,
        promotion_details=request.promotion_details,
        tone=request.tone
    )
    return result


# Customer Segments

@router.get("/segments/", response_model=List[SegmentResponse])
def list_segments(db: DbSession):
    """List customer segments."""
    return db.query(CustomerSegment).filter(CustomerSegment.is_active == True).all()


@router.get("/segments/{segment_id}", response_model=SegmentResponse)
def get_segment(db: DbSession, segment_id: int):
    """Get segment by ID."""
    segment = db.query(CustomerSegment).filter(CustomerSegment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@router.post("/segments/", response_model=SegmentResponse)
def create_segment(db: DbSession, segment: SegmentCreate):
    """Create a customer segment."""
    db_segment = CustomerSegment(**segment.model_dump())
    db.add(db_segment)
    db.commit()
    db.refresh(db_segment)
    return db_segment


@router.put("/segments/{segment_id}", response_model=SegmentResponse)
def update_segment(
    db: DbSession,
    segment_id: int,
    segment: SegmentUpdate,
):
    """Update a segment."""
    db_segment = db.query(CustomerSegment).filter(CustomerSegment.id == segment_id).first()
    if not db_segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    for key, value in segment.model_dump(exclude_unset=True).items():
        setattr(db_segment, key, value)

    db.commit()
    db.refresh(db_segment)
    return db_segment


@router.post("/segments/preview", response_model=SegmentPreview)
def preview_segment(db: DbSession, criteria: dict):
    """Preview customers matching segment criteria."""
    service = MarketingAutomationService(db)
    result = service.preview_segment(criteria)
    return result


# Automated Triggers

@router.get("/triggers/", response_model=List[TriggerResponse])
def list_triggers(db: DbSession):
    """List automated triggers."""
    return db.query(AutomatedTrigger).all()


@router.post("/triggers/", response_model=TriggerResponse)
def create_trigger(db: DbSession, trigger: TriggerCreate):
    """Create an automated trigger."""
    db_trigger = AutomatedTrigger(**trigger.model_dump())
    db.add(db_trigger)
    db.commit()
    db.refresh(db_trigger)
    return db_trigger


@router.put("/triggers/{trigger_id}", response_model=TriggerResponse)
def update_trigger(
    db: DbSession,
    trigger_id: int,
    trigger: TriggerUpdate,
):
    """Update a trigger."""
    db_trigger = db.query(AutomatedTrigger).filter(AutomatedTrigger.id == trigger_id).first()
    if not db_trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    for key, value in trigger.model_dump(exclude_unset=True).items():
        setattr(db_trigger, key, value)

    db.commit()
    db.refresh(db_trigger)
    return db_trigger


@router.post("/triggers/process-all")
async def process_all_triggers(db: DbSession):
    """Process all active triggers."""
    service = AutomatedTriggerService(db)
    results = await service.process_triggers()
    return {"processed": len(results), "results": results}


# Menu Recommendations ("Picked for You")

@router.get("/recommendations/{customer_id}")
def get_customer_recommendations(
    db: DbSession,
    customer_id: int,
    limit: int = 5,
):
    """Get personalized menu recommendations for a customer."""
    service = MenuRecommendationService(db)
    recommendations = service.get_recommendations(customer_id=customer_id)

    return {
        "customer_id": customer_id,
        "recommendations": recommendations[:limit],
        "generated_at": datetime.utcnow().isoformat()
    }


@router.post("/recommendations/{recommendation_id}/presented")
def mark_recommendation_presented(
    db: DbSession,
    recommendation_id: int,
):
    """Mark a recommendation as presented to customer."""
    rec = db.query(MenuRecommendation).filter(MenuRecommendation.id == recommendation_id).first()
    if rec:
        rec.is_presented = True
        rec.presented_at = datetime.utcnow()
        db.commit()
    return {"status": "ok"}


@router.post("/recommendations/{recommendation_id}/purchased")
def mark_recommendation_purchased(
    db: DbSession,
    recommendation_id: int,
):
    """Mark a recommendation as purchased."""
    rec = db.query(MenuRecommendation).filter(MenuRecommendation.id == recommendation_id).first()
    if rec:
        rec.is_purchased = True
        rec.purchased_at = datetime.utcnow()
        db.commit()
    return {"status": "ok"}


# Loyalty Program

@router.get("/loyalty/programs/", response_model=List[LoyaltyProgramResponse])
def list_loyalty_programs(db: DbSession):
    """List loyalty programs."""
    return db.query(LoyaltyProgram).all()


@router.post("/loyalty/programs/", response_model=LoyaltyProgramResponse)
def create_loyalty_program(db: DbSession, program: LoyaltyProgramCreate):
    """Create a loyalty program."""
    db_program = LoyaltyProgram(**program.model_dump())
    db.add(db_program)
    db.commit()
    db.refresh(db_program)
    return db_program


@router.get("/loyalty/customer/{customer_id}", response_model=CustomerLoyaltyResponse)
def get_customer_loyalty(db: DbSession, customer_id: int):
    """Get customer's loyalty status."""
    loyalty = db.query(CustomerLoyalty).filter(
        CustomerLoyalty.customer_id == customer_id
    ).first()

    if not loyalty:
        raise HTTPException(status_code=404, detail="Customer not in loyalty program")

    return loyalty


@router.post("/loyalty/earn")
def earn_loyalty_points(db: DbSession, transaction: LoyaltyTransaction):
    """Award loyalty points to a customer."""
    service = LoyaltyService(db)
    result = service.award_points(
        customer_id=transaction.customer_id,
        points=transaction.points,
        description=transaction.description,
        order_id=transaction.order_id
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/loyalty/redeem", response_model=LoyaltyRedemptionResponse)
def redeem_loyalty_points(db: DbSession, redemption: LoyaltyRedemption):
    """Redeem loyalty points."""
    service = LoyaltyService(db)
    result = service.redeem_points(
        customer_id=redemption.customer_id,
        points=redemption.points_to_redeem
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result
