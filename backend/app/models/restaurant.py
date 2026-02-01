"""Restaurant operations models - tables, checks, orders, kitchen."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class Table(Base):
    """Restaurant table for seating."""
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), nullable=False)
    capacity = Column(Integer, default=4)
    status = Column(String(20), default="available")  # available, occupied, reserved, cleaning
    area = Column(String(50), nullable=True)  # Main Floor, Bar, Patio, VIP
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    token = Column(String(100), nullable=True, unique=True)  # QR code token
    pos_table_id = Column(String(50), nullable=True)  # External POS ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    checks = relationship("Check", back_populates="table")


class Check(Base):
    """Restaurant check/bill."""
    __tablename__ = "checks"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    server_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    guest_count = Column(Integer, default=1)
    status = Column(String(20), default="open")  # open, closed, voided

    subtotal = Column(Numeric(10, 2), default=Decimal("0"))
    tax = Column(Numeric(10, 2), default=Decimal("0"))
    discount = Column(Numeric(10, 2), default=Decimal("0"))
    total = Column(Numeric(10, 2), default=Decimal("0"))
    balance_due = Column(Numeric(10, 2), default=Decimal("0"))

    notes = Column(Text, nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    table = relationship("Table", back_populates="checks")
    items = relationship("CheckItem", back_populates="check", cascade="all, delete-orphan")
    payments = relationship("CheckPayment", back_populates="check", cascade="all, delete-orphan")


class CheckItem(Base):
    """Item on a check."""
    __tablename__ = "check_items"

    id = Column(Integer, primary_key=True, index=True)
    check_id = Column(Integer, ForeignKey("checks.id"), nullable=False)
    menu_item_id = Column(Integer, nullable=True)

    name = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)

    seat_number = Column(Integer, nullable=True)
    course = Column(String(20), nullable=True)  # appetizer, main, dessert
    status = Column(String(20), default="ordered")  # ordered, fired, cooking, ready, served, voided

    notes = Column(Text, nullable=True)
    modifiers = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    fired_at = Column(DateTime, nullable=True)
    served_at = Column(DateTime, nullable=True)
    voided_at = Column(DateTime, nullable=True)
    void_reason = Column(String(200), nullable=True)

    # Relationships
    check = relationship("Check", back_populates="items")


class CheckPayment(Base):
    """Payment on a check."""
    __tablename__ = "check_payments"

    id = Column(Integer, primary_key=True, index=True)
    check_id = Column(Integer, ForeignKey("checks.id"), nullable=False)

    payment_type = Column(String(50), nullable=False)  # cash, credit, debit, gift_card
    amount = Column(Numeric(10, 2), nullable=False)
    tip = Column(Numeric(10, 2), default=Decimal("0"))

    card_last_four = Column(String(4), nullable=True)
    authorization_code = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    check = relationship("Check", back_populates="payments")


class MenuItem(Base):
    """Menu item for ordering."""
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(100), nullable=False)

    image_url = Column(String(500), nullable=True)
    available = Column(Boolean, default=True)

    prep_time_minutes = Column(Integer, nullable=True)
    station = Column(String(50), nullable=True)  # grill, fry, salad, bar

    allergens = Column(JSON, nullable=True)
    modifiers = Column(JSON, nullable=True)

    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    pos_item_id = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KitchenOrder(Base):
    """Kitchen order/ticket."""
    __tablename__ = "kitchen_orders"

    id = Column(Integer, primary_key=True, index=True)
    check_id = Column(Integer, ForeignKey("checks.id"), nullable=True)
    table_number = Column(String(50), nullable=True)

    status = Column(String(20), default="pending")  # pending, cooking, ready, completed, cancelled
    priority = Column(Integer, default=0)

    station = Column(String(50), nullable=True)
    course = Column(String(20), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    items = Column(JSON, nullable=True)  # List of items
    notes = Column(Text, nullable=True)

    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)


# Note: KitchenStation model is defined in advanced_features.py
# Import it from there instead of redefining


class GuestOrder(Base):
    """Guest order from QR code ordering."""
    __tablename__ = "guest_orders"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    table_token = Column(String(100), nullable=True)
    table_number = Column(String(50), nullable=True)

    status = Column(String(20), default="received")  # received, confirmed, preparing, ready, served, cancelled
    order_type = Column(String(20), default="dine-in")  # dine-in, takeout, delivery

    subtotal = Column(Numeric(10, 2), default=Decimal("0"))
    tax = Column(Numeric(10, 2), default=Decimal("0"))
    total = Column(Numeric(10, 2), default=Decimal("0"))

    items = Column(JSON, nullable=True)  # List of ordered items
    notes = Column(Text, nullable=True)

    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)

    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Payment fields
    payment_status = Column(String(20), default="unpaid")  # unpaid, pending, paid, refunded
    payment_method = Column(String(20), nullable=True)  # card, cash, online
    tip_amount = Column(Numeric(10, 2), default=Decimal("0"))
    paid_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    ready_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
