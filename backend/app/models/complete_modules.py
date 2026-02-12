"""
Complete Missing Modules - Database Models
Adds all missing tables for production-grade POS system
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Numeric, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


# ==================== PRODUCTION MODULE ====================

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'), nullable=False)
    stock_item_id = Column(Integer, ForeignKey('stock_items.id'), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    unit = Column(String(20), nullable=False)
    cost_per_unit = Column(Numeric(10, 2))
    is_optional = Column(Boolean, default=False)
    substitutes = Column(JSON)  # Alternative ingredients
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    recipe = relationship("Recipe", backref="ingredients")
    stock_item = relationship("StockItem")
    
    __table_args__ = (
        Index('idx_recipe_ingredients_recipe', 'recipe_id'),
        Index('idx_recipe_ingredients_stock', 'stock_item_id'),
        {'extend_existing': True},
    )


class ProductionOrder(Base):
    __tablename__ = "production_orders"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False)
    recipe_id = Column(Integer, ForeignKey('recipes.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String(20), default='pending')  # pending, in_progress, completed, cancelled
    scheduled_for = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    produced_by = Column(Integer, ForeignKey('staff_users.id'))
    batch_number = Column(String(50))
    actual_cost = Column(Numeric(10, 2))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    venue = relationship("Venue")
    recipe = relationship("Recipe", backref="production_orders")
    producer = relationship("StaffUser")
    # Note: batches relationship removed - ProductionBatch in feature_models has different structure
    
    __table_args__ = (
        Index('idx_production_orders_venue', 'venue_id'),
        Index('idx_production_orders_status', 'status'),
        Index('idx_production_orders_scheduled', 'scheduled_for'),
    )


# ProductionBatch is defined in feature_models.py - import from there to avoid duplicate


# ==================== SERIAL/BATCH TRACKING MODULE ====================

class SerialNumber(Base):
    __tablename__ = "serial_numbers"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    stock_item_id = Column(Integer, ForeignKey('stock_items.id'), nullable=False)
    serial_number = Column(String(100), unique=True, nullable=False)
    batch_number = Column(String(50))
    manufacture_date = Column(Date)
    expiry_date = Column(Date)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'))
    purchase_order_id = Column(Integer, ForeignKey('purchase_orders.id'))
    received_date = Column(DateTime(timezone=True))
    warranty_months = Column(Integer)
    warranty_expires = Column(Date)
    status = Column(String(20), default='in_stock')  # in_stock, sold, returned, expired, destroyed
    current_location = Column(String(100))
    sold_to_customer_id = Column(Integer, ForeignKey('customers.id'))
    sold_date = Column(DateTime(timezone=True))
    order_id = Column(Integer, ForeignKey('orders.id'))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    stock_item = relationship("StockItem")
    supplier = relationship("Supplier")
    purchase_order = relationship("PurchaseOrder")
    customer = relationship("Customer")
    order = relationship("Order")
    history = relationship("SerialHistory", back_populates="serial_number", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_serial_numbers_serial', 'serial_number'),
        Index('idx_serial_numbers_status', 'status'),
        Index('idx_serial_numbers_expiry', 'expiry_date'),
    )


class BatchTracking(Base):
    __tablename__ = "batch_tracking"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    batch_number = Column(String(50), nullable=False)
    stock_item_id = Column(Integer, ForeignKey('stock_items.id'), nullable=False)
    quantity_received = Column(Integer, nullable=False)
    quantity_remaining = Column(Integer, nullable=False)
    manufacture_date = Column(Date)
    expiry_date = Column(Date)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'))
    received_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default='active')  # active, depleted, expired
    auto_writeoff = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    stock_item = relationship("StockItem")
    supplier = relationship("Supplier")
    
    __table_args__ = (
        Index('idx_batch_tracking_batch', 'batch_number'),
        Index('idx_batch_tracking_expiry', 'expiry_date'),
        Index('idx_batch_tracking_status', 'status'),
    )


class SerialHistory(Base):
    __tablename__ = "serial_history"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    serial_number_id = Column(Integer, ForeignKey('serial_numbers.id'), nullable=False)
    event_type = Column(String(50), nullable=False)  # received, sold, moved, returned, expired
    event_date = Column(DateTime(timezone=True), server_default=func.now())
    from_location = Column(String(100))
    to_location = Column(String(100))
    staff_id = Column(Integer, ForeignKey('staff_users.id'))
    customer_id = Column(Integer, ForeignKey('customers.id'))
    order_id = Column(Integer, ForeignKey('orders.id'))
    notes = Column(Text)
    
    # Relationships
    serial_number = relationship("SerialNumber", back_populates="history")
    staff = relationship("StaffUser")
    customer = relationship("Customer")
    order = relationship("Order")
    
    __table_args__ = (
        Index('idx_serial_history_serial', 'serial_number_id'),
        Index('idx_serial_history_event', 'event_type'),
        Index('idx_serial_history_date', 'event_date'),
    )


# ==================== SCALE MODULE ====================

class ScaleConfiguration(Base):
    __tablename__ = "scale_configurations"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False)
    scale_name = Column(String(100), nullable=False)
    scale_model = Column(String(100), nullable=False)
    connection_type = Column(String(20))  # serial, usb, network
    connection_string = Column(String(255))
    baudrate = Column(Integer)
    port = Column(String(50))
    ip_address = Column(String(50))
    label_format = Column(JSON)  # Label template
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    venue = relationship("Venue")
    scale_items = relationship("ScaleItem", back_populates="scale_config")
    
    __table_args__ = (
        Index('idx_scale_configs_venue', 'venue_id'),
    )


class ScaleItem(Base):
    __tablename__ = "scale_items"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    scale_config_id = Column(Integer, ForeignKey('scale_configurations.id'), nullable=False)
    menu_item_id = Column(Integer, ForeignKey('menu_items.id'), nullable=False)
    plu_code = Column(String(20), nullable=False)  # Price Look Up code
    unit_price = Column(Numeric(10, 2), nullable=False)
    tare_weight = Column(Numeric(10, 3))  # Container weight
    price_per = Column(String(10), default='kg')  # kg, lb, unit
    label_template = Column(String(50))
    barcode_format = Column(String(20))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    scale_config = relationship("ScaleConfiguration", back_populates="scale_items")
    menu_item = relationship("MenuItem")
    
    __table_args__ = (
        Index('idx_scale_items_plu', 'plu_code'),
        Index('idx_scale_items_menu', 'menu_item_id'),
    )


# ==================== SALES MONITOR MODULE ====================

class OperatorAction(Base):
    __tablename__ = "operator_actions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False)
    terminal_id = Column(String(50))
    staff_id = Column(Integer, ForeignKey('staff_users.id'), nullable=False)
    action_type = Column(String(50), nullable=False)  # login, logout, sale, void, discount, refund
    action_details = Column(JSON)
    order_id = Column(Integer, ForeignKey('orders.id'))
    amount = Column(Numeric(10, 2))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(50))
    flagged = Column(Boolean, default=False)  # Suspicious activity
    flag_reason = Column(Text)
    
    # Relationships
    venue = relationship("Venue")
    staff = relationship("StaffUser")
    order = relationship("Order")
    
    __table_args__ = (
        Index('idx_operator_actions_staff', 'staff_id'),
        Index('idx_operator_actions_type', 'action_type'),
        Index('idx_operator_actions_timestamp', 'timestamp'),
        Index('idx_operator_actions_flagged', 'flagged'),
    )


# ==================== COLLECTOR MODULE ====================

class CollectorDevice(Base):
    __tablename__ = "collector_devices"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    device_id = Column(String(50), unique=True, nullable=False)
    device_name = Column(String(100), nullable=False)
    device_model = Column(String(100))
    assigned_to_staff_id = Column(Integer, ForeignKey('staff_users.id'))
    venue_id = Column(Integer, ForeignKey('venues.id'))
    last_sync = Column(DateTime(timezone=True))
    battery_level = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    staff = relationship("StaffUser")
    venue = relationship("Venue")
    protocols = relationship("CollectorProtocol", back_populates="device")
    
    __table_args__ = (
        Index('idx_collector_devices_device_id', 'device_id'),
    )


class CollectorProtocol(Base):
    __tablename__ = "collector_protocols"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('collector_devices.id'), nullable=False)
    protocol_type = Column(String(20), nullable=False)  # delivery, transfer, inventory, return
    protocol_number = Column(String(50))
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False)
    staff_id = Column(Integer, ForeignKey('staff_users.id'), nullable=False)
    status = Column(String(20), default='pending')  # pending, synced, processed, cancelled
    items_data = Column(JSON, nullable=False)  # Item IDs and quantities
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    synced_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))
    
    # Relationships
    device = relationship("CollectorDevice", back_populates="protocols")
    venue = relationship("Venue")
    staff = relationship("StaffUser")
    
    __table_args__ = (
        Index('idx_collector_protocols_device', 'device_id'),
        Index('idx_collector_protocols_status', 'status'),
    )


# ==================== MPOS MODULE ====================

class MobileFiscalDevice(Base):
    __tablename__ = "mobile_fiscal_devices"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    device_id = Column(String(50), unique=True, nullable=False)
    device_name = Column(String(100), nullable=False)
    device_model = Column(String(100), nullable=False)
    serial_number = Column(String(100))
    connection_type = Column(String(20))  # bluetooth, wifi, usb
    assigned_to_staff_id = Column(Integer, ForeignKey('staff_users.id'))
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False)
    nra_registered = Column(Boolean, default=False)
    last_connected = Column(DateTime(timezone=True))
    battery_level = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    staff = relationship("StaffUser")
    venue = relationship("Venue")
    transactions = relationship("MobileTransaction", back_populates="device")
    
    __table_args__ = (
        Index('idx_mobile_fiscal_devices_device_id', 'device_id'),
        Index('idx_mobile_fiscal_devices_venue', 'venue_id'),
    )


class MobileTransaction(Base):
    __tablename__ = "mobile_transactions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('mobile_fiscal_devices.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    staff_id = Column(Integer, ForeignKey('staff_users.id'), nullable=False)
    fiscal_receipt_number = Column(String(50))
    transaction_type = Column(String(20))  # sale, refund
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(20))
    status = Column(String(20), default='pending')  # pending, completed, failed
    offline_mode = Column(Boolean, default=False)
    synced_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    device = relationship("MobileFiscalDevice", back_populates="transactions")
    order = relationship("Order")
    staff = relationship("StaffUser")
    
    __table_args__ = (
        Index('idx_mobile_transactions_device', 'device_id'),
        Index('idx_mobile_transactions_order', 'order_id'),
        Index('idx_mobile_transactions_status', 'status'),
    )


# ==================== PRINT SPOOLER MODULE ====================

class PrintQueue(Base):
    __tablename__ = "print_queue"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    queue_name = Column(String(100), nullable=False)
    printer_name = Column(String(100), nullable=False)
    printer_type = Column(String(20))  # receipt, fiscal, label, kitchen
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False)
    job_data = Column(JSON, nullable=False)
    priority = Column(Integer, default=5)
    status = Column(String(20), default='pending')  # pending, printing, completed, failed
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    printed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    
    # Relationships
    venue = relationship("Venue")
    
    __table_args__ = (
        Index('idx_print_queue_status', 'status'),
        Index('idx_print_queue_priority', 'priority'),
        Index('idx_print_queue_created', 'created_at'),
    )


# ==================== REMOTE WORKPLACE MODULE ====================

class RemoteSession(Base):
    __tablename__ = "remote_sessions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    session_token = Column(String(255), unique=True, nullable=False)
    staff_id = Column(Integer, ForeignKey('staff_users.id'), nullable=False)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False)
    connection_type = Column(String(20))  # lan, wan, vpn
    ip_address = Column(String(50))
    device_info = Column(JSON)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))
    active = Column(Boolean, default=True)
    
    # Relationships
    staff = relationship("StaffUser")
    venue = relationship("Venue")
    
    __table_args__ = (
        Index('idx_remote_sessions_token', 'session_token'),
        Index('idx_remote_sessions_active', 'active'),
    )


# ==================== ACCOUNTING EXPORT MODULE ====================

class AccountingExport(Base):
    __tablename__ = "accounting_exports"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False)
    export_type = Column(String(50), nullable=False)  # sales, purchases, inventory, payroll
    export_format = Column(String(50), nullable=False)  # xml, csv, json, excel
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    file_path = Column(String(255))
    file_size = Column(Integer)
    record_count = Column(Integer)
    status = Column(String(20), default='pending')  # pending, generated, exported, failed
    generated_by = Column(Integer, ForeignKey('staff_users.id'))
    generated_at = Column(DateTime(timezone=True))
    exported_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    venue = relationship("Venue")
    staff = relationship("StaffUser")
    
    __table_args__ = (
        Index('idx_accounting_exports_venue', 'venue_id'),
        Index('idx_accounting_exports_period', 'period_start', 'period_end'),
        Index('idx_accounting_exports_status', 'status'),
    )


# ==================== WASTE MANAGEMENT MODULE ====================

class WasteRecord(Base):
    __tablename__ = "waste_records"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False)
    stock_item_id = Column(Integer, ForeignKey('stock_items.id'), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False)
    unit = Column(String(20), nullable=False)
    reason = Column(String(50), nullable=False)  # expired, spoiled, damaged, overproduction, customer_return, spillage, theft, other
    cost = Column(Numeric(10, 2), nullable=False)
    batch_number = Column(String(50))
    recorded_by = Column(Integer, ForeignKey('staff_users.id'), nullable=False)
    notes = Column(Text)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    venue = relationship("Venue")
    stock_item = relationship("StockItem")
    staff = relationship("StaffUser")

    __table_args__ = (
        Index('idx_waste_records_venue', 'venue_id'),
        Index('idx_waste_records_stock_item', 'stock_item_id'),
        Index('idx_waste_records_reason', 'reason'),
        Index('idx_waste_records_date', 'recorded_at'),
        {'extend_existing': True}
    )


# ==================== STOCK COUNT MODULE ====================

class StockCount(Base):
    __tablename__ = "stock_counts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False)
    count_number = Column(String(50), nullable=False, unique=True)
    count_type = Column(String(20), nullable=False)  # full, partial, spot
    status = Column(String(20), default='draft')  # draft, in_progress, pending_review, approved, rejected
    location = Column(String(100))
    categories = Column(JSON)  # List of categories to count
    counted_by = Column(Integer, ForeignKey('staff_users.id'), nullable=False)
    approved_by = Column(Integer, ForeignKey('staff_users.id'))
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    approved_at = Column(DateTime(timezone=True))
    total_items = Column(Integer, default=0)
    variance_count = Column(Integer, default=0)
    variance_value = Column(Numeric(10, 2), default=0)
    notes = Column(Text)

    # Relationships
    venue = relationship("Venue")
    counter = relationship("StaffUser", foreign_keys=[counted_by])
    approver = relationship("StaffUser", foreign_keys=[approved_by])
    items = relationship("StockCountItem", back_populates="stock_count", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_stock_counts_venue', 'venue_id'),
        Index('idx_stock_counts_status', 'status'),
        Index('idx_stock_counts_date', 'started_at'),
        {'extend_existing': True}
    )


class StockCountItem(Base):
    __tablename__ = "stock_count_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    stock_count_id = Column(Integer, ForeignKey('stock_counts.id'), nullable=False)
    stock_item_id = Column(Integer, ForeignKey('stock_items.id'), nullable=False)
    system_quantity = Column(Numeric(10, 3), nullable=False)
    counted_quantity = Column(Numeric(10, 3))
    variance = Column(Numeric(10, 3))
    variance_cost = Column(Numeric(10, 2))
    unit = Column(String(20), nullable=False)
    counted_at = Column(DateTime(timezone=True))
    notes = Column(Text)

    # Relationships
    stock_count = relationship("StockCount", back_populates="items")
    stock_item = relationship("StockItem")

    __table_args__ = (
        Index('idx_stock_count_items_count', 'stock_count_id'),
        Index('idx_stock_count_items_stock', 'stock_item_id'),
        {'extend_existing': True}
    )
