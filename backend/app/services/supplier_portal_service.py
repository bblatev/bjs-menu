"""Supplier Self-Service Portal.

Provides a portal for suppliers to:
- View and confirm purchase orders
- Submit invoices with line items
- Update delivery schedules and ETAs
- View payment status and history
- Update product catalogs and pricing
- Communicate with restaurant buyers
"""

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class SupplierPortalService:
    """Supplier self-service portal backend."""

    def __init__(self):
        self._portal_tokens: Dict[str, Dict[str, Any]] = {}
        self._invoices: List[Dict[str, Any]] = []
        self._delivery_updates: List[Dict[str, Any]] = []
        self._messages: List[Dict[str, Any]] = []
        self._catalog_updates: List[Dict[str, Any]] = []
        self._next_invoice_id = 1
        self._next_message_id = 1

    # ------------------------------------------------------------------
    # Portal Access
    # ------------------------------------------------------------------

    def generate_portal_token(
        self,
        supplier_id: int,
        supplier_name: str,
        contact_email: str,
        permissions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a secure portal access token for a supplier."""
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        self._portal_tokens[token_hash] = {
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "contact_email": contact_email,
            "permissions": permissions or [
                "view_orders", "confirm_orders", "submit_invoices",
                "update_delivery", "view_payments", "update_catalog",
                "send_messages",
            ],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": None,
            "is_active": True,
        }

        return {
            "token": token,
            "supplier_id": supplier_id,
            "portal_url": f"/supplier-portal?token={token}",
            "permissions": self._portal_tokens[token_hash]["permissions"],
        }

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a portal token and return supplier info."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        info = self._portal_tokens.get(token_hash)
        if info and info.get("is_active"):
            info["last_used"] = datetime.now(timezone.utc).isoformat()
            return info
        return None

    def revoke_token(self, supplier_id: int) -> Dict[str, Any]:
        """Revoke all portal tokens for a supplier."""
        revoked = 0
        for token_hash, info in self._portal_tokens.items():
            if info["supplier_id"] == supplier_id:
                info["is_active"] = False
                revoked += 1
        return {"revoked": revoked, "supplier_id": supplier_id}

    # ------------------------------------------------------------------
    # Purchase Order Management
    # ------------------------------------------------------------------

    def get_pending_orders(self, supplier_id: int) -> List[Dict[str, Any]]:
        """Get pending purchase orders for a supplier (stub - would query PO table)."""
        # In production, queries PurchaseOrder model filtered by supplier_id
        return [
            {
                "info": "This endpoint returns pending POs from the database",
                "supplier_id": supplier_id,
                "status": "pending_confirmation",
            }
        ]

    def confirm_order(
        self,
        supplier_id: int,
        order_id: int,
        estimated_delivery: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Supplier confirms a purchase order."""
        return {
            "order_id": order_id,
            "supplier_id": supplier_id,
            "status": "confirmed",
            "estimated_delivery": estimated_delivery,
            "notes": notes,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        }

    def reject_order(
        self,
        supplier_id: int,
        order_id: int,
        reason: str,
        alternative_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Supplier rejects or proposes changes to a PO."""
        return {
            "order_id": order_id,
            "supplier_id": supplier_id,
            "status": "rejected",
            "reason": reason,
            "alternative_date": alternative_date,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Invoice Submission
    # ------------------------------------------------------------------

    def submit_invoice(
        self,
        supplier_id: int,
        purchase_order_id: Optional[int] = None,
        invoice_number: str = "",
        amount: float = 0,
        tax_amount: float = 0,
        currency: str = "USD",
        due_date: Optional[str] = None,
        line_items: Optional[List[Dict[str, Any]]] = None,
        attachment_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Supplier submits an invoice."""
        invoice = {
            "id": self._next_invoice_id,
            "supplier_id": supplier_id,
            "purchase_order_id": purchase_order_id,
            "invoice_number": invoice_number,
            "amount": amount,
            "tax_amount": tax_amount,
            "total": amount + tax_amount,
            "currency": currency,
            "due_date": due_date,
            "line_items": line_items or [],
            "attachment_url": attachment_url,
            "notes": notes,
            "status": "submitted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "reviewed_at": None,
        }
        self._invoices.append(invoice)
        self._next_invoice_id += 1
        return invoice

    def get_invoices(
        self,
        supplier_id: int,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get invoices for a supplier."""
        invoices = [i for i in self._invoices if i["supplier_id"] == supplier_id]
        if status:
            invoices = [i for i in invoices if i["status"] == status]
        return invoices

    def review_invoice(
        self,
        invoice_id: int,
        status: str,
        reviewer_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Review a supplier invoice (approve/reject)."""
        for invoice in self._invoices:
            if invoice["id"] == invoice_id:
                invoice["status"] = status
                invoice["reviewed_at"] = datetime.now(timezone.utc).isoformat()
                if reviewer_notes:
                    invoice["reviewer_notes"] = reviewer_notes
                return invoice
        return {"error": "Invoice not found"}

    # ------------------------------------------------------------------
    # Delivery Updates
    # ------------------------------------------------------------------

    def update_delivery(
        self,
        supplier_id: int,
        order_id: int,
        status: str,
        eta: Optional[str] = None,
        driver_name: Optional[str] = None,
        driver_phone: Optional[str] = None,
        tracking_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Supplier updates delivery status."""
        update = {
            "supplier_id": supplier_id,
            "order_id": order_id,
            "status": status,  # dispatched, in_transit, arriving_soon, delivered, delayed
            "eta": eta,
            "driver_name": driver_name,
            "driver_phone": driver_phone,
            "tracking_number": tracking_number,
            "notes": notes,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._delivery_updates.append(update)
        return update

    def get_delivery_updates(
        self, order_id: Optional[int] = None, supplier_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        updates = self._delivery_updates
        if order_id is not None:
            updates = [u for u in updates if u["order_id"] == order_id]
        if supplier_id is not None:
            updates = [u for u in updates if u["supplier_id"] == supplier_id]
        return updates

    # ------------------------------------------------------------------
    # Catalog Updates
    # ------------------------------------------------------------------

    def submit_catalog_update(
        self,
        supplier_id: int,
        products: List[Dict[str, Any]],
        effective_date: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Supplier submits product catalog/pricing updates."""
        update = {
            "id": len(self._catalog_updates) + 1,
            "supplier_id": supplier_id,
            "products": products,
            "effective_date": effective_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "notes": notes,
            "status": "pending_review",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._catalog_updates.append(update)
        return update

    def get_catalog_updates(
        self, supplier_id: Optional[int] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        updates = self._catalog_updates
        if supplier_id is not None:
            updates = [u for u in updates if u["supplier_id"] == supplier_id]
        if status:
            updates = [u for u in updates if u["status"] == status]
        return updates

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def send_message(
        self,
        supplier_id: int,
        subject: str,
        body: str,
        direction: str = "supplier_to_buyer",
    ) -> Dict[str, Any]:
        """Send a message between supplier and buyer."""
        msg = {
            "id": self._next_message_id,
            "supplier_id": supplier_id,
            "subject": subject,
            "body": body,
            "direction": direction,
            "read": False,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        self._messages.append(msg)
        self._next_message_id += 1
        return msg

    def get_messages(
        self, supplier_id: int, direction: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        msgs = [m for m in self._messages if m["supplier_id"] == supplier_id]
        if direction:
            msgs = [m for m in msgs if m["direction"] == direction]
        return msgs

    # ------------------------------------------------------------------
    # Payment Status
    # ------------------------------------------------------------------

    def get_payment_status(self, supplier_id: int) -> Dict[str, Any]:
        """Get payment summary for a supplier (stub)."""
        return {
            "supplier_id": supplier_id,
            "info": "Payment data is sourced from the accounting system",
            "pending_invoices": len([i for i in self._invoices if i["supplier_id"] == supplier_id and i["status"] in ("submitted", "approved")]),
            "total_pending_amount": sum(
                i["total"] for i in self._invoices
                if i["supplier_id"] == supplier_id and i["status"] in ("submitted", "approved")
            ),
        }

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def get_portal_dashboard(self, supplier_id: int) -> Dict[str, Any]:
        """Get supplier portal dashboard data."""
        return {
            "supplier_id": supplier_id,
            "invoices": {
                "submitted": len([i for i in self._invoices if i["supplier_id"] == supplier_id and i["status"] == "submitted"]),
                "approved": len([i for i in self._invoices if i["supplier_id"] == supplier_id and i["status"] == "approved"]),
                "paid": len([i for i in self._invoices if i["supplier_id"] == supplier_id and i["status"] == "paid"]),
            },
            "deliveries": {
                "pending": len([d for d in self._delivery_updates if d["supplier_id"] == supplier_id and d["status"] in ("dispatched", "in_transit")]),
            },
            "unread_messages": len([m for m in self._messages if m["supplier_id"] == supplier_id and m["direction"] == "buyer_to_supplier" and not m["read"]]),
            "catalog_updates_pending": len([c for c in self._catalog_updates if c["supplier_id"] == supplier_id and c["status"] == "pending_review"]),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_service: Optional[SupplierPortalService] = None


def get_supplier_portal_service() -> SupplierPortalService:
    global _service
    if _service is None:
        _service = SupplierPortalService()
    return _service
