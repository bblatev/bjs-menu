"""
Third-Party Integrations Service
Implements integrations with labor, accounting, and automation platforms
Competitor: Toast 7shifts, Square Homebase, MarginEdge, Zapier
"""

import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import Session

from app.models.gap_features_models import (
    IntegrationCredential, ZapierWebhook
)


class IntegrationCredentialService:
    """
    Service for managing third-party integration credentials securely.
    """

    def __init__(self, db: Session):
        self.db = db

    async def store_credential(
        self,
        venue_id: UUID,
        integration_type: str,  # '7shifts', 'homebase', 'marginedge', 'quickbooks', 'xero', etc.
        credentials: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> IntegrationCredential:
        """Store encrypted integration credentials."""
        from app.core.security import encrypt_data

        # Check if credential already exists
        result = await self.db.execute(
            select(IntegrationCredential).where(
                and_(
                    IntegrationCredential.venue_id == venue_id,
                    IntegrationCredential.integration_type == integration_type
                )
            )
        )
        existing = result.scalar_one_or_none()

        encrypted_credentials = encrypt_data(json.dumps(credentials))

        if existing:
            existing.encrypted_credentials = encrypted_credentials
            existing.metadata = metadata or {}
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        credential = IntegrationCredential(
            id=uuid4(),
            venue_id=venue_id,
            integration_type=integration_type,
            encrypted_credentials=encrypted_credentials,
            metadata=metadata or {},
            is_active=True,
            created_at=datetime.utcnow()
        )
        self.db.add(credential)
        await self.db.commit()
        await self.db.refresh(credential)
        return credential

    async def get_credential(
        self,
        venue_id: UUID,
        integration_type: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt integration credentials."""
        from app.core.security import decrypt_data

        result = await self.db.execute(
            select(IntegrationCredential).where(
                and_(
                    IntegrationCredential.venue_id == venue_id,
                    IntegrationCredential.integration_type == integration_type,
                    IntegrationCredential.is_active == True
                )
            )
        )
        credential = result.scalar_one_or_none()

        if not credential:
            return None

        decrypted = decrypt_data(credential.encrypted_credentials)
        return json.loads(decrypted)

    async def delete_credential(
        self,
        venue_id: UUID,
        integration_type: str
    ) -> bool:
        """Delete integration credentials."""
        result = await self.db.execute(
            select(IntegrationCredential).where(
                and_(
                    IntegrationCredential.venue_id == venue_id,
                    IntegrationCredential.integration_type == integration_type
                )
            )
        )
        credential = result.scalar_one_or_none()

        if credential:
            credential.is_active = False
            credential.encrypted_credentials = ""
            await self.db.commit()
            return True
        return False

    async def list_integrations(
        self,
        venue_id: UUID
    ) -> List[Dict[str, Any]]:
        """List all configured integrations for a venue."""
        result = await self.db.execute(
            select(IntegrationCredential).where(
                and_(
                    IntegrationCredential.venue_id == venue_id,
                    IntegrationCredential.is_active == True
                )
            )
        )
        credentials = result.scalars().all()

        return [
            {
                "id": str(c.id),
                "integration_type": c.integration_type,
                "is_connected": True,
                "connected_at": c.created_at.isoformat(),
                "last_sync": c.last_sync_at.isoformat() if c.last_sync_at else None,
                "metadata": c.metadata
            }
            for c in credentials
        ]


class SevenShiftsIntegration:
    """
    Integration with 7shifts labor management platform.
    Syncs schedules, time tracking, and labor costs.
    """

    BASE_URL = "https://api.7shifts.com/v2"

    def __init__(self, db: Session, venue_id: UUID):
        self.db = db
        self.venue_id = venue_id
        self.credential_service = IntegrationCredentialService(db)

    async def _get_client(self):
        """Get authenticated HTTP client."""
        import httpx

        credentials = await self.credential_service.get_credential(
            self.venue_id,
            "7shifts"
        )
        if not credentials:
            raise ValueError("7shifts integration not configured")

        return httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {credentials['access_token']}",
                "Content-Type": "application/json"
            }
        )

    async def sync_employees(self) -> Dict[str, Any]:
        """Sync employees from 7shifts to local database."""
        async with await self._get_client() as client:
            response = await client.get("/users")
            response.raise_for_status()
            users = response.json().get("data", [])

            synced = []
            for user in users:
                # Map 7shifts user to local staff
                synced.append({
                    "external_id": user["id"],
                    "name": f"{user['first_name']} {user['last_name']}",
                    "email": user.get("email"),
                    "role": user.get("role_names", []),
                    "hourly_rate": user.get("wage_cents", 0) / 100
                })

            return {
                "synced_count": len(synced),
                "employees": synced
            }

    async def sync_schedules(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Sync schedules from 7shifts."""
        async with await self._get_client() as client:
            response = await client.get(
                "/shifts",
                params={
                    "start[gte]": start_date.isoformat(),
                    "end[lte]": end_date.isoformat()
                }
            )
            response.raise_for_status()
            shifts = response.json().get("data", [])

            return {
                "synced_count": len(shifts),
                "shifts": [
                    {
                        "external_id": s["id"],
                        "employee_id": s["user_id"],
                        "start": s["start"],
                        "end": s["end"],
                        "role": s.get("role", {}).get("name"),
                        "break_minutes": s.get("break_minutes", 0)
                    }
                    for s in shifts
                ]
            }

    async def push_sales_data(
        self,
        date: datetime,
        sales_data: Dict[str, Any]
    ) -> bool:
        """Push sales data to 7shifts for labor % calculations."""
        async with await self._get_client() as client:
            response = await client.post(
                "/sales",
                json={
                    "date": date.strftime("%Y-%m-%d"),
                    "total": sales_data.get("total_sales", 0),
                    "labor_cost": sales_data.get("labor_cost", 0),
                    "labor_hours": sales_data.get("labor_hours", 0)
                }
            )
            return response.status_code < 400


class HomebaseIntegration:
    """
    Integration with Homebase scheduling and time tracking.
    """

    BASE_URL = "https://api.joinhomebase.com/v1"

    def __init__(self, db: Session, venue_id: UUID):
        self.db = db
        self.venue_id = venue_id
        self.credential_service = IntegrationCredentialService(db)

    async def _get_client(self):
        """Get authenticated HTTP client."""
        import httpx

        credentials = await self.credential_service.get_credential(
            self.venue_id,
            "homebase"
        )
        if not credentials:
            raise ValueError("Homebase integration not configured")

        return httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {credentials['access_token']}",
                "Content-Type": "application/json"
            }
        )

    async def sync_timecards(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Sync timecards from Homebase."""
        async with await self._get_client() as client:
            response = await client.get(
                "/timecards",
                params={
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }
            )
            response.raise_for_status()
            timecards = response.json().get("timecards", [])

            return {
                "synced_count": len(timecards),
                "timecards": [
                    {
                        "external_id": tc["id"],
                        "employee_id": tc["employee_id"],
                        "clock_in": tc["clock_in"],
                        "clock_out": tc.get("clock_out"),
                        "break_minutes": tc.get("break_minutes", 0),
                        "total_hours": tc.get("total_hours", 0)
                    }
                    for tc in timecards
                ]
            }

    async def get_labor_report(
        self,
        date: datetime
    ) -> Dict[str, Any]:
        """Get labor report from Homebase."""
        async with await self._get_client() as client:
            response = await client.get(
                "/reports/labor",
                params={"date": date.strftime("%Y-%m-%d")}
            )
            response.raise_for_status()
            return response.json()


class MarginEdgeIntegration:
    """
    Integration with MarginEdge invoice processing and food cost management.
    """

    BASE_URL = "https://api.marginedge.com/v1"

    def __init__(self, db: Session, venue_id: UUID):
        self.db = db
        self.venue_id = venue_id
        self.credential_service = IntegrationCredentialService(db)

    async def _get_client(self):
        """Get authenticated HTTP client."""
        import httpx

        credentials = await self.credential_service.get_credential(
            self.venue_id,
            "marginedge"
        )
        if not credentials:
            raise ValueError("MarginEdge integration not configured")

        return httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {credentials['access_token']}",
                "Content-Type": "application/json"
            }
        )

    async def sync_invoices(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Sync processed invoices from MarginEdge."""
        async with await self._get_client() as client:
            response = await client.get(
                "/invoices",
                params={
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "status": "processed"
                }
            )
            response.raise_for_status()
            invoices = response.json().get("invoices", [])

            return {
                "synced_count": len(invoices),
                "invoices": [
                    {
                        "external_id": inv["id"],
                        "vendor": inv["vendor_name"],
                        "invoice_number": inv["invoice_number"],
                        "date": inv["invoice_date"],
                        "total": inv["total"],
                        "items": inv.get("line_items", [])
                    }
                    for inv in invoices
                ]
            }

    async def get_food_cost_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get food cost report from MarginEdge."""
        async with await self._get_client() as client:
            response = await client.get(
                "/reports/food-cost",
                params={
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }
            )
            response.raise_for_status()
            return response.json()

    async def upload_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Upload an invoice for processing."""
        import httpx

        credentials = await self.credential_service.get_credential(
            self.venue_id,
            "marginedge"
        )
        if not credentials:
            raise ValueError("MarginEdge integration not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/invoices/upload",
                headers={"Authorization": f"Bearer {credentials['access_token']}"},
                files={"file": (filename, file_content)}
            )
            response.raise_for_status()
            return response.json()


class ZapierService:
    """
    Zapier integration service for automation workflows.
    """

    def __init__(self, db: Session):
        self.db = db

    async def create_webhook(
        self,
        venue_id: UUID,
        event_type: str,
        webhook_url: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> ZapierWebhook:
        """Create a Zapier webhook subscription."""
        # Generate webhook secret for verification
        import secrets
        webhook_secret = secrets.token_urlsafe(32)

        webhook = ZapierWebhook(
            id=uuid4(),
            venue_id=venue_id,
            event_type=event_type,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            filters=filters or {},
            is_active=True,
            created_at=datetime.utcnow()
        )
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def delete_webhook(
        self,
        webhook_id: UUID,
        venue_id: UUID
    ) -> bool:
        """Delete a Zapier webhook."""
        result = await self.db.execute(
            select(ZapierWebhook).where(
                and_(
                    ZapierWebhook.id == webhook_id,
                    ZapierWebhook.venue_id == venue_id
                )
            )
        )
        webhook = result.scalar_one_or_none()
        if webhook:
            await self.db.delete(webhook)
            await self.db.commit()
            return True
        return False

    async def list_webhooks(
        self,
        venue_id: UUID
    ) -> List[ZapierWebhook]:
        """List all webhooks for a venue."""
        result = await self.db.execute(
            select(ZapierWebhook).where(
                and_(
                    ZapierWebhook.venue_id == venue_id,
                    ZapierWebhook.is_active == True
                )
            )
        )
        return list(result.scalars().all())

    async def trigger_webhooks(
        self,
        venue_id: UUID,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trigger all webhooks for an event type."""
        import httpx

        result = await self.db.execute(
            select(ZapierWebhook).where(
                and_(
                    ZapierWebhook.venue_id == venue_id,
                    ZapierWebhook.event_type == event_type,
                    ZapierWebhook.is_active == True
                )
            )
        )
        webhooks = result.scalars().all()

        results = {"triggered": 0, "failed": 0, "errors": []}

        for webhook in webhooks:
            # Check filters
            if not self._matches_filters(payload, webhook.filters):
                continue

            # Prepare payload with signature
            timestamp = datetime.utcnow().isoformat()
            signed_payload = {
                "event": event_type,
                "timestamp": timestamp,
                "venue_id": str(venue_id),
                "data": payload
            }

            # Generate HMAC signature
            signature = hmac.new(
                webhook.webhook_secret.encode(),
                json.dumps(signed_payload, sort_keys=True).encode(),
                hashlib.sha256
            ).hexdigest()

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        webhook.webhook_url,
                        json=signed_payload,
                        headers={
                            "X-Zver-Signature": signature,
                            "X-Zver-Timestamp": timestamp
                        },
                        timeout=10.0
                    )
                    if response.status_code < 400:
                        results["triggered"] += 1
                        webhook.last_triggered_at = datetime.utcnow()
                        webhook.trigger_count = (webhook.trigger_count or 0) + 1
                    else:
                        results["failed"] += 1
                        webhook.last_error = f"HTTP {response.status_code}"
                        results["errors"].append({
                            "webhook_id": str(webhook.id),
                            "error": webhook.last_error
                        })
            except Exception as e:
                results["failed"] += 1
                webhook.last_error = str(e)
                results["errors"].append({
                    "webhook_id": str(webhook.id),
                    "error": str(e)
                })

        await self.db.commit()
        return results

    def _matches_filters(
        self,
        payload: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> bool:
        """Check if payload matches webhook filters."""
        if not filters:
            return True

        for key, value in filters.items():
            payload_value = payload.get(key)
            if isinstance(value, list):
                if payload_value not in value:
                    return False
            elif payload_value != value:
                return False

        return True

    def get_available_events(self) -> List[Dict[str, Any]]:
        """Get list of available webhook event types."""
        return [
            {
                "event": "order.created",
                "description": "Triggered when a new order is created",
                "payload_example": {
                    "order_id": "uuid",
                    "table_number": 5,
                    "total": 45.99,
                    "items_count": 3
                }
            },
            {
                "event": "order.completed",
                "description": "Triggered when an order is marked as completed",
                "payload_example": {
                    "order_id": "uuid",
                    "total": 45.99,
                    "payment_method": "card"
                }
            },
            {
                "event": "payment.received",
                "description": "Triggered when a payment is received",
                "payload_example": {
                    "payment_id": "uuid",
                    "order_id": "uuid",
                    "amount": 45.99,
                    "method": "card"
                }
            },
            {
                "event": "reservation.created",
                "description": "Triggered when a new reservation is made",
                "payload_example": {
                    "reservation_id": "uuid",
                    "customer_name": "John Doe",
                    "party_size": 4,
                    "datetime": "2024-01-15T19:00:00Z"
                }
            },
            {
                "event": "stock.low",
                "description": "Triggered when stock falls below minimum threshold",
                "payload_example": {
                    "item_id": "uuid",
                    "item_name": "Tomatoes",
                    "current_quantity": 5,
                    "min_quantity": 10
                }
            },
            {
                "event": "shift.started",
                "description": "Triggered when a staff member clocks in",
                "payload_example": {
                    "staff_id": "uuid",
                    "staff_name": "Jane Smith",
                    "clock_in_time": "2024-01-15T09:00:00Z"
                }
            },
            {
                "event": "shift.ended",
                "description": "Triggered when a staff member clocks out",
                "payload_example": {
                    "staff_id": "uuid",
                    "staff_name": "Jane Smith",
                    "clock_out_time": "2024-01-15T17:00:00Z",
                    "hours_worked": 8.0
                }
            },
            {
                "event": "review.received",
                "description": "Triggered when a customer leaves a review",
                "payload_example": {
                    "review_id": "uuid",
                    "rating": 5,
                    "comment": "Great food!"
                }
            },
            {
                "event": "daily.summary",
                "description": "Triggered daily with sales summary",
                "payload_example": {
                    "date": "2024-01-15",
                    "total_sales": 5432.10,
                    "order_count": 87,
                    "avg_ticket": 62.44
                }
            }
        ]


class AccountingSyncService:
    """
    Service for syncing data with accounting platforms (QuickBooks, Xero, etc.)
    """

    def __init__(self, db: Session, venue_id: UUID):
        self.db = db
        self.venue_id = venue_id
        self.credential_service = IntegrationCredentialService(db)

    async def sync_sales_to_quickbooks(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Sync sales data to QuickBooks."""
        import httpx

        credentials = await self.credential_service.get_credential(
            self.venue_id,
            "quickbooks"
        )
        if not credentials:
            raise ValueError("QuickBooks integration not configured")

        # Get sales data
        from app.models.orders import Order
        result = await self.db.execute(
            select(Order).where(
                and_(
                    Order.venue_id == self.venue_id,
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status == "completed"
                )
            )
        )
        orders = result.scalars().all()

        # Aggregate by day
        daily_sales = {}
        for order in orders:
            day = order.created_at.strftime("%Y-%m-%d")
            if day not in daily_sales:
                daily_sales[day] = {"total": 0, "tax": 0, "count": 0}
            daily_sales[day]["total"] += float(order.total)
            daily_sales[day]["tax"] += float(getattr(order, 'tax_amount', 0))
            daily_sales[day]["count"] += 1

        # Push to QuickBooks
        synced = 0
        async with httpx.AsyncClient() as client:
            for day, data in daily_sales.items():
                response = await client.post(
                    f"https://quickbooks.api.intuit.com/v3/company/{credentials['realm_id']}/salesreceipt",
                    headers={
                        "Authorization": f"Bearer {credentials['access_token']}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "Line": [{
                            "Amount": data["total"],
                            "DetailType": "SalesItemLineDetail",
                            "SalesItemLineDetail": {
                                "ItemRef": {"value": credentials.get("sales_item_id", "1")}
                            }
                        }],
                        "TxnDate": day,
                        "PrivateNote": f"POS Sales - {data['count']} orders"
                    }
                )
                if response.status_code < 400:
                    synced += 1

        return {
            "synced_days": synced,
            "total_days": len(daily_sales),
            "total_sales": sum(d["total"] for d in daily_sales.values())
        }

    async def sync_invoices_to_xero(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Sync purchase invoices to Xero."""
        import httpx

        credentials = await self.credential_service.get_credential(
            self.venue_id,
            "xero"
        )
        if not credentials:
            raise ValueError("Xero integration not configured")

        # Get purchase orders
        from app.models.purchase_orders import PurchaseOrder
        result = await self.db.execute(
            select(PurchaseOrder).where(
                and_(
                    PurchaseOrder.venue_id == self.venue_id,
                    PurchaseOrder.created_at >= start_date,
                    PurchaseOrder.created_at <= end_date,
                    PurchaseOrder.status == "received"
                )
            )
        )
        purchase_orders = result.scalars().all()

        synced = 0
        async with httpx.AsyncClient() as client:
            for po in purchase_orders:
                response = await client.post(
                    "https://api.xero.com/api.xro/2.0/Invoices",
                    headers={
                        "Authorization": f"Bearer {credentials['access_token']}",
                        "xero-tenant-id": credentials["tenant_id"],
                        "Content-Type": "application/json"
                    },
                    json={
                        "Type": "ACCPAY",
                        "Contact": {"Name": getattr(po, 'supplier_name', 'Supplier')},
                        "Date": po.created_at.strftime("%Y-%m-%d"),
                        "DueDate": (po.created_at + timedelta(days=30)).strftime("%Y-%m-%d"),
                        "LineItems": [{
                            "Description": f"Purchase Order {po.id}",
                            "Quantity": 1,
                            "UnitAmount": float(po.total_amount),
                            "AccountCode": credentials.get("expense_account", "400")
                        }],
                        "Reference": str(po.id)
                    }
                )
                if response.status_code < 400:
                    synced += 1

        return {
            "synced_invoices": synced,
            "total_invoices": len(purchase_orders)
        }
