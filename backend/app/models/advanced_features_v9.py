"""
BJ's Bar V9 - Advanced Features Models
Comprehensive implementation of missing enterprise features

Features covered:
- Advanced POS Operations (Q)
- Advanced Kitchen & Production (R)
- Advanced Inventory & Supply Chain (S)
- Financial Controls & Reporting (T)
- Advanced Loyalty & CRM (U)
- Online, QR & Self-service (V)
- Hardware & IoT Extensions (W)
- Compliance & Audit (X)
- AI & Automation (Y)
- Platform & Architecture (Z)
- Legal, Insurance & Risk (AA-AK)
- ESG & Sustainability Extensions (AM)
- Smart Building & Environment (AN)
- Training & Certification (AP)
- Crisis & Resilience (AR)
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Enum, UniqueConstraint, Index, LargeBinary, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.db.base import Base


# =============================================================================
# SECTION Q: ADVANCED OPERATIONS & ENTERPRISE CONTROLS
# =============================================================================

class PermissionOverrideType(str, enum.Enum):
    GRANT = "grant"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class LocationPermissionOverride(Base):
    """Per-location permission overrides beyond base role"""
    __tablename__ = "location_permission_overrides"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    
    permission_key = Column(String(100), nullable=False)  # e.g., "void_order", "apply_discount", "access_reports"
    override_type = Column(String(20), nullable=False)  # PermissionOverrideType
    
    # Time restrictions
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Approval requirements
    requires_manager_approval = Column(Boolean, default=False)
    max_value_limit = Column(Float, nullable=True)  # e.g., max discount amount
    
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="permission_overrides")
    
    __table_args__ = (
        UniqueConstraint('venue_id', 'staff_user_id', 'permission_key', name='uq_location_permission'),
        Index('ix_permission_overrides_user', 'staff_user_id'),
    )


class TerminalHealthStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class TerminalHealth(Base):
    """POS terminal health monitoring"""
    __tablename__ = "terminal_health"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    terminal_id = Column(String(50), nullable=False, index=True)
    terminal_name = Column(String(100), nullable=True)
    
    # Status
    status = Column(String(20), default="online")  # TerminalHealthStatus
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    is_locked = Column(Boolean, default=False)
    lock_reason = Column(String(200), nullable=True)
    
    # Hardware info
    os_version = Column(String(50), nullable=True)
    app_version = Column(String(20), nullable=True)
    ip_address = Column(String(45), nullable=True)
    mac_address = Column(String(17), nullable=True)
    
    # Performance metrics
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)
    disk_usage_percent = Column(Float, nullable=True)
    network_latency_ms = Column(Integer, nullable=True)
    
    # Printer status
    receipt_printer_status = Column(String(20), nullable=True)
    kitchen_printer_status = Column(String(20), nullable=True)
    fiscal_device_status = Column(String(20), nullable=True)
    
    # Cash drawer
    cash_drawer_open = Column(Boolean, default=False)
    last_cash_count = Column(DateTime(timezone=True), nullable=True)
    
    # Session info
    current_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    session_started_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    
    # Geo-fencing
    allowed_ip_range = Column(String(100), nullable=True)
    geo_fence_enabled = Column(Boolean, default=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geo_fence_radius_meters = Column(Integer, default=100)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="terminal_health")
    
    __table_args__ = (
        UniqueConstraint('venue_id', 'terminal_id', name='uq_terminal_health_venue_terminal'),
    )


class SafeModeType(str, enum.Enum):
    NORMAL = "normal"
    SAFE = "safe"
    EMERGENCY = "emergency"
    OFFLINE = "offline"
    LOCKED = "locked"


class EmergencyModeConfig(Base):
    """Emergency/safe mode configuration for POS"""
    __tablename__ = "emergency_mode_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, unique=True)
    
    # Current mode
    current_mode = Column(String(20), default="normal")  # SafeModeType
    mode_activated_at = Column(DateTime(timezone=True), nullable=True)
    mode_activated_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    mode_reason = Column(Text, nullable=True)
    
    # Safe mode settings
    safe_mode_allowed_operations = Column(JSON, default=list)  # List of allowed ops
    safe_mode_max_transaction = Column(Float, nullable=True)
    safe_mode_require_manager = Column(Boolean, default=True)
    
    # Emergency mode settings
    emergency_disable_discounts = Column(Boolean, default=True)
    emergency_cash_only = Column(Boolean, default=False)
    emergency_menu_subset = Column(JSON, nullable=True)  # Limited menu item IDs
    
    # Auto-recovery
    auto_recover_after_minutes = Column(Integer, nullable=True)
    recovery_notification_emails = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="emergency_mode_config")


class CashVarianceConfig(Base):
    """Cash variance tolerance and alert configuration"""
    __tablename__ = "cash_variance_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, unique=True)
    
    # Tolerance thresholds
    warning_threshold_amount = Column(Float, default=5.0)  # Amount in BGN/EUR
    warning_threshold_percent = Column(Float, default=1.0)  # Percentage
    critical_threshold_amount = Column(Float, default=20.0)
    critical_threshold_percent = Column(Float, default=5.0)
    
    # Actions on variance
    require_explanation_on_warning = Column(Boolean, default=True)
    require_manager_approval_on_critical = Column(Boolean, default=True)
    auto_flag_suspicious = Column(Boolean, default=True)
    
    # Cash count requirements
    force_count_on_shift_close = Column(Boolean, default=True)
    force_count_on_shift_start = Column(Boolean, default=False)
    blind_cash_count = Column(Boolean, default=True)  # Hide expected amount
    
    # Dual control
    require_dual_control_over = Column(Float, nullable=True)  # Amount requiring 2-person
    
    # Alert settings
    alert_manager_on_critical = Column(Boolean, default=True)
    alert_email_addresses = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="cash_variance_config")


class CashVarianceRecord(Base):
    """Record of cash variance events"""
    __tablename__ = "cash_variance_records"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("staff_shifts.id"), nullable=False)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    
    # Amounts
    expected_amount = Column(Float, nullable=False)
    counted_amount = Column(Float, nullable=False)
    variance_amount = Column(Float, nullable=False)
    variance_percent = Column(Float, nullable=False)
    
    # Status
    severity = Column(String(20), nullable=False)  # ok, warning, critical
    explanation = Column(Text, nullable=True)
    manager_approved = Column(Boolean, default=False)
    manager_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    manager_notes = Column(Text, nullable=True)
    
    # Investigation
    is_flagged = Column(Boolean, default=False)
    investigation_status = Column(String(20), nullable=True)
    investigation_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="cash_variance_records")
    shift = relationship("StaffShift", backref="cash_variance_records")
    
    __table_args__ = (
        Index('ix_cash_variance_venue_date', 'venue_id', 'created_at'),
    )


class SessionTimeoutConfig(Base):
    """Session timeout and auto-logout configuration"""
    __tablename__ = "session_timeout_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, unique=True)
    
    # Timeout settings
    inactivity_timeout_seconds = Column(Integer, default=300)  # 5 minutes
    absolute_timeout_hours = Column(Integer, default=12)  # Max session length
    
    # Lock vs logout
    lock_instead_of_logout = Column(Boolean, default=True)
    require_pin_to_unlock = Column(Boolean, default=True)
    require_full_login_after_lock = Column(Integer, default=30)  # Minutes
    
    # Per-role overrides
    role_timeouts = Column(JSON, nullable=True)  # {"admin": 3600, "waiter": 300}
    
    # Grace period
    warning_before_timeout_seconds = Column(Integer, default=60)
    
    # Activity tracking
    track_mouse_movement = Column(Boolean, default=False)
    track_keyboard_activity = Column(Boolean, default=True)
    track_touch_activity = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="session_timeout_config")


# =============================================================================
# SECTION R: ADVANCED KITCHEN & PRODUCTION
# =============================================================================

class ProductionForecast(Base):
    """Production forecasting based on sales history"""
    __tablename__ = "production_forecasts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    forecast_date = Column(DateTime(timezone=True), nullable=False)
    forecast_type = Column(String(20), nullable=False)  # daily, weekly, event
    
    # Forecast data
    item_forecasts = Column(JSON, nullable=False)  # {item_id: {quantity: X, confidence: Y}}
    ingredient_requirements = Column(JSON, nullable=True)  # {ingredient_id: quantity}
    
    # Basis
    historical_days_analyzed = Column(Integer, default=30)
    seasonality_factor = Column(Float, default=1.0)
    event_factor = Column(Float, default=1.0)  # Special events adjustment
    weather_factor = Column(Float, default=1.0)
    
    # Accuracy tracking
    actual_demand = Column(JSON, nullable=True)  # Filled after the fact
    accuracy_score = Column(Float, nullable=True)
    
    # Status
    is_approved = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="production_forecasts")
    
    __table_args__ = (
        UniqueConstraint('venue_id', 'forecast_date', 'forecast_type', name='uq_production_forecast'),
        Index('ix_production_forecast_date', 'venue_id', 'forecast_date'),
    )


class StationLoadStatus(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    OVERLOADED = "overloaded"
    BLOCKED = "blocked"


class StationLoad(Base):
    """Real-time station load balancing metrics"""
    __tablename__ = "station_loads"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("venue_stations.id"), nullable=False)
    
    # Current metrics (updated frequently)
    current_orders = Column(Integer, default=0)
    current_items = Column(Integer, default=0)
    estimated_queue_time_minutes = Column(Integer, default=0)
    
    # Load status
    load_status = Column(String(20), default="normal")  # StationLoadStatus
    load_percentage = Column(Float, default=0.0)  # 0-100+
    
    # Capacity config
    max_concurrent_orders = Column(Integer, default=10)
    max_concurrent_items = Column(Integer, default=30)
    optimal_queue_time_minutes = Column(Integer, default=15)
    
    # Performance
    avg_item_time_seconds = Column(Integer, default=300)  # Rolling average
    items_completed_last_hour = Column(Integer, default=0)
    
    # Smart routing
    accept_overflow = Column(Boolean, default=True)
    overflow_from_stations = Column(JSON, default=list)  # Station IDs that can overflow here
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="station_loads")
    station = relationship("VenueStation", backref="station_load")
    
    __table_args__ = (
        UniqueConstraint('venue_id', 'station_id', name='uq_station_load'),
    )


class AutoFireRule(Base):
    """Automatic course firing rules"""
    __tablename__ = "auto_fire_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Trigger type
    trigger_type = Column(String(30), nullable=False)  # time_based, previous_course_ready, manual
    
    # Time-based settings
    fire_after_minutes = Column(Integer, nullable=True)  # Minutes after previous course
    fire_at_time = Column(String(5), nullable=True)  # Specific time like "19:30"
    
    # Course settings
    applicable_courses = Column(JSON, default=list)  # Course numbers this applies to
    
    # Conditions
    hold_until_all_ready = Column(Boolean, default=False)
    require_expo_approval = Column(Boolean, default=False)
    
    # Schedule
    is_active = Column(Boolean, default=True)
    active_days = Column(JSON, nullable=True)
    active_start_time = Column(String(5), nullable=True)
    active_end_time = Column(String(5), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="auto_fire_rules")


class KitchenPerformanceMetric(Base):
    """Kitchen performance KPIs"""
    __tablename__ = "kitchen_performance_metrics"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("venue_stations.id"), nullable=True)
    
    metric_date = Column(DateTime(timezone=True), nullable=False)
    metric_hour = Column(Integer, nullable=True)  # 0-23, null for daily
    
    # Ticket metrics
    tickets_received = Column(Integer, default=0)
    tickets_completed = Column(Integer, default=0)
    tickets_voided = Column(Integer, default=0)
    
    # Time metrics (seconds)
    avg_ticket_time = Column(Integer, nullable=True)
    min_ticket_time = Column(Integer, nullable=True)
    max_ticket_time = Column(Integer, nullable=True)
    p95_ticket_time = Column(Integer, nullable=True)  # 95th percentile
    
    # Quality metrics
    items_remade = Column(Integer, default=0)
    complaints_received = Column(Integer, default=0)
    
    # Rush detection
    was_rush_hour = Column(Boolean, default=False)
    peak_concurrent_tickets = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="kitchen_performance")
    
    __table_args__ = (
        Index('ix_kitchen_perf_venue_date', 'venue_id', 'metric_date'),
    )


# =============================================================================
# SECTION S: ADVANCED INVENTORY & SUPPLY CHAIN
# =============================================================================

class AutoPurchaseOrderConfig(Base):
    """Configuration for automatic purchase order generation"""
    __tablename__ = "auto_purchase_order_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, unique=True)
    
    # Enable/disable
    is_enabled = Column(Boolean, default=False)
    
    # Trigger settings
    trigger_on_min_stock = Column(Boolean, default=True)
    trigger_on_forecast = Column(Boolean, default=False)
    
    # Order settings
    order_to_max_stock = Column(Boolean, default=True)  # Order up to max level
    order_quantity_days = Column(Integer, default=7)  # Days of stock to order
    round_to_pack_size = Column(Boolean, default=True)
    
    # Approval workflow
    require_approval = Column(Boolean, default=True)
    auto_send_threshold = Column(Float, nullable=True)  # Auto-send if below this amount
    approval_email = Column(String(255), nullable=True)
    
    # Supplier selection
    prefer_primary_supplier = Column(Boolean, default=True)
    use_best_price = Column(Boolean, default=False)
    consolidate_suppliers = Column(Boolean, default=True)  # Group items by supplier
    
    # Schedule
    check_frequency_hours = Column(Integer, default=24)
    preferred_order_day = Column(String(10), nullable=True)  # monday, tuesday, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="auto_purchase_config")


class SupplierLeadTime(Base):
    """Supplier lead time tracking"""
    __tablename__ = "supplier_lead_times"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)  # Null = supplier default
    
    # Lead time settings
    standard_lead_time_days = Column(Integer, nullable=False)
    express_lead_time_days = Column(Integer, nullable=True)
    express_surcharge_percent = Column(Float, nullable=True)
    
    # Reliability metrics
    avg_actual_lead_time_days = Column(Float, nullable=True)
    on_time_delivery_percent = Column(Float, nullable=True)
    
    # Minimum order
    minimum_order_amount = Column(Float, nullable=True)
    minimum_order_quantity = Column(Float, nullable=True)
    
    # Delivery schedule
    delivery_days = Column(JSON, nullable=True)  # ["monday", "wednesday", "friday"]
    cut_off_time = Column(String(5), nullable=True)  # Order cut-off time
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    supplier = relationship("Supplier", backref="lead_times")
    
    __table_args__ = (
        UniqueConstraint('supplier_id', 'stock_item_id', name='uq_supplier_item_lead'),
    )


class AlternativeSupplier(Base):
    """Alternative suppliers for ingredients"""
    __tablename__ = "alternative_suppliers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    
    # Priority
    priority = Column(Integer, default=1)  # 1 = primary, 2 = first alternative, etc.
    
    # Pricing
    unit_price = Column(Float, nullable=True)
    last_price_date = Column(DateTime(timezone=True), nullable=True)
    
    # Supplier item details
    supplier_sku = Column(String(50), nullable=True)
    supplier_product_name = Column(String(200), nullable=True)
    pack_size = Column(Float, nullable=True)
    pack_unit = Column(String(20), nullable=True)
    
    # Quality
    quality_rating = Column(Float, nullable=True)  # 1-5
    notes = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    stock_item = relationship("StockItem", backref="alternative_suppliers")
    supplier = relationship("Supplier", backref="supplied_items")
    
    __table_args__ = (
        UniqueConstraint('stock_item_id', 'supplier_id', name='uq_item_supplier'),
        Index('ix_alt_supplier_item', 'stock_item_id', 'priority'),
    )


class CostingMethod(str, enum.Enum):
    FIFO = "fifo"
    LIFO = "lifo"
    WEIGHTED_AVERAGE = "weighted_average"
    SPECIFIC_ID = "specific_id"


class InventoryCostingConfig(Base):
    """Inventory costing method configuration"""
    __tablename__ = "inventory_costing_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, unique=True)
    
    # Default method
    default_costing_method = Column(String(20), default="weighted_average")  # CostingMethod
    
    # Per-category overrides
    category_methods = Column(JSON, nullable=True)  # {category_id: "fifo"}
    
    # Cost recalculation
    auto_recalculate_on_receipt = Column(Boolean, default=True)
    
    # Variance tracking
    track_cost_variance = Column(Boolean, default=True)
    variance_alert_threshold_percent = Column(Float, default=10.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="costing_config")


class CrossStoreStockSuggestion(Base):
    """Cross-store stock balancing suggestions"""
    __tablename__ = "cross_store_stock_suggestions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    
    # Stores involved
    from_venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    to_venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
    
    # Suggestion details
    suggested_quantity = Column(Float, nullable=False)
    reason = Column(String(50), nullable=False)  # surplus, shortage, expiry_risk
    
    # Stock levels
    from_store_quantity = Column(Float, nullable=False)
    to_store_quantity = Column(Float, nullable=False)
    from_store_days_of_stock = Column(Float, nullable=True)
    to_store_days_of_stock = Column(Float, nullable=True)
    
    # Cost savings
    estimated_savings = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), default="pending")  # pending, approved, rejected, completed
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    transfer_id = Column(Integer, nullable=True)  # If transfer was created
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    from_venue = relationship("Venue", foreign_keys=[from_venue_id], backref="outbound_suggestions")
    to_venue = relationship("Venue", foreign_keys=[to_venue_id], backref="inbound_suggestions")
    stock_item = relationship("StockItem", backref="stock_suggestions")


# =============================================================================
# SECTION T: FINANCIAL CONTROLS & ADVANCED REPORTING
# =============================================================================

class PrimeCostTracking(Base):
    """Track prime cost (food + labor)"""
    __tablename__ = "prime_cost_tracking"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    tracking_date = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Revenue
    total_revenue = Column(Float, nullable=False)
    food_revenue = Column(Float, nullable=True)
    beverage_revenue = Column(Float, nullable=True)
    
    # Food cost
    food_cost = Column(Float, nullable=False)
    food_cost_percent = Column(Float, nullable=False)
    food_cost_target_percent = Column(Float, nullable=True)
    food_cost_variance = Column(Float, nullable=True)
    
    # Labor cost
    labor_cost = Column(Float, nullable=False)
    labor_cost_percent = Column(Float, nullable=False)
    labor_cost_target_percent = Column(Float, nullable=True)
    labor_cost_variance = Column(Float, nullable=True)
    
    # Prime cost (combined)
    prime_cost = Column(Float, nullable=False)
    prime_cost_percent = Column(Float, nullable=False)
    prime_cost_target_percent = Column(Float, nullable=True)
    prime_cost_variance = Column(Float, nullable=True)
    
    # Breakdown
    hourly_labor_cost = Column(Float, nullable=True)
    salaried_labor_cost = Column(Float, nullable=True)
    overtime_cost = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="prime_cost_tracking")
    
    __table_args__ = (
        UniqueConstraint('venue_id', 'tracking_date', 'period_type', name='uq_prime_cost_period'),
        Index('ix_prime_cost_venue_date', 'venue_id', 'tracking_date'),
    )


class AbuseDetectionConfig(Base):
    """Configuration for refund/discount abuse detection"""
    __tablename__ = "abuse_detection_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, unique=True)

    # General toggle
    enabled = Column(Boolean, default=True)

    # Refund abuse detection
    refund_detection_enabled = Column(Boolean, default=True)
    refund_threshold_count = Column(Integer, default=5)  # Per period
    refund_threshold_period_hours = Column(Integer, default=24)
    refund_threshold_amount = Column(Numeric(10, 2), default=100.0)  # Max amount
    refund_same_customer_flag = Column(Boolean, default=True)

    # Discount abuse detection
    discount_detection_enabled = Column(Boolean, default=True)
    discount_threshold_count = Column(Integer, default=10)  # Per shift
    discount_threshold_period_hours = Column(Integer, default=8)
    discount_threshold_percent = Column(Float, default=10.0)  # Of employee's sales
    discount_threshold_percentage = Column(Numeric(5, 2), default=50.0)  # Max percentage
    discount_to_associates_flag = Column(Boolean, default=True)  # Discounts to known associates

    # Void abuse detection
    void_detection_enabled = Column(Boolean, default=True)
    void_threshold_count = Column(Integer, default=8)  # Per shift
    void_threshold_period_hours = Column(Integer, default=8)
    void_after_payment_flag = Column(Boolean, default=True)

    # Suspicious hours
    suspicious_time_start = Column(String(10), default="22:00")
    suspicious_time_end = Column(String(10), default="06:00")

    # Alert settings
    alert_manager_immediately = Column(Boolean, default=True)
    alert_manager = Column(Boolean, default=True)
    alert_email = Column(String(200), nullable=True)
    create_investigation_case = Column(Boolean, default=False)
    auto_lock_on_critical = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="abuse_detection_config")


class AbuseAlert(Base):
    """Detected abuse alerts"""
    __tablename__ = "abuse_alerts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    
    alert_type = Column(String(30), nullable=False)  # refund, discount, void, cash_variance
    severity = Column(String(20), nullable=False)  # warning, critical
    
    # Details
    description = Column(Text, nullable=False)
    metric_value = Column(Float, nullable=True)  # The value that triggered
    threshold_value = Column(Float, nullable=True)  # The threshold that was exceeded
    related_transactions = Column(JSON, nullable=True)  # Order/transaction IDs
    
    # Status
    status = Column(String(20), default="open")  # open, investigating, resolved, dismissed
    assigned_to = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    
    # Resolution
    resolution_type = Column(String(30), nullable=True)  # confirmed_abuse, false_positive, training_needed
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="abuse_alerts")
    staff_user = relationship("StaffUser", foreign_keys=[staff_user_id], backref="abuse_alerts")
    
    __table_args__ = (
        Index('ix_abuse_alerts_venue_status', 'venue_id', 'status'),
    )


# =============================================================================
# SECTION U: ADVANCED LOYALTY & CRM
# =============================================================================

class GuestPreference(Base):
    """Guest preferences and history for personalization"""
    __tablename__ = "guest_preferences"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, unique=True)
    
    # Table preferences
    preferred_table_ids = Column(JSON, default=list)
    preferred_areas = Column(JSON, default=list)  # "terrace", "window", "quiet"
    seating_notes = Column(Text, nullable=True)
    
    # Dietary
    dietary_restrictions = Column(JSON, default=list)  # ["vegetarian", "gluten-free"]
    allergies = Column(JSON, default=list)
    dietary_notes = Column(Text, nullable=True)
    
    # Service preferences
    preferred_waiter_ids = Column(JSON, default=list)
    communication_preference = Column(String(20), nullable=True)  # phone, email, sms
    language_preference = Column(String(5), nullable=True)
    
    # Occasion preferences
    celebration_dates = Column(JSON, nullable=True)  # [{"type": "birthday", "date": "03-15"}]
    
    # Beverage preferences
    favorite_drinks = Column(JSON, default=list)
    wine_preferences = Column(JSON, nullable=True)  # {"style": "red", "region": "bulgaria"}
    
    # Special handling
    is_vip = Column(Boolean, default=False)
    vip_status = Column(String(30), nullable=True)  # Alias for service compatibility
    vip_notes = Column(Text, nullable=True)
    requires_accessibility = Column(Boolean, default=False)
    accessibility_notes = Column(Text, nullable=True)
    
    # Do not contact
    is_blacklisted = Column(Boolean, default=False)
    blacklist_reason = Column(Text, nullable=True)
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    
    customer = relationship("Customer", backref="guest_preferences")


class CustomerLifetimeValue(Base):
    """Customer lifetime value calculations"""
    __tablename__ = "customer_lifetime_values"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, unique=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    # Basic metrics
    first_visit_date = Column(DateTime(timezone=True), nullable=True)
    last_visit_date = Column(DateTime(timezone=True), nullable=True)
    total_visits = Column(Integer, default=0)
    total_spend = Column(Float, default=0.0)
    
    # Visit frequency
    avg_days_between_visits = Column(Float, nullable=True)
    visit_frequency_score = Column(Integer, nullable=True)  # 1-5
    
    # Spending metrics
    avg_order_value = Column(Float, nullable=True)
    average_order_value = Column(Float, nullable=True)  # Alias for avg_order_value
    max_order_value = Column(Float, nullable=True)
    monetary_score = Column(Integer, nullable=True)  # 1-5
    
    # Recency
    days_since_last_visit = Column(Integer, nullable=True)
    recency_score = Column(Integer, nullable=True)  # 1-5
    
    # Calculated CLV
    historical_clv = Column(Float, nullable=True)  # Total spent to date
    predicted_clv = Column(Float, nullable=True)  # Predicted future value
    lifetime_value = Column(Float, nullable=True)  # Alias for predicted_clv
    clv_segment = Column(String(30), nullable=True)  # high, medium, low
    segment = Column(String(30), nullable=True)  # Alias for clv_segment

    # Churn prediction
    churn_risk_score = Column(Float, nullable=True)  # 0-1
    predicted_next_visit = Column(DateTime(timezone=True), nullable=True)
    
    last_calculated = Column(DateTime(timezone=True), server_default=func.now())
    
    customer = relationship("Customer", backref="clv_calculations")
    venue = relationship("Venue", backref="customer_clv")


# =============================================================================
# SECTION V: ONLINE, QR & SELF-SERVICE
# =============================================================================

class QRPaymentSession(Base):
    """QR code pay-at-table sessions"""
    __tablename__ = "qr_payment_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    
    # Session details
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Bill details
    bill_total = Column(Float, nullable=False)
    items_json = Column(JSON, nullable=True)  # Snapshot of order items
    
    # Split payment support
    is_split_payment = Column(Boolean, default=False)
    split_type = Column(String(20), nullable=True)  # equal, by_item, custom
    number_of_splits = Column(Integer, nullable=True)
    
    # Payment progress
    amount_paid = Column(Float, default=0.0)
    payments = Column(JSON, default=list)  # [{guest_id, amount, method, timestamp}]
    
    # Tip
    suggested_tips = Column(JSON, default=list)  # [15, 18, 20, 25] percentages
    tip_amount = Column(Float, default=0.0)
    
    # Status
    status = Column(String(20), default="pending")  # pending, partial, completed, expired
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Guest info (optional)
    guest_email = Column(String(255), nullable=True)
    send_receipt = Column(Boolean, default=False)
    
    venue = relationship("Venue", backref="qr_payment_sessions")
    table = relationship("Table", backref="qr_payment_sessions")
    order = relationship("Order", backref="qr_payment_session")


class ReorderSession(Base):
    """Scan-to-reorder last order functionality"""
    __tablename__ = "reorder_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    # Reference order
    reference_order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    reference_items = Column(JSON, nullable=False)  # Snapshot of items
    
    # Current session
    modified_items = Column(JSON, nullable=True)  # Modified version
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    
    # Status
    status = Column(String(20), default="pending")  # pending, modified, ordered, expired
    new_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    venue = relationship("Venue", backref="reorder_sessions")
    customer = relationship("Customer", backref="reorder_sessions")


# =============================================================================
# SECTION W: HARDWARE & IOT EXTENSIONS
# =============================================================================

class IoTDeviceType(str, enum.Enum):
    SCALE = "scale"
    POUR_METER = "pour_meter"
    TEMPERATURE_SENSOR = "temperature_sensor"
    SMART_TAP = "smart_tap"
    DISPENSER = "dispenser"
    TIMER = "timer"
    CAMERA = "camera"
    RFID_READER = "rfid_reader"
    FLOW_METER = "flow_meter"
    KEG_MONITOR = "keg_monitor"


class IoTDevice(Base):
    """IoT device registry"""
    __tablename__ = "iot_devices"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    device_id = Column(String(100), unique=True, nullable=False, index=True)
    device_type = Column(String(30), nullable=False)  # IoTDeviceType
    device_name = Column(String(100), nullable=False)
    device_model = Column(String(100), nullable=True)

    # Aliases for service compatibility
    serial_number = Column(String(100), nullable=True)  # Alias for device_id
    location = Column(String(200), nullable=True)  # Alias for location_description
    status = Column(String(20), default="active")  # active, inactive, maintenance
    configuration = Column(JSON, nullable=True)  # Alias for config_json
    firmware_version = Column(String(50), nullable=True)

    # Location
    location_description = Column(String(200), nullable=True)
    station_id = Column(Integer, ForeignKey("venue_stations.id"), nullable=True)

    # Connection
    connection_type = Column(String(20), nullable=True, default="network")  # wifi, bluetooth, serial, network
    ip_address = Column(String(45), nullable=True)
    mac_address = Column(String(17), nullable=True)

    # Status
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    battery_level = Column(Integer, nullable=True)  # 0-100

    # Configuration
    config_json = Column(JSON, nullable=True)

    # Calibration
    last_calibration = Column(DateTime(timezone=True), nullable=True)
    calibration_due = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="iot_devices")
    station = relationship("VenueStation", backref="iot_devices")
    
    __table_args__ = (
        Index('ix_iot_device_venue_type', 'venue_id', 'device_type'),
    )


class TemperatureLog(Base):
    """HACCP temperature logging"""
    __tablename__ = "temperature_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("iot_devices.id"), nullable=False)

    # Reading - with service compatibility aliases
    temperature_celsius = Column(Float, nullable=False)
    temperature = Column(Float, nullable=True)  # Alias for service compatibility
    temperature_unit = Column(String(5), default="C")
    humidity_percent = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)  # Alias for service compatibility

    # Thresholds
    min_threshold = Column(Float, nullable=True)
    max_threshold = Column(Float, nullable=True)
    is_in_range = Column(Boolean, nullable=True, default=True)

    # Alert
    alert_triggered = Column(Boolean, default=False)
    alert_type = Column(String(30), nullable=True)  # above_maximum, below_minimum
    alert_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    # Location context
    location_type = Column(String(30), nullable=True)  # fridge, freezer, storage, prep_area
    location_name = Column(String(100), nullable=True)
    location = Column(String(200), nullable=True)  # Alias for service compatibility

    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Alias
    
    venue = relationship("Venue", backref="temperature_logs")
    device = relationship("IoTDevice", backref="temperature_logs")
    
    __table_args__ = (
        Index('ix_temp_logs_venue_device', 'venue_id', 'device_id', 'recorded_at'),
    )


class PourReading(Base):
    """Smart pour/flow meter readings"""
    __tablename__ = "pour_readings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("iot_devices.id"), nullable=False)

    # Linked stock item
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)

    # Pour data
    pour_volume_ml = Column(Float, nullable=False)
    pour_duration_seconds = Column(Float, nullable=True)

    # Expected vs actual
    expected_volume_ml = Column(Float, nullable=True)
    variance_ml = Column(Float, nullable=True)
    variance_percent = Column(Float, nullable=True)

    # Context
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=True)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Flags
    is_anomaly = Column(Boolean, default=False)
    anomaly_type = Column(String(30), nullable=True)  # overpour, underpour, free_pour

    poured_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="pour_readings")
    device = relationship("IoTDevice", backref="pour_readings")
    stock_item = relationship("StockItem", backref="pour_readings")


# =============================================================================
# RFID INVENTORY TRACKING
# =============================================================================

class RFIDTagType(str, enum.Enum):
    ASSET = "asset"  # Equipment, furniture, etc.
    INVENTORY = "inventory"  # Stock items (cases, bottles)
    CONTAINER = "container"  # Reusable containers, kegs
    PALLET = "pallet"  # Bulk shipments
    SHELF = "shelf"  # Shelf/location tag
    STAFF = "staff"  # Staff badges (for reference)


# RFIDTag is defined in hardware.py - DO NOT define here


class RFIDReading(Base):
    """RFID tag scan/read events"""
    __tablename__ = "rfid_readings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Reader and tag
    reader_id = Column(Integer, ForeignKey("iot_devices.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("rfid_tags.id"), nullable=False)

    # Read details
    read_type = Column(String(30), nullable=False)  # inventory_scan, movement, checkout, checkin, count
    signal_strength = Column(Integer, nullable=True)  # RSSI value
    read_count = Column(Integer, default=1)  # Multiple reads in scan period

    # Location context
    location_zone = Column(String(50), nullable=True)
    location_description = Column(String(200), nullable=True)

    # Movement tracking
    previous_zone = Column(String(50), nullable=True)
    movement_detected = Column(Boolean, default=False)

    # Context
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    transfer_id = Column(Integer, nullable=True)  # Stock transfer

    # Alerts
    alert_triggered = Column(Boolean, default=False)
    alert_type = Column(String(50), nullable=True)  # unauthorized_movement, expiry_warning, low_stock

    read_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="rfid_readings")
    reader = relationship("IoTDevice", backref="rfid_readings")
    tag = relationship("RFIDTag", backref="readings")

    __table_args__ = (
        Index('ix_rfid_reading_venue_tag', 'venue_id', 'tag_id', 'read_at'),
        Index('ix_rfid_reading_reader', 'reader_id', 'read_at'),
    )


class RFIDInventoryCount(Base):
    """RFID-based inventory count sessions"""
    __tablename__ = "rfid_inventory_counts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Count session
    count_id = Column(String(50), unique=True, nullable=False, index=True)
    count_type = Column(String(30), nullable=False)  # full, zone, spot_check, cycle

    # Scope
    zone = Column(String(50), nullable=True)  # Specific zone or null for full
    category_id = Column(Integer, nullable=True)  # Specific category

    # Status
    status = Column(String(20), default="in_progress")  # in_progress, completed, cancelled
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Results
    tags_expected = Column(Integer, nullable=True)
    tags_found = Column(Integer, default=0)
    tags_missing = Column(Integer, default=0)
    tags_unexpected = Column(Integer, default=0)  # Found but not expected

    # Details
    found_tags = Column(JSON, nullable=True)  # [tag_ids]
    missing_tags = Column(JSON, nullable=True)  # [tag_ids]
    unexpected_tags = Column(JSON, nullable=True)  # [tag_ids]

    # Variance
    variance_value = Column(Float, nullable=True)  # Total value variance
    variance_items = Column(Integer, nullable=True)  # Number of items with variance

    # Staff
    started_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    completed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    venue = relationship("Venue", backref="rfid_inventory_counts")

    __table_args__ = (
        Index('ix_rfid_count_venue_date', 'venue_id', 'started_at'),
    )


# =============================================================================
# FLOW METER - BULK LIQUID TRACKING
# =============================================================================

class FlowMeterType(str, enum.Enum):
    KEG = "keg"  # Beer/beverage kegs
    TANK = "tank"  # Bulk storage tanks
    LINE = "line"  # Beverage lines
    DISPENSER = "dispenser"  # Sauce/oil dispensers
    FUEL = "fuel"  # Cooking fuel (gas)


class FlowMeterReading(Base):
    """Flow meter readings for bulk liquid inventory"""
    __tablename__ = "flow_meter_readings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("iot_devices.id"), nullable=False)

    # Meter type and context
    meter_type = Column(String(30), nullable=False)  # FlowMeterType

    # Linked inventory
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)
    container_id = Column(String(50), nullable=True)  # Keg ID, tank ID

    # Flow measurement
    flow_volume_ml = Column(Float, nullable=False)
    flow_rate_ml_per_sec = Column(Float, nullable=True)
    flow_duration_seconds = Column(Float, nullable=True)

    # Cumulative tracking
    total_dispensed_ml = Column(Float, nullable=True)  # Total since last reset/refill
    remaining_volume_ml = Column(Float, nullable=True)  # Estimated remaining
    container_capacity_ml = Column(Float, nullable=True)  # Full capacity
    fill_percentage = Column(Float, nullable=True)  # % remaining

    # Temperature (important for beverages)
    temperature_celsius = Column(Float, nullable=True)

    # Pressure (for kegs/tanks)
    pressure_psi = Column(Float, nullable=True)

    # Context
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    tap_number = Column(Integer, nullable=True)  # For multi-tap systems

    # Alerts
    is_low_level = Column(Boolean, default=False)
    is_empty = Column(Boolean, default=False)
    alert_sent = Column(Boolean, default=False)

    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="flow_meter_readings")
    device = relationship("IoTDevice", backref="flow_meter_readings")
    stock_item = relationship("StockItem", backref="flow_meter_readings")

    __table_args__ = (
        Index('ix_flow_meter_venue_device', 'venue_id', 'device_id', 'recorded_at'),
        Index('ix_flow_meter_container', 'container_id', 'recorded_at'),
    )


class KegTracking(Base):
    """Keg-specific tracking for beer/beverage management"""
    __tablename__ = "keg_tracking"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Keg identification
    keg_id = Column(String(50), nullable=False, index=True)
    rfid_tag_id = Column(Integer, ForeignKey("rfid_tags.id"), nullable=True)
    flow_meter_id = Column(Integer, ForeignKey("iot_devices.id"), nullable=True)

    # Product
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)
    product_name = Column(String(200), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Keg specs
    keg_size_liters = Column(Float, nullable=False)  # 20L, 30L, 50L
    keg_type = Column(String(30), nullable=True)  # slim, full, sixtel, half_barrel

    # Status
    status = Column(String(30), default="full")  # full, tapped, low, empty, returned

    # Volume tracking
    initial_volume_ml = Column(Float, nullable=False)
    current_volume_ml = Column(Float, nullable=False)
    dispensed_volume_ml = Column(Float, default=0)
    waste_volume_ml = Column(Float, default=0)  # Foam, spillage

    # Dates
    received_date = Column(DateTime(timezone=True), nullable=True)
    tapped_date = Column(DateTime(timezone=True), nullable=True)
    empty_date = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)

    # Location
    current_location = Column(String(100), nullable=True)  # Cooler, bar, storage
    tap_number = Column(Integer, nullable=True)

    # Cost tracking
    purchase_price = Column(Float, nullable=True)
    price_per_ml = Column(Float, nullable=True)

    # Performance
    pours_count = Column(Integer, default=0)
    avg_pour_ml = Column(Float, nullable=True)
    yield_percentage = Column(Float, nullable=True)  # Actual vs expected yield

    # Deposit tracking
    deposit_amount = Column(Float, nullable=True)
    deposit_returned = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="keg_tracking")
    rfid_tag = relationship("RFIDTag", backref="keg")
    flow_meter = relationship("IoTDevice", backref="kegs")
    stock_item = relationship("StockItem", backref="kegs")
    supplier = relationship("Supplier", backref="kegs")

    __table_args__ = (
        Index('ix_keg_venue_status', 'venue_id', 'status'),
        Index('ix_keg_product', 'venue_id', 'stock_item_id'),
    )


class BulkTankLevel(Base):
    """Bulk storage tank level monitoring"""
    __tablename__ = "bulk_tank_levels"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Tank identification
    tank_id = Column(String(50), nullable=False, index=True)
    tank_name = Column(String(100), nullable=False)
    flow_meter_id = Column(Integer, ForeignKey("iot_devices.id"), nullable=True)

    # Product
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)
    product_type = Column(String(50), nullable=True)  # oil, sauce, syrup, etc.

    # Tank specs
    capacity_liters = Column(Float, nullable=False)
    min_level_liters = Column(Float, nullable=True)  # Reorder point

    # Current reading
    current_level_liters = Column(Float, nullable=False)
    fill_percentage = Column(Float, nullable=False)

    # Consumption tracking
    daily_usage_avg_liters = Column(Float, nullable=True)
    days_until_empty = Column(Float, nullable=True)

    # Status
    status = Column(String(20), default="normal")  # normal, low, critical, empty
    last_refill_date = Column(DateTime(timezone=True), nullable=True)
    last_refill_amount = Column(Float, nullable=True)

    # Alerts
    low_level_alert_sent = Column(Boolean, default=False)
    critical_level_alert_sent = Column(Boolean, default=False)

    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="bulk_tank_levels")
    flow_meter = relationship("IoTDevice", backref="tank_levels")
    stock_item = relationship("StockItem", backref="tank_levels")

    __table_args__ = (
        Index('ix_tank_venue', 'venue_id', 'tank_id'),
    )


# =============================================================================
# SECTION X: COMPLIANCE & AUDIT (DEEP)
# =============================================================================

class ImmutableAuditLog(Base):
    """WORM (Write Once Read Many) audit log for compliance"""
    __tablename__ = "immutable_audit_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    # Log identification
    log_uuid = Column(String(36), unique=True, nullable=False, index=True)
    sequence_number = Column(Integer, nullable=False)  # Sequential within venue
    
    # Event details
    event_type = Column(String(50), nullable=False)
    event_category = Column(String(30), nullable=False)  # fiscal, financial, security, compliance
    event_description = Column(Text, nullable=False)
    
    # Actor
    actor_type = Column(String(20), nullable=False)  # user, system, external
    actor_id = Column(Integer, nullable=True)
    actor_name = Column(String(200), nullable=True)
    actor_ip = Column(String(45), nullable=True)
    
    # Target
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True)
    
    # Data snapshot
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    
    # Integrity
    checksum = Column(String(64), nullable=False)  # SHA-256 of content
    previous_checksum = Column(String(64), nullable=True)  # Chain link
    
    # Timestamp
    event_timestamp = Column(DateTime(timezone=True), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Alias for service

    # Retention
    retention_until = Column(DateTime(timezone=True), nullable=True)
    is_archived = Column(Boolean, default=False)
    
    venue = relationship("Venue", backref="immutable_audit_logs")
    
    __table_args__ = (
        Index('ix_immutable_audit_venue_seq', 'venue_id', 'sequence_number'),
        Index('ix_immutable_audit_category', 'venue_id', 'event_category', 'event_timestamp'),
    )


class FiscalArchive(Base):
    """Digital archive of fiscal receipts"""
    __tablename__ = "fiscal_archives"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    
    # Fiscal data
    fiscal_number = Column(String(50), nullable=False, index=True)
    fiscal_memory_number = Column(String(50), nullable=True)
    receipt_date = Column(DateTime(timezone=True), nullable=False)
    
    # Receipt content
    receipt_text = Column(Text, nullable=False)
    receipt_json = Column(JSON, nullable=True)  # Structured version
    
    # Amounts
    total_amount = Column(Float, nullable=False)
    vat_amounts = Column(JSON, nullable=True)  # {rate: amount}
    payment_methods = Column(JSON, nullable=True)
    
    # Signatures
    digital_signature = Column(Text, nullable=True)
    qr_code_data = Column(Text, nullable=True)
    
    # NRA compliance
    unp = Column(String(50), nullable=True)  # Unique number of sale
    device_serial = Column(String(50), nullable=True)
    operator_code = Column(String(20), nullable=True)
    
    # Archive metadata
    archive_date = Column(DateTime(timezone=True), server_default=func.now())
    archive_checksum = Column(String(64), nullable=False)
    retention_until = Column(DateTime(timezone=True), nullable=False)
    
    venue = relationship("Venue", backref="fiscal_archives")
    order = relationship("Order", backref="fiscal_archive")
    
    __table_args__ = (
        Index('ix_fiscal_archive_number', 'venue_id', 'fiscal_number'),
        Index('ix_fiscal_archive_date', 'venue_id', 'receipt_date'),
    )


class NRAExportLog(Base):
    """Export logs for NRA/NAP inspections"""
    __tablename__ = "nra_export_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    # Export details
    export_type = Column(String(30), nullable=False)  # sales, vat, inventory, payroll
    export_format = Column(String(20), nullable=False)  # xml, csv, json, pdf
    
    # Date range
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # File info
    file_name = Column(String(200), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    file_checksum = Column(String(64), nullable=True)
    file_path = Column(String(500), nullable=True)
    
    # Request context
    requested_by_type = Column(String(20), nullable=False)  # user, authority, system
    requested_by_id = Column(Integer, nullable=True)
    request_reference = Column(String(100), nullable=True)  # Authority reference number
    
    # Status
    status = Column(String(20), nullable=False)  # generated, sent, acknowledged
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Alias for service
    sent_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    venue = relationship("Venue", backref="nra_export_logs")


# =============================================================================
# SECTION Y: AI & AUTOMATION
# =============================================================================

class AIModelType(str, enum.Enum):
    SALES_FORECAST = "sales_forecast"
    DEMAND_PREDICTION = "demand_prediction"
    PRICE_OPTIMIZATION = "price_optimization"
    ANOMALY_DETECTION = "anomaly_detection"
    CHURN_PREDICTION = "churn_prediction"
    UPSELL_RECOMMENDATION = "upsell_recommendation"
    LABOR_OPTIMIZATION = "labor_optimization"


class AIModel(Base):
    """AI model registry"""
    __tablename__ = "ai_models"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True)  # Null = global model
    
    model_type = Column(String(30), nullable=False)  # AIModelType
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(20), nullable=False)
    
    # Training info
    training_data_start = Column(DateTime(timezone=True), nullable=True)
    training_data_end = Column(DateTime(timezone=True), nullable=True)
    samples_count = Column(Integer, nullable=True)
    
    # Performance metrics
    accuracy_score = Column(Float, nullable=True)
    precision_score = Column(Float, nullable=True)
    recall_score = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    mae = Column(Float, nullable=True)  # Mean Absolute Error
    rmse = Column(Float, nullable=True)  # Root Mean Square Error
    
    # Model artifacts
    model_path = Column(String(500), nullable=True)
    model_parameters = Column(JSON, nullable=True)
    feature_importance = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_production = Column(Boolean, default=False)
    
    # Lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_trained = Column(DateTime(timezone=True), nullable=True)
    last_prediction = Column(DateTime(timezone=True), nullable=True)
    predictions_count = Column(Integer, default=0)
    
    venue = relationship("Venue", backref="ai_models")


class AIPrediction(Base):
    """AI prediction log"""
    __tablename__ = "ai_predictions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=False)
    
    # Prediction details
    prediction_type = Column(String(30), nullable=False)
    prediction_target = Column(String(50), nullable=True)  # What we're predicting
    prediction_horizon = Column(String(20), nullable=True)  # daily, weekly, etc.
    
    # Input/Output
    input_features = Column(JSON, nullable=True)
    predicted_value = Column(Float, nullable=True)
    predicted_class = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=True)
    prediction_range = Column(JSON, nullable=True)  # {low, high}
    
    # Actuals (filled later)
    actual_value = Column(Float, nullable=True)
    actual_class = Column(String(50), nullable=True)
    prediction_error = Column(Float, nullable=True)
    
    # Usage
    was_used = Column(Boolean, default=False)
    action_taken = Column(String(100), nullable=True)
    
    predicted_at = Column(DateTime(timezone=True), server_default=func.now())
    target_date = Column(DateTime(timezone=True), nullable=True)
    
    venue = relationship("Venue", backref="ai_predictions")
    model = relationship("AIModel", backref="predictions")
    
    __table_args__ = (
        Index('ix_ai_predictions_venue_type', 'venue_id', 'prediction_type', 'predicted_at'),
    )


class AutomatedAction(Base):
    """Automated actions triggered by AI/rules"""
    __tablename__ = "automated_actions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    action_type = Column(String(50), nullable=False)
    action_name = Column(String(100), nullable=False)
    
    # Trigger
    trigger_type = Column(String(30), nullable=False)  # ai_prediction, rule, schedule, event
    trigger_source = Column(String(100), nullable=True)
    trigger_data = Column(JSON, nullable=True)
    
    # Action details
    action_parameters = Column(JSON, nullable=False)
    
    # Execution
    status = Column(String(20), nullable=False)  # pending, executed, failed, cancelled
    executed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Human override
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    override_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="automated_actions")


# =============================================================================
# SECTION Z: PLATFORM & ARCHITECTURE
# =============================================================================

class FeatureFlag(Base):
    """Per-location feature flags"""
    __tablename__ = "feature_flags"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True)  # Null = global
    tenant_id = Column(Integer, nullable=True)
    
    flag_key = Column(String(100), nullable=False, index=True)
    flag_name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    # State
    is_enabled = Column(Boolean, default=False)
    rollout_percentage = Column(Integer, default=100)  # 0-100
    
    # Targeting
    target_roles = Column(JSON, nullable=True)  # Specific roles
    target_users = Column(JSON, nullable=True)  # Specific user IDs
    
    # Schedule
    enabled_from = Column(DateTime(timezone=True), nullable=True)
    enabled_until = Column(DateTime(timezone=True), nullable=True)
    
    # Tracking
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="feature_flags")
    tenant = relationship("Tenant", backref="feature_flags")
    
    __table_args__ = (
        UniqueConstraint('venue_id', 'flag_key', name='uq_venue_feature_flag'),
    )


class WhiteLabelConfig(Base):
    """White-label branding configuration"""
    __tablename__ = "white_label_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True)  # For venue-specific config

    # Branding
    brand_name = Column(String(200), nullable=False)
    logo_url = Column(String(500), nullable=True)
    favicon_url = Column(String(500), nullable=True)
    
    # Colors
    primary_color = Column(String(10), nullable=True)
    secondary_color = Column(String(10), nullable=True)
    accent_color = Column(String(10), nullable=True)
    
    # Domain
    custom_domain = Column(String(200), nullable=True)
    ssl_enabled = Column(Boolean, default=True)
    
    # Email
    email_from_name = Column(String(100), nullable=True)
    email_from_address = Column(String(255), nullable=True)
    
    # Receipts
    receipt_header = Column(Text, nullable=True)
    receipt_footer = Column(Text, nullable=True)
    receipt_logo_url = Column(String(500), nullable=True)
    
    # Legal
    terms_url = Column(String(500), nullable=True)
    privacy_url = Column(String(500), nullable=True)
    support_email = Column(String(255), nullable=True)
    support_phone = Column(String(20), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    tenant = relationship("Tenant", backref="white_label_config")


# =============================================================================
# SECTION AK: LEGAL, INSURANCE & RISK
# =============================================================================

class IncidentType(str, enum.Enum):
    INJURY_CUSTOMER = "injury_customer"
    INJURY_STAFF = "injury_staff"
    PROPERTY_DAMAGE = "property_damage"
    FOOD_SAFETY = "food_safety"
    THEFT = "theft"
    HARASSMENT = "harassment"
    SLIP_FALL = "slip_fall"
    FIRE_HAZARD = "fire_hazard"
    OTHER = "other"


class IncidentReport(Base):
    """Automated incident report generation"""
    __tablename__ = "incident_reports"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    # Incident identification
    incident_number = Column(String(50), unique=True, nullable=False, index=True)
    incident_type = Column(String(30), nullable=False)  # IncidentType
    severity = Column(String(20), nullable=False)  # minor, moderate, major, critical
    
    # Date/time
    incident_date = Column(DateTime(timezone=True), nullable=False)
    reported_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Location
    location_description = Column(String(200), nullable=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    floor_plan_coordinates = Column(JSON, nullable=True)  # {x, y}
    
    # People involved
    injured_parties = Column(JSON, nullable=True)  # [{name, contact, role}]
    witnesses = Column(JSON, nullable=True)  # [{name, contact, statement}]
    staff_involved = Column(JSON, nullable=True)  # [staff_user_id]
    
    # Description
    description = Column(Text, nullable=False)
    immediate_actions = Column(Text, nullable=True)
    
    # Evidence
    photos = Column(JSON, nullable=True)  # [url]
    video_clips = Column(JSON, nullable=True)  # [url]
    related_orders = Column(JSON, nullable=True)  # [order_id]
    
    # Medical
    medical_attention_required = Column(Boolean, default=False)
    ambulance_called = Column(Boolean, default=False)
    hospital_name = Column(String(200), nullable=True)
    
    # Insurance
    insurance_claim_filed = Column(Boolean, default=False)
    insurance_claim_number = Column(String(50), nullable=True)
    estimated_liability = Column(Float, nullable=True)
    
    # Investigation
    investigation_status = Column(String(20), default="open")  # open, investigating, closed
    root_cause = Column(Text, nullable=True)
    preventive_measures = Column(Text, nullable=True)
    
    # Sign-off
    reported_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    closed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    venue = relationship("Venue", backref="incident_reports")
    
    __table_args__ = (
        Index('ix_incident_venue_date', 'venue_id', 'incident_date'),
        Index('ix_incident_type_status', 'venue_id', 'incident_type', 'investigation_status'),
    )


class AgeVerificationLog(Base):
    """Age verification audit trail"""
    __tablename__ = "age_verification_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    
    # Verification
    verification_type = Column(String(30), nullable=False)  # id_check, verbal, system
    document_type = Column(String(30), nullable=True)  # passport, id_card, driving_license
    
    # Result
    verification_passed = Column(Boolean, nullable=False)
    verified_age = Column(Integer, nullable=True)
    minimum_age_required = Column(Integer, nullable=False)
    
    # Product
    product_category = Column(String(50), nullable=True)  # alcohol, tobacco
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True)
    
    # Staff
    verified_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    sale_refused = Column(Boolean, default=False)
    refusal_reason = Column(String(100), nullable=True)
    
    verified_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="age_verification_logs")
    order = relationship("Order", backref="age_verifications")
    
    __table_args__ = (
        Index('ix_age_verification_venue_date', 'venue_id', 'verified_at'),
    )


# =============================================================================
# SECTION AM: ESG & SUSTAINABILITY EXTENSIONS
# =============================================================================

class FoodDonation(Base):
    """Food donation tracking"""
    __tablename__ = "food_donations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    # Donation details
    donation_date = Column(DateTime(timezone=True), nullable=False)
    recipient_organization = Column(String(200), nullable=False)
    recipient_contact = Column(String(100), nullable=True)
    
    # Food details
    items_donated = Column(JSON, nullable=False)  # [{item_name, quantity, unit}]
    total_weight_kg = Column(Float, nullable=True)
    estimated_servings = Column(Integer, nullable=True)
    
    # Value
    retail_value = Column(Float, nullable=True)
    tax_deductible_value = Column(Float, nullable=True)
    
    # Transport
    pickup_or_delivery = Column(String(20), nullable=False)  # pickup, delivery
    transport_notes = Column(Text, nullable=True)
    
    # Compliance
    temperature_at_handoff = Column(Float, nullable=True)
    food_safety_checklist_completed = Column(Boolean, default=False)
    
    # Documentation
    receipt_number = Column(String(50), nullable=True)
    photos = Column(JSON, nullable=True)
    
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    venue = relationship("Venue", backref="food_donations")


# =============================================================================
# SECTION AP: TRAINING & CERTIFICATION
# =============================================================================

class TrainingModule(Base):
    """Training module definitions"""
    __tablename__ = "training_modules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=True)
    
    # Module info
    module_code = Column(String(50), nullable=False, unique=True)
    module_name = Column(JSON, nullable=False)  # {bg, en}
    description = Column(JSON, nullable=True)
    
    # Content
    content_type = Column(String(20), nullable=False)  # video, document, quiz, practical
    content_url = Column(String(500), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # Requirements
    required_for_roles = Column(JSON, default=list)  # [role_names]
    prerequisite_modules = Column(JSON, default=list)  # [module_ids]
    
    # Certification
    is_certification = Column(Boolean, default=False)
    certification_valid_months = Column(Integer, nullable=True)
    passing_score = Column(Integer, nullable=True)  # For quizzes
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class StaffTrainingRecord(Base):
    """Staff training completion records"""
    __tablename__ = "staff_training_records"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    staff_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("training_modules.id"), nullable=False)
    
    # Progress
    status = Column(String(20), nullable=False)  # not_started, in_progress, completed, failed
    progress_percent = Column(Integer, default=0)
    
    # Completion
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    score = Column(Integer, nullable=True)  # For quizzes
    
    # Certification
    certification_expires = Column(DateTime(timezone=True), nullable=True)
    certificate_url = Column(String(500), nullable=True)
    
    # Verification
    verified_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    staff_user = relationship("StaffUser", foreign_keys=[staff_user_id], backref="training_records")
    module = relationship("TrainingModule", backref="completion_records")
    
    __table_args__ = (
        UniqueConstraint('staff_user_id', 'module_id', name='uq_staff_training_module'),
    )


# =============================================================================
# SECTION AR: ECONOMIC RESILIENCE & CRISIS MODES
# =============================================================================

class CrisisMode(Base):
    """Crisis mode configurations and activations"""
    __tablename__ = "crisis_modes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    # Crisis type
    crisis_type = Column(String(30), nullable=False)
    # Types: pandemic, economic_crisis, supply_shortage, staffing_crisis, 
    #        power_outage, emergency, blackout
    
    # Status
    is_active = Column(Boolean, default=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    activated_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Menu adjustments
    simplified_menu_enabled = Column(Boolean, default=False)
    enabled_categories = Column(JSON, nullable=True)
    disabled_items = Column(JSON, nullable=True)
    
    # Pricing adjustments
    margin_protection_enabled = Column(Boolean, default=False)
    price_increase_percent = Column(Float, nullable=True)
    
    # Staffing
    minimum_staff_mode = Column(Boolean, default=False)
    
    # Communication
    customer_notice = Column(JSON, nullable=True)  # {bg, en}
    staff_notice = Column(JSON, nullable=True)
    
    # Auto-settings
    auto_activate_conditions = Column(JSON, nullable=True)
    auto_deactivate_conditions = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="crisis_modes")


# =============================================================================
# RECEIPT TEMPLATES
# =============================================================================

class ReceiptTemplate(Base):
    """Customizable receipt templates"""
    __tablename__ = "receipt_templates"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    
    template_type = Column(String(30), nullable=False)  # customer, merchant, kitchen, void
    template_name = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)
    
    # Header
    header_logo_url = Column(String(500), nullable=True)
    header_text = Column(JSON, nullable=True)  # {line1, line2, line3}
    show_venue_address = Column(Boolean, default=True)
    show_venue_phone = Column(Boolean, default=True)
    show_venue_vat = Column(Boolean, default=True)
    
    # Body customization
    show_item_codes = Column(Boolean, default=False)
    show_modifiers_separately = Column(Boolean, default=True)
    show_item_notes = Column(Boolean, default=True)
    show_waiter_name = Column(Boolean, default=True)
    show_table_number = Column(Boolean, default=True)
    
    # Footer
    footer_text = Column(JSON, nullable=True)  # {line1, line2}
    show_feedback_qr = Column(Boolean, default=False)
    feedback_url = Column(String(500), nullable=True)
    show_social_media = Column(Boolean, default=False)
    social_media_handles = Column(JSON, nullable=True)
    
    # Legal
    legal_text = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    venue = relationship("Venue", backref="receipt_templates")
    
    __table_args__ = (
        Index('ix_receipt_template_venue_type', 'venue_id', 'template_type'),
    )
