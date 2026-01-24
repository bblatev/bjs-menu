"""Base class for POS connectors.

This defines the interface that all POS connectors must implement.
To add a new POS vendor connector:
1. Create a new file in this directory
2. Subclass POSConnector
3. Implement all abstract methods
4. Register the connector in the factory
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass
class NormalizedSalesLine:
    """Normalized sales line from any POS system."""

    timestamp: datetime
    pos_item_id: str | None
    item_name: str
    qty: Decimal
    is_refund: bool
    location_id: int | None = None
    raw_data: dict | None = None  # Original data for debugging


class POSConnector(ABC):
    """Abstract base class for POS system connectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Connector name (e.g., 'csv', 'toast', 'square')."""
        pass

    @abstractmethod
    def parse_data(self, raw_data: Any) -> list[NormalizedSalesLine]:
        """
        Parse raw POS data into normalized sales lines.

        Args:
            raw_data: Raw data from the POS (format depends on connector)

        Returns:
            List of normalized sales lines
        """
        pass

    @abstractmethod
    def validate_data(self, raw_data: Any) -> tuple[bool, list[str]]:
        """
        Validate raw POS data before parsing.

        Args:
            raw_data: Raw data to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        pass


class POSConnectorFactory:
    """Factory for creating POS connectors."""

    _connectors: dict[str, type[POSConnector]] = {}

    @classmethod
    def register(cls, connector_class: type[POSConnector]) -> type[POSConnector]:
        """Register a connector class. Can be used as a decorator."""
        # Create an instance to get the name
        instance = connector_class()
        cls._connectors[instance.name] = connector_class
        return connector_class

    @classmethod
    def get(cls, name: str) -> POSConnector:
        """Get a connector instance by name."""
        if name not in cls._connectors:
            available = ", ".join(cls._connectors.keys())
            raise ValueError(f"Unknown POS connector: {name}. Available: {available}")
        return cls._connectors[name]()

    @classmethod
    def list_connectors(cls) -> list[str]:
        """List available connector names."""
        return list(cls._connectors.keys())
