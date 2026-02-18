"""
V3.1 Database Models - Complete Enterprise Features
Models for Multi-Location, Payroll, Integrations, Benchmarking, Hardware, Support
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Numeric, Text, JSON, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum

# Re-export models defined in other modules but expected here by services
from app.models.location import Location
from app.models.hardware import Integration


# ==================== MULTI-LOCATION MODELS ====================

class LocationStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TEMPORARILY_CLOSED = "temporarily_closed"
    COMING_SOON = "coming_soon"



class LocationGroup(Base):
    """Group of locations (by region, franchise owner, etc.)"""
    __tablename__ = "location_groups"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    group_type = Column(String(50), index=True)  # region, franchise, brand
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("LocationGroupMember", back_populates="group")


class LocationGroupMember(Base):
    """Location membership in groups"""
    __tablename__ = "location_group_members"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey('location_groups.id'), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=False, index=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("LocationGroup", back_populates="members")
    location = relationship("Location", backref="group_memberships")


class LocationStaffAssignment(Base):
    """Staff assignment to locations"""
    __tablename__ = "location_staff_assignments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey('staff_users.id'), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    is_primary = Column(Boolean, default=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    location = relationship("Location", backref="staff_assignments")
    staff = relationship("StaffUser", backref="location_assignments")


class InventoryTransfer(Base):
    """Inventory transfers between locations"""
    __tablename__ = "inventory_transfers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    transfer_code = Column(String(50), unique=True, nullable=False, index=True)
    from_location_id = Column(Integer, ForeignKey('locations.id'), nullable=False, index=True)
    to_location_id = Column(Integer, ForeignKey('locations.id'), nullable=False, index=True)
    status = Column(String(20), default="pending", index=True)  # pending, shipped, received, cancelled
    notes = Column(Text)

    shipped_at = Column(DateTime(timezone=True))
    received_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey('staff_users.id'))

    items = relationship("InventoryTransferItem", back_populates="transfer")
    from_location = relationship("Location", foreign_keys=[from_location_id], backref="transfers_out")
    to_location = relationship("Location", foreign_keys=[to_location_id], backref="transfers_in")
    creator = relationship("StaffUser", backref="created_transfers")


class InventoryTransferItem(Base):
    """Items in inventory transfer"""
    __tablename__ = "inventory_transfer_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(Integer, ForeignKey('inventory_transfers.id'), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey('stock_items.id'), nullable=False, index=True)
    quantity_sent = Column(Numeric(10, 3), nullable=False)
    quantity_received = Column(Numeric(10, 3))
    unit = Column(String(20))
    unit_cost = Column(Numeric(10, 2))

    transfer = relationship("InventoryTransfer", back_populates="items")
    stock_item = relationship("StockItem", backref="transfer_items")


# ==================== PAYROLL MODELS ====================

class EmployeePayroll(Base):
    """Employee payroll configuration"""
    __tablename__ = "employee_payroll"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey('staff_users.id'), unique=True, nullable=False, index=True)

    # Pay configuration
    pay_rate = Column(Numeric(10, 2), nullable=False)
    pay_type = Column(String(20), default="hourly")  # hourly, salary
    pay_frequency = Column(String(20), default="monthly")  # weekly, biweekly, semi_monthly, monthly
    payment_method = Column(String(20), default="direct_deposit")  # direct_deposit, check, cash

    # Bank details (encrypted in production)
    bank_name = Column(String(200))
    iban = Column(String(50))
    bic = Column(String(20))
    account_holder = Column(String(200))

    # Tax info
    tax_id = Column(String(50))  # Bulgarian EGN/EIK
    tax_class = Column(String(20))

    # Status
    status = Column(String(20), default="active", index=True)
    start_date = Column(Date)
    end_date = Column(Date)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    staff = relationship("StaffUser", backref="payroll_config")
    deductions = relationship("PayrollDeduction", back_populates="employee_payroll")
    pay_stubs = relationship("PayStub", back_populates="employee_payroll")


class PayrollDeduction(Base):
    """Payroll deductions (taxes, benefits, etc.)"""
    __tablename__ = "payroll_deductions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    employee_payroll_id = Column(Integer, ForeignKey('employee_payroll.id'), nullable=False, index=True)
    deduction_type = Column(String(50), nullable=False, index=True)  # tax, insurance, pension, other
    description = Column(String(200))
    amount = Column(Numeric(10, 2), nullable=False)
    is_percentage = Column(Boolean, default=False)
    is_pretax = Column(Boolean, default=True)
    frequency = Column(String(20), default="per_paycheck")
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee_payroll = relationship("EmployeePayroll", back_populates="deductions")


class PayStub(Base):
    """Individual pay stub"""
    __tablename__ = "pay_stubs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    stub_code = Column(String(50), unique=True, nullable=False, index=True)
    payroll_run_id = Column(Integer, ForeignKey('payroll_runs.id'), nullable=False, index=True)
    employee_payroll_id = Column(Integer, ForeignKey('employee_payroll.id'), nullable=False, index=True)

    # Hours
    regular_hours = Column(Numeric(8, 2))
    overtime_hours = Column(Numeric(8, 2))

    # Earnings
    regular_pay = Column(Numeric(10, 2))
    overtime_pay = Column(Numeric(10, 2))
    tips = Column(Numeric(10, 2))
    bonuses = Column(Numeric(10, 2))
    gross_pay = Column(Numeric(10, 2))

    # Deductions & Taxes
    pretax_deductions = Column(Numeric(10, 2))
    social_security = Column(Numeric(10, 2))
    income_tax = Column(Numeric(10, 2))
    posttax_deductions = Column(Numeric(10, 2))
    total_deductions = Column(Numeric(10, 2))

    # Net
    net_pay = Column(Numeric(10, 2))

    # Payment
    payment_method = Column(String(20))
    payment_reference = Column(String(100))
    paid_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    payroll_run = relationship("PayrollRun", backref="pay_stubs")
    employee_payroll = relationship("EmployeePayroll", back_populates="pay_stubs")


# ==================== SUPPORT MODELS ====================

class SupportTicket(Base):
    """Support ticket"""
    __tablename__ = "support_tickets"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    ticket_code = Column(String(50), unique=True, nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('staff_users.id'), nullable=False, index=True)

    subject = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(50), index=True)  # hardware, software, payments, etc.
    priority = Column(String(20), default="medium", index=True)  # critical, high, medium, low
    status = Column(String(20), default="open", index=True)  # open, in_progress, waiting, resolved, closed

    # Assignment
    assigned_to = Column(Integer)
    assigned_at = Column(DateTime(timezone=True))

    # SLA tracking
    first_response_due = Column(DateTime(timezone=True))
    resolution_due = Column(DateTime(timezone=True))
    first_response_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))

    # Resolution
    resolution_notes = Column(Text)
    satisfaction_rating = Column(Integer)  # 1-5
    satisfaction_feedback = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="support_tickets")
    user = relationship("StaffUser", backref="support_tickets")
    messages = relationship("SupportTicketMessage", back_populates="ticket")

    __table_args__ = (
        Index('idx_support_tickets_venue', 'venue_id'),
        Index('idx_support_tickets_status', 'status'),
        Index('idx_support_tickets_priority', 'priority'),
        {'extend_existing': True},
    )


class SupportTicketMessage(Base):
    """Message in support ticket"""
    __tablename__ = "support_ticket_messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('support_tickets.id'), nullable=False, index=True)
    sender_type = Column(String(20))  # customer, support
    sender_id = Column(Integer)
    content = Column(Text, nullable=False)
    attachments = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("SupportTicket", back_populates="messages")


class KnowledgeBaseArticle(Base):
    """Knowledge base article"""
    __tablename__ = "knowledge_base_articles"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    article_code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), index=True)
    tags = Column(JSON)
    status = Column(String(20), default="published", index=True)  # draft, published, archived
    views = Column(Integer, default=0)
    helpful_votes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ==================== HARDWARE MODELS ====================

class HardwareDevice(Base):
    """Hardware device registry"""
    __tablename__ = "hardware_devices"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    device_code = Column(String(50), unique=True, nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey('locations.id'), index=True)

    sku = Column(String(50), nullable=False)
    device_type = Column(String(50), nullable=False, index=True)  # pos_terminal, handheld, kds, printer
    name = Column(String(200), nullable=False)
    serial_number = Column(String(100), index=True)

    # Status
    status = Column(String(20), default="online", index=True)  # online, offline, error, maintenance
    last_seen = Column(DateTime(timezone=True))

    # Firmware
    firmware_version = Column(String(50))
    firmware_update_available = Column(Boolean, default=False)

    # Warranty
    warranty_expires = Column(Date)

    # Location within venue
    physical_location = Column(String(200))  # "Front Counter", "Kitchen", etc.

    installed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="hardware_devices")
    location = relationship("Location", backref="hardware_devices")
    maintenance_logs = relationship("HardwareMaintenanceLog", back_populates="device")


class HardwareMaintenanceLog(Base):
    """Hardware maintenance history"""
    __tablename__ = "hardware_maintenance_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey('hardware_devices.id'), nullable=False, index=True)
    maintenance_type = Column(String(50), index=True)  # firmware_update, repair, replacement
    description = Column(Text)
    performed_by = Column(String(200))
    cost = Column(Numeric(10, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("HardwareDevice", back_populates="maintenance_logs")


class HardwareOrder(Base):
    """Hardware purchase order"""
    __tablename__ = "hardware_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String(50), unique=True, nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False, index=True)

    status = Column(String(20), default="pending", index=True)  # pending, confirmed, shipped, delivered

    subtotal = Column(Numeric(10, 2))
    shipping = Column(Numeric(10, 2))
    tax = Column(Numeric(10, 2))
    total = Column(Numeric(10, 2))

    shipping_address = Column(JSON)
    tracking_number = Column(String(100))

    ordered_at = Column(DateTime(timezone=True), server_default=func.now())
    shipped_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))

    venue = relationship("Venue", backref="hardware_orders")
    items = relationship("HardwareOrderItem", back_populates="order")


class HardwareOrderItem(Base):
    """Items in hardware order"""
    __tablename__ = "hardware_order_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('hardware_orders.id'), nullable=False, index=True)
    sku = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)

    order = relationship("HardwareOrder", back_populates="items")


# ==================== BENCHMARKING MODELS ====================

class BenchmarkGoal(Base):
    """Benchmark goals for venue"""
    __tablename__ = "benchmark_goals"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False, index=True)
    metric = Column(String(100), nullable=False, index=True)
    baseline_value = Column(Numeric(15, 4))
    target_value = Column(Numeric(15, 4), nullable=False)
    current_value = Column(Numeric(15, 4))
    target_date = Column(Date, nullable=False)
    status = Column(String(20), default="in_progress", index=True)  # in_progress, achieved, missed
    achieved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="benchmark_goals")


class BenchmarkSnapshot(Base):
    """Historical benchmark snapshots"""
    __tablename__ = "benchmark_snapshots"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    metrics = Column(JSON, nullable=False)  # All metrics as of this date
    industry_comparison = Column(JSON)  # Comparison to industry averages
    regional_comparison = Column(JSON)  # Comparison to regional averages
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="benchmark_snapshots")

    __table_args__ = (
        Index('idx_benchmark_snapshots_venue_date', 'venue_id', 'snapshot_date'),
        {'extend_existing': True},
    )
