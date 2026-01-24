"""Delivery Aggregator Integration models - DoorDash/Uber Eats/Deliverect style."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class DeliveryPlatform(str, Enum):
    DOORDASH = "doordash"
    UBER_EATS = "uber_eats"
    GRUBHUB = "grubhub"
    GLOVO = "glovo"
    WOLT = "wolt"
    FOODPANDA = "foodpanda"
    DELIVEROO = "deliveroo"
    CUSTOM = "custom"


class DeliveryOrderStatus(str, Enum):
    RECEIVED = "received"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY_FOR_PICKUP = "ready_for_pickup"
    PICKED_UP = "picked_up"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


class DeliveryIntegration(Base):
    """Third-party delivery platform integration configuration."""
    __tablename__ = "delivery_integrations"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    platform = Column(SQLEnum(DeliveryPlatform), nullable=False)

    # API credentials
    api_key = Column(String(500), nullable=True)
    api_secret = Column(String(500), nullable=True)
    store_id = Column(String(200), nullable=True)  # Platform's store identifier
    merchant_id = Column(String(200), nullable=True)

    # Webhook configuration
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(200), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_menu_synced = Column(Boolean, default=False)
    last_menu_sync_at = Column(DateTime, nullable=True)
    last_order_received_at = Column(DateTime, nullable=True)

    # Settings
    auto_accept_orders = Column(Boolean, default=True)
    auto_confirm_ready = Column(Boolean, default=False)
    prep_time_minutes = Column(Integer, default=20)
    sync_inventory = Column(Boolean, default=True)  # Auto-86 items

    # Commission tracking
    commission_percent = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeliveryOrder(Base):
    """Orders received from delivery platforms."""
    __tablename__ = "delivery_orders"

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("delivery_integrations.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Platform identifiers
    platform = Column(SQLEnum(DeliveryPlatform), nullable=False)
    platform_order_id = Column(String(200), nullable=False)  # Their order ID
    platform_display_id = Column(String(50), nullable=True)   # Short display ID

    # Status
    status = Column(SQLEnum(DeliveryOrderStatus), default=DeliveryOrderStatus.RECEIVED)
    status_updated_at = Column(DateTime, nullable=True)

    # Timing
    received_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    ready_at = Column(DateTime, nullable=True)
    picked_up_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    estimated_pickup_at = Column(DateTime, nullable=True)
    estimated_delivery_at = Column(DateTime, nullable=True)

    # Customer info (from platform)
    customer_name = Column(String(200), nullable=True)
    customer_phone = Column(String(50), nullable=True)
    delivery_address = Column(Text, nullable=True)
    delivery_instructions = Column(Text, nullable=True)

    # Order details
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    delivery_fee = Column(Float, default=0.0)
    tip = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    platform_fee = Column(Float, default=0.0)  # Commission taken
    net_payout = Column(Float, default=0.0)    # What we receive

    # Special instructions
    special_instructions = Column(Text, nullable=True)
    is_scheduled = Column(Boolean, default=False)
    scheduled_for = Column(DateTime, nullable=True)

    # POS integration
    pos_order_id = Column(Integer, nullable=True)  # Linked to our order system
    sent_to_kds = Column(Boolean, default=False)
    kds_ticket_id = Column(Integer, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Raw payload (for debugging)
    raw_payload = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    integration = relationship("DeliveryIntegration", backref="orders")
    items = relationship("DeliveryOrderItem", back_populates="order", cascade="all, delete-orphan")


class DeliveryOrderItem(Base):
    """Individual items in a delivery order."""
    __tablename__ = "delivery_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("delivery_orders.id"), nullable=False)

    # Platform item info
    platform_item_id = Column(String(200), nullable=True)
    item_name = Column(String(300), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)

    # Modifiers
    modifiers = Column(JSON, nullable=True)
    # [{"name": "Extra cheese", "price": 1.50}]

    # Special instructions
    special_instructions = Column(Text, nullable=True)

    # Local mapping
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)

    # Relationships
    order = relationship("DeliveryOrder", back_populates="items")


class MenuSync(Base):
    """Track menu synchronization with delivery platforms."""
    __tablename__ = "menu_syncs"

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("delivery_integrations.id"), nullable=False)

    # Sync details
    sync_type = Column(String(50), nullable=False)  # full, incremental, availability
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Results
    success = Column(Boolean, default=False)
    items_synced = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    availability_changes = Column(Integer, default=0)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class ItemAvailability(Base):
    """Track item availability across delivery platforms (86'd items)."""
    __tablename__ = "item_availability"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Availability
    is_available = Column(Boolean, default=True)
    unavailable_reason = Column(String(200), nullable=True)  # out_of_stock, 86d, etc.
    unavailable_until = Column(DateTime, nullable=True)

    # Platform sync status
    platforms_synced = Column(JSON, nullable=True)
    # {"doordash": true, "uber_eats": true, "grubhub": false}
    last_sync_at = Column(DateTime, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeliveryPlatformMapping(Base):
    """Map local products to delivery platform product IDs."""
    __tablename__ = "delivery_platform_mappings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    integration_id = Column(Integer, ForeignKey("delivery_integrations.id"), nullable=False)

    # Platform-specific IDs
    platform_item_id = Column(String(200), nullable=False)
    platform_item_name = Column(String(300), nullable=True)

    # Price override for this platform
    platform_price = Column(Float, nullable=True)  # If different from base price

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
