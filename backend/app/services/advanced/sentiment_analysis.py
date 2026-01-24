"""Review Sentiment Analysis Service - AI-powered analysis."""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
import re

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.advanced_features import ReviewSentiment


class SentimentAnalysisService:
    """Service for AI-powered review sentiment analysis."""

    def __init__(self, db: Session):
        self.db = db

    # Simplified sentiment keywords (would use ML model in production)
    POSITIVE_WORDS = {
        "excellent", "amazing", "great", "wonderful", "fantastic", "delicious",
        "fresh", "friendly", "fast", "clean", "love", "best", "perfect",
        "outstanding", "superb", "incredible", "recommend", "impressed"
    }

    NEGATIVE_WORDS = {
        "terrible", "awful", "horrible", "disgusting", "slow", "rude", "cold",
        "dirty", "overpriced", "worst", "disappointing", "bad", "poor", "never",
        "wait", "mistake", "wrong", "stale", "bland", "complaint"
    }

    TOPICS = {
        "food_quality": ["food", "dish", "meal", "taste", "flavor", "fresh", "cooked", "portion"],
        "service": ["service", "staff", "waiter", "waitress", "server", "friendly", "attentive", "rude"],
        "atmosphere": ["atmosphere", "ambiance", "decor", "music", "clean", "comfortable", "cozy"],
        "value": ["price", "value", "expensive", "cheap", "worth", "portion", "overpriced"],
        "speed": ["wait", "slow", "fast", "quick", "time", "minutes", "hour"],
    }

    def analyze_review(
        self,
        location_id: int,
        source: str,
        review_text: str,
        rating: Optional[float] = None,
        review_date: Optional[date] = None,
        external_review_id: Optional[str] = None,
        reviewer_name: Optional[str] = None,
    ) -> ReviewSentiment:
        """Analyze a review and store sentiment data."""
        if review_date is None:
            review_date = date.today()

        # Analyze sentiment
        sentiment_score, overall = self._analyze_sentiment(review_text)
        topics = self._extract_topics(review_text)
        positive_phrases, negative_phrases = self._extract_phrases(review_text)

        # Determine if response needed
        needs_response = sentiment_score < -0.3 or (rating and rating <= 2)

        review = ReviewSentiment(
            location_id=location_id,
            source=source,
            external_review_id=external_review_id,
            review_text=review_text,
            rating=rating,
            review_date=review_date,
            reviewer_name=reviewer_name,
            overall_sentiment=overall,
            sentiment_score=sentiment_score,
            topics=topics,
            positive_phrases=positive_phrases,
            negative_phrases=negative_phrases,
            needs_response=needs_response,
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def _analyze_sentiment(self, text: str) -> tuple[float, str]:
        """Analyze sentiment of text. Returns (score, label)."""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))

        positive_count = len(words & self.POSITIVE_WORDS)
        negative_count = len(words & self.NEGATIVE_WORDS)

        total = positive_count + negative_count
        if total == 0:
            return 0.0, "neutral"

        score = (positive_count - negative_count) / total

        if score > 0.3:
            label = "positive"
        elif score < -0.3:
            label = "negative"
        elif positive_count > 0 and negative_count > 0:
            label = "mixed"
        else:
            label = "neutral"

        return score, label

    def _extract_topics(self, text: str) -> List[Dict[str, Any]]:
        """Extract topics and their sentiment from text."""
        text_lower = text.lower()
        topics = []

        for topic, keywords in self.TOPICS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > 0:
                # Calculate local sentiment for this topic
                sentences = text_lower.split('.')
                topic_sentences = [s for s in sentences if any(kw in s for kw in keywords)]

                if topic_sentences:
                    combined = ' '.join(topic_sentences)
                    score, _ = self._analyze_sentiment(combined)
                else:
                    score = 0

                topics.append({
                    "topic": topic,
                    "sentiment": score,
                    "mentions": matches,
                })

        return topics

    def _extract_phrases(self, text: str) -> tuple[List[str], List[str]]:
        """Extract positive and negative phrases."""
        sentences = text.split('.')
        positive = []
        negative = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            words = set(re.findall(r'\b\w+\b', sentence.lower()))

            if words & self.POSITIVE_WORDS:
                positive.append(sentence)
            elif words & self.NEGATIVE_WORDS:
                negative.append(sentence)

        return positive[:5], negative[:5]  # Limit to top 5

    def get_reviews(
        self,
        location_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sentiment: Optional[str] = None,
        source: Optional[str] = None,
        needs_response: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ReviewSentiment]:
        """Get reviews with filters."""
        query = select(ReviewSentiment).where(
            ReviewSentiment.location_id == location_id
        )

        if start_date:
            query = query.where(ReviewSentiment.review_date >= start_date)
        if end_date:
            query = query.where(ReviewSentiment.review_date <= end_date)
        if sentiment:
            query = query.where(ReviewSentiment.overall_sentiment == sentiment)
        if source:
            query = query.where(ReviewSentiment.source == source)
        if needs_response is not None:
            query = query.where(ReviewSentiment.needs_response == needs_response)

        query = query.order_by(ReviewSentiment.review_date.desc()).limit(limit).offset(offset)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_summary(
        self,
        location_id: int,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get sentiment summary for a location."""
        start_date = date.today() - timedelta(days=days)

        # Overall counts
        query = select(
            func.count(ReviewSentiment.id).label("total"),
            func.avg(ReviewSentiment.sentiment_score).label("avg_score"),
        ).where(
            and_(
                ReviewSentiment.location_id == location_id,
                ReviewSentiment.review_date >= start_date,
            )
        )
        result = self.db.execute(query)
        totals = result.first()

        # By sentiment
        sentiment_query = select(
            ReviewSentiment.overall_sentiment,
            func.count(ReviewSentiment.id).label("count"),
        ).where(
            and_(
                ReviewSentiment.location_id == location_id,
                ReviewSentiment.review_date >= start_date,
            )
        ).group_by(ReviewSentiment.overall_sentiment)

        sentiment_result = self.db.execute(sentiment_query)
        by_sentiment = {row.overall_sentiment: row.count for row in sentiment_result.all()}

        # Pending responses
        pending_query = select(
            func.count(ReviewSentiment.id)
        ).where(
            and_(
                ReviewSentiment.location_id == location_id,
                ReviewSentiment.needs_response == True,
                ReviewSentiment.response_sent == False,
            )
        )
        pending_result = self.db.execute(pending_query)
        pending_responses = pending_result.scalar() or 0

        # Aggregate topics
        reviews = self.get_reviews(location_id, start_date=start_date)

        topic_scores = {}
        for review in reviews:
            for topic_data in (review.topics or []):
                topic = topic_data.get("topic")
                score = topic_data.get("sentiment", 0)
                if topic not in topic_scores:
                    topic_scores[topic] = {"total": 0, "count": 0}
                topic_scores[topic]["total"] += score
                topic_scores[topic]["count"] += 1

        # Calculate averages and sort
        topic_averages = [
            {"topic": topic, "avg_sentiment": data["total"] / data["count"]}
            for topic, data in topic_scores.items()
            if data["count"] > 0
        ]
        top_positive = sorted(topic_averages, key=lambda x: x["avg_sentiment"], reverse=True)[:5]
        top_negative = sorted(topic_averages, key=lambda x: x["avg_sentiment"])[:5]

        return {
            "total_reviews": totals.total or 0,
            "avg_sentiment_score": float(totals.avg_score or 0),
            "positive_count": by_sentiment.get("positive", 0),
            "negative_count": by_sentiment.get("negative", 0),
            "neutral_count": by_sentiment.get("neutral", 0),
            "mixed_count": by_sentiment.get("mixed", 0),
            "top_positive_topics": top_positive,
            "top_negative_topics": top_negative,
            "pending_responses": pending_responses,
        }

    def generate_response(
        self,
        review_id: int,
    ) -> Dict[str, Any]:
        """Generate a suggested response for a review."""
        review = self.db.get(ReviewSentiment, review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")

        # Generate response based on sentiment
        if review.overall_sentiment == "negative":
            response = (
                f"Thank you for taking the time to share your feedback. "
                f"We're truly sorry to hear about your experience. "
                f"We take all feedback seriously and would love the opportunity "
                f"to make things right. Please reach out to us directly at "
                f"[contact info] so we can address your concerns personally."
            )
            tone = "apologetic"
        elif review.overall_sentiment == "positive":
            response = (
                f"Thank you so much for your wonderful feedback! "
                f"We're thrilled to hear you enjoyed your experience with us. "
                f"Your kind words mean a lot to our team. "
                f"We look forward to serving you again soon!"
            )
            tone = "grateful"
        else:
            response = (
                f"Thank you for your feedback. We appreciate you taking "
                f"the time to share your thoughts. We're always looking "
                f"for ways to improve, and your input helps us do just that. "
                f"We hope to see you again!"
            )
            tone = "professional"

        key_points = []
        for topic_data in (review.topics or []):
            key_points.append(topic_data.get("topic"))

        return {
            "review_id": review_id,
            "suggested_response": response,
            "tone": tone,
            "key_points_addressed": key_points,
        }

    def send_response(
        self,
        review_id: int,
        response_text: str,
    ) -> ReviewSentiment:
        """Mark a response as sent."""
        review = self.db.get(ReviewSentiment, review_id)
        if not review:
            raise ValueError(f"Review {review_id} not found")

        review.response_sent = True
        review.response_text = response_text
        review.responded_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(review)
        return review
