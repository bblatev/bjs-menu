"""
BJS V6 Features - Database Models
==================================
Database models for Drive-Thru, Cloud Kitchen, Financial Management,
Delivery Aggregator, Franchise Management, NRA Tax Compliance, and HACCP.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum, Date, Time, Numeric, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime, date, time as dtime
from enum import Enum as PyEnum
from app.db.base import Base


# =====================================================
# DRIVE-THRU MODELS
# =====================================================

class LaneStatus(str, PyEnum):
    OPEN = "open"
    CLOSED = "closed"
    MAINTENANCE = "maintenance"


class VehicleStatus(str, PyEnum):
    AT_MENU = "at_menu"
    ORDERING = "ordering"
    AT_PAYMENT = "at_payment"
    AT_PICKUP = "at_pickup"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class DriveThruLane(Base):
    """Drive-thru lane configuration"""
    __tablename__ = "drive_thru_lanes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    lane_number = Column(Integer, nullable=False)
    lane_type = Column(String(20), default="standard")  # standard, express, preorder
    status = Column(String(20), default=LaneStatus.OPEN.value)

    # Stats (updated in real-time)
    queue_length = Column(Integer, default=0)
    avg_service_time_seconds = Column(Integer, default=180)
    total_vehicles_today = Column(Integer, default=0)
    revenue_today = Column(Numeric(10, 2), default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    venue = relationship("Venue", backref="drive_thru_lanes")
    vehicles = relationship("DriveThruVehicle", back_populates="lane")

    __table_args__ = (
        UniqueConstraint('venue_id', 'lane_number', name='uq_drive_thru_lane'),
        Index('idx_drive_thru_lane_venue', 'venue_id', 'status'),
    )


class DriveThruVehicle(Base):
    """Vehicle tracking in drive-thru"""
    __tablename__ = "drive_thru_vehicles"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    lane_id = Column(Integer, ForeignKey("drive_thru_lanes.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    license_plate = Column(String(20), nullable=True)
    customer_name = Column(String(100), nullable=True)
    status = Column(String(20), default=VehicleStatus.AT_MENU.value)
    is_preorder = Column(Boolean, default=False)

    # Timing
    entered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    order_started_at = Column(DateTime, nullable=True)
    order_completed_at = Column(DateTime, nullable=True)
    payment_at = Column(DateTime, nullable=True)
    pickup_at = Column(DateTime, nullable=True)
    exited_at = Column(DateTime, nullable=True)
    total_time_seconds = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    venue = relationship("Venue", backref="drive_thru_vehicles")
    lane = relationship("DriveThruLane", back_populates="vehicles")
    order = relationship("Order", backref="drive_thru_vehicle")

    __table_args__ = (
        Index('idx_drive_thru_vehicle_venue_status', 'venue_id', 'status'),
        Index('idx_drive_thru_vehicle_date', 'venue_id', 'entered_at'),
    )


class DriveThruOrderDisplay(Base):
    """Drive-thru order display data"""
    __tablename__ = "drive_thru_order_displays"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("drive_thru_vehicles.id"), nullable=False)

    items = Column(JSON, default=[])
    subtotal = Column(Numeric(10, 2), default=0)
    tax = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)
    payment_method = Column(String(20), nullable=True)
    status = Column(String(20), default="pending")

    ready_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    venue = relationship("Venue", backref="drive_thru_displays")
    vehicle = relationship("DriveThruVehicle", backref="display")


# =====================================================
# CLOUD KITCHEN / GHOST KITCHEN MODELS
# =====================================================

class BrandStatus(str, PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DISCONTINUED = "discontinued"


class StationStatus(str, PyEnum):
    IDLE = "idle"
    PREPARING = "preparing"
    BUSY = "busy"
    OFFLINE = "offline"


# VirtualBrand is defined in advanced_features.py - DO NOT define here


class CloudKitchenStation(Base):
    """Kitchen station for cloud kitchen operations"""
    __tablename__ = "cloud_kitchen_stations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    station_type = Column(String(50), nullable=False)  # grill, fryer, prep, assembly, packaging
    brands_assigned = Column(JSON, default=[])  # Brand IDs

    max_concurrent_orders = Column(Integer, default=5)
    current_orders = Column(Integer, default=0)
    status = Column(String(20), default=StationStatus.IDLE.value)

    staff_assigned = Column(JSON, default=[])  # Staff IDs
    equipment = Column(JSON, default=[])

    created_at = Column(DateTime, default=datetime.utcnow)

    venue = relationship("Venue", backref="cloud_kitchen_stations")

    __table_args__ = (
        Index('idx_cloud_station_venue', 'venue_id', 'station_type'),
    )


class VirtualBrandOrder(Base):
    """Orders for virtual brands"""
    __tablename__ = "virtual_brand_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey("virtual_brands.id"), nullable=False, index=True)

    platform = Column(String(50), nullable=False)  # glovo, wolt, etc.
    platform_order_id = Column(String(100), nullable=False)

    items = Column(JSON, default=[])
    station_assignments = Column(JSON, default={})  # item_id -> station_id

    total = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default="received")
    estimated_ready = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    venue = relationship("Venue", backref="virtual_brand_orders")
    brand = relationship("VirtualBrand", backref="orders")

    __table_args__ = (
        Index('idx_vb_order_venue_brand', 'venue_id', 'brand_id'),
        Index('idx_vb_order_platform', 'platform', 'platform_order_id'),
    )


# =====================================================
# FINANCIAL MANAGEMENT MODELS
# =====================================================

class ExpenseCategory(str, PyEnum):
    FOOD_COST = "food_cost"
    LABOR = "labor"
    RENT = "rent"
    UTILITIES = "utilities"
    MARKETING = "marketing"
    EQUIPMENT = "equipment"
    SUPPLIES = "supplies"
    INSURANCE = "insurance"
    LICENSES = "licenses"
    MAINTENANCE = "maintenance"
    OTHER = "other"


class FinancialExpense(Base):
    """Financial expense tracking"""
    __tablename__ = "financial_expenses"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="BGN")

    vendor = Column(String(200), nullable=True)
    invoice_number = Column(String(100), nullable=True)
    payment_method = Column(String(50), default="bank_transfer")
    expense_date = Column(Date, nullable=False)

    recurring = Column(Boolean, default=False)
    recurring_frequency = Column(String(20), nullable=True)  # weekly, monthly, yearly
    tax_deductible = Column(Boolean, default=True)
    receipt_url = Column(String(500), nullable=True)

    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    venue = relationship("Venue", backref="financial_expenses")
    created_by_user = relationship("StaffUser", foreign_keys=[created_by])

    __table_args__ = (
        Index('idx_expense_venue_date', 'venue_id', 'expense_date'),
        Index('idx_expense_category', 'venue_id', 'category'),
    )


# BankTransaction is defined elsewhere - commented out to avoid duplicate
# class BankTransaction(Base):
#     """Bank transaction for reconciliation"""
#     __tablename__ = "bank_transactions"

#     id = Column(Integer, primary_key=True, index=True)
#     venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

#     bank_account = Column(String(100), nullable=False)
#     transaction_type = Column(String(20), nullable=False)  # income, expense, transfer
#     amount = Column(Numeric(12, 2), nullable=False)
#     description = Column(Text, nullable=False)
#     reference = Column(String(100), nullable=True)
#     transaction_date = Column(Date, nullable=False)

#     reconciled = Column(Boolean, default=False)
#     matched_expense_id = Column(Integer, ForeignKey("financial_expenses.id"), nullable=True)
#     matched_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

#     imported_at = Column(DateTime, default=datetime.utcnow)

#     venue = relationship("Venue", backref="bank_transactions")
#     matched_expense = relationship("FinancialExpense", foreign_keys=[matched_expense_id])
#     matched_order = relationship("Order", foreign_keys=[matched_order_id])

#     __table_args__ = (
#         Index('idx_bank_txn_venue_date', 'venue_id', 'transaction_date'),
#         Index('idx_bank_txn_reconciled', 'venue_id', 'reconciled'),
#     )


class FinancialBudget(Base):
    """Budget settings per category"""
    __tablename__ = "financial_budgets"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    category = Column(String(50), nullable=False)
    monthly_budget = Column(Numeric(12, 2), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    venue = relationship("Venue", backref="financial_budgets")

    __table_args__ = (
        UniqueConstraint('venue_id', 'category', 'year', 'month', name='uq_budget'),
        Index('idx_budget_venue_period', 'venue_id', 'year', 'month'),
    )


# =====================================================
# DELIVERY AGGREGATOR MODELS
# =====================================================

class DeliveryPlatformCredentials(Base):
    """Delivery platform API credentials"""
    __tablename__ = "delivery_platform_credentials"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    platform = Column(String(50), nullable=False)  # glovo, wolt, bolt_food, uber_eats, etc.
    api_key = Column(Text, nullable=False)
    api_secret = Column(Text, nullable=False)
    store_id = Column(String(100), nullable=False)
    webhook_secret = Column(Text, nullable=True)

    auto_accept = Column(Boolean, default=False)
    auto_accept_delay_seconds = Column(Integer, default=30)
    prep_time_minutes = Column(Integer, default=20)
    commission_percent = Column(Numeric(5, 2), default=30.0)

    enabled = Column(Boolean, default=True)
    connected = Column(Boolean, default=False)
    last_sync = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    venue = relationship("Venue", backref="delivery_credentials")

    __table_args__ = (
        UniqueConstraint('venue_id', 'platform', name='uq_platform_creds'),
    )


class OwnDeliveryDriver(Base):
    """Own fleet delivery drivers"""
    __tablename__ = "own_delivery_drivers"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    vehicle_type = Column(String(20), default="car")
    vehicle_plate = Column(String(20), nullable=True)

    status = Column(String(20), default="offline")  # offline, available, assigned, delivering
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    current_order_id = Column(Integer, ForeignKey("aggregator_orders.id"), nullable=True)

    deliveries_today = Column(Integer, default=0)
    rating = Column(Numeric(3, 2), default=5.0)
    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    venue = relationship("Venue", backref="own_drivers")
    current_order = relationship("app.models.AggregatorOrder", foreign_keys=[current_order_id])

    __table_args__ = (
        Index('idx_driver_venue_status', 'venue_id', 'status'),
    )


class DeliveryZoneConfig(Base):
    """Delivery zone configuration"""
    __tablename__ = "delivery_zone_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    radius_km = Column(Numeric(5, 2), default=5.0)
    center_lat = Column(Float, nullable=False)
    center_lng = Column(Float, nullable=False)

    delivery_fee = Column(Numeric(10, 2), default=3.0)
    min_order_amount = Column(Numeric(10, 2), default=15.0)
    free_delivery_threshold = Column(Numeric(10, 2), nullable=True)
    estimated_minutes = Column(Integer, default=30)

    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    venue = relationship("Venue", backref="delivery_zone_configs")


# =====================================================
# FRANCHISE MANAGEMENT MODELS
# =====================================================

class FranchiseStatus(str, PyEnum):
    PROSPECT = "prospect"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class ComplianceStatus(str, PyEnum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"
    UNDER_REVIEW = "under_review"


class Franchisee(Base):
    """Franchise owner/operator"""
    __tablename__ = "franchisees"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)

    company_name = Column(String(200), nullable=False)
    contact_name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(50), default="Bulgaria")
    territory = Column(String(100), nullable=False)

    venue_ids = Column(JSON, default=[])
    status = Column(String(20), default=FranchiseStatus.PROSPECT.value)

    franchise_fee = Column(Numeric(12, 2), default=50000)
    royalty_percent = Column(Numeric(5, 2), default=5.0)
    marketing_fund_percent = Column(Numeric(5, 2), default=2.0)

    agreement_start = Column(Date, nullable=True)
    agreement_end = Column(Date, nullable=True)
    compliance_status = Column(String(20), default=ComplianceStatus.COMPLIANT.value)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    royalty_payments = relationship("RoyaltyPayment", back_populates="franchisee")
    compliance_audits = relationship("FranchiseComplianceAudit", back_populates="franchisee")

    __table_args__ = (
        Index('idx_franchisee_status', 'status'),
    )


class RoyaltyPayment(Base):
    """Franchise royalty payments"""
    __tablename__ = "royalty_payments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    franchisee_id = Column(Integer, ForeignKey("franchisees.id"), nullable=False, index=True)

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    gross_sales = Column(Numeric(12, 2), nullable=False)
    royalty_rate = Column(Numeric(5, 2), nullable=False)
    royalty_amount = Column(Numeric(12, 2), nullable=False)
    marketing_fund_rate = Column(Numeric(5, 2), nullable=False)
    marketing_fund_amount = Column(Numeric(12, 2), nullable=False)
    total_due = Column(Numeric(12, 2), nullable=False)

    paid_amount = Column(Numeric(12, 2), default=0)
    status = Column(String(20), default="pending")  # pending, paid, overdue
    due_date = Column(Date, nullable=False)
    paid_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    franchisee = relationship("Franchisee", back_populates="royalty_payments")

    __table_args__ = (
        Index('idx_royalty_franchisee_period', 'franchisee_id', 'period_start'),
        Index('idx_royalty_status', 'status', 'due_date'),
    )


class FranchiseComplianceAudit(Base):
    """Franchise compliance audits"""
    __tablename__ = "franchise_compliance_audits"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    franchisee_id = Column(Integer, ForeignKey("franchisees.id"), nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    audit_date = Column(Date, nullable=False)
    auditor_name = Column(String(200), nullable=False)

    categories = Column(JSON, default={})  # category -> score
    overall_score = Column(Numeric(5, 2), nullable=False)
    passed = Column(Boolean, default=False)

    findings = Column(JSON, default=[])
    corrective_actions = Column(JSON, default=[])
    next_audit_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    franchisee = relationship("Franchisee", back_populates="compliance_audits")
    venue = relationship("Venue", backref="franchise_audits")

    __table_args__ = (
        Index('idx_audit_franchisee_date', 'franchisee_id', 'audit_date'),
    )


class FranchiseTerritory(Base):
    """Franchise territory mapping"""
    __tablename__ = "franchise_territories"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)
    region = Column(String(100), nullable=False)
    city = Column(String(100), nullable=True)
    postal_codes = Column(JSON, default=[])
    population = Column(Integer, nullable=True)

    franchisee_id = Column(Integer, ForeignKey("franchisees.id"), nullable=True)
    status = Column(String(20), default="available")  # available, reserved, assigned

    created_at = Column(DateTime, default=datetime.utcnow)

    franchisee = relationship("Franchisee", backref="territories")

    __table_args__ = (
        Index('idx_territory_status', 'status'),
    )


# =====================================================
# NRA TAX COMPLIANCE MODELS
# =====================================================

class TaxDocumentType(str, PyEnum):
    FISCAL_RECEIPT = "fiscal_receipt"
    INVOICE = "invoice"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    STORNO = "storno"


class NRAReportStatus(str, PyEnum):
    PENDING = "pending"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ERROR = "error"


class FiscalDocument(Base):
    """NRA fiscal documents"""
    __tablename__ = "fiscal_documents"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    document_type = Column(String(20), nullable=False)
    document_number = Column(String(50), nullable=False)
    fiscal_memory_number = Column(String(50), nullable=False)

    # Customer info (for invoices)
    customer_vat_number = Column(String(20), nullable=True)
    customer_name = Column(String(200), nullable=True)
    customer_address = Column(Text, nullable=True)

    # Amounts
    items = Column(JSON, default=[])
    subtotal_by_vat = Column(JSON, default={})  # vat_rate -> amount
    vat_by_rate = Column(JSON, default={})  # vat_rate -> vat_amount
    total_without_vat = Column(Numeric(12, 2), nullable=False)
    total_vat = Column(Numeric(12, 2), nullable=False)
    total_with_vat = Column(Numeric(12, 2), nullable=False)

    currency = Column(String(3), default="BGN")
    payment_method = Column(String(50), nullable=False)

    # Fiscal
    unique_sale_number = Column(String(100), nullable=False, unique=True)  # УНП
    fiscal_sign = Column(String(100), nullable=False)
    qr_code = Column(Text, nullable=False)

    issued_at = Column(DateTime, nullable=False)
    sent_to_nra = Column(Boolean, default=False)
    nra_status = Column(String(20), default=NRAReportStatus.PENDING.value)
    nra_response = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    venue = relationship("Venue", backref="fiscal_documents")
    order = relationship("Order", backref="fiscal_document")

    __table_args__ = (
        Index('idx_fiscal_doc_venue_date', 'venue_id', 'issued_at'),
        Index('idx_fiscal_doc_usn', 'unique_sale_number'),
    )


class NRAReport(Base):
    """NRA daily/monthly reports"""
    __tablename__ = "nra_reports"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    report_type = Column(String(20), nullable=False)  # daily, monthly, yearly
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    total_sales = Column(Numeric(12, 2), nullable=False)
    total_vat = Column(Numeric(12, 2), nullable=False)
    total_receipts = Column(Integer, nullable=False)
    total_stornos = Column(Integer, default=0)

    sales_by_vat_rate = Column(JSON, default={})
    vat_by_rate = Column(JSON, default={})
    sales_by_payment_method = Column(JSON, default={})

    generated_at = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String(20), default=NRAReportStatus.PENDING.value)
    nra_reference = Column(String(100), nullable=True)

    venue = relationship("Venue", backref="nra_reports")

    __table_args__ = (
        Index('idx_nra_report_venue_period', 'venue_id', 'report_type', 'period_start'),
        UniqueConstraint('venue_id', 'report_type', 'period_start', name='uq_nra_report'),
    )


class GDPRConsent(Base):
    """GDPR consent records"""
    __tablename__ = "gdpr_consents"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)

    consent_type = Column(String(50), nullable=False)  # marketing, analytics, third_party
    consented = Column(Boolean, nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    consent_text = Column(Text, nullable=False)

    given_at = Column(DateTime, nullable=False)
    withdrawn_at = Column(DateTime, nullable=True)

    venue = relationship("Venue", backref="gdpr_consents")
    customer = relationship("Customer", backref="gdpr_consents")

    __table_args__ = (
        Index('idx_gdpr_customer', 'customer_id', 'consent_type'),
    )


# =====================================================
# HACCP FOOD SAFETY MODELS
# =====================================================

class HazardType(str, PyEnum):
    BIOLOGICAL = "biological"
    CHEMICAL = "chemical"
    PHYSICAL = "physical"
    ALLERGEN = "allergen"


class CriticalControlPoint(Base):
    """HACCP Critical Control Points"""
    __tablename__ = "critical_control_points"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    location = Column(String(200), nullable=False)
    hazard_type = Column(String(20), nullable=False)

    critical_limit_min = Column(Float, nullable=True)
    critical_limit_max = Column(Float, nullable=True)
    target_value = Column(Float, nullable=True)
    unit = Column(String(10), default="C")  # Celsius

    monitoring_frequency_minutes = Column(Integer, default=60)

    last_reading = Column(Float, nullable=True)
    last_reading_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="normal")  # normal, warning, critical

    sensor_id = Column(String(100), nullable=True)
    auto_monitoring = Column(Boolean, default=False)
    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    venue = relationship("Venue", backref="control_points")
    readings = relationship("TemperatureReading", back_populates="ccp")

    __table_args__ = (
        Index('idx_ccp_venue_status', 'venue_id', 'status'),
    )


class TemperatureReading(Base):
    """Temperature readings for HACCP"""
    __tablename__ = "temperature_readings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    ccp_id = Column(Integer, ForeignKey("critical_control_points.id"), nullable=False, index=True)

    location = Column(String(200), nullable=False)
    zone = Column(String(50), nullable=False)  # cold_storage, freezer, hot_holding, cooking
    temperature = Column(Float, nullable=False)

    recorded_by = Column(String(100), nullable=False)
    recorded_at = Column(DateTime, nullable=False)
    within_limits = Column(Boolean, nullable=False)
    corrective_action = Column(Text, nullable=True)

    ccp = relationship("CriticalControlPoint", back_populates="readings")
    venue = relationship("Venue", backref="temperature_readings")

    __table_args__ = (
        Index('idx_temp_reading_venue_date', 'venue_id', 'recorded_at'),
        Index('idx_temp_reading_ccp', 'ccp_id', 'recorded_at'),
    )


class HACCPFoodBatch(Base):
    """Food batch tracking for HACCP"""
    __tablename__ = "haccp_food_batches"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    item_name = Column(String(200), nullable=False)
    batch_number = Column(String(100), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    received_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    storage_location = Column(String(100), nullable=False)

    allergens = Column(JSON, default=[])
    status = Column(String(20), default="active")

    created_at = Column(DateTime, default=datetime.utcnow)

    venue = relationship("Venue", backref="food_batches")
    supplier = relationship("Supplier", backref="food_batches")

    __table_args__ = (
        Index('idx_batch_venue_expiry', 'venue_id', 'expiry_date'),
        Index('idx_batch_status', 'venue_id', 'status'),
    )


class HACCPSupplierCertification(Base):
    """Supplier certifications for HACCP"""
    __tablename__ = "haccp_supplier_certifications"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    supplier_name = Column(String(200), nullable=False)
    certification_type = Column(String(100), nullable=False)
    certificate_number = Column(String(100), nullable=False)

    issued_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    document_url = Column(String(500), nullable=True)
    verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    venue = relationship("Venue", backref="supplier_certifications")
    supplier = relationship("Supplier", backref="certifications")

    __table_args__ = (
        Index('idx_cert_venue_expiry', 'venue_id', 'expiry_date'),
    )


class HACCPInspectionChecklist(Base):
    """HACCP inspection checklists"""
    __tablename__ = "haccp_inspection_checklists"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    inspection_type = Column(String(50), nullable=False)
    inspection_date = Column(Date, nullable=False)
    inspector_name = Column(String(200), nullable=False)

    items = Column(JSON, default=[])
    overall_score = Column(Numeric(5, 2), default=100.0)
    passed = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    venue = relationship("Venue", backref="inspection_checklists")

    __table_args__ = (
        Index('idx_inspection_venue_date', 'venue_id', 'inspection_date'),
    )


class HACCPCorrectiveAction(Base):
    """HACCP corrective actions"""
    __tablename__ = "haccp_corrective_actions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    ccp_id = Column(Integer, ForeignKey("critical_control_points.id"), nullable=True)

    incident_type = Column(String(50), nullable=False)
    incident_date = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical

    immediate_action = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=True)
    preventive_measures = Column(Text, nullable=True)
    responsible_person = Column(String(200), nullable=False)

    status = Column(String(20), default="pending")  # pending, in_progress, completed
    completed_at = Column(DateTime, nullable=True)
    verified_by = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    venue = relationship("Venue", backref="corrective_actions")
    ccp = relationship("CriticalControlPoint", backref="corrective_actions")

    __table_args__ = (
        Index('idx_corrective_venue_status', 'venue_id', 'status'),
    )
