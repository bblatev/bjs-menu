"""AI Assistant API routes - Conversational AI, P&L Analysis, Demand Forecasting, Auto-Planning."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional
from datetime import date, datetime, timedelta
from pydantic import BaseModel, Field
import logging

from app.db.session import DbSession
from app.core.rbac import CurrentUser, OptionalCurrentUser
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== SCHEMAS ====================

class AIQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    conversation_id: Optional[str] = None


class AIQueryResponse(BaseModel):
    message: str
    data: dict = {}
    chart_type: Optional[str] = None
    suggestions: List[str] = []
    sql_query: Optional[str] = None
    intent: Optional[str] = None
    conversation_id: str


class AIInsightResponse(BaseModel):
    id: int
    insight_type: str
    category: str
    severity: str
    title: str
    description: str
    data: dict = {}
    recommendations: List[str] = []
    potential_impact: Optional[float] = None
    is_read: bool = False
    created_at: str


class MenuCommandRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=500)
    preview_only: bool = True


class PLAnalysisResponse(BaseModel):
    metrics: dict
    insights: List[str]
    opportunities: List[dict]
    trend_data: dict


class PLSnapshotResponse(BaseModel):
    id: int
    period_type: str
    period_start: str
    period_end: str
    gross_revenue: float
    net_profit: float
    net_margin_pct: float
    food_cost_pct: float
    labor_cost_pct: float
    prime_cost_pct: float
    order_count: int
    avg_ticket: float
    created_at: str


class SavingOpportunityResponse(BaseModel):
    id: int
    category: str
    title: str
    current_value: float
    target_value: float
    potential_savings: float
    recommendations: List[str]
    status: str
    priority: int
    created_at: str


class OpportunityUpdateRequest(BaseModel):
    status: str
    actual_savings: Optional[float] = None


class DemandForecastResponse(BaseModel):
    daily_forecasts: List[dict]
    item_forecasts: List[dict]
    confidence_level: float
    model_version: str


class ScheduleProposalResponse(BaseModel):
    id: int
    week_start: str
    week_end: str
    status: str
    total_labor_hours: float
    estimated_labor_cost: float
    coverage_score: float
    shifts_data: List[dict]
    created_at: str


class PurchasePlanResponse(BaseModel):
    id: int
    plan_date: str
    status: str
    total_cost: float
    purchase_orders: List[dict]
    created_at: str


class ProposalApprovalRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None


# ==================== In-memory stores ====================
_conversations: list = []
_insights: list = []
_snapshots: list = []
_opportunities: list = []
_forecasts: list = []
_schedule_proposals: list = []
_purchase_plans: list = []
_next_ids = {
    "conversation": 1, "insight": 1, "snapshot": 1,
    "opportunity": 1, "schedule": 1, "purchase": 1,
}


# ==================== CONVERSATIONAL AI ENDPOINTS ====================

@router.post("/ai-assistant/query", response_model=AIQueryResponse)
@limiter.limit("30/minute")
def process_ai_query(request: Request, data: AIQueryRequest, db: DbSession, current_user: CurrentUser = None):
    """Process natural language query with AI assistant."""
    import uuid
    conversation_id = data.conversation_id or str(uuid.uuid4())

    # Placeholder AI response
    return AIQueryResponse(
        message=f"I received your query: '{data.query}'. AI processing is not yet configured.",
        data={},
        chart_type=None,
        suggestions=["Try asking about sales", "Ask about top items", "Compare periods"],
        sql_query=None,
        intent="general_query",
        conversation_id=conversation_id,
    )


@router.get("/ai-assistant/insights", response_model=List[AIInsightResponse])
@limiter.limit("60/minute")
def get_ai_insights(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    limit: int = Query(5, ge=1, le=20), include_dismissed: bool = False,
):
    """Get proactive AI-generated business insights."""
    now = datetime.utcnow().isoformat()
    # Return placeholder insights
    return [
        AIInsightResponse(
            id=1, insight_type="trend", category="sales",
            severity="info", title="Sales Trend Analysis",
            description="AI insights will appear here once the AI service is configured.",
            data={}, recommendations=["Configure AI service for real insights"],
            potential_impact=None, is_read=False, created_at=now,
        )
    ][:limit]


@router.post("/ai-assistant/insights/{insight_id}/read")
@limiter.limit("30/minute")
def mark_insight_read(request: Request, insight_id: int, db: DbSession, current_user: CurrentUser = None):
    """Mark an insight as read."""
    return {"status": "ok"}


@router.post("/ai-assistant/insights/{insight_id}/dismiss")
@limiter.limit("30/minute")
def dismiss_insight(request: Request, insight_id: int, db: DbSession, current_user: CurrentUser = None):
    """Dismiss an insight."""
    return {"status": "ok"}


@router.post("/ai-assistant/menu-command")
@limiter.limit("30/minute")
def execute_menu_command(request: Request, data: MenuCommandRequest, db: DbSession, current_user: CurrentUser = None):
    """Execute a natural language menu command."""
    return {
        "command": data.command,
        "preview_only": data.preview_only,
        "changes": [],
        "message": "Menu command processing is not yet configured.",
    }


@router.get("/ai-assistant/conversations")
@limiter.limit("60/minute")
def get_conversations(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    limit: int = Query(10, ge=1, le=50),
):
    """Get recent AI conversations."""
    return _conversations[:limit]


@router.get("/ai-assistant/conversations/{session_id}/messages")
@limiter.limit("60/minute")
def get_conversation_messages(
    request: Request,
    session_id: str, db: DbSession, current_user: CurrentUser = None,
    limit: int = Query(50, ge=1, le=100),
):
    """Get messages from a conversation."""
    return []


# ==================== P&L ANALYSIS ENDPOINTS ====================

@router.get("/profit-assist/analysis", response_model=PLAnalysisResponse)
@limiter.limit("60/minute")
def get_pl_analysis(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    period: str = Query("last_30_days"),
):
    """Get comprehensive P&L analysis with AI insights."""
    return PLAnalysisResponse(
        metrics={
            "gross_revenue": 0.0,
            "net_profit": 0.0,
            "food_cost_pct": 0.0,
            "labor_cost_pct": 0.0,
            "prime_cost_pct": 0.0,
        },
        insights=["P&L analysis will be available once data is collected."],
        opportunities=[],
        trend_data={"revenue": [], "costs": []},
    )


@router.get("/profit-assist/comparison")
@limiter.limit("60/minute")
def get_pl_comparison(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    current_period: str = Query("last_7_days"),
    comparison_period: str = Query("last_7_days"),
):
    """Compare P&L metrics between two periods."""
    return {
        "current_period": current_period,
        "comparison_period": comparison_period,
        "metrics": {},
        "changes": {},
    }


@router.post("/profit-assist/snapshots", response_model=PLSnapshotResponse)
@limiter.limit("30/minute")
def create_pl_snapshot(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    period_type: str = Query("daily"),
):
    """Create a P&L snapshot for record-keeping."""
    global _next_ids
    now = datetime.utcnow()
    today = date.today()

    snapshot = PLSnapshotResponse(
        id=_next_ids["snapshot"],
        period_type=period_type,
        period_start=str(today - timedelta(days=1)),
        period_end=str(today - timedelta(days=1)),
        gross_revenue=0.0,
        net_profit=0.0,
        net_margin_pct=0.0,
        food_cost_pct=0.0,
        labor_cost_pct=0.0,
        prime_cost_pct=0.0,
        order_count=0,
        avg_ticket=0.0,
        created_at=now.isoformat(),
    )
    _next_ids["snapshot"] += 1
    return snapshot


@router.get("/profit-assist/snapshots", response_model=List[PLSnapshotResponse])
@limiter.limit("60/minute")
def get_pl_snapshots(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    period_type: Optional[str] = None,
    limit: int = Query(30, ge=1, le=100),
):
    """Get historical P&L snapshots."""
    return []


@router.get("/profit-assist/opportunities", response_model=List[SavingOpportunityResponse])
@limiter.limit("60/minute")
def get_saving_opportunities(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    status: Optional[str] = Query(None),
):
    """Get cost saving opportunities."""
    return []


@router.patch("/profit-assist/opportunities/{opportunity_id}", response_model=SavingOpportunityResponse)
@limiter.limit("30/minute")
def update_opportunity(
    request: Request,
    opportunity_id: int, data: OpportunityUpdateRequest,
    db: DbSession, current_user: CurrentUser = None,
):
    """Update a saving opportunity status."""
    raise HTTPException(status_code=404, detail="Opportunity not found")


# ==================== DEMAND FORECASTING ENDPOINTS ====================

@router.get("/forecasting/demand", response_model=DemandForecastResponse)
@limiter.limit("60/minute")
def get_demand_forecast(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    days: int = Query(7, ge=1, le=30),
):
    """Get demand forecast for the next N days."""
    return DemandForecastResponse(
        daily_forecasts=[],
        item_forecasts=[],
        confidence_level=0.0,
        model_version="placeholder-v1",
    )


@router.get("/forecasting/accuracy")
@limiter.limit("60/minute")
def get_forecast_accuracy(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    days: int = Query(30, ge=7, le=90),
):
    """Get forecast accuracy metrics."""
    return {
        "period_days": days,
        "accuracy_metrics": {},
        "message": "Forecast accuracy will be available once forecasting data is collected.",
    }


@router.post("/forecasting/demand/save")
@limiter.limit("30/minute")
def save_demand_forecast(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    days: int = Query(7, ge=1, le=30),
):
    """Generate and save demand forecast to database."""
    return {"status": "ok", "forecasts_saved": 0}


# ==================== AUTO-PLANNING ENDPOINTS ====================

@router.post("/auto-planning/schedule", response_model=ScheduleProposalResponse)
@limiter.limit("30/minute")
def generate_schedule_proposal(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    week_start: date = Query(..., description="Start date of the week (Monday)"),
):
    """Auto-generate staff schedule based on demand forecast."""
    global _next_ids
    now = datetime.utcnow()
    week_end = week_start + timedelta(days=6)

    proposal = ScheduleProposalResponse(
        id=_next_ids["schedule"],
        week_start=str(week_start),
        week_end=str(week_end),
        status="draft",
        total_labor_hours=0.0,
        estimated_labor_cost=0.0,
        coverage_score=0.0,
        shifts_data=[],
        created_at=now.isoformat(),
    )
    _next_ids["schedule"] += 1
    return proposal


@router.get("/auto-planning/schedules", response_model=List[ScheduleProposalResponse])
@limiter.limit("60/minute")
def get_schedule_proposals(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    status: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Get schedule proposals."""
    return []


@router.post("/auto-planning/schedules/{proposal_id}/approve")
@limiter.limit("30/minute")
def approve_schedule_proposal(
    request: Request,
    proposal_id: int, data: ProposalApprovalRequest,
    db: DbSession, current_user: CurrentUser = None,
):
    """Approve or reject a schedule proposal."""
    new_status = "approved" if data.approved else "rejected"
    return {"status": "ok", "new_status": new_status}


@router.post("/auto-planning/purchase-plan", response_model=PurchasePlanResponse)
@limiter.limit("30/minute")
def generate_purchase_plan(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    forecast_days: int = Query(7, ge=1, le=14),
):
    """Auto-generate purchase orders based on demand forecast."""
    global _next_ids
    now = datetime.utcnow()

    plan = PurchasePlanResponse(
        id=_next_ids["purchase"],
        plan_date=str(date.today()),
        status="draft",
        total_cost=0.0,
        purchase_orders=[],
        created_at=now.isoformat(),
    )
    _next_ids["purchase"] += 1
    return plan


@router.get("/auto-planning/purchase-plans", response_model=List[PurchasePlanResponse])
@limiter.limit("60/minute")
def get_purchase_plans(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    status: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Get purchase plan proposals."""
    return []


@router.post("/auto-planning/purchase-plans/{proposal_id}/approve")
@limiter.limit("30/minute")
def approve_purchase_plan(
    request: Request,
    proposal_id: int, data: ProposalApprovalRequest,
    db: DbSession, current_user: CurrentUser = None,
):
    """Approve or reject a purchase plan proposal."""
    new_status = "approved" if data.approved else "rejected"
    return {"status": "ok", "new_status": new_status}
