"""V9 Financial Controls & CRM"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

from app.core.rbac import get_current_user
from app.core.rate_limit import limiter

# Import all services and schemas from shared
from app.api.routes.v9_endpoints._shared import *

router = APIRouter()

# ==================== FINANCIAL CONTROLS - PRIME COST ====================

@router.post("/financial/prime-cost", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def record_prime_cost(
    request: Request,
    period_date: date,
    food_cost: Decimal,
    beverage_cost: Decimal,
    labor_cost: Decimal,
    revenue: Decimal,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record prime cost data for a period"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PrimeCostService.record_prime_cost(
        db=db,
        venue_id=venue_id,
        period_date=period_date,
        food_cost=food_cost,
        beverage_cost=beverage_cost,
        labor_cost=labor_cost,
        revenue=revenue,
        notes=notes
    )


@router.get("/financial/prime-cost/dashboard", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_prime_cost_dashboard(
    request: Request,
    start_date: Optional[date] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get prime cost dashboard with trends and analysis"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PrimeCostService.get_prime_cost_dashboard(db, venue_id, start_date, end_date)


@router.get("/financial/profitability/{menu_item_id}", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_item_profitability(
    request: Request,
    menu_item_id: int,
    start_date: Optional[date] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Calculate profitability metrics for a menu item"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PrimeCostService.calculate_item_profitability(db, venue_id, menu_item_id, start_date, end_date)


@router.get("/financial/profit-leaderboard", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_profit_leaderboard(
    request: Request,
    start_date: Optional[date] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get top and bottom performing items by profitability"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PrimeCostService.get_profit_leaderboard(db, venue_id, start_date, end_date, limit)


# ==================== FINANCIAL CONTROLS - ABUSE DETECTION ====================

@router.get("/financial/abuse/config", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_abuse_config(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get abuse detection configuration"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AbuseDetectionService.get_or_create_abuse_config(db, venue_id)


@router.put("/financial/abuse/config", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def update_abuse_config(
    request: Request,
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update abuse detection configuration"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AbuseDetectionService.update_abuse_config(db, venue_id, updates)


@router.post("/financial/abuse/check", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def check_for_abuse(
    request: Request,
    staff_id: int,
    action_type: str,
    amount: Decimal,
    order_id: Optional[int] = None,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check if an action triggers abuse detection"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AbuseDetectionService.check_for_abuse(db, venue_id, staff_id, action_type, amount, order_id, reason)


@router.get("/financial/abuse/alerts", response_model=List[Dict[str, Any]], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_pending_abuse_alerts(
    request: Request,
    severity: Optional[str] = None,
    staff_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get pending abuse alerts for investigation"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AbuseDetectionService.get_pending_alerts(db, venue_id, severity, staff_id)


@router.post("/financial/abuse/investigate/{alert_id}", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("30/minute")
async def investigate_abuse_alert(
    request: Request,
    alert_id: int,
    status: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update alert investigation status"""
    investigator_id = current_user.id
    return AbuseDetectionService.investigate_alert(db, alert_id, investigator_id, status, notes)


@router.get("/financial/abuse/analytics", response_model=Dict[str, Any], tags=["V9 - Financial Controls"])
@limiter.limit("60/minute")
async def get_abuse_analytics(
    request: Request,
    start_date: Optional[date] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get abuse analytics for a period"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AbuseDetectionService.get_abuse_analytics(db, venue_id, start_date, end_date)


# ==================== CRM - GUEST PREFERENCES ====================

@router.post("/crm/preferences/{guest_id}", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("30/minute")
async def set_guest_preferences(
    request: Request,
    guest_id: int,
    preferences: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Set or update guest preferences"""
    if GuestPreferencesService is None:
        raise HTTPException(status_code=501, detail="Advanced CRM service is not available. Required dependencies are not installed.")
    return GuestPreferencesService.set_guest_preferences(db, guest_id, preferences)


@router.get("/crm/preferences/{guest_id}", response_model=Optional[Dict[str, Any]], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_guest_preferences(
    request: Request,
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all preferences for a guest"""
    if GuestPreferencesService is None:
        raise HTTPException(status_code=501, detail="Advanced CRM service is not available. Required dependencies are not installed.")
    return GuestPreferencesService.get_guest_preferences(db, guest_id)


@router.get("/crm/service-alerts/{guest_id}", response_model=List[Dict[str, Any]], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_service_alerts(
    request: Request,
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get service alerts for a guest (allergies, preferences, VIP status)"""
    if GuestPreferencesService is None:
        raise HTTPException(status_code=501, detail="Advanced CRM service is not available. Required dependencies are not installed.")
    return GuestPreferencesService.get_service_alerts(db, guest_id)


# ==================== CRM - CUSTOMER LIFETIME VALUE ====================

@router.get("/crm/clv/{guest_id}", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def calculate_clv(
    request: Request,
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Calculate Customer Lifetime Value for a guest"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if CustomerLifetimeValueService is None:
        raise HTTPException(status_code=501, detail="CRM CLV service is not available. Required dependencies are not installed.")
    return CustomerLifetimeValueService.calculate_clv(db, guest_id, venue_id)


@router.post("/crm/clv/update", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("30/minute")
async def update_clv_from_order(
    request: Request,
    guest_id: int,
    order_total: Decimal,
    order_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update CLV after a new order"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if not order_date:
        order_date = datetime.now(timezone.utc)
    if CustomerLifetimeValueService is None:
        raise HTTPException(status_code=501, detail="CRM CLV service is not available. Required dependencies are not installed.")
    return CustomerLifetimeValueService.update_clv_from_order(db, guest_id, venue_id, order_total, order_date)


@router.get("/crm/at-risk-customers", response_model=List[Dict[str, Any]], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_at_risk_customers(
    request: Request,
    risk_threshold: float = 0.6,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get customers at risk of churning"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return CustomerLifetimeValueService.get_at_risk_customers(db, venue_id, risk_threshold, limit)


# ==================== CRM - CUSTOMER SEGMENTS ====================

@router.get("/crm/segments", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_customer_segments(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get customer segmentation summary"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if CustomerSegmentationService is None:
        raise HTTPException(status_code=501, detail="Advanced CRM service is not available. Required dependencies are not installed.")
    return CustomerSegmentationService.get_customer_segments(db, venue_id)


# ==================== CRM - VIP MANAGEMENT ====================

@router.post("/crm/vip/{guest_id}", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("30/minute")
async def set_vip_status(
    request: Request,
    guest_id: int,
    vip_status: bool,
    vip_tier: Optional[str] = None,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Set or update VIP status for a guest"""
    set_by = current_user.id
    if VIPManagementService is None:
        raise HTTPException(status_code=501, detail="Advanced CRM service is not available. Required dependencies are not installed.")
    return VIPManagementService.set_vip_status(db, guest_id, vip_status, vip_tier, reason, set_by)


@router.get("/crm/vip", response_model=List[Dict[str, Any]], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_vip_guests(
    request: Request,
    tier: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all VIP guests, optionally filtered by tier"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if VIPManagementService is None:
        raise HTTPException(status_code=501, detail="Advanced CRM service is not available. Required dependencies are not installed.")
    return VIPManagementService.get_vip_guests(db, venue_id, tier)


# ==================== CRM - PERSONALIZATION ====================

@router.get("/crm/recommendations/{guest_id}", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_personalized_recommendations(
    request: Request,
    guest_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get personalized menu recommendations for a guest"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if PersonalizationService is None:
        raise HTTPException(status_code=501, detail="Advanced CRM service is not available. Required dependencies are not installed.")
    return PersonalizationService.get_personalized_recommendations(db, guest_id, venue_id, limit)


@router.post("/crm/feedback", response_model=Dict[str, Any], tags=["V9 - CRM"])
@limiter.limit("30/minute")
async def record_feedback(
    request: Request,
    guest_id: int,
    order_id: int,
    rating: int,
    feedback_type: str,
    comments: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record guest feedback for continuous improvement"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if PersonalizationService is None:
        raise HTTPException(status_code=501, detail="Advanced CRM service is not available. Required dependencies are not installed.")
    return PersonalizationService.record_feedback(db, guest_id, venue_id, order_id, rating, feedback_type, comments)


