"""Model-level validation utilities for data integrity.

Provides reusable validators that enforce business rules at the ORM level,
preventing invalid data from reaching the database regardless of which
API endpoint or service writes the data.
"""

from decimal import Decimal


def non_negative(key: str, value):
    """Validate that a numeric value is >= 0."""
    if value is not None:
        v = Decimal(str(value)) if not isinstance(value, Decimal) else value
        if v < 0:
            raise ValueError(f"{key} cannot be negative, got {value}")
    return value


def positive(key: str, value):
    """Validate that a numeric value is > 0."""
    if value is not None:
        v = Decimal(str(value)) if not isinstance(value, Decimal) else value
        if v <= 0:
            raise ValueError(f"{key} must be positive, got {value}")
    return value


def percentage(key: str, value):
    """Validate that a value is between 0 and 100 inclusive."""
    if value is not None:
        v = float(value)
        if v < 0 or v > 100:
            raise ValueError(f"{key} must be between 0 and 100, got {value}")
    return value


def rating_score(key: str, value):
    """Validate that a rating value is between 0 and 5."""
    if value is not None:
        v = float(value)
        if v < 0 or v > 5:
            raise ValueError(f"{key} must be between 0 and 5, got {value}")
    return value
