"""Multiple Price Lists model - TouchSale gap feature."""

from __future__ import annotations
from datetime import datetime, time
from typing import Optional
from sqlalchemy import Boolean, String, Integer, Float, Time, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class PriceList(Base, TimestampMixin):
    """Price list configuration - allows different pricing contexts."""

    __tablename__ = "price_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "Dine-In", "Takeout", "Delivery", "Happy Hour", "VIP"
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # "dine_in", "takeout", "delivery", "happy_hour", "vip"
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Time-based activation
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    days_of_week: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # [0,1,2,3,4,5,6] - Mon=0, Sun=6

    # Priority for auto-selection (higher = more priority)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Conditions
    min_order_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    requires_membership: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    product_prices = relationship("ProductPrice", back_populates="price_list", cascade="all, delete-orphan")


class ProductPrice(Base, TimestampMixin):
    """Product price in a specific price list."""

    __tablename__ = "product_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)  # References products table
    price_list_id: Mapped[int] = mapped_column(ForeignKey("price_lists.id"), nullable=False)

    price: Mapped[float] = mapped_column(Float, nullable=False)

    # Optional percentage adjustment instead of fixed price
    adjustment_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "fixed", "percent_markup", "percent_discount"
    adjustment_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    price_list = relationship("PriceList", back_populates="product_prices")


class DailyMenu(Base, TimestampMixin):
    """Daily specials menu - Menu of the Day feature."""

    __tablename__ = "daily_menus"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "Lunch Special", "Chef's Choice"
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Time availability
    available_from: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    available_until: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    # Menu items with special pricing
    items: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    # Format: [{"product_id": 1, "special_price": 12.99, "portion_size": "regular", "note": "Includes salad"}]

    # Pricing
    set_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Fixed price for entire menu

    # Limits
    max_orders: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    orders_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class OperatorRecentItem(Base, TimestampMixin):
    """Track recently used items per operator for quick access."""

    __tablename__ = "operator_recent_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)

    last_used: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class ManagerAlert(Base, TimestampMixin):
    """Manager alert configuration for real-time notifications."""

    __tablename__ = "manager_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: "void", "discount", "daily_close", "stock_critical", "large_order", "no_sale_open", "reversal"

    # Threshold for triggering (e.g., discount > 20%)
    threshold_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    threshold_operator: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # ">", "<", ">=", "<=", "="

    # Recipients
    recipient_phones: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # ["+359888123456"]
    recipient_emails: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # ["manager@restaurant.com"]

    # Notification methods
    send_sms: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    send_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    send_push: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timing
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # Don't spam
    last_triggered: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class CustomerCredit(Base, TimestampMixin):
    """Customer credit/account limit tracking."""

    __tablename__ = "customer_credits"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    credit_limit: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    current_balance: Mapped[float] = mapped_column(Float, default=0, nullable=False)  # Positive = owes money

    # Status
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    block_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # History
    last_payment_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_payment_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
