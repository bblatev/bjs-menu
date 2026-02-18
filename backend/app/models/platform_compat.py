"""
Platform Compatibility Models
Models ported from platform.zver.ai for feature compatibility
"""

import enum
from datetime import datetime, date, time
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Time,
    Text, ForeignKey, Numeric, JSON, Enum, UniqueConstraint, Index, func
)
from sqlalchemy.orm import relationship
from decimal import Decimal
from app.db.base import Base


class DepositStatus(str, enum.Enum):
    pending = "pending"
    collected = "collected"
    applied = "applied"
    refunded = "refunded"
    cancelled = "cancelled"


class ShiftStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    ON_BREAK = "on_break"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class OrderStatus(str, enum.Enum):
    NEW = "new"
    DRAFT = "draft"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"
    SERVED = "served"
    CANCELLED = "cancelled"


class WaiterCallStatus(str, enum.Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SPAM = "spam"


class Venue(Base):
    __tablename__ = "venues"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    name = Column(JSON, nullable=True)
    address = Column(String(500))
    phone = Column(String(20))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    stations = relationship("VenueStation", back_populates="venue")


class VenueStation(Base):
    __tablename__ = "venue_stations"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    name = Column(JSON, nullable=False)
    station_type = Column(String(50), nullable=False)  # kitchen, bar, etc
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", back_populates="stations")
    orders = relationship("Order", back_populates="station")


class TableToken(Base):
    __tablename__ = "table_tokens"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False, index=True)
    token = Column(String(100), unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    table = relationship("Table", back_populates="tokens")


class Menu(Base):
    __tablename__ = "menus"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="menus")
    versions = relationship("MenuVersion", back_populates="menu")


class MenuVersion(Base):
    __tablename__ = "menu_versions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    menu_id = Column(Integer, ForeignKey("menus.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    published = Column(Boolean, default=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    menu = relationship("Menu", back_populates="versions")


class ItemTag(Base):
    __tablename__ = "item_tags"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # vegan, spicy, new, popular
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    
    items = relationship("ItemTagLink", back_populates="tag")


class ItemTagLink(Base):
    __tablename__ = "item_tag_links"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("item_tags.id"), nullable=False, index=True)
    
    item = relationship("MenuItem", backref="tags")
    tag = relationship("ItemTag", back_populates="items")
    
    __table_args__ = (
        UniqueConstraint('item_id', 'tag_id', name='uq_item_tag'),
        {'extend_existing': True},
    )


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)  # Nullable for takeaway
    session_id = Column(Integer, nullable=True, index=True)  # Table session
    station_id = Column(Integer, ForeignKey("venue_stations.id"), nullable=True, index=True)  # Made nullable
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    waiter_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    parent_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)  # For split checks
    order_group_id = Column(String(100), nullable=True, index=True)  # Links multi-station orders
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(Enum(OrderStatus, values_callable=lambda x: [e.value for e in x]), default=OrderStatus.NEW)

    # Totals
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    discount_reason = Column(String(200), nullable=True)
    auto_gratuity = Column(Float, default=0.0)
    total = Column(Float, nullable=False)

    # Check management
    guest_count = Column(Integer, default=1)
    check_printed = Column(Boolean, default=False)
    check_printed_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    is_rush = Column(Boolean, default=False, nullable=False)
    is_vip = Column(Boolean, default=False, nullable=False)

    # ADDED: Order Type (dine-in or takeaway)
    order_type = Column(String(20), default="dine-in", nullable=False)  # "dine-in", "takeaway"
    
    # ADDED: Takeaway Customer Info
    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    estimated_ready_time = Column(DateTime(timezone=True), nullable=True)
    pickup_time = Column(DateTime(timezone=True), nullable=True)

    # ADDED: Tips & Payment Support
    tip_amount = Column(Float, default=0.0, nullable=False)
    payment_method = Column(String(20), nullable=True)  # "cash", "card"
    payment_status = Column(String(20), default="pending", nullable=False)  # "pending", "paid", "refunded"
    payment_date = Column(DateTime(timezone=True), nullable=True)

    # Kitchen timing
    kitchen_started_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    table = relationship("Table", back_populates="orders")
    station = relationship("VenueStation", back_populates="orders")
    customer = relationship("Customer", backref="orders")
    waiter = relationship("StaffUser", foreign_keys=[waiter_id])
    items = relationship("OrderItem", back_populates="order")
    events = relationship("OrderEvent", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)  # quantity * unit_price
    subtotal = Column(Float, nullable=True)  # Kept for backwards compatibility

    # Seat and course management
    seat_number = Column(Integer, nullable=True)
    course = Column(String(20), nullable=True)  # drinks, appetizer, main, dessert

    # Kitchen/bar firing
    fired = Column(Boolean, default=False)
    fired_at = Column(DateTime(timezone=True), nullable=True)
    hold_reason = Column(Text, nullable=True)

    # Modifiers and instructions
    modifiers_text = Column(Text, nullable=True)  # Comma-separated modifier names
    special_instructions = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)
    status = Column(String(20), default="active")  # active, sent, preparing, ready, delivered, voided, held

    # Void tracking
    voided_at = Column(DateTime(timezone=True), nullable=True)
    voided_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    void_reason = Column(Text, nullable=True)

    # Comp tracking
    comp_reason = Column(Text, nullable=True)
    comped_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    comped_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", backref="order_items")
    modifiers = relationship("OrderItemModifier", back_populates="order_item")


class OrderItemModifier(Base):
    __tablename__ = "order_item_modifiers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False, index=True)
    modifier_option_id = Column(Integer, ForeignKey("modifier_options.id"), nullable=False, index=True)
    price_delta = Column(Float, default=0.0)
    
    order_item = relationship("OrderItem", back_populates="modifiers")
    option = relationship("ModifierOption", backref="order_item_modifiers")


class OrderEvent(Base):
    __tablename__ = "order_events"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    status = Column(Enum(OrderStatus, values_callable=lambda x: [e.value for e in x]), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    order = relationship("Order", back_populates="events")


class LoyaltyTransaction(Base):
    """Loyalty points transactions"""
    __tablename__ = "loyalty_transactions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    transaction_type = Column(String(50), nullable=False)  # "earn", "redeem", "expire", "adjust"
    points = Column(Integer, nullable=False)  # positive for earn, negative for redeem
    balance_after = Column(Integer, nullable=False)

    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    customer = relationship("Customer", backref="loyalty_transactions")
    order = relationship("Order", backref="loyalty_transactions")
    created_by_user = relationship("StaffUser", foreign_keys=[created_by])


class PromotionUsage(Base):
    """Track promotion usage per customer"""
    __tablename__ = "promotion_usages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    promotion_id = Column(Integer, ForeignKey("promotions.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    discount_applied = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    promotion = relationship("Promotion", backref="usages")
    customer = relationship("Customer", backref="promotion_usages")
    order = relationship("Order", backref="promotion_usages")


# ============================================================================
# SUPPLIER / PURCHASE ORDERS MODELS
# ============================================================================


class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    ORDERED = "ordered"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class PurchaseOrderItem(Base):
    """Line items in a purchase order"""
    __tablename__ = "purchase_order_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)

    # Item details (in case stock item doesn't exist yet)
    item_name = Column(String(200), nullable=False)
    sku = Column(String(100), nullable=True)
    unit = Column(String(20), nullable=False)

    # Quantities
    quantity_ordered = Column(Float, nullable=False)
    quantity_received = Column(Float, default=0.0)

    # Pricing
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    notes = Column(Text, nullable=True)

    purchase_order = relationship("PurchaseOrder", backref="purchase_order_items")
    stock_item = relationship("StockItem", backref="purchase_order_items")


# ============================================================================
# AUDIT LOG MODELS
# ============================================================================


class AuditLog(Base):
    """Audit trail for all important actions"""
    __tablename__ = "audit_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Action details
    action = Column(String(50), nullable=False, index=True)  # "create", "update", "delete", "login", etc.
    entity_type = Column(String(50), nullable=False, index=True)  # "order", "menu_item", "stock_item", etc.
    entity_id = Column(Integer, nullable=True)

    # Changes
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)

    # Context
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    venue = relationship("Venue", backref="audit_logs")
    staff_user = relationship("StaffUser", backref="audit_logs")

    __table_args__ = (
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_action_date', 'action', 'created_at'),
        {'extend_existing': True},
    )


# ============================================================================
# SPLIT BILL MODELS
# ============================================================================


class GiftCardStatus(str, enum.Enum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# GiftCard is defined in advanced_features.py - DO NOT define here


# ============================================================================
# AUTOMATIC DISCOUNT / HAPPY HOUR MODELS
# ============================================================================


class AutoDiscount(Base):
    """Automatic time-based discounts (Happy Hour, etc.)"""
    __tablename__ = "auto_discounts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    discount_type = Column(String(50), nullable=False)  # happy_hour, early_bird, late_night, etc.
    discount_percentage = Column(Float, nullable=True)
    discount_amount = Column(Float, nullable=True)

    # Time restrictions
    start_time = Column(String(5), nullable=False)  # "17:00"
    end_time = Column(String(5), nullable=False)  # "19:00"
    valid_days = Column(JSON, nullable=False)  # ["monday", "tuesday", ...]

    # Item restrictions
    applicable_categories = Column(JSON, nullable=True)  # [category_id, ...]
    applicable_items = Column(JSON, nullable=True)  # [item_id, ...]

    # Limits
    min_order_amount = Column(Float, nullable=True)
    max_discount_amount = Column(Float, nullable=True)

    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="auto_discounts")


# ============================================================================
# FLOOR PLAN MODELS
# ============================================================================


class StockBatch(Base):
    """Batch tracking for stock items"""
    __tablename__ = "stock_batches"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
    batch_number = Column(String(100), nullable=False)
    initial_quantity = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)

    manufacture_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True, index=True)

    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    cost_per_unit = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stock_item = relationship("StockItem", backref="batches")
    supplier = relationship("Supplier", backref="stock_batches")
    purchase_order = relationship("PurchaseOrder", backref="stock_batches")

    __table_args__ = (
        Index('idx_batch_expiration', 'expiration_date'),
        UniqueConstraint('stock_item_id', 'batch_number', name='uq_stock_batch'),
        {'extend_existing': True},
    )


# ============================================================================
# PAYROLL MODELS
# ============================================================================


class DeliveryZone(Base):
    """Delivery zones for a venue"""
    __tablename__ = "delivery_zones"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    zone_id = Column(String(50), nullable=False, index=True)  # e.g., "zone_1", "ZONE-ABC123"
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    min_order = Column(Float, default=0.0)  # Minimum order amount
    delivery_fee = Column(Float, default=0.0)  # Delivery fee
    estimated_time = Column(Integer, default=30)  # Estimated delivery time in minutes

    # Polygon coordinates stored as JSON array of [lat, lng] pairs
    polygon = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="delivery_zones")

    __table_args__ = (
        UniqueConstraint('venue_id', 'zone_id', name='uq_venue_zone'),
        {'extend_existing': True},
    )


class DeliveryDriver(Base):
    """Delivery drivers"""
    __tablename__ = "delivery_drivers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    vehicle_type = Column(String(50), nullable=True)  # car, motorcycle, bicycle
    vehicle_registration = Column(String(20), nullable=True)

    is_active = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)

    # Current location
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    last_location_update = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="delivery_drivers")
    staff_user = relationship("StaffUser", backref="driver_profile")


class ReservationDeposit(Base):
    """Deposits for reservations (e.g., large party deposits)"""
    __tablename__ = "reservation_deposits"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False, index=True)

    # Amount info
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(10), default="BGN")

    # Status tracking
    status = Column(Enum(DepositStatus, values_callable=lambda x: [e.value for e in x]), default=DepositStatus.pending)
    payment_link = Column(String(500), nullable=True)

    # Collection info
    payment_method = Column(String(50), nullable=True)
    transaction_id = Column(String(200), nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=True)
    collected_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Application to order
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    amount_applied = Column(Numeric(12, 2), nullable=True)

    # Refund info
    refund_reason = Column(Text, nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    refunded_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    venue = relationship("Venue")
    reservation = relationship("Reservation", backref="deposits")
    order = relationship("Order")
    collected_by_user = relationship("StaffUser", foreign_keys=[collected_by])
    refunded_by_user = relationship("StaffUser", foreign_keys=[refunded_by])


# ============================================================================
# CUSTOMER / CRM MODELS
# ============================================================================


class StaffShift(Base):
    """Staff work shifts"""
    __tablename__ = "staff_shifts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)

    # Scheduled times
    scheduled_start = Column(DateTime(timezone=True), nullable=False)
    scheduled_end = Column(DateTime(timezone=True), nullable=False)

    # Actual times
    actual_start = Column(DateTime(timezone=True), nullable=True)  # Clock-in
    actual_end = Column(DateTime(timezone=True), nullable=True)  # Clock-out

    # Duration tracking
    total_break_minutes = Column(Integer, default=0)
    total_worked_minutes = Column(Integer, nullable=True)

    status = Column(Enum(ShiftStatus, values_callable=lambda x: [e.value for e in x]), default=ShiftStatus.SCHEDULED)
    notes = Column(Text, nullable=True)

    # Assignment
    assigned_station_id = Column(Integer, ForeignKey("venue_stations.id"), nullable=True)
    assigned_area = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    venue = relationship("Venue", backref="staff_shifts")
    staff_user = relationship("StaffUser", foreign_keys=[staff_user_id], backref="staff_shifts")
    assigned_station = relationship("VenueStation", backref="assigned_shifts")
    created_by_user = relationship("StaffUser", foreign_keys=[created_by])
    breaks = relationship("StaffBreak", back_populates="shift", cascade="all, delete-orphan")
    clock_events = relationship("ClockEvent", back_populates="shift", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_shift_schedule', 'venue_id', 'scheduled_start'),
        Index('idx_shift_staff', 'staff_user_id', 'scheduled_start'),
        {'extend_existing': True},
    )


class ClockEvent(Base):
    """Clock in/out events"""
    __tablename__ = "clock_events"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("staff_shifts.id"), nullable=False)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)

    event_type = Column(String(20), nullable=False)  # clock_in, clock_out, break_start, break_end
    event_time = Column(DateTime(timezone=True), server_default=func.now())

    # Location/device verification
    device_id = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    gps_latitude = Column(Float, nullable=True)
    gps_longitude = Column(Float, nullable=True)

    notes = Column(Text, nullable=True)

    shift = relationship("StaffShift", back_populates="clock_events")
    staff_user = relationship("StaffUser", backref="clock_events")


class StaffBreak(Base):
    """Break tracking during shifts"""
    __tablename__ = "staff_breaks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("staff_shifts.id"), nullable=False)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)

    break_type = Column(String(20), nullable=False)  # meal, rest, personal
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    is_paid = Column(Boolean, default=False)

    shift = relationship("StaffShift", back_populates="breaks")
    staff_user = relationship("StaffUser", backref="breaks")


# ============================================================================
# STAFF PERFORMANCE & SALES TRACKING (MISSING FEATURE)
# ============================================================================


class CashDrawer(Base):
    """Cash drawer sessions for cash responsibility tracking"""
    __tablename__ = "cash_drawers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)

    # Session
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Amounts
    opening_balance = Column(Float, nullable=False)
    expected_balance = Column(Float, nullable=True)  # Calculated from transactions
    actual_balance = Column(Float, nullable=True)  # Counted at close
    variance = Column(Float, nullable=True)

    # Transactions summary
    cash_sales = Column(Float, default=0.0)
    cash_tips = Column(Float, default=0.0)
    payouts = Column(Float, default=0.0)
    deposits = Column(Float, default=0.0)

    notes = Column(Text, nullable=True)
    status = Column(String(20), default="open")  # open, closed, reconciled

    venue = relationship("Venue", backref="cash_drawers")
    staff_user = relationship("StaffUser", backref="cash_drawer_sessions")
    transactions = relationship("CashDrawerTransaction", back_populates="drawer", cascade="all, delete-orphan")


class CashDrawerTransaction(Base):
    """Individual cash drawer transactions"""
    __tablename__ = "cash_drawer_transactions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    drawer_id = Column(Integer, ForeignKey("cash_drawers.id"), nullable=False)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)

    transaction_type = Column(String(20), nullable=False)  # cash_in, cash_out, paid_in, paid_out, adjustment
    amount = Column(Float, nullable=False)
    reason = Column(String(200), nullable=True)  # Reason for the transaction
    reference_type = Column(String(20), nullable=True)  # order, expense, etc.
    reference_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    drawer = relationship("CashDrawer", back_populates="transactions")
    staff_user = relationship("StaffUser")


# ============================================================================
# AI RISK SCORING & ANTI-FRAUD (MISSING FEATURE - ZVER CORE)
# ============================================================================


class OrderCancellation(Base):
    """Detailed tracking of order/item cancellations"""
    __tablename__ = "order_cancellations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=True)  # Null = full order

    cancellation_type = Column(String(20), nullable=False)  # full_order, partial_item, void
    reason_category = Column(String(50), nullable=False)  # customer_request, kitchen_issue, staff_error, fraud, other
    reason_detail = Column(Text, nullable=False)

    # Amount impact
    amount_cancelled = Column(Float, nullable=False)
    was_prepared = Column(Boolean, default=False)  # Was food already made?

    # Approval
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    cancelled_at = Column(DateTime(timezone=True), server_default=func.now())
    cancelled_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)

    # Refund tracking
    was_refunded = Column(Boolean, default=False)
    refund_amount = Column(Float, nullable=True)
    refund_method = Column(String(20), nullable=True)

    venue = relationship("Venue", backref="order_cancellations")
    order = relationship("Order", backref="cancellation_details")
    order_item = relationship("OrderItem", backref="cancellation_details")
    cancelled_by_user = relationship("StaffUser", foreign_keys=[cancelled_by])
    approved_by_user = relationship("StaffUser", foreign_keys=[approved_by])


# ============================================================================
# COMBO / MENU DEALS (ENHANCED MENU ITEMS)
# ============================================================================


class ComboMenu(Base):
    """Combo meals / Set menus"""
    __tablename__ = "combo_menus"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("menu_categories.id"), nullable=True)

    name = Column(JSON, nullable=False)  # Multilingual
    description = Column(JSON, nullable=True)
    image_url = Column(String(500), nullable=True)

    combo_price = Column(Float, nullable=False)  # Fixed combo price
    savings_amount = Column(Float, nullable=True)  # How much customer saves

    # Availability
    is_active = Column(Boolean, default=True)
    available_start_time = Column(String(5), nullable=True)  # "11:00"
    available_end_time = Column(String(5), nullable=True)  # "15:00"
    available_days = Column(JSON, nullable=True)  # ["monday", "tuesday", ...]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="combo_menus")
    category = relationship("MenuCategory", backref="combo_menus")
    items = relationship("ComboMenuItem", back_populates="combo", cascade="all, delete-orphan")


class ComboMenuItem(Base):
    """Items in a combo"""
    __tablename__ = "combo_menu_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    combo_id = Column(Integer, ForeignKey("combo_menus.id"), nullable=False)

    # Either a specific item or a choice from category
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True)
    choice_category_id = Column(Integer, ForeignKey("menu_categories.id"), nullable=True)

    slot_name = Column(JSON, nullable=True)  # "Main", "Side", "Drink" - multilingual
    quantity = Column(Integer, default=1)
    is_required = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    # Price adjustments for upgrades
    price_adjustment = Column(Float, default=0.0)

    combo = relationship("ComboMenu", back_populates="items")
    menu_item = relationship("MenuItem", backref="combo_appearances")
    choice_category = relationship("MenuCategory", backref="combo_choices")


# ============================================================================
# ENTERPRISE V4.0 FEATURES - NCR ALOHA / TOAST / ORACLE / LIGHTSPEED PARITY
# ============================================================================

# ----------- TRUE OFFLINE POS (Store-and-Forward) -----------


class OfflineTransaction(Base):
    """Store-and-Forward offline transactions queue"""
    __tablename__ = "offline_transactions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    
    # Offline identification
    offline_id = Column(String(100), unique=True, nullable=False, index=True)
    offline_sequence = Column(Integer, nullable=False)  # Local sequence number
    terminal_id = Column(String(50), nullable=False)
    
    transaction_type = Column(String(30), nullable=False)  # OfflineTransactionType
    transaction_data = Column(JSON, nullable=False)  # Full transaction payload
    
    # Payment specifics (for card transactions)
    payment_method = Column(String(30), nullable=True)
    amount = Column(Float, nullable=True)
    encrypted_card_data = Column(Text, nullable=True)  # P2PE encrypted
    offline_auth_code = Column(String(20), nullable=True)
    requires_voice_auth = Column(Boolean, default=False)
    floor_limit_exceeded = Column(Boolean, default=False)
    
    # Sync status
    sync_status = Column(String(20), default="pending")  # OfflineSyncStatus
    sync_attempts = Column(Integer, default=0)
    last_sync_attempt = Column(DateTime(timezone=True), nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)
    server_id = Column(Integer, nullable=True)  # ID after server sync
    
    # Conflict resolution
    has_conflict = Column(Boolean, default=False)
    conflict_type = Column(String(50), nullable=True)
    conflict_details = Column(JSON, nullable=True)
    conflict_resolved = Column(Boolean, default=False)
    resolution_type = Column(String(30), nullable=True)  # keep_local, keep_server, merge
    resolved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="offline_transactions")
    creator = relationship("StaffUser", foreign_keys=[created_by])
    resolver = relationship("StaffUser", foreign_keys=[resolved_by])

    __table_args__ = (
        Index('ix_offline_transactions_venue_sync', 'venue_id', 'sync_status'),
        Index('ix_offline_transactions_terminal_seq', 'terminal_id', 'offline_sequence'),
        {'extend_existing': True},
    )


class OfflineConnectivityLog(Base):
    """Track connectivity status changes for offline mode"""
    __tablename__ = "offline_connectivity_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    terminal_id = Column(String(50), nullable=False)
    
    event_type = Column(String(30), nullable=False)  # went_offline, came_online, sync_started, sync_completed
    services_status = Column(JSON, nullable=False)  # {internet: bool, payment_gateway: bool, ...}
    
    offline_duration_seconds = Column(Integer, nullable=True)
    transactions_queued = Column(Integer, default=0)
    transactions_synced = Column(Integer, default=0)
    sync_errors = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="connectivity_logs")


# ----------- CONVERSATIONAL ORDERING -----------


class FraudScore(Base):
    """Historical fraud index scores for employees"""
    __tablename__ = "fraud_scores"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    
    # Score breakdown (0-100 each)
    overall_score = Column(Float, nullable=False)  # Combined fraud index
    void_risk_score = Column(Float, default=0.0)
    discount_risk_score = Column(Float, default=0.0)
    cash_risk_score = Column(Float, default=0.0)
    refund_risk_score = Column(Float, default=0.0)
    time_fraud_score = Column(Float, default=0.0)
    pattern_anomaly_score = Column(Float, default=0.0)
    manager_override_score = Column(Float, default=0.0)
    
    # Risk classification
    risk_level = Column(String(20), nullable=False)  # normal, low, medium, high, critical
    
    # Context
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    transactions_analyzed = Column(Integer, default=0)
    
    # Score change
    score_change = Column(Float, nullable=True)  # vs previous period
    trend_direction = Column(String(10), nullable=True)  # up, down, stable
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="fraud_scores")
    employee = relationship("StaffUser", backref="fraud_scores")

    __table_args__ = (
        Index('ix_fraud_scores_venue_employee', 'venue_id', 'employee_id'),
        Index('ix_fraud_scores_risk_level', 'venue_id', 'risk_level'),
        {'extend_existing': True},
    )


# DynamicPricingRule is defined in advanced_features.py - DO NOT define here


class Stock(Base):
    """Stock levels at locations"""
    __tablename__ = "stock"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, nullable=False, index=True)
    item_id = Column(Integer, nullable=False, index=True)
    quantity = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class HouseAccount(Base):
    __tablename__ = "house_accounts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    account_number = Column(String(50), unique=True, nullable=False)
    account_name = Column(String(200), nullable=False)
    account_type = Column(String(50), default="corporate")  # corporate, individual, government
    status = Column(String(20), default="active")  # active, suspended, closed

    # Contact info
    contact_name = Column(String(100))
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    billing_address = Column(Text)

    # Financial settings
    credit_limit = Column(Numeric(12, 2), default=0)
    current_balance = Column(Numeric(12, 2), default=0)
    payment_terms = Column(Integer, default=30)  # days
    discount_percentage = Column(Numeric(5, 2), default=0)
    tax_id = Column(String(50))

    # Authorized users (JSON array of staff IDs)
    authorized_users = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    venue = relationship("Venue", backref="house_accounts")
    transactions = relationship("HouseAccountTransaction", back_populates="account")


class HouseAccountTransaction(Base):
    __tablename__ = "house_account_transactions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("house_accounts.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    transaction_type = Column(String(20), nullable=False)  # charge, payment, credit, adjustment
    amount = Column(Numeric(12, 2), nullable=False)
    balance_after = Column(Numeric(12, 2), nullable=False)

    description = Column(String(500))
    reference_number = Column(String(100))

    created_by = Column(Integer, ForeignKey("staff_users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    account = relationship("HouseAccount", back_populates="transactions")
    order = relationship("Order")
    staff = relationship("StaffUser")


# MarketingCampaign is defined in marketing_models.py - DO NOT define here


class ThrottleEvent(Base):
    """Log of throttling events when rules are triggered"""
    __tablename__ = "throttle_events"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    rule_id = Column(Integer, ForeignKey("throttle_rules.id"), nullable=False)
    
    # Event details
    event_type = Column(String(30), nullable=False)  # activated, deactivated, escalated
    trigger_value = Column(Integer, nullable=False)  # Current value that triggered
    threshold_value = Column(Integer, nullable=False)  # Threshold at time of trigger
    
    # Impact
    orders_affected = Column(Integer, default=0)
    items_disabled = Column(JSON, nullable=True)
    delay_added_minutes = Column(Integer, nullable=True)
    
    # Duration
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    venue = relationship("Venue", backref="throttle_events")
    rule = relationship("ThrottleRule", backref="events")



# ============================================================================
# ADDITIONAL MODELS
# ============================================================================


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    FAILED = "failed"
    VOIDED = "voided"


class Payment(Base):
    """Payment records for orders"""
    __tablename__ = "payments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    tip = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    payment_method = Column(String(20), nullable=False)
    card_last_four = Column(String(4), nullable=True)
    card_brand = Column(String(20), nullable=True)
    auth_code = Column(String(50), nullable=True)
    reference_id = Column(String(100), nullable=True)
    status = Column(Enum(PaymentStatus, values_callable=lambda x: [e.value for e in x]), default=PaymentStatus.COMPLETED)
    processed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", backref="payments")


class LoyaltyCard(Base):
    """Loyalty card"""
    __tablename__ = "loyalty_cards"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    card_number = Column(String(50), unique=True, nullable=False)
    points_balance = Column(Integer, default=0)
    tier = Column(String(20), default="bronze")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", backref="loyalty_cards")


class MenuItemModifier(Base):
    """Menu item modifier link"""
    __tablename__ = "menu_item_modifiers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    modifier_group_id = Column(Integer, ForeignKey("modifier_groups.id"), nullable=False)
    required = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    menu_item = relationship("MenuItem", backref="item_modifiers")
    modifier_group = relationship("ModifierGroup", backref="item_links")


# MenuItemVariant is defined in menu_inventory_complete.py - DO NOT define here


class KioskStatusLog(Base):
    """Kiosk status tracking"""
    __tablename__ = "kiosk_status_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    kiosk_id = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TimeEntry(Base):
    """Time tracking entries"""
    __tablename__ = "time_entries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    clock_in = Column(DateTime(timezone=True), nullable=False)
    clock_out = Column(DateTime(timezone=True), nullable=True)
    break_minutes = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    staff_user = relationship("StaffUser", backref="time_entries")

