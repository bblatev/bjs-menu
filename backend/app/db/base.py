"""SQLAlchemy declarative base and common utilities."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VersionMixin:
    """Optimistic locking via a version counter.

    Models using this mixin gain a ``version`` column that starts at 1
    and should be incremented on every update.  Call ``check_version()``
    before committing to detect concurrent modifications.
    """

    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    def check_version(self, expected: Optional[int]) -> None:
        """Raise ValueError if *expected* doesn't match current version."""
        if expected is not None and expected != self.version:
            raise ValueError(
                f"Version conflict: expected {expected}, current {self.version}"
            )


class SoftDeleteMixin:
    """Soft-delete support via a ``deleted_at`` timestamp.

    Instead of physically removing rows, set ``deleted_at`` to the
    current UTC time.  Use ``not_deleted()`` as a query filter.
    """

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )

    def soft_delete(self) -> None:
        """Mark this row as deleted."""
        from datetime import timezone
        self.deleted_at = datetime.now(timezone.utc)

    @classmethod
    def not_deleted(cls):
        """SQLAlchemy filter expression: ``WHERE deleted_at IS NULL``."""
        return cls.deleted_at.is_(None)
