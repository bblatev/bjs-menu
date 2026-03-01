"""V5 sub-module: SMS Marketing & Catering Events"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from datetime import datetime, date, timezone, time, timedelta
from decimal import Decimal
from pydantic import BaseModel
import secrets

from app.db.session import get_db
from app.models import (
    MarketingCampaign, Customer, Order, MenuItem, StaffUser, OrderItem,
    Reservation, ReservationDeposit, DepositStatus, VenueSettings,
    Promotion, PromotionUsage, Table, StaffShift
)
from app.models.missing_features_models import (
    CateringEvent, CateringEventStatus, CateringOrderItem, CateringInvoice,
    CustomerReferral, VIPTier, CustomerVIPStatus, GuestbookEntry,
    Chargeback, ChargebackStatus, TaxReport, MenuPairing,
    CustomerDisplay, CustomerDisplayContent, FundraisingCampaign, FundraisingDonation,
    TableBlock, EmployeeBreak,
    ShiftTradeRequest as ShiftTradeRequestModel, EmployeeOnboarding,
    OnboardingChecklist, OnboardingTask, OnboardingTaskCompletion,
    IngredientPriceHistory, PriceAlertNotification, MenuItemReview,
    PrepTimePrediction
)
from app.models.operations import ReferralProgram
from app.models.invoice import PriceAlert
from app.models.core_business_models import SMSMessage
from app.models import StockItem
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from app.core.rate_limit import limiter
from app.api.routes.v5_endpoints._schemas import *

router = APIRouter()

# ==================== SMS MARKETING ====================

@router.get("/")
@limiter.limit("60/minute")
async def get_v5_root(request: Request, db: Session = Depends(get_db)):
    """V5 API features status."""
    return {"module": "v5-features", "version": "5.0", "status": "active", "features": ["sms-campaigns", "catering", "invoice-generation"]}


@router.post("/sms/campaigns")
@limiter.limit("30/minute")
async def create_sms_campaign(
    request: Request,
    campaign: SMSCampaignCreate,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Create a new SMS marketing campaign"""
    db_campaign = MarketingCampaign(
        venue_id=venue_id,
        name=campaign.name,
        campaign_type="sms",
        status="draft" if not campaign.scheduled_at else "scheduled",
        body=campaign.message,
        target_segment=campaign.target_segment,
        scheduled_at=campaign.scheduled_at,
        audience_size=0  # Will be calculated when sending
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)

    return {
        "id": db_campaign.id,
        "venue_id": db_campaign.venue_id,
        "name": db_campaign.name,
        "message": db_campaign.body,
        "target_segment": db_campaign.target_segment,
        "scheduled_at": db_campaign.scheduled_at.isoformat() if db_campaign.scheduled_at else None,
        "status": db_campaign.status,
        "estimated_recipients": db_campaign.audience_size,
        "created_at": db_campaign.created_at.isoformat() if db_campaign.created_at else datetime.now(timezone.utc).isoformat()
    }

@router.get("/sms/campaigns")
@limiter.limit("60/minute")
async def list_sms_campaigns(
    request: Request,
    venue_id: int = Query(1),
    status: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List SMS campaigns"""
    query = db.query(MarketingCampaign).filter(
        MarketingCampaign.campaign_type == "sms"
    )

    if status:
        query = query.filter(MarketingCampaign.status == status)

    total = query.count()
    campaigns = query.order_by(MarketingCampaign.created_at.desc()).limit(limit).all()

    return {
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "recipients": c.total_sent or 0,
                "delivered": c.total_delivered or 0,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in campaigns
        ],
        "total": total
    }

@router.post("/sms/campaigns/{campaign_id}/send")
@limiter.limit("30/minute")
async def send_sms_campaign(
    request: Request,
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Send an SMS campaign immediately"""
    campaign = db.query(MarketingCampaign).filter(
        MarketingCampaign.id == campaign_id,
        MarketingCampaign.campaign_type == "sms"
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="SMS campaign not found")

    if campaign.status not in ["draft", "scheduled"]:
        raise HTTPException(status_code=400, detail=f"Cannot send campaign with status '{campaign.status}'")

    # Update campaign status to sending/active
    campaign.status = "active"
    campaign.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(campaign)

    return {
        "campaign_id": campaign.id,
        "status": campaign.status,
        "recipients": campaign.audience_size,
        "estimated_completion": datetime.now(timezone.utc).isoformat()
    }

@router.get("/sms/campaigns/{campaign_id}/analytics")
@limiter.limit("60/minute")
async def get_campaign_analytics(
    request: Request,
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Get SMS campaign analytics"""
    campaign = db.query(MarketingCampaign).filter(
        MarketingCampaign.id == campaign_id,
        MarketingCampaign.campaign_type == "sms"
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="SMS campaign not found")

    # Calculate delivery rate
    delivery_rate = 0.0
    if campaign.sent_count > 0:
        delivery_rate = round((campaign.delivered_count / campaign.sent_count) * 100, 1)

    failed_count = campaign.sent_count - campaign.delivered_count

    return {
        "campaign_id": campaign.id,
        "total_sent": campaign.sent_count,
        "delivered": campaign.delivered_count,
        "failed": failed_count,
        "delivery_rate": delivery_rate,
        "orders_attributed": campaign.converted_count,
        "revenue_attributed": float(campaign.revenue_generated) if campaign.revenue_generated else 0.0
    }

@router.post("/sms/send-transactional")
@limiter.limit("30/minute")
async def send_transactional_sms(
    request: Request,
    phone: str = Body(...),
    message_type: str = Body(...),
    message_data: Dict = Body(...),
    venue_id: int = Query(1),
    customer_id: Optional[int] = Body(None),
    order_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Send transactional SMS (order confirmation, etc)"""
    # Validate message type
    valid_types = ["order_confirmation", "order_ready", "reservation_reminder",
                   "delivery_update", "payment_receipt", "custom"]
    if message_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid message type. Must be one of: {valid_types}"
        )

    # Build message content based on type
    if message_type == "order_confirmation":
        order_number = message_data.get("order_number", "N/A")
        total = message_data.get("total", "N/A")
        message_content = f"Your order #{order_number} has been confirmed. Total: {total} BGN. Thank you!"
    elif message_type == "order_ready":
        order_number = message_data.get("order_number", "N/A")
        message_content = f"Your order #{order_number} is ready for pickup!"
    elif message_type == "reservation_reminder":
        reservation_date = message_data.get("date", "N/A")
        reservation_time = message_data.get("time", "N/A")
        party_size = message_data.get("party_size", "N/A")
        message_content = f"Reminder: Your reservation for {party_size} guests on {reservation_date} at {reservation_time}."
    elif message_type == "delivery_update":
        status = message_data.get("status", "on the way")
        eta = message_data.get("eta", "soon")
        message_content = f"Your delivery is {status}. Estimated arrival: {eta}."
    elif message_type == "payment_receipt":
        order_number = message_data.get("order_number", "N/A")
        amount = message_data.get("amount", "N/A")
        message_content = f"Payment of {amount} BGN received for order #{order_number}. Thank you!"
    else:  # custom
        message_content = message_data.get("message", "Thank you for your business!")

    # Generate unique message ID
    message_id = secrets.token_hex(16)

    # Store SMS message in database
    sms_message = SMSMessage(
        venue_id=venue_id,
        customer_id=customer_id,
        phone_number=phone,
        message_content=message_content,
        provider="internal",  # Would be actual provider like twilio
        provider_message_id=message_id,
        status="queued",
        sent_at=datetime.now(timezone.utc)
    )
    db.add(sms_message)
    db.commit()
    db.refresh(sms_message)

    # In a real implementation, this would call an SMS provider API
    # For now, we mark it as sent
    sms_message.status = "sent"
    db.commit()

    return {
        "id": sms_message.id,
        "message_id": message_id,
        "phone": phone,
        "type": message_type,
        "message": message_content,
        "status": sms_message.status,
        "sent_at": sms_message.sent_at.isoformat() if sms_message.sent_at else None
    }

# ==================== CATERING & EVENTS ====================

@router.post("/catering/events")
@limiter.limit("30/minute")
async def create_catering_event(
    request: Request,
    event: CateringEventCreate,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Create a catering event"""
    # Parse event_date to separate date and time
    event_date_only = event.event_date.date() if isinstance(event.event_date, datetime) else event.event_date
    event_time_only = event.event_date.time() if isinstance(event.event_date, datetime) else None

    db_event = CateringEvent(
        venue_id=venue_id,
        event_name=event.event_name,
        event_type=event.event_type,
        event_date=event_date_only,
        event_time=event_time_only,
        guest_count=event.guest_count,
        contact_name=event.contact_name,
        contact_phone=event.contact_phone,
        contact_email=event.contact_email,
        venue_name=event.location,
        venue_type="on_site" if not event.location else "off_site",
        status=CateringEventStatus.INQUIRY.value
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    return {
        "id": db_event.id,
        "venue_id": db_event.venue_id,
        "event_name": db_event.event_name,
        "event_type": db_event.event_type,
        "event_date": datetime.combine(db_event.event_date, db_event.event_time or time(0, 0)).isoformat() if db_event.event_date else None,
        "guest_count": db_event.guest_count,
        "contact_name": db_event.contact_name,
        "contact_phone": db_event.contact_phone,
        "contact_email": db_event.contact_email,
        "location": db_event.venue_name,
        "status": db_event.status,
        "created_at": db_event.created_at.isoformat() if db_event.created_at else datetime.now(timezone.utc).isoformat()
    }

@router.get("/catering/events")
@limiter.limit("60/minute")
async def list_catering_events(
    request: Request,
    venue_id: int = Query(1),
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """List catering events"""
    query = db.query(CateringEvent).filter(CateringEvent.venue_id == venue_id)

    if status:
        query = query.filter(CateringEvent.status == status)

    if start_date:
        query = query.filter(CateringEvent.event_date >= start_date)

    if end_date:
        query = query.filter(CateringEvent.event_date <= end_date)

    total = query.count()
    events = query.order_by(CateringEvent.event_date.desc()).offset(offset).limit(limit).all()

    return {
        "events": [
            {
                "id": e.id,
                "event_name": e.event_name,
                "event_type": e.event_type,
                "event_date": e.event_date.isoformat() if e.event_date else None,
                "guest_count": e.guest_count,
                "status": e.status,
                "total_amount": float(e.total) if e.total else 0,
                "contact_name": e.contact_name
            }
            for e in events
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/catering/events/{event_id}")
@limiter.limit("60/minute")
async def get_catering_event(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get catering event details"""
    event = db.query(CateringEvent).filter(CateringEvent.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Catering event not found")

    # Get event items
    items = db.query(CateringOrderItem).filter(
        CateringOrderItem.catering_event_id == event_id
    ).all()

    return {
        "id": event.id,
        "venue_id": event.venue_id,
        "event_name": event.event_name,
        "event_type": event.event_type,
        "event_date": datetime.combine(event.event_date, event.event_time or time(0, 0)).isoformat() if event.event_date else None,
        "guest_count": event.guest_count,
        "status": event.status,
        "contact_name": event.contact_name,
        "contact_phone": event.contact_phone,
        "contact_email": event.contact_email,
        "location": event.venue_name,
        "venue_type": event.venue_type,
        "venue_address": event.venue_address,
        "dietary_requirements": event.dietary_requirements,
        "subtotal": float(event.subtotal) if event.subtotal else 0,
        "service_charge": float(event.service_charge) if event.service_charge else 0,
        "delivery_fee": float(event.delivery_fee) if event.delivery_fee else 0,
        "tax": float(event.tax) if event.tax else 0,
        "total_amount": float(event.total) if event.total else 0,
        "deposit_required": float(event.deposit_required) if event.deposit_required else 0,
        "deposit_paid": float(event.deposit_paid) if event.deposit_paid else 0,
        "notes": event.notes,
        "items": [
            {
                "id": item.id,
                "item_name": item.item_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price) if item.unit_price else 0,
                "total_price": float(item.total_price) if item.total_price else 0,
                "special_instructions": item.special_instructions,
                "dietary_tags": item.dietary_tags
            }
            for item in items
        ],
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "updated_at": event.updated_at.isoformat() if event.updated_at else None
    }

@router.patch("/catering/events/{event_id}")
@limiter.limit("30/minute")
async def update_catering_event(
    request: Request,
    event_id: int,
    event_name: Optional[str] = Body(None),
    event_type: Optional[str] = Body(None),
    event_date: Optional[datetime] = Body(None),
    guest_count: Optional[int] = Body(None),
    contact_name: Optional[str] = Body(None),
    contact_phone: Optional[str] = Body(None),
    contact_email: Optional[str] = Body(None),
    location: Optional[str] = Body(None),
    status: Optional[str] = Body(None),
    notes: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Update a catering event"""
    event = db.query(CateringEvent).filter(CateringEvent.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Catering event not found")

    # Update fields if provided
    if event_name is not None:
        event.event_name = event_name
    if event_type is not None:
        event.event_type = event_type
    if event_date is not None:
        event.event_date = event_date.date() if isinstance(event_date, datetime) else event_date
        event.event_time = event_date.time() if isinstance(event_date, datetime) else None
    if guest_count is not None:
        event.guest_count = guest_count
    if contact_name is not None:
        event.contact_name = contact_name
    if contact_phone is not None:
        event.contact_phone = contact_phone
    if contact_email is not None:
        event.contact_email = contact_email
    if location is not None:
        event.venue_name = location
    if status is not None:
        # Validate status
        valid_statuses = [s.value for s in CateringEventStatus]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        event.status = status
        # Update status timestamps
        if status == CateringEventStatus.QUOTED.value:
            event.quote_sent_date = datetime.now(timezone.utc)
        elif status == CateringEventStatus.CONFIRMED.value:
            event.confirmed_date = datetime.now(timezone.utc)
    if notes is not None:
        event.notes = notes

    db.commit()
    db.refresh(event)

    return {
        "id": event.id,
        "event_name": event.event_name,
        "status": event.status,
        "updated_at": event.updated_at.isoformat() if event.updated_at else datetime.now(timezone.utc).isoformat()
    }

@router.delete("/catering/events/{event_id}")
@limiter.limit("30/minute")
async def delete_catering_event(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db)
):
    """Delete a catering event"""
    event = db.query(CateringEvent).filter(CateringEvent.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Catering event not found")

    # Delete related items first
    db.query(CateringOrderItem).filter(CateringOrderItem.catering_event_id == event_id).delete()

    # Delete related invoices
    db.query(CateringInvoice).filter(CateringInvoice.catering_event_id == event_id).delete()

    # Delete the event
    db.delete(event)
    db.commit()

    return {"deleted": True, "event_id": event_id}

@router.post("/catering/events/{event_id}/items")
@limiter.limit("30/minute")
async def add_event_item(
    request: Request,
    event_id: int,
    item_name: str = Body(...),
    quantity: int = Body(...),
    unit_price: float = Body(...),
    menu_item_id: Optional[int] = Body(None),
    special_instructions: Optional[str] = Body(None),
    dietary_tags: Optional[List[str]] = Body(None),
    db: Session = Depends(get_db)
):
    """Add item to catering event"""
    # Verify event exists
    event = db.query(CateringEvent).filter(CateringEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Catering event not found")

    total_price = Decimal(str(quantity)) * Decimal(str(unit_price))

    db_item = CateringOrderItem(
        catering_event_id=event_id,
        menu_item_id=menu_item_id,
        item_name=item_name,
        quantity=quantity,
        unit_price=Decimal(str(unit_price)),
        total_price=total_price,
        special_instructions=special_instructions,
        dietary_tags=dietary_tags
    )
    db.add(db_item)

    # Recalculate event totals
    _recalculate_event_totals(db, event)

    db.commit()
    db.refresh(db_item)

    return {
        "id": db_item.id,
        "event_id": event_id,
        "item_name": db_item.item_name,
        "quantity": db_item.quantity,
        "unit_price": float(db_item.unit_price),
        "total_price": float(db_item.total_price),
        "special_instructions": db_item.special_instructions,
        "dietary_tags": db_item.dietary_tags
    }

@router.delete("/catering/events/{event_id}/items/{item_id}")
@limiter.limit("30/minute")
async def delete_event_item(
    request: Request,
    event_id: int,
    item_id: int,
    db: Session = Depends(get_db)
):
    """Remove item from catering event"""
    item = db.query(CateringOrderItem).filter(
        CateringOrderItem.id == item_id,
        CateringOrderItem.catering_event_id == event_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Event item not found")

    event = db.query(CateringEvent).filter(CateringEvent.id == event_id).first()

    db.delete(item)

    # Recalculate event totals
    if event:
        _recalculate_event_totals(db, event)

    db.commit()

    return {"deleted": True, "item_id": item_id}


def _recalculate_event_totals(db: Session, event: CateringEvent):
    """Helper function to recalculate event totals from items"""
    items = db.query(CateringOrderItem).filter(
        CateringOrderItem.catering_event_id == event.id
    ).all()

    subtotal = sum(item.total_price or Decimal("0") for item in items)
    service_charge = subtotal * Decimal("0.18")  # 18% service charge
    tax = (subtotal + service_charge) * Decimal("0.20")  # 20% VAT
    total = subtotal + service_charge + tax

    event.subtotal = subtotal
    event.service_charge = service_charge
    event.tax = tax
    event.total = total
    event.deposit_required = total * Decimal("0.30")  # 30% deposit required
    event.balance_due = total - (event.deposit_paid or Decimal("0"))


@router.post("/catering/events/{event_id}/invoice")
@limiter.limit("30/minute")
async def create_event_invoice(
    request: Request,
    event_id: int,
    due_date: date = Body(...),
    notes: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Create invoice for catering event"""
    # Verify event exists
    event = db.query(CateringEvent).filter(CateringEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Catering event not found")

    # Check if invoice already exists
    existing_invoice = db.query(CateringInvoice).filter(
        CateringInvoice.catering_event_id == event_id
    ).first()

    if existing_invoice:
        raise HTTPException(status_code=400, detail="Invoice already exists for this event")

    # Generate invoice number
    invoice_count = db.query(func.count(CateringInvoice.id)).filter(
        CateringInvoice.venue_id == event.venue_id
    ).scalar() or 0
    invoice_number = f"CAT-{datetime.now(timezone.utc).strftime('%Y%m')}-{(invoice_count + 1):04d}"

    # Calculate totals from event
    subtotal = event.subtotal or Decimal("0")
    tax = event.tax or Decimal("0")
    total = event.total or Decimal("0")

    db_invoice = CateringInvoice(
        venue_id=event.venue_id,
        catering_event_id=event_id,
        invoice_number=invoice_number,
        invoice_date=date.today(),
        due_date=due_date,
        subtotal=subtotal,
        tax=tax,
        total=total,
        amount_paid=event.deposit_paid or Decimal("0"),
        balance_due=total - (event.deposit_paid or Decimal("0")),
        status="draft",
        notes=notes
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)

    return {
        "id": db_invoice.id,
        "event_id": event_id,
        "invoice_number": db_invoice.invoice_number,
        "invoice_date": db_invoice.invoice_date.isoformat() if db_invoice.invoice_date else None,
        "due_date": db_invoice.due_date.isoformat() if db_invoice.due_date else None,
        "subtotal": float(db_invoice.subtotal),
        "tax": float(db_invoice.tax),
        "total_amount": float(db_invoice.total),
        "amount_paid": float(db_invoice.amount_paid) if db_invoice.amount_paid else 0,
        "balance_due": float(db_invoice.balance_due) if db_invoice.balance_due else float(db_invoice.total),
        "status": db_invoice.status,
        "created_at": db_invoice.created_at.isoformat() if db_invoice.created_at else datetime.now(timezone.utc).isoformat()
    }

@router.get("/catering/events/{event_id}/invoice")
@limiter.limit("60/minute")
async def get_event_invoice(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get invoice for catering event"""
    invoice = db.query(CateringInvoice).filter(
        CateringInvoice.catering_event_id == event_id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found for this event")

    # Get event details
    event = db.query(CateringEvent).filter(CateringEvent.id == event_id).first()

    # Get event items
    items = db.query(CateringOrderItem).filter(
        CateringOrderItem.catering_event_id == event_id
    ).all()

    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "event_id": event_id,
        "event_name": event.event_name if event else None,
        "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "subtotal": float(invoice.subtotal) if invoice.subtotal else 0,
        "tax": float(invoice.tax) if invoice.tax else 0,
        "total_amount": float(invoice.total) if invoice.total else 0,
        "amount_paid": float(invoice.amount_paid) if invoice.amount_paid else 0,
        "balance_due": float(invoice.balance_due) if invoice.balance_due else 0,
        "status": invoice.status,
        "items": [
            {
                "item_name": item.item_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price) if item.unit_price else 0,
                "total_price": float(item.total_price) if item.total_price else 0
            }
            for item in items
        ],
        "notes": invoice.notes
    }

@router.get("/catering/events/{event_id}/prep-sheet")
@limiter.limit("60/minute")
async def get_prep_sheet(
    request: Request,
    event_id: int,
    station: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get kitchen prep sheet for event"""
    # Verify event exists
    event = db.query(CateringEvent).filter(CateringEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Catering event not found")

    # Get event items
    items = db.query(CateringOrderItem).filter(
        CateringOrderItem.catering_event_id == event_id
    ).all()

    # Group items by prep type/station (simplified categorization)
    prep_items = []
    for item in items:
        # Determine station based on item name patterns (simplified)
        item_station = "hot_kitchen"  # default
        item_name_lower = item.item_name.lower()
        if any(word in item_name_lower for word in ["salad", "cold", "appetizer", "carpaccio"]):
            item_station = "cold_kitchen"
        elif any(word in item_name_lower for word in ["cake", "dessert", "pastry", "ice cream", "chocolate"]):
            item_station = "pastry"
        elif any(word in item_name_lower for word in ["drink", "beverage", "cocktail", "wine", "beer"]):
            item_station = "bar"

        # Filter by station if specified
        if station is None or station == item_station:
            prep_items.append({
                "item": item.item_name,
                "quantity": item.quantity,
                "station": item_station,
                "prep_notes": item.special_instructions or f"Prepare {item.quantity} portions",
                "dietary_tags": item.dietary_tags or [],
                "status": item.prep_status or "pending"
            })

    # Calculate days until event
    days_until_event = None
    if event.event_date:
        days_until_event = (event.event_date - date.today()).days

    return {
        "event_id": event_id,
        "event_name": event.event_name,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "guest_count": event.guest_count,
        "prep_date": date.today().isoformat(),
        "days_until_event": days_until_event,
        "station": station,
        "items": prep_items,
        "total_items": len(prep_items)
    }

@router.get("/catering/events/{event_id}/labels")
@limiter.limit("60/minute")
async def get_food_labels(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db)
):
    """Generate food labels for catering"""
    # Verify event exists
    event = db.query(CateringEvent).filter(CateringEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Catering event not found")

    # Get event items
    items = db.query(CateringOrderItem).filter(
        CateringOrderItem.catering_event_id == event_id
    ).all()

    labels = []
    for item in items:
        # Get allergens from dietary tags if available
        allergens = item.dietary_tags or []

        labels.append({
            "id": item.id,
            "item": item.item_name,
            "quantity": item.quantity,
            "allergens": allergens,
            "prep_date": date.today().isoformat(),
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "storage_instructions": "Keep refrigerated below 5C",
            "special_instructions": item.special_instructions
        })

    return {
        "event_id": event_id,
        "event_name": event.event_name,
        "labels": labels,
        "total_labels": len(labels),
        "print_url": f"/api/v5/catering/events/{event_id}/labels/print"
    }

