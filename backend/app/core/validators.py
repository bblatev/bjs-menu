"""Reusable parameter validators and optimistic locking utilities."""

from typing import Annotated

from fastapi import HTTPException, Path, Query
from sqlalchemy.orm import Session

# Positive integer ID validator for path parameters
PositiveIntId = Annotated[int, Path(gt=0, description="Resource ID (must be positive)")]

# Optional positive int for query params
PositiveIntQuery = Annotated[int, Query(gt=0)]


def optimistic_update(db: Session, instance, expected_version: int) -> None:
    """Perform optimistic locking check before update.

    Raises 409 Conflict if the record was modified by another user since it was read.
    Automatically increments the version counter on success.
    """
    if hasattr(instance, "version"):
        if instance.version != expected_version:
            raise HTTPException(
                status_code=409,
                detail="Record was modified by another user. Please refresh and try again.",
            )
        instance.version += 1
