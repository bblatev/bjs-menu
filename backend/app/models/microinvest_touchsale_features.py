"""
Microinvest Restaurant Plus & TouchSale (UnrealSoft) Feature Parity Models
============================================================================

Features implemented:
1. Customer Self-Ordering (MyMenu style) - QR code ordering from table
2. Customer Favorites & Order History
3. Preparation Time Tracking & Display
4. Staff Biometric Authentication
5. Hotel PMS Integration (FourSeasons style)
6. Video Surveillance Integration
7. Chef Mode Enhancements
8. Order Carry/Delivered Status
9. Manager SMS Alerts
10. Electronic Menu with Real-time Availability
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Date, Index, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.db.base import Base


# =============================================================================
# 1. CUSTOMER SELF-ORDERING (MyMenu Style)
# =============================================================================

class CustomerOrderingSession(Base):
    """Customer self-ordering session via QR code"""
    __tablename__ = "customer_ordering_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)

    # Session identifier
    session_token = Column(String(100), unique=True, nullable=False, index=True)
    qr_code_scanned = Column(Boolean, default=True)

    # Customer info (optional)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(20), nullable=True)

    # Session status
    status = Column(String(20), default="active")  # active, closed, expired

    # Language preference
    language = Column(String(5), default="en")  # en, bg, de, ru

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Device info
    device_type = Column(String(20), nullable=True)  # mobile, tablet
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Order tracking
    total_orders = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)

    venue = relationship("Venue", backref="customer_ordering_sessions")
    table = relationship("Table", backref="customer_ordering_sessions")

    __table_args__ = (
        Index('ix_customer_session_table', 'venue_id', 'table_id', 'status'),
        {'extend_existing': True},
    )


class CustomerOrderItem(Base):
    """Items added to cart by customer in self-ordering"""
    __tablename__ = "customer_order_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("customer_ordering_sessions.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)

    # Item details
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    # Modifiers
    modifiers = Column(JSON, nullable=True)  # [{modifier_id, name, price}]

    # Special requests/preferences
    special_requests = Column(Text, nullable=True)
    preparation_notes = Column(Text, nullable=True)

    # Status
    status = Column(String(20), default="in_cart")  # in_cart, ordered, preparing, ready, served

    # Estimated prep time (from menu item)
    estimated_prep_minutes = Column(Integer, nullable=True)

    added_at = Column(DateTime(timezone=True), server_default=func.now())
    ordered_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("CustomerOrderingSession", backref="cart_items")
    menu_item = relationship("MenuItem", backref="customer_cart_items")


class CustomerWaiterCall(Base):
    """Customer requests for waiter via self-ordering app"""
    __tablename__ = "customer_waiter_calls"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("customer_ordering_sessions.id"), nullable=False)

    # Call type
    call_type = Column(String(30), nullable=False)  # waiter, bill, help, water, complaint, other
    message = Column(Text, nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, acknowledged, resolved
    acknowledged_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("CustomerOrderingSession", backref="waiter_calls")


# =============================================================================
# 2. CUSTOMER FAVORITES & ORDER HISTORY
# =============================================================================

class CustomerFavorite(Base):
    """Customer favorite menu items"""
    __tablename__ = "customer_favorites"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)

    # Customizations saved
    saved_modifiers = Column(JSON, nullable=True)
    saved_notes = Column(Text, nullable=True)

    # Usage stats
    times_ordered = Column(Integer, default=0)
    last_ordered_at = Column(DateTime(timezone=True), nullable=True)

    added_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", backref="favorites")
    venue = relationship("Venue", backref="customer_favorites")
    menu_item = relationship("MenuItem", backref="favorited_by")

    __table_args__ = (
        UniqueConstraint('customer_id', 'venue_id', 'menu_item_id', name='uq_customer_favorite'),
        Index('ix_customer_favorites_customer', 'customer_id', 'venue_id'),
    )


class CustomerOrderHistory(Base):
    """Customer order history for reordering"""
    __tablename__ = "customer_order_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    # Order summary
    order_date = Column(DateTime(timezone=True), nullable=False)
    total_amount = Column(Float, nullable=False)
    item_count = Column(Integer, default=0)

    # Items snapshot for easy reordering
    items_snapshot = Column(JSON, nullable=False)  # [{menu_item_id, name, quantity, modifiers}]

    # Customer rating
    rating = Column(Integer, nullable=True)  # 1-5
    rating_comment = Column(Text, nullable=True)

    customer = relationship("Customer", backref="order_history")
    venue = relationship("Venue", backref="customer_order_histories")
    order = relationship("Order", backref="customer_history_entry")

    __table_args__ = (
        Index('ix_order_history_customer', 'customer_id', 'venue_id', 'order_date'),
    )


# =============================================================================
# 3. PREPARATION TIME TRACKING & DISPLAY
# =============================================================================

class MenuItemPrepTime(Base):
    """Preparation time configuration for menu items"""
    __tablename__ = "menu_item_prep_times"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, unique=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Standard times
    standard_prep_minutes = Column(Integer, nullable=False, default=15)
    minimum_prep_minutes = Column(Integer, nullable=True)
    maximum_prep_minutes = Column(Integer, nullable=True)

    # Rush hour adjustments
    rush_hour_multiplier = Column(Float, default=1.5)  # e.g., 1.5x during rush

    # Calculated averages
    actual_avg_prep_minutes = Column(Float, nullable=True)
    actual_min_prep_minutes = Column(Float, nullable=True)
    actual_max_prep_minutes = Column(Float, nullable=True)
    samples_count = Column(Integer, default=0)

    # Display settings
    show_to_customer = Column(Boolean, default=True)
    show_as_range = Column(Boolean, default=False)  # "10-15 min" vs "12 min"

    # Station that prepares this
    station_id = Column(Integer, ForeignKey("venue_stations.id"), nullable=True)

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    menu_item = relationship("MenuItem", backref="prep_time_config")
    venue = relationship("Venue", backref="menu_prep_times")


class OrderPrepTimeTracking(Base):
    """Track actual preparation times for orders"""
    __tablename__ = "order_prep_time_tracking"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Timestamps
    order_received_at = Column(DateTime(timezone=True), nullable=False)
    prep_started_at = Column(DateTime(timezone=True), nullable=True)
    prep_completed_at = Column(DateTime(timezone=True), nullable=True)
    served_at = Column(DateTime(timezone=True), nullable=True)

    # Calculated times
    wait_time_minutes = Column(Float, nullable=True)  # Time before prep started
    prep_time_minutes = Column(Float, nullable=True)  # Actual prep duration
    total_time_minutes = Column(Float, nullable=True)  # Order to served

    # Expected vs actual
    expected_prep_minutes = Column(Integer, nullable=True)
    variance_minutes = Column(Float, nullable=True)  # Actual - Expected

    # Context
    station_id = Column(Integer, ForeignKey("venue_stations.id"), nullable=True)
    prepared_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    is_rush_hour = Column(Boolean, default=False)
    concurrent_orders = Column(Integer, nullable=True)  # Orders being prepared simultaneously

    order = relationship("Order", backref="prep_tracking")
    menu_item = relationship("MenuItem", backref="prep_tracking")


class CustomerPrepTimeNotification(Base):
    """Notifications to customers about their order prep status"""
    __tablename__ = "customer_prep_time_notifications"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("customer_ordering_sessions.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    # Notification type
    notification_type = Column(String(30), nullable=False)  # order_received, preparing, almost_ready, ready, delayed

    # Content
    message = Column(JSON, nullable=False)  # {"en": "...", "bg": "..."}

    # Estimated times
    estimated_ready_at = Column(DateTime(timezone=True), nullable=True)
    estimated_wait_minutes = Column(Integer, nullable=True)

    # Delivery status
    delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("CustomerOrderingSession", backref="prep_notifications")
    order = relationship("Order", backref="prep_notifications")


# =============================================================================
# 4. STAFF BIOMETRIC AUTHENTICATION
# =============================================================================

class StaffBiometricMethod(str, enum.Enum):
    FINGERPRINT = "fingerprint"
    FACE_ID = "face_id"
    CARD = "card"
    PIN = "pin"
    NFC = "nfc"


class StaffBiometricCredential(Base):
    """Staff biometric authentication credentials"""
    __tablename__ = "staff_biometric_credentials"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Authentication method
    method = Column(String(20), nullable=False)  # fingerprint, face_id, card, pin, nfc

    # Credential data (encrypted)
    credential_hash = Column(String(500), nullable=False)
    credential_salt = Column(String(100), nullable=True)

    # For card/NFC
    card_number = Column(String(50), nullable=True)
    card_type = Column(String(30), nullable=True)  # rfid, nfc, magnetic

    # Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)

    # Security
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Device registration
    registered_device_id = Column(String(100), nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    registered_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=True)

    staff_user = relationship("StaffUser", foreign_keys=[staff_user_id], backref="biometric_credentials")
    venue = relationship("Venue", backref="staff_biometric_credentials")

    __table_args__ = (
        Index('ix_biometric_staff', 'staff_user_id', 'method', 'is_active'),
        Index('ix_biometric_card', 'venue_id', 'card_number'),
    )


class StaffBiometricLoginLog(Base):
    """Log of biometric authentication attempts"""
    __tablename__ = "staff_biometric_login_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)  # Null if failed

    # Attempt details
    method = Column(String(20), nullable=False)
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(100), nullable=True)

    # Device info
    device_id = Column(String(100), nullable=True)
    device_type = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Location
    terminal_id = Column(String(50), nullable=True)
    location = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="biometric_login_logs")
    staff_user = relationship("StaffUser", backref="biometric_login_logs")

    __table_args__ = (
        Index('ix_biometric_log_date', 'venue_id', 'created_at'),
        Index('ix_biometric_log_staff', 'staff_user_id', 'created_at'),
    )


# =============================================================================
# 5. HOTEL PMS INTEGRATION (FourSeasons Style)
# =============================================================================

class HotelPMSConnection(Base):
    """Hotel Property Management System integration"""
    __tablename__ = "hotel_pms_connections"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, unique=True)

    # PMS details
    pms_name = Column(String(100), nullable=False)  # fourseasons, opera, protel, mews, cloudbeds
    pms_version = Column(String(20), nullable=True)

    # Connection settings
    api_endpoint = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=True)
    api_secret = Column(String(500), nullable=True)

    # Authentication
    auth_type = Column(String(20), default="api_key")  # api_key, oauth, basic
    oauth_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Hotel info
    hotel_id = Column(String(50), nullable=True)
    hotel_name = Column(String(200), nullable=True)

    # Features enabled
    room_charge_enabled = Column(Boolean, default=True)
    guest_lookup_enabled = Column(Boolean, default=True)
    breakfast_sync_enabled = Column(Boolean, default=False)
    minibar_sync_enabled = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="hotel_pms_connection")


# HotelGuest is defined in hardware.py - DO NOT define here


class HotelRoomCharge(Base):
    """Charges posted to hotel rooms"""
    __tablename__ = "hotel_room_charges"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    hotel_guest_id = Column(Integer, ForeignKey("hotel_guests.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    # Room info
    room_number = Column(String(20), nullable=False)

    # Charge details
    charge_type = Column(String(30), nullable=False)  # restaurant, bar, room_service, minibar
    description = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)

    # Guest signature
    signature_captured = Column(Boolean, default=False)
    signature_data = Column(Text, nullable=True)

    # PMS posting
    pms_posting_status = Column(String(20), default="pending")  # pending, posted, failed
    pms_posting_id = Column(String(100), nullable=True)
    pms_posted_at = Column(DateTime(timezone=True), nullable=True)
    pms_error = Column(Text, nullable=True)

    # Staff
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="hotel_room_charges")
    hotel_guest = relationship("HotelGuest", backref="room_charges")
    order = relationship("Order", backref="hotel_room_charges")

    __table_args__ = (
        Index('ix_room_charge_guest', 'hotel_guest_id', 'created_at'),
        Index('ix_room_charge_status', 'venue_id', 'pms_posting_status'),
    )


# =============================================================================
# 6. VIDEO SURVEILLANCE INTEGRATION
# =============================================================================

class VideoSurveillanceConfig(Base):
    """Video surveillance system configuration"""
    __tablename__ = "video_surveillance_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, unique=True)

    # System type
    system_type = Column(String(50), nullable=False)  # hikvision, dahua, axis, generic_rtsp

    # Server connection
    server_url = Column(String(500), nullable=False)
    server_port = Column(Integer, default=8000)
    username = Column(String(100), nullable=True)
    password = Column(String(200), nullable=True)  # Encrypted

    # AI features
    ai_enabled = Column(Boolean, default=False)
    theft_detection_enabled = Column(Boolean, default=False)
    crowd_detection_enabled = Column(Boolean, default=False)
    staff_tracking_enabled = Column(Boolean, default=False)

    # Recording settings
    record_pos_events = Column(Boolean, default=True)
    event_pre_roll_seconds = Column(Integer, default=10)
    event_post_roll_seconds = Column(Integer, default=30)

    # Status
    is_active = Column(Boolean, default=True)
    last_connection_at = Column(DateTime(timezone=True), nullable=True)
    connection_status = Column(String(20), default="disconnected")  # connected, disconnected, error

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="video_surveillance_config")


class VideoCamera(Base):
    """Individual camera configuration"""
    __tablename__ = "video_cameras"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    config_id = Column(Integer, ForeignKey("video_surveillance_configs.id"), nullable=False)

    # Camera info
    camera_id = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(200), nullable=True)

    # Stream settings
    stream_url = Column(String(500), nullable=True)
    snapshot_url = Column(String(500), nullable=True)

    # Location
    location = Column(String(100), nullable=True)  # entrance, bar, kitchen, dining_area
    covers_pos_terminal = Column(Integer, nullable=True)  # Terminal ID if covering a POS
    covers_table_ids = Column(JSON, nullable=True)  # [table_id] if covering tables

    # POS event linking
    link_to_pos_events = Column(Boolean, default=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=True)
    last_snapshot = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="video_cameras")
    config = relationship("VideoSurveillanceConfig", backref="cameras")

    __table_args__ = (
        UniqueConstraint('venue_id', 'camera_id', name='uq_camera_id'),
    )


class VideoEventClip(Base):
    """Video clips linked to POS events"""
    __tablename__ = "video_event_clips"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    camera_id = Column(Integer, ForeignKey("video_cameras.id"), nullable=False)

    # Event reference
    event_type = Column(String(50), nullable=False)  # order, payment, void, discount, cash_drawer, suspicious
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    transaction_id = Column(Integer, nullable=True)

    # Clip info
    clip_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)

    # Timing
    event_time = Column(DateTime(timezone=True), nullable=False)
    clip_start = Column(DateTime(timezone=True), nullable=False)
    clip_end = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer, nullable=False)

    # AI analysis (if enabled)
    ai_analyzed = Column(Boolean, default=False)
    ai_flags = Column(JSON, nullable=True)  # [{type: "suspicious_behavior", confidence: 0.85}]
    ai_summary = Column(Text, nullable=True)

    # Status
    clip_status = Column(String(20), default="pending")  # pending, ready, failed, expired

    # Review
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="video_event_clips")
    camera = relationship("VideoCamera", backref="event_clips")
    order = relationship("Order", backref="video_clips")

    __table_args__ = (
        Index('ix_video_clip_event', 'venue_id', 'event_type', 'event_time'),
        Index('ix_video_clip_order', 'order_id'),
    )


# =============================================================================
# 7. CHEF MODE ENHANCEMENTS
# =============================================================================

class ChefModeConfig(Base):
    """Chef mode/kitchen display configuration"""
    __tablename__ = "chef_mode_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("venue_stations.id"), nullable=True)

    # Display settings
    display_name = Column(String(100), nullable=False)
    display_type = Column(String(30), default="grid")  # grid, list, timeline

    # Group filtering
    show_categories = Column(JSON, nullable=True)  # [category_id] or null for all
    show_groups = Column(JSON, nullable=True)  # Category groups to show
    group_sort_by = Column(String(20), default="code")  # code, name, priority

    # Item sizing
    item_size = Column(String(20), default="medium")  # small, medium, large, dynamic
    dynamic_sizing_enabled = Column(Boolean, default=True)

    # Quantity adjustment
    allow_quantity_change = Column(Boolean, default=True)
    allow_partial_complete = Column(Boolean, default=True)

    # Timing
    show_elapsed_time = Column(Boolean, default=True)
    warning_minutes = Column(Integer, default=10)
    critical_minutes = Column(Integer, default=15)

    # Sound alerts
    new_order_sound = Column(Boolean, default=True)
    warning_sound = Column(Boolean, default=True)

    # Colors
    color_scheme = Column(String(20), default="standard")  # standard, high_contrast, dark

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="chef_mode_configs")
    station = relationship("VenueStation", backref="chef_mode_config")

    __table_args__ = (
        UniqueConstraint('venue_id', 'station_id', name='uq_chef_mode_station'),
    )


class ChefQuantityAdjustment(Base):
    """Log of chef quantity adjustments"""
    __tablename__ = "chef_quantity_adjustments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)

    # Adjustment
    original_quantity = Column(Integer, nullable=False)
    adjusted_quantity = Column(Integer, nullable=False)
    adjustment_type = Column(String(20), nullable=False)  # increase, decrease, split

    # Reason
    reason = Column(String(50), nullable=True)  # partial_ready, portion_issue, mistake, customer_change
    notes = Column(Text, nullable=True)

    # Staff
    adjusted_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    adjusted_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="chef_quantity_adjustments")

    __table_args__ = (
        Index('ix_chef_adjust_date', 'venue_id', 'adjusted_at'),
    )


# =============================================================================
# 8. ORDER CARRY/DELIVERED STATUS
# =============================================================================

class OrderDeliveryStatus(str, enum.Enum):
    NEW = "new"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"
    CARRIED = "carried"  # TouchSale/MyWaiter specific - item picked up by waiter
    DELIVERED = "delivered"  # Microinvest specific - item delivered to table
    SERVED = "served"
    CANCELLED = "cancelled"


class OrderItemDeliveryTracking(Base):
    """Track delivery status of individual order items"""
    __tablename__ = "order_item_delivery_tracking"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Status progression
    status = Column(String(20), default="new")

    # Timestamps
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    prep_started_at = Column(DateTime(timezone=True), nullable=True)
    ready_at = Column(DateTime(timezone=True), nullable=True)
    carried_at = Column(DateTime(timezone=True), nullable=True)  # Picked up by waiter
    delivered_at = Column(DateTime(timezone=True), nullable=True)  # Delivered to table
    served_at = Column(DateTime(timezone=True), nullable=True)

    # Staff tracking
    prepared_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    carried_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    delivered_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Table info
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)

    # Notes
    delivery_notes = Column(Text, nullable=True)

    order = relationship("Order", backref="item_delivery_tracking")
    venue = relationship("Venue", backref="order_item_delivery_tracking")

    __table_args__ = (
        Index('ix_delivery_tracking_status', 'venue_id', 'status'),
        Index('ix_delivery_tracking_order', 'order_id'),
    )


# =============================================================================
# 9. MANAGER SMS ALERTS
# =============================================================================

class ManagerSMSAlertConfig(Base):
    """SMS alert configuration for managers"""
    __tablename__ = "manager_sms_alert_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)

    # Contact
    phone_number = Column(String(20), nullable=False)

    # Alert types enabled
    alert_on_voids = Column(Boolean, default=True)
    alert_on_refunds = Column(Boolean, default=True)
    alert_on_discounts = Column(Boolean, default=True)
    discount_threshold = Column(Float, default=20.0)  # Percent
    alert_on_corrections = Column(Boolean, default=True)
    alert_on_cash_drawer = Column(Boolean, default=True)
    alert_on_low_stock = Column(Boolean, default=False)
    alert_on_customer_complaints = Column(Boolean, default=True)
    alert_on_eod_reports = Column(Boolean, default=True)

    # Thresholds
    min_void_amount = Column(Float, default=0.0)  # Only alert if void above this
    min_refund_amount = Column(Float, default=0.0)

    # Quiet hours
    quiet_hours_start = Column(String(5), nullable=True)  # HH:MM
    quiet_hours_end = Column(String(5), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="manager_sms_alert_configs")
    staff_user = relationship("StaffUser", backref="sms_alert_config")

    __table_args__ = (
        UniqueConstraint('venue_id', 'staff_user_id', name='uq_manager_sms_config'),
    )


class ManagerSMSAlertLog(Base):
    """Log of SMS alerts sent to managers"""
    __tablename__ = "manager_sms_alert_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    config_id = Column(Integer, ForeignKey("manager_sms_alert_configs.id"), nullable=False)

    # Alert details
    alert_type = Column(String(30), nullable=False)
    message = Column(Text, nullable=False)

    # Reference
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)  # Who triggered event

    # Delivery
    phone_number = Column(String(20), nullable=False)
    sms_provider_id = Column(String(100), nullable=True)
    delivery_status = Column(String(20), default="pending")  # pending, sent, delivered, failed
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="manager_sms_alert_logs")
    config = relationship("ManagerSMSAlertConfig", backref="alert_logs")

    __table_args__ = (
        Index('ix_sms_alert_log_date', 'venue_id', 'created_at'),
    )


# =============================================================================
# 10. ELECTRONIC MENU WITH REAL-TIME AVAILABILITY
# =============================================================================

class ElectronicMenuConfig(Base):
    """Electronic menu display configuration"""
    __tablename__ = "electronic_menu_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, unique=True)

    # Menu appearance
    theme = Column(String(30), default="light")  # light, dark, custom
    primary_color = Column(String(10), default="#007bff")
    accent_color = Column(String(10), default="#28a745")
    background_image_url = Column(String(500), nullable=True)
    logo_url = Column(String(500), nullable=True)

    # Display options
    show_prices = Column(Boolean, default=True)
    show_descriptions = Column(Boolean, default=True)
    show_photos = Column(Boolean, default=True)
    show_allergens = Column(Boolean, default=True)
    show_nutritional = Column(Boolean, default=False)
    show_prep_time = Column(Boolean, default=True)
    show_availability = Column(Boolean, default=True)  # Real-time stock availability
    show_popular_badge = Column(Boolean, default=True)

    # Ordering
    allow_ordering = Column(Boolean, default=True)
    require_table_qr = Column(Boolean, default=True)
    allow_customizations = Column(Boolean, default=True)

    # Languages
    supported_languages = Column(JSON, default=["en", "bg"])
    default_language = Column(String(5), default="en")

    # Auto-refresh
    auto_refresh_enabled = Column(Boolean, default=True)
    refresh_interval_seconds = Column(Integer, default=60)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="electronic_menu_config")


class MenuItemAvailability(Base):
    """Real-time availability of menu items"""
    __tablename__ = "menu_item_availability"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, unique=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Availability status
    is_available = Column(Boolean, default=True)
    availability_type = Column(String(20), default="available")  # available, low_stock, sold_out, temporarily_unavailable

    # Stock-based (calculated from inventory)
    portions_available = Column(Integer, nullable=True)
    low_stock_threshold = Column(Integer, default=5)

    # Manual override
    manual_override = Column(Boolean, default=False)
    override_reason = Column(String(100), nullable=True)
    override_until = Column(DateTime(timezone=True), nullable=True)
    override_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Customer display message
    unavailable_message = Column(JSON, nullable=True)  # {"en": "...", "bg": "..."}

    # Last update
    last_stock_check = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    menu_item = relationship("MenuItem", backref="availability_status")
    venue = relationship("Venue", backref="menu_item_availabilities")

    __table_args__ = (
        Index('ix_menu_availability', 'venue_id', 'is_available'),
    )
