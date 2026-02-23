"""
Sentiment Analysis Service
Analyzes customer review sentiment using keyword-based scoring.
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timezone
import logging
import re

logger = logging.getLogger(__name__)

POSITIVE_WORDS = {
    "great", "excellent", "amazing", "wonderful", "fantastic", "delicious",
    "perfect", "love", "best", "outstanding", "superb", "fresh", "friendly",
    "quick", "tasty", "recommend", "awesome", "impressive", "beautiful",
    "attentive", "cozy", "clean", "generous", "flavorful", "incredible",
}

NEGATIVE_WORDS = {
    "terrible", "awful", "horrible", "worst", "disgusting", "rude", "slow",
    "cold", "stale", "dirty", "overpriced", "disappointing", "bland", "raw",
    "undercooked", "overcooked", "burned", "waiting", "ignored", "wrong",
    "missing", "never", "complaint", "mediocre", "greasy", "soggy",
}


class SentimentAnalysisService:
    """Analyze customer feedback sentiment."""

    @staticmethod
    def analyze_review(text: str) -> Dict[str, Any]:
        """Analyze review text for sentiment."""
        if not text:
            return {"sentiment": "neutral", "score": 0.0, "confidence": 0.0}

        words = set(re.findall(r'\b\w+\b', text.lower()))
        pos_count = len(words & POSITIVE_WORDS)
        neg_count = len(words & NEGATIVE_WORDS)
        total = pos_count + neg_count

        if total == 0:
            return {"sentiment": "neutral", "score": 0.0, "confidence": 0.3, "keywords": []}

        score = (pos_count - neg_count) / total
        confidence = min(total / 5, 1.0)

        if score > 0.2:
            sentiment = "positive"
        elif score < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": round(score, 2),
            "confidence": round(confidence, 2),
            "positive_keywords": list(words & POSITIVE_WORDS),
            "negative_keywords": list(words & NEGATIVE_WORDS),
        }

    @staticmethod
    def get_sentiment_trends(
        db: Session, venue_id: int, days: int = 30
    ) -> Dict[str, Any]:
        """Get sentiment trend over time."""
        return {
            "venue_id": venue_id,
            "period_days": days,
            "overall_sentiment": "positive",
            "overall_score": 0.0,
            "total_reviews": 0,
            "positive_pct": 0,
            "neutral_pct": 0,
            "negative_pct": 0,
            "trend": [],
        }

    @staticmethod
    def get_flagged_reviews(
        db: Session, venue_id: int
    ) -> List[Dict[str, Any]]:
        """Get negative reviews that need attention."""
        return []
