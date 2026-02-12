"""
Enhanced Inventory & Supply Chain Models
Complete implementation for Menu, Recipe, Stock, Supplier, Purchase Order management
Industry-leading features beyond Toast, TouchBistro, iiko, Oracle, NCR
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Numeric, Date, Index, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.db.base import Base


# =============================================================================
# ENUMS
# =============================================================================

class MenuVersionStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class RecipeStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DISCONTINUED = "discontinued"


class StockAdjustmentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TransferStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    MATCHED = "matched"
    DISPUTED = "disputed"
    PAID = "paid"
    CANCELLED = "cancelled"


# =============================================================================
# MENU MANAGEMENT - ENHANCED
# =============================================================================

class MenuItemVersionHistory(Base):
    """Track per-menu-item changes with full audit trail"""
    __tablename__ = "menu_item_version_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    version_number = Column(Integer, nullable=False)

    # Change tracking
    change_type = Column(String(30), nullable=False)  # created, updated, price_changed, restore
    previous_data = Column(JSON, nullable=True)  # Snapshot of item before change
    new_data = Column(JSON, nullable=True)  # Snapshot of item after change
    change_reason = Column(Text, nullable=True)

    # Audit
    changed_by_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    menu_item = relationship("MenuItem", backref="enhanced_version_history")

    __table_args__ = (
        Index('ix_menu_item_version_history_menu_item_id', 'menu_item_id'),
        Index('ix_menu_item_version_history_created_at', 'created_at'),
    )


class MenuVersionHistory(Base):
    """Track all menu version changes with full audit"""
    __tablename__ = "menu_version_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    menu_version_id = Column(Integer, ForeignKey("menu_versions.id"), nullable=False)

    # Status tracking
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)

    # Change details
    change_type = Column(String(30), nullable=False)  # created, updated, published, archived
    change_description = Column(Text, nullable=True)
    changes_json = Column(JSON, nullable=True)  # Detailed diff of changes

    # Audit
    changed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Approval
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    venue = relationship("Venue", backref="menu_version_history")

    __table_args__ = (
        Index('ix_menu_version_history_venue_id', 'venue_id'),
        Index('ix_menu_version_history_changed_at', 'changed_at'),
    )


class MenuSchedule(Base):
    """Schedule menus for specific times/days"""
    __tablename__ = "menu_schedules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    menu_version_id = Column(Integer, ForeignKey("menu_versions.id"), nullable=False)

    name = Column(String(100), nullable=False)

    # Schedule type
    schedule_type = Column(String(20), nullable=False)  # recurring, one_time, date_range

    # For recurring
    days_of_week = Column(JSON, nullable=True)  # [0,1,2,3,4,5,6] - Monday=0
    start_time = Column(String(5), nullable=True)  # "11:00"
    end_time = Column(String(5), nullable=True)  # "14:00"

    # For date ranges
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Priority (higher wins)
    priority = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="menu_schedules")

    __table_args__ = (
        Index('ix_menu_schedules_venue_id', 'venue_id'),
        Index('ix_menu_schedules_is_active', 'is_active'),
    )


class MenuItemNutrition(Base):
    """Detailed nutrition information per menu item"""
    __tablename__ = "menu_item_nutrition"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, unique=True)

    # Calories
    calories = Column(Float, nullable=True)
    calories_from_fat = Column(Float, nullable=True)

    # Macros (grams)
    total_fat = Column(Float, nullable=True)
    saturated_fat = Column(Float, nullable=True)
    trans_fat = Column(Float, nullable=True)
    cholesterol = Column(Float, nullable=True)  # mg
    sodium = Column(Float, nullable=True)  # mg
    total_carbohydrates = Column(Float, nullable=True)
    dietary_fiber = Column(Float, nullable=True)
    sugars = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)

    # Vitamins (% daily value)
    vitamin_a = Column(Float, nullable=True)
    vitamin_c = Column(Float, nullable=True)
    calcium = Column(Float, nullable=True)
    iron = Column(Float, nullable=True)

    # Serving info
    serving_size = Column(String(50), nullable=True)
    servings_per_item = Column(Float, default=1.0)

    # Source
    calculated_from_recipe = Column(Boolean, default=False)
    manually_entered = Column(Boolean, default=True)
    last_calculated = Column(DateTime(timezone=True), nullable=True)

    menu_item = relationship("MenuItem", backref="nutrition")


class MenuItemAllergen(Base):
    """Detailed allergen tracking"""
    __tablename__ = "menu_item_allergens"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)

    allergen_type = Column(String(50), nullable=False)  # gluten, dairy, nuts, etc.
    severity = Column(String(20), default="contains")  # contains, may_contain, free_from
    notes = Column(String(200), nullable=True)

    # Source tracking
    from_ingredient_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)
    manually_added = Column(Boolean, default=False)

    menu_item = relationship("MenuItem", backref="allergen_details")

    __table_args__ = (
        UniqueConstraint('menu_item_id', 'allergen_type', name='uq_menu_allergen'),
    )


class MenuItemBundle(Base):
    """Bundle/combo items with component tracking"""
    __tablename__ = "menu_item_bundles"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    bundle_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    component_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)

    quantity = Column(Integer, default=1)
    is_required = Column(Boolean, default=True)
    max_quantity = Column(Integer, nullable=True)  # For customizable bundles

    # Price adjustments
    price_adjustment = Column(Float, default=0.0)  # Discount/surcharge

    sort_order = Column(Integer, default=0)

    bundle_item = relationship("MenuItem", foreign_keys=[bundle_item_id], backref="bundle_components")
    component_item = relationship("MenuItem", foreign_keys=[component_item_id])


# =============================================================================
# RECIPE MANAGEMENT - COMPREHENSIVE
# =============================================================================

class RecipeVersion(Base):
    """Version control for recipes"""
    __tablename__ = "recipe_versions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)

    version_number = Column(Integer, nullable=False)

    # Snapshot of recipe at this version
    yield_quantity = Column(Numeric(10, 3), nullable=False)
    yield_unit = Column(String(20), nullable=False)
    preparation_time = Column(Integer, nullable=True)
    cook_time = Column(Integer, nullable=True)
    total_time = Column(Integer, nullable=True)

    # Ingredients snapshot
    ingredients_snapshot = Column(JSON, nullable=False)

    # Instructions snapshot
    instructions_snapshot = Column(JSON, nullable=True)

    # Cost at this version
    total_cost = Column(Float, nullable=True)
    cost_per_portion = Column(Float, nullable=True)

    # Status
    status = Column(String(20), default="active")

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)

    recipe = relationship("Recipe", backref="versions")

    __table_args__ = (
        UniqueConstraint('recipe_id', 'version_number', name='uq_recipe_version'),
    )


class RecipeInstruction(Base):
    """Detailed recipe instructions with step tracking"""
    __tablename__ = "recipe_instructions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)

    step_number = Column(Integer, nullable=False)
    instruction_text = Column(JSON, nullable=False)  # Multilingual

    # Timing
    estimated_time_minutes = Column(Integer, nullable=True)

    # Equipment
    equipment_needed = Column(JSON, nullable=True)  # ["oven", "whisk"]

    # Temperature
    temperature_celsius = Column(Float, nullable=True)
    temperature_fahrenheit = Column(Float, nullable=True)

    # Media
    image_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)

    # Tips
    tips = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)

    recipe = relationship("Recipe", backref="detailed_instructions")

    __table_args__ = (
        UniqueConstraint('recipe_id', 'step_number', name='uq_recipe_step'),
    )


class RecipeSubRecipe(Base):
    """Sub-recipes (recipes within recipes)"""
    __tablename__ = "recipe_sub_recipes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    parent_recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    child_recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)

    quantity = Column(Numeric(10, 3), nullable=False)  # How much of sub-recipe to use
    unit = Column(String(20), nullable=False)

    # When to prepare
    prep_stage = Column(String(20), nullable=True)  # "before", "during", "ahead"
    can_prep_ahead_days = Column(Integer, nullable=True)

    notes = Column(Text, nullable=True)

    parent_recipe = relationship("Recipe", foreign_keys=[parent_recipe_id], backref="sub_recipes")
    child_recipe = relationship("Recipe", foreign_keys=[child_recipe_id])

    __table_args__ = (
        UniqueConstraint('parent_recipe_id', 'child_recipe_id', name='uq_recipe_subrecipe'),
    )


class RecipeYieldVariation(Base):
    """Pre-calculated recipe scales for common yields"""
    __tablename__ = "recipe_yield_variations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)

    variation_name = Column(String(100), nullable=False)  # "Small batch", "Party size"
    target_yield = Column(Numeric(10, 3), nullable=False)
    scale_factor = Column(Numeric(10, 4), nullable=False)

    # Adjusted ingredients
    scaled_ingredients = Column(JSON, nullable=False)

    # Adjusted times (may not scale linearly)
    adjusted_prep_time = Column(Integer, nullable=True)
    adjusted_cook_time = Column(Integer, nullable=True)

    # Cost
    total_cost = Column(Float, nullable=True)
    cost_per_portion = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    recipe = relationship("Recipe", backref="yield_variations")


class RecipeCostHistory(Base):
    """Track recipe cost changes over time"""
    __tablename__ = "recipe_cost_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)

    recorded_date = Column(Date, nullable=False)

    # Costs
    ingredient_cost = Column(Float, nullable=False)
    labor_cost = Column(Float, nullable=True)
    overhead_cost = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=False)
    cost_per_portion = Column(Float, nullable=False)

    # Selling price context
    menu_price = Column(Float, nullable=True)
    food_cost_percent = Column(Float, nullable=True)

    # Change from previous
    previous_cost = Column(Float, nullable=True)
    cost_change_amount = Column(Float, nullable=True)
    cost_change_percent = Column(Float, nullable=True)

    # What changed
    cost_drivers = Column(JSON, nullable=True)  # [{ingredient, old_cost, new_cost}]

    recipe = relationship("Recipe", backref="cost_history")

    __table_args__ = (
        Index('ix_recipe_cost_history', 'recipe_id', 'recorded_date'),
    )


# =============================================================================
# STOCK/INVENTORY MANAGEMENT - ADVANCED
# =============================================================================

class EnhancedWarehouse(Base):
    """Enhanced warehouse with advanced features (extends basic Warehouse)"""
    __tablename__ = "enhanced_warehouses"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    base_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)  # Link to basic warehouse

    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)

    # Location
    address = Column(String(500), nullable=True)

    # Type
    warehouse_type = Column(String(30), nullable=False)  # main, satellite, cold_storage, dry_storage

    # Capacity
    total_capacity = Column(Float, nullable=True)
    capacity_unit = Column(String(20), nullable=True)  # sqft, pallets

    # Contact
    manager_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    phone = Column(String(20), nullable=True)

    # Operational
    is_active = Column(Boolean, default=True)
    accepts_deliveries = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    auto_replenish = Column(Boolean, default=False)
    min_stock_level_pct = Column(Numeric(5, 2), default=20)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="enhanced_warehouses_list")

    __table_args__ = (
        UniqueConstraint('venue_id', 'code', name='uq_enhanced_warehouse_code'),
        Index('ix_enhanced_warehouses_venue_id', 'venue_id'),
    )


class EnhancedWarehouseStock(Base):
    """Enhanced stock levels per warehouse with advanced tracking"""
    __tablename__ = "enhanced_warehouse_stock"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("enhanced_warehouses.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Quantities
    quantity = Column(Numeric(12, 4), default=0)
    reserved_quantity = Column(Numeric(12, 4), default=0)  # Reserved for orders
    available_quantity = Column(Numeric(12, 4), default=0)  # quantity - reserved

    # Location within warehouse
    bin_location = Column(String(50), nullable=True)
    zone = Column(String(50), nullable=True)

    # Par levels for this location
    min_quantity = Column(Numeric(12, 4), nullable=True)
    max_quantity = Column(Numeric(12, 4), nullable=True)
    reorder_point = Column(Numeric(12, 4), nullable=True)
    reorder_quantity = Column(Numeric(12, 4), nullable=True)

    last_counted = Column(DateTime(timezone=True), nullable=True)
    last_movement = Column(DateTime(timezone=True), nullable=True)

    warehouse = relationship("EnhancedWarehouse", backref="stock_levels")
    stock_item = relationship("StockItem", backref="enhanced_warehouse_levels")

    __table_args__ = (
        UniqueConstraint('warehouse_id', 'stock_item_id', name='uq_enhanced_warehouse_stock'),
    )


class EnhancedStockBatch(Base):
    """Enhanced Batch/Lot tracking for FIFO, expiry management"""
    __tablename__ = "enhanced_stock_batches"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("enhanced_warehouses.id"), nullable=True)

    batch_number = Column(String(100), nullable=False)
    lot_number = Column(String(100), nullable=True)

    # Quantities
    initial_quantity = Column(Numeric(12, 4), nullable=False)
    current_quantity = Column(Numeric(12, 4), nullable=False)

    # Dates
    manufacture_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    received_date = Column(Date, nullable=False)

    # Cost
    unit_cost = Column(Numeric(12, 4), nullable=True)

    # Source
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)

    # Status
    status = Column(String(20), default="active")  # active, depleted, expired, quarantine

    # Quality
    quality_status = Column(String(20), default="passed")  # passed, failed, pending
    quality_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stock_item = relationship("StockItem", backref="enhanced_batches")

    __table_args__ = (
        Index('ix_enhanced_batch_expiry', 'stock_item_id', 'expiry_date'),
        Index('ix_enhanced_batch_number', 'batch_number'),
    )


class EnhancedStockTransfer(Base):
    """Enhanced inter-warehouse transfers with full tracking"""
    __tablename__ = "enhanced_stock_transfers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    transfer_number = Column(String(50), unique=True, nullable=False)

    # Locations
    from_warehouse_id = Column(Integer, ForeignKey("enhanced_warehouses.id"), nullable=False)
    to_warehouse_id = Column(Integer, ForeignKey("enhanced_warehouses.id"), nullable=False)

    # Status
    status = Column(String(20), default="draft")  # TransferStatus

    # Dates
    requested_date = Column(DateTime(timezone=True), server_default=func.now())
    shipped_date = Column(DateTime(timezone=True), nullable=True)
    received_date = Column(DateTime(timezone=True), nullable=True)
    expected_date = Column(Date, nullable=True)

    # Staff
    requested_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    shipped_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    received_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Reason
    reason = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    venue = relationship("Venue", backref="enhanced_stock_transfers")
    from_warehouse = relationship("EnhancedWarehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("EnhancedWarehouse", foreign_keys=[to_warehouse_id])
    items = relationship("EnhancedStockTransferItem", back_populates="transfer", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_enhanced_stock_transfers_venue_id', 'venue_id'),
        Index('ix_enhanced_stock_transfers_status', 'status'),
    )


class EnhancedStockTransferItem(Base):
    """Items in an enhanced stock transfer"""
    __tablename__ = "enhanced_stock_transfer_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(Integer, ForeignKey("enhanced_stock_transfers.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Quantities
    quantity_requested = Column(Numeric(12, 4), nullable=False)
    quantity_shipped = Column(Numeric(12, 4), nullable=True)
    quantity_received = Column(Numeric(12, 4), nullable=True)

    # Batch tracking (optional)
    batch_id = Column(Integer, ForeignKey("enhanced_stock_batches.id"), nullable=True)

    # Variance
    variance = Column(Numeric(12, 4), nullable=True)
    variance_reason = Column(String(100), nullable=True)

    transfer = relationship("EnhancedStockTransfer", back_populates="items")
    stock_item = relationship("StockItem", backref="enhanced_transfer_items")


class EnhancedStockAdjustment(Base):
    """Enhanced stock adjustments with approval workflow"""
    __tablename__ = "enhanced_stock_adjustments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("enhanced_warehouses.id"), nullable=True)

    adjustment_number = Column(String(50), unique=True, nullable=False)

    # Type
    adjustment_type = Column(String(30), nullable=False)  # count_variance, damage, theft, spoilage, found, correction

    # Status
    status = Column(String(20), default="pending")  # StockAdjustmentStatus

    # Totals
    total_items = Column(Integer, default=0)
    total_value_impact = Column(Float, default=0.0)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Approval
    requires_approval = Column(Boolean, default=True)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    notes = Column(Text, nullable=True)

    venue = relationship("Venue", backref="enhanced_stock_adjustments")
    warehouse = relationship("EnhancedWarehouse")
    items = relationship("EnhancedStockAdjustmentItem", back_populates="adjustment", cascade="all, delete-orphan")


class EnhancedStockAdjustmentItem(Base):
    """Items in an enhanced stock adjustment"""
    __tablename__ = "enhanced_stock_adjustment_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    adjustment_id = Column(Integer, ForeignKey("enhanced_stock_adjustments.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Quantities
    system_quantity = Column(Numeric(12, 4), nullable=False)
    counted_quantity = Column(Numeric(12, 4), nullable=False)
    adjustment_quantity = Column(Numeric(12, 4), nullable=False)  # counted - system

    # Cost impact
    unit_cost = Column(Numeric(12, 4), nullable=True)
    value_impact = Column(Numeric(12, 4), nullable=True)

    # Reason per item
    reason = Column(String(100), nullable=True)

    # Batch (if applicable)
    batch_id = Column(Integer, ForeignKey("stock_batches.id"), nullable=True)

    adjustment = relationship("EnhancedStockAdjustment", back_populates="items")
    stock_item = relationship("StockItem", backref="enhanced_adjustment_items")


class EnhancedStockReservation(Base):
    """Enhanced stock reservation for pending orders"""
    __tablename__ = "enhanced_stock_reservations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("enhanced_warehouses.id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("stock_batches.id"), nullable=True)

    # What it's reserved for
    reservation_type = Column(String(30), nullable=False)  # order, production, event
    reference_type = Column(String(30), nullable=True)  # order, production_order
    reference_id = Column(Integer, nullable=True)

    # Quantity
    quantity = Column(Numeric(12, 4), nullable=False)

    # Timing
    reserved_at = Column(DateTime(timezone=True), server_default=func.now())
    reserved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(20), default="active")  # active, fulfilled, expired, cancelled
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    stock_item = relationship("StockItem", backref="enhanced_reservations")
    warehouse = relationship("EnhancedWarehouse")


# =============================================================================
# SUPPLIER MANAGEMENT - ENHANCED
# =============================================================================

class SupplierContact(Base):
    """Multiple contacts per supplier"""
    __tablename__ = "supplier_contacts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)

    contact_name = Column(String(200), nullable=False)
    role = Column(String(100), nullable=True)  # Sales Rep, Account Manager, etc.

    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    mobile = Column(String(50), nullable=True)

    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    notes = Column(Text, nullable=True)

    supplier = relationship("Supplier", backref="contacts")


class SupplierPriceList(Base):
    """Supplier price lists with effective dates"""
    __tablename__ = "supplier_price_lists"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)

    name = Column(String(100), nullable=False)

    # Validity
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)

    # Currency
    currency = Column(String(3), default="BGN")

    # Status
    is_active = Column(Boolean, default=True)

    # Source
    source_document = Column(String(255), nullable=True)  # File path
    uploaded_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    supplier = relationship("Supplier", backref="price_lists")
    items = relationship("SupplierPriceListItem", back_populates="price_list", cascade="all, delete-orphan")


class SupplierPriceListItem(Base):
    """Items in a supplier price list"""
    __tablename__ = "supplier_price_list_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    price_list_id = Column(Integer, ForeignKey("supplier_price_lists.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)

    # Supplier's info
    supplier_sku = Column(String(100), nullable=True)
    supplier_product_name = Column(String(300), nullable=False)
    supplier_description = Column(Text, nullable=True)

    # Pricing
    unit_price = Column(Numeric(12, 4), nullable=False)
    minimum_order_quantity = Column(Numeric(12, 4), nullable=True)

    # Pack size
    pack_size = Column(Numeric(12, 4), nullable=True)
    pack_unit = Column(String(20), nullable=True)
    price_per_unit = Column(Numeric(12, 4), nullable=True)  # Calculated

    # Volume discounts
    volume_discounts = Column(JSON, nullable=True)  # [{qty: 10, discount_percent: 5}]

    # Lead time
    lead_time_days = Column(Integer, nullable=True)

    price_list = relationship("SupplierPriceList", back_populates="items")
    stock_item = relationship("StockItem", backref="supplier_price_list_items")


class SupplierRating(Base):
    """Supplier ratings and reviews"""
    __tablename__ = "supplier_ratings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Rating period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Scores (1-5)
    quality_score = Column(Float, nullable=True)
    delivery_score = Column(Float, nullable=True)
    pricing_score = Column(Float, nullable=True)
    communication_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)

    # Metrics used
    orders_count = Column(Integer, default=0)
    on_time_count = Column(Integer, default=0)
    issues_count = Column(Integer, default=0)

    # Comments
    comments = Column(Text, nullable=True)

    rated_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    rated_at = Column(DateTime(timezone=True), server_default=func.now())

    supplier = relationship("Supplier", backref="ratings")


# =============================================================================
# PURCHASE ORDER - ADVANCED
# =============================================================================

class PurchaseOrderTemplate(Base):
    """Templates for recurring orders"""
    __tablename__ = "purchase_order_templates"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)

    template_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Items
    items = Column(JSON, nullable=False)  # [{stock_item_id, quantity, unit, notes}]

    # Schedule
    is_scheduled = Column(Boolean, default=False)
    schedule_frequency = Column(String(20), nullable=True)  # daily, weekly, biweekly, monthly
    schedule_day = Column(Integer, nullable=True)  # Day of week (0-6) or day of month (1-31)
    next_order_date = Column(Date, nullable=True)

    # Auto settings
    auto_create = Column(Boolean, default=False)
    auto_submit = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="po_templates")
    supplier = relationship("Supplier", backref="po_templates")


class PurchaseOrderApproval(Base):
    """Multi-level approval workflow"""
    __tablename__ = "purchase_order_approvals"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)

    # Approval level
    approval_level = Column(Integer, nullable=False)  # 1, 2, 3...
    approval_type = Column(String(30), nullable=False)  # manager, finance, director

    # Required approver
    required_role = Column(String(50), nullable=True)
    required_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, approved, rejected

    # Actual approval
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    comments = Column(Text, nullable=True)

    purchase_order = relationship("PurchaseOrder", backref="approval_history")


class SupplierInvoice(Base):
    """Supplier invoices for three-way matching"""
    __tablename__ = "supplier_invoices"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)

    invoice_number = Column(String(100), nullable=False)

    # Dates
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    received_date = Column(Date, nullable=True)

    # Amounts
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), nullable=False)

    # Currency
    currency = Column(String(3), default="BGN")

    # Linked PO
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # InvoiceStatus

    # Matching
    is_matched = Column(Boolean, default=False)
    match_status = Column(String(30), nullable=True)  # matched, partial_match, variance
    variance_amount = Column(Numeric(12, 2), nullable=True)
    variance_reason = Column(Text, nullable=True)

    # Payment
    payment_status = Column(String(20), default="unpaid")  # unpaid, partial, paid
    payment_date = Column(Date, nullable=True)
    payment_reference = Column(String(100), nullable=True)

    # File
    document_url = Column(String(500), nullable=True)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="supplier_invoices")
    supplier = relationship("Supplier", backref="supplier_invoices_enhanced")
    purchase_order = relationship("PurchaseOrder", backref="supplier_invoices")
    items = relationship("SupplierInvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('venue_id', 'supplier_id', 'invoice_number', name='uq_supplier_invoice'),
    )


class SupplierInvoiceItem(Base):
    """Line items on supplier invoices"""
    __tablename__ = "supplier_invoice_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("supplier_invoices.id"), nullable=False)

    # Item details
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)
    description = Column(String(300), nullable=False)

    # Quantities
    quantity = Column(Numeric(12, 4), nullable=False)
    unit = Column(String(20), nullable=True)
    unit_price = Column(Numeric(12, 4), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)

    # Matching to PO item
    po_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), nullable=True)

    # Variance
    expected_quantity = Column(Numeric(12, 4), nullable=True)
    expected_price = Column(Numeric(12, 4), nullable=True)
    quantity_variance = Column(Numeric(12, 4), nullable=True)
    price_variance = Column(Numeric(12, 4), nullable=True)

    invoice = relationship("SupplierInvoice", back_populates="items")


class GoodsReceivedNote(Base):
    """Goods Received Notes for receiving workflow"""
    __tablename__ = "goods_received_notes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    grn_number = Column(String(50), unique=True, nullable=False)

    # Source
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)

    # Delivery
    delivery_date = Column(DateTime(timezone=True), server_default=func.now())
    delivery_note_number = Column(String(100), nullable=True)
    carrier = Column(String(100), nullable=True)

    # Receiving
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    received_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)

    # Status
    status = Column(String(20), default="draft")  # draft, completed, disputed

    # Quality check
    quality_check_required = Column(Boolean, default=False)
    quality_check_completed = Column(Boolean, default=False)
    quality_check_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    quality_notes = Column(Text, nullable=True)

    # Totals
    total_items = Column(Integer, default=0)
    total_value = Column(Numeric(12, 2), default=0)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="goods_received_notes")
    supplier = relationship("Supplier", backref="goods_received_notes")
    items = relationship("GoodsReceivedNoteItem", back_populates="grn", cascade="all, delete-orphan")


class GoodsReceivedNoteItem(Base):
    """Items in a GRN"""
    __tablename__ = "goods_received_note_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    grn_id = Column(Integer, ForeignKey("goods_received_notes.id"), nullable=False)

    # Item
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)
    po_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), nullable=True)
    item_description = Column(String(300), nullable=False)

    # Quantities
    quantity_expected = Column(Numeric(12, 4), nullable=True)
    quantity_received = Column(Numeric(12, 4), nullable=False)
    quantity_accepted = Column(Numeric(12, 4), nullable=True)
    quantity_rejected = Column(Numeric(12, 4), nullable=True)

    # Unit
    unit = Column(String(20), nullable=True)

    # Batch/Lot
    batch_number = Column(String(100), nullable=True)
    expiry_date = Column(Date, nullable=True)

    # Quality
    quality_status = Column(String(20), default="accepted")  # accepted, rejected, quarantine
    rejection_reason = Column(String(200), nullable=True)

    # Storage
    bin_location = Column(String(50), nullable=True)

    # Value
    unit_cost = Column(Numeric(12, 4), nullable=True)

    grn = relationship("GoodsReceivedNote", back_populates="items")
    stock_item = relationship("StockItem", backref="grn_items")


class PurchaseOrderAnalytics(Base):
    """Pre-aggregated PO analytics"""
    __tablename__ = "purchase_order_analytics"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Period
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    period_date = Column(Date, nullable=False)

    # Order counts
    total_orders = Column(Integer, default=0)
    orders_by_status = Column(JSON, nullable=True)

    # Spending
    total_spend = Column(Float, default=0.0)
    spend_by_supplier = Column(JSON, nullable=True)
    spend_by_category = Column(JSON, nullable=True)

    # Efficiency
    avg_lead_time_days = Column(Float, nullable=True)
    on_time_delivery_rate = Column(Float, nullable=True)

    # Issues
    orders_with_issues = Column(Integer, default=0)
    total_variance_amount = Column(Float, default=0.0)

    # Top items
    top_items_by_spend = Column(JSON, nullable=True)
    top_items_by_quantity = Column(JSON, nullable=True)

    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="po_analytics")

    __table_args__ = (
        UniqueConstraint('venue_id', 'period_type', 'period_date', name='uq_po_analytics'),
    )
