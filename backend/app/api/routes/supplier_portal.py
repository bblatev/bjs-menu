"""Supplier Self-Service Portal API routes.

Provides endpoints for:
- Portal access token management
- Purchase order viewing and confirmation/rejection
- Invoice submission and tracking
- Delivery status updates
- Catalog/pricing updates
- Buyer-supplier messaging
- Supplier dashboard
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, RequireManager
from app.services.supplier_portal_service import get_supplier_portal_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Schemas ----

class GenerateTokenRequest(BaseModel):
    supplier_id: int
    supplier_name: str
    contact_email: str
    permissions: Optional[List[str]] = None


class ConfirmOrderRequest(BaseModel):
    supplier_id: int
    order_id: int
    estimated_delivery: Optional[str] = None
    notes: Optional[str] = None


class RejectOrderRequest(BaseModel):
    supplier_id: int
    order_id: int
    reason: str
    alternative_date: Optional[str] = None


class SubmitInvoiceRequest(BaseModel):
    supplier_id: int
    purchase_order_id: Optional[int] = None
    invoice_number: str
    amount: float
    tax_amount: float = 0
    currency: str = "USD"
    due_date: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]] = None
    attachment_url: Optional[str] = None
    notes: Optional[str] = None


class ReviewInvoiceRequest(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected|paid)$")
    reviewer_notes: Optional[str] = None


class DeliveryUpdateRequest(BaseModel):
    supplier_id: int
    order_id: int
    status: str = Field(..., pattern="^(dispatched|in_transit|arriving_soon|delivered|delayed)$")
    eta: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None


class CatalogUpdateRequest(BaseModel):
    supplier_id: int
    products: List[Dict[str, Any]]
    effective_date: Optional[str] = None
    notes: Optional[str] = None


class SendMessageRequest(BaseModel):
    supplier_id: int
    subject: str
    body: str
    direction: str = "supplier_to_buyer"


# ---- Routes ----

@router.get("/")
@limiter.limit("60/minute")
async def portal_overview(request: Request):
    """Supplier portal overview."""
    return {
        "module": "supplier-portal",
        "features": [
            "Portal access token management",
            "Purchase order confirmation/rejection",
            "Invoice submission and tracking",
            "Delivery status updates with ETA",
            "Catalog/pricing updates",
            "Buyer-supplier messaging",
            "Supplier dashboard",
        ],
    }


# ---- Access Tokens ----

@router.post("/tokens")
@limiter.limit("10/minute")
async def generate_token(request: Request, body: GenerateTokenRequest, user: RequireManager):
    """Generate a portal access token for a supplier."""
    svc = get_supplier_portal_service()
    return svc.generate_portal_token(
        supplier_id=body.supplier_id,
        supplier_name=body.supplier_name,
        contact_email=body.contact_email,
        permissions=body.permissions,
    )


@router.post("/tokens/validate")
@limiter.limit("60/minute")
async def validate_token(request: Request, token: str):
    """Validate a supplier portal token."""
    svc = get_supplier_portal_service()
    result = svc.validate_token(token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"valid": True, **result}


@router.delete("/tokens/{supplier_id}")
@limiter.limit("10/minute")
async def revoke_tokens(request: Request, supplier_id: int, user: RequireManager):
    """Revoke all portal tokens for a supplier."""
    svc = get_supplier_portal_service()
    return svc.revoke_token(supplier_id)


# ---- Purchase Orders ----

@router.get("/orders/{supplier_id}")
@limiter.limit("30/minute")
async def get_pending_orders(request: Request, supplier_id: int):
    """Get pending purchase orders for a supplier."""
    svc = get_supplier_portal_service()
    return {"orders": svc.get_pending_orders(supplier_id)}


@router.post("/orders/confirm")
@limiter.limit("20/minute")
async def confirm_order(request: Request, body: ConfirmOrderRequest):
    """Supplier confirms a purchase order."""
    svc = get_supplier_portal_service()
    return svc.confirm_order(
        supplier_id=body.supplier_id, order_id=body.order_id,
        estimated_delivery=body.estimated_delivery, notes=body.notes,
    )


@router.post("/orders/reject")
@limiter.limit("20/minute")
async def reject_order(request: Request, body: RejectOrderRequest):
    """Supplier rejects a purchase order."""
    svc = get_supplier_portal_service()
    return svc.reject_order(
        supplier_id=body.supplier_id, order_id=body.order_id,
        reason=body.reason, alternative_date=body.alternative_date,
    )


# ---- Invoices ----

@router.post("/invoices")
@limiter.limit("20/minute")
async def submit_invoice(request: Request, body: SubmitInvoiceRequest):
    """Supplier submits an invoice."""
    svc = get_supplier_portal_service()
    return svc.submit_invoice(
        supplier_id=body.supplier_id,
        purchase_order_id=body.purchase_order_id,
        invoice_number=body.invoice_number,
        amount=body.amount, tax_amount=body.tax_amount,
        currency=body.currency, due_date=body.due_date,
        line_items=body.line_items,
        attachment_url=body.attachment_url, notes=body.notes,
    )


@router.get("/invoices/{supplier_id}")
@limiter.limit("30/minute")
async def get_invoices(request: Request, supplier_id: int, status: Optional[str] = None):
    """Get invoices for a supplier."""
    svc = get_supplier_portal_service()
    return {"invoices": svc.get_invoices(supplier_id, status=status)}


@router.put("/invoices/{invoice_id}/review")
@limiter.limit("20/minute")
async def review_invoice(request: Request, invoice_id: int, body: ReviewInvoiceRequest, user: RequireManager):
    """Review (approve/reject) a supplier invoice."""
    svc = get_supplier_portal_service()
    result = svc.review_invoice(invoice_id, status=body.status, reviewer_notes=body.reviewer_notes)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---- Deliveries ----

@router.post("/deliveries")
@limiter.limit("30/minute")
async def update_delivery(request: Request, body: DeliveryUpdateRequest):
    """Supplier updates delivery status."""
    svc = get_supplier_portal_service()
    return svc.update_delivery(
        supplier_id=body.supplier_id, order_id=body.order_id,
        status=body.status, eta=body.eta,
        driver_name=body.driver_name, driver_phone=body.driver_phone,
        tracking_number=body.tracking_number, notes=body.notes,
    )


@router.get("/deliveries")
@limiter.limit("30/minute")
async def get_deliveries(
    request: Request,
    order_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
):
    """Get delivery updates."""
    svc = get_supplier_portal_service()
    return {"deliveries": svc.get_delivery_updates(order_id=order_id, supplier_id=supplier_id)}


# ---- Catalog ----

@router.post("/catalog")
@limiter.limit("10/minute")
async def submit_catalog_update(request: Request, body: CatalogUpdateRequest):
    """Supplier submits catalog/pricing updates."""
    svc = get_supplier_portal_service()
    return svc.submit_catalog_update(
        supplier_id=body.supplier_id, products=body.products,
        effective_date=body.effective_date, notes=body.notes,
    )


@router.get("/catalog")
@limiter.limit("30/minute")
async def get_catalog_updates(
    request: Request,
    supplier_id: Optional[int] = None,
    status: Optional[str] = None,
):
    """Get catalog update submissions."""
    svc = get_supplier_portal_service()
    return {"updates": svc.get_catalog_updates(supplier_id=supplier_id, status=status)}


# ---- Messaging ----

@router.post("/messages")
@limiter.limit("30/minute")
async def send_message(request: Request, body: SendMessageRequest):
    """Send a message between supplier and buyer."""
    svc = get_supplier_portal_service()
    return svc.send_message(
        supplier_id=body.supplier_id, subject=body.subject,
        body=body.body, direction=body.direction,
    )


@router.get("/messages/{supplier_id}")
@limiter.limit("30/minute")
async def get_messages(request: Request, supplier_id: int, direction: Optional[str] = None):
    """Get messages for a supplier."""
    svc = get_supplier_portal_service()
    return {"messages": svc.get_messages(supplier_id, direction=direction)}


# ---- Dashboard ----

@router.get("/dashboard/{supplier_id}")
@limiter.limit("30/minute")
async def get_dashboard(request: Request, supplier_id: int):
    """Get supplier portal dashboard data."""
    svc = get_supplier_portal_service()
    return svc.get_portal_dashboard(supplier_id)
