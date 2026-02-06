"""Feedback and reviews API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

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


@router.get("/")
async def get_feedback_overview():
    """Get feedback overview."""
    return {
        "average_rating": 4.5,
        "total_reviews": 234,
        "recent_reviews": [],
        "rating_distribution": {"5": 120, "4": 65, "3": 30, "2": 12, "1": 7},
        "response_rate": 85.0,
        "sources": [
            {"name": "Google", "count": 120, "avg_rating": 4.6},
            {"name": "Internal", "count": 80, "avg_rating": 4.4},
            {"name": "TripAdvisor", "count": 34, "avg_rating": 4.3},
        ],
    }


@router.get("/reviews")
async def get_reviews(
    source: str = Query(None),
    rating: int = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None)
):
    """Get customer reviews."""
    return [
        Review(id="1", customer_name="John D.", rating=5, comment="Excellent food and service!", source="google", created_at="2026-02-01T18:00:00Z"),
        Review(id="2", customer_name="Sarah M.", rating=4, comment="Good food, a bit slow service", source="tripadvisor", response="Thank you for your feedback! We're working on improving our service times.", responded_at="2026-01-31T10:00:00Z", created_at="2026-01-30T20:00:00Z"),
        Review(id="3", customer_name="Mike R.", rating=5, comment="Best cocktails in town!", source="facebook", created_at="2026-01-29T22:00:00Z"),
        Review(id="4", customer_name="Anna K.", rating=3, comment="Food was okay, nothing special", source="google", created_at="2026-01-28T19:00:00Z"),
        Review(id="5", customer_name="Guest", rating=5, source="internal", order_id="ORD-1234", created_at="2026-01-27T21:00:00Z"),
    ]


@router.get("/reviews/{review_id}")
async def get_review(review_id: str):
    """Get a specific review."""
    return Review(id=review_id, customer_name="John D.", rating=5, comment="Excellent!", source="google", created_at="2026-02-01T18:00:00Z")


@router.post("/reviews/{review_id}/respond")
async def respond_to_review(review_id: str, response: str):
    """Respond to a review."""
    return {"success": True}


@router.get("/stats")
async def get_feedback_stats(period: str = Query("month")):
    """Get feedback statistics."""
    return FeedbackStats(
        average_rating=4.3,
        total_reviews=156,
        five_star=78,
        four_star=45,
        three_star=20,
        two_star=8,
        one_star=5,
        response_rate=82.5,
        avg_response_time_hours=4.2
    )
