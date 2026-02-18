"""Wolt Merchant API integration."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.delivery.base import DeliveryProvider

logger = logging.getLogger(__name__)

WOLT_API_BASE = "https://restaurant-api.wolt.com/v1"


class WoltProvider(DeliveryProvider):
    """Wolt Merchant API client."""

    platform_name = "wolt"

    def __init__(self):
        self._api_key = getattr(settings, "wolt_api_key", None) or ""
        self._venue_id = getattr(settings, "wolt_venue_id", None) or ""

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._venue_id)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    async def accept_order(self, order_id: str) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "Wolt not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{WOLT_API_BASE}/orders/{order_id}/accept", headers=self._headers()
            )
            resp.raise_for_status()
            return resp.json()

    async def reject_order(self, order_id: str, reason: str = "") -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "Wolt not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{WOLT_API_BASE}/orders/{order_id}/reject",
                headers=self._headers(),
                json={"reason": reason or "busy"},
            )
            resp.raise_for_status()
            return resp.json()

    async def update_order_status(self, order_id: str, status: str) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "Wolt not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{WOLT_API_BASE}/orders/{order_id}/status",
                headers=self._headers(),
                json={"status": status},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_configured:
            return []
        params = {"venue_id": self._venue_id}
        if status:
            params["status"] = status
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{WOLT_API_BASE}/orders", headers=self._headers(), params=params
            )
            resp.raise_for_status()
            return resp.json().get("orders", [])

    async def sync_menu(self, menu_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "Wolt not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{WOLT_API_BASE}/venues/{self._venue_id}/menu",
                headers=self._headers(),
                json={"categories": menu_items},
            )
            resp.raise_for_status()
            return resp.json()

    async def cancel_order(self, order_id: str, reason: str = "") -> Dict[str, Any]:
        return await self.reject_order(order_id, reason)
