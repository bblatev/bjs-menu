"""Pagination schemas and utilities."""

from typing import Generic, List, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters."""

    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum items to return")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[T]
    total: int = Field(description="Total number of items matching the query")
    skip: int = Field(description="Number of items skipped")
    limit: int = Field(description="Maximum items requested")
    has_more: bool = Field(description="Whether more items are available")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        skip: int,
        limit: int,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        return cls(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + len(items)) < total,
        )


def paginate_query(query, skip: int = 0, limit: int = 50):
    """
    Apply pagination to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        skip: Number of items to skip
        limit: Maximum items to return

    Returns:
        Tuple of (paginated items, total count)
    """
    # Get total count (before pagination)
    total = query.count()

    # Apply pagination
    items = query.offset(skip).limit(limit).all()

    return items, total
