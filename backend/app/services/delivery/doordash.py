"""DoorDash Drive API integration."""

import hashlib
import hmac
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.delivery.base import DeliveryProvider

logger = logging.getLogger(__name__)

DOORDASH_API_BASE = "https://openapi.doordash.com"


class DoorDashProvider(DeliveryProvider):
    """DoorDash Drive API client."""

    platform_name = "doordash"

    def __init__(self):
        self._api_key = getattr(settings, "doordash_api_key", None) or ""
        self._developer_id = settings.doordash_developer_id
        self._key_id = settings.doordash_key_id
        self._signing_secret = settings.doordash_signing_secret
        self._store_id = settings.doordash_store_id

    @property
    def is_configured(self) -> bool:
        return bool(self._developer_id and self._key_id and self._signing_secret)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def accept_order(self, order_id: str) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "DoorDash not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DOORDASH_API_BASE}/drive/v2/deliveries/{order_id}/accept",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def reject_order(self, order_id: str, reason: str = "") -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "DoorDash not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DOORDASH_API_BASE}/drive/v2/deliveries/{order_id}/cancel",
                headers=self._headers(),
                json={"reason": reason or "restaurant_too_busy"},
            )
            resp.raise_for_status()
            return resp.json()

    async def update_order_status(self, order_id: str, status: str) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "DoorDash not configured"}
        status_map = {
            "preparing": "confirmed",
            "ready_for_pickup": "picked_up",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{DOORDASH_API_BASE}/drive/v2/deliveries/{order_id}",
                headers=self._headers(),
                json={"status": status_map.get(status, status)},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_configured:
            return []
        params = {}
        if status:
            params["status"] = status
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{DOORDASH_API_BASE}/drive/v2/deliveries",
                headers=self._headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json().get("deliveries", [])

    async def sync_menu(self, menu_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "DoorDash not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{DOORDASH_API_BASE}/drive/v2/stores/{self._store_id}/menu",
                headers=self._headers(),
                json={"items": menu_items},
            )
            resp.raise_for_status()
            return resp.json()

    async def cancel_order(self, order_id: str, reason: str = "") -> Dict[str, Any]:
        return await self.reject_order(order_id, reason)

    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        if not self._signing_secret:
            return False
        expected = hmac.new(
            self._signing_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
