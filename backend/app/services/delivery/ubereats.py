"""Uber Eats API integration."""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.delivery.base import DeliveryProvider

logger = logging.getLogger(__name__)

UBEREATS_API_BASE = "https://api.uber.com/v1/eats"


class UberEatsProvider(DeliveryProvider):
    """Uber Eats API client."""

    platform_name = "ubereats"

    def __init__(self):
        self._client_id = settings.ubereats_client_id
        self._client_secret = settings.ubereats_client_secret
        self._store_id = settings.ubereats_store_id
        self._webhook_secret = settings.ubereats_webhook_secret
        self._access_token: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret and self._store_id)

    async def _ensure_token(self):
        if self._access_token:
            return
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://login.uber.com/oauth/v2/token",
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "grant_type": "client_credentials",
                    "scope": "eats.store eats.order eats.store.orders.read",
                },
            )
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    async def accept_order(self, order_id: str) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "UberEats not configured"}
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{UBEREATS_API_BASE}/orders/{order_id}/accept_pos_order",
                headers=self._headers(),
                json={"reason": "accepted"},
            )
            resp.raise_for_status()
            return resp.json()

    async def reject_order(self, order_id: str, reason: str = "") -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "UberEats not configured"}
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{UBEREATS_API_BASE}/orders/{order_id}/deny_pos_order",
                headers=self._headers(),
                json={"reason": {"explanation": reason or "Store is too busy"}},
            )
            resp.raise_for_status()
            return resp.json()

    async def update_order_status(self, order_id: str, status: str) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "UberEats not configured"}
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{UBEREATS_API_BASE}/orders/{order_id}/ready_for_pickup",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_configured:
            return []
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{UBEREATS_API_BASE}/stores/{self._store_id}/orders",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json().get("orders", [])

    async def sync_menu(self, menu_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.is_configured:
            return {"error": "UberEats not configured"}
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{UBEREATS_API_BASE}/stores/{self._store_id}/menus",
                headers=self._headers(),
                json={"menus": [{"items": menu_items}]},
            )
            resp.raise_for_status()
            return resp.json()

    async def cancel_order(self, order_id: str, reason: str = "") -> Dict[str, Any]:
        return await self.reject_order(order_id, reason)
