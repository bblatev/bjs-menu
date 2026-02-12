"""
Advanced Purchase Order Management Models
Complete implementation for:
- Returns to Suppliers & Credit Notes
- PO Amendments & Change Orders
- Blanket/Standing Purchase Orders
- Purchase Requisitions
- Landed Cost Calculation
- Financial Integration (AP, Aging)
- Consolidated Multi-Location Purchasing
- Enhanced Quality Control
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

class ReturnStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SHIPPED = "shipped"
    RECEIVED_BY_SUPPLIER = "received_by_supplier"
    CREDIT_ISSUED = "credit_issued"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ReturnReason(str, enum.Enum):
    DAMAGED = "damaged"
    DEFECTIVE = "defective"
    WRONG_ITEM = "wrong_item"
    WRONG_QUANTITY = "wrong_quantity"
    EXPIRED = "expired"
    QUALITY_ISSUE = "quality_issue"
    NOT_AS_DESCRIBED = "not_as_described"
    OVERSTOCK = "overstock"
    OTHER = "other"


class CreditNoteStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    APPLIED = "applied"
    CANCELLED = "cancelled"


class CreditNoteType(str, enum.Enum):
    RETURN = "return"  # Credit for returned goods
    PRICE_ADJUSTMENT = "price_adjustment"  # Price correction
    SHORTAGE = "shortage"  # Short delivery
    DAMAGE = "damage"  # Damaged goods compensation
    QUALITY = "quality"  # Quality issue compensation
    PROMOTIONAL = "promotional"  # Supplier promotional credit
    OTHER = "other"


class RequisitionStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PARTIALLY_CONVERTED = "partially_converted"
    CONVERTED = "converted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RequisitionPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class BlanketOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    EXPIRED = "expired"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AmendmentType(str, enum.Enum):
    QUANTITY_CHANGE = "quantity_change"
    PRICE_CHANGE = "price_change"
    ITEM_ADDED = "item_added"
    ITEM_REMOVED = "item_removed"
    DATE_CHANGE = "date_change"
    TERMS_CHANGE = "terms_change"
    CANCELLATION = "cancellation"
    OTHER = "other"


class AmendmentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class PaymentStatus(str, enum.Enum):
    NOT_DUE = "not_due"
    DUE = "due"
    OVERDUE = "overdue"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    ON_HOLD = "on_hold"
    DISPUTED = "disputed"


class QCStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    CONDITIONAL = "conditional"


class ConsolidatedOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    COLLECTING = "collecting"
    SUBMITTED = "submitted"
    ORDERED = "ordered"
    RECEIVING = "receiving"
    DISTRIBUTING = "distributing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# =============================================================================
# PURCHASE RETURNS & CREDIT NOTES
# =============================================================================

class SupplierReturn(Base):
    """Return Merchandise Authorization (RMA) for returning goods to supplier"""
    __tablename__ = "supplier_returns"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # Return identification
    return_number = Column(String(50), unique=True, nullable=False, index=True)
    rma_number = Column(String(100), nullable=True)  # Supplier's RMA number

    # Source documents
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    grn_id = Column(Integer, ForeignKey("goods_received_notes.id"), nullable=True)
    invoice_id = Column(Integer, ForeignKey("supplier_invoices.id"), nullable=True)

    # Status
    status = Column(Enum(ReturnStatus), default=ReturnStatus.DRAFT, index=True)

    # Dates
    return_date = Column(Date, nullable=False)
    shipped_date = Column(Date, nullable=True)
    received_by_supplier_date = Column(Date, nullable=True)

    # Shipping
    carrier = Column(String(100), nullable=True)
    tracking_number = Column(String(200), nullable=True)
    shipping_cost = Column(Numeric(12, 2), default=0)
    shipping_paid_by = Column(String(20), default="supplier")  # supplier, buyer

    # Totals
    subtotal = Column(Numeric(12, 2), default=0)
    tax_amount = Column(Numeric(12, 2), default=0)
    total_value = Column(Numeric(12, 2), default=0)

    # Credit expectation
    expected_credit = Column(Numeric(12, 2), default=0)
    credit_received = Column(Numeric(12, 2), default=0)

    # Notes
    return_reason = Column(Enum(ReturnReason), nullable=False)
    reason_details = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    supplier_instructions = Column(Text, nullable=True)

    # Attachments
    attachments = Column(JSON, nullable=True)  # [{filename, url, type}]

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    venue = relationship("Venue", backref="supplier_returns")
    supplier = relationship("Supplier", backref="returns")
    items = relationship("SupplierReturnItem", back_populates="supplier_return", cascade="all, delete-orphan")
    credit_notes = relationship("SupplierCreditNote", back_populates="supplier_return")

    __table_args__ = (
        Index('ix_supplier_returns_venue_status', 'venue_id', 'status'),
        Index('ix_supplier_returns_supplier', 'supplier_id', 'return_date'),
    )


class SupplierReturnItem(Base):
    """Line items in a supplier return"""
    __tablename__ = "supplier_return_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    supplier_return_id = Column(Integer, ForeignKey("supplier_returns.id"), nullable=False, index=True)

    # Source item references
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)
    po_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), nullable=True)
    grn_item_id = Column(Integer, ForeignKey("goods_received_note_items.id"), nullable=True)

    # Item details
    item_name = Column(String(200), nullable=False)
    sku = Column(String(100), nullable=True)
    unit = Column(String(20), nullable=False)

    # Quantities
    quantity_to_return = Column(Numeric(12, 4), nullable=False)
    quantity_shipped = Column(Numeric(12, 4), default=0)
    quantity_received_back = Column(Numeric(12, 4), default=0)  # Confirmed by supplier

    # Pricing
    unit_price = Column(Numeric(12, 4), nullable=False)
    total_value = Column(Numeric(12, 2), nullable=False)

    # Return details
    return_reason = Column(Enum(ReturnReason), nullable=False)
    condition = Column(String(50), nullable=True)  # new, opened, damaged, defective

    # Batch/Lot tracking
    batch_number = Column(String(100), nullable=True)
    expiry_date = Column(Date, nullable=True)

    # Disposition
    disposition = Column(String(50), nullable=True)  # credit, replace, repair, dispose
    replacement_received = Column(Boolean, default=False)

    notes = Column(Text, nullable=True)

    supplier_return = relationship("SupplierReturn", back_populates="items")
    stock_item = relationship("StockItem", backref="return_items")


class SupplierCreditNote(Base):
    """Credit notes received from suppliers"""
    __tablename__ = "supplier_credit_notes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # Credit note identification
    credit_note_number = Column(String(100), nullable=False)
    supplier_reference = Column(String(100), nullable=True)  # Supplier's CN number

    # Type
    credit_type = Column(Enum(CreditNoteType), nullable=False)

    # Source documents
    supplier_return_id = Column(Integer, ForeignKey("supplier_returns.id"), nullable=True)
    invoice_id = Column(Integer, ForeignKey("supplier_invoices.id"), nullable=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)

    # Status
    status = Column(Enum(CreditNoteStatus), default=CreditNoteStatus.PENDING, index=True)

    # Dates
    credit_date = Column(Date, nullable=False)
    received_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)  # Some credits expire

    # Amounts
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), nullable=False)

    # Application tracking
    amount_applied = Column(Numeric(12, 2), default=0)
    amount_remaining = Column(Numeric(12, 2), nullable=False)

    # Currency
    currency = Column(String(3), default="BGN")
    exchange_rate = Column(Numeric(10, 6), default=1)

    # Notes
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Document
    document_url = Column(String(500), nullable=True)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    venue = relationship("Venue", backref="supplier_credit_notes")
    supplier = relationship("Supplier", backref="credit_notes")
    supplier_return = relationship("SupplierReturn", back_populates="credit_notes")
    items = relationship("SupplierCreditNoteItem", back_populates="credit_note", cascade="all, delete-orphan")
    applications = relationship("CreditNoteApplication", back_populates="credit_note", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('venue_id', 'supplier_id', 'credit_note_number', name='uq_supplier_credit_note'),
        Index('ix_credit_notes_status', 'status', 'amount_remaining'),
    )


class SupplierCreditNoteItem(Base):
    """Line items in a credit note"""
    __tablename__ = "supplier_credit_note_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    credit_note_id = Column(Integer, ForeignKey("supplier_credit_notes.id"), nullable=False, index=True)

    # Item reference
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)
    return_item_id = Column(Integer, ForeignKey("supplier_return_items.id"), nullable=True)

    # Item details
    description = Column(String(300), nullable=False)

    # Quantities
    quantity = Column(Numeric(12, 4), nullable=True)
    unit = Column(String(20), nullable=True)

    # Pricing
    unit_price = Column(Numeric(12, 4), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)

    # Tax
    tax_rate = Column(Numeric(5, 2), default=0)
    tax_amount = Column(Numeric(12, 2), default=0)

    credit_note = relationship("SupplierCreditNote", back_populates="items")


class CreditNoteApplication(Base):
    """Track how credit notes are applied to invoices/payments"""
    __tablename__ = "credit_note_applications"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    credit_note_id = Column(Integer, ForeignKey("supplier_credit_notes.id"), nullable=False, index=True)

    # Applied to
    invoice_id = Column(Integer, ForeignKey("supplier_invoices.id"), nullable=True)
    payment_id = Column(Integer, ForeignKey("supplier_payments.id"), nullable=True)

    # Amount
    amount_applied = Column(Numeric(12, 2), nullable=False)

    # Date
    applied_date = Column(Date, nullable=False)

    # Audit
    applied_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    credit_note = relationship("SupplierCreditNote", back_populates="applications")


class SupplierDebitNote(Base):
    """Debit notes issued to suppliers for corrections"""
    __tablename__ = "supplier_debit_notes"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # Debit note identification
    debit_note_number = Column(String(100), unique=True, nullable=False)

    # Source documents
    invoice_id = Column(Integer, ForeignKey("supplier_invoices.id"), nullable=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)

    # Status
    status = Column(String(20), default="draft")  # draft, sent, acknowledged, settled

    # Dates
    debit_date = Column(Date, nullable=False)

    # Amounts
    subtotal = Column(Numeric(12, 2), nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), nullable=False)

    # Reason
    reason = Column(Text, nullable=False)

    # Document
    document_url = Column(String(500), nullable=True)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="supplier_debit_notes")
    supplier = relationship("Supplier", backref="debit_notes")


# =============================================================================
# PO AMENDMENTS & CHANGE ORDERS
# =============================================================================

class PurchaseOrderAmendment(Base):
    """Track changes/amendments to purchase orders"""
    __tablename__ = "purchase_order_amendments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, index=True)

    # Amendment identification
    amendment_number = Column(Integer, nullable=False)  # Sequential per PO
    change_order_number = Column(String(50), nullable=True)  # External reference

    # Type
    amendment_type = Column(Enum(AmendmentType), nullable=False)

    # Status
    status = Column(Enum(AmendmentStatus), default=AmendmentStatus.PENDING, index=True)

    # Changes snapshot
    previous_values = Column(JSON, nullable=True)  # Snapshot before change
    new_values = Column(JSON, nullable=True)  # New values

    # Affected items
    affected_items = Column(JSON, nullable=True)  # [{item_id, field, old_value, new_value}]

    # Financial impact
    previous_total = Column(Numeric(12, 2), nullable=True)
    new_total = Column(Numeric(12, 2), nullable=True)
    variance = Column(Numeric(12, 2), nullable=True)

    # Reason
    reason = Column(Text, nullable=False)

    # Supplier notification
    supplier_notified = Column(Boolean, default=False)
    supplier_notified_at = Column(DateTime(timezone=True), nullable=True)
    supplier_acknowledged = Column(Boolean, default=False)
    supplier_acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    # Audit
    requested_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_at = Column(DateTime(timezone=True), nullable=True)

    purchase_order = relationship("PurchaseOrder", backref="amendments")

    __table_args__ = (
        UniqueConstraint('purchase_order_id', 'amendment_number', name='uq_po_amendment_number'),
    )


class PurchaseOrderVersionHistory(Base):
    """Full version history of PO changes"""
    __tablename__ = "purchase_order_version_history"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, index=True)

    # Version
    version_number = Column(Integer, nullable=False)

    # Snapshot
    full_snapshot = Column(JSON, nullable=False)  # Complete PO data at this version
    items_snapshot = Column(JSON, nullable=False)  # Complete items data

    # Change info
    change_type = Column(String(50), nullable=False)  # created, updated, amended, cancelled
    change_summary = Column(Text, nullable=True)
    amendment_id = Column(Integer, ForeignKey("purchase_order_amendments.id"), nullable=True)

    # Audit
    changed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    purchase_order = relationship("PurchaseOrder", backref="version_history")

    __table_args__ = (
        UniqueConstraint('purchase_order_id', 'version_number', name='uq_po_version'),
        Index('ix_po_version_history', 'purchase_order_id', 'version_number'),
    )


# =============================================================================
# BLANKET / STANDING PURCHASE ORDERS
# =============================================================================

class BlanketPurchaseOrder(Base):
    """Long-term purchase agreements with suppliers"""
    __tablename__ = "blanket_purchase_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # Identification
    blanket_number = Column(String(50), unique=True, nullable=False, index=True)
    contract_reference = Column(String(100), nullable=True)

    # Status
    status = Column(Enum(BlanketOrderStatus), default=BlanketOrderStatus.DRAFT, index=True)

    # Period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Agreement terms
    agreement_type = Column(String(50), nullable=False)  # quantity_based, value_based, time_based

    # Limits
    total_quantity_limit = Column(Numeric(12, 4), nullable=True)
    total_value_limit = Column(Numeric(12, 2), nullable=True)

    # Used amounts
    quantity_released = Column(Numeric(12, 4), default=0)
    value_released = Column(Numeric(12, 2), default=0)

    # Remaining
    quantity_remaining = Column(Numeric(12, 4), nullable=True)
    value_remaining = Column(Numeric(12, 2), nullable=True)

    # Terms
    payment_terms = Column(String(100), nullable=True)
    delivery_terms = Column(String(200), nullable=True)
    price_protection = Column(Boolean, default=False)  # Fixed prices for duration

    # Volume discounts
    volume_discounts = Column(JSON, nullable=True)  # [{min_qty, discount_pct}, ...]

    # Notes
    terms_and_conditions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Document
    contract_document_url = Column(String(500), nullable=True)

    # Auto-renewal
    auto_renew = Column(Boolean, default=False)
    renewal_notice_days = Column(Integer, default=30)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    venue = relationship("Venue", backref="blanket_orders")
    supplier = relationship("Supplier", backref="blanket_orders")
    items = relationship("BlanketPurchaseOrderItem", back_populates="blanket_order", cascade="all, delete-orphan")
    releases = relationship("BlanketOrderRelease", back_populates="blanket_order", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_blanket_orders_dates', 'start_date', 'end_date'),
    )


class BlanketPurchaseOrderItem(Base):
    """Items covered under a blanket PO"""
    __tablename__ = "blanket_purchase_order_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    blanket_order_id = Column(Integer, ForeignKey("blanket_purchase_orders.id"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)

    # Item details
    item_name = Column(String(200), nullable=False)
    sku = Column(String(100), nullable=True)
    unit = Column(String(20), nullable=False)

    # Agreed pricing
    unit_price = Column(Numeric(12, 4), nullable=False)
    price_valid_until = Column(Date, nullable=True)

    # Quantity limits
    min_order_quantity = Column(Numeric(12, 4), nullable=True)
    max_order_quantity = Column(Numeric(12, 4), nullable=True)
    total_quantity_limit = Column(Numeric(12, 4), nullable=True)

    # Released tracking
    quantity_released = Column(Numeric(12, 4), default=0)
    quantity_remaining = Column(Numeric(12, 4), nullable=True)

    # Volume discounts for this item
    volume_discounts = Column(JSON, nullable=True)

    notes = Column(Text, nullable=True)

    blanket_order = relationship("BlanketPurchaseOrder", back_populates="items")
    stock_item = relationship("StockItem", backref="blanket_order_items")


class BlanketOrderRelease(Base):
    """Individual release orders against blanket PO"""
    __tablename__ = "blanket_order_releases"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    blanket_order_id = Column(Integer, ForeignKey("blanket_purchase_orders.id"), nullable=False, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)  # Linked actual PO

    # Release identification
    release_number = Column(Integer, nullable=False)  # Sequential per blanket

    # Status
    status = Column(String(20), default="draft")  # draft, submitted, ordered, received

    # Release details
    release_date = Column(Date, nullable=False)
    expected_delivery = Column(Date, nullable=True)

    # Totals
    total_quantity = Column(Numeric(12, 4), default=0)
    total_value = Column(Numeric(12, 2), default=0)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    blanket_order = relationship("BlanketPurchaseOrder", back_populates="releases")
    items = relationship("BlanketOrderReleaseItem", back_populates="release", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('blanket_order_id', 'release_number', name='uq_blanket_release_number'),
    )


class BlanketOrderReleaseItem(Base):
    """Items in a blanket order release"""
    __tablename__ = "blanket_order_release_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    release_id = Column(Integer, ForeignKey("blanket_order_releases.id"), nullable=False, index=True)
    blanket_item_id = Column(Integer, ForeignKey("blanket_purchase_order_items.id"), nullable=False)

    # Quantity
    quantity = Column(Numeric(12, 4), nullable=False)

    # Price (from blanket or override)
    unit_price = Column(Numeric(12, 4), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)

    notes = Column(Text, nullable=True)

    release = relationship("BlanketOrderRelease", back_populates="items")
    blanket_item = relationship("BlanketPurchaseOrderItem", backref="release_items")


# =============================================================================
# PURCHASE REQUISITIONS
# =============================================================================

class PurchaseRequisition(Base):
    """Purchase requests before becoming POs"""
    __tablename__ = "purchase_requisitions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Requisition identification
    requisition_number = Column(String(50), unique=True, nullable=False, index=True)

    # Status
    status = Column(Enum(RequisitionStatus), default=RequisitionStatus.DRAFT, index=True)
    priority = Column(Enum(RequisitionPriority), default=RequisitionPriority.NORMAL)

    # Requester info
    department = Column(String(100), nullable=True)
    cost_center = Column(String(50), nullable=True)

    # Dates
    request_date = Column(Date, nullable=False)
    required_by_date = Column(Date, nullable=True)

    # Budget reference
    budget_code = Column(String(50), nullable=True)
    budget_available = Column(Numeric(12, 2), nullable=True)

    # Estimated totals
    estimated_total = Column(Numeric(12, 2), default=0)

    # Preferred supplier (suggestion)
    suggested_supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Justification
    business_justification = Column(Text, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)  # For approvers

    # Conversion tracking
    converted_to_po = Column(Boolean, default=False)

    # Audit
    requested_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    venue = relationship("Venue", backref="purchase_requisitions")
    suggested_supplier = relationship("Supplier", backref="suggested_requisitions")
    items = relationship("PurchaseRequisitionItem", back_populates="requisition", cascade="all, delete-orphan")
    approvals = relationship("RequisitionApproval", back_populates="requisition", cascade="all, delete-orphan")
    converted_orders = relationship("RequisitionToPO", back_populates="requisition")

    __table_args__ = (
        Index('ix_requisitions_status_date', 'status', 'request_date'),
    )


class PurchaseRequisitionItem(Base):
    """Line items in a requisition"""
    __tablename__ = "purchase_requisition_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("purchase_requisitions.id"), nullable=False, index=True)

    # Item reference
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)

    # Item details
    item_description = Column(String(300), nullable=False)
    specifications = Column(Text, nullable=True)

    # Quantity
    quantity_requested = Column(Numeric(12, 4), nullable=False)
    unit = Column(String(20), nullable=False)

    # Estimated pricing
    estimated_unit_price = Column(Numeric(12, 4), nullable=True)
    estimated_total = Column(Numeric(12, 2), nullable=True)

    # Suggested supplier
    suggested_supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Conversion tracking
    quantity_converted = Column(Numeric(12, 4), default=0)
    fully_converted = Column(Boolean, default=False)

    notes = Column(Text, nullable=True)

    requisition = relationship("PurchaseRequisition", back_populates="items")
    stock_item = relationship("StockItem", backref="requisition_items")
    suggested_supplier = relationship("Supplier", backref="suggested_req_items")


class RequisitionApproval(Base):
    """Approval workflow for requisitions"""
    __tablename__ = "requisition_approvals"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("purchase_requisitions.id"), nullable=False, index=True)

    # Approval level
    approval_level = Column(Integer, nullable=False)
    approval_type = Column(String(50), nullable=False)  # department, manager, finance, director

    # Required approver
    required_role = Column(String(50), nullable=True)
    required_user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Threshold (approve if below this amount)
    amount_threshold = Column(Numeric(12, 2), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, approved, rejected, skipped

    # Actual approval
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    comments = Column(Text, nullable=True)

    requisition = relationship("PurchaseRequisition", back_populates="approvals")


class RequisitionToPO(Base):
    """Track conversion from requisitions to POs"""
    __tablename__ = "requisition_to_po"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    requisition_id = Column(Integer, ForeignKey("purchase_requisitions.id"), nullable=False, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, index=True)

    # Conversion details
    converted_at = Column(DateTime(timezone=True), server_default=func.now())
    converted_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Items converted
    items_converted = Column(JSON, nullable=True)  # [{req_item_id, po_item_id, quantity}]

    requisition = relationship("PurchaseRequisition", back_populates="converted_orders")
    purchase_order = relationship("PurchaseOrder", backref="source_requisitions")


# =============================================================================
# LANDED COST CALCULATION
# =============================================================================

class LandedCostConfig(Base):
    """Configuration for landed cost calculation"""
    __tablename__ = "landed_cost_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)

    # Default cost components
    default_freight_method = Column(String(50), nullable=True)  # weight, volume, value, quantity
    default_customs_rate = Column(Numeric(5, 2), default=0)
    default_handling_rate = Column(Numeric(5, 2), default=0)

    # Auto-apply settings
    auto_apply_to_imports = Column(Boolean, default=True)
    auto_apply_to_domestic = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="landed_cost_configs")


class PurchaseOrderLandedCost(Base):
    """Landed cost calculation for a purchase order"""
    __tablename__ = "purchase_order_landed_costs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, index=True)
    grn_id = Column(Integer, ForeignKey("goods_received_notes.id"), nullable=True)

    # Status
    status = Column(String(20), default="draft")  # draft, calculated, applied, finalized

    # Base cost
    merchandise_cost = Column(Numeric(12, 2), nullable=False)

    # Freight/Shipping
    freight_cost = Column(Numeric(12, 2), default=0)
    freight_allocation_method = Column(String(50), nullable=True)  # weight, volume, value, quantity

    # Customs & Duties
    customs_duty = Column(Numeric(12, 2), default=0)
    import_tax = Column(Numeric(12, 2), default=0)
    customs_broker_fee = Column(Numeric(12, 2), default=0)

    # Handling & Other
    handling_fee = Column(Numeric(12, 2), default=0)
    insurance_cost = Column(Numeric(12, 2), default=0)
    inspection_fee = Column(Numeric(12, 2), default=0)
    other_costs = Column(Numeric(12, 2), default=0)
    other_costs_description = Column(Text, nullable=True)

    # Totals
    total_additional_costs = Column(Numeric(12, 2), default=0)
    total_landed_cost = Column(Numeric(12, 2), default=0)

    # Per-unit impact (average)
    average_cost_increase_pct = Column(Numeric(5, 2), default=0)

    # Currency
    currency = Column(String(3), default="BGN")
    exchange_rate = Column(Numeric(10, 6), default=1)

    # Documents
    documents = Column(JSON, nullable=True)  # [{type, number, url}]

    # Audit
    calculated_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=True)
    applied_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    purchase_order = relationship("PurchaseOrder", backref="landed_costs")
    items = relationship("LandedCostAllocation", back_populates="landed_cost", cascade="all, delete-orphan")


class LandedCostAllocation(Base):
    """Allocation of landed costs to individual items"""
    __tablename__ = "landed_cost_allocations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    landed_cost_id = Column(Integer, ForeignKey("purchase_order_landed_costs.id"), nullable=False, index=True)
    po_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), nullable=False)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)

    # Base values for allocation
    quantity = Column(Numeric(12, 4), nullable=False)
    weight = Column(Numeric(12, 4), nullable=True)
    volume = Column(Numeric(12, 4), nullable=True)
    merchandise_value = Column(Numeric(12, 2), nullable=False)

    # Allocated costs
    allocated_freight = Column(Numeric(12, 4), default=0)
    allocated_customs = Column(Numeric(12, 4), default=0)
    allocated_handling = Column(Numeric(12, 4), default=0)
    allocated_other = Column(Numeric(12, 4), default=0)
    total_allocated = Column(Numeric(12, 4), default=0)

    # Final cost
    original_unit_cost = Column(Numeric(12, 4), nullable=False)
    landed_unit_cost = Column(Numeric(12, 4), nullable=False)
    cost_increase_pct = Column(Numeric(5, 2), default=0)

    # Applied to inventory
    applied_to_stock = Column(Boolean, default=False)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    landed_cost = relationship("PurchaseOrderLandedCost", back_populates="items")


# =============================================================================
# FINANCIAL INTEGRATION - ACCOUNTS PAYABLE
# =============================================================================

class SupplierPayment(Base):
    """Track payments made to suppliers"""
    __tablename__ = "supplier_payments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # Payment identification
    payment_number = Column(String(50), unique=True, nullable=False, index=True)
    payment_reference = Column(String(100), nullable=True)  # Bank reference

    # Payment details
    payment_date = Column(Date, nullable=False)
    payment_method = Column(String(50), nullable=False)  # bank_transfer, check, cash, card

    # Amounts
    payment_amount = Column(Numeric(12, 2), nullable=False)
    discount_taken = Column(Numeric(12, 2), default=0)  # Early payment discount
    credits_applied = Column(Numeric(12, 2), default=0)
    net_payment = Column(Numeric(12, 2), nullable=False)

    # Currency
    currency = Column(String(3), default="BGN")
    exchange_rate = Column(Numeric(10, 6), default=1)

    # Bank details
    bank_account = Column(String(100), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, processing, completed, failed, reversed

    # Reconciliation
    reconciled = Column(Boolean, default=False)
    reconciled_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    venue = relationship("Venue", backref="supplier_payments")
    supplier = relationship("Supplier", backref="payments")
    allocations = relationship("PaymentAllocation", back_populates="payment", cascade="all, delete-orphan")


class PaymentAllocation(Base):
    """Allocate payments to invoices"""
    __tablename__ = "payment_allocations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("supplier_payments.id"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("supplier_invoices.id"), nullable=False, index=True)

    # Allocation amounts
    allocated_amount = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), default=0)

    # Dates
    allocation_date = Column(Date, nullable=False)

    notes = Column(Text, nullable=True)

    payment = relationship("SupplierPayment", back_populates="allocations")


class SupplierAccountBalance(Base):
    """Track running balance with each supplier"""
    __tablename__ = "supplier_account_balances"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # Balances
    total_invoiced = Column(Numeric(14, 2), default=0)
    total_paid = Column(Numeric(14, 2), default=0)
    total_credits = Column(Numeric(14, 2), default=0)
    current_balance = Column(Numeric(14, 2), default=0)

    # Aging buckets
    current_amount = Column(Numeric(12, 2), default=0)  # Not yet due
    aging_1_30 = Column(Numeric(12, 2), default=0)  # 1-30 days overdue
    aging_31_60 = Column(Numeric(12, 2), default=0)  # 31-60 days
    aging_61_90 = Column(Numeric(12, 2), default=0)  # 61-90 days
    aging_over_90 = Column(Numeric(12, 2), default=0)  # Over 90 days

    # Credit limit
    credit_limit = Column(Numeric(12, 2), nullable=True)
    available_credit = Column(Numeric(12, 2), nullable=True)

    # Stats
    average_days_to_pay = Column(Integer, nullable=True)
    last_payment_date = Column(Date, nullable=True)
    last_invoice_date = Column(Date, nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    venue = relationship("Venue", backref="supplier_balances")
    supplier = relationship("Supplier", backref="account_balance", uselist=False)

    __table_args__ = (
        UniqueConstraint('venue_id', 'supplier_id', name='uq_supplier_balance'),
    )


class InvoiceAgingSnapshot(Base):
    """Periodic snapshots of invoice aging for reporting"""
    __tablename__ = "invoice_aging_snapshots"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Snapshot date
    snapshot_date = Column(Date, nullable=False)

    # Totals
    total_outstanding = Column(Numeric(14, 2), default=0)

    # Aging buckets (venue totals)
    current_total = Column(Numeric(12, 2), default=0)
    aging_1_30_total = Column(Numeric(12, 2), default=0)
    aging_31_60_total = Column(Numeric(12, 2), default=0)
    aging_61_90_total = Column(Numeric(12, 2), default=0)
    aging_over_90_total = Column(Numeric(12, 2), default=0)

    # By supplier breakdown
    supplier_breakdown = Column(JSON, nullable=True)  # [{supplier_id, amounts by bucket}]

    # Stats
    invoice_count = Column(Integer, default=0)
    overdue_count = Column(Integer, default=0)
    average_days_outstanding = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="aging_snapshots")

    __table_args__ = (
        UniqueConstraint('venue_id', 'snapshot_date', name='uq_aging_snapshot'),
    )


class PaymentTermsConfig(Base):
    """Payment terms configuration"""
    __tablename__ = "payment_terms_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Term name
    name = Column(String(100), nullable=False)  # "Net 30", "2/10 Net 30", etc.
    code = Column(String(20), nullable=False)

    # Due date calculation
    due_days = Column(Integer, nullable=False)  # Days until due
    due_from = Column(String(20), default="invoice_date")  # invoice_date, receipt_date, month_end

    # Early payment discount
    discount_days = Column(Integer, nullable=True)  # Pay within X days
    discount_percent = Column(Numeric(5, 2), nullable=True)  # Get Y% discount

    # Late payment
    late_fee_percent = Column(Numeric(5, 2), nullable=True)
    late_fee_grace_days = Column(Integer, default=0)

    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="payment_terms")

    __table_args__ = (
        UniqueConstraint('venue_id', 'code', name='uq_payment_terms_code'),
    )


# =============================================================================
# CONSOLIDATED MULTI-LOCATION PURCHASING
# =============================================================================

class ConsolidatedPurchaseOrder(Base):
    """Consolidated orders across multiple venues"""
    __tablename__ = "consolidated_purchase_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)

    # Organization level (parent of venues)
    tenant_id = Column(Integer, nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # Identification
    consolidated_number = Column(String(50), unique=True, nullable=False, index=True)

    # Status
    status = Column(Enum(ConsolidatedOrderStatus), default=ConsolidatedOrderStatus.DRAFT, index=True)

    # Collection window
    collection_start = Column(DateTime(timezone=True), nullable=True)
    collection_end = Column(DateTime(timezone=True), nullable=True)

    # Dates
    order_date = Column(DateTime(timezone=True), nullable=True)
    expected_delivery = Column(DateTime(timezone=True), nullable=True)

    # Delivery
    delivery_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    delivery_address = Column(Text, nullable=True)

    # Totals
    total_quantity = Column(Numeric(12, 4), default=0)
    subtotal = Column(Numeric(14, 2), default=0)
    volume_discount = Column(Numeric(12, 2), default=0)  # Consolidated discount
    tax_amount = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(14, 2), default=0)

    # Participating venues
    venue_count = Column(Integer, default=0)

    notes = Column(Text, nullable=True)

    # Audit
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    supplier = relationship("Supplier", backref="consolidated_orders")
    venue_orders = relationship("ConsolidatedOrderVenue", back_populates="consolidated_order", cascade="all, delete-orphan")
    items = relationship("ConsolidatedOrderItem", back_populates="consolidated_order", cascade="all, delete-orphan")


class ConsolidatedOrderVenue(Base):
    """Venue participation in consolidated order"""
    __tablename__ = "consolidated_order_venues"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    consolidated_order_id = Column(Integer, ForeignKey("consolidated_purchase_orders.id"), nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Source requisition or request
    source_requisition_id = Column(Integer, ForeignKey("purchase_requisitions.id"), nullable=True)

    # Venue's portion
    subtotal = Column(Numeric(12, 2), default=0)
    allocated_discount = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(12, 2), default=0)

    # Distribution status
    distribution_status = Column(String(20), default="pending")  # pending, in_transit, received
    received_at = Column(DateTime(timezone=True), nullable=True)

    # Generated PO for this venue (after distribution)
    generated_po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)

    notes = Column(Text, nullable=True)

    consolidated_order = relationship("ConsolidatedPurchaseOrder", back_populates="venue_orders")
    venue = relationship("Venue", backref="consolidated_participations")


class ConsolidatedOrderItem(Base):
    """Items in consolidated order"""
    __tablename__ = "consolidated_order_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    consolidated_order_id = Column(Integer, ForeignKey("consolidated_purchase_orders.id"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)

    # Item details
    item_name = Column(String(200), nullable=False)
    sku = Column(String(100), nullable=True)
    unit = Column(String(20), nullable=False)

    # Total consolidated quantity
    total_quantity = Column(Numeric(12, 4), nullable=False)

    # Pricing
    unit_price = Column(Numeric(12, 4), nullable=False)
    volume_discount_pct = Column(Numeric(5, 2), default=0)
    net_unit_price = Column(Numeric(12, 4), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)

    # Distribution breakdown
    venue_breakdown = Column(JSON, nullable=False)  # [{venue_id, quantity, amount}]

    notes = Column(Text, nullable=True)

    consolidated_order = relationship("ConsolidatedPurchaseOrder", back_populates="items")


# =============================================================================
# ENHANCED QUALITY CONTROL
# =============================================================================

class QualityControlChecklist(Base):
    """QC checklists for receiving"""
    __tablename__ = "quality_control_checklists"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Applicable to
    applies_to_category = Column(String(100), nullable=True)  # Stock category
    applies_to_supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Checklist items
    checklist_items = Column(JSON, nullable=False)  # [{id, question, type, required, options}]

    # Settings
    requires_photos = Column(Boolean, default=False)
    requires_temperature = Column(Boolean, default=False)
    auto_reject_threshold = Column(Integer, nullable=True)  # Auto-reject if X items fail

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="qc_checklists")


class QualityControlInspection(Base):
    """QC inspection records"""
    __tablename__ = "quality_control_inspections"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Source
    grn_id = Column(Integer, ForeignKey("goods_received_notes.id"), nullable=True)
    grn_item_id = Column(Integer, ForeignKey("goods_received_note_items.id"), nullable=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)

    # Checklist used
    checklist_id = Column(Integer, ForeignKey("quality_control_checklists.id"), nullable=True)

    # Inspection reference
    inspection_number = Column(String(50), nullable=False)

    # Status
    status = Column(Enum(QCStatus), default=QCStatus.PENDING, index=True)

    # Inspection date
    inspection_date = Column(DateTime(timezone=True), server_default=func.now())

    # Results
    checklist_responses = Column(JSON, nullable=True)  # [{item_id, response, passed}]
    overall_score = Column(Numeric(5, 2), nullable=True)  # Percentage passed

    # Temperature
    temperature_reading = Column(Numeric(5, 2), nullable=True)
    temperature_unit = Column(String(1), default="C")  # C or F

    # Photos/Documents
    photos = Column(JSON, nullable=True)  # [{url, caption, timestamp}]
    documents = Column(JSON, nullable=True)  # [{type, url}]

    # Outcome
    items_passed = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    quantity_accepted = Column(Numeric(12, 4), nullable=True)
    quantity_rejected = Column(Numeric(12, 4), nullable=True)
    quantity_quarantined = Column(Numeric(12, 4), nullable=True)

    # Disposition
    disposition = Column(String(50), nullable=True)  # accept, reject, quarantine, return
    disposition_reason = Column(Text, nullable=True)

    # Follow-up
    requires_follow_up = Column(Boolean, default=False)
    follow_up_notes = Column(Text, nullable=True)

    # Supplier notification
    supplier_notified = Column(Boolean, default=False)
    supplier_notified_at = Column(DateTime(timezone=True), nullable=True)

    # Audit
    inspected_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="qc_inspections")
    checklist = relationship("QualityControlChecklist", backref="inspections")


class QualityIssue(Base):
    """Track quality issues for supplier performance"""
    __tablename__ = "quality_issues"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)

    # Source
    inspection_id = Column(Integer, ForeignKey("quality_control_inspections.id"), nullable=True)
    grn_id = Column(Integer, ForeignKey("goods_received_notes.id"), nullable=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)

    # Issue details
    issue_number = Column(String(50), unique=True, nullable=False)
    issue_type = Column(String(50), nullable=False)  # contamination, damage, expiry, wrong_item, etc.
    severity = Column(String(20), nullable=False)  # minor, moderate, major, critical

    # Description
    description = Column(Text, nullable=False)

    # Affected quantity
    affected_quantity = Column(Numeric(12, 4), nullable=True)
    affected_value = Column(Numeric(12, 2), nullable=True)

    # Status
    status = Column(String(20), default="open")  # open, investigating, resolved, closed

    # Resolution
    resolution = Column(Text, nullable=True)
    resolution_date = Column(Date, nullable=True)

    # Corrective action
    corrective_action_required = Column(Boolean, default=False)
    corrective_action = Column(Text, nullable=True)
    corrective_action_deadline = Column(Date, nullable=True)
    corrective_action_completed = Column(Boolean, default=False)

    # Financial impact
    credit_requested = Column(Numeric(12, 2), default=0)
    credit_received = Column(Numeric(12, 2), default=0)

    # Audit
    reported_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    resolved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="quality_issues")
    supplier = relationship("Supplier", backref="quality_issues")


# =============================================================================
# ENHANCED STOCK REORDER - MIN/MAX LEVELS
# =============================================================================

class StockReorderConfig(Base):
    """Enhanced reorder configuration per stock item"""
    __tablename__ = "stock_reorder_configs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False, index=True)

    # Min/Max levels
    min_stock_level = Column(Numeric(12, 4), nullable=False)  # Reorder point
    max_stock_level = Column(Numeric(12, 4), nullable=False)  # Order up to
    safety_stock = Column(Numeric(12, 4), default=0)  # Buffer stock

    # Reorder quantity
    reorder_quantity = Column(Numeric(12, 4), nullable=True)  # Fixed reorder qty
    reorder_method = Column(String(20), default="to_max")  # to_max, fixed_qty, days_supply
    days_of_supply = Column(Integer, nullable=True)  # For days_supply method

    # Lead time
    lead_time_days = Column(Integer, default=1)
    lead_time_variance_days = Column(Integer, default=0)  # For safety stock calc

    # Seasonal adjustments
    seasonal_adjustments = Column(JSON, nullable=True)  # [{month, multiplier}]

    # Location-specific (for multi-warehouse)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)

    # Preferred supplier
    preferred_supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Auto-order settings
    auto_order_enabled = Column(Boolean, default=False)
    auto_order_threshold = Column(Numeric(12, 4), nullable=True)
    require_approval = Column(Boolean, default=True)

    # ABC classification
    abc_class = Column(String(1), nullable=True)  # A, B, C

    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    venue = relationship("Venue", backref="reorder_configs")
    stock_item = relationship("StockItem", backref="reorder_config", uselist=False)
    preferred_supplier = relationship("Supplier", backref="preferred_for_items")

    __table_args__ = (
        UniqueConstraint('venue_id', 'stock_item_id', 'warehouse_id', name='uq_stock_reorder_config'),
    )


class ReorderAlert(Base):
    """Alerts for items needing reorder"""
    __tablename__ = "reorder_alerts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False, index=True)

    # Alert type
    alert_type = Column(String(30), nullable=False)  # below_min, below_safety, stockout, forecast_shortage

    # Current status
    current_stock = Column(Numeric(12, 4), nullable=False)
    min_level = Column(Numeric(12, 4), nullable=False)

    # Suggested action
    suggested_quantity = Column(Numeric(12, 4), nullable=True)
    suggested_supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Priority
    priority = Column(String(20), default="normal")  # low, normal, high, critical
    days_until_stockout = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), default="active")  # active, acknowledged, ordered, dismissed

    # Action taken
    action_taken = Column(String(50), nullable=True)
    po_created_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)

    # Audit
    acknowledged_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="reorder_alerts")
    stock_item = relationship("StockItem", backref="reorder_alerts")

    __table_args__ = (
        Index('ix_reorder_alerts_active', 'venue_id', 'status'),
    )


# =============================================================================
# PARTIAL DELIVERY TRACKING
# =============================================================================

class PartialDeliverySchedule(Base):
    """Track expected partial deliveries for a PO"""
    __tablename__ = "partial_delivery_schedules"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, index=True)

    # Delivery number
    delivery_number = Column(Integer, nullable=False)  # 1, 2, 3...

    # Expected delivery
    expected_date = Column(Date, nullable=False)

    # Status
    status = Column(String(20), default="scheduled")  # scheduled, shipped, received, cancelled

    # Actual delivery
    grn_id = Column(Integer, ForeignKey("goods_received_notes.id"), nullable=True)
    actual_date = Column(Date, nullable=True)

    # Totals for this delivery
    total_quantity = Column(Numeric(12, 4), default=0)
    total_value = Column(Numeric(12, 2), default=0)

    # Shipping info
    shipping_reference = Column(String(100), nullable=True)
    carrier = Column(String(100), nullable=True)
    tracking_number = Column(String(200), nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    purchase_order = relationship("PurchaseOrder", backref="delivery_schedules")
    items = relationship("PartialDeliveryItem", back_populates="schedule", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('purchase_order_id', 'delivery_number', name='uq_partial_delivery'),
    )


class PartialDeliveryItem(Base):
    """Items in a partial delivery"""
    __tablename__ = "partial_delivery_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("partial_delivery_schedules.id"), nullable=False, index=True)
    po_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), nullable=False)

    # Quantities
    quantity_scheduled = Column(Numeric(12, 4), nullable=False)
    quantity_shipped = Column(Numeric(12, 4), default=0)
    quantity_received = Column(Numeric(12, 4), default=0)

    notes = Column(Text, nullable=True)

    schedule = relationship("PartialDeliverySchedule", back_populates="items")


class BackorderTracking(Base):
    """Track backordered items"""
    __tablename__ = "backorder_tracking"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False, index=True)
    po_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), nullable=False, index=True)

    # Backorder details
    quantity_backordered = Column(Numeric(12, 4), nullable=False)
    original_expected_date = Column(Date, nullable=True)
    new_expected_date = Column(Date, nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, confirmed, shipped, received, cancelled

    # Supplier response
    supplier_confirmed = Column(Boolean, default=False)
    supplier_eta = Column(Date, nullable=True)
    supplier_notes = Column(Text, nullable=True)

    # Resolution
    resolution = Column(String(50), nullable=True)  # received, cancelled, substituted
    resolved_date = Column(Date, nullable=True)
    substitution_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="backorders")
    purchase_order = relationship("PurchaseOrder", backref="backorders")

    __table_args__ = (
        Index('ix_backorders_status', 'venue_id', 'status'),
    )
