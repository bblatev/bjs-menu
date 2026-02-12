"""Invoice and AP Automation models - Toast xtraCHEF style."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class InvoiceCaptureMethod(str, Enum):
    PHOTO = "photo"
    EMAIL = "email"
    UPLOAD = "upload"
    EDI = "edi"


class Invoice(Base):
    """Supplier invoice with OCR processing."""
    __tablename__ = "invoices"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Invoice details (from OCR or manual)
    invoice_number = Column(String(100), nullable=True)
    invoice_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)

    # Totals
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)

    # OCR processing
    capture_method = Column(SQLEnum(InvoiceCaptureMethod), default=InvoiceCaptureMethod.UPLOAD)
    original_image_path = Column(String(500), nullable=True)
    ocr_raw_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    ocr_processed_at = Column(DateTime, nullable=True)

    # Status and workflow
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.PENDING)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # GL coding
    gl_code = Column(String(50), nullable=True)
    cost_category = Column(String(100), nullable=True)

    # Payment tracking
    payment_date = Column(DateTime, nullable=True)
    payment_reference = Column(String(100), nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    supplier = relationship("Supplier", backref="invoices")
    location = relationship("Location", backref="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base):
    """Individual line item on an invoice."""
    __tablename__ = "invoice_lines"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)

    # Item details (from OCR)
    item_description = Column(String(500), nullable=True)
    item_code = Column(String(100), nullable=True)

    # Quantities and pricing
    quantity = Column(Float, default=1.0)
    unit_of_measure = Column(String(50), nullable=True)
    unit_price = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)

    # Price tracking
    previous_price = Column(Float, nullable=True)
    price_change_percent = Column(Float, nullable=True)
    price_alert_triggered = Column(Boolean, default=False)

    # GL coding (can override invoice-level)
    gl_code = Column(String(50), nullable=True)
    cost_category = Column(String(100), nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="lines")
    product = relationship("Product", backref="invoice_lines")


class PriceHistory(Base):
    """Track historical prices for products from suppliers."""
    __tablename__ = "price_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)

    price = Column(Float, nullable=False)
    unit_of_measure = Column(String(50), nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)

    # Relationships
    product = relationship("Product", backref="price_history")
    supplier = relationship("Supplier", backref="price_history")


class PriceAlert(Base):
    """Price alert configuration and triggers."""
    __tablename__ = "price_alerts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Alert configuration
    alert_type = Column(String(50), nullable=False)  # price_increase, price_decrease, threshold
    threshold_percent = Column(Float, nullable=True)  # % change to trigger
    threshold_amount = Column(Float, nullable=True)   # absolute amount
    max_price = Column(Float, nullable=True)          # alert if price exceeds

    # Status
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    product = relationship("Product", backref="price_alerts")
    supplier = relationship("Supplier", backref="price_alerts")


class GLCode(Base):
    """General Ledger codes for accounting integration."""
    __tablename__ = "gl_codes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # COGS, Operating, etc.
    is_active = Column(Boolean, default=True)

    # Auto-assignment rules
    auto_assign_keywords = Column(JSON, nullable=True)  # ["vodka", "whiskey"] -> this GL code

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class APApprovalWorkflow(Base):
    """Approval workflow configuration."""
    __tablename__ = "ap_approval_workflows"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)

    # Threshold rules
    min_amount = Column(Float, default=0.0)
    max_amount = Column(Float, nullable=True)

    # Approvers (user IDs)
    approver_ids = Column(JSON, nullable=True)  # [1, 2, 3]
    requires_all_approvers = Column(Boolean, default=False)

    # Auto-approve rules
    auto_approve_known_vendors = Column(Boolean, default=False)
    auto_approve_below_amount = Column(Float, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
