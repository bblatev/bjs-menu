"""
Integration Models
Missing model classes needed by untracked route files.
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum, Index, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from app.db.base import Base


# ============================================================================
# SPLIT BILL MODELS
# ============================================================================

class SplitBillStatus(str, enum.Enum):
    ACTIVE = "active"
    PARTIALLY_PAID = "partially_paid"
    FULLY_PAID = "fully_paid"
    CANCELLED = "cancelled"


class SplitBill(Base):
    __tablename__ = "split_bills"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    split_type = Column(String(30), nullable=False, default="equal")
    num_guests = Column(Integer, default=2)
    total_amount = Column(Float, default=0.0)
    total_tips = Column(Float, default=0.0)
    status = Column(Enum(SplitBillStatus), default=SplitBillStatus.ACTIVE)
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    guests = relationship("SplitBillGuest", back_populates="split_bill", cascade="all, delete-orphan")
    orders = relationship("SplitBillOrder", back_populates="split_bill", cascade="all, delete-orphan")


class SplitBillOrder(Base):
    __tablename__ = "split_bill_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    split_bill_id = Column(Integer, ForeignKey("split_bills.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    split_bill = relationship("SplitBill", back_populates="orders")
    order = relationship("Order")


class SplitBillGuest(Base):
    __tablename__ = "split_bill_guests"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    split_bill_id = Column(Integer, ForeignKey("split_bills.id"), nullable=False)
    guest_number = Column(Integer, nullable=False)
    guest_name = Column(String(100), nullable=True)
    amount = Column(Float, default=0.0)
    paid = Column(Boolean, default=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_method = Column(String(30), nullable=True)
    tip_amount = Column(Float, default=0.0)

    split_bill = relationship("SplitBill", back_populates="guests")
    items = relationship("SplitBillGuestItem", back_populates="guest", cascade="all, delete-orphan")


class SplitBillGuestItem(Base):
    __tablename__ = "split_bill_guest_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    guest_id = Column(Integer, ForeignKey("split_bill_guests.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    quantity = Column(Float, default=1.0)

    guest = relationship("SplitBillGuest", back_populates="items")


# ============================================================================
# HELD ORDER MODELS
# ============================================================================

class HeldOrderStatus(str, enum.Enum):
    HELD = "held"
    RESUMED = "resumed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class HeldOrder(Base):
    __tablename__ = "held_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    original_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    hold_reason = Column(String(200), nullable=True)
    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    order_data = Column(JSON, nullable=True)
    total_amount = Column(Float, default=0.0)
    status = Column(Enum(HeldOrderStatus), default=HeldOrderStatus.HELD)
    held_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    held_at = Column(DateTime(timezone=True), server_default=func.now())
    resumed_at = Column(DateTime(timezone=True), nullable=True)
    resumed_by = Column(Integer, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)


# ============================================================================
# TABLE MERGE MODELS
# ============================================================================

class TableMerge(Base):
    __tablename__ = "table_merges"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    primary_table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    merged_at = Column(DateTime(timezone=True), server_default=func.now())
    merged_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    notes = Column(String(500), nullable=True)
    unmerged_at = Column(DateTime(timezone=True), nullable=True)
    unmerged_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    items = relationship("TableMergeItem", back_populates="merge", cascade="all, delete-orphan")


class TableMergeItem(Base):
    __tablename__ = "table_merge_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    merge_id = Column(Integer, ForeignKey("table_merges.id"), nullable=False)
    secondary_table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)

    merge = relationship("TableMerge", back_populates="items")


# ============================================================================
# TABLE SESSION MODELS
# ============================================================================

class TableSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class TableSession(Base):
    __tablename__ = "table_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    guest_count = Column(Integer, default=1)
    waiter_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    guest_name = Column(String(100), nullable=True)
    status = Column(Enum(TableSessionStatus), default=TableSessionStatus.ACTIVE)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)


class TableHistory(Base):
    __tablename__ = "table_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("table_sessions.id"), nullable=True)
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSON, nullable=True)
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================================
# FLOOR PLAN MODELS
# ============================================================================

class FloorPlan(Base):
    __tablename__ = "floor_plans"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    width = Column(Float, default=800.0)
    height = Column(Float, default=600.0)
    background_image = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    table_positions = relationship("FloorPlanTablePosition", back_populates="floor_plan", cascade="all, delete-orphan")
    areas = relationship("FloorPlanArea", back_populates="floor_plan", cascade="all, delete-orphan")


class FloorPlanTablePosition(Base):
    __tablename__ = "floor_plan_table_positions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    floor_plan_id = Column(Integer, ForeignKey("floor_plans.id"), nullable=False)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    x = Column(Float, default=0.0)
    y = Column(Float, default=0.0)
    width = Column(Float, default=60.0)
    height = Column(Float, default=60.0)
    rotation = Column(Float, default=0.0)
    shape = Column(String(20), default="circle")

    floor_plan = relationship("FloorPlan", back_populates="table_positions")
    table = relationship("Table")


class FloorPlanArea(Base):
    __tablename__ = "floor_plan_areas"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    floor_plan_id = Column(Integer, ForeignKey("floor_plans.id"), nullable=False)
    name = Column(String(100), nullable=False)
    color = Column(String(20), default="#CCCCCC")
    x = Column(Float, default=0.0)
    y = Column(Float, default=0.0)
    width = Column(Float, default=200.0)
    height = Column(Float, default=200.0)

    floor_plan = relationship("FloorPlan", back_populates="areas")


# ============================================================================
# KIOSK CONFIG MODEL
# ============================================================================

class KioskConfig(Base):
    __tablename__ = "kiosk_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    enabled = Column(Boolean, default=False)
    idle_timeout_seconds = Column(Integer, default=120)
    show_prices = Column(Boolean, default=True)
    allow_cash_payment = Column(Boolean, default=True)
    allow_card_payment = Column(Boolean, default=True)
    require_phone_number = Column(Boolean, default=False)
    show_allergens = Column(Boolean, default=True)
    show_calories = Column(Boolean, default=False)
    language_options = Column(JSON, default=["bg", "en"])
    default_language = Column(String(10), default="bg")
    receipt_print_mode = Column(String(20), default="auto")
    custom_welcome_message = Column(Text, nullable=True)
    custom_thank_you_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============================================================================
# VENUE SETTINGS MODEL
# ============================================================================

class VenueSettings(Base):
    __tablename__ = "venue_settings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, unique=True, index=True)
    currency = Column(String(10), default="BGN")
    timezone = Column(String(50), default="Europe/Sofia")
    tax_rate = Column(Float, default=20.0)
    service_charge_rate = Column(Float, default=0.0)
    auto_gratuity_rate = Column(Float, default=0.0)
    auto_gratuity_threshold = Column(Integer, default=6)
    default_language = Column(String(10), default="bg")
    receipt_header = Column(Text, nullable=True)
    receipt_footer = Column(Text, nullable=True)
    opening_time = Column(String(5), default="09:00")
    closing_time = Column(String(5), default="23:00")
    settings_json = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="settings")


# ============================================================================
# DRIVE-THRU ORDER MODEL
# ============================================================================

class DriveThruOrder(Base):
    __tablename__ = "drive_thru_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    lane = Column(String(20), nullable=False, default="lane_1")
    queue_position = Column(Integer, default=0)
    status = Column(String(30), default="queued")
    vehicle_description = Column(String(200), nullable=True)
    license_plate = Column(String(20), nullable=True)
    customer_name = Column(String(100), nullable=True)
    estimated_wait_minutes = Column(Integer, nullable=True)
    total_amount = Column(Float, default=0.0)
    payment_method = Column(String(20), nullable=True)
    items_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    venue = relationship("Venue", backref="drive_thru_orders")
    order = relationship("Order", backref="drive_thru_order")


# ============================================================================
# AGGREGATOR ORDER MODEL (for v6_endpoints.py)
# ============================================================================

class AggregatorOrder(Base):
    __tablename__ = "aggregator_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    aggregator_order_id = Column(String(100), nullable=False, index=True)
    platform = Column(String(30), nullable=False)  # ubereats, doordash, glovo, etc
    status = Column(String(30), default="new")
    customer_name = Column(String(200), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    items = Column(JSON, nullable=True)
    subtotal = Column(Float, default=0.0)
    delivery_fee = Column(Float, default=0.0)
    platform_fee = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    ordered_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    ready_at = Column(DateTime(timezone=True), nullable=True)
    picked_up_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    venue = relationship("Venue", backref="aggregator_orders")
