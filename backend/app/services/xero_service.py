"""Xero accounting integration service (OAuth2 + REST API).

Implements the Xero API v2 for:
- OAuth2 authorization flow
- Invoice creation and sync
- Contact (customer/supplier) sync
- Chart of accounts retrieval
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

XERO_AUTH_URL = "https://login.xero.com/identity/connect/authorize"
XERO_TOKEN_URL = "https://identity.xero.com/connect/token"
XERO_API_BASE = "https://api.xero.com/api.xro/2.0"
XERO_CONNECTIONS_URL = "https://api.xero.com/connections"


class XeroService:
    """Xero accounting API client."""

    def __init__(self):
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._tenant_id: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    @property
    def is_configured(self) -> bool:
        return bool(
            getattr(settings, "xero_client_id", None)
            and getattr(settings, "xero_client_secret", None)
        )

    def get_authorization_url(self, redirect_uri: str, state: str = "") -> str:
        """Generate Xero OAuth2 authorization URL."""
        params = {
            "response_type": "code",
            "client_id": settings.xero_client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email accounting.transactions accounting.contacts accounting.settings offline_access",
            "state": state,
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{XERO_AUTH_URL}?{qs}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access/refresh tokens."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                XERO_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                auth=(settings.xero_client_id, settings.xero_client_secret),
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            self._refresh_token = data.get("refresh_token")

            # Get tenant ID
            conns = await client.get(
                XERO_CONNECTIONS_URL,
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            if conns.status_code == 200 and conns.json():
                self._tenant_id = conns.json()[0]["tenantId"]

            return {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "tenant_id": self._tenant_id,
            }

    async def refresh_tokens(self) -> bool:
        """Refresh expired access token."""
        if not self._refresh_token:
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    XERO_TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self._refresh_token,
                    },
                    auth=(settings.xero_client_id, settings.xero_client_secret),
                )
                resp.raise_for_status()
                data = resp.json()
                self._access_token = data["access_token"]
                self._refresh_token = data.get("refresh_token", self._refresh_token)
                return True
        except Exception as e:
            logger.error(f"Xero token refresh failed: {e}")
            return False

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "xero-tenant-id": self._tenant_id or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_accounts(self) -> List[Dict]:
        """Get chart of accounts."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{XERO_API_BASE}/Accounts", headers=self._headers())
            resp.raise_for_status()
            return resp.json().get("Accounts", [])

    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict:
        """Create a sales invoice in Xero."""
        payload = {"Invoices": [invoice_data]}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{XERO_API_BASE}/Invoices",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            invoices = resp.json().get("Invoices", [])
            return invoices[0] if invoices else {}

    async def sync_contacts(self, contacts: List[Dict[str, Any]]) -> Dict:
        """Create or update contacts (customers/suppliers)."""
        payload = {"Contacts": contacts}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{XERO_API_BASE}/Contacts",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_invoices(
        self, status: Optional[str] = None, modified_since: Optional[str] = None
    ) -> List[Dict]:
        """Get invoices, optionally filtered."""
        params = {}
        if status:
            params["where"] = f'Status=="{status}"'
        headers = self._headers()
        if modified_since:
            headers["If-Modified-Since"] = modified_since
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{XERO_API_BASE}/Invoices", headers=headers, params=params
            )
            resp.raise_for_status()
            return resp.json().get("Invoices", [])


xero_service = XeroService()
