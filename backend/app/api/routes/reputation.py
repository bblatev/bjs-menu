"""Reputation Management API routes.

Provides endpoints for review aggregation, sentiment analysis, response
management, reputation dashboards, and alerting.
"""

import json
import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from app.core.rbac import CurrentUser, RequireManager
from app.db.session import DbSession
from app.services.reputation_service import (
    ExternalReview,
    ReputationService,
    ReviewSentiment,
    ReviewSource,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

# -- Reviews --

class ReviewCreateRequest(BaseModel):
    """Schema for adding/importing a review."""
    source: str = Field(..., description="Review source: google, yelp, tripadvisor, facebook, internal")
    external_id: Optional[str] = Field(None, description="External platform review ID")
    author_name: Optional[str] = Field(None, max_length=200)
    rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")
    review_text: Optional[str] = Field(None, description="Full review text")
    review_date: Optional[datetime] = Field(None, description="Date the review was posted")
    location_id: int = Field(..., description="Location ID this review belongs to")

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        allowed = {s.value for s in ReviewSource}
        if v not in allowed:
            raise ValueError(f"source must be one of: {', '.join(sorted(allowed))}")
        return v


class ReviewResponse(BaseModel):
    """Schema for a single review in API responses."""
    id: int
    location_id: int
    source: str
    external_id: Optional[str] = None
    author_name: Optional[str] = None
    rating: Optional[float] = None
    review_text: Optional[str] = None
    review_date: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    keywords: Optional[List[str]] = None
    response_text: Optional[str] = None
    response_date: Optional[str] = None
    responded_by: Optional[int] = None
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    created_at: Optional[str] = None


class ReviewListResponse(BaseModel):
    """Paginated list of reviews."""
    items: List[ReviewResponse]
    total: int
    offset: int
    limit: int


class RespondToReviewRequest(BaseModel):
    """Schema for saving a response to a review."""
    response_text: str = Field(..., min_length=1, max_length=5000)


class FlagReviewRequest(BaseModel):
    """Schema for flagging a review."""
    reason: str = Field(..., min_length=1, max_length=200)


class GenerateResponseRequest(BaseModel):
    """Schema for generating a response from a template."""
    template_id: Optional[int] = Field(None, description="Template ID to use; auto-selects if omitted")


# -- Templates --

class TemplateCreateRequest(BaseModel):
    """Schema for creating a response template."""
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., description="positive, negative, or neutral")
    template_text: str = Field(..., min_length=1)
    variables: Optional[List[str]] = Field(None, description="Available template variables")
    is_active: bool = True

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        allowed = {"positive", "negative", "neutral"}
        if v not in allowed:
            raise ValueError(f"category must be one of: {', '.join(sorted(allowed))}")
        return v


class TemplateUpdateRequest(BaseModel):
    """Schema for updating a response template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = None
    template_text: Optional[str] = Field(None, min_length=1)
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"positive", "negative", "neutral"}
            if v not in allowed:
                raise ValueError(f"category must be one of: {', '.join(sorted(allowed))}")
        return v


class TemplateResponse(BaseModel):
    """Schema for a response template."""
    id: int
    name: str
    category: str
    template_text: str
    variables: Optional[List[str]] = None
    is_active: bool
    created_at: Optional[str] = None


# -- Dashboard & Trends --

class SourceRating(BaseModel):
    avg_rating: Optional[float] = None
    count: int = 0


class DashboardResponse(BaseModel):
    location_id: int
    overall_rating: Optional[float] = None
    total_reviews: int = 0
    source_ratings: Dict[str, SourceRating] = {}
    response_rate: float = 0.0
    responded_count: int = 0
    sentiment_breakdown: Dict[str, int] = {}
    recent_reviews: List[ReviewResponse] = []
    unread_alerts: List[Dict[str, Any]] = []
    trends: Dict[str, Any] = {}


class TrendsResponse(BaseModel):
    period_days: int
    data_points: int
    daily: List[Dict[str, Any]]
    rating_delta: Optional[float] = None
    review_count_delta: int = 0


class KeywordTopicItem(BaseModel):
    topic: str
    mention_count: int
    sentiment: Dict[str, int] = {}


class KeywordAnalysisResponse(BaseModel):
    period_days: int
    total_reviews_analyzed: int
    topics: List[KeywordTopicItem]


# -- Alerts --

class AlertResponse(BaseModel):
    id: int
    location_id: int
    review_id: int
    alert_type: str
    severity: str
    message: str
    is_read: bool
    read_by: Optional[int] = None
    created_at: Optional[str] = None


# -- Snapshot --

class SnapshotResponse(BaseModel):
    id: int
    location_id: int
    snapshot_date: str
    overall_rating: Optional[float] = None
    total_reviews: int = 0
    google_rating: Optional[float] = None
    google_count: int = 0
    yelp_rating: Optional[float] = None
    yelp_count: int = 0
    tripadvisor_rating: Optional[float] = None
    tripadvisor_count: int = 0
    facebook_rating: Optional[float] = None
    facebook_count: int = 0
    internal_rating: Optional[float] = None
    internal_count: int = 0
    positive_pct: Optional[float] = None
    negative_pct: Optional[float] = None


# -- Competitor --

class CompetitorComparisonResponse(BaseModel):
    location_id: int
    overall_rating: Optional[float] = None
    source_comparison: Dict[str, Any]
    note: str


# -- Generated Response --

class GeneratedResponseResult(BaseModel):
    review_id: int
    generated_text: str


# ---------------------------------------------------------------------------
# Helper: build ReviewResponse from dict
# ---------------------------------------------------------------------------

def _review_dict_to_schema(d: Dict[str, Any]) -> ReviewResponse:
    """Convert a service-layer review dict to a Pydantic response schema."""
    return ReviewResponse(
        id=d["id"],
        location_id=d["location_id"],
        source=d["source"],
        external_id=d.get("external_id"),
        author_name=d.get("author_name"),
        rating=d.get("rating"),
        review_text=d.get("review_text"),
        review_date=d.get("review_date"),
        sentiment=d.get("sentiment"),
        sentiment_score=d.get("sentiment_score"),
        keywords=d.get("keywords"),
        response_text=d.get("response_text"),
        response_date=d.get("response_date"),
        responded_by=d.get("responded_by"),
        is_flagged=d.get("is_flagged", False),
        flag_reason=d.get("flag_reason"),
        created_at=d.get("created_at"),
    )


def _review_orm_to_schema(review: ExternalReview) -> ReviewResponse:
    """Convert a review ORM object directly to a Pydantic response schema."""
    keywords_list: Optional[List[str]] = None
    if review.keywords:
        try:
            keywords_list = json.loads(review.keywords)
        except (json.JSONDecodeError, TypeError):
            keywords_list = None

    return ReviewResponse(
        id=review.id,
        location_id=review.location_id,
        source=review.source,
        external_id=review.external_id,
        author_name=review.author_name,
        rating=float(review.rating) if review.rating is not None else None,
        review_text=review.review_text,
        review_date=review.review_date.isoformat() if review.review_date else None,
        sentiment=review.sentiment,
        sentiment_score=float(review.sentiment_score) if review.sentiment_score is not None else None,
        keywords=keywords_list,
        response_text=review.response_text,
        response_date=review.response_date.isoformat() if review.response_date else None,
        responded_by=review.responded_by,
        is_flagged=review.is_flagged,
        flag_reason=review.flag_reason,
        created_at=review.created_at.isoformat() if review.created_at else None,
    )


# ---------------------------------------------------------------------------
# Routes: Dashboard
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/{location_id}",
    response_model=DashboardResponse,
    summary="Full reputation dashboard",
)
def get_dashboard(
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> DashboardResponse:
    """Return the full reputation dashboard for a location.

    Includes overall ratings, per-source breakdowns, sentiment distribution,
    recent reviews, unread alerts, and 30-day trends.
    """
    svc = ReputationService(db)
    data = svc.get_dashboard(location_id)

    source_ratings = {}
    for src_name, src_data in data.get("source_ratings", {}).items():
        source_ratings[src_name] = SourceRating(
            avg_rating=src_data.get("avg_rating"),
            count=src_data.get("count", 0),
        )

    recent = [
        _review_dict_to_schema(r) for r in data.get("recent_reviews", [])
    ]

    return DashboardResponse(
        location_id=data["location_id"],
        overall_rating=data.get("overall_rating"),
        total_reviews=data.get("total_reviews", 0),
        source_ratings=source_ratings,
        response_rate=data.get("response_rate", 0.0),
        responded_count=data.get("responded_count", 0),
        sentiment_breakdown=data.get("sentiment_breakdown", {}),
        recent_reviews=recent,
        unread_alerts=data.get("unread_alerts", []),
        trends=data.get("trends", {}),
    )


# ---------------------------------------------------------------------------
# Routes: Reviews
# ---------------------------------------------------------------------------

@router.get(
    "/reviews",
    response_model=ReviewListResponse,
    summary="List reviews with filters",
)
def list_reviews(
    db: DbSession,
    current_user: CurrentUser,
    location_id: int = Query(1, description="Location ID"),
    source: Optional[str] = Query(None, description="Filter by source"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment"),
    min_rating: Optional[float] = Query(None, ge=1.0, le=5.0),
    max_rating: Optional[float] = Query(None, ge=1.0, le=5.0),
    is_flagged: Optional[bool] = Query(None),
    has_response: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None, description="Start date filter"),
    date_to: Optional[date] = Query(None, description="End date filter"),
    search: Optional[str] = Query(None, description="Search in review text / author"),
    sort_by: str = Query("review_date", description="Sort field"),
    sort_order: str = Query("desc", description="asc or desc"),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> ReviewListResponse:
    """Get reviews with filtering, sorting, and pagination."""
    svc = ReputationService(db)
    result = svc.get_reviews(
        location_id=location_id,
        source=source,
        sentiment=sentiment,
        min_rating=min_rating,
        max_rating=max_rating,
        is_flagged=is_flagged,
        has_response=has_response,
        date_from=date_from,
        date_to=date_to,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        offset=offset,
        limit=limit,
    )

    items = [_review_orm_to_schema(r) for r in result["items"]]

    return ReviewListResponse(
        items=items,
        total=result["total"],
        offset=result["offset"],
        limit=result["limit"],
    )


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add/import a review",
)
def create_review(
    body: ReviewCreateRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ReviewResponse:
    """Add or import an external review.

    If ``external_id`` matches an existing review, the record is updated.
    Sentiment analysis and keyword extraction are performed automatically.
    """
    svc = ReputationService(db)
    review_data = body.model_dump()
    location_id = review_data.pop("location_id")

    review = svc.add_review(review_data, location_id)
    db.commit()
    return _review_orm_to_schema(review)


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Single review detail",
)
def get_review(
    review_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> ReviewResponse:
    """Get a single review by ID."""
    svc = ReputationService(db)
    review = svc.get_review_by_id(review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review {review_id} not found",
        )
    return _review_orm_to_schema(review)


@router.post(
    "/reviews/{review_id}/respond",
    response_model=ReviewResponse,
    summary="Save response to review",
)
def respond_to_review(
    review_id: int,
    body: RespondToReviewRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ReviewResponse:
    """Save a response to a review."""
    svc = ReputationService(db)
    try:
        review = svc.save_response(review_id, body.response_text, current_user.user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    db.commit()
    return _review_orm_to_schema(review)


@router.post(
    "/reviews/{review_id}/flag",
    response_model=ReviewResponse,
    summary="Flag review for attention",
)
def flag_review(
    review_id: int,
    body: FlagReviewRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> ReviewResponse:
    """Flag a review for attention with a reason."""
    svc = ReputationService(db)
    try:
        review = svc.flag_review(review_id, body.reason)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    db.commit()
    return _review_orm_to_schema(review)


# ---------------------------------------------------------------------------
# Routes: Trends
# ---------------------------------------------------------------------------

@router.get(
    "/trends/{location_id}",
    response_model=TrendsResponse,
    summary="Rating trends over time",
)
def get_trends(
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
) -> TrendsResponse:
    """Get rating trends over the specified time period."""
    svc = ReputationService(db)
    data = svc.get_trends(location_id, days=days)
    return TrendsResponse(**data)


# ---------------------------------------------------------------------------
# Routes: Keywords
# ---------------------------------------------------------------------------

@router.get(
    "/keywords/{location_id}",
    response_model=KeywordAnalysisResponse,
    summary="Keyword/topic analysis",
)
def get_keyword_analysis(
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
) -> KeywordAnalysisResponse:
    """Get keyword and topic analysis for reviews at a location."""
    svc = ReputationService(db)
    data = svc.get_keyword_analysis(location_id, days=days)
    return KeywordAnalysisResponse(
        period_days=data["period_days"],
        total_reviews_analyzed=data["total_reviews_analyzed"],
        topics=[
            KeywordTopicItem(
                topic=t["topic"],
                mention_count=t["mention_count"],
                sentiment=t.get("sentiment", {}),
            )
            for t in data["topics"]
        ],
    )


# ---------------------------------------------------------------------------
# Routes: Alerts
# ---------------------------------------------------------------------------

@router.get(
    "/alerts/{location_id}",
    response_model=List[AlertResponse],
    summary="Active alerts for location",
)
def get_alerts(
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
    unread_only: bool = Query(True, description="Only return unread alerts"),
) -> List[AlertResponse]:
    """Get reputation alerts for a location."""
    svc = ReputationService(db)

    # Also trigger alert generation to catch new issues
    svc.check_alerts(location_id)
    db.commit()

    alerts = svc.get_alerts(location_id, unread_only=unread_only)
    return [
        AlertResponse(
            id=a.id,
            location_id=a.location_id,
            review_id=a.review_id,
            alert_type=a.alert_type,
            severity=a.severity,
            message=a.message,
            is_read=a.is_read,
            read_by=a.read_by,
            created_at=a.created_at.isoformat() if a.created_at else None,
        )
        for a in alerts
    ]


@router.post(
    "/alerts/{alert_id}/read",
    response_model=AlertResponse,
    summary="Mark alert as read",
)
def mark_alert_read(
    alert_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> AlertResponse:
    """Mark a reputation alert as read."""
    svc = ReputationService(db)
    try:
        alert = svc.mark_alert_read(alert_id, current_user.user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    db.commit()
    return AlertResponse(
        id=alert.id,
        location_id=alert.location_id,
        review_id=alert.review_id,
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        is_read=alert.is_read,
        read_by=alert.read_by,
        created_at=alert.created_at.isoformat() if alert.created_at else None,
    )


# ---------------------------------------------------------------------------
# Routes: Snapshot
# ---------------------------------------------------------------------------

@router.post(
    "/snapshot/{location_id}",
    response_model=SnapshotResponse,
    summary="Trigger reputation snapshot",
)
def take_snapshot(
    location_id: int,
    db: DbSession,
    current_user: RequireManager,
) -> SnapshotResponse:
    """Trigger a reputation snapshot for the given location.

    Requires manager role or higher.  Creates or updates today's snapshot
    with aggregated ratings from all sources.
    """
    svc = ReputationService(db)
    snap = svc.take_snapshot(location_id)
    db.commit()
    return SnapshotResponse(
        id=snap.id,
        location_id=snap.location_id,
        snapshot_date=snap.snapshot_date.isoformat(),
        overall_rating=float(snap.overall_rating) if snap.overall_rating else None,
        total_reviews=snap.total_reviews,
        google_rating=float(snap.google_rating) if snap.google_rating else None,
        google_count=snap.google_count,
        yelp_rating=float(snap.yelp_rating) if snap.yelp_rating else None,
        yelp_count=snap.yelp_count,
        tripadvisor_rating=float(snap.tripadvisor_rating) if snap.tripadvisor_rating else None,
        tripadvisor_count=snap.tripadvisor_count,
        facebook_rating=float(snap.facebook_rating) if snap.facebook_rating else None,
        facebook_count=snap.facebook_count,
        internal_rating=float(snap.internal_rating) if snap.internal_rating else None,
        internal_count=snap.internal_count,
        positive_pct=float(snap.positive_pct) if snap.positive_pct else None,
        negative_pct=float(snap.negative_pct) if snap.negative_pct else None,
    )


# ---------------------------------------------------------------------------
# Routes: Templates
# ---------------------------------------------------------------------------

@router.get(
    "/templates",
    response_model=List[TemplateResponse],
    summary="List response templates",
)
def list_templates(
    db: DbSession,
    current_user: CurrentUser,
    active_only: bool = Query(True, description="Only return active templates"),
) -> List[TemplateResponse]:
    """List all response templates."""
    svc = ReputationService(db)
    templates = svc.get_templates(active_only=active_only)
    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            category=t.category,
            template_text=t.template_text,
            variables=json.loads(t.variables) if t.variables else None,
            is_active=t.is_active,
            created_at=t.created_at.isoformat() if t.created_at else None,
        )
        for t in templates
    ]


@router.post(
    "/templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create response template",
)
def create_template(
    body: TemplateCreateRequest,
    db: DbSession,
    current_user: RequireManager,
) -> TemplateResponse:
    """Create a new response template.  Requires manager role or higher."""
    svc = ReputationService(db)
    template = svc.create_template(body.model_dump())
    db.commit()
    return TemplateResponse(
        id=template.id,
        name=template.name,
        category=template.category,
        template_text=template.template_text,
        variables=json.loads(template.variables) if template.variables else None,
        is_active=template.is_active,
        created_at=template.created_at.isoformat() if template.created_at else None,
    )


@router.put(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="Update response template",
)
def update_template(
    template_id: int,
    body: TemplateUpdateRequest,
    db: DbSession,
    current_user: RequireManager,
) -> TemplateResponse:
    """Update an existing response template.  Requires manager role or higher."""
    svc = ReputationService(db)
    update_data = body.model_dump(exclude_unset=True)
    try:
        template = svc.update_template(template_id, update_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    db.commit()
    return TemplateResponse(
        id=template.id,
        name=template.name,
        category=template.category,
        template_text=template.template_text,
        variables=json.loads(template.variables) if template.variables else None,
        is_active=template.is_active,
        created_at=template.created_at.isoformat() if template.created_at else None,
    )


# ---------------------------------------------------------------------------
# Routes: Generate Response
# ---------------------------------------------------------------------------

@router.post(
    "/generate-response/{review_id}",
    response_model=GeneratedResponseResult,
    summary="Generate response from template",
)
def generate_response(
    review_id: int,
    body: GenerateResponseRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> GeneratedResponseResult:
    """Generate a response for a review using a template.

    If ``template_id`` is not provided, an appropriate template is selected
    based on the review's sentiment.  The generated text is returned but
    NOT automatically saved -- call the respond endpoint to persist it.
    """
    svc = ReputationService(db)
    try:
        text = svc.generate_response(review_id, template_id=body.template_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    return GeneratedResponseResult(review_id=review_id, generated_text=text)


# ---------------------------------------------------------------------------
# Routes: Competitor Comparison
# ---------------------------------------------------------------------------

@router.get(
    "/competitor-comparison/{location_id}",
    response_model=CompetitorComparisonResponse,
    summary="Competitor rating comparison",
)
def get_competitor_comparison(
    location_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> CompetitorComparisonResponse:
    """Get competitor rating comparison for a location.

    Currently returns industry benchmark comparisons.  Connect third-party
    APIs for live competitor data.
    """
    svc = ReputationService(db)
    data = svc.get_competitor_comparison(location_id)
    return CompetitorComparisonResponse(**data)
