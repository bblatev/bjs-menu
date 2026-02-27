"""Standardized API response helpers.

All list endpoints should return a consistent envelope:
    {"items": [...], "total": <int>}

Paginated endpoints additionally include:
    {"items": [...], "total": <int>, "skip": <int>, "limit": <int>, "has_more": <bool>}

Single-item endpoints return the object directly (no wrapper).

Use list_response() for simple lists and paginated_response() for paginated queries.
The existing PaginatedResponse.create() in app.schemas.pagination also follows
this convention and remains the preferred choice for routes that already use it.
"""

from typing import Any, List, Optional


def list_response(
    items: list,
    total: Optional[int] = None,
) -> dict:
    """Wrap a list in the standard envelope.

    Args:
        items: The list of serialized items.
        total: Total count (defaults to len(items) when the full list is returned).

    Returns:
        {"items": items, "total": total}
    """
    return {
        "items": items,
        "total": total if total is not None else len(items),
    }


def paginated_response(
    items: list,
    total: int,
    skip: int = 0,
    limit: int = 50,
) -> dict:
    """Wrap a paginated list in the standard envelope.

    Args:
        items: The page of serialized items.
        total: Total count across all pages.
        skip: Number of items skipped.
        limit: Page size requested.

    Returns:
        {"items": items, "total": total, "skip": skip, "limit": limit, "has_more": bool}
    """
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(items)) < total,
    }
