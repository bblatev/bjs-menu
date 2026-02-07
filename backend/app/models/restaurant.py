"""Restaurant operations models - tables, checks, orders, kitchen."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship, validates

from app.db.base import Base
from app.models.validators import non_negative, positive


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

    @validates('subtotal', 'tax', 'discount', 'total', 'balance_due')
    def _validate_amounts(self, key, value):
        return non_negative(key, value)

    @validates('guest_count')
    def _validate_guest_count(self, key, value):
        return positive(key, value)


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

    @validates('quantity')
    def _validate_quantity(self, key, value):
        return positive(key, value)

    @validates('price', 'total')
    def _validate_amounts(self, key, value):
        return non_negative(key, value)


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

    @validates('amount')
    def _validate_amount(self, key, value):
        return positive(key, value)

    @validates('tip')
    def _validate_tip(self, key, value):
        return non_negative(key, value)


class MenuCategory(Base):
    """Menu category for organizing items."""
    __tablename__ = "menu_categories"

    id = Column(Integer, primary_key=True, index=True)
    name_bg = Column(String(200), nullable=False)
    name_en = Column(String(200), nullable=True)
    description_bg = Column(Text, nullable=True, default="")
    description_en = Column(Text, nullable=True, default="")
    icon = Column(String(10), nullable=True, default="🍽")
    color = Column(String(20), nullable=True, default="#3B82F6")
    image_url = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    parent_id = Column(Integer, ForeignKey("menu_categories.id"), nullable=True)
    visibility = Column(String(20), default="all")
    tax_rate = Column(Numeric(5, 2), nullable=True)
    printer_id = Column(Integer, nullable=True)
    display_on_kiosk = Column(Boolean, default=True)
    display_on_app = Column(Boolean, default=True)
    display_on_web = Column(Boolean, default=True)
    schedule = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    children = relationship("MenuCategory", backref="parent", remote_side="MenuCategory.id", lazy="select")


class MenuItem(Base):
    """Menu item for ordering."""
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=True)  # Cost/base price for turnover reporting
    category = Column(String(100), nullable=False)

    image_url = Column(String(500), nullable=True)
    available = Column(Boolean, default=True)

    prep_time_minutes = Column(Integer, nullable=True)
    station = Column(String(50), nullable=True)  # grill, fry, salad, bar

    allergens = Column(JSON, nullable=True)
    modifiers = Column(JSON, nullable=True)

    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    pos_item_id = Column(String(50), nullable=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True)  # Link to recipe for stock deduction

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipe = relationship("Recipe", foreign_keys=[recipe_id])
    modifier_group_links = relationship("MenuItemModifierGroup", back_populates="menu_item", cascade="all, delete-orphan")

    @validates('price', 'base_price')
    def _validate_price(self, key, value):
        return non_negative(key, value)


class ModifierGroup(Base):
    """A group of modifiers (e.g. 'Choose your side', 'Add toppings')."""
    __tablename__ = "modifier_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    min_selections = Column(Integer, default=0)
    max_selections = Column(Integer, default=1)
    active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    options = relationship("ModifierOption", back_populates="group", cascade="all, delete-orphan")
    menu_item_links = relationship("MenuItemModifierGroup", back_populates="modifier_group", cascade="all, delete-orphan")


class ModifierOption(Base):
    """An individual modifier option within a group."""
    __tablename__ = "modifier_options"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("modifier_groups.id"), nullable=False)
    name = Column(String(200), nullable=False)
    price_adjustment = Column(Numeric(10, 2), default=Decimal("0"))
    available = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("ModifierGroup", back_populates="options")


class MenuItemModifierGroup(Base):
    """Link table between menu items and modifier groups."""
    __tablename__ = "menu_item_modifier_groups"

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    modifier_group_id = Column(Integer, ForeignKey("modifier_groups.id"), nullable=False)
    sort_order = Column(Integer, default=0)

    menu_item = relationship("MenuItem", back_populates="modifier_group_links")
    modifier_group = relationship("ModifierGroup", back_populates="menu_item_links")


class ComboMeal(Base):
    """A combo meal that bundles multiple items at a set price."""
    __tablename__ = "combo_meals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    image_url = Column(String(500), nullable=True)
    available = Column(Boolean, default=True)
    featured = Column(Boolean, default=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("ComboItem", back_populates="combo", cascade="all, delete-orphan")


class ComboItem(Base):
    """An item included in a combo meal."""
    __tablename__ = "combo_items"

    id = Column(Integer, primary_key=True, index=True)
    combo_id = Column(Integer, ForeignKey("combo_meals.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True)
    name = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    is_choice = Column(Boolean, default=False)  # True if guest picks from options
    choice_group = Column(String(100), nullable=True)  # e.g. "Choose your side"

    combo = relationship("ComboMeal", back_populates="items")


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

    # Workflow mode support (Gap 11)
    workflow_mode = Column(String(20), default="order")  # "order" (direct) or "request" (needs confirmation)
    is_confirmed = Column(Boolean, default=True)  # For request mode: needs manager/kitchen confirmation
    confirmed_by = Column(Integer, nullable=True)  # Staff ID who confirmed
    confirmed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(200), nullable=True)

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

    @validates('subtotal', 'tax', 'total', 'tip_amount')
    def _validate_amounts(self, key, value):
        return non_negative(key, value)
