"""Feedback and reviews API routes."""

from datetime import datetime, date, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, field_validator

from app.core.sanitize import sanitize_text
from sqlalchemy import func

from app.db.session import DbSession
from app.models.operations import FeedbackReview

router = APIRouter()


class Review(BaseModel):
    id: str
    customer_name: str
    rating: int  # 1-5
    comment: Optional[str] = None
    source: str  # google, facebook, tripadvisor, internal
    response: Optional[str] = None
    responded_at: Optional[str] = None
    order_id: Optional[str] = None
    created_at: str


class FeedbackStats(BaseModel):
    average_rating: float
    total_reviews: int
    five_star: int
    four_star: int
    three_star: int
    two_star: int
    one_star: int
    response_rate: float
    avg_response_time_hours: float


class RespondRequest(BaseModel):
    response: str

    @field_validator("response", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return sanitize_text(v)


def _review_to_schema(r: FeedbackReview) -> Review:
    """Convert a FeedbackReview model instance to a Review schema."""
    return Review(
        id=str(r.id),
        customer_name=r.customer_name or "Guest",
        rating=r.rating or 0,
        comment=r.text,
        source=r.source or "internal",
        response=r.response,
        responded_at=r.responded_at.isoformat() if r.responded_at else None,
        order_id=None,
        created_at=r.created_at.isoformat() if r.created_at else "",
    )


@router.get("/")
async def get_feedback_overview(db: DbSession):
    """Get feedback overview."""
    total_reviews = db.query(func.count(FeedbackReview.id)).scalar() or 0

    avg_rating_val = db.query(func.avg(FeedbackReview.rating)).filter(
        FeedbackReview.rating.isnot(None)
    ).scalar()
    average_rating = round(float(avg_rating_val), 2) if avg_rating_val else 0.0

    # Rating distribution
    rating_dist = {}
    for star in range(1, 6):
        count = db.query(func.count(FeedbackReview.id)).filter(
            FeedbackReview.rating == star
        ).scalar() or 0
        rating_dist[str(star)] = count

    # Response rate
    responded_count = db.query(func.count(FeedbackReview.id)).filter(
        FeedbackReview.status == "responded"
    ).scalar() or 0
    response_rate = round((responded_count / total_reviews * 100), 1) if total_reviews > 0 else 0.0

    # Source breakdown
    source_rows = db.query(
        FeedbackReview.source,
        func.count(FeedbackReview.id).label("cnt"),
        func.avg(FeedbackReview.rating).label("avg_r"),
    ).group_by(FeedbackReview.source).all()

    sources = [
        {
            "name": row.source or "internal",
            "count": row.cnt,
            "avg_rating": round(float(row.avg_r), 1) if row.avg_r else 0.0,
        }
        for row in source_rows
    ]

    # Recent reviews
    recent = db.query(FeedbackReview).order_by(
        FeedbackReview.created_at.desc()
    ).limit(10).all()
    recent_reviews = [_review_to_schema(r).model_dump() for r in recent]

    return {
        "average_rating": average_rating,
        "total_reviews": total_reviews,
        "recent_reviews": recent_reviews,
        "rating_distribution": rating_dist,
        "response_rate": response_rate,
        "sources": sources,
    }


@router.post("/reviews")
async def create_review(data: dict, db: DbSession):
    """Create a customer review."""
    review = FeedbackReview(
        customer_name=data.get("customer_name", "Guest"),
        rating=data.get("rating", 5),
        text=data.get("comment", data.get("text", "")),
        source=data.get("source", "internal"),
        status="new",
        created_at=datetime.now(timezone.utc),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return {"id": review.id, "customer_name": review.customer_name, "rating": review.rating}


@router.get("/reviews")
async def get_reviews(
    db: DbSession,
    source: str = Query(None),
    rating: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
):
    """Get customer reviews."""
    query = db.query(FeedbackReview)

    if source:
        query = query.filter(FeedbackReview.source == source)
    if rating is not None:
        query = query.filter(FeedbackReview.rating == rating)
    if start_date:
        try:
            sd = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            query = query.filter(FeedbackReview.created_at >= sd)
        except (ValueError, TypeError):
            pass
    if end_date:
        try:
            ed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            query = query.filter(FeedbackReview.created_at <= ed)
        except (ValueError, TypeError):
            pass

    reviews = query.order_by(FeedbackReview.created_at.desc()).all()
    return [_review_to_schema(r) for r in reviews]


@router.get("/reviews/{review_id}")
async def get_review(review_id: str, db: DbSession):
    """Get a specific review."""
    review = db.query(FeedbackReview).filter(
        FeedbackReview.id == int(review_id)
    ).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    return _review_to_schema(review)


@router.patch("/reviews/{review_id}/status")
async def update_review_status(review_id: str, data: dict, db: DbSession):
    """Update a review's status."""
    review = db.query(FeedbackReview).filter(
        FeedbackReview.id == int(review_id)
    ).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    new_status = data.get("status")
    if new_status not in ("new", "responded", "flagged"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be one of: new, responded, flagged",
        )

    review.status = new_status
    db.commit()
    return {"success": True, "id": str(review.id), "status": review.status}


@router.post("/reviews/{review_id}/respond")
async def respond_to_review(review_id: str, body: RespondRequest, db: DbSession):
    """Respond to a review."""
    review = db.query(FeedbackReview).filter(
        FeedbackReview.id == int(review_id)
    ).first()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    review.response = body.response
    review.responded_at = datetime.now(timezone.utc)
    review.status = "responded"
    db.commit()

    return {"success": True}


@router.get("/stats")
async def get_feedback_stats(db: DbSession, period: str = Query("month")):
    """Get feedback statistics."""
    query = db.query(FeedbackReview)

    # Apply period filter
    now = datetime.now(timezone.utc)
    if period == "week":
        from datetime import timedelta
        cutoff = now - timedelta(weeks=1)
        query = query.filter(FeedbackReview.created_at >= cutoff)
    elif period == "month":
        from datetime import timedelta
        cutoff = now - timedelta(days=30)
        query = query.filter(FeedbackReview.created_at >= cutoff)
    elif period == "year":
        from datetime import timedelta
        cutoff = now - timedelta(days=365)
        query = query.filter(FeedbackReview.created_at >= cutoff)

    all_reviews = query.all()
    total = len(all_reviews)

    if total == 0:
        return FeedbackStats(
            average_rating=0.0,
            total_reviews=0,
            five_star=0,
            four_star=0,
            three_star=0,
            two_star=0,
            one_star=0,
            response_rate=0.0,
            avg_response_time_hours=0.0,
        )

    avg_rating = sum(r.rating for r in all_reviews if r.rating) / max(
        sum(1 for r in all_reviews if r.rating), 1
    )

    star_counts = {s: 0 for s in range(1, 6)}
    for r in all_reviews:
        if r.rating and 1 <= r.rating <= 5:
            star_counts[r.rating] += 1

    responded = [r for r in all_reviews if r.status == "responded"]
    response_rate = round(len(responded) / total * 100, 1) if total > 0 else 0.0

    # Average response time for reviews that have been responded to
    response_times = []
    for r in responded:
        if r.responded_at and r.created_at:
            responded_at = r.responded_at.replace(tzinfo=timezone.utc) if r.responded_at.tzinfo is None else r.responded_at
            created_at = r.created_at.replace(tzinfo=timezone.utc) if r.created_at.tzinfo is None else r.created_at
            delta = (responded_at - created_at).total_seconds() / 3600.0
            response_times.append(delta)
    avg_response_time = round(sum(response_times) / len(response_times), 1) if response_times else 0.0

    return FeedbackStats(
        average_rating=round(avg_rating, 1),
        total_reviews=total,
        five_star=star_counts[5],
        four_star=star_counts[4],
        three_star=star_counts[3],
        two_star=star_counts[2],
        one_star=star_counts[1],
        response_rate=response_rate,
        avg_response_time_hours=avg_response_time,
    )
