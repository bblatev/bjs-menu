"""Customer model for CRM."""

from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Boolean, String, Integer, Float, DateTime, Text, JSON, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, validates
from app.db.base import Base, TimestampMixin, SoftDeleteMixin
from app.models.validators import non_negative


class Customer(Base, TimestampMixin, SoftDeleteMixin):
    """Customer model for CRM."""

    __tablename__ = "customers"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Order history stats
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    average_order: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)

    # Visit tracking
    first_visit: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_visit: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    visit_frequency: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # visits per month

    # Customer value
    lifetime_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)

    # Segmentation
    tags: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # ['VIP', 'Regular', etc.]
    segment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Champions, Loyal, etc.
    spend_trend: Mapped[Optional[str]] = mapped_column(String(20), default='stable', nullable=True)  # up, down, stable

    # RFM scoring
    rfm_recency: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rfm_frequency: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rfm_monetary: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Personal info
    birthday: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    anniversary: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acquisition_source: Mapped[Optional[str]] = mapped_column(String(50), default='direct', nullable=True)

    # Preferences
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    allergies: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # ['Gluten', 'Dairy', etc.]
    preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    favorite_items: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # Product names
    avg_party_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preferred_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Communication
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    communication_preference: Mapped[Optional[str]] = mapped_column(String(20), default='email', nullable=True)  # sms, email, none

    # Location
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)

    @validates('total_orders', 'total_spent', 'average_order', 'visit_frequency',
               'lifetime_value', 'rfm_recency', 'rfm_frequency', 'rfm_monetary')
    def _validate_non_negative(self, key, value):
        return non_negative(key, value)
