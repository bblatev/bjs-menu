"""Hardware inventory models - kegs, tanks, RFID tags."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, String, Integer, Float, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import validates

from app.db.base import Base, TimestampMixin
from app.models.validators import validate_list_of_dicts


class Keg(Base, TimestampMixin):
    """Keg inventory model."""

    __tablename__ = "kegs"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    size_liters: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    remaining_liters: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="full", nullable=False)  # full, in_use, empty, maintenance
    tap_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tapped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    location: Mapped[str] = mapped_column(String(100), default="Bar", nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Tank(Base, TimestampMixin):
    """Gas tank model (CO2, Nitrogen, etc.)."""

    __tablename__ = "tanks"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    capacity_liters: Mapped[float] = mapped_column(Float, nullable=False)
    current_level_liters: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ok", nullable=False)  # full, ok, low, critical, empty
    last_refill: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sensor_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class RFIDTag(Base, TimestampMixin):
    """RFID tag for inventory tracking."""

    __tablename__ = "rfid_tags"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    tag_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="units", nullable=False)
    zone: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active, inactive, lost
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class InventoryCountSession(Base, TimestampMixin):
    """RFID inventory count session."""

    __tablename__ = "inventory_count_sessions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    zone: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tags_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discrepancies: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="in_progress", nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class BarTab(Base, TimestampMixin):
    """Bar tab model."""

    __tablename__ = "bar_tabs"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    seat_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    card_on_file: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)  # open, closed, void
    items: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # [{menu_item_id, quantity, price, notes}]
    subtotal: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    tax: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    tip: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    total: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    @validates('items')
    def _validate_items(self, key, value):
        return validate_list_of_dicts(key, value)


class WaiterCall(Base, TimestampMixin):
    """Waiter call from guest tablet."""

    __tablename__ = "waiter_calls"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(Integer, nullable=False)
    table_number: Mapped[str] = mapped_column(String(50), nullable=False)
    call_type: Mapped[str] = mapped_column(String(50), nullable=False)  # assistance, check, refill, other
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, acknowledged, completed
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # staff_id
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Integration(Base, TimestampMixin):
    """External integration configuration."""

    __tablename__ = "integrations"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    integration_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="disconnected", nullable=False)
    config: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class ThrottleRule(Base, TimestampMixin):
    """Order throttling rule."""

    __tablename__ = "throttle_rules"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_orders_per_hour: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    max_items_per_order: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applies_to: Mapped[str] = mapped_column(String(50), default="all", nullable=False)  # all, dine-in, delivery, takeout
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class HotelGuest(Base, TimestampMixin):
    """Hotel guest for PMS integration."""

    __tablename__ = "hotel_guests"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    room_number: Mapped[str] = mapped_column(String(50), nullable=False)
    guest_name: Mapped[str] = mapped_column(String(255), nullable=False)
    check_in: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    check_out: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    vip_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    preferences: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class OfflineQueueItem(Base, TimestampMixin):
    """Offline sync queue item."""

    __tablename__ = "offline_queue"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)  # order, payment, inventory
    data: Mapped[str] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class OCRJob(Base, TimestampMixin):
    """Invoice OCR job."""

    __tablename__ = "ocr_jobs"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
