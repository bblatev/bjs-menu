"""
Complete Menu & Inventory Database Models
Persistent storage for all menu and inventory features - Competitor Parity
Replaces in-memory storage with proper SQLAlchemy models
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, ForeignKey,
    Text, JSON, Numeric, Date, Time, Index, UniqueConstraint, Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.db.base import Base


# =============================================================================
# ENUMS
# =============================================================================

class VariantType(str, enum.Enum):
    SIZE = "size"
    PORTION = "portion"
    STYLE = "style"
    CUSTOM = "custom"


class ComboPricingType(str, enum.Enum):
    FIXED = "fixed"
    PERCENTAGE_DISCOUNT = "percentage_discount"
    CHEAPEST_FREE = "cheapest_free"
    TIERED = "tiered"


class UpsellType(str, enum.Enum):
    UPSELL = "upsell"
    CROSS_SELL = "cross_sell"
    UPGRADE = "upgrade"
    ADDON = "addon"


class OfferType(str, enum.Enum):
    NEW_ITEM = "new_item"
    DISCOUNT = "discount"
    SPECIAL_PRICE = "special_price"
    BUNDLE = "bundle"
    BOGO = "bogo"


class Item86Reason(str, enum.Enum):
    SOLD_OUT = "sold_out"
    INGREDIENT_MISSING = "ingredient_missing"
    EQUIPMENT_ISSUE = "equipment_issue"
    QUALITY_ISSUE = "quality_issue"
    SEASONAL = "seasonal"
    OTHER = "other"


class BoardDisplayType(str, enum.Enum):
    FULL_MENU = "full_menu"
    CATEGORY = "category"
    SPECIALS = "specials"
    COMBOS = "combos"
    PROMOTIONS = "promotions"


class BoardLayout(str, enum.Enum):
    GRID = "grid"
    LIST = "list"
    CAROUSEL = "carousel"
    FEATURED = "featured"


class InventoryMethod(str, enum.Enum):
    FIFO = "fifo"
    FEFO = "fefo"
    LIFO = "lifo"
    AVERAGE = "average"


class ReorderPriority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CountType(str, enum.Enum):
    FULL = "full"
    CYCLE = "cycle"
    SPOT = "spot"
    ABC = "abc"


class ShrinkageReason(str, enum.Enum):
    THEFT = "theft"
    DAMAGE = "damage"
    SPOILAGE = "spoilage"
    ADMIN_ERROR = "admin_error"
    VENDOR_ERROR = "vendor_error"
    UNKNOWN = "unknown"


class ReconciliationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    APPROVED = "approved"


# =============================================================================
# MENU ITEM VARIANTS
# =============================================================================

class MenuItemVariant(Base):
    """Size/portion variants for menu items (Small, Medium, Large, etc.)"""
    __tablename__ = "menu_item_variants"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, index=True)

    # Variant details
    name = Column(JSON, nullable=False)  # {"bg": "Малък", "en": "Small"}
    variant_type = Column(Enum(VariantType), default=VariantType.SIZE)
    sku_suffix = Column(String(20), nullable=True)  # "-S", "-M", "-L"

    # Pricing
    price = Column(Numeric(10, 2), nullable=False)
    cost = Column(Numeric(10, 2), nullable=True)

    # Details
    calories = Column(Integer, nullable=True)
    portion_size = Column(String(50), nullable=True)  # "200g", "350g"
    portion_multiplier = Column(Float, default=1.0)  # For recipe scaling

    # Display
    is_default = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    active = Column(Boolean, default=True)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    menu_item = relationship("MenuItem", backref="variants")

    __table_args__ = (
        Index('ix_menu_item_variants_venue_item', 'venue_id', 'menu_item_id'),
        UniqueConstraint('menu_item_id', 'sku_suffix', name='uq_variant_sku'),
        {'extend_existing': True},
    )


# =============================================================================
# COMBOS / BUNDLES
# =============================================================================

class MenuCombo(Base):
    """Combo/bundle deals with multiple items"""
    __tablename__ = "menu_combos"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Basic info
    name = Column(JSON, nullable=False)
    description = Column(JSON, nullable=True)
    image_url = Column(String(500), nullable=True)

    # Pricing
    pricing_type = Column(Enum(ComboPricingType), default=ComboPricingType.FIXED)
    fixed_price = Column(Numeric(10, 2), nullable=True)
    discount_percentage = Column(Float, nullable=True)

    # Availability
    available_from = Column(Time, nullable=True)
    available_until = Column(Time, nullable=True)
    available_days = Column(JSON, default=[0, 1, 2, 3, 4, 5, 6])  # Days of week
    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)

    # Limits
    max_per_order = Column(Integer, nullable=True)
    max_per_day = Column(Integer, nullable=True)
    total_limit = Column(Integer, nullable=True)
    sold_count = Column(Integer, default=0)

    # Status
    active = Column(Boolean, default=True)
    featured = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    items = relationship("MenuComboItem", back_populates="combo", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_menu_combos_venue_active', 'venue_id', 'active'),
    )


class MenuComboItem(Base):
    """Items within a combo"""
    __tablename__ = "menu_combo_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    combo_id = Column(Integer, ForeignKey("menu_combos.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, index=True)

    quantity = Column(Integer, default=1)
    is_required = Column(Boolean, default=True)
    max_selections = Column(Integer, default=1)  # For "choose X" items
    allowed_substitutions = Column(JSON, nullable=True)  # List of item IDs

    sort_order = Column(Integer, default=0)

    combo = relationship("MenuCombo", back_populates="items")
    menu_item = relationship("MenuItem")


# =============================================================================
# MENU TAGS (Enhanced)
# =============================================================================

class MenuTag(Base):
    """Menu tags (vegan, spicy, new, popular, etc.)"""
    __tablename__ = "menu_tags_enhanced"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    code = Column(String(50), nullable=False)  # vegan, spicy, new
    name = Column(JSON, nullable=False)  # Multilingual
    description = Column(JSON, nullable=True)

    # Display
    icon = Column(String(100), nullable=True)  # Emoji or icon class
    color = Column(String(20), nullable=True)  # Hex color
    background_color = Column(String(20), nullable=True)

    # Auto-assignment rules
    auto_assign_rules = Column(JSON, nullable=True)  # Rules for auto-tagging

    sort_order = Column(Integer, default=0)
    active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item_tags = relationship("MenuItemTagAssignment", back_populates="tag", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('venue_id', 'code', name='uq_venue_tag_code'),
    )


class MenuItemTagAssignment(Base):
    """Link between menu items and tags"""
    __tablename__ = "menu_item_tag_assignments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("menu_tags_enhanced.id", ondelete="CASCADE"), nullable=False, index=True)

    auto_assigned = Column(Boolean, default=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    tag = relationship("MenuTag", back_populates="item_tags")

    __table_args__ = (
        UniqueConstraint('menu_item_id', 'tag_id', name='uq_item_tag_assignment'),
    )


# =============================================================================
# UPSELL / CROSS-SELL RULES
# =============================================================================

class UpsellRule(Base):
    """Upsell and cross-sell suggestions"""
    __tablename__ = "upsell_rules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Source item (when this is ordered)
    source_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, index=True)

    # Suggestion type
    suggestion_type = Column(Enum(UpsellType), nullable=False)

    # What to suggest
    suggested_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True)
    suggested_category_id = Column(Integer, ForeignKey("menu_categories.id"), nullable=True)
    suggested_modifier_group_id = Column(Integer, ForeignKey("modifier_groups.id"), nullable=True)

    # Custom message
    message = Column(JSON, nullable=True)  # Multilingual

    # Discount offer
    discount_percentage = Column(Float, nullable=True)
    discount_amount = Column(Numeric(10, 2), nullable=True)

    # Display
    priority = Column(Integer, default=0)
    display_position = Column(String(20), default="popup")  # popup, inline, cart

    # Limits
    max_suggestions_per_order = Column(Integer, default=1)

    # Status
    active = Column(Boolean, default=True)

    # Performance tracking
    times_shown = Column(Integer, default=0)
    times_accepted = Column(Integer, default=0)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    source_item = relationship("MenuItem", foreign_keys=[source_item_id])
    suggested_item = relationship("MenuItem", foreign_keys=[suggested_item_id])


# =============================================================================
# LIMITED TIME OFFERS
# =============================================================================

class LimitedTimeOffer(Base):
    """Limited-time offers with auto-expiry"""
    __tablename__ = "limited_time_offers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Basic info
    name = Column(JSON, nullable=False)
    description = Column(JSON, nullable=True)
    image_url = Column(String(500), nullable=True)
    badge_text = Column(JSON, nullable=True)  # "NEW", "LIMITED"

    # What's on offer
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("menu_categories.id"), nullable=True)
    combo_id = Column(Integer, ForeignKey("menu_combos.id"), nullable=True)

    # Offer type and pricing
    offer_type = Column(Enum(OfferType), nullable=False)
    original_price = Column(Numeric(10, 2), nullable=True)
    offer_price = Column(Numeric(10, 2), nullable=True)
    discount_percentage = Column(Float, nullable=True)

    # Timing
    start_datetime = Column(DateTime(timezone=True), nullable=False)
    end_datetime = Column(DateTime(timezone=True), nullable=False)

    # Quantity limits
    max_quantity = Column(Integer, nullable=True)  # Total available
    max_per_customer = Column(Integer, nullable=True)
    remaining_quantity = Column(Integer, nullable=True)
    sold_count = Column(Integer, default=0)

    # Display options
    countdown_enabled = Column(Boolean, default=True)
    auto_disable_when_sold_out = Column(Boolean, default=True)
    show_remaining_count = Column(Boolean, default=False)

    # Status
    active = Column(Boolean, default=True)
    featured = Column(Boolean, default=False)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    menu_item = relationship("MenuItem")

    __table_args__ = (
        Index('ix_lto_venue_active', 'venue_id', 'active'),
        Index('ix_lto_dates', 'start_datetime', 'end_datetime'),
    )


# =============================================================================
# 86'd ITEMS (OUT OF STOCK)
# =============================================================================

class Item86Record(Base):
    """Track 86'd (out of stock) items"""
    __tablename__ = "item_86_records"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, index=True)

    # Reason and details
    reason = Column(Enum(Item86Reason), nullable=False)
    notes = Column(Text, nullable=True)

    # Expected return
    expected_back = Column(DateTime(timezone=True), nullable=True)
    auto_restore = Column(Boolean, default=True)

    # Alternatives
    alternative_items = Column(JSON, nullable=True)  # List of item IDs

    # Notification
    notify_staff = Column(Boolean, default=True)
    notified = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)

    # Audit
    marked_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    marked_at = Column(DateTime(timezone=True), server_default=func.now())
    restored_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    restored_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    menu_item = relationship("MenuItem")
    marked_by_user = relationship("StaffUser", foreign_keys=[marked_by])

    __table_args__ = (
        Index('ix_86_venue_active', 'venue_id', 'is_active'),
    )


# =============================================================================
# DIGITAL MENU BOARDS
# =============================================================================

class DigitalMenuBoard(Base):
    """Digital menu board configurations"""
    __tablename__ = "digital_menu_boards"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Basic info
    name = Column(String(100), nullable=False)
    token = Column(String(50), unique=True, nullable=False, index=True)

    # Display configuration
    display_type = Column(Enum(BoardDisplayType), default=BoardDisplayType.FULL_MENU)
    layout = Column(Enum(BoardLayout), default=BoardLayout.GRID)
    columns = Column(Integer, default=3)

    # Content selection
    categories = Column(JSON, nullable=True)  # List of category IDs
    items = Column(JSON, nullable=True)  # List of item IDs
    combos = Column(JSON, nullable=True)  # List of combo IDs

    # Display options
    show_prices = Column(Boolean, default=True)
    show_descriptions = Column(Boolean, default=True)
    show_images = Column(Boolean, default=True)
    show_calories = Column(Boolean, default=False)
    show_allergens = Column(Boolean, default=True)
    auto_hide_unavailable = Column(Boolean, default=True)

    # Animation
    rotation_seconds = Column(Integer, default=10)

    # Theming
    theme = Column(String(20), default="dark")  # dark, light, custom
    custom_css = Column(Text, nullable=True)
    background_image = Column(String(500), nullable=True)
    header_text = Column(JSON, nullable=True)
    footer_text = Column(JSON, nullable=True)

    # Scheduling
    schedule = Column(JSON, nullable=True)  # When to display this board

    # Status
    active = Column(Boolean, default=True)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_accessed = Column(DateTime(timezone=True), nullable=True)


# =============================================================================
# BARCODE MANAGEMENT
# =============================================================================

class StockItemBarcode(Base):
    """Barcodes for stock items"""
    __tablename__ = "stock_item_barcodes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False, index=True)

    # Barcode details
    barcode_type = Column(String(20), nullable=False)  # ean13, ean8, upc_a, code128, qr
    barcode_value = Column(String(100), nullable=False, index=True)

    # Status
    is_primary = Column(Boolean, default=True)
    active = Column(Boolean, default=True)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    stock_item = relationship("StockItem", backref="barcodes")

    __table_args__ = (
        UniqueConstraint('venue_id', 'barcode_value', name='uq_venue_barcode'),
        Index('ix_barcode_lookup', 'barcode_value', 'venue_id'),
    )


# =============================================================================
# AUTO-REORDER RULES
# =============================================================================

# AutoReorderRule is defined in feature_models.py - import from there to avoid duplicate
# Using feature_models.AutoReorderRule instead


# =============================================================================
# STOCK BATCHES (FIFO/FEFO)
# =============================================================================

class StockBatchFIFO(Base):
    """Enhanced batch tracking for FIFO/FEFO management with detailed costing"""
    __tablename__ = "stock_batches_fifo"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True, index=True)

    # Batch identification
    batch_number = Column(String(100), nullable=False)
    lot_number = Column(String(100), nullable=True)

    # Quantities
    quantity_received = Column(Numeric(10, 3), nullable=False)
    quantity_remaining = Column(Numeric(10, 3), nullable=False)
    quantity_reserved = Column(Numeric(10, 3), default=0)

    # Dates
    received_date = Column(Date, nullable=False)
    production_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    best_before_date = Column(Date, nullable=True)

    # Costing
    cost_per_unit = Column(Numeric(10, 4), nullable=False)
    total_cost = Column(Numeric(12, 2), nullable=False)

    # Source
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    purchase_order_id = Column(Integer, nullable=True)
    grn_id = Column(Integer, nullable=True)

    # Quality
    quality_status = Column(String(20), default="approved")  # pending, approved, rejected, quarantine
    quality_notes = Column(Text, nullable=True)

    # Status
    status = Column(String(20), default="active")  # active, depleted, expired, disposed

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    stock_item = relationship("StockItem", backref="fifo_batches")
    supplier = relationship("Supplier")

    __table_args__ = (
        Index('ix_batch_expiry', 'venue_id', 'expiry_date'),
        Index('ix_batch_item_status', 'stock_item_id', 'status'),
        UniqueConstraint('venue_id', 'stock_item_id', 'batch_number', name='uq_venue_item_batch'),
    )


# =============================================================================
# SHRINKAGE TRACKING
# =============================================================================

class ShrinkageRecord(Base):
    """Track inventory shrinkage (loss)"""
    __tablename__ = "shrinkage_records"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("stock_batches_fifo.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Loss details
    quantity_lost = Column(Numeric(10, 3), nullable=False)
    unit = Column(String(20), nullable=False)
    value_lost = Column(Numeric(10, 2), nullable=False)

    # Reason
    reason = Column(Enum(ShrinkageReason), nullable=False)
    detailed_reason = Column(Text, nullable=True)

    # Detection
    detected_date = Column(Date, nullable=False)
    detected_during = Column(String(50), nullable=True)  # inventory_count, receiving, production

    # Investigation
    investigated = Column(Boolean, default=False)
    investigation_notes = Column(Text, nullable=True)
    root_cause = Column(String(200), nullable=True)
    corrective_action = Column(Text, nullable=True)

    # Audit
    detected_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    stock_item = relationship("StockItem")
    batch = relationship("StockBatchFIFO")

    __table_args__ = (
        Index('ix_shrinkage_venue_date', 'venue_id', 'detected_date'),
        Index('ix_shrinkage_reason', 'venue_id', 'reason'),
    )


# =============================================================================
# CYCLE COUNTING
# =============================================================================

class CycleCountSchedule(Base):
    """Scheduled cycle counts"""
    __tablename__ = "cycle_count_schedules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    count_type = Column(Enum(CountType), nullable=False)

    # Frequency
    frequency = Column(String(20), nullable=False)  # daily, weekly, monthly
    day_of_week = Column(Integer, nullable=True)  # For weekly (0=Monday)
    day_of_month = Column(Integer, nullable=True)  # For monthly

    # Scope
    categories = Column(JSON, nullable=True)  # Category IDs
    locations = Column(JSON, nullable=True)  # Location IDs
    abc_class = Column(String(1), nullable=True)  # A, B, or C

    # Limits
    items_per_count = Column(Integer, nullable=True)

    # Assignment
    assigned_to = Column(JSON, nullable=True)  # Staff IDs

    # Status
    active = Column(Boolean, default=True)
    last_run = Column(Date, nullable=True)
    next_run = Column(Date, nullable=True)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tasks = relationship("CycleCountTask", back_populates="schedule")


class CycleCountTask(Base):
    """Individual cycle count tasks"""
    __tablename__ = "cycle_count_tasks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    schedule_id = Column(Integer, ForeignKey("cycle_count_schedules.id"), nullable=True)

    # Task details
    count_type = Column(Enum(CountType), nullable=False)
    due_date = Column(Date, nullable=False)

    # Status
    status = Column(String(20), default="pending")  # pending, in_progress, completed, overdue

    # Progress
    items_to_count = Column(Integer, default=0)
    items_counted = Column(Integer, default=0)
    discrepancies_found = Column(Integer, default=0)
    total_variance_value = Column(Numeric(10, 2), default=0)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    schedule = relationship("CycleCountSchedule", back_populates="tasks")
    items = relationship("CycleCountItem", back_populates="task", cascade="all, delete-orphan")


class CycleCountItem(Base):
    """Items within a cycle count task"""
    __tablename__ = "cycle_count_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("cycle_count_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False, index=True)

    # Quantities
    system_quantity = Column(Numeric(10, 3), nullable=False)
    counted_quantity = Column(Numeric(10, 3), nullable=True)
    variance = Column(Numeric(10, 3), nullable=True)
    variance_value = Column(Numeric(10, 2), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, counted, variance, approved

    # Notes
    notes = Column(Text, nullable=True)

    # Audit
    counted_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    counted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    task = relationship("CycleCountTask", back_populates="items")
    stock_item = relationship("StockItem")


# =============================================================================
# UNIT CONVERSIONS
# =============================================================================

class UnitConversion(Base):
    """Unit conversion rules"""
    __tablename__ = "unit_conversions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=True, index=True)  # Null = global
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)  # Null = applies to all

    # Conversion
    from_unit = Column(String(30), nullable=False)
    to_unit = Column(String(30), nullable=False)
    conversion_factor = Column(Numeric(15, 6), nullable=False)

    # Notes
    notes = Column(String(200), nullable=True)

    # Status
    active = Column(Boolean, default=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_unit_conv_lookup', 'from_unit', 'to_unit', 'venue_id'),
    )


# =============================================================================
# INVENTORY RECONCILIATION
# =============================================================================

class ReconciliationSession(Base):
    """Inventory reconciliation sessions"""
    __tablename__ = "reconciliation_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Session details
    session_date = Column(Date, nullable=False)
    session_type = Column(String(30), default="full")  # full, partial, category, location

    # Scope (no FK constraints to avoid table resolution issues)
    category_id = Column(Integer, nullable=True)  # References stock_categories
    location_id = Column(Integer, nullable=True)  # References locations

    # Status
    status = Column(Enum(ReconciliationStatus), default=ReconciliationStatus.PENDING)

    # Progress
    total_items = Column(Integer, default=0)
    items_matched = Column(Integer, default=0)
    items_with_variance = Column(Integer, default=0)
    total_variance_value = Column(Numeric(12, 2), default=0)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Approval
    adjustments_applied = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Audit
    started_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    items = relationship("ReconciliationItem", back_populates="session", cascade="all, delete-orphan")


class ReconciliationItem(Base):
    """Items within a reconciliation session"""
    __tablename__ = "reconciliation_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("reconciliation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False, index=True)

    # Quantities
    system_quantity = Column(Numeric(10, 3), nullable=False)
    physical_quantity = Column(Numeric(10, 3), nullable=True)
    variance = Column(Numeric(10, 3), nullable=True)
    variance_value = Column(Numeric(10, 2), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, counted, approved, adjusted

    # Investigation
    notes = Column(Text, nullable=True)
    variance_reason = Column(String(100), nullable=True)

    # Audit
    counted_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    counted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("ReconciliationSession", back_populates="items")
    stock_item = relationship("StockItem")


# =============================================================================
# SUPPLIER PERFORMANCE
# =============================================================================

class SupplierPerformanceRecord(Base):
    """Track supplier performance metrics"""
    __tablename__ = "supplier_performance_records"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # Period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Order metrics
    total_orders = Column(Integer, default=0)
    orders_on_time = Column(Integer, default=0)
    orders_late = Column(Integer, default=0)
    orders_cancelled = Column(Integer, default=0)

    # Delivery metrics
    average_lead_time_days = Column(Float, nullable=True)
    on_time_delivery_rate = Column(Float, nullable=True)

    # Quality metrics
    items_received = Column(Integer, default=0)
    items_rejected = Column(Integer, default=0)
    items_returned = Column(Integer, default=0)
    quality_rating = Column(Float, nullable=True)  # 1-5

    # Fulfillment
    fill_rate = Column(Float, nullable=True)  # % of order fulfilled

    # Financial
    total_spend = Column(Numeric(12, 2), default=0)
    average_order_value = Column(Numeric(10, 2), nullable=True)

    # Calculated score
    overall_score = Column(Float, nullable=True)  # Weighted average

    # Audit
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    supplier = relationship("Supplier")

    __table_args__ = (
        Index('ix_supplier_perf_period', 'supplier_id', 'period_start', 'period_end'),
        UniqueConstraint('supplier_id', 'period_start', 'period_end', name='uq_supplier_period'),
    )
