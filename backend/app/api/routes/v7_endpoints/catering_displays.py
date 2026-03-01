"""V7 Catering, displays & reviews"""
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Path, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
from enum import Enum
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.missing_features_models import (
    SMSCampaign, SMSOptOut, CustomerRFMScore, RFMSegmentDefinition,
    CustomerVIPStatus, VIPTier as VIPTierModel, IngredientPriceHistory,
    EmployeeBreak, BreakPolicy, ShiftTradeRequest, SingleUsePromoCode,
    PromoCodeCampaign, CustomerReferral, MenuItemReview,
    MenuItemRatingAggregate, CustomerDisplay, CateringEvent,
    CateringInvoice, CateringOrderItem, DepositPolicy, PrepTimeModel,
)
from app.models.invoice import PriceAlert
from app.models import Customer, ReservationDeposit
from app.models.operations import ReferralProgram
from app.models.core_business_models import SMSMessage

from app.core.rbac import get_current_user
from app.api.routes.v7_endpoints._helpers import (
    require_manager, verify_venue_access,
    DepositPolicyType, CampaignType, EventType, PromoCodeType,
    VIPTier, ChargebackReason, BlockType,
)

router = APIRouter()

# ============================================================================
# TIER 1: CATERING & EVENTS (8 endpoints)
# ============================================================================

@router.get("/{venue_id}/catering/packages")
@limiter.limit("60/minute")
async def get_catering_packages(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get catering packages from database"""
    from app.models.missing_features_models import CateringPackage
    packages = db.query(CateringPackage).filter(
        CateringPackage.venue_id == venue_id,
        CateringPackage.is_active == True
    ).all()

    return {
        "packages": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price_per_person": float(p.price_per_person) if p.price_per_person else None,
                "min_guests": p.min_guests,
                "max_guests": p.max_guests,
                "included_items": p.included_items or []
            }
            for p in packages
        ]
    }

@router.post("/{venue_id}/catering/inquiries")
@limiter.limit("30/minute")
async def create_catering_inquiry(
    request: Request,
    venue_id: int,
    customer_id: str = Body(...),
    event_type: EventType = Body(...),
    event_name: str = Body(...),
    event_date: datetime = Body(...),
    duration_hours: float = Body(4.0),
    location: str = Body(...),
    guest_count: int = Body(...),
    contact_name: str = Body(...),
    contact_phone: str = Body(...),
    contact_email: str = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create catering inquiry in database"""
    verify_venue_access(venue_id, current_user)
    try:
        customer_id_int = int(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    event = CateringEvent(
        venue_id=venue_id,
        customer_id=customer_id_int,
        event_type=event_type.value,
        event_name=event_name,
        event_date=event_date,
        duration_hours=duration_hours,
        location=location,
        guest_count=guest_count,
        contact_name=contact_name,
        contact_phone=contact_phone,
        contact_email=contact_email,
        status="inquiry",
        created_at=datetime.now(timezone.utc)
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return {"event_id": event.id, "status": event.status}

@router.post("/{venue_id}/catering/events/{event_id}/quote")
@limiter.limit("30/minute")
async def generate_catering_quote(
    request: Request,
    venue_id: int,
    event_id: str,
    package_id: Optional[str] = Body(None),
    custom_items: Optional[List[Dict]] = Body(None),
    staff_count: int = Body(0),
    delivery_fee: float = Body(0),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Generate catering quote in database"""
    verify_venue_access(venue_id, current_user)
    try:
        event_id_int = int(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event_id format")

    event = db.query(CateringEvent).filter(
        CateringEvent.id == event_id_int
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Calculate quote
    food_total = 0.0
    items_list = []

    if package_id:
        try:
            package_id_int = int(package_id)
            from app.models.missing_features_models import CateringPackage
            package = db.query(CateringPackage).filter(
                CateringPackage.id == package_id_int
            ).first()
            if package and package.price_per_person:
                food_total = float(package.price_per_person) * event.guest_count
                items_list.append({"name": package.name, "quantity": event.guest_count, "price": float(package.price_per_person)})
        except ValueError:
            pass

    if custom_items:
        for item in custom_items:
            item_total = item.get("price", 0) * item.get("quantity", 1)
            food_total += item_total
            items_list.append(item)

    staff_cost = staff_count * 150.0  # 150 BGN per staff member
    total = food_total + staff_cost + delivery_fee

    # Update event with quote
    event.quoted_amount = Decimal(str(total))
    event.status = "quoted"

    db.commit()
    db.refresh(event)

    return {
        "event_id": event.id,
        "quote": {
            "food_total": round(food_total, 2),
            "staff_cost": round(staff_cost, 2),
            "delivery_fee": round(delivery_fee, 2),
            "total": round(total, 2),
            "guest_count": event.guest_count,
            "items": items_list
        }
    }

@router.get("/{venue_id}/catering/events/{event_id}/kitchen-sheet")
@limiter.limit("60/minute")
async def get_kitchen_sheet(
    request: Request,
    venue_id: int,
    event_id: str,
    db: Session = Depends(get_db)
):
    """Generate kitchen sheet from database"""
    try:
        event_id_int = int(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event_id format")

    event = db.query(CateringEvent).filter(
        CateringEvent.id == event_id_int
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get order items
    items = db.query(CateringOrderItem).filter(
        CateringOrderItem.catering_event_id == event_id_int
    ).all()

    return {
        "event_id": event.id,
        "event_name": event.event_name,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "guest_count": event.guest_count,
        "items": [
            {
                "name": item.item_name,
                "quantity": item.quantity,
                "notes": item.special_instructions
            }
            for item in items
        ],
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

@router.get("/{venue_id}/catering/events/{event_id}/labels")
@limiter.limit("60/minute")
async def get_catering_labels(
    request: Request,
    venue_id: int,
    event_id: str,
    db: Session = Depends(get_db)
):
    """Generate catering labels from database"""
    try:
        event_id_int = int(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event_id format")

    event = db.query(CateringEvent).filter(
        CateringEvent.id == event_id_int
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    items = db.query(CateringOrderItem).filter(
        CateringOrderItem.catering_event_id == event_id_int
    ).all()

    labels = []
    for item in items:
        labels.append({
            "item_name": item.item_name,
            "quantity": item.quantity,
            "event_name": event.event_name,
            "event_date": event.event_date.strftime("%d/%m/%Y") if event.event_date else "",
            "allergens": item.allergens or [],
            "dietary_info": item.dietary_info or []
        })

    return {"labels": labels}

@router.post("/{venue_id}/catering/events/{event_id}/invoice")
@limiter.limit("30/minute")
async def create_catering_invoice(
    request: Request,
    venue_id: int,
    event_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Create catering invoice in database"""
    verify_venue_access(venue_id, current_user)
    try:
        event_id_int = int(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    event = db.query(CateringEvent).filter(
        CateringEvent.id == event_id_int
    ).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Generate invoice number
    invoice_count = db.query(func.count(CateringInvoice.id)).filter(
        CateringInvoice.venue_id == venue_id
    ).scalar() or 0
    invoice_number = f"CAT-{venue_id}-{invoice_count + 1:05d}"

    invoice = CateringInvoice(
        venue_id=venue_id,
        catering_event_id=event_id_int,
        invoice_number=invoice_number,
        subtotal=event.quoted_amount or Decimal("0"),
        tax_amount=Decimal(str(float(event.quoted_amount or 0) * 0.2)),  # 20% VAT
        total_amount=Decimal(str(float(event.quoted_amount or 0) * 1.2)),
        status="issued",
        issued_date=datetime.now(timezone.utc).date(),
        due_date=(datetime.now(timezone.utc) + timedelta(days=14)).date()
    )

    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "total": float(invoice.total_amount)
    }


# ============================================================================
# TIER 1: CUSTOMER DISPLAY (5 endpoints)
# ============================================================================

@router.post("/{venue_id}/displays")
@limiter.limit("30/minute")
async def register_customer_display(
    request: Request,
    venue_id: int,
    terminal_id: str = Body(...),
    name: str = Body(...),
    language: str = Body("bg"),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Register customer display in database"""
    verify_venue_access(venue_id, current_user)
    # Check if display already exists
    existing = db.query(CustomerDisplay).filter(
        CustomerDisplay.venue_id == venue_id,
        CustomerDisplay.terminal_id == terminal_id
    ).first()

    if existing:
        existing.name = name
        existing.language = language
        existing.is_active = True
        existing.last_seen_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return {"display_id": existing.id, "name": existing.name}

    display = CustomerDisplay(
        venue_id=venue_id,
        terminal_id=terminal_id,
        name=name,
        language=language,
        display_mode="idle",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc)
    )

    db.add(display)
    db.commit()
    db.refresh(display)

    return {"display_id": display.id, "name": display.name}

@router.post("/{venue_id}/displays/{display_id}/order")
@limiter.limit("30/minute")
async def update_display_order(
    request: Request,
    venue_id: int,
    display_id: str,
    order_data: Dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Update customer display with order info in database"""
    verify_venue_access(venue_id, current_user)
    try:
        display_id_int = int(display_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid display_id format")

    display = db.query(CustomerDisplay).filter(
        CustomerDisplay.id == display_id_int
    ).first()

    if not display:
        raise HTTPException(status_code=404, detail="Display not found")

    display.display_mode = "order"
    display.current_order_data = order_data
    display.last_seen_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "display_id": display.id,
        "mode": "order",
        "order_data": order_data
    }

@router.post("/{venue_id}/displays/{display_id}/payment")
@limiter.limit("30/minute")
async def show_payment_screen(
    request: Request,
    venue_id: int,
    display_id: str,
    total: float = Body(...),
    payment_method: str = Body("card"),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Show payment screen on display in database"""
    verify_venue_access(venue_id, current_user)
    try:
        display_id_int = int(display_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid display_id format")

    display = db.query(CustomerDisplay).filter(
        CustomerDisplay.id == display_id_int
    ).first()

    if not display:
        raise HTTPException(status_code=404, detail="Display not found")

    display.display_mode = "payment"
    display.last_seen_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "display_id": display.id,
        "mode": "payment",
        "total": total,
        "payment_method": payment_method
    }

@router.post("/{venue_id}/displays/{display_id}/survey")
@limiter.limit("30/minute")
async def show_survey(
    request: Request,
    venue_id: int,
    display_id: str,
    order_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    """Show survey on display in database"""
    verify_venue_access(venue_id, current_user)
    try:
        display_id_int = int(display_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid display_id format")

    display = db.query(CustomerDisplay).filter(
        CustomerDisplay.id == display_id_int
    ).first()

    if not display:
        raise HTTPException(status_code=404, detail="Display not found")

    display.display_mode = "survey"
    display.last_seen_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "display_id": display.id,
        "mode": "survey",
        "order_id": order_id
    }

@router.post("/{venue_id}/displays/{display_id}/idle")
@limiter.limit("30/minute")
async def show_idle_screen(request: Request, venue_id: int, display_id: str, db: Session = Depends(get_db), current_user=Depends(require_manager)):
    """Show idle screen on customer display from database"""
    verify_venue_access(venue_id, current_user)
    try:
        display_id_int = int(display_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid venue_id or display_id format")

    # Query display from database
    display = db.query(CustomerDisplay).filter(
        CustomerDisplay.venue_id == venue_id,
        CustomerDisplay.id == display_id_int,
        CustomerDisplay.is_active == True
    ).first()

    if not display:
        raise HTTPException(status_code=404, detail="Display not found")

    # Update display mode to idle
    display.display_mode = "idle"
    display.last_seen_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "display_id": display.id,
        "mode": "idle",
        "idle_content_type": display.idle_content_type,
        "idle_content_config": display.idle_content_config,
        "theme": display.theme,
        "language": display.language
    }


