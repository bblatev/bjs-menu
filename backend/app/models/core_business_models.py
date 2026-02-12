"""
Core Business Models
Invoice and Tab management for POS system
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


# Invoice and InvoiceItem are defined in invoice.py - DO NOT define here


class TabStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    VOIDED = "voided"
    TRANSFERRED = "transferred"


class Tab(Base):
    """Customer tabs for running bills"""
    __tablename__ = "tabs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    tab_number = Column(String(50), unique=True, index=True, nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, default=1)

    # Customer info
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(200), nullable=True)
    customer_phone = Column(String(50), nullable=True)

    # Table association (optional)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)

    # Staff
    server_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Financial
    subtotal = Column(Float, nullable=False, default=0)
    tax_amount = Column(Float, nullable=False, default=0)
    discount_amount = Column(Float, nullable=False, default=0)
    tip_amount = Column(Float, nullable=False, default=0)
    total = Column(Float, nullable=False, default=0)
    amount_paid = Column(Float, nullable=False, default=0)
    balance_due = Column(Float, nullable=False, default=0)

    # Credit limit for house accounts
    credit_limit = Column(Float, nullable=True)

    # Status
    status = Column(Enum(TabStatus), nullable=False, default=TabStatus.OPEN)

    # Dates
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = relationship("TabItem", back_populates="tab", cascade="all, delete-orphan")
    payments = relationship("TabPayment", back_populates="tab", cascade="all, delete-orphan")


class TabItem(Base):
    """Items on a tab"""
    __tablename__ = "tab_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    tab_id = Column(Integer, ForeignKey("tabs.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    # Item details
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Float, nullable=False, default=1)
    unit_price = Column(Float, nullable=False, default=0)
    modifiers = Column(JSON, nullable=True)
    total = Column(Float, nullable=False, default=0)

    # Status
    voided = Column(Boolean, nullable=False, default=False)
    voided_reason = Column(String(200), nullable=True)
    voided_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Metadata
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    added_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Relationships
    tab = relationship("Tab", back_populates="items")


class TabPayment(Base):
    """Payments on a tab"""
    __tablename__ = "tab_payments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    tab_id = Column(Integer, ForeignKey("tabs.id", ondelete="CASCADE"), nullable=False)

    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=False)  # cash, card, gift_card, etc.
    reference = Column(String(100), nullable=True)

    # Metadata
    paid_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Relationships
    tab = relationship("Tab", back_populates="payments")


class SMSMessage(Base):
    """SMS message log for tracking sent messages"""
    __tablename__ = "sms_messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, default=1)
    campaign_id = Column(Integer, ForeignKey("sms_campaigns.id"), nullable=True, index=True)

    # Recipient
    phone_number = Column(String(20), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    # Message
    message = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=True)  # marketing, alert, notification, etc.

    # Provider info
    provider = Column(String(50), nullable=False)  # twilio, nexmo, etc.
    provider_message_id = Column(String(100), nullable=True)

    # Status
    status = Column(String(20), nullable=False, default="pending")  # pending, sent, delivered, failed
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    # Cost tracking
    cost = Column(Float, nullable=True)
    segments = Column(Integer, nullable=True)

    # Relationships
    campaign = relationship("SMSCampaign", back_populates="messages")


class EmailMessage(Base):
    """Email message log"""
    __tablename__ = "email_messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, default=1)

    # Recipient
    email = Column(String(200), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    # Email content
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)

    # Type
    email_type = Column(String(50), nullable=True)  # receipt, marketing, notification, etc.
    template_id = Column(Integer, nullable=True)

    # Provider info
    provider = Column(String(50), nullable=False)  # sendgrid, mailgun, ses, etc.
    provider_message_id = Column(String(100), nullable=True)

    # Status
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)

    # Tracking
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)


class CryptoPayment(Base):
    """Cryptocurrency payment records"""
    __tablename__ = "crypto_payments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, default=1)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    # Payment details
    payment_id = Column(String(100), unique=True, index=True, nullable=False)
    currency = Column(String(10), nullable=False)  # BTC, ETH, USDT, etc.
    amount_crypto = Column(Float, nullable=False)
    amount_fiat = Column(Float, nullable=False)
    fiat_currency = Column(String(3), nullable=False, default="BGN")
    exchange_rate = Column(Float, nullable=False)

    # Wallet info
    wallet_address = Column(String(200), nullable=False)
    from_address = Column(String(200), nullable=True)

    # Blockchain info
    transaction_hash = Column(String(200), nullable=True, index=True)
    block_number = Column(Integer, nullable=True)
    confirmations = Column(Integer, nullable=False, default=0)
    required_confirmations = Column(Integer, nullable=False, default=3)

    # Status
    status = Column(String(20), nullable=False, default="pending")  # pending, confirming, confirmed, expired, failed

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)

    # Provider info
    provider = Column(String(50), nullable=True)  # coinbase, bitpay, etc.
    provider_payment_id = Column(String(100), nullable=True)


class BiometricRecord(Base):
    """Biometric authentication records"""
    __tablename__ = "biometric_records"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, default=1)

    # Biometric type
    biometric_type = Column(String(50), nullable=False)  # fingerprint, face, card, nfc

    # Template data (encrypted)
    template_data = Column(Text, nullable=False)  # Encrypted biometric template
    template_hash = Column(String(100), nullable=False, index=True)  # For quick lookup

    # Device info
    device_id = Column(String(100), nullable=True)
    device_type = Column(String(50), nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    use_count = Column(Integer, nullable=False, default=0)


class BiometricAuthLog(Base):
    """Log of biometric authentication attempts"""
    __tablename__ = "biometric_auth_logs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, default=1)
    staff_id = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Authentication details
    biometric_type = Column(String(50), nullable=False)
    success = Column(Boolean, nullable=False)
    confidence_score = Column(Float, nullable=True)

    # Device info
    device_id = Column(String(100), nullable=True)

    # Failure info
    failure_reason = Column(String(200), nullable=True)

    # Timestamp
    attempted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
