"""
Gamification System Database Models
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import enum

from app.db.base import Base


class GameProfile(Base):
    """Customer gamification profile"""
    __tablename__ = "game_profiles"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), unique=True, nullable=False)
    total_points = Column(Integer, default=0, nullable=False)
    current_level = Column(Integer, default=1, nullable=False)

    # Streaks
    current_streak_days = Column(Integer, default=0)
    longest_streak_days = Column(Integer, default=0)
    last_order_date = Column(DateTime)

    # Statistics
    total_achievements = Column(Integer, default=0)
    total_challenges_completed = Column(Integer, default=0)
    points_earned_all_time = Column(Integer, default=0)

    # Social
    social_shares_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    customer = relationship("Customer", back_populates="game_profile")
    achievements = relationship("UserAchievement", back_populates="game_profile", cascade="all, delete-orphan")
    challenges = relationship("UserChallenge", back_populates="game_profile", cascade="all, delete-orphan")
    point_transactions = relationship("PointTransaction", back_populates="game_profile", cascade="all, delete-orphan")


class UserAchievement(Base):
    """Tracks achievements unlocked by users"""
    __tablename__ = "user_achievements"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    game_profile_id = Column(Integer, ForeignKey("game_profiles.id"), nullable=False)
    achievement_id = Column(String(100), nullable=False)  # Maps to ACHIEVEMENTS dict

    unlocked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    points_awarded = Column(Integer, default=0)

    # Social sharing
    shared_on_social = Column(Boolean, default=False)
    shared_at = Column(DateTime)

    # Additional context
    extra_data = Column(JSON)  # Store additional context (renamed from metadata to avoid SQLAlchemy conflict)

    # Relationships
    game_profile = relationship("GameProfile", back_populates="achievements")


class UserChallenge(Base):
    """User's active/completed challenges"""
    __tablename__ = "user_challenges"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    game_profile_id = Column(Integer, ForeignKey("game_profiles.id"), nullable=False)
    challenge_id = Column(Integer, ForeignKey("challenges.id"), nullable=False)

    status = Column(String(20), default="active")

    # Progress
    current_progress = Column(Integer, default=0)
    target_progress = Column(Integer, nullable=False)

    # Timing
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Reward
    points_earned = Column(Integer, default=0)

    # Relationships
    game_profile = relationship("GameProfile", back_populates="challenges")
    challenge = relationship("Challenge", backref="user_challenges")


class PointTransactionType(str, enum.Enum):
    """Point transaction types"""
    EARNED_ORDER = "earned_order"
    EARNED_ACHIEVEMENT = "earned_achievement"
    EARNED_CHALLENGE = "earned_challenge"
    EARNED_BONUS = "earned_bonus"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    ADJUSTED = "adjusted"


class PointTransaction(Base):
    """History of all point transactions"""
    __tablename__ = "point_transactions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    game_profile_id = Column(Integer, ForeignKey("game_profiles.id"), nullable=False)

    transaction_type = Column(String(50), nullable=False)
    points = Column(Integer, nullable=False)  # Positive or negative
    balance_after = Column(Integer, nullable=False)

    # Context
    order_id = Column(Integer, ForeignKey("orders.id"))
    achievement_id = Column(String(100))
    challenge_id = Column(Integer, ForeignKey("challenges.id"))

    reason = Column(Text)
    extra_data = Column(JSON)  # Additional context (renamed from metadata to avoid SQLAlchemy conflict)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    game_profile = relationship("GameProfile", back_populates="point_transactions")
    order = relationship("Order")
    challenge = relationship("Challenge")


class LeaderboardEntry(Base):
    """Cached leaderboard rankings"""
    __tablename__ = "leaderboard_entries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    game_profile_id = Column(Integer, ForeignKey("game_profiles.id"), nullable=False)

    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly, seasonal, all_time
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    rank = Column(Integer, nullable=False)
    points = Column(Integer, default=0)
    order_count = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)

    # Metadata
    level = Column(Integer)
    level_name = Column(String(50))

    # Freshness
    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    venue = relationship("Venue")
    customer = relationship("Customer")
    game_profile = relationship("GameProfile")


class SocialShare(Base):
    """Track social sharing of achievements"""
    __tablename__ = "social_shares"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("user_achievements.id"))

    platform = Column(String(50))  # facebook, instagram, twitter, etc.
    share_url = Column(String(500))

    points_earned = Column(Integer, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    customer = relationship("Customer")
    achievement = relationship("UserAchievement")
