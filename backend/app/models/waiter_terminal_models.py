"""
Waiter Terminal Models
Additional database models for waiter terminal functionality
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


# Payment is defined in platform_compat.py - DO NOT define here
# BarTab is defined in hardware.py - DO NOT define here


class CheckSplit(Base):
    """Track check splits for audit purposes"""
    __tablename__ = "check_splits"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Original order
    original_order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    # Split details
    split_type = Column(String(20), nullable=False)  # by_item, by_seat, even, custom
    num_splits = Column(Integer, default=2)

    # New orders created
    new_order_ids = Column(Text, nullable=True)  # Comma-separated IDs

    # Staff
    split_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    split_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="check_splits")
    original_order = relationship("Order", foreign_keys=[original_order_id])
    split_by_user = relationship("StaffUser", foreign_keys=[split_by])


class WaiterSection(Base):
    """Waiter section assignments"""
    __tablename__ = "waiter_sections"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    waiter_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False, index=True)

    # Section info
    section_name = Column(String(50), nullable=False)
    table_ids = Column(Text, nullable=True)  # Comma-separated table IDs

    # Shift
    shift_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)

    venue = relationship("Venue", backref="waiter_sections")
    waiter = relationship("StaffUser", backref="sections")


class CourseOrder(Base):
    """Track course firing for an order"""
    __tablename__ = "course_orders"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)

    course_name = Column(String(20), nullable=False)  # drinks, appetizer, main, dessert
    course_number = Column(Integer, default=1)

    # Status
    status = Column(String(20), default="pending")  # pending, held, fired, completed
    hold_reason = Column(Text, nullable=True)

    # Timing
    fired_at = Column(DateTime(timezone=True), nullable=True)
    fired_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", backref="courses")
    fired_by_user = relationship("StaffUser", foreign_keys=[fired_by])


class Comp(Base):
    """Track comped items for reporting"""
    __tablename__ = "comps"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=True)

    # Comp details
    comp_type = Column(String(20), nullable=False)  # item, percent, amount
    original_amount = Column(Float, nullable=False)
    comp_amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)

    # Staff
    comped_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    comped_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="comps")
    order = relationship("Order", backref="comps")
    order_item = relationship("OrderItem", backref="comps")
    comped_by_user = relationship("StaffUser", foreign_keys=[comped_by])
    approved_by_user = relationship("StaffUser", foreign_keys=[approved_by])


class Discount(Base):
    """Track applied discounts"""
    __tablename__ = "discounts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    # Discount details
    discount_type = Column(String(20), nullable=False)  # percent, amount
    discount_value = Column(Float, nullable=False)  # 10 for 10% or $10
    discount_amount = Column(Float, nullable=False)  # Actual dollar amount
    reason = Column(Text, nullable=True)

    # Coupon/promo
    coupon_code = Column(String(50), nullable=True)
    promotion_id = Column(Integer, nullable=True)

    # Staff
    applied_by = Column(Integer, ForeignKey("staff_users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="discounts")
    order = relationship("Order", backref="applied_discounts")
    applied_by_user = relationship("StaffUser", foreign_keys=[applied_by])
    approved_by_user = relationship("StaffUser", foreign_keys=[approved_by])


class CashDrawerSession(Base):
    """Cash drawer sessions for end-of-shift reconciliation"""
    __tablename__ = "cash_drawer_sessions"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    waiter_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False, index=True)

    # Opening
    opening_amount = Column(Float, nullable=False)
    opened_at = Column(DateTime(timezone=True), server_default=func.now())

    # Closing
    closing_amount = Column(Float, nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Calculated
    expected_amount = Column(Float, nullable=True)
    difference = Column(Float, nullable=True)

    # Cash transactions during session
    cash_sales = Column(Float, default=0.0)
    cash_tips = Column(Float, default=0.0)
    payouts = Column(Float, default=0.0)
    paid_ins = Column(Float, default=0.0)

    # Status
    status = Column(String(20), default="open")  # open, closed, reconciled

    notes = Column(Text, nullable=True)

    venue = relationship("Venue", backref="drawer_sessions")
    waiter = relationship("StaffUser", backref="drawer_sessions")


class ReceiptPrint(Base):
    """Track receipt prints"""
    __tablename__ = "receipt_prints"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    print_type = Column(String(20), nullable=False)  # guest_check, kitchen, receipt, email
    printer_name = Column(String(100), nullable=True)
    printed_at = Column(DateTime(timezone=True), server_default=func.now())
    printed_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)

    # Email receipt
    email_address = Column(String(255), nullable=True)
    email_sent = Column(Boolean, default=False)

    venue = relationship("Venue", backref="receipt_prints")
    order = relationship("Order", backref="receipt_prints")
    printed_by_user = relationship("StaffUser", foreign_keys=[printed_by])
