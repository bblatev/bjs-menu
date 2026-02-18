"""Abstract base class for delivery platform providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DeliveryProvider(ABC):
    """Base interface for delivery platform integrations."""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name (e.g., 'doordash', 'ubereats')."""

    @abstractmethod
    async def accept_order(self, order_id: str) -> Dict[str, Any]:
        """Accept an incoming delivery order."""

    @abstractmethod
    async def reject_order(self, order_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject an incoming delivery order."""

    @abstractmethod
    async def update_order_status(self, order_id: str, status: str) -> Dict[str, Any]:
        """Update order status (preparing, ready_for_pickup, etc.)."""

    @abstractmethod
    async def get_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get orders from the platform."""

    @abstractmethod
    async def sync_menu(self, menu_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync local menu items to the delivery platform."""

    @abstractmethod
    async def cancel_order(self, order_id: str, reason: str = "") -> Dict[str, Any]:
        """Cancel an order."""

    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature from the platform."""
        return True  # Override per platform
