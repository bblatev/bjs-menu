"""Glovo Partner API integration."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.delivery.base import DeliveryProvider

logger = logging.getLogger(__name__)

GLOVO_API_BASE = "https://storeapi.glovoapp.com"


class GlovoProvider(DeliveryProvider):
    """Glovo Partner API client."""

    platform_name = "glovo"

    def __init__(self):
        self._api_key = getattr(settings, "glovo_api_key", None) or ""
        self._store_id = getattr(settings, "glovo_store_id", None) or ""

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._store_id)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": self._api_key, "Content-Type": "application/json"}

    async def accept_order(self, order_id: str) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "Glovo not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{GLOVO_API_BASE}/webhook/stores/{self._store_id}/orders/{order_id}",
                headers=self._headers(),
                json={"action": "ACCEPT"},
            )
            resp.raise_for_status()
            return resp.json()

    async def reject_order(self, order_id: str, reason: str = "") -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "Glovo not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{GLOVO_API_BASE}/webhook/stores/{self._store_id}/orders/{order_id}",
                headers=self._headers(),
                json={"action": "CANCEL", "cancel_reason": reason or "STORE_BUSY"},
            )
            resp.raise_for_status()
            return resp.json()

    async def update_order_status(self, order_id: str, status: str) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "Glovo not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{GLOVO_API_BASE}/webhook/stores/{self._store_id}/orders/{order_id}",
                headers=self._headers(),
                json={"action": "READY_FOR_PICKUP" if status == "ready" else status.upper()},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_configured:
            return []
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GLOVO_API_BASE}/webhook/stores/{self._store_id}/orders",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json().get("orders", [])

    async def sync_menu(self, menu_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "Glovo not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{GLOVO_API_BASE}/webhook/stores/{self._store_id}/menu",
                headers=self._headers(),
                json={"sections": menu_items},
            )
            resp.raise_for_status()
            return resp.json()

    async def cancel_order(self, order_id: str, reason: str = "") -> Dict[str, Any]:
        return await self.reject_order(order_id, reason)
