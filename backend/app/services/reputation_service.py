"""Reputation Management Service.

Aggregates reviews from multiple platforms (Google, Yelp, TripAdvisor, Facebook),
performs sentiment analysis, generates auto-response templates, and provides
reputation dashboard with trends.

Industry standard: Toast Reputation, Yelp for Business, Sprout Social.
"""

import json
import logging
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    and_,
    desc,
    func,
    or_,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db.base import Base, TimestampMixin

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ReviewSource(str, Enum):
    GOOGLE = "google"
    YELP = "yelp"
    TRIPADVISOR = "tripadvisor"
    FACEBOOK = "facebook"
    INTERNAL = "internal"  # From in-app feedback


class ReviewSentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


# ---------------------------------------------------------------------------
# SQLAlchemy Models
# ---------------------------------------------------------------------------

class ExternalReview(Base, TimestampMixin):
    __tablename__ = "external_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), index=True)
    source: Mapped[str] = mapped_column(String(30), index=True)  # ReviewSource
    external_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, unique=True
    )
    author_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 1), nullable=True
    )  # 1.0-5.0
    review_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4), nullable=True
    )  # -1.0 to 1.0
    keywords: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    responded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    is_flagged: Mapped[bool] = mapped_column(default=False)
    flag_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)


class ReputationSnapshot(Base, TimestampMixin):
    __tablename__ = "reputation_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    google_rating: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    google_count: Mapped[int] = mapped_column(default=0)
    yelp_rating: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    yelp_count: Mapped[int] = mapped_column(default=0)
    tripadvisor_rating: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    tripadvisor_count: Mapped[int] = mapped_column(default=0)
    facebook_rating: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    facebook_count: Mapped[int] = mapped_column(default=0)
    internal_rating: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    internal_count: Mapped[int] = mapped_column(default=0)
    overall_rating: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    total_reviews: Mapped[int] = mapped_column(default=0)
    positive_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    negative_pct: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )


class ResponseTemplate(Base, TimestampMixin):
    __tablename__ = "review_response_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(30))  # positive, negative, neutral
    template_text: Mapped[str] = mapped_column(Text)
    variables: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON: available template variables
    is_active: Mapped[bool] = mapped_column(default=True)


class ReviewAlert(Base, TimestampMixin):
    __tablename__ = "review_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), index=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("external_reviews.id"), index=True
    )
    alert_type: Mapped[str] = mapped_column(
        String(30)
    )  # negative_review, rating_drop, trending_complaint
    severity: Mapped[str] = mapped_column(
        String(10)
    )  # low, medium, high, critical
    message: Mapped[str] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(default=False)
    read_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )


# ---------------------------------------------------------------------------
# Sentiment Analysis Word Lists
# ---------------------------------------------------------------------------

POSITIVE_WORDS = {
    "great",
    "excellent",
    "amazing",
    "delicious",
    "wonderful",
    "fantastic",
    "perfect",
    "love",
    "best",
    "outstanding",
    "friendly",
    "fresh",
    "quick",
    "clean",
    "cozy",
    "recommend",
    "superb",
    "impressed",
    "enjoyed",
    "tasty",
    "attentive",
    "pleasant",
    "welcoming",
    "beautiful",
    "incredible",
    "lovely",
    "happy",
    "satisfied",
    "generous",
    "warm",
}

NEGATIVE_WORDS = {
    "terrible",
    "horrible",
    "awful",
    "disgusting",
    "worst",
    "rude",
    "slow",
    "dirty",
    "cold",
    "stale",
    "overpriced",
    "wait",
    "bad",
    "poor",
    "disappointing",
    "never",
    "bland",
    "undercooked",
    "raw",
    "burnt",
    "greasy",
    "unfriendly",
    "inattentive",
    "noisy",
    "uncomfortable",
    "mediocre",
    "tasteless",
    "soggy",
    "forgot",
    "wrong",
}

# Topics for keyword extraction
TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "food_quality": [
        "food",
        "taste",
        "flavor",
        "fresh",
        "stale",
        "delicious",
        "bland",
        "undercooked",
        "overcooked",
        "raw",
        "burnt",
        "seasoning",
        "portion",
        "dish",
        "meal",
        "menu",
    ],
    "service": [
        "service",
        "waiter",
        "waitress",
        "staff",
        "server",
        "friendly",
        "rude",
        "attentive",
        "slow",
        "quick",
        "helpful",
        "polite",
        "ignored",
    ],
    "ambiance": [
        "ambiance",
        "atmosphere",
        "decor",
        "music",
        "noise",
        "clean",
        "dirty",
        "cozy",
        "comfortable",
        "crowded",
        "quiet",
        "lighting",
        "view",
    ],
    "value": [
        "price",
        "value",
        "expensive",
        "cheap",
        "overpriced",
        "worth",
        "affordable",
        "cost",
        "bill",
        "tip",
        "deal",
    ],
    "wait_time": [
        "wait",
        "waiting",
        "slow",
        "fast",
        "quick",
        "long",
        "reservation",
        "seated",
        "table",
        "line",
        "queue",
        "hour",
        "minutes",
    ],
    "cleanliness": [
        "clean",
        "dirty",
        "hygiene",
        "restroom",
        "bathroom",
        "sanitary",
        "spotless",
        "messy",
        "tidy",
    ],
}


# ---------------------------------------------------------------------------
# Service Class
# ---------------------------------------------------------------------------

class ReputationService:
    """Manages reputation monitoring, sentiment analysis, and review responses."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Review Management
    # ------------------------------------------------------------------

    def add_review(
        self,
        review_data: Dict[str, Any],
        location_id: int,
    ) -> ExternalReview:
        """Add or update an external review.

        If an ``external_id`` is provided and a review with that ID already
        exists, the existing record is updated.  Otherwise a new review is
        created.  Sentiment analysis and keyword extraction are performed
        automatically on the review text.
        """
        external_id = review_data.get("external_id")
        existing: Optional[ExternalReview] = None

        if external_id:
            existing = (
                self.db.query(ExternalReview)
                .filter(ExternalReview.external_id == external_id)
                .first()
            )

        # Run NLP-lite analysis if text is present
        review_text = review_data.get("review_text") or ""
        sentiment_label: Optional[str] = None
        sentiment_score: Optional[float] = None
        keywords_json: Optional[str] = None

        if review_text:
            sentiment_label, sentiment_score = self.analyze_sentiment(review_text)
            keywords_list = self.extract_keywords(review_text)
            keywords_json = json.dumps(keywords_list) if keywords_list else None

        if existing:
            existing.author_name = review_data.get("author_name", existing.author_name)
            existing.rating = review_data.get("rating", existing.rating)
            existing.review_text = review_text or existing.review_text
            existing.review_date = review_data.get("review_date", existing.review_date)
            existing.source = review_data.get("source", existing.source)
            if review_text:
                existing.sentiment = sentiment_label
                existing.sentiment_score = sentiment_score
                existing.keywords = keywords_json
            self.db.flush()
            logger.info(
                "Updated existing review id=%s external_id=%s",
                existing.id,
                external_id,
            )
            return existing

        review = ExternalReview(
            location_id=location_id,
            source=review_data.get("source", ReviewSource.INTERNAL.value),
            external_id=external_id,
            author_name=review_data.get("author_name"),
            rating=review_data.get("rating"),
            review_text=review_text or None,
            review_date=review_data.get("review_date"),
            sentiment=sentiment_label,
            sentiment_score=sentiment_score,
            keywords=keywords_json,
        )
        self.db.add(review)
        self.db.flush()
        logger.info(
            "Created new review id=%s source=%s location=%s",
            review.id,
            review.source,
            location_id,
        )
        return review

    # ------------------------------------------------------------------
    # Sentiment Analysis
    # ------------------------------------------------------------------

    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """Perform keyword-based sentiment analysis on review text.

        Returns a tuple of ``(sentiment_label, sentiment_score)`` where
        *sentiment_label* is one of ``positive``, ``negative``, or
        ``neutral`` and *sentiment_score* is a float in the range
        ``[-1.0, 1.0]``.
        """
        if not text:
            return ReviewSentiment.NEUTRAL.value, 0.0

        words = re.findall(r"[a-z]+", text.lower())
        if not words:
            return ReviewSentiment.NEUTRAL.value, 0.0

        positive_count = sum(1 for w in words if w in POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in NEGATIVE_WORDS)
        total_sentiment_words = positive_count + negative_count

        if total_sentiment_words == 0:
            return ReviewSentiment.NEUTRAL.value, 0.0

        # Score from -1.0 (all negative) to +1.0 (all positive)
        raw_score = (positive_count - negative_count) / total_sentiment_words

        # Weight by density of sentiment words in the review
        density = min(total_sentiment_words / len(words), 1.0)
        weighted_score = round(raw_score * (0.5 + 0.5 * density), 4)

        if weighted_score > 0.1:
            label = ReviewSentiment.POSITIVE.value
        elif weighted_score < -0.1:
            label = ReviewSentiment.NEGATIVE.value
        else:
            label = ReviewSentiment.NEUTRAL.value

        return label, weighted_score

    # ------------------------------------------------------------------
    # Keyword Extraction
    # ------------------------------------------------------------------

    def extract_keywords(self, text: str) -> List[str]:
        """Extract key topics from review text.

        Returns a list of topic labels (e.g. ``food_quality``, ``service``)
        that are mentioned in the review, based on keyword matching against
        predefined topic dictionaries.
        """
        if not text:
            return []

        words = set(re.findall(r"[a-z]+", text.lower()))
        matched_topics: List[str] = []

        for topic, topic_words in TOPIC_KEYWORDS.items():
            overlap = words.intersection(topic_words)
            if len(overlap) >= 1:
                matched_topics.append(topic)

        return matched_topics

    # ------------------------------------------------------------------
    # Review Queries
    # ------------------------------------------------------------------

    def get_reviews(
        self,
        location_id: int,
        source: Optional[str] = None,
        sentiment: Optional[str] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        is_flagged: Optional[bool] = None,
        has_response: Optional[bool] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None,
        sort_by: str = "review_date",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Get reviews with filtering, sorting, and pagination.

        Returns a dict with ``items``, ``total``, ``offset``, and ``limit``.
        """
        query = self.db.query(ExternalReview).filter(
            ExternalReview.location_id == location_id
        )

        if source:
            query = query.filter(ExternalReview.source == source)
        if sentiment:
            query = query.filter(ExternalReview.sentiment == sentiment)
        if min_rating is not None:
            query = query.filter(ExternalReview.rating >= min_rating)
        if max_rating is not None:
            query = query.filter(ExternalReview.rating <= max_rating)
        if is_flagged is not None:
            query = query.filter(ExternalReview.is_flagged == is_flagged)
        if has_response is True:
            query = query.filter(ExternalReview.response_text.isnot(None))
        elif has_response is False:
            query = query.filter(ExternalReview.response_text.is_(None))
        if date_from:
            query = query.filter(
                func.date(ExternalReview.review_date) >= date_from
            )
        if date_to:
            query = query.filter(
                func.date(ExternalReview.review_date) <= date_to
            )
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    ExternalReview.review_text.ilike(pattern),
                    ExternalReview.author_name.ilike(pattern),
                )
            )

        total = query.count()

        # Sorting
        sort_column_map = {
            "review_date": ExternalReview.review_date,
            "rating": ExternalReview.rating,
            "created_at": ExternalReview.created_at,
            "sentiment_score": ExternalReview.sentiment_score,
        }
        sort_col = sort_column_map.get(sort_by, ExternalReview.review_date)
        if sort_order == "asc":
            query = query.order_by(sort_col.asc().nullslast())
        else:
            query = query.order_by(sort_col.desc().nullslast())

        items = query.offset(offset).limit(limit).all()
        return {
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    def get_review_by_id(self, review_id: int) -> Optional[ExternalReview]:
        """Return a single review by primary key."""
        return (
            self.db.query(ExternalReview)
            .filter(ExternalReview.id == review_id)
            .first()
        )

    # ------------------------------------------------------------------
    # Response Generation
    # ------------------------------------------------------------------

    def generate_response(
        self,
        review_id: int,
        template_id: Optional[int] = None,
    ) -> str:
        """Generate a response for a review using a template.

        If *template_id* is not provided, an appropriate template is
        selected based on the review's sentiment.  Template variables
        (``{author_name}``, ``{rating}``, ``{location}``) are substituted
        automatically.
        """
        review = self.get_review_by_id(review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")

        template: Optional[ResponseTemplate] = None

        if template_id:
            template = (
                self.db.query(ResponseTemplate)
                .filter(
                    ResponseTemplate.id == template_id,
                    ResponseTemplate.is_active == True,  # noqa: E712
                )
                .first()
            )
        else:
            # Auto-select based on sentiment
            category = review.sentiment or ReviewSentiment.NEUTRAL.value
            template = (
                self.db.query(ResponseTemplate)
                .filter(
                    ResponseTemplate.category == category,
                    ResponseTemplate.is_active == True,  # noqa: E712
                )
                .first()
            )

        if not template:
            # Fallback generic responses
            return self._fallback_response(review)

        # Substitute variables
        response = template.template_text
        response = response.replace("{author_name}", review.author_name or "Valued Guest")
        response = response.replace("{rating}", str(review.rating or ""))
        response = response.replace("{source}", review.source or "")
        response = response.replace("{review_date}", str(review.review_date or ""))

        return response

    def _fallback_response(self, review: ExternalReview) -> str:
        """Generate a generic fallback response when no template is available."""
        author = review.author_name or "Valued Guest"
        sentiment = review.sentiment or ReviewSentiment.NEUTRAL.value

        if sentiment == ReviewSentiment.POSITIVE.value:
            return (
                f"Thank you so much for your wonderful review, {author}! "
                f"We're thrilled to hear you had a great experience. "
                f"We look forward to welcoming you back soon!"
            )
        elif sentiment == ReviewSentiment.NEGATIVE.value:
            return (
                f"Thank you for your feedback, {author}. We sincerely apologize "
                f"that your experience did not meet expectations. Your concerns are "
                f"important to us and we would love the opportunity to make things right. "
                f"Please reach out to us directly so we can address this personally."
            )
        else:
            return (
                f"Thank you for taking the time to share your experience, {author}. "
                f"We appreciate your feedback and will use it to continue improving. "
                f"We hope to see you again soon!"
            )

    def save_response(
        self,
        review_id: int,
        response_text: str,
        user_id: int,
    ) -> ExternalReview:
        """Save a response to a review."""
        review = self.get_review_by_id(review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")

        review.response_text = response_text
        review.response_date = datetime.now(timezone.utc)
        review.responded_by = user_id
        self.db.flush()
        logger.info(
            "Response saved for review id=%s by user=%s", review_id, user_id
        )
        return review

    # ------------------------------------------------------------------
    # Reputation Snapshots
    # ------------------------------------------------------------------

    def take_snapshot(self, location_id: int) -> ReputationSnapshot:
        """Create a daily reputation snapshot for a location.

        Aggregates current ratings and review counts from all sources, as well
        as sentiment distribution percentages.  If a snapshot already exists
        for today it is updated in place.
        """
        today = date.today()

        existing = (
            self.db.query(ReputationSnapshot)
            .filter(
                ReputationSnapshot.location_id == location_id,
                ReputationSnapshot.snapshot_date == today,
            )
            .first()
        )

        snapshot = existing or ReputationSnapshot(
            location_id=location_id,
            snapshot_date=today,
        )

        # Gather per-source stats
        source_stats = self._get_source_stats(location_id)

        snapshot.google_rating = source_stats.get("google", {}).get("avg_rating")
        snapshot.google_count = source_stats.get("google", {}).get("count", 0)
        snapshot.yelp_rating = source_stats.get("yelp", {}).get("avg_rating")
        snapshot.yelp_count = source_stats.get("yelp", {}).get("count", 0)
        snapshot.tripadvisor_rating = source_stats.get("tripadvisor", {}).get("avg_rating")
        snapshot.tripadvisor_count = source_stats.get("tripadvisor", {}).get("count", 0)
        snapshot.facebook_rating = source_stats.get("facebook", {}).get("avg_rating")
        snapshot.facebook_count = source_stats.get("facebook", {}).get("count", 0)
        snapshot.internal_rating = source_stats.get("internal", {}).get("avg_rating")
        snapshot.internal_count = source_stats.get("internal", {}).get("count", 0)

        # Overall
        overall = (
            self.db.query(
                func.avg(ExternalReview.rating),
                func.count(ExternalReview.id),
            )
            .filter(
                ExternalReview.location_id == location_id,
                ExternalReview.rating.isnot(None),
            )
            .first()
        )
        avg_all, total_count = overall or (None, 0)
        snapshot.overall_rating = round(float(avg_all), 2) if avg_all else None
        snapshot.total_reviews = total_count

        # Sentiment distribution
        total_with_sentiment = (
            self.db.query(func.count(ExternalReview.id))
            .filter(
                ExternalReview.location_id == location_id,
                ExternalReview.sentiment.isnot(None),
            )
            .scalar()
        ) or 0

        if total_with_sentiment > 0:
            positive_count = (
                self.db.query(func.count(ExternalReview.id))
                .filter(
                    ExternalReview.location_id == location_id,
                    ExternalReview.sentiment == ReviewSentiment.POSITIVE.value,
                )
                .scalar()
            ) or 0
            negative_count = (
                self.db.query(func.count(ExternalReview.id))
                .filter(
                    ExternalReview.location_id == location_id,
                    ExternalReview.sentiment == ReviewSentiment.NEGATIVE.value,
                )
                .scalar()
            ) or 0
            snapshot.positive_pct = round(
                (positive_count / total_with_sentiment) * 100, 2
            )
            snapshot.negative_pct = round(
                (negative_count / total_with_sentiment) * 100, 2
            )
        else:
            snapshot.positive_pct = None
            snapshot.negative_pct = None

        if not existing:
            self.db.add(snapshot)
        self.db.flush()
        logger.info(
            "Reputation snapshot taken for location=%s date=%s overall=%.2f total=%d",
            location_id,
            today,
            float(snapshot.overall_rating or 0),
            snapshot.total_reviews,
        )
        return snapshot

    def _get_source_stats(self, location_id: int) -> Dict[str, Dict[str, Any]]:
        """Aggregate rating stats grouped by source for a location."""
        rows = (
            self.db.query(
                ExternalReview.source,
                func.avg(ExternalReview.rating),
                func.count(ExternalReview.id),
            )
            .filter(
                ExternalReview.location_id == location_id,
                ExternalReview.rating.isnot(None),
            )
            .group_by(ExternalReview.source)
            .all()
        )
        stats: Dict[str, Dict[str, Any]] = {}
        for source_name, avg_rating, count in rows:
            stats[source_name] = {
                "avg_rating": round(float(avg_rating), 2) if avg_rating else None,
                "count": count,
            }
        return stats

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def get_dashboard(self, location_id: int) -> Dict[str, Any]:
        """Full dashboard data: ratings, trends, alerts, recent reviews.

        Returns a dictionary containing current ratings per source, overall
        rating, recent reviews, unread alerts, 30-day trend summary, and
        response rate metrics.
        """
        source_stats = self._get_source_stats(location_id)

        # Overall rating
        overall = (
            self.db.query(
                func.avg(ExternalReview.rating),
                func.count(ExternalReview.id),
            )
            .filter(
                ExternalReview.location_id == location_id,
                ExternalReview.rating.isnot(None),
            )
            .first()
        )
        avg_all, total_count = overall or (None, 0)

        # Recent reviews (last 10)
        recent_reviews = (
            self.db.query(ExternalReview)
            .filter(ExternalReview.location_id == location_id)
            .order_by(desc(ExternalReview.review_date))
            .limit(10)
            .all()
        )

        # Unread alerts
        unread_alerts = (
            self.db.query(ReviewAlert)
            .filter(
                ReviewAlert.location_id == location_id,
                ReviewAlert.is_read == False,  # noqa: E712
            )
            .order_by(desc(ReviewAlert.created_at))
            .limit(20)
            .all()
        )

        # Response rate
        total_reviews_count = (
            self.db.query(func.count(ExternalReview.id))
            .filter(ExternalReview.location_id == location_id)
            .scalar()
        ) or 0
        responded_count = (
            self.db.query(func.count(ExternalReview.id))
            .filter(
                ExternalReview.location_id == location_id,
                ExternalReview.response_text.isnot(None),
            )
            .scalar()
        ) or 0
        response_rate = (
            round((responded_count / total_reviews_count) * 100, 1)
            if total_reviews_count > 0
            else 0.0
        )

        # Sentiment breakdown
        sentiment_rows = (
            self.db.query(
                ExternalReview.sentiment,
                func.count(ExternalReview.id),
            )
            .filter(
                ExternalReview.location_id == location_id,
                ExternalReview.sentiment.isnot(None),
            )
            .group_by(ExternalReview.sentiment)
            .all()
        )
        sentiment_breakdown = {row[0]: row[1] for row in sentiment_rows}

        # 30-day trend (latest snapshot vs 30 days ago)
        trend = self.get_trends(location_id, days=30)

        return {
            "location_id": location_id,
            "overall_rating": round(float(avg_all), 2) if avg_all else None,
            "total_reviews": total_count,
            "source_ratings": source_stats,
            "response_rate": response_rate,
            "responded_count": responded_count,
            "sentiment_breakdown": sentiment_breakdown,
            "recent_reviews": [
                self._review_to_dict(r) for r in recent_reviews
            ],
            "unread_alerts": [
                self._alert_to_dict(a) for a in unread_alerts
            ],
            "trends": trend,
        }

    # ------------------------------------------------------------------
    # Trends
    # ------------------------------------------------------------------

    def get_trends(self, location_id: int, days: int = 30) -> Dict[str, Any]:
        """Rating trends over time from reputation snapshots.

        Returns daily snapshot data and computed deltas for overall rating
        and review volume compared to the start of the period.
        """
        cutoff = date.today() - timedelta(days=days)

        snapshots = (
            self.db.query(ReputationSnapshot)
            .filter(
                ReputationSnapshot.location_id == location_id,
                ReputationSnapshot.snapshot_date >= cutoff,
            )
            .order_by(ReputationSnapshot.snapshot_date.asc())
            .all()
        )

        daily_data = []
        for snap in snapshots:
            daily_data.append({
                "date": snap.snapshot_date.isoformat(),
                "overall_rating": float(snap.overall_rating) if snap.overall_rating else None,
                "total_reviews": snap.total_reviews,
                "google_rating": float(snap.google_rating) if snap.google_rating else None,
                "yelp_rating": float(snap.yelp_rating) if snap.yelp_rating else None,
                "tripadvisor_rating": float(snap.tripadvisor_rating) if snap.tripadvisor_rating else None,
                "facebook_rating": float(snap.facebook_rating) if snap.facebook_rating else None,
                "internal_rating": float(snap.internal_rating) if snap.internal_rating else None,
                "positive_pct": float(snap.positive_pct) if snap.positive_pct else None,
                "negative_pct": float(snap.negative_pct) if snap.negative_pct else None,
            })

        # Compute deltas
        rating_delta: Optional[float] = None
        review_count_delta: int = 0

        if len(snapshots) >= 2:
            first = snapshots[0]
            last = snapshots[-1]
            if first.overall_rating and last.overall_rating:
                rating_delta = round(
                    float(last.overall_rating) - float(first.overall_rating), 2
                )
            review_count_delta = last.total_reviews - first.total_reviews

        return {
            "period_days": days,
            "data_points": len(daily_data),
            "daily": daily_data,
            "rating_delta": rating_delta,
            "review_count_delta": review_count_delta,
        }

    # ------------------------------------------------------------------
    # Keyword Analysis
    # ------------------------------------------------------------------

    def get_keyword_analysis(
        self, location_id: int, days: int = 30
    ) -> Dict[str, Any]:
        """Most mentioned topics/keywords across reviews for a location.

        Aggregates keyword data from reviews within the specified time window
        and returns counts per topic plus sentiment distribution per topic.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        reviews = (
            self.db.query(ExternalReview)
            .filter(
                ExternalReview.location_id == location_id,
                ExternalReview.keywords.isnot(None),
                or_(
                    ExternalReview.review_date >= cutoff,
                    and_(
                        ExternalReview.review_date.is_(None),
                        ExternalReview.created_at >= cutoff,
                    ),
                ),
            )
            .all()
        )

        topic_counts: Counter = Counter()
        topic_sentiment: Dict[str, Dict[str, int]] = {}

        for review in reviews:
            try:
                keywords = json.loads(review.keywords) if review.keywords else []
            except (json.JSONDecodeError, TypeError):
                keywords = []

            sentiment = review.sentiment or ReviewSentiment.NEUTRAL.value
            for kw in keywords:
                topic_counts[kw] += 1
                if kw not in topic_sentiment:
                    topic_sentiment[kw] = {"positive": 0, "neutral": 0, "negative": 0}
                if sentiment in topic_sentiment[kw]:
                    topic_sentiment[kw][sentiment] += 1

        # Sort by frequency
        sorted_topics = topic_counts.most_common(20)

        return {
            "period_days": days,
            "total_reviews_analyzed": len(reviews),
            "topics": [
                {
                    "topic": topic,
                    "mention_count": count,
                    "sentiment": topic_sentiment.get(topic, {}),
                }
                for topic, count in sorted_topics
            ],
        }

    # ------------------------------------------------------------------
    # Flagging
    # ------------------------------------------------------------------

    def flag_review(self, review_id: int, reason: str) -> ExternalReview:
        """Flag a review for attention."""
        review = self.get_review_by_id(review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")

        review.is_flagged = True
        review.flag_reason = reason
        self.db.flush()
        logger.info("Review id=%s flagged: %s", review_id, reason)
        return review

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def check_alerts(self, location_id: int) -> List[ReviewAlert]:
        """Generate alerts for negative reviews and rating drops.

        Scans recent reviews (last 24 hours) for negative sentiment and
        checks for overall rating drops.  Only creates an alert if one
        does not already exist for the same review.
        """
        created_alerts: List[ReviewAlert] = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        # Negative reviews in the last 24 hours without existing alerts
        negative_reviews = (
            self.db.query(ExternalReview)
            .filter(
                ExternalReview.location_id == location_id,
                ExternalReview.sentiment == ReviewSentiment.NEGATIVE.value,
                or_(
                    ExternalReview.review_date >= cutoff,
                    and_(
                        ExternalReview.review_date.is_(None),
                        ExternalReview.created_at >= cutoff,
                    ),
                ),
            )
            .all()
        )

        existing_alert_review_ids = set(
            row[0]
            for row in self.db.query(ReviewAlert.review_id)
            .filter(
                ReviewAlert.location_id == location_id,
                ReviewAlert.alert_type == "negative_review",
            )
            .all()
        )

        for review in negative_reviews:
            if review.id in existing_alert_review_ids:
                continue

            rating_val = float(review.rating) if review.rating else 0
            if rating_val <= 2.0:
                severity = "critical"
            elif rating_val <= 3.0:
                severity = "high"
            else:
                severity = "medium"

            author = review.author_name or "Anonymous"
            source_label = review.source or "unknown"
            message = (
                f"Negative review from {author} on {source_label} "
                f"(rating: {review.rating or 'N/A'}): "
                f"{(review.review_text or '')[:120]}"
            )

            alert = ReviewAlert(
                location_id=location_id,
                review_id=review.id,
                alert_type="negative_review",
                severity=severity,
                message=message,
            )
            self.db.add(alert)
            created_alerts.append(alert)

        # Check for rating drop by comparing latest two snapshots
        recent_snapshots = (
            self.db.query(ReputationSnapshot)
            .filter(ReputationSnapshot.location_id == location_id)
            .order_by(desc(ReputationSnapshot.snapshot_date))
            .limit(2)
            .all()
        )

        if len(recent_snapshots) == 2:
            latest = recent_snapshots[0]
            previous = recent_snapshots[1]

            if latest.overall_rating and previous.overall_rating:
                delta = float(latest.overall_rating) - float(previous.overall_rating)
                if delta <= -0.2:
                    # Check if a rating_drop alert already exists for today
                    existing_drop = (
                        self.db.query(ReviewAlert)
                        .filter(
                            ReviewAlert.location_id == location_id,
                            ReviewAlert.alert_type == "rating_drop",
                            func.date(ReviewAlert.created_at) == date.today(),
                        )
                        .first()
                    )
                    if not existing_drop:
                        # Use the latest review id as a reference for the alert
                        latest_review = (
                            self.db.query(ExternalReview)
                            .filter(ExternalReview.location_id == location_id)
                            .order_by(desc(ExternalReview.created_at))
                            .first()
                        )
                        ref_review_id = latest_review.id if latest_review else 0

                        if ref_review_id:
                            drop_severity = "critical" if delta <= -0.5 else "high"
                            drop_alert = ReviewAlert(
                                location_id=location_id,
                                review_id=ref_review_id,
                                alert_type="rating_drop",
                                severity=drop_severity,
                                message=(
                                    f"Overall rating dropped by {abs(delta):.2f} points "
                                    f"(from {float(previous.overall_rating):.2f} to "
                                    f"{float(latest.overall_rating):.2f})"
                                ),
                            )
                            self.db.add(drop_alert)
                            created_alerts.append(drop_alert)

        # Check for trending complaints (3+ negative reviews with same topic in 7 days)
        week_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent_negative = (
            self.db.query(ExternalReview)
            .filter(
                ExternalReview.location_id == location_id,
                ExternalReview.sentiment == ReviewSentiment.NEGATIVE.value,
                ExternalReview.keywords.isnot(None),
                or_(
                    ExternalReview.review_date >= week_cutoff,
                    and_(
                        ExternalReview.review_date.is_(None),
                        ExternalReview.created_at >= week_cutoff,
                    ),
                ),
            )
            .all()
        )

        complaint_topics: Counter = Counter()
        for rev in recent_negative:
            try:
                kws = json.loads(rev.keywords) if rev.keywords else []
            except (json.JSONDecodeError, TypeError):
                kws = []
            for kw in kws:
                complaint_topics[kw] += 1

        for topic, count in complaint_topics.items():
            if count >= 3:
                existing_trend = (
                    self.db.query(ReviewAlert)
                    .filter(
                        ReviewAlert.location_id == location_id,
                        ReviewAlert.alert_type == "trending_complaint",
                        ReviewAlert.message.contains(topic),
                        func.date(ReviewAlert.created_at) == date.today(),
                    )
                    .first()
                )
                if not existing_trend:
                    latest_review = (
                        self.db.query(ExternalReview)
                        .filter(ExternalReview.location_id == location_id)
                        .order_by(desc(ExternalReview.created_at))
                        .first()
                    )
                    ref_id = latest_review.id if latest_review else 0
                    if ref_id:
                        trend_alert = ReviewAlert(
                            location_id=location_id,
                            review_id=ref_id,
                            alert_type="trending_complaint",
                            severity="high",
                            message=(
                                f"Trending complaint: '{topic}' mentioned in "
                                f"{count} negative reviews in the past 7 days"
                            ),
                        )
                        self.db.add(trend_alert)
                        created_alerts.append(trend_alert)

        if created_alerts:
            self.db.flush()
            logger.info(
                "Generated %d alerts for location=%s",
                len(created_alerts),
                location_id,
            )
        return created_alerts

    def get_alerts(
        self,
        location_id: int,
        unread_only: bool = True,
    ) -> List[ReviewAlert]:
        """Get alerts for a location, optionally filtered to unread only."""
        query = self.db.query(ReviewAlert).filter(
            ReviewAlert.location_id == location_id
        )
        if unread_only:
            query = query.filter(ReviewAlert.is_read == False)  # noqa: E712
        return query.order_by(desc(ReviewAlert.created_at)).all()

    def mark_alert_read(self, alert_id: int, user_id: int) -> ReviewAlert:
        """Mark an alert as read."""
        alert = (
            self.db.query(ReviewAlert)
            .filter(ReviewAlert.id == alert_id)
            .first()
        )
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.is_read = True
        alert.read_by = user_id
        self.db.flush()
        return alert

    # ------------------------------------------------------------------
    # Competitor Comparison (Placeholder)
    # ------------------------------------------------------------------

    def get_competitor_comparison(
        self, location_id: int
    ) -> Dict[str, Any]:
        """Placeholder for competitor rating comparison.

        In a production implementation this would integrate with third-party
        APIs to fetch competitor restaurant ratings.  For now it returns
        the location's own ratings alongside industry benchmark averages.
        """
        source_stats = self._get_source_stats(location_id)

        overall = (
            self.db.query(func.avg(ExternalReview.rating))
            .filter(
                ExternalReview.location_id == location_id,
                ExternalReview.rating.isnot(None),
            )
            .scalar()
        )

        # Industry benchmarks (static averages for demonstration)
        benchmarks = {
            "google": {"industry_avg": 4.1, "top_quartile": 4.5},
            "yelp": {"industry_avg": 3.8, "top_quartile": 4.3},
            "tripadvisor": {"industry_avg": 4.0, "top_quartile": 4.4},
            "facebook": {"industry_avg": 4.2, "top_quartile": 4.6},
        }

        comparison = {}
        for source_name, benchmark in benchmarks.items():
            our_rating = source_stats.get(source_name, {}).get("avg_rating")
            comparison[source_name] = {
                "our_rating": our_rating,
                "our_review_count": source_stats.get(source_name, {}).get("count", 0),
                "industry_avg": benchmark["industry_avg"],
                "top_quartile": benchmark["top_quartile"],
                "vs_industry": (
                    round(our_rating - benchmark["industry_avg"], 2)
                    if our_rating
                    else None
                ),
                "vs_top_quartile": (
                    round(our_rating - benchmark["top_quartile"], 2)
                    if our_rating
                    else None
                ),
            }

        return {
            "location_id": location_id,
            "overall_rating": round(float(overall), 2) if overall else None,
            "source_comparison": comparison,
            "note": (
                "Competitor data is based on industry benchmarks. "
                "Connect third-party API integrations for live competitor tracking."
            ),
        }

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def get_templates(
        self, active_only: bool = True
    ) -> List[ResponseTemplate]:
        """List all response templates."""
        query = self.db.query(ResponseTemplate)
        if active_only:
            query = query.filter(ResponseTemplate.is_active == True)  # noqa: E712
        return query.order_by(ResponseTemplate.category, ResponseTemplate.name).all()

    def create_template(self, data: Dict[str, Any]) -> ResponseTemplate:
        """Create a new response template."""
        template = ResponseTemplate(
            name=data["name"],
            category=data["category"],
            template_text=data["template_text"],
            variables=json.dumps(data.get("variables")) if data.get("variables") else None,
            is_active=data.get("is_active", True),
        )
        self.db.add(template)
        self.db.flush()
        logger.info("Created response template id=%s name=%s", template.id, template.name)
        return template

    def update_template(
        self, template_id: int, data: Dict[str, Any]
    ) -> ResponseTemplate:
        """Update an existing response template."""
        template = (
            self.db.query(ResponseTemplate)
            .filter(ResponseTemplate.id == template_id)
            .first()
        )
        if not template:
            raise ValueError(f"Template {template_id} not found")

        if "name" in data:
            template.name = data["name"]
        if "category" in data:
            template.category = data["category"]
        if "template_text" in data:
            template.template_text = data["template_text"]
        if "variables" in data:
            template.variables = (
                json.dumps(data["variables"]) if data["variables"] else None
            )
        if "is_active" in data:
            template.is_active = data["is_active"]

        self.db.flush()
        logger.info("Updated response template id=%s", template_id)
        return template

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _review_to_dict(review: ExternalReview) -> Dict[str, Any]:
        """Convert a review ORM instance to a plain dictionary."""
        keywords_list: List[str] = []
        if review.keywords:
            try:
                keywords_list = json.loads(review.keywords)
            except (json.JSONDecodeError, TypeError):
                keywords_list = []

        return {
            "id": review.id,
            "location_id": review.location_id,
            "source": review.source,
            "external_id": review.external_id,
            "author_name": review.author_name,
            "rating": float(review.rating) if review.rating is not None else None,
            "review_text": review.review_text,
            "review_date": (
                review.review_date.isoformat() if review.review_date else None
            ),
            "sentiment": review.sentiment,
            "sentiment_score": (
                float(review.sentiment_score)
                if review.sentiment_score is not None
                else None
            ),
            "keywords": keywords_list,
            "response_text": review.response_text,
            "response_date": (
                review.response_date.isoformat() if review.response_date else None
            ),
            "responded_by": review.responded_by,
            "is_flagged": review.is_flagged,
            "flag_reason": review.flag_reason,
            "created_at": (
                review.created_at.isoformat() if review.created_at else None
            ),
        }

    @staticmethod
    def _alert_to_dict(alert: ReviewAlert) -> Dict[str, Any]:
        """Convert an alert ORM instance to a plain dictionary."""
        return {
            "id": alert.id,
            "location_id": alert.location_id,
            "review_id": alert.review_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "is_read": alert.is_read,
            "read_by": alert.read_by,
            "created_at": (
                alert.created_at.isoformat() if alert.created_at else None
            ),
        }

    @staticmethod
    def _template_to_dict(template: ResponseTemplate) -> Dict[str, Any]:
        """Convert a template ORM instance to a plain dictionary."""
        variables_list: Optional[List[str]] = None
        if template.variables:
            try:
                variables_list = json.loads(template.variables)
            except (json.JSONDecodeError, TypeError):
                variables_list = None

        return {
            "id": template.id,
            "name": template.name,
            "category": template.category,
            "template_text": template.template_text,
            "variables": variables_list,
            "is_active": template.is_active,
            "created_at": (
                template.created_at.isoformat() if template.created_at else None
            ),
        }
