"""QuickBooks Online Integration API routes."""

import logging
from typing import Optional, List
from datetime import datetime, date, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.hardware import Integration
from app.services.quickbooks_service import (
    get_quickbooks_service,
    QBOTokens,
)

logger = logging.getLogger(__name__)

router = APIRouter()

QBO_INTEGRATION_ID = "quickbooks_online"


def _save_qbo_tokens(db, tokens: QBOTokens):
    """Persist QuickBooks tokens to the integrations table."""
    integration = db.query(Integration).filter(Integration.integration_id == QBO_INTEGRATION_ID).first()
    if not integration:
        integration = Integration(
            integration_id=QBO_INTEGRATION_ID,
            name="QuickBooks Online",
            category="accounting",
            status="connected",
        )
        db.add(integration)
    integration.status = "connected"
    integration.connected_at = datetime.now(timezone.utc)
    integration.config = {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "realm_id": tokens.realm_id,
        "expires_at": tokens.expires_at.isoformat() if tokens.expires_at else None,
    }
    db.commit()


def _load_qbo_tokens(db) -> Optional[QBOTokens]:
    """Load QuickBooks tokens from the integrations table."""
    integration = db.query(Integration).filter(Integration.integration_id == QBO_INTEGRATION_ID).first()
    if not integration or not integration.config:
        return None
    config = integration.config
    expires_at = None
    if config.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(config["expires_at"])
        except (ValueError, TypeError):
            pass
    return QBOTokens(
        access_token=config.get("access_token", ""),
        refresh_token=config.get("refresh_token", ""),
        realm_id=config.get("realm_id", ""),
        expires_at=expires_at,
    )


# ============================================================================
# Request/Response Models
# ============================================================================

class OAuthCallbackRequest(BaseModel):
    code: str
    realm_id: str
    state: Optional[str] = None


class TokenResponse(BaseModel):
    success: bool
    realm_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


class SetTokensRequest(BaseModel):
    access_token: str
    refresh_token: str
    realm_id: str
    expires_at: Optional[datetime] = None


class CustomerSyncRequest(BaseModel):
    display_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    notes: Optional[str] = None
    internal_id: Optional[str] = None


class VendorSyncRequest(BaseModel):
    display_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None


class LineItemRequest(BaseModel):
    description: str
    amount: float
    quantity: int = 1
    item_id: Optional[str] = None
    account_id: Optional[str] = None


class SalesReceiptRequest(BaseModel):
    customer_id: Optional[str] = None
    line_items: List[LineItemRequest]
    payment_method: str = "Cash"
    txn_date: Optional[str] = None
    memo: Optional[str] = None
    order_id: Optional[str] = None


class InvoiceRequest(BaseModel):
    customer_id: str
    line_items: List[LineItemRequest]
    due_date: Optional[str] = None
    txn_date: Optional[str] = None
    memo: Optional[str] = None
    invoice_number: Optional[str] = None


class BillRequest(BaseModel):
    vendor_id: str
    line_items: List[LineItemRequest]
    due_date: Optional[str] = None
    txn_date: Optional[str] = None
    memo: Optional[str] = None
    ref_number: Optional[str] = None


class ItemSyncRequest(BaseModel):
    name: str
    description: Optional[str] = None
    unit_price: Optional[float] = None
    purchase_cost: Optional[float] = None
    item_type: str = "Service"
    income_account_id: Optional[str] = None
    expense_account_id: Optional[str] = None
    sku: Optional[str] = None


class DailySalesSyncRequest(BaseModel):
    start_date: str
    end_date: str


class SyncResponse(BaseModel):
    success: bool
    synced_count: int = 0
    error_count: int = 0
    errors: List[str] = []
    last_sync: Optional[datetime] = None


# ============================================================================
# OAuth Flow
# ============================================================================

@router.get("/auth-url")
async def get_authorization_url(state: str = "random_state"):
    """Get the OAuth2 authorization URL to connect QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(
            status_code=503,
            detail="QuickBooks not configured. Set QBO_CLIENT_ID and QBO_CLIENT_SECRET environment variables.",
        )

    url = qbo.get_authorization_url(state=state)
    return {"authorization_url": url, "state": state}


@router.get("/callback")
async def oauth_callback(
    db: DbSession,
    code: str = Query(...),
    realmId: str = Query(...),
    state: Optional[str] = Query(None),
):
    """
    OAuth2 callback endpoint.

    This is called by QuickBooks after user authorizes the connection.
    """
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    tokens = await qbo.exchange_code_for_tokens(
        authorization_code=code,
        realm_id=realmId,
    )

    if tokens:
        _save_qbo_tokens(db, tokens)
        logger.info(f"QuickBooks tokens saved for realm {tokens.realm_id}")
        return {
            "success": True,
            "realm_id": tokens.realm_id,
            "expires_at": tokens.expires_at.isoformat() if tokens.expires_at else None,
            "message": "QuickBooks connected successfully!",
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")


@router.post("/tokens")
async def set_tokens(db: DbSession, request: SetTokensRequest):
    """Set tokens manually and persist to database."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    tokens = QBOTokens(
        access_token=request.access_token,
        refresh_token=request.refresh_token,
        realm_id=request.realm_id,
        expires_at=request.expires_at,
    )
    qbo.set_tokens(tokens)
    _save_qbo_tokens(db, tokens)

    return {"success": True, "message": "Tokens set and saved successfully"}


@router.post("/refresh")
async def refresh_tokens(db: DbSession):
    """Refresh access tokens and persist new tokens to database."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    # Load tokens from DB if service doesn't have them in memory
    if not qbo.get_tokens():
        saved_tokens = _load_qbo_tokens(db)
        if saved_tokens:
            qbo.set_tokens(saved_tokens)

    success = await qbo.refresh_tokens()

    if success:
        tokens = qbo.get_tokens()
        if tokens:
            _save_qbo_tokens(db, tokens)
        return {
            "success": True,
            "expires_at": tokens.expires_at.isoformat() if tokens and tokens.expires_at else None,
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to refresh tokens")


@router.get("/status")
async def get_connection_status(db: DbSession):
    """Check QuickBooks connection status, restoring tokens from DB if needed."""
    qbo = get_quickbooks_service()

    if not qbo:
        return {
            "configured": False,
            "connected": False,
            "message": "QuickBooks not configured. Set QBO_CLIENT_ID and QBO_CLIENT_SECRET.",
        }

    tokens = qbo.get_tokens()
    # Auto-restore tokens from database on server restart
    if not tokens:
        saved_tokens = _load_qbo_tokens(db)
        if saved_tokens:
            qbo.set_tokens(saved_tokens)
            tokens = saved_tokens

    if not tokens:
        return {
            "configured": True,
            "connected": False,
            "message": "QuickBooks configured but not connected. Use /auth-url to connect.",
        }

    # Try to get company info to verify connection
    try:
        company_info = await qbo.get_company_info()
        if company_info.get("success"):
            return {
                "configured": True,
                "connected": True,
                "realm_id": tokens.realm_id,
                "company_name": company_info.get("company_name"),
                "expires_at": tokens.expires_at.isoformat() if tokens.expires_at else None,
            }
        else:
            return {
                "configured": True,
                "connected": False,
                "message": "Connection error - tokens may be expired",
                "error": company_info.get("error"),
            }
    except Exception as e:
        return {
            "configured": True,
            "connected": False,
            "message": str(e),
        }


# ============================================================================
# Customers
# ============================================================================

@router.get("/customers")
async def get_customers(limit: int = 100):
    """Get all customers from QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    customers = await qbo.get_customers(limit=limit)
    return {"customers": customers, "count": len(customers)}


@router.post("/customers")
async def sync_customer(request: CustomerSyncRequest):
    """Create or update a customer in QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    result = await qbo.sync_customer(
        display_name=request.display_name,
        email=request.email,
        phone=request.phone,
        company_name=request.company_name,
        notes=request.notes,
        internal_id=request.internal_id,
    )

    if result.get("success"):
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))


# ============================================================================
# Vendors (Suppliers)
# ============================================================================

@router.post("/vendors")
async def sync_vendor(request: VendorSyncRequest):
    """Create or update a vendor in QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    result = await qbo.sync_vendor(
        display_name=request.display_name,
        email=request.email,
        phone=request.phone,
        company_name=request.company_name,
    )

    if result.get("success"):
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))


# ============================================================================
# Items (Products/Services)
# ============================================================================

@router.get("/items")
async def get_items(limit: int = 1000):
    """Get all items from QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    items = await qbo.get_items(limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/items")
async def sync_item(request: ItemSyncRequest):
    """Create or update an item in QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    result = await qbo.sync_item(
        name=request.name,
        description=request.description,
        unit_price=request.unit_price,
        purchase_cost=request.purchase_cost,
        item_type=request.item_type,
        income_account_id=request.income_account_id,
        expense_account_id=request.expense_account_id,
        sku=request.sku,
    )

    if result.get("success"):
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))


# ============================================================================
# Sales Receipts
# ============================================================================

@router.post("/sales-receipts")
async def create_sales_receipt(request: SalesReceiptRequest):
    """Create a sales receipt in QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    line_items = [
        {
            "description": item.description,
            "amount": item.amount,
            "quantity": item.quantity,
            "item_id": item.item_id,
        }
        for item in request.line_items
    ]

    result = await qbo.create_sales_receipt(
        customer_id=request.customer_id,
        line_items=line_items,
        payment_method=request.payment_method,
        txn_date=request.txn_date,
        memo=request.memo,
        order_id=request.order_id,
    )

    if result.get("success"):
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))


# ============================================================================
# Invoices
# ============================================================================

@router.post("/invoices")
async def create_invoice(request: InvoiceRequest):
    """Create an invoice in QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    line_items = [
        {
            "description": item.description,
            "amount": item.amount,
            "quantity": item.quantity,
            "item_id": item.item_id,
        }
        for item in request.line_items
    ]

    result = await qbo.create_invoice(
        customer_id=request.customer_id,
        line_items=line_items,
        due_date=request.due_date,
        txn_date=request.txn_date,
        memo=request.memo,
        invoice_number=request.invoice_number,
    )

    if result.get("success"):
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))


# ============================================================================
# Bills (Vendor Invoices)
# ============================================================================

@router.post("/bills")
async def create_bill(request: BillRequest):
    """Create a bill (vendor invoice) in QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    line_items = [
        {
            "description": item.description,
            "amount": item.amount,
            "quantity": item.quantity,
            "account_id": item.account_id,
        }
        for item in request.line_items
    ]

    result = await qbo.create_bill(
        vendor_id=request.vendor_id,
        line_items=line_items,
        due_date=request.due_date,
        txn_date=request.txn_date,
        memo=request.memo,
        ref_number=request.ref_number,
    )

    if result.get("success"):
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))


# ============================================================================
# Accounts (Chart of Accounts)
# ============================================================================

@router.get("/accounts")
async def get_accounts(account_type: Optional[str] = None):
    """Get chart of accounts from QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    accounts = await qbo.get_accounts(account_type=account_type)
    return {"accounts": accounts, "count": len(accounts)}


# ============================================================================
# Reports
# ============================================================================

@router.get("/reports/profit-and-loss")
async def get_profit_and_loss(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get profit and loss report from QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    result = await qbo.get_profit_and_loss(start_date=start_date, end_date=end_date)

    if result.get("success"):
        return result.get("data")
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))


@router.get("/reports/balance-sheet")
async def get_balance_sheet(
    as_of_date: str = Query(..., description="As of date (YYYY-MM-DD)"),
):
    """Get balance sheet report from QuickBooks."""
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    result = await qbo.get_balance_sheet(as_of_date=as_of_date)

    if result.get("success"):
        return result.get("data")
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))


# ============================================================================
# Bulk Sync
# ============================================================================

@router.post("/sync/daily-sales", response_model=SyncResponse)
async def sync_daily_sales(db: DbSession, request: DailySalesSyncRequest):
    """
    Sync daily sales from BJS Menu to QuickBooks.

    Fetches completed, paid orders in the date range and creates sales receipts in QBO.
    """
    qbo = get_quickbooks_service()
    if not qbo:
        raise HTTPException(status_code=503, detail="QuickBooks not configured")

    from app.models.restaurant import GuestOrder
    from sqlalchemy import and_

    start = datetime.strptime(request.start_date, "%Y-%m-%d")
    end = datetime.strptime(request.end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

    orders = db.query(GuestOrder).filter(
        and_(
            GuestOrder.payment_status == "paid",
            GuestOrder.created_at >= start,
            GuestOrder.created_at <= end,
        )
    ).all()

    synced = 0
    errors = []
    for order in orders:
        items = order.items or []
        line_items = []
        for item in items:
            if isinstance(item, dict):
                line_items.append({
                    "description": item.get("name", "Item"),
                    "amount": float(item.get("price", 0)) * item.get("quantity", 1),
                    "quantity": item.get("quantity", 1),
                })
        if not line_items:
            continue
        try:
            result = await qbo.create_sales_receipt(
                line_items=line_items,
                payment_method=order.payment_method or "Card",
                txn_date=order.created_at.strftime("%Y-%m-%d") if order.created_at else None,
                memo=f"BJS Order #{order.id}",
                order_id=str(order.id),
            )
            if result.get("success"):
                synced += 1
            else:
                errors.append(f"Order {order.id}: {result.get('error', 'unknown')}")
        except Exception as e:
            errors.append(f"Order {order.id}: {str(e)}")

    return SyncResponse(
        success=len(errors) == 0,
        synced_count=synced,
        error_count=len(errors),
        errors=errors[:20],
        last_sync=datetime.now(timezone.utc),
    )
