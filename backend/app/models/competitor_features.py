"""
Competitor Features Models
Toast, TouchBistro, iiko feature parity - SQLAlchemy models
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean, Text,
    Numeric, Date, JSON, Float
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


# =============================================================================
# 86 AUTOMATION
# =============================================================================

class Item86Config(Base):
    """Configuration for automatic 86-ing of menu items based on stock levels."""
    __tablename__ = "item_86_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Thresholds and automation toggles
    auto_86_enabled = Column(Boolean, default=True)
    auto_restore_enabled = Column(Boolean, default=True)
    threshold_quantity = Column(Numeric(10, 2), default=0.0)

    # Notification settings
    notify_kitchen = Column(Boolean, default=True)
    notify_floor = Column(Boolean, default=True)
    notify_manager = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="item_86_config")


class Item86Log(Base):
    """Log of 86 events (items taken off / restored to menu)."""
    __tablename__ = "item_86_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, index=True)

    # Event details
    event_type = Column(String(30), nullable=False)  # auto_86, manual_86, auto_restore, manual_restore
    triggered_by = Column(String(50), nullable=False)  # system, staff_user_id
    reason = Column(Text)

    # Timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime)
    duration_minutes = Column(Integer)

    # Stock snapshot at time of event
    stock_level_at_event = Column(Numeric(10, 2))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="item_86_logs")
    menu_item = relationship("MenuItem", backref="item_86_logs")


# =============================================================================
# DEMAND FORECASTING - INGREDIENTS
# =============================================================================

class IngredientForecast(Base):
    """Forecasted ingredient usage and stock-out predictions."""
    __tablename__ = "ingredient_forecasts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Forecast target
    forecast_date = Column(Date, nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Predictions
    predicted_usage = Column(Numeric(10, 2), nullable=False)
    current_stock = Column(Numeric(10, 2))

    # Stock-out analysis
    will_stock_out = Column(Boolean, default=False)
    days_of_stock = Column(Numeric(6, 1))
    suggested_order_quantity = Column(Numeric(10, 2), default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="ingredient_forecasts")
    stock_item = relationship("StockItem", backref="ingredient_forecasts")


# =============================================================================
# AUTO PURCHASE ORDERS
# =============================================================================

class AutoPurchaseOrderRule(Base):
    """Rules for automatic purchase order generation."""
    __tablename__ = "auto_purchase_order_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Reorder triggers
    reorder_point = Column(Numeric(10, 2), nullable=False)
    reorder_quantity = Column(Numeric(10, 2), nullable=False)

    # Par level integration
    use_par_level = Column(Boolean, default=False)
    par_level = Column(Numeric(10, 2))

    # Supplier preference
    preferred_supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    minimum_order_quantity = Column(Numeric(10, 2))

    # Status
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="auto_purchase_order_rules")
    stock_item = relationship("StockItem", backref="auto_po_rules")
    preferred_supplier = relationship("Supplier", backref="auto_po_rules")


class SuggestedPurchaseOrder(Base):
    """System-generated suggested purchase orders awaiting approval."""
    __tablename__ = "suggested_purchase_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)

    # Order details
    status = Column(String(30), default="pending")  # pending, approved, rejected, converted
    items = Column(JSON, default=list)  # List of {stock_item_id, quantity, unit_price, ...}
    subtotal = Column(Numeric(12, 2), default=0)

    # Generation context
    trigger_reason = Column(String(200))  # below_reorder_point, forecast_based, par_level
    generated_at = Column(DateTime, default=datetime.utcnow)

    # Approval
    approved_by = Column(Integer, ForeignKey("staff_users.id"))
    approved_at = Column(DateTime)
    converted_po_id = Column(Integer, ForeignKey("purchase_orders.id"))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="suggested_purchase_orders")
    supplier = relationship("Supplier", backref="suggested_purchase_orders")


# =============================================================================
# FOOD COST
# =============================================================================

class FoodCostSnapshot(Base):
    """Point-in-time food cost calculations and trends."""
    __tablename__ = "food_cost_snapshots"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Snapshot scope
    snapshot_date = Column(Date, nullable=False)
    period_type = Column(String(20), default="daily")  # daily, weekly, monthly

    # Optional item-level snapshot
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))

    # Ingredient breakdown
    ingredients = Column(JSON, default=list)  # [{stock_item_id, name, qty, unit_cost, total}]

    # Cost calculations
    ingredient_cost = Column(Numeric(10, 2), default=0)
    adjusted_cost = Column(Numeric(10, 2), default=0)  # After waste/yield adjustments
    total_plate_cost = Column(Numeric(10, 2), default=0)

    # Pricing
    menu_price = Column(Numeric(10, 2), default=0)
    food_cost_percent = Column(Numeric(6, 2), default=0)
    contribution_margin = Column(Numeric(10, 2), default=0)
    gross_profit_percent = Column(Numeric(6, 2), default=0)

    # Suggestions
    suggested_price_for_target = Column(Numeric(10, 2))
    cost_change_percent = Column(Numeric(6, 2))

    # Aggregate venue-level stats (when menu_item_id is NULL)
    total_revenue = Column(Numeric(12, 2))
    total_food_cost = Column(Numeric(12, 2))
    overall_food_cost_percent = Column(Numeric(6, 2))

    calculated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="food_cost_snapshots")


# =============================================================================
# SUPPLIER PERFORMANCE
# =============================================================================

class SupplierPerformance(Base):
    """Calculated supplier performance scorecard."""
    __tablename__ = "supplier_performances"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # Evaluation period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Order metrics
    total_orders = Column(Integer, default=0)
    total_order_value = Column(Numeric(12, 2), default=0)

    # Delivery performance
    on_time_deliveries = Column(Integer, default=0)
    late_deliveries = Column(Integer, default=0)
    on_time_percent = Column(Numeric(5, 2), default=0)

    # Quality metrics
    quality_score = Column(Numeric(5, 2), default=0)  # 0-100
    total_issues = Column(Integer, default=0)
    resolved_issues = Column(Integer, default=0)

    # Pricing accuracy
    price_accuracy_percent = Column(Numeric(5, 2))
    price_increases = Column(Integer, default=0)

    # Overall composite score
    overall_score = Column(Numeric(5, 2), default=0)  # 0-100

    calculated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="supplier_performances")
    supplier = relationship("Supplier", backref="performance_records")


class SupplierIssue(Base):
    """Reported issues with suppliers."""
    __tablename__ = "supplier_issues"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # Issue details
    issue_type = Column(String(50), nullable=False)  # late_delivery, quality, wrong_items, short_delivery, pricing
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    description = Column(Text, nullable=False)

    # Context
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"))
    affected_items = Column(JSON)  # [{stock_item_id, description}]

    # Status tracking
    status = Column(String(30), default="open")  # open, investigating, resolved, closed
    resolution = Column(Text)
    resolved_at = Column(DateTime)
    resolved_by = Column(Integer, ForeignKey("staff_users.id"))

    # Reporter
    reported_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    reported_at = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="supplier_issues")
    supplier = relationship("Supplier", backref="issues")


# =============================================================================
# PAR LEVELS
# =============================================================================

class ParLevelConfig(Base):
    """Par level configuration for stock items."""
    __tablename__ = "par_level_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Par levels
    minimum_level = Column(Numeric(10, 2), nullable=False, default=0)
    par_level = Column(Numeric(10, 2), nullable=False, default=0)
    maximum_level = Column(Numeric(10, 2))
    safety_stock = Column(Numeric(10, 2), default=0)

    # Usage statistics
    average_daily_usage = Column(Numeric(10, 2))
    last_calculated = Column(DateTime)

    # Calculation parameters
    historical_days = Column(Integer, default=30)
    safety_days = Column(Integer, default=2)
    target_days = Column(Integer, default=7)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="par_level_configs")
    stock_item = relationship("StockItem", backref="par_level_config")


# =============================================================================
# WASTE TRACKING
# =============================================================================

class WasteLog(Base):
    """Individual waste event records."""
    __tablename__ = "waste_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Item identification
    item_name = Column(String(200), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))

    # Waste details
    quantity = Column(Numeric(10, 3), nullable=False)
    unit = Column(String(30), nullable=False)
    unit_cost = Column(Numeric(10, 2), default=0)
    total_cost = Column(Numeric(10, 2), default=0)

    # Classification
    waste_type = Column(String(50), nullable=False)  # spoilage, overproduction, plate_waste, prep_waste, expired
    cause = Column(String(200))
    notes = Column(Text)
    is_preventable = Column(Boolean, default=False)

    # Location
    station_id = Column(Integer)

    # Staff
    recorded_by = Column(Integer, ForeignKey("staff_users.id"))
    recorded_at = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="waste_logs")


# =============================================================================
# RECIPE SCALING
# =============================================================================

class RecipeScaleLog(Base):
    """Log of recipe scaling operations."""
    __tablename__ = "recipe_scale_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)

    # Scaling details
    original_yield = Column(Numeric(10, 2), nullable=False)
    scaled_yield = Column(Numeric(10, 2), nullable=False)
    scale_factor = Column(Numeric(8, 4), nullable=False)

    # Scaled ingredients snapshot
    scaled_ingredients = Column(JSON, default=list)  # [{name, original_qty, scaled_qty, unit}]

    # Context
    purpose = Column(String(200))
    created_by = Column(Integer, ForeignKey("staff_users.id"))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="recipe_scale_logs")
    menu_item = relationship("MenuItem", backref="recipe_scale_logs")


# =============================================================================
# STOCK TAKING
# =============================================================================

class StockTake(Base):
    """Stock take / inventory count session."""
    __tablename__ = "stock_takes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Identification
    stock_take_number = Column(String(50), nullable=False, unique=True)
    name = Column(String(200))

    # Configuration
    scope_type = Column(String(30), default="full")  # full, partial, category, location
    blind_count = Column(Boolean, default=True)
    category_ids = Column(JSON)

    # Status
    status = Column(String(30), default="draft")  # draft, in_progress, completed, cancelled

    # Counts summary
    items_counted = Column(Integer, default=0)
    items_with_variance = Column(Integer, default=0)

    # Valuation
    total_expected_value = Column(Numeric(12, 2), default=0)
    total_counted_value = Column(Numeric(12, 2), default=0)
    total_variance_value = Column(Numeric(12, 2), default=0)
    variance_percent = Column(Numeric(6, 2), default=0)

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Staff
    created_by = Column(Integer, ForeignKey("staff_users.id"))
    approved_by = Column(Integer, ForeignKey("staff_users.id"))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="stock_takes")
    items = relationship("StockTakeItem", back_populates="stock_take")


class StockTakeItem(Base):
    """Individual item within a stock take session."""
    __tablename__ = "stock_take_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    stock_take_id = Column(Integer, ForeignKey("stock_takes.id"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Expected (system) values
    expected_quantity = Column(Numeric(10, 3), default=0)
    expected_value = Column(Numeric(10, 2), default=0)

    # Counted values
    counted_quantity = Column(Numeric(10, 3))
    counted_value = Column(Numeric(10, 2))
    counted_by = Column(Integer, ForeignKey("staff_users.id"))
    counted_at = Column(DateTime)

    # Location
    location = Column(String(100))

    # Variance
    variance_quantity = Column(Numeric(10, 3), default=0)
    variance_value = Column(Numeric(10, 2), default=0)
    variance_percent = Column(Numeric(6, 2), default=0)
    variance_type = Column(String(20))  # overage, shortage, match

    # Investigation
    requires_investigation = Column(Boolean, default=False)
    investigation_notes = Column(Text)

    # Adjustment
    adjustment_applied = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    stock_take = relationship("StockTake", back_populates="items")
    stock_item = relationship("StockItem", backref="stock_take_items")


# =============================================================================
# INVOICE SCANNING & OCR
# =============================================================================

class ScannedInvoice(Base):
    """Scanned/uploaded invoice with OCR extraction data."""
    __tablename__ = "scanned_invoices"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # File info
    file_url = Column(String(500), nullable=False)
    file_name = Column(String(300), nullable=False)
    file_type = Column(String(20))  # pdf, image
    file_size_bytes = Column(Integer)

    # OCR processing
    ocr_status = Column(String(30), default="pending")  # pending, processing, completed, failed, pending_manual
    ocr_confidence = Column(Numeric(5, 2))
    ocr_raw_text = Column(Text)
    ocr_error = Column(Text)

    # Extracted data
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    supplier_name_extracted = Column(String(300))
    invoice_number_extracted = Column(String(100))
    invoice_date_extracted = Column(Date)
    due_date_extracted = Column(Date)
    subtotal_extracted = Column(Numeric(12, 2))
    tax_extracted = Column(Numeric(10, 2))
    total_extracted = Column(Numeric(12, 2))
    line_items_extracted = Column(JSON)  # [{description, quantity, unit_price, total, matched_stock_item_id}]

    # Verification
    verification_status = Column(String(30), default="unverified")  # unverified, verified, discrepancy
    verified_by = Column(Integer, ForeignKey("staff_users.id"))
    verified_at = Column(DateTime)
    notes = Column(Text)

    # PO matching
    matched_po_id = Column(Integer, ForeignKey("purchase_orders.id"))

    # Staff
    uploaded_by = Column(Integer, ForeignKey("staff_users.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="scanned_invoices")
    supplier = relationship("Supplier", backref="scanned_invoices")


class InvoiceMatchingRule(Base):
    """Rules for matching invoice line item descriptions to stock items."""
    __tablename__ = "invoice_matching_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Matching pattern
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    invoice_description_pattern = Column(String(500), nullable=False)

    # Target stock item
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Unit conversion
    invoice_unit = Column(String(50))
    stock_unit = Column(String(50))
    conversion_factor = Column(Numeric(10, 4), default=1.0)

    # Priority for rule ordering
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="invoice_matching_rules")
    supplier = relationship("Supplier", backref="invoice_matching_rules")
    stock_item = relationship("StockItem", backref="invoice_matching_rules")
