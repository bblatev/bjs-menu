"""
Tab Management API Endpoints - Database-backed implementation
Provides full tab management functionality for restaurant operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import StaffUser, MenuItem
from app.models.core_business_models import Tab, TabItem, TabPayment, TabStatus


router = APIRouter()


# ========== SCHEMAS ==========

class TabOpenRequest(BaseModel):
    table_id: Optional[int] = None
    customer_name: str
    customer_id: Optional[int] = None
    customer_phone: Optional[str] = None
    card_last_four: Optional[str] = None
    pre_auth_amount: float = 0.0
    credit_limit: float = 500.0
    notes: Optional[str] = None


class TabAddItemRequest(BaseModel):
    menu_item_id: int
    quantity: float = 1
    unit_price: Optional[float] = None
    modifiers: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class TabAddItemsRequest(BaseModel):
    items: List[TabAddItemRequest]


class TabCloseRequest(BaseModel):
    payment_method: str = "cash"
    tip_amount: float = 0.0
    payment_reference: Optional[str] = None


class TabTransferRequest(BaseModel):
    new_table_id: int


class TabVoidItemRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class TabPaymentRequest(BaseModel):
    amount: float
    payment_method: str
    reference: Optional[str] = None


# ========== HELPER FUNCTIONS ==========

def generate_tab_number(db: Session) -> str:
    """Generate unique tab number"""
    today = datetime.utcnow()
    prefix = f"TAB-{today.strftime('%Y%m%d')}"

    count = db.query(func.count(Tab.id)).filter(
        Tab.tab_number.like(f"{prefix}%")
    ).scalar() or 0

    return f"{prefix}-{count + 1:04d}"


def recalculate_tab_totals(db: Session, tab: Tab):
    """Recalculate tab totals from items"""
    items = db.query(TabItem).filter(
        TabItem.tab_id == tab.id,
        TabItem.voided == False
    ).all()

    subtotal = sum(item.total for item in items)
    tax_rate = 0.20  # 20% default
    tax_amount = subtotal * tax_rate
    total = subtotal + tax_amount + tab.tip_amount

    tab.subtotal = subtotal
    tab.tax_amount = tax_amount
    tab.total = total
    tab.balance_due = total - tab.amount_paid


def format_tab_response(tab: Tab, include_items: bool = True) -> Dict:
    """Format tab for API response"""
    response = {
        "id": tab.id,
        "tab_number": tab.tab_number,
        "customer_name": tab.customer_name,
        "customer_phone": tab.customer_phone,
        "table_id": tab.table_id,
        "server_id": tab.server_id,
        "subtotal": tab.subtotal,
        "tax_amount": tab.tax_amount,
        "discount_amount": tab.discount_amount,
        "tip_amount": tab.tip_amount,
        "total": tab.total,
        "amount_paid": tab.amount_paid,
        "balance_due": tab.balance_due,
        "credit_limit": tab.credit_limit,
        "status": tab.status.value if tab.status else "open",
        "opened_at": tab.opened_at.isoformat() if tab.opened_at else None,
        "closed_at": tab.closed_at.isoformat() if tab.closed_at else None,
        "last_activity_at": tab.last_activity_at.isoformat() if tab.last_activity_at else None,
        "notes": tab.notes
    }

    if include_items and tab.items:
        response["items"] = [
            {
                "id": item.id,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total": item.total,
                "modifiers": item.modifiers,
                "voided": item.voided,
                "added_at": item.added_at.isoformat() if item.added_at else None
            }
            for item in tab.items if not item.voided
        ]
        response["items_count"] = len([i for i in tab.items if not i.voided])

    return response


# ========== ENDPOINTS ==========

@router.get("")
@router.get("/", include_in_schema=False)
async def list_tabs(
    status_filter: Optional[str] = Query(None, alias="status"),
    table_id: Optional[int] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get all tabs for the venue"""
    query = db.query(Tab).filter(Tab.venue_id == current_user.venue_id)

    # Filter by status
    if status_filter:
        if status_filter == "all":
            pass
        elif "," in status_filter:
            statuses = [TabStatus(s.strip()) for s in status_filter.split(",") if s.strip()]
            query = query.filter(Tab.status.in_(statuses))
        else:
            try:
                query = query.filter(Tab.status == TabStatus(status_filter))
            except ValueError:
                pass
    else:
        # Default to open tabs
        query = query.filter(Tab.status == TabStatus.OPEN)

    # Filter by table
    if table_id:
        query = query.filter(Tab.table_id == table_id)

    # Get results
    total = query.count()
    tabs = query.order_by(Tab.opened_at.desc()).offset(offset).limit(limit).all()

    return {
        "tabs": [format_tab_response(tab) for tab in tabs],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/stats")
async def get_tab_stats(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get tab statistics for the venue"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Open tabs
    open_tabs = db.query(Tab).filter(
        Tab.venue_id == current_user.venue_id,
        Tab.status == TabStatus.OPEN
    ).all()

    open_count = len(open_tabs)
    total_open_value = sum(tab.balance_due for tab in open_tabs)
    avg_tab_value = total_open_value / open_count if open_count > 0 else 0

    # Closed today
    closed_today = db.query(func.count(Tab.id)).filter(
        Tab.venue_id == current_user.venue_id,
        Tab.status == TabStatus.CLOSED,
        Tab.closed_at >= today
    ).scalar() or 0

    # Total closed value today
    closed_value_today = db.query(func.sum(Tab.total)).filter(
        Tab.venue_id == current_user.venue_id,
        Tab.status == TabStatus.CLOSED,
        Tab.closed_at >= today
    ).scalar() or 0

    # Average time open
    closed_tabs_today = db.query(Tab).filter(
        Tab.venue_id == current_user.venue_id,
        Tab.status == TabStatus.CLOSED,
        Tab.closed_at >= today
    ).all()

    if closed_tabs_today:
        total_minutes = sum(
            (tab.closed_at - tab.opened_at).total_seconds() / 60
            for tab in closed_tabs_today
            if tab.closed_at and tab.opened_at
        )
        avg_duration_minutes = total_minutes / len(closed_tabs_today)
    else:
        avg_duration_minutes = 0

    return {
        "open_tabs": open_count,
        "total_open_value": float(total_open_value),
        "avg_tab_value": round(float(avg_tab_value), 2),
        "tabs_closed_today": closed_today,
        "closed_value_today": float(closed_value_today),
        "avg_duration_minutes": round(avg_duration_minutes, 1),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/expiring")
async def get_expiring_tabs(
    minutes_before: int = Query(default=30, ge=1, le=1440),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get tabs that have been open for a long time (potential issues)"""
    cutoff = datetime.utcnow() - timedelta(hours=4)  # Tabs open > 4 hours

    tabs = db.query(Tab).filter(
        Tab.venue_id == current_user.venue_id,
        Tab.status == TabStatus.OPEN,
        Tab.opened_at <= cutoff
    ).all()

    return [
        {
            "tab_id": tab.tab_number,
            "customer_name": tab.customer_name,
            "table_id": tab.table_id,
            "current_total": tab.total,
            "opened_at": tab.opened_at.isoformat() if tab.opened_at else None,
            "hours_open": round((datetime.utcnow() - tab.opened_at).total_seconds() / 3600, 1) if tab.opened_at else 0,
            "warning": "Tab has been open for extended period"
        }
        for tab in tabs
    ]


@router.post("")
@router.post("/", include_in_schema=False)
async def open_tab(
    data: TabOpenRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Open a new tab"""
    tab_number = generate_tab_number(db)

    tab = Tab(
        tab_number=tab_number,
        venue_id=current_user.venue_id,
        customer_id=data.customer_id,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        table_id=data.table_id,
        server_id=current_user.id,
        credit_limit=data.credit_limit,
        status=TabStatus.OPEN,
        notes=data.notes
    )

    db.add(tab)
    db.commit()
    db.refresh(tab)

    return {
        "success": True,
        "tab_id": tab.tab_number,
        "id": tab.id,
        "customer_name": tab.customer_name,
        "table_id": tab.table_id,
        "credit_limit": tab.credit_limit,
        "status": tab.status.value,
        "opened_at": tab.opened_at.isoformat(),
        "message": f"Tab {tab.tab_number} opened successfully"
    }


@router.get("/{tab_id}")
async def get_tab(
    tab_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get tab details by ID"""
    tab = db.query(Tab).filter(
        Tab.id == tab_id,
        Tab.venue_id == current_user.venue_id
    ).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found")

    return format_tab_response(tab, include_items=True)


@router.post("/{tab_id}/items")
async def add_items_to_tab(
    tab_id: int,
    data: TabAddItemsRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Add items to a tab"""
    tab = db.query(Tab).filter(
        Tab.id == tab_id,
        Tab.venue_id == current_user.venue_id
    ).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found")

    if tab.status != TabStatus.OPEN:
        raise HTTPException(status_code=400, detail="Cannot add items to closed tab")

    items_added = []
    items_total = 0

    for item_data in data.items:
        # Get menu item for price and name
        menu_item = db.query(MenuItem).filter(MenuItem.id == item_data.menu_item_id).first()

        if not menu_item:
            raise HTTPException(status_code=404, detail=f"Menu item {item_data.menu_item_id} not found")

        unit_price = item_data.unit_price or float(menu_item.price)
        total = unit_price * item_data.quantity

        tab_item = TabItem(
            tab_id=tab.id,
            menu_item_id=item_data.menu_item_id,
            description=menu_item.name,
            quantity=item_data.quantity,
            unit_price=unit_price,
            modifiers=item_data.modifiers,
            total=total,
            added_by=current_user.id
        )

        db.add(tab_item)
        items_added.append({
            "menu_item_id": item_data.menu_item_id,
            "name": menu_item.name,
            "quantity": item_data.quantity,
            "unit_price": unit_price,
            "total": total
        })
        items_total += total

    # Update tab totals
    tab.last_activity_at = datetime.utcnow()
    db.flush()
    recalculate_tab_totals(db, tab)

    # Check credit limit
    warning = None
    if tab.credit_limit and tab.total > tab.credit_limit:
        warning = f"Tab total ({tab.total:.2f}) exceeds credit limit ({tab.credit_limit:.2f})"

    db.commit()

    return {
        "success": True,
        "tab_id": tab.tab_number,
        "items_added": items_added,
        "items_total": items_total,
        "new_tab_total": tab.total,
        "warning": warning,
        "message": f"Added {len(items_added)} item(s) to tab"
    }


@router.delete("/{tab_id}/items/{item_id}")
async def void_item_from_tab(
    tab_id: int,
    item_id: int,
    data: TabVoidItemRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Void an item from a tab"""
    tab = db.query(Tab).filter(
        Tab.id == tab_id,
        Tab.venue_id == current_user.venue_id
    ).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found")

    if tab.status != TabStatus.OPEN:
        raise HTTPException(status_code=400, detail="Cannot void items on closed tab")

    item = db.query(TabItem).filter(
        TabItem.id == item_id,
        TabItem.tab_id == tab_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found on tab")

    if item.voided:
        raise HTTPException(status_code=400, detail="Item already voided")

    voided_amount = item.total
    item.voided = True
    item.voided_reason = data.reason
    item.voided_by = current_user.id

    # Recalculate totals
    tab.last_activity_at = datetime.utcnow()
    recalculate_tab_totals(db, tab)

    db.commit()

    return {
        "success": True,
        "tab_id": tab.tab_number,
        "voided_item_id": item_id,
        "voided_amount": voided_amount,
        "new_tab_total": tab.total,
        "reason": data.reason,
        "voided_by": current_user.id,
        "message": "Item voided successfully"
    }


@router.post("/{tab_id}/payments")
async def add_payment_to_tab(
    tab_id: int,
    data: TabPaymentRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Add a payment to a tab (partial payment)"""
    tab = db.query(Tab).filter(
        Tab.id == tab_id,
        Tab.venue_id == current_user.venue_id
    ).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found")

    if tab.status == TabStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Tab already closed")

    payment = TabPayment(
        tab_id=tab.id,
        amount=data.amount,
        payment_method=data.payment_method,
        reference=data.reference,
        processed_by=current_user.id
    )

    db.add(payment)

    tab.amount_paid += data.amount
    tab.balance_due = tab.total - tab.amount_paid
    tab.last_activity_at = datetime.utcnow()

    db.commit()

    return {
        "success": True,
        "tab_id": tab.tab_number,
        "payment_amount": data.amount,
        "total_paid": tab.amount_paid,
        "balance_due": tab.balance_due,
        "message": "Payment recorded"
    }


@router.post("/{tab_id}/close")
async def close_tab(
    tab_id: int,
    data: TabCloseRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Close a tab with final payment"""
    tab = db.query(Tab).filter(
        Tab.id == tab_id,
        Tab.venue_id == current_user.venue_id
    ).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found")

    if tab.status == TabStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Tab already closed")

    # Add tip
    tab.tip_amount = data.tip_amount
    recalculate_tab_totals(db, tab)

    # Record final payment if balance due
    if tab.balance_due > 0:
        payment = TabPayment(
            tab_id=tab.id,
            amount=tab.balance_due,
            payment_method=data.payment_method,
            reference=data.payment_reference,
            processed_by=current_user.id
        )
        db.add(payment)
        tab.amount_paid = tab.total
        tab.balance_due = 0

    # Close the tab
    tab.status = TabStatus.CLOSED
    tab.closed_at = datetime.utcnow()

    db.commit()

    return {
        "success": True,
        "tab_id": tab.tab_number,
        "subtotal": tab.subtotal,
        "tax_amount": tab.tax_amount,
        "tip_amount": tab.tip_amount,
        "total_charged": tab.total,
        "payment_method": data.payment_method,
        "closed_at": tab.closed_at.isoformat(),
        "closed_by": current_user.id,
        "message": "Tab closed successfully"
    }


@router.post("/{tab_id}/transfer")
async def transfer_tab(
    tab_id: int,
    data: TabTransferRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Transfer tab to another table"""
    tab = db.query(Tab).filter(
        Tab.id == tab_id,
        Tab.venue_id == current_user.venue_id
    ).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found")

    if tab.status != TabStatus.OPEN:
        raise HTTPException(status_code=400, detail="Cannot transfer closed tab")

    old_table_id = tab.table_id
    tab.table_id = data.new_table_id
    tab.last_activity_at = datetime.utcnow()

    db.commit()

    return {
        "success": True,
        "tab_id": tab.tab_number,
        "old_table_id": old_table_id,
        "new_table_id": data.new_table_id,
        "transferred_by": current_user.id,
        "transferred_at": datetime.utcnow().isoformat(),
        "message": f"Tab transferred from table {old_table_id} to table {data.new_table_id}"
    }


@router.post("/{tab_id}/void")
async def void_tab(
    tab_id: int,
    reason: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Void entire tab"""
    tab = db.query(Tab).filter(
        Tab.id == tab_id,
        Tab.venue_id == current_user.venue_id
    ).first()

    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found")

    if tab.status == TabStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot void closed tab")

    if tab.amount_paid > 0:
        raise HTTPException(status_code=400, detail="Cannot void tab with payments - refund first")

    tab.status = TabStatus.VOIDED
    tab.notes = f"VOIDED: {reason}" + (f"\n{tab.notes}" if tab.notes else "")
    tab.closed_at = datetime.utcnow()

    db.commit()

    return {
        "success": True,
        "tab_id": tab.tab_number,
        "voided_by": current_user.id,
        "reason": reason,
        "message": "Tab voided successfully"
    }
