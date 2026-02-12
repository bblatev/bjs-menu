"""POS integration models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PosRawEvent(Base):
    """Raw POS event data as received from connectors."""

    __tablename__ = "pos_raw_events"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # csv, webhook, etc.
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)


class PosSalesLine(Base):
    """Normalized POS sales line (after processing raw events)."""

    __tablename__ = "pos_sales_lines"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    pos_item_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_refund: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    raw_event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pos_raw_events.id", ondelete="SET NULL"), nullable=True
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="pos_sales_lines")


# Forward references
from app.models.location import Location
