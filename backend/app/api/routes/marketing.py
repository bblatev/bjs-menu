"""Marketing Automation routes - SpotOn style."""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Request

from app.db.session import DbSession
from app.core.rate_limit import limiter
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


# ==================== STUB ENDPOINTS ====================

@router.get("/promotions")
@limiter.limit("60/minute")
def get_promotions(request: Request, db: DbSession, active_only: bool = False):
    """Get promotions list."""
    from app.models.operations import Promotion
    query = db.query(Promotion)
    if active_only:
        query = query.filter(Promotion.active == True)
    promos = query.order_by(Promotion.created_at.desc()).all()
    items = [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "type": p.type,
            "value": float(p.value) if p.value else None,
            "code": p.code,
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "end_date": p.end_date.isoformat() if p.end_date else None,
            "active": p.active,
            "usage_count": p.usage_count,
            "usage_limit": p.usage_limit,
        }
        for p in promos
    ]
    return {"promotions": items, "total": len(items)}


@router.get("/stats")
@limiter.limit("60/minute")
def get_marketing_stats(request: Request, db: DbSession):
    """Get marketing statistics."""
    from sqlalchemy import func as sqlfunc
    total = db.query(sqlfunc.count(MarketingCampaign.id)).scalar() or 0
    active = db.query(sqlfunc.count(MarketingCampaign.id)).filter(
        MarketingCampaign.status == "active"
    ).scalar() or 0
    total_sent = db.query(sqlfunc.sum(MarketingCampaign.total_sent)).scalar() or 0
    total_opened = db.query(sqlfunc.sum(MarketingCampaign.total_opened)).scalar() or 0
    open_rate = round((total_opened / total_sent * 100), 1) if total_sent > 0 else 0
    total_revenue = db.query(sqlfunc.sum(MarketingCampaign.total_revenue)).scalar() or 0
    return {
        "total_campaigns": total,
        "active": active,
        "total_sent": int(total_sent),
        "open_rate": open_rate,
        "conversion_rate": 0,
        "total_revenue": float(total_revenue),
    }


@router.get("/pricing-rules")
@limiter.limit("60/minute")
def get_pricing_rules(request: Request, db: DbSession):
    """Get pricing rules."""
    from app.models.advanced_features import DynamicPricingRule
    rules = db.query(DynamicPricingRule).order_by(DynamicPricingRule.id).all()
    items = [
        {
            "id": r.id,
            "name": r.name,
            "trigger_type": r.trigger_type,
            "trigger_conditions": r.trigger_conditions,
            "adjustment_type": r.adjustment_type,
            "adjustment_value": float(r.adjustment_value),
            "applies_to": r.applies_to,
            "is_active": r.is_active,
        }
        for r in rules
    ]
    return {"rules": items, "total": len(items)}


@router.post("/pricing-rules")
@limiter.limit("30/minute")
def create_pricing_rule(request: Request, db: DbSession, data: dict = None):
    """Create a dynamic pricing rule."""
    from fastapi import Body
    from app.models.advanced_features import DynamicPricingRule
    if data is None:
        data = {}
    rule = DynamicPricingRule(
        name=data.get("name", ""),
        trigger_type=data.get("type", data.get("trigger_type", "manual")),
        trigger_conditions=data.get("trigger_conditions", {}),
        adjustment_type=data.get("adjustment_type", "percentage"),
        adjustment_value=data.get("value", data.get("adjustment_value", 0)),
        applies_to=data.get("applies_to", "all"),
        is_active=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"id": rule.id, "name": rule.name, "is_active": rule.is_active}


@router.patch("/pricing-rules/{rule_id}/toggle-active")
@limiter.limit("30/minute")
def toggle_pricing_rule_active(request: Request, rule_id: int, db: DbSession):
    """Toggle a pricing rule's active status."""
    from app.models.advanced_features import DynamicPricingRule
    rule = db.query(DynamicPricingRule).filter(DynamicPricingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")

    rule.is_active = not rule.is_active
    db.commit()
    db.refresh(rule)
    return {"success": True, "id": rule.id, "is_active": rule.is_active}


@router.post("/promotions/")
@limiter.limit("30/minute")
def create_marketing_promotion(request: Request, db: DbSession, data: dict = None):
    """Create a promotion via marketing route."""
    from fastapi import Body
    from app.models.operations import Promotion
    if data is None:
        data = {}
    promo = Promotion(
        name=data.get("name", ""),
        description=data.get("description", ""),
        type=data.get("type", "percentage"),
        value=data.get("value", 0),
        active=data.get("status", "active") == "active",
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return {"id": promo.id, "name": promo.name, "active": promo.active}


# Marketing Campaigns

@router.get("/campaigns/", response_model=List[CampaignResponse])
@limiter.limit("60/minute")
def list_campaigns(
    request: Request,
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
@limiter.limit("60/minute")
def get_campaign(request: Request, db: DbSession, campaign_id: int):
    """Get campaign by ID."""
    campaign = db.query(MarketingCampaign).filter(MarketingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/campaigns/", response_model=CampaignResponse)
@limiter.limit("30/minute")
def create_campaign(request: Request, db: DbSession, campaign: CampaignCreate):
    """Create a new marketing campaign."""
    db_campaign = MarketingCampaign(**campaign.model_dump())
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
@limiter.limit("30/minute")
def update_campaign(
    request: Request,
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
@limiter.limit("30/minute")
async def send_campaign(
    request: Request,
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
@limiter.limit("60/minute")
def get_campaign_stats(request: Request, db: DbSession, campaign_id: int):
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
@limiter.limit("30/minute")
async def generate_ai_campaign(
    request: Request,
    db: DbSession,
    body: AICampaignRequest,
):
    """Generate campaign content using AI."""
    service = MarketingAutomationService(db)
    result = await service.generate_ai_campaign(
        campaign_type=body.campaign_type,
        target_segment=body.target_segment,
        promotion_details=body.promotion_details,
        tone=body.tone
    )
    return result


# Customer Segments

@router.get("/segments/", response_model=List[SegmentResponse])
@limiter.limit("60/minute")
def list_segments(request: Request, db: DbSession):
    """List customer segments."""
    return db.query(CustomerSegment).filter(CustomerSegment.is_active == True).all()


@router.get("/segments/{segment_id}", response_model=SegmentResponse)
@limiter.limit("60/minute")
def get_segment(request: Request, db: DbSession, segment_id: int):
    """Get segment by ID."""
    segment = db.query(CustomerSegment).filter(CustomerSegment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@router.post("/segments/", response_model=SegmentResponse)
@limiter.limit("30/minute")
def create_segment(request: Request, db: DbSession, segment: SegmentCreate):
    """Create a customer segment."""
    db_segment = CustomerSegment(**segment.model_dump())
    db.add(db_segment)
    db.commit()
    db.refresh(db_segment)
    return db_segment


@router.put("/segments/{segment_id}", response_model=SegmentResponse)
@limiter.limit("30/minute")
def update_segment(
    request: Request,
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
@limiter.limit("30/minute")
def preview_segment(request: Request, db: DbSession, criteria: dict):
    """Preview customers matching segment criteria."""
    service = MarketingAutomationService(db)
    result = service.preview_segment(criteria)
    return result


# Automated Triggers

@router.get("/triggers/", response_model=List[TriggerResponse])
@limiter.limit("60/minute")
def list_triggers(request: Request, db: DbSession):
    """List automated triggers."""
    return db.query(AutomatedTrigger).all()


@router.post("/triggers/", response_model=TriggerResponse)
@limiter.limit("30/minute")
def create_trigger(request: Request, db: DbSession, trigger: TriggerCreate):
    """Create an automated trigger."""
    db_trigger = AutomatedTrigger(**trigger.model_dump())
    db.add(db_trigger)
    db.commit()
    db.refresh(db_trigger)
    return db_trigger


@router.put("/triggers/{trigger_id}", response_model=TriggerResponse)
@limiter.limit("30/minute")
def update_trigger(
    request: Request,
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
@limiter.limit("30/minute")
async def process_all_triggers(request: Request, db: DbSession):
    """Process all active triggers."""
    service = AutomatedTriggerService(db)
    results = await service.process_triggers()
    return {"processed": len(results), "results": results}


# Menu Recommendations ("Picked for You")

@router.get("/recommendations/{customer_id}")
@limiter.limit("60/minute")
def get_customer_recommendations(
    request: Request,
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
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/recommendations/{recommendation_id}/presented")
@limiter.limit("30/minute")
def mark_recommendation_presented(
    request: Request,
    db: DbSession,
    recommendation_id: int,
):
    """Mark a recommendation as presented to customer."""
    rec = db.query(MenuRecommendation).filter(MenuRecommendation.id == recommendation_id).first()
    if rec:
        rec.is_presented = True
        rec.presented_at = datetime.now(timezone.utc)
        db.commit()
    return {"status": "ok"}


@router.post("/recommendations/{recommendation_id}/purchased")
@limiter.limit("30/minute")
def mark_recommendation_purchased(
    request: Request,
    db: DbSession,
    recommendation_id: int,
):
    """Mark a recommendation as purchased."""
    rec = db.query(MenuRecommendation).filter(MenuRecommendation.id == recommendation_id).first()
    if rec:
        rec.is_purchased = True
        rec.purchased_at = datetime.now(timezone.utc)
        db.commit()
    return {"status": "ok"}


# Loyalty Program

@router.get("/loyalty/programs/", response_model=List[LoyaltyProgramResponse])
@limiter.limit("60/minute")
def list_loyalty_programs(request: Request, db: DbSession):
    """List loyalty programs."""
    return db.query(LoyaltyProgram).all()


@router.post("/loyalty/programs/", response_model=LoyaltyProgramResponse)
@limiter.limit("30/minute")
def create_loyalty_program(request: Request, db: DbSession, program: LoyaltyProgramCreate):
    """Create a loyalty program."""
    db_program = LoyaltyProgram(**program.model_dump())
    db.add(db_program)
    db.commit()
    db.refresh(db_program)
    return db_program


@router.get("/loyalty/customer/{customer_id}", response_model=CustomerLoyaltyResponse)
@limiter.limit("60/minute")
def get_customer_loyalty(request: Request, db: DbSession, customer_id: int):
    """Get customer's loyalty status."""
    loyalty = db.query(CustomerLoyalty).filter(
        CustomerLoyalty.customer_id == customer_id
    ).first()

    if not loyalty:
        raise HTTPException(status_code=404, detail="Customer not in loyalty program")

    return loyalty


@router.post("/loyalty/earn")
@limiter.limit("30/minute")
def earn_loyalty_points(request: Request, db: DbSession, transaction: LoyaltyTransaction):
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
@limiter.limit("30/minute")
def redeem_loyalty_points(request: Request, db: DbSession, redemption: LoyaltyRedemption):
    """Redeem loyalty points."""
    service = LoyaltyService(db)
    result = service.redeem_points(
        customer_id=redemption.customer_id,
        points=redemption.points_to_redeem
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result
