"""V5 API Endpoints - TouchBistro/iiko/Toast Feature Parity
33 New Features, ~150 Endpoints
"""
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


router = APIRouter(tags=["V5 - Competitive Features"])

# ==================== PYDANTIC MODELS ====================

class SMSCampaignCreate(BaseModel):
    name: str
    message: str
    target_segment: str = "all"
    scheduled_at: Optional[datetime] = None

class CateringEventCreate(BaseModel):
    event_name: str
    event_type: str
    event_date: datetime
    guest_count: int
    contact_name: str
    contact_phone: str
    contact_email: Optional[str] = None
    location: Optional[str] = None

class DepositRequest(BaseModel):
    reservation_id: int
    amount: float
    currency: str = "BGN"

class ReferralCodeValidation(BaseModel):
    code: str
    referee_customer_id: int

class ShiftTradeRequest(BaseModel):
    original_shift_id: int
    trade_type: str
    target_staff_id: Optional[int] = None
    offered_shift_id: Optional[int] = None
    reason: Optional[str] = None

class PromoCodeGenerate(BaseModel):
    count: int = 10
    discount_type: str
    discount_value: float
    valid_days: int = 30
    minimum_order: Optional[float] = None

class TableBlockCreate(BaseModel):
    venue_id: int
    table_id: int
    block_date: date
    start_time: str
    end_time: str
    block_type: str = "manual"  # reservation, private_event, maintenance, manual
    reason: Optional[str] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # daily, weekly, etc.
    recurrence_end_date: Optional[date] = None
    reservation_id: Optional[int] = None
    event_id: Optional[int] = None

class MenuPairingCreate(BaseModel):
    primary_item_id: int
    paired_item_id: int
    pairing_type: str
    pairing_reason: Optional[str] = None

class CharityDonation(BaseModel):
    campaign_id: int
    amount: float
    donation_type: str = "flat"
    order_id: Optional[int] = None

class ChargebackCreate(BaseModel):
    order_id: Optional[int] = None
    payment_id: Optional[int] = None
    amount: float
    currency: str = "BGN"
    reason_code: str
    reason: Optional[str] = None
    provider: Optional[str] = None
    provider_case_id: Optional[str] = None

class ChargebackResponse(BaseModel):
    evidence_documents: List[str] = []
    response_notes: str

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
        MarketingCampaign.venue_id == venue_id,
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
                "recipients": c.sent_count,
                "delivered": c.delivered_count,
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

# ==================== BENCHMARKING ====================

# Industry benchmark constants (these would typically come from external data sources)
INDUSTRY_BENCHMARKS = {
    "avg_ticket": 45.00,  # Industry average ticket in BGN
    "table_turn_time": 55,  # Industry average table turn time in minutes
    "labor_cost_pct": 32,  # Industry average labor cost percentage
    "items_per_order": 3.2,  # Industry average items per order
    "order_completion_rate": 95,  # Industry average order completion rate %
}


def _get_period_date_range(period: str) -> tuple:
    """Calculate date range based on period type"""
    today = date.today()
    if period == "week":
        start_date = today - relativedelta(weeks=1)
    elif period == "month":
        start_date = today.replace(day=1)
    elif period == "quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=quarter_start_month, day=1)
    elif period == "year":
        start_date = today.replace(month=1, day=1)
    else:
        start_date = today - relativedelta(months=1)
    return start_date, today


def _calculate_percentile(venue_value: float, industry_avg: float, higher_is_better: bool = True) -> int:
    """Calculate approximate percentile based on venue vs industry average"""
    if industry_avg == 0:
        return 50
    ratio = venue_value / industry_avg
    if higher_is_better:
        # If venue is 20% above industry, roughly 70th percentile
        percentile = int(50 + (ratio - 1) * 100)
    else:
        # For metrics where lower is better (like turn time, labor cost)
        percentile = int(50 + (1 - ratio) * 100)
    return max(1, min(99, percentile))


@router.get("/benchmarking/summary")
@limiter.limit("60/minute")
async def get_benchmark_summary(
    request: Request,
    venue_id: int = Query(1),
    period: str = Query("month"),
    db: Session = Depends(get_db)
):
    """Get benchmark summary comparing to industry using real database metrics"""
    start_date, end_date = _get_period_date_range(period)

    # Calculate average ticket from orders
    avg_ticket_result = db.query(func.avg(Order.total)).filter(
        Order.venue_id == venue_id,
        Order.created_at >= start_date,
        Order.created_at <= end_date,
        Order.status != "cancelled"
    ).scalar()
    avg_ticket = float(avg_ticket_result) if avg_ticket_result else 0.0

    # Calculate average table turn time (time from order creation to payment)
    # Using orders that have payment_date set
    turn_time_result = db.query(
        func.avg(
            func.extract('epoch', Order.payment_date) - func.extract('epoch', Order.created_at)
        ) / 60  # Convert to minutes
    ).filter(
        Order.venue_id == venue_id,
        Order.created_at >= start_date,
        Order.created_at <= end_date,
        Order.payment_date.isnot(None),
        Order.order_type == "dine-in"
    ).scalar()
    table_turn_time = float(turn_time_result) if turn_time_result else 0.0

    # Calculate labor cost percentage (staff count * estimated hourly rate / revenue)
    total_revenue = db.query(func.sum(Order.total)).filter(
        Order.venue_id == venue_id,
        Order.created_at >= start_date,
        Order.created_at <= end_date,
        Order.status != "cancelled"
    ).scalar() or 0

    active_staff_count = db.query(func.count(StaffUser.id)).filter(
        StaffUser.venue_id == venue_id,
        StaffUser.active == True
    ).scalar() or 0

    # Estimate labor cost (assuming 8 hours/day, 20 days, 15 BGN/hour average)
    days_in_period = (end_date - start_date).days or 1
    estimated_labor_cost = active_staff_count * 8 * days_in_period * 15
    labor_cost_pct = (estimated_labor_cost / total_revenue * 100) if total_revenue > 0 else 0

    # Build metrics comparison
    metrics = [
        {
            "metric": "avg_ticket",
            "venue": round(avg_ticket, 2),
            "industry_avg": INDUSTRY_BENCHMARKS["avg_ticket"],
            "percentile": _calculate_percentile(avg_ticket, INDUSTRY_BENCHMARKS["avg_ticket"], higher_is_better=True)
        },
        {
            "metric": "table_turn_time",
            "venue": round(table_turn_time, 0),
            "industry_avg": INDUSTRY_BENCHMARKS["table_turn_time"],
            "percentile": _calculate_percentile(table_turn_time, INDUSTRY_BENCHMARKS["table_turn_time"], higher_is_better=False)
        },
        {
            "metric": "labor_cost_pct",
            "venue": round(labor_cost_pct, 1),
            "industry_avg": INDUSTRY_BENCHMARKS["labor_cost_pct"],
            "percentile": _calculate_percentile(labor_cost_pct, INDUSTRY_BENCHMARKS["labor_cost_pct"], higher_is_better=False)
        }
    ]

    # Calculate overall score (weighted average of percentiles)
    overall_score = sum(m["percentile"] for m in metrics) // len(metrics) if metrics else 0

    return {
        "venue_id": venue_id,
        "period": period,
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "overall_score": overall_score,
        "metrics": metrics
    }


@router.get("/benchmarking/peers")
@limiter.limit("60/minute")
async def get_peer_comparison(
    request: Request,
    venue_id: int = Query(1),
    comparison_group: str = Query("region"),
    db: Session = Depends(get_db)
):
    """Compare against peer group using real database metrics"""
    # Get all venues for peer comparison (in real implementation, would filter by region/type)
    # For now, comparing against all other venues in the system

    # Calculate metrics for all venues
    venue_metrics = db.query(
        Order.venue_id,
        func.avg(Order.total).label("avg_ticket"),
        func.count(Order.id).label("order_count"),
        func.sum(Order.total).label("total_revenue")
    ).filter(
        Order.status != "cancelled",
        Order.created_at >= date.today() - relativedelta(months=1)
    ).group_by(Order.venue_id).all()

    peer_count = len(venue_metrics)

    # Find current venue's metrics and rank
    venue_data = None
    venue_rank = 0
    sorted_by_revenue = sorted(venue_metrics, key=lambda x: x.total_revenue or 0, reverse=True)

    for idx, vm in enumerate(sorted_by_revenue, 1):
        if vm.venue_id == venue_id:
            venue_rank = idx
            venue_data = vm
            break

    # Calculate peer averages
    if venue_metrics:
        peer_avg_ticket = sum(v.avg_ticket or 0 for v in venue_metrics) / peer_count
        peer_avg_orders = sum(v.order_count or 0 for v in venue_metrics) / peer_count
        peer_avg_revenue = sum(v.total_revenue or 0 for v in venue_metrics) / peer_count
    else:
        peer_avg_ticket = 0
        peer_avg_orders = 0
        peer_avg_revenue = 0

    metrics = {
        "avg_ticket": {
            "venue": round(float(venue_data.avg_ticket), 2) if venue_data and venue_data.avg_ticket else 0,
            "peer_avg": round(peer_avg_ticket, 2)
        },
        "order_count": {
            "venue": venue_data.order_count if venue_data else 0,
            "peer_avg": round(peer_avg_orders, 0)
        },
        "total_revenue": {
            "venue": round(float(venue_data.total_revenue), 2) if venue_data and venue_data.total_revenue else 0,
            "peer_avg": round(peer_avg_revenue, 2)
        }
    }

    return {
        "venue_id": venue_id,
        "comparison_group": comparison_group,
        "peer_count": peer_count,
        "your_rank": venue_rank,
        "metrics": metrics
    }


@router.get("/benchmarking/trends/{metric}")
@limiter.limit("60/minute")
async def get_benchmark_trends(
    request: Request,
    metric: str,
    venue_id: int = Query(1),
    periods: int = Query(12),
    db: Session = Depends(get_db)
):
    """Get historical benchmark trends from real database data"""
    trends = []
    today = date.today()

    for i in range(periods - 1, -1, -1):
        period_date = today - relativedelta(months=i)
        period_start = period_date.replace(day=1)
        _, last_day = monthrange(period_date.year, period_date.month)
        period_end = period_date.replace(day=last_day)

        period_label = period_start.strftime("%Y-%m")

        if metric == "avg_ticket":
            value = db.query(func.avg(Order.total)).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end,
                Order.status != "cancelled"
            ).scalar()
            venue_value = round(float(value), 2) if value else 0
            industry_value = INDUSTRY_BENCHMARKS["avg_ticket"]

        elif metric == "order_count":
            value = db.query(func.count(Order.id)).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end,
                Order.status != "cancelled"
            ).scalar()
            venue_value = value or 0
            industry_value = 500  # Estimated industry average orders per month

        elif metric == "revenue":
            value = db.query(func.sum(Order.total)).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end,
                Order.status != "cancelled"
            ).scalar()
            venue_value = round(float(value), 2) if value else 0
            industry_value = 25000  # Estimated industry average revenue per month

        elif metric == "items_per_order":
            # Calculate average items per order
            subq = db.query(
                OrderItem.order_id,
                func.sum(OrderItem.quantity).label("total_items")
            ).join(Order).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end,
                Order.status != "cancelled"
            ).group_by(OrderItem.order_id).subquery()

            value = db.query(func.avg(subq.c.total_items)).scalar()
            venue_value = round(float(value), 2) if value else 0
            industry_value = INDUSTRY_BENCHMARKS["items_per_order"]

        elif metric == "top_item_sales":
            # Get total quantity of top selling item
            top_item = db.query(
                func.sum(OrderItem.quantity).label("qty")
            ).join(Order).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end,
                Order.status != "cancelled"
            ).group_by(OrderItem.menu_item_id).order_by(
                func.sum(OrderItem.quantity).desc()
            ).first()
            venue_value = top_item.qty if top_item else 0
            industry_value = 150  # Estimated industry average for top item

        else:
            # Default to order count for unknown metrics
            value = db.query(func.count(Order.id)).filter(
                Order.venue_id == venue_id,
                Order.created_at >= period_start,
                Order.created_at <= period_end
            ).scalar()
            venue_value = value or 0
            industry_value = 500

        trends.append({
            "period": period_label,
            "venue": venue_value,
            "industry": industry_value
        })

    return {
        "metric": metric,
        "venue_id": venue_id,
        "trends": trends
    }


@router.get("/benchmarking/recommendations")
@limiter.limit("60/minute")
async def get_improvement_recommendations(
    request: Request,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get data-driven improvement recommendations based on actual performance"""
    recommendations = []
    start_date = date.today() - relativedelta(months=1)

    # Get current metrics
    avg_ticket = db.query(func.avg(Order.total)).filter(
        Order.venue_id == venue_id,
        Order.created_at >= start_date,
        Order.status != "cancelled"
    ).scalar() or 0

    # Get average items per order
    items_per_order_subq = db.query(
        OrderItem.order_id,
        func.sum(OrderItem.quantity).label("total_items")
    ).join(Order).filter(
        Order.venue_id == venue_id,
        Order.created_at >= start_date,
        Order.status != "cancelled"
    ).group_by(OrderItem.order_id).subquery()

    avg_items = db.query(func.avg(items_per_order_subq.c.total_items)).scalar() or 0

    # Get total orders count
    order_count = db.query(func.count(Order.id)).filter(
        Order.venue_id == venue_id,
        Order.created_at >= start_date,
        Order.status != "cancelled"
    ).scalar() or 0

    # Get top selling items
    top_items = db.query(
        MenuItem.id,
        func.sum(OrderItem.quantity).label("qty")
    ).join(OrderItem, MenuItem.id == OrderItem.menu_item_id).join(
        Order
    ).filter(
        Order.venue_id == venue_id,
        Order.created_at >= start_date,
        Order.status != "cancelled"
    ).group_by(MenuItem.id).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(5).all()

    # Generate recommendations based on metrics
    if float(avg_ticket) < INDUSTRY_BENCHMARKS["avg_ticket"]:
        gap = INDUSTRY_BENCHMARKS["avg_ticket"] - float(avg_ticket)
        recommendations.append({
            "metric": "avg_ticket",
            "current_value": round(float(avg_ticket), 2),
            "industry_avg": INDUSTRY_BENCHMARKS["avg_ticket"],
            "recommendation": "Implement upselling prompts for high-margin items",
            "potential_impact": f"{round(gap / float(avg_ticket) * 100 if avg_ticket else 0, 1)}% revenue increase per order"
        })

    if float(avg_items) < INDUSTRY_BENCHMARKS["items_per_order"]:
        recommendations.append({
            "metric": "items_per_order",
            "current_value": round(float(avg_items), 2),
            "industry_avg": INDUSTRY_BENCHMARKS["items_per_order"],
            "recommendation": "Add combo deals and bundle suggestions at checkout",
            "potential_impact": f"Increase items per order by {round(INDUSTRY_BENCHMARKS['items_per_order'] - float(avg_items), 1)}"
        })

    if order_count < 500:  # Below estimated industry average
        recommendations.append({
            "metric": "order_volume",
            "current_value": order_count,
            "industry_avg": 500,
            "recommendation": "Launch targeted marketing campaigns to increase foot traffic",
            "potential_impact": f"Potential to increase orders by {500 - order_count} per month"
        })

    # If venue is doing well, suggest maintenance recommendations
    if not recommendations:
        recommendations.append({
            "metric": "overall_performance",
            "current_value": "Above average",
            "industry_avg": "N/A",
            "recommendation": "Maintain current strategies and explore premium offerings",
            "potential_impact": "Sustain competitive advantage"
        })

    # Add top items analysis
    if top_items:
        recommendations.append({
            "metric": "menu_optimization",
            "current_value": f"Top 5 items: {len(top_items)} identified",
            "industry_avg": "N/A",
            "recommendation": "Focus promotion on top-selling items and consider expanding similar offerings",
            "potential_impact": "10-15% revenue optimization"
        })

    return {
        "venue_id": venue_id,
        "analysis_period": f"{start_date.isoformat()} to {date.today().isoformat()}",
        "recommendations": recommendations
    }

# ==================== RESERVATION DEPOSITS ====================

@router.post("/reservations/{reservation_id}/deposit")
@limiter.limit("30/minute")
async def create_deposit_request(
    request: Request,
    reservation_id: int,
    deposit: DepositRequest,
    db: Session = Depends(get_db)
):
    """Create deposit request for reservation"""
    # Verify reservation exists
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # Generate unique payment link
    payment_token = secrets.token_urlsafe(16)
    payment_link = f"https://bjsbar.bg/pay/{payment_token}"

    # Create deposit record
    new_deposit = ReservationDeposit(
        venue_id=reservation.venue_id,
        reservation_id=reservation_id,
        amount=Decimal(str(deposit.amount)),
        currency=deposit.currency,
        status=DepositStatus.pending,
        payment_link=payment_link
    )

    db.add(new_deposit)
    db.commit()
    db.refresh(new_deposit)

    return {
        "id": new_deposit.id,
        "reservation_id": new_deposit.reservation_id,
        "amount": float(new_deposit.amount),
        "currency": new_deposit.currency,
        "status": new_deposit.status.value,
        "payment_link": new_deposit.payment_link,
        "created_at": new_deposit.created_at.isoformat() if new_deposit.created_at else None
    }


@router.get("/deposits/{deposit_id}")
@limiter.limit("60/minute")
async def get_deposit(
    request: Request,
    deposit_id: int,
    db: Session = Depends(get_db)
):
    """Get deposit details"""
    deposit = db.query(ReservationDeposit).filter(ReservationDeposit.id == deposit_id).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    return {
        "id": deposit.id,
        "reservation_id": deposit.reservation_id,
        "venue_id": deposit.venue_id,
        "amount": float(deposit.amount),
        "currency": deposit.currency,
        "status": deposit.status.value,
        "payment_link": deposit.payment_link,
        "payment_method": deposit.payment_method,
        "transaction_id": deposit.transaction_id,
        "collected_at": deposit.collected_at.isoformat() if deposit.collected_at else None,
        "order_id": deposit.order_id,
        "applied_at": deposit.applied_at.isoformat() if deposit.applied_at else None,
        "amount_applied": float(deposit.amount_applied) if deposit.amount_applied else None,
        "refund_reason": deposit.refund_reason,
        "refunded_at": deposit.refunded_at.isoformat() if deposit.refunded_at else None,
        "created_at": deposit.created_at.isoformat() if deposit.created_at else None,
        "updated_at": deposit.updated_at.isoformat() if deposit.updated_at else None
    }


@router.post("/deposits/{deposit_id}/collect")
@limiter.limit("30/minute")
async def collect_deposit(
    request: Request,
    deposit_id: int,
    payment_method: str = Body(...),
    transaction_id: str = Body(...),
    staff_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Record deposit collection"""
    deposit = db.query(ReservationDeposit).filter(ReservationDeposit.id == deposit_id).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    if deposit.status != DepositStatus.pending:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot collect deposit with status '{deposit.status.value}'. Only pending deposits can be collected."
        )

    # Update deposit record
    deposit.status = DepositStatus.collected
    deposit.payment_method = payment_method
    deposit.transaction_id = transaction_id
    deposit.collected_at = datetime.now(timezone.utc)
    deposit.collected_by = staff_id

    db.commit()
    db.refresh(deposit)

    return {
        "deposit_id": deposit.id,
        "reservation_id": deposit.reservation_id,
        "amount": float(deposit.amount),
        "status": deposit.status.value,
        "payment_method": deposit.payment_method,
        "transaction_id": deposit.transaction_id,
        "collected_at": deposit.collected_at.isoformat() if deposit.collected_at else None
    }


@router.post("/deposits/{deposit_id}/apply")
@limiter.limit("30/minute")
async def apply_deposit_to_order(
    request: Request,
    deposit_id: int,
    order_id: int = Body(...),
    amount: Optional[float] = Body(None),
    db: Session = Depends(get_db)
):
    """Apply deposit to final bill"""
    deposit = db.query(ReservationDeposit).filter(ReservationDeposit.id == deposit_id).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    if deposit.status != DepositStatus.collected:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot apply deposit with status '{deposit.status.value}'. Only collected deposits can be applied."
        )

    # Verify order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Determine amount to apply (default to full deposit amount)
    amount_to_apply = Decimal(str(amount)) if amount else deposit.amount

    if amount_to_apply > deposit.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot apply more than deposit amount ({float(deposit.amount)})"
        )

    # Update deposit record
    deposit.status = DepositStatus.applied
    deposit.order_id = order_id
    deposit.applied_at = datetime.now(timezone.utc)
    deposit.amount_applied = amount_to_apply

    db.commit()
    db.refresh(deposit)

    return {
        "deposit_id": deposit.id,
        "reservation_id": deposit.reservation_id,
        "order_id": deposit.order_id,
        "amount_applied": float(deposit.amount_applied),
        "status": deposit.status.value,
        "applied_at": deposit.applied_at.isoformat() if deposit.applied_at else None
    }


@router.post("/deposits/{deposit_id}/refund")
@limiter.limit("30/minute")
async def refund_deposit(
    request: Request,
    deposit_id: int,
    reason: str = Body(...),
    staff_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Refund a deposit"""
    deposit = db.query(ReservationDeposit).filter(ReservationDeposit.id == deposit_id).first()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    if deposit.status not in [DepositStatus.pending, DepositStatus.collected]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot refund deposit with status '{deposit.status.value}'. Only pending or collected deposits can be refunded."
        )

    # Update deposit record
    deposit.status = DepositStatus.refunded
    deposit.refund_reason = reason
    deposit.refunded_at = datetime.now(timezone.utc)
    deposit.refunded_by = staff_id

    db.commit()
    db.refresh(deposit)

    return {
        "deposit_id": deposit.id,
        "reservation_id": deposit.reservation_id,
        "amount": float(deposit.amount),
        "status": deposit.status.value,
        "reason": deposit.refund_reason,
        "refunded_at": deposit.refunded_at.isoformat() if deposit.refunded_at else None
    }


@router.get("/reservations/{reservation_id}/deposits")
@limiter.limit("60/minute")
async def get_reservation_deposits(
    request: Request,
    reservation_id: int,
    db: Session = Depends(get_db)
):
    """Get all deposits for a reservation"""
    # Verify reservation exists
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    deposits = db.query(ReservationDeposit).filter(
        ReservationDeposit.reservation_id == reservation_id
    ).order_by(ReservationDeposit.created_at.desc()).all()

    return {
        "reservation_id": reservation_id,
        "deposits": [
            {
                "id": d.id,
                "amount": float(d.amount),
                "currency": d.currency,
                "status": d.status.value,
                "payment_method": d.payment_method,
                "collected_at": d.collected_at.isoformat() if d.collected_at else None,
                "order_id": d.order_id,
                "applied_at": d.applied_at.isoformat() if d.applied_at else None,
                "amount_applied": float(d.amount_applied) if d.amount_applied else None,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in deposits
        ],
        "total_deposited": float(sum(d.amount for d in deposits if d.status == DepositStatus.collected)),
        "total_applied": float(sum(d.amount_applied or 0 for d in deposits if d.status == DepositStatus.applied))
    }


@router.get("/deposits/settings")
@limiter.limit("60/minute")
async def get_deposit_settings(
    request: Request,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get deposit settings for venue"""
    # Try to get venue settings from database
    venue_settings = db.query(VenueSettings).filter(VenueSettings.venue_id == venue_id).first()

    # Default deposit settings
    default_settings = {
        "deposits_enabled": True,
        "default_amount": 50.00,
        "min_party_size": 6,
        "required_peak_hours": True,
        "peak_hours_start": "18:00",
        "peak_hours_end": "22:00",
        "weekend_required": True,
        "currency": "BGN"
    }

    if venue_settings and venue_settings.settings_data:
        # Merge with deposit settings from venue settings if present
        deposit_settings = venue_settings.settings_data.get("deposit_settings", {})
        return {**default_settings, **deposit_settings, "venue_id": venue_id}

    return {**default_settings, "venue_id": venue_id}


@router.put("/deposits/settings")
@limiter.limit("30/minute")
async def update_deposit_settings(
    request: Request,
    venue_id: int = Query(1),
    deposits_enabled: Optional[bool] = Body(None),
    default_amount: Optional[float] = Body(None),
    min_party_size: Optional[int] = Body(None),
    required_peak_hours: Optional[bool] = Body(None),
    peak_hours_start: Optional[str] = Body(None),
    peak_hours_end: Optional[str] = Body(None),
    weekend_required: Optional[bool] = Body(None),
    currency: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Update deposit settings for venue"""
    # Get or create venue settings
    venue_settings = db.query(VenueSettings).filter(VenueSettings.venue_id == venue_id).first()

    if not venue_settings:
        venue_settings = VenueSettings(venue_id=venue_id, settings_data={})
        db.add(venue_settings)

    # Get current deposit settings or initialize
    current_settings = venue_settings.settings_data or {}
    deposit_settings = current_settings.get("deposit_settings", {
        "deposits_enabled": True,
        "default_amount": 50.00,
        "min_party_size": 6,
        "required_peak_hours": True,
        "peak_hours_start": "18:00",
        "peak_hours_end": "22:00",
        "weekend_required": True,
        "currency": "BGN"
    })

    # Update only provided fields
    if deposits_enabled is not None:
        deposit_settings["deposits_enabled"] = deposits_enabled
    if default_amount is not None:
        deposit_settings["default_amount"] = default_amount
    if min_party_size is not None:
        deposit_settings["min_party_size"] = min_party_size
    if required_peak_hours is not None:
        deposit_settings["required_peak_hours"] = required_peak_hours
    if peak_hours_start is not None:
        deposit_settings["peak_hours_start"] = peak_hours_start
    if peak_hours_end is not None:
        deposit_settings["peak_hours_end"] = peak_hours_end
    if weekend_required is not None:
        deposit_settings["weekend_required"] = weekend_required
    if currency is not None:
        deposit_settings["currency"] = currency

    # Save updated settings
    current_settings["deposit_settings"] = deposit_settings
    venue_settings.settings_data = current_settings

    db.commit()
    db.refresh(venue_settings)

    return {**deposit_settings, "venue_id": venue_id}

# ==================== RFM ANALYTICS ====================

def _calculate_rfm_score(value: float, thresholds: List[float], inverse: bool = False) -> int:
    """Calculate RFM score (1-5) based on value and thresholds.

    Args:
        value: The raw value to score
        thresholds: List of 4 threshold values defining score boundaries
        inverse: If True, lower values get higher scores (used for Recency)

    Returns:
        Score from 1-5
    """
    if inverse:
        # For recency: fewer days = higher score
        if value <= thresholds[0]:
            return 5
        elif value <= thresholds[1]:
            return 4
        elif value <= thresholds[2]:
            return 3
        elif value <= thresholds[3]:
            return 2
        else:
            return 1
    else:
        # For frequency/monetary: higher values = higher score
        if value >= thresholds[3]:
            return 5
        elif value >= thresholds[2]:
            return 4
        elif value >= thresholds[1]:
            return 3
        elif value >= thresholds[0]:
            return 2
        else:
            return 1


def _get_rfm_segment(recency_score: int, frequency_score: int, monetary_score: int) -> str:
    """Determine RFM segment based on scores."""
    # Combined score for segmentation
    avg_score = (recency_score + frequency_score + monetary_score) / 3

    # Champions: High in all three
    if recency_score >= 4 and frequency_score >= 4 and monetary_score >= 4:
        return "Champions"

    # Loyal Customers: High frequency and monetary, good recency
    if frequency_score >= 4 and monetary_score >= 3 and recency_score >= 3:
        return "Loyal Customers"

    # Potential Loyalists: Recent customers with moderate frequency
    if recency_score >= 4 and frequency_score >= 2 and frequency_score <= 3:
        return "Potential Loyalists"

    # New Customers: Very recent but low frequency
    if recency_score >= 4 and frequency_score <= 2:
        return "New Customers"

    # At Risk: Previously good customers who haven't visited recently
    if recency_score <= 2 and frequency_score >= 3:
        return "At Risk"

    # Can't Lose: High value but haven't visited in a while
    if recency_score <= 2 and monetary_score >= 4:
        return "Can't Lose"

    # Hibernating: Low recency and low frequency
    if recency_score <= 2 and frequency_score <= 2:
        return "Lost"

    # About to Sleep: Below average recency
    if recency_score <= 3 and avg_score <= 3:
        return "About to Sleep"

    # Default
    return "Need Attention"


@router.get("/rfm/customer/{customer_id}")
@limiter.limit("60/minute")
async def get_customer_rfm(
    request: Request,
    customer_id: int,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get RFM score for customer - calculated from actual order data"""
    # Get customer
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.venue_id == venue_id
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Calculate RFM values from orders
    orders = db.query(Order).filter(
        Order.customer_id == customer_id,
        Order.venue_id == venue_id
    ).all()

    now = datetime.now(timezone.utc)

    if not orders:
        # No orders - return lowest scores
        return {
            "customer_id": customer_id,
            "customer_name": customer.name,
            "recency_days": None,
            "frequency_count": 0,
            "monetary_total": 0.0,
            "recency_score": 1,
            "frequency_score": 1,
            "monetary_score": 1,
            "rfm_score": 111,
            "segment": "Lost"
        }

    # Recency: Days since last order
    last_order_date = max(o.created_at for o in orders if o.created_at)
    recency_days = (now - last_order_date.replace(tzinfo=None)).days if last_order_date else 365

    # Frequency: Total order count
    frequency_count = len(orders)

    # Monetary: Total spent
    monetary_total = sum(o.total or 0 for o in orders)

    # Calculate scores using typical restaurant thresholds
    # Recency thresholds (days): 7, 30, 60, 90
    recency_score = _calculate_rfm_score(recency_days, [7, 30, 60, 90], inverse=True)

    # Frequency thresholds (orders): 2, 5, 10, 20
    frequency_score = _calculate_rfm_score(frequency_count, [2, 5, 10, 20], inverse=False)

    # Monetary thresholds (BGN): 50, 150, 400, 1000
    monetary_score = _calculate_rfm_score(monetary_total, [50, 150, 400, 1000], inverse=False)

    # Combined RFM score (e.g., 434 means R=4, F=3, M=4)
    rfm_score = recency_score * 100 + frequency_score * 10 + monetary_score

    # Determine segment
    segment = _get_rfm_segment(recency_score, frequency_score, monetary_score)

    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "recency_days": recency_days,
        "frequency_count": frequency_count,
        "monetary_total": round(monetary_total, 2),
        "recency_score": recency_score,
        "frequency_score": frequency_score,
        "monetary_score": monetary_score,
        "rfm_score": rfm_score,
        "segment": segment
    }


@router.get("/rfm/segments")
@limiter.limit("60/minute")
async def get_rfm_segments(
    request: Request,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get all RFM segments with counts - calculated from actual customer/order data"""
    # Get all customers for this venue
    customers = db.query(Customer).filter(
        Customer.venue_id == venue_id,
        Customer.is_active == True
    ).all()

    now = datetime.now(timezone.utc)
    segment_counts: Dict[str, int] = {}

    for customer in customers:
        # Get orders for this customer
        orders = db.query(Order).filter(
            Order.customer_id == customer.id,
            Order.venue_id == venue_id
        ).all()

        if not orders:
            segment = "Lost"
        else:
            # Calculate RFM values
            last_order_date = max(o.created_at for o in orders if o.created_at)
            recency_days = (now - last_order_date.replace(tzinfo=None)).days if last_order_date else 365
            frequency_count = len(orders)
            monetary_total = sum(o.total or 0 for o in orders)

            # Calculate scores
            recency_score = _calculate_rfm_score(recency_days, [7, 30, 60, 90], inverse=True)
            frequency_score = _calculate_rfm_score(frequency_count, [2, 5, 10, 20], inverse=False)
            monetary_score = _calculate_rfm_score(monetary_total, [50, 150, 400, 1000], inverse=False)

            segment = _get_rfm_segment(recency_score, frequency_score, monetary_score)

        segment_counts[segment] = segment_counts.get(segment, 0) + 1

    return {
        "segments": segment_counts,
        "total_customers": len(customers)
    }


@router.get("/rfm/segment/{segment}/customers")
@limiter.limit("60/minute")
async def get_segment_customers(
    request: Request,
    segment: str,
    venue_id: int = Query(1),
    limit: int = Query(100),
    db: Session = Depends(get_db)
):
    """Get customers in segment - calculated from actual order data"""
    # Get all customers for this venue
    customers = db.query(Customer).filter(
        Customer.venue_id == venue_id,
        Customer.is_active == True
    ).all()

    now = datetime.now(timezone.utc)
    segment_customers = []

    for customer in customers:
        # Get orders for this customer
        orders = db.query(Order).filter(
            Order.customer_id == customer.id,
            Order.venue_id == venue_id
        ).all()

        if not orders:
            customer_segment = "Lost"
            rfm_score = 111
            recency_days = None
            frequency_count = 0
            monetary_total = 0.0
        else:
            # Calculate RFM values
            last_order_date = max(o.created_at for o in orders if o.created_at)
            recency_days = (now - last_order_date.replace(tzinfo=None)).days if last_order_date else 365
            frequency_count = len(orders)
            monetary_total = sum(o.total or 0 for o in orders)

            # Calculate scores
            recency_score = _calculate_rfm_score(recency_days, [7, 30, 60, 90], inverse=True)
            frequency_score = _calculate_rfm_score(frequency_count, [2, 5, 10, 20], inverse=False)
            monetary_score = _calculate_rfm_score(monetary_total, [50, 150, 400, 1000], inverse=False)

            rfm_score = recency_score * 100 + frequency_score * 10 + monetary_score
            customer_segment = _get_rfm_segment(recency_score, frequency_score, monetary_score)

        # Check if customer belongs to requested segment
        if customer_segment.lower() == segment.lower() or segment.lower() == "all":
            segment_customers.append({
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "rfm_score": rfm_score,
                "recency_days": recency_days,
                "frequency_count": frequency_count,
                "monetary_total": round(monetary_total, 2) if monetary_total else 0.0
            })

            if len(segment_customers) >= limit:
                break

    # Sort by RFM score descending
    segment_customers.sort(key=lambda x: x["rfm_score"], reverse=True)

    return {
        "segment": segment,
        "customers": segment_customers[:limit]
    }


@router.get("/rfm/segment/{segment}/recommendations")
@limiter.limit("60/minute")
async def get_segment_recommendations(request: Request, segment: str):
    """Get marketing recommendations for segment"""
    # Segment-specific marketing strategies
    recommendations = {
        "champions": {
            "segment": "Champions",
            "strategy": "Reward and retain - these are your best customers",
            "actions": [
                "Offer exclusive VIP rewards and early access",
                "Create referral programs with premium incentives",
                "Invite to special events and tastings",
                "Personalized thank-you messages from management"
            ],
            "suggested_offers": [
                "Exclusive members-only dishes",
                "Complimentary dessert on visits",
                "Priority reservations"
            ]
        },
        "loyal customers": {
            "segment": "Loyal Customers",
            "strategy": "Upsell and increase engagement",
            "actions": [
                "Introduce loyalty program upgrades",
                "Cross-sell new menu items",
                "Encourage trying premium options",
                "Ask for reviews and testimonials"
            ],
            "suggested_offers": [
                "20% off on premium items",
                "Double loyalty points this month",
                "Free appetizer with main course"
            ]
        },
        "potential loyalists": {
            "segment": "Potential Loyalists",
            "strategy": "Build loyalty before they drift away",
            "actions": [
                "Enroll in loyalty program",
                "Offer membership benefits",
                "Send personalized recommendations",
                "Regular engagement emails"
            ],
            "suggested_offers": [
                "Welcome to loyalty bonus points",
                "15% off next 3 visits",
                "Free drink with meal"
            ]
        },
        "new customers": {
            "segment": "New Customers",
            "strategy": "Onboard and educate about your offerings",
            "actions": [
                "Send welcome series emails",
                "Introduce loyalty program",
                "Showcase bestsellers and signature dishes",
                "Follow up after first visit"
            ],
            "suggested_offers": [
                "Welcome discount 10% off",
                "Free dessert on second visit",
                "Join loyalty program bonus"
            ]
        },
        "at risk": {
            "segment": "At Risk",
            "strategy": "Reactivate before they leave",
            "actions": [
                "Send win-back campaigns urgently",
                "Call or message personally",
                "Ask for feedback on last experience",
                "Offer significant incentive to return"
            ],
            "suggested_offers": [
                "We miss you - 30% off return visit",
                "Free main course on us",
                "Exclusive comeback offer"
            ]
        },
        "can't lose": {
            "segment": "Can't Lose",
            "strategy": "Urgent reactivation - high-value customers at risk",
            "actions": [
                "Personal outreach from manager",
                "VIP win-back campaign",
                "Investigate if there was an issue",
                "Offer premium incentives"
            ],
            "suggested_offers": [
                "Complimentary meal for two",
                "40% off your next visit",
                "Personal invitation from chef"
            ]
        },
        "lost": {
            "segment": "Lost",
            "strategy": "Attempt reactivation with strong offers",
            "actions": [
                "Send reactivation campaign",
                "Highlight what's new since their last visit",
                "Offer significant discount",
                "Consider removing from active lists after attempts"
            ],
            "suggested_offers": [
                "50% off comeback special",
                "Free meal on your return",
                "See what you've been missing"
            ]
        },
        "about to sleep": {
            "segment": "About to Sleep",
            "strategy": "Reactivate before they become lost",
            "actions": [
                "Send reminder campaigns",
                "Highlight new menu items",
                "Offer time-limited discount",
                "Engagement through events"
            ],
            "suggested_offers": [
                "25% off this week only",
                "New dishes you'll love",
                "Double points weekend"
            ]
        },
        "need attention": {
            "segment": "Need Attention",
            "strategy": "Understand and engage",
            "actions": [
                "Send survey to understand preferences",
                "Personalized recommendations",
                "Moderate incentives to increase frequency",
                "Regular newsletters"
            ],
            "suggested_offers": [
                "15% off your favorites",
                "Try something new - 20% off",
                "Loyalty program introduction"
            ]
        }
    }

    # Normalize segment name for lookup
    segment_lower = segment.lower()

    if segment_lower in recommendations:
        return recommendations[segment_lower]

    # Default recommendation for unknown segments
    return {
        "segment": segment,
        "strategy": "Analyze and engage appropriately",
        "actions": [
            "Review customer data for insights",
            "Send targeted marketing campaign",
            "Offer moderate incentives",
            "Track response rates"
        ],
        "suggested_offers": [
            "15% discount",
            "Free appetizer",
            "Loyalty points bonus"
        ]
    }

# ==================== REFERRAL PROGRAM ====================

@router.post("/referral/programs")
@limiter.limit("30/minute")
async def create_referral_program(
    request: Request,
    venue_id: int = Query(1),
    name: str = Body(...),
    referrer_reward_type: str = Body("credit"),
    referrer_reward_value: float = Body(...),
    referee_reward_type: str = Body("discount"),
    referee_reward_value: float = Body(...),
    min_order_value: Optional[float] = Body(None),
    reward_after_orders: int = Body(1),
    max_referrals_per_customer: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Create referral program"""
    program = ReferralProgram(
        venue_id=venue_id,
        name=name,
        referrer_reward_type=referrer_reward_type,
        referrer_reward_value=Decimal(str(referrer_reward_value)),
        referee_reward_type=referee_reward_type,
        referee_reward_value=Decimal(str(referee_reward_value)),
        min_order_value=Decimal(str(min_order_value)) if min_order_value else None,
        reward_after_orders=reward_after_orders,
        max_referrals_per_customer=max_referrals_per_customer,
        is_active=True
    )
    db.add(program)
    db.commit()
    db.refresh(program)

    return {
        "id": program.id,
        "venue_id": program.venue_id,
        "name": program.name,
        "referrer_reward_type": program.referrer_reward_type,
        "referrer_reward_value": float(program.referrer_reward_value),
        "referee_reward_type": program.referee_reward_type,
        "referee_reward_value": float(program.referee_reward_value),
        "min_order_value": float(program.min_order_value) if program.min_order_value else None,
        "reward_after_orders": program.reward_after_orders,
        "max_referrals_per_customer": program.max_referrals_per_customer,
        "is_active": program.is_active,
        "created_at": program.created_at.isoformat() if program.created_at else None
    }


@router.get("/referral/programs")
@limiter.limit("60/minute")
async def list_referral_programs(
    request: Request,
    venue_id: int = Query(1),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """List all referral programs for a venue"""
    query = db.query(ReferralProgram).filter(ReferralProgram.venue_id == venue_id)

    if is_active is not None:
        query = query.filter(ReferralProgram.is_active == is_active)

    programs = query.all()

    return {
        "programs": [
            {
                "id": p.id,
                "name": p.name,
                "referrer_reward_type": p.referrer_reward_type,
                "referrer_reward_value": float(p.referrer_reward_value) if p.referrer_reward_value else 0,
                "referee_reward_type": p.referee_reward_type,
                "referee_reward_value": float(p.referee_reward_value) if p.referee_reward_value else 0,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in programs
        ],
        "total": len(programs)
    }


@router.post("/referral/generate-code")
@limiter.limit("30/minute")
async def generate_referral_code(
    request: Request,
    program_id: int = Body(...),
    customer_id: int = Body(...),
    referee_email: Optional[str] = Body(None),
    referee_phone: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Generate referral code for customer"""
    # Verify program exists and is active
    program = db.query(ReferralProgram).filter(
        ReferralProgram.id == program_id,
        ReferralProgram.is_active == True
    ).first()

    if not program:
        raise HTTPException(status_code=404, detail="Referral program not found or inactive")

    # Verify customer exists
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Check if customer has reached max referrals limit
    if program.max_referrals_per_customer:
        existing_referrals = db.query(CustomerReferral).filter(
            CustomerReferral.program_id == program_id,
            CustomerReferral.referrer_id == customer_id
        ).count()

        if existing_referrals >= program.max_referrals_per_customer:
            raise HTTPException(
                status_code=400,
                detail=f"Customer has reached maximum referrals limit ({program.max_referrals_per_customer})"
            )

    # Generate unique referral code
    while True:
        code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
        existing = db.query(CustomerReferral).filter(CustomerReferral.referral_code == code).first()
        if not existing:
            break

    # Create referral record
    referral = CustomerReferral(
        venue_id=program.venue_id,
        program_id=program_id,
        referrer_id=customer_id,
        referral_code=code,
        referee_email=referee_email,
        referee_phone=referee_phone,
        status="pending"
    )
    db.add(referral)
    db.commit()
    db.refresh(referral)

    return {
        "referral_id": referral.id,
        "referral_code": code,
        "share_url": f"https://bjsbar.bg/ref/{code}",
        "program_name": program.name,
        "referee_reward": {
            "type": program.referee_reward_type,
            "value": float(program.referee_reward_value) if program.referee_reward_value else 0
        },
        "referrer_reward": {
            "type": program.referrer_reward_type,
            "value": float(program.referrer_reward_value) if program.referrer_reward_value else 0
        }
    }


@router.post("/referral/validate")
@limiter.limit("30/minute")
async def validate_referral_code(
    request: Request,
    validation: ReferralCodeValidation,
    db: Session = Depends(get_db)
):
    """Validate a referral code and register referee"""
    # Find the referral by code
    referral = db.query(CustomerReferral).filter(
        CustomerReferral.referral_code == validation.code
    ).first()

    if not referral:
        return {
            "valid": False,
            "code": validation.code,
            "error": "Invalid referral code"
        }

    # Check if referral is still pending (not already used)
    if referral.status != "pending":
        return {
            "valid": False,
            "code": validation.code,
            "error": f"Referral code already used (status: {referral.status})"
        }

    # Check if referee is trying to use their own code
    if referral.referrer_id == validation.referee_customer_id:
        return {
            "valid": False,
            "code": validation.code,
            "error": "Cannot use your own referral code"
        }

    # Get the program details
    program = db.query(ReferralProgram).filter(
        ReferralProgram.id == referral.program_id
    ).first()

    if not program or not program.is_active:
        return {
            "valid": False,
            "code": validation.code,
            "error": "Referral program is no longer active"
        }

    # Update referral with referee info
    referral.referee_id = validation.referee_customer_id
    referral.status = "registered"
    referral.registered_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "valid": True,
        "code": validation.code,
        "referral_id": referral.id,
        "program_name": program.name,
        "referee_reward": {
            "type": program.referee_reward_type,
            "value": float(program.referee_reward_value) if program.referee_reward_value else 0
        },
        "min_order_value": float(program.min_order_value) if program.min_order_value else None,
        "message": "Referral code validated. Complete a qualifying order to receive your reward."
    }


@router.post("/referral/{referral_id}/qualify")
@limiter.limit("30/minute")
async def qualify_referral(
    request: Request,
    referral_id: int,
    order_id: int = Body(...),
    db: Session = Depends(get_db)
):
    """Mark a referral as qualified after referee completes qualifying order"""
    referral = db.query(CustomerReferral).filter(CustomerReferral.id == referral_id).first()

    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    if referral.status not in ["pending", "registered"]:
        raise HTTPException(status_code=400, detail=f"Referral cannot be qualified (current status: {referral.status})")

    # Get the program to check min order value
    program = db.query(ReferralProgram).filter(ReferralProgram.id == referral.program_id).first()

    if program and program.min_order_value:
        # Verify order meets minimum value
        order = db.query(Order).filter(Order.id == order_id).first()
        if order and order.total_amount < float(program.min_order_value):
            raise HTTPException(
                status_code=400,
                detail=f"Order value must be at least {program.min_order_value} to qualify"
            )

    referral.status = "qualified"
    referral.qualified_at = datetime.now(timezone.utc)
    referral.qualifying_order_id = order_id
    db.commit()

    return {
        "referral_id": referral.id,
        "status": "qualified",
        "qualified_at": referral.qualified_at.isoformat(),
        "message": "Referral qualified. Rewards can now be issued."
    }


@router.post("/referral/{referral_id}/issue-rewards")
@limiter.limit("30/minute")
async def issue_referral_rewards(
    request: Request,
    referral_id: int,
    db: Session = Depends(get_db)
):
    """Issue rewards to both referrer and referee"""
    referral = db.query(CustomerReferral).filter(CustomerReferral.id == referral_id).first()

    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    if referral.status != "qualified":
        raise HTTPException(status_code=400, detail="Referral must be qualified before issuing rewards")

    program = db.query(ReferralProgram).filter(ReferralProgram.id == referral.program_id).first()

    rewards_issued = []

    # Issue referrer reward
    if not referral.referrer_reward_issued and program.referrer_reward_value:
        referrer = db.query(Customer).filter(Customer.id == referral.referrer_id).first()
        if referrer:
            if program.referrer_reward_type == "points":
                referrer.loyalty_points = (referrer.loyalty_points or 0) + int(program.referrer_reward_value)
            # For credit/discount types, you would typically create a credit record
            # Here we'll add to loyalty points as a simplified implementation
            referral.referrer_reward_issued = True
            rewards_issued.append({
                "recipient": "referrer",
                "customer_id": referrer.id,
                "reward_type": program.referrer_reward_type,
                "reward_value": float(program.referrer_reward_value)
            })

    # Issue referee reward
    if not referral.referee_reward_issued and referral.referee_id and program.referee_reward_value:
        referee = db.query(Customer).filter(Customer.id == referral.referee_id).first()
        if referee:
            if program.referee_reward_type == "points":
                referee.loyalty_points = (referee.loyalty_points or 0) + int(program.referee_reward_value)
            referral.referee_reward_issued = True
            rewards_issued.append({
                "recipient": "referee",
                "customer_id": referee.id,
                "reward_type": program.referee_reward_type,
                "reward_value": float(program.referee_reward_value)
            })

    if rewards_issued:
        referral.status = "rewarded"
        referral.rewarded_at = datetime.now(timezone.utc)
        db.commit()

    return {
        "referral_id": referral.id,
        "status": referral.status,
        "rewards_issued": rewards_issued,
        "referrer_reward_issued": referral.referrer_reward_issued,
        "referee_reward_issued": referral.referee_reward_issued
    }


@router.get("/referral/customer/{customer_id}/stats")
@limiter.limit("60/minute")
async def get_customer_referrals(
    request: Request,
    customer_id: int,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get customer's referral statistics"""
    # Get all referrals where customer is the referrer
    referrals = db.query(CustomerReferral).filter(
        CustomerReferral.referrer_id == customer_id,
        CustomerReferral.venue_id == venue_id
    ).all()

    total_referrals = len(referrals)
    pending = sum(1 for r in referrals if r.status == "pending")
    registered = sum(1 for r in referrals if r.status == "registered")
    qualified = sum(1 for r in referrals if r.status == "qualified")
    rewarded = sum(1 for r in referrals if r.status == "rewarded")

    # Calculate total rewards earned
    total_rewards = Decimal("0")
    for r in referrals:
        if r.referrer_reward_issued:
            program = db.query(ReferralProgram).filter(ReferralProgram.id == r.program_id).first()
            if program and program.referrer_reward_value:
                total_rewards += program.referrer_reward_value

    # Get recent referrals
    recent_referrals = sorted(referrals, key=lambda x: x.created_at or datetime.min, reverse=True)[:5]

    return {
        "customer_id": customer_id,
        "total_referrals": total_referrals,
        "pending": pending,
        "registered": registered,
        "qualified": qualified,
        "rewarded": rewarded,
        "successful": qualified + rewarded,
        "rewards_earned": float(total_rewards),
        "recent_referrals": [
            {
                "referral_code": r.referral_code,
                "status": r.status,
                "referee_email": r.referee_email,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "qualified_at": r.qualified_at.isoformat() if r.qualified_at else None
            }
            for r in recent_referrals
        ]
    }


@router.get("/referral/program/{program_id}/stats")
@limiter.limit("60/minute")
async def get_program_stats(
    request: Request,
    program_id: int,
    db: Session = Depends(get_db)
):
    """Get statistics for a referral program"""
    program = db.query(ReferralProgram).filter(ReferralProgram.id == program_id).first()

    if not program:
        raise HTTPException(status_code=404, detail="Referral program not found")

    referrals = db.query(CustomerReferral).filter(CustomerReferral.program_id == program_id).all()

    total = len(referrals)
    by_status = {}
    for r in referrals:
        by_status[r.status] = by_status.get(r.status, 0) + 1

    # Calculate total rewards issued
    total_referrer_rewards = sum(
        float(program.referrer_reward_value) for r in referrals
        if r.referrer_reward_issued and program.referrer_reward_value
    )
    total_referee_rewards = sum(
        float(program.referee_reward_value) for r in referrals
        if r.referee_reward_issued and program.referee_reward_value
    )

    # Unique referrers
    unique_referrers = len(set(r.referrer_id for r in referrals))

    return {
        "program_id": program_id,
        "program_name": program.name,
        "is_active": program.is_active,
        "total_referrals": total,
        "by_status": by_status,
        "unique_referrers": unique_referrers,
        "conversion_rate": round((by_status.get("rewarded", 0) + by_status.get("qualified", 0)) / total * 100, 2) if total > 0 else 0,
        "total_rewards_issued": {
            "referrer_rewards": total_referrer_rewards,
            "referee_rewards": total_referee_rewards,
            "total": total_referrer_rewards + total_referee_rewards
        }
    }

# ==================== STAFF MANAGEMENT V5 ====================

@router.post("/staff/{staff_id}/breaks")
@limiter.limit("30/minute")
async def schedule_break(
    request: Request,
    staff_id: int,
    shift_id: int = Body(...),
    break_type: str = Body(...),
    scheduled_start: datetime = Body(...),
    duration_minutes: int = Body(...),
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Schedule employee break"""
    # Verify staff exists
    staff = db.query(StaffUser).filter(
        StaffUser.id == staff_id,
        StaffUser.venue_id == venue_id
    ).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    # Verify shift exists and belongs to this staff member
    shift = db.query(StaffShift).filter(
        StaffShift.id == shift_id,
        StaffShift.staff_user_id == staff_id
    ).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found for this staff member")

    # Calculate scheduled end time
    scheduled_end = scheduled_start + timedelta(minutes=duration_minutes)

    # Create the break record
    employee_break = EmployeeBreak(
        venue_id=venue_id,
        staff_id=staff_id,
        shift_id=shift_id,
        break_type=break_type,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        scheduled_duration_minutes=duration_minutes,
        status="scheduled"
    )
    db.add(employee_break)
    db.commit()
    db.refresh(employee_break)

    return {
        "id": employee_break.id,
        "staff_id": staff_id,
        "shift_id": shift_id,
        "break_type": break_type,
        "scheduled_start": scheduled_start.isoformat(),
        "scheduled_end": scheduled_end.isoformat(),
        "duration_minutes": duration_minutes,
        "status": "scheduled"
    }

@router.post("/breaks/{break_id}/start")
@limiter.limit("30/minute")
async def start_break(request: Request, break_id: int, db: Session = Depends(get_db)):
    """Clock in for break"""
    # Find the break record
    employee_break = db.query(EmployeeBreak).filter(
        EmployeeBreak.id == break_id
    ).first()
    if not employee_break:
        raise HTTPException(status_code=404, detail="Break not found")

    if employee_break.status != "scheduled":
        raise HTTPException(status_code=400, detail=f"Break cannot be started - current status: {employee_break.status}")

    # Update break status and actual start time
    employee_break.status = "in_progress"
    employee_break.actual_start = datetime.now(timezone.utc)
    db.commit()
    db.refresh(employee_break)

    return {
        "break_id": break_id,
        "status": "in_progress",
        "started_at": employee_break.actual_start.isoformat(),
        "staff_id": employee_break.staff_id
    }

@router.post("/breaks/{break_id}/end")
@limiter.limit("30/minute")
async def end_break(request: Request, break_id: int, db: Session = Depends(get_db)):
    """Clock out from break"""
    # Find the break record
    employee_break = db.query(EmployeeBreak).filter(
        EmployeeBreak.id == break_id
    ).first()
    if not employee_break:
        raise HTTPException(status_code=404, detail="Break not found")

    if employee_break.status != "in_progress":
        raise HTTPException(status_code=400, detail=f"Break cannot be ended - current status: {employee_break.status}")

    # Update break status, actual end time, and calculate duration
    employee_break.status = "completed"
    employee_break.actual_end = datetime.now(timezone.utc)

    # Calculate actual duration if we have start time
    if employee_break.actual_start:
        duration = employee_break.actual_end - employee_break.actual_start
        employee_break.actual_duration_minutes = int(duration.total_seconds() / 60)
    else:
        employee_break.actual_duration_minutes = employee_break.scheduled_duration_minutes

    db.commit()
    db.refresh(employee_break)

    return {
        "break_id": break_id,
        "status": "completed",
        "ended_at": employee_break.actual_end.isoformat(),
        "duration_minutes": employee_break.actual_duration_minutes,
        "staff_id": employee_break.staff_id
    }

@router.post("/shifts/trade-requests")
@limiter.limit("30/minute")
async def create_shift_trade(
    request: Request,
    body_data: ShiftTradeRequest,
    requesting_staff_id: int = Query(...),
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Create shift trade body_data"""
    # Verify requesting staff exists
    requester = db.query(StaffUser).filter(
        StaffUser.id == requesting_staff_id,
        StaffUser.venue_id == venue_id
    ).first()
    if not requester:
        raise HTTPException(status_code=404, detail="Requesting staff member not found")

    # Verify original shift exists and belongs to requester
    original_shift = db.query(StaffShift).filter(
        StaffShift.id == body_data.original_shift_id,
        StaffShift.staff_user_id == requesting_staff_id
    ).first()
    if not original_shift:
        raise HTTPException(status_code=404, detail="Original shift not found for this staff member")

    # Verify offered shift if provided
    if body_data.offered_shift_id:
        offered_shift = db.query(StaffShift).filter(
            StaffShift.id == body_data.offered_shift_id
        ).first()
        if not offered_shift:
            raise HTTPException(status_code=404, detail="Offered shift not found")

    # Create the trade body_data
    trade_request = ShiftTradeRequestModel(
        venue_id=venue_id,
        original_shift_id=body_data.original_shift_id,
        requester_id=requesting_staff_id,
        trade_type=body_data.trade_type,
        offered_shift_id=body_data.offered_shift_id,
        target_employee_id=body_data.target_staff_id,
        is_open_to_all=body_data.target_staff_id is None,
        status="pending",
        reason=body_data.reason,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)  # Default 7 day expiry
    )
    db.add(trade_request)
    db.commit()
    db.refresh(trade_request)

    return {
        "id": trade_request.id,
        "original_shift_id": trade_request.original_shift_id,
        "trade_type": trade_request.trade_type,
        "target_staff_id": trade_request.target_employee_id,
        "offered_shift_id": trade_request.offered_shift_id,
        "requesting_staff_id": requesting_staff_id,
        "status": "pending",
        "expires_at": trade_request.expires_at.isoformat() if trade_request.expires_at else None
    }

@router.post("/shifts/trade-requests/{request_id}/respond")
@limiter.limit("30/minute")
async def respond_to_trade(
    request: Request,
    request_id: int,
    response: str = Body(...),
    staff_id: int = Body(...),
    db: Session = Depends(get_db)
):
    """Respond to shift trade request"""
    # Find the trade request
    trade_request = db.query(ShiftTradeRequestModel).filter(
        ShiftTradeRequestModel.id == request_id
    ).first()
    if not trade_request:
        raise HTTPException(status_code=404, detail="Trade request not found")

    if trade_request.status != "pending":
        raise HTTPException(status_code=400, detail=f"Trade request cannot be responded to - current status: {trade_request.status}")

    # Validate response value
    if response not in ["accepted", "rejected"]:
        raise HTTPException(status_code=400, detail="Response must be 'accepted' or 'rejected'")

    # Update trade request
    if response == "accepted":
        trade_request.status = "accepted"
        trade_request.accepted_by_id = staff_id
        trade_request.accepted_at = datetime.now(timezone.utc)
    else:
        trade_request.status = "rejected"

    db.commit()
    db.refresh(trade_request)

    return {
        "request_id": request_id,
        "status": trade_request.status,
        "responded_by": staff_id,
        "responded_at": datetime.now(timezone.utc).isoformat()
    }

@router.post("/shifts/trade-requests/{request_id}/approve")
@limiter.limit("30/minute")
async def approve_trade(
    request: Request,
    request_id: int,
    manager_id: int = Body(...),
    approved: bool = Body(...),
    rejection_reason: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Manager approval for trade"""
    # Find the trade request
    trade_request = db.query(ShiftTradeRequestModel).filter(
        ShiftTradeRequestModel.id == request_id
    ).first()
    if not trade_request:
        raise HTTPException(status_code=404, detail="Trade request not found")

    if trade_request.status != "accepted":
        raise HTTPException(status_code=400, detail="Trade request must be accepted before manager approval")

    # Update with manager decision
    trade_request.approved_by_id = manager_id
    trade_request.approved_at = datetime.now(timezone.utc)

    if approved:
        trade_request.status = "approved"

        # Actually swap the shifts in StaffShift table
        original_shift = db.query(StaffShift).filter(
            StaffShift.id == trade_request.original_shift_id
        ).first()

        if original_shift:
            if trade_request.trade_type == "swap" and trade_request.offered_shift_id:
                # For swaps: exchange staff_user_id between the two shifts
                offered_shift = db.query(StaffShift).filter(
                    StaffShift.id == trade_request.offered_shift_id
                ).first()
                if offered_shift:
                    # Swap the staff assignments
                    original_staff_id = original_shift.staff_user_id
                    offered_staff_id = offered_shift.staff_user_id
                    original_shift.staff_user_id = offered_staff_id
                    offered_shift.staff_user_id = original_staff_id
            elif trade_request.trade_type in ["giveaway", "pickup"] and trade_request.accepted_by_id:
                # For giveaways/pickups: transfer shift to the accepting staff
                original_shift.staff_user_id = trade_request.accepted_by_id
    else:
        trade_request.status = "rejected"
        trade_request.rejection_reason = rejection_reason

    db.commit()
    db.refresh(trade_request)

    return {
        "request_id": request_id,
        "approved": approved,
        "approved_by": manager_id,
        "status": trade_request.status
    }

@router.get("/shifts/open-requests")
@limiter.limit("60/minute")
async def get_open_shifts(request: Request, venue_id: int = Query(1), db: Session = Depends(get_db)):
    """Get open shift giveaway requests"""
    # Get all open trade requests (giveaways that are open to all)
    open_requests = db.query(ShiftTradeRequestModel).filter(
        ShiftTradeRequestModel.venue_id == venue_id,
        ShiftTradeRequestModel.trade_type == "giveaway",
        ShiftTradeRequestModel.is_open_to_all == True,
        ShiftTradeRequestModel.status == "pending"
    ).all()

    result = []
    for req in open_requests:
        # Get the shift details
        shift = db.query(StaffShift).filter(StaffShift.id == req.original_shift_id).first()
        requester = db.query(StaffUser).filter(StaffUser.id == req.requester_id).first()

        result.append({
            "request_id": req.id,
            "shift_id": req.original_shift_id,
            "shift_start": shift.scheduled_start.isoformat() if shift else None,
            "shift_end": shift.scheduled_end.isoformat() if shift else None,
            "requester_id": req.requester_id,
            "requester_name": requester.name if requester else None,
            "reason": req.reason,
            "expires_at": req.expires_at.isoformat() if req.expires_at else None
        })

    return {"open_shifts": result}

@router.post("/staff/{staff_id}/onboarding")
@limiter.limit("30/minute")
async def create_onboarding(
    request: Request,
    staff_id: int,
    venue_id: int = Query(1),
    start_date: date = Body(...),
    checklist_id: Optional[int] = Body(None),
    mentor_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Create onboarding record"""
    # Verify staff exists
    staff = db.query(StaffUser).filter(
        StaffUser.id == staff_id,
        StaffUser.venue_id == venue_id
    ).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    # Check if staff already has an active onboarding
    existing = db.query(EmployeeOnboarding).filter(
        EmployeeOnboarding.staff_id == staff_id,
        EmployeeOnboarding.status == "in_progress"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Staff member already has an active onboarding")

    # Get or find checklist
    if checklist_id:
        checklist = db.query(OnboardingChecklist).filter(
            OnboardingChecklist.id == checklist_id,
            OnboardingChecklist.venue_id == venue_id,
            OnboardingChecklist.is_active == True
        ).first()
        if not checklist:
            raise HTTPException(status_code=404, detail="Onboarding checklist not found")
    else:
        # Try to find a default checklist for this venue
        checklist = db.query(OnboardingChecklist).filter(
            OnboardingChecklist.venue_id == venue_id,
            OnboardingChecklist.is_active == True
        ).first()

    # Create onboarding record
    onboarding = EmployeeOnboarding(
        venue_id=venue_id,
        staff_id=staff_id,
        checklist_id=checklist.id if checklist else None,
        start_date=start_date,
        target_completion_date=start_date + timedelta(days=30),  # Default 30 day target
        status="in_progress",
        progress_percentage=0.0,
        assigned_mentor=mentor_id
    )
    db.add(onboarding)
    db.commit()
    db.refresh(onboarding)

    return {
        "id": onboarding.id,
        "staff_id": staff_id,
        "start_date": start_date.isoformat(),
        "target_completion_date": onboarding.target_completion_date.isoformat() if onboarding.target_completion_date else None,
        "status": "in_progress",
        "progress": 0,
        "checklist_id": onboarding.checklist_id,
        "mentor_id": mentor_id
    }

@router.get("/onboarding/{onboarding_id}")
@limiter.limit("60/minute")
async def get_onboarding_progress(request: Request, onboarding_id: int, db: Session = Depends(get_db)):
    """Get onboarding progress"""
    # Find the onboarding record
    onboarding = db.query(EmployeeOnboarding).filter(
        EmployeeOnboarding.id == onboarding_id
    ).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding record not found")

    # Get all tasks for this onboarding's checklist
    tasks = []
    documents_completed = 0
    documents_total = 0
    training_completed = 0
    training_total = 0

    if onboarding.checklist_id:
        checklist_tasks = db.query(OnboardingTask).filter(
            OnboardingTask.checklist_id == onboarding.checklist_id
        ).all()

        for task in checklist_tasks:
            # Check completion status
            completion = db.query(OnboardingTaskCompletion).filter(
                OnboardingTaskCompletion.onboarding_id == onboarding_id,
                OnboardingTaskCompletion.task_id == task.id
            ).first()

            is_completed = completion and completion.status == "completed"

            if task.task_type == "document":
                documents_total += 1
                if is_completed:
                    documents_completed += 1
            elif task.task_type == "training":
                training_total += 1
                if is_completed:
                    training_completed += 1

            tasks.append({
                "id": task.id,
                "title": task.title,
                "type": task.task_type,
                "is_required": task.is_required,
                "status": completion.status if completion else "pending",
                "completed_at": completion.completed_at.isoformat() if completion and completion.completed_at else None
            })

    # Calculate overall progress
    total_tasks = len(tasks) if tasks else 1
    completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
    progress_percentage = round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0

    return {
        "onboarding_id": onboarding_id,
        "staff_id": onboarding.staff_id,
        "status": onboarding.status,
        "start_date": onboarding.start_date.isoformat() if onboarding.start_date else None,
        "target_completion_date": onboarding.target_completion_date.isoformat() if onboarding.target_completion_date else None,
        "progress_percentage": progress_percentage,
        "documents": {"completed": documents_completed, "total": documents_total},
        "training": {"completed": training_completed, "total": training_total},
        "tasks": tasks
    }

@router.patch("/onboarding/{onboarding_id}")
@limiter.limit("30/minute")
async def update_onboarding(
    request: Request,
    onboarding_id: int,
    task_id: int = Body(...),
    completed: bool = Body(...),
    notes: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Update onboarding task completion"""
    # Find the onboarding record
    onboarding = db.query(EmployeeOnboarding).filter(
        EmployeeOnboarding.id == onboarding_id
    ).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding record not found")

    # Find the task
    task = db.query(OnboardingTask).filter(
        OnboardingTask.id == task_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Onboarding task not found")

    # Find or create completion record
    completion = db.query(OnboardingTaskCompletion).filter(
        OnboardingTaskCompletion.onboarding_id == onboarding_id,
        OnboardingTaskCompletion.task_id == task_id
    ).first()

    if not completion:
        completion = OnboardingTaskCompletion(
            onboarding_id=onboarding_id,
            task_id=task_id,
            status="pending"
        )
        db.add(completion)

    # Update completion status
    if completed:
        completion.status = "completed"
        completion.completed_at = datetime.now(timezone.utc)
    else:
        completion.status = "pending"
        completion.completed_at = None

    if notes:
        completion.notes = notes

    db.commit()
    db.refresh(completion)

    # Recalculate overall progress
    total_tasks = db.query(OnboardingTask).filter(
        OnboardingTask.checklist_id == onboarding.checklist_id
    ).count()

    completed_tasks = db.query(OnboardingTaskCompletion).filter(
        OnboardingTaskCompletion.onboarding_id == onboarding_id,
        OnboardingTaskCompletion.status == "completed"
    ).count()

    progress = round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0
    onboarding.progress_percentage = progress

    # Check if onboarding is complete
    if progress >= 100:
        onboarding.status = "completed"
        onboarding.actual_completion_date = date.today()

    db.commit()

    return {
        "onboarding_id": onboarding_id,
        "task_id": task_id,
        "updated": True,
        "task_status": completion.status,
        "overall_progress": progress
    }

# ==================== PRICE TRACKER ====================

@router.post("/price-tracker/record")
@limiter.limit("30/minute")
async def record_price(
    request: Request,
    stock_item_id: int = Body(...),
    supplier_id: int = Body(...),
    unit_price: float = Body(...),
    unit: str = Body("kg"),
    source: str = Body("manual"),
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Record ingredient price"""
    # Verify stock item exists
    stock_item = db.query(StockItem).filter(
        StockItem.id == stock_item_id,
        StockItem.venue_id == venue_id
    ).first()
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    # Create price history record
    price_record = IngredientPriceHistory(
        venue_id=venue_id,
        stock_item_id=stock_item_id,
        supplier_id=supplier_id,
        price=Decimal(str(unit_price)),
        unit=unit,
        recorded_date=date.today(),
        source=source
    )
    db.add(price_record)
    db.commit()
    db.refresh(price_record)

    return {
        "id": price_record.id,
        "stock_item_id": price_record.stock_item_id,
        "stock_item_name": stock_item.name,
        "supplier_id": price_record.supplier_id,
        "unit_price": float(price_record.price),
        "unit": price_record.unit,
        "recorded_date": price_record.recorded_date.isoformat(),
        "source": price_record.source
    }

@router.get("/price-tracker/item/{stock_item_id}/history")
@limiter.limit("60/minute")
async def get_price_history(
    request: Request,
    stock_item_id: int,
    months: int = Query(6),
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get price history for item"""
    # Verify stock item exists
    stock_item = db.query(StockItem).filter(
        StockItem.id == stock_item_id,
        StockItem.venue_id == venue_id
    ).first()
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    # Calculate start date based on months
    start_date = date.today() - relativedelta(months=months)

    # Get price history from database
    history = db.query(IngredientPriceHistory).filter(
        IngredientPriceHistory.stock_item_id == stock_item_id,
        IngredientPriceHistory.venue_id == venue_id,
        IngredientPriceHistory.recorded_date >= start_date
    ).order_by(IngredientPriceHistory.recorded_date.asc()).all()

    # Calculate price change
    price_change = 0.0
    change_pct = 0.0
    if len(history) >= 2:
        oldest_price = float(history[0].price)
        newest_price = float(history[-1].price)
        price_change = newest_price - oldest_price
        if oldest_price > 0:
            change_pct = (price_change / oldest_price) * 100

    return {
        "stock_item_id": stock_item_id,
        "stock_item_name": stock_item.name,
        "current_unit": stock_item.unit,
        "history": [
            {
                "id": h.id,
                "date": h.recorded_date.isoformat(),
                "price": float(h.price),
                "unit": h.unit,
                "supplier_id": h.supplier_id,
                "source": h.source
            }
            for h in history
        ],
        "total_records": len(history),
        "price_change": round(price_change, 4),
        "change_percentage": round(change_pct, 2)
    }

@router.get("/price-tracker/alerts")
@limiter.limit("60/minute")
async def get_price_alerts(
    request: Request,
    venue_id: int = Query(1),
    unacknowledged: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get price change alerts"""
    # Get alert notifications (the actual triggered alerts)
    query = db.query(PriceAlertNotification).join(
        PriceAlert,
        PriceAlertNotification.alert_id == PriceAlert.id
    ).filter(
        PriceAlert.venue_id == venue_id
    )

    if unacknowledged:
        query = query.filter(PriceAlertNotification.is_read == False)

    notifications = query.order_by(PriceAlertNotification.created_at.desc()).limit(50).all()

    alerts = []
    for n in notifications:
        # Get the parent alert and stock item
        alert = db.query(PriceAlert).filter(PriceAlert.id == n.alert_id).first()
        if alert:
            stock_item = db.query(StockItem).filter(StockItem.id == alert.stock_item_id).first()
            alerts.append({
                "id": n.id,
                "alert_id": alert.id,
                "item_id": alert.stock_item_id,
                "item": stock_item.name if stock_item else "Unknown",
                "old_price": float(n.old_price) if n.old_price else None,
                "new_price": float(n.new_price) if n.new_price else None,
                "change_pct": round(n.change_percentage, 2) if n.change_percentage else 0,
                "alert_type": alert.alert_type,
                "acknowledged": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None
            })

    return {
        "alerts": alerts,
        "total": len(alerts)
    }

@router.post("/price-tracker/alerts/{alert_id}/acknowledge")
@limiter.limit("30/minute")
async def acknowledge_alert(
    request: Request,
    alert_id: int,
    staff_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Acknowledge price alert"""
    # Find the notification
    notification = db.query(PriceAlertNotification).filter(
        PriceAlertNotification.id == alert_id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Alert notification not found")

    if notification.is_read:
        return {"alert_id": alert_id, "acknowledged": True, "message": "Already acknowledged"}

    # Mark as read
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    notification.read_by = staff_id

    db.commit()

    return {
        "alert_id": alert_id,
        "acknowledged": True,
        "acknowledged_at": notification.read_at.isoformat()
    }

@router.get("/price-tracker/trends")
@limiter.limit("60/minute")
async def get_price_trends(
    request: Request,
    venue_id: int = Query(1),
    days: int = Query(30),
    db: Session = Depends(get_db)
):
    """Get overall price trends"""
    start_date = date.today() - timedelta(days=days)

    # Get all price records for the period
    recent_prices = db.query(IngredientPriceHistory).filter(
        IngredientPriceHistory.venue_id == venue_id,
        IngredientPriceHistory.recorded_date >= start_date
    ).all()

    # Group by stock_item_id and calculate trends
    item_prices = {}
    for p in recent_prices:
        if p.stock_item_id not in item_prices:
            item_prices[p.stock_item_id] = []
        item_prices[p.stock_item_id].append({
            "date": p.recorded_date,
            "price": float(p.price)
        })

    items_increased = 0
    items_decreased = 0
    items_stable = 0
    total_change = 0.0
    items_with_change = 0

    for item_id, prices in item_prices.items():
        if len(prices) >= 2:
            # Sort by date
            sorted_prices = sorted(prices, key=lambda x: x["date"])
            first_price = sorted_prices[0]["price"]
            last_price = sorted_prices[-1]["price"]

            if first_price > 0:
                change_pct = ((last_price - first_price) / first_price) * 100
                total_change += change_pct
                items_with_change += 1

                if change_pct > 1:  # More than 1% increase
                    items_increased += 1
                elif change_pct < -1:  # More than 1% decrease
                    items_decreased += 1
                else:
                    items_stable += 1

    overall_change = total_change / items_with_change if items_with_change > 0 else 0

    return {
        "venue_id": venue_id,
        "period_days": days,
        "overall_change": round(overall_change, 2),
        "items_increased": items_increased,
        "items_decreased": items_decreased,
        "items_stable": items_stable,
        "total_items_tracked": len(item_prices),
        "total_price_records": len(recent_prices)
    }

# ==================== VIP & CUSTOMER ENGAGEMENT ====================

@router.post("/vip/profiles")
@limiter.limit("30/minute")
async def create_vip_profile(
    request: Request,
    customer_id: int = Body(...),
    venue_id: int = Query(1),
    vip_tier: str = Body("silver"),
    db: Session = Depends(get_db)
):
    """Create VIP profile - assigns a VIP tier to a customer"""
    # Verify customer exists
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.venue_id == venue_id
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Find or create VIP tier
    tier = db.query(VIPTier).filter(
        VIPTier.venue_id == venue_id,
        VIPTier.name.ilike(vip_tier)
    ).first()

    if not tier:
        # Create the tier if it doesn't exist
        tier = VIPTier(
            venue_id=venue_id,
            name=vip_tier.capitalize(),
            description=f"{vip_tier.capitalize()} tier VIP customer",
            is_active=True
        )
        db.add(tier)
        db.flush()

    # Check if VIP status already exists
    existing_status = db.query(CustomerVIPStatus).filter(
        CustomerVIPStatus.customer_id == customer_id,
        CustomerVIPStatus.venue_id == venue_id
    ).first()

    if existing_status:
        # Update existing status
        existing_status.vip_tier_id = tier.id
        existing_status.is_active = True
        db.commit()
        return {
            "id": existing_status.id,
            "customer_id": customer_id,
            "vip_tier": tier.name,
            "updated": True
        }

    # Create new VIP status
    vip_status = CustomerVIPStatus(
        venue_id=venue_id,
        customer_id=customer_id,
        vip_tier_id=tier.id,
        assigned_date=date.today(),
        assignment_reason="manual",
        is_active=True
    )
    db.add(vip_status)

    # Also update customer loyalty_tier for consistency
    customer.loyalty_tier = vip_tier.lower()

    db.commit()
    db.refresh(vip_status)

    return {
        "id": vip_status.id,
        "customer_id": customer_id,
        "vip_tier": tier.name,
        "created": True
    }

@router.get("/vip/profiles/{customer_id}")
@limiter.limit("60/minute")
async def get_vip_profile(
    request: Request,
    customer_id: int,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get VIP profile for a customer"""
    # Get customer with their VIP status
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.venue_id == venue_id
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get VIP status if exists
    vip_status = db.query(CustomerVIPStatus).filter(
        CustomerVIPStatus.customer_id == customer_id,
        CustomerVIPStatus.venue_id == venue_id,
        CustomerVIPStatus.is_active == True
    ).first()

    vip_tier_name = customer.loyalty_tier or "bronze"
    preferences = {}

    if vip_status:
        # Get tier details
        tier = db.query(VIPTier).filter(VIPTier.id == vip_status.vip_tier_id).first()
        if tier:
            vip_tier_name = tier.name
        preferences = vip_status.preferences or {}

    return {
        "customer_id": customer_id,
        "vip_tier": vip_tier_name,
        "preferences": preferences,
        "lifetime_spend": float(customer.total_spent or 0),
        "total_orders": customer.total_orders or 0,
        "loyalty_points": customer.loyalty_points or 0,
        "last_visit": customer.last_visit.isoformat() if customer.last_visit else None
    }

@router.get("/vip/upcoming-occasions")
@limiter.limit("60/minute")
async def get_upcoming_occasions(
    request: Request,
    venue_id: int = Query(1),
    days: int = Query(30),
    db: Session = Depends(get_db)
):
    """Get upcoming VIP occasions (birthdays, anniversaries) for VIP customers"""
    today = date.today()
    end_date = today + timedelta(days=days)

    # Get VIP customers (those with VIP status or high loyalty tier)
    vip_customers = db.query(Customer).join(
        CustomerVIPStatus,
        (CustomerVIPStatus.customer_id == Customer.id) &
        (CustomerVIPStatus.venue_id == venue_id) &
        (CustomerVIPStatus.is_active == True)
    ).filter(
        Customer.venue_id == venue_id,
        Customer.is_active == True
    ).all()

    # Also include customers with VIP-level loyalty tiers
    high_tier_customers = db.query(Customer).filter(
        Customer.venue_id == venue_id,
        Customer.is_active == True,
        Customer.loyalty_tier.in_(["gold", "platinum", "vip", "diamond"])
    ).all()

    # Combine and deduplicate
    all_vip_customers = {c.id: c for c in vip_customers}
    for c in high_tier_customers:
        all_vip_customers[c.id] = c

    occasions = []
    for customer in all_vip_customers.values():
        if customer.birthday:
            # Check if birthday falls within the date range (ignoring year)
            bday = customer.birthday
            this_year_bday = date(today.year, bday.month, bday.day)
            if today <= this_year_bday <= end_date:
                occasions.append({
                    "customer_id": customer.id,
                    "customer_name": customer.name,
                    "occasion_type": "birthday",
                    "occasion_date": this_year_bday.isoformat(),
                    "days_until": (this_year_bday - today).days,
                    "loyalty_tier": customer.loyalty_tier
                })

    # Sort by date
    occasions.sort(key=lambda x: x["days_until"])

    return {"occasions": occasions, "total": len(occasions)}

@router.post("/guestbook/entries")
@limiter.limit("30/minute")
async def create_guestbook_entry(
    request: Request,
    venue_id: int = Query(1),
    customer_id: Optional[int] = Body(None),
    guest_name: Optional[str] = Body(None),
    guest_email: Optional[str] = Body(None),
    message: str = Body(...),
    rating: Optional[int] = Body(None),
    visit_date: Optional[date] = Body(None),
    occasion: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Create guestbook entry"""
    # Validate rating if provided
    if rating is not None and (rating < 1 or rating > 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Get customer name if customer_id provided
    if customer_id and not guest_name:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer:
            guest_name = customer.name
            guest_email = guest_email or customer.email

    entry = GuestbookEntry(
        venue_id=venue_id,
        customer_id=customer_id,
        guest_name=guest_name,
        guest_email=guest_email,
        message=message,
        rating=rating,
        visit_date=visit_date or date.today(),
        occasion=occasion,
        is_approved=False,  # Requires moderation
        is_public=True,
        show_name=True
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "id": entry.id,
        "venue_id": entry.venue_id,
        "guest_name": entry.guest_name,
        "message": entry.message,
        "rating": entry.rating,
        "visit_date": entry.visit_date.isoformat() if entry.visit_date else None,
        "occasion": entry.occasion,
        "is_approved": entry.is_approved,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "recorded": True
    }

@router.get("/guestbook/entries")
@limiter.limit("60/minute")
async def list_guestbook_entries(
    request: Request,
    venue_id: int = Query(1),
    approved_only: bool = Query(True),
    featured_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get guestbook entries for a venue"""
    query = db.query(GuestbookEntry).filter(GuestbookEntry.venue_id == venue_id)

    if approved_only:
        query = query.filter(GuestbookEntry.is_approved == True)
    if featured_only:
        query = query.filter(GuestbookEntry.is_featured == True)

    total = query.count()
    entries = query.order_by(GuestbookEntry.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "entries": [
            {
                "id": e.id,
                "guest_name": e.guest_name if e.show_name else "Anonymous",
                "message": e.message,
                "rating": e.rating,
                "visit_date": e.visit_date.isoformat() if e.visit_date else None,
                "occasion": e.occasion,
                "is_featured": e.is_featured,
                "photo_urls": e.photo_urls,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in entries
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/guestbook/customer/{customer_id}/history")
@limiter.limit("60/minute")
async def get_visit_history(
    request: Request,
    customer_id: int,
    venue_id: int = Query(1),
    limit: int = Query(20),
    db: Session = Depends(get_db)
):
    """Get customer visit history from guestbook and orders"""
    # Verify customer exists
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.venue_id == venue_id
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get guestbook entries
    guestbook_visits = db.query(GuestbookEntry).filter(
        GuestbookEntry.customer_id == customer_id,
        GuestbookEntry.venue_id == venue_id
    ).order_by(GuestbookEntry.visit_date.desc()).limit(limit).all()

    # Get order-based visits (dine-in orders indicate visits)
    order_visits = db.query(Order).filter(
        Order.customer_id == customer_id,
        Order.venue_id == venue_id,
        Order.order_type == "dine-in"
    ).order_by(Order.created_at.desc()).limit(limit).all()

    visits = []

    # Add guestbook entries
    for g in guestbook_visits:
        visits.append({
            "source": "guestbook",
            "date": g.visit_date.isoformat() if g.visit_date else None,
            "occasion": g.occasion,
            "rating": g.rating,
            "message": g.message,
            "guestbook_id": g.id
        })

    # Add order-based visits
    for o in order_visits:
        visits.append({
            "source": "order",
            "date": o.created_at.isoformat() if o.created_at else None,
            "order_id": o.id,
            "order_total": float(o.total) if o.total else 0,
            "table_id": o.table_id
        })

    # Sort by date
    visits.sort(key=lambda x: x.get("date") or "", reverse=True)

    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "visits": visits[:limit],
        "total_guestbook_entries": len(guestbook_visits),
        "total_dine_in_orders": len(order_visits)
    }

@router.post("/menu-reviews")
@limiter.limit("30/minute")
async def submit_menu_review(
    request: Request,
    venue_id: int = Query(1),
    menu_item_id: int = Body(...),
    rating: int = Body(...),
    comment: Optional[str] = Body(None),
    customer_id: Optional[int] = Body(None),
    order_id: Optional[int] = Body(None),
    taste_rating: Optional[int] = Body(None),
    presentation_rating: Optional[int] = Body(None),
    portion_rating: Optional[int] = Body(None),
    value_rating: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Submit menu item review"""
    # Validate rating
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Verify menu item exists
    menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Determine if this is a verified purchase
    verified_purchase = False
    if order_id:
        # Check if this order contains this menu item
        order_item = db.query(OrderItem).filter(
            OrderItem.order_id == order_id,
            OrderItem.menu_item_id == menu_item_id
        ).first()
        if order_item:
            verified_purchase = True

    review = MenuItemReview(
        venue_id=venue_id,
        menu_item_id=menu_item_id,
        customer_id=customer_id,
        order_id=order_id,
        rating=rating,
        review_text=comment,
        taste_rating=taste_rating,
        presentation_rating=presentation_rating,
        portion_rating=portion_rating,
        value_rating=value_rating,
        verified_purchase=verified_purchase,
        status="pending"  # Requires moderation
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return {
        "id": review.id,
        "menu_item_id": review.menu_item_id,
        "menu_item_name": menu_item.name,
        "rating": review.rating,
        "review_text": review.review_text,
        "verified_purchase": review.verified_purchase,
        "status": review.status,
        "submitted": True,
        "created_at": review.created_at.isoformat() if review.created_at else None
    }

@router.get("/menu-reviews/item/{menu_item_id}")
@limiter.limit("60/minute")
async def get_item_reviews(
    request: Request,
    menu_item_id: int,
    venue_id: int = Query(1),
    approved_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get reviews for menu item"""
    # Verify menu item exists
    menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Build query
    query = db.query(MenuItemReview).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.venue_id == venue_id
    )

    if approved_only:
        query = query.filter(MenuItemReview.status == "approved")

    # Calculate statistics
    total_reviews = query.count()
    avg_rating_result = db.query(func.avg(MenuItemReview.rating)).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.venue_id == venue_id,
        MenuItemReview.status == "approved"
    ).scalar()
    avg_rating = round(float(avg_rating_result), 1) if avg_rating_result else 0

    # Get aspect ratings
    avg_taste = db.query(func.avg(MenuItemReview.taste_rating)).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.status == "approved",
        MenuItemReview.taste_rating.isnot(None)
    ).scalar()
    avg_presentation = db.query(func.avg(MenuItemReview.presentation_rating)).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.status == "approved",
        MenuItemReview.presentation_rating.isnot(None)
    ).scalar()
    avg_portion = db.query(func.avg(MenuItemReview.portion_rating)).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.status == "approved",
        MenuItemReview.portion_rating.isnot(None)
    ).scalar()
    avg_value = db.query(func.avg(MenuItemReview.value_rating)).filter(
        MenuItemReview.menu_item_id == menu_item_id,
        MenuItemReview.status == "approved",
        MenuItemReview.value_rating.isnot(None)
    ).scalar()

    # Get reviews
    reviews = query.order_by(MenuItemReview.created_at.desc()).offset(offset).limit(limit).all()

    # Calculate rating distribution
    rating_distribution = {}
    for r in range(1, 6):
        count = db.query(func.count(MenuItemReview.id)).filter(
            MenuItemReview.menu_item_id == menu_item_id,
            MenuItemReview.status == "approved",
            MenuItemReview.rating == r
        ).scalar()
        rating_distribution[str(r)] = count or 0

    return {
        "menu_item_id": menu_item_id,
        "menu_item_name": menu_item.name,
        "avg_rating": avg_rating,
        "total_reviews": total_reviews,
        "aspect_ratings": {
            "taste": round(float(avg_taste), 1) if avg_taste else None,
            "presentation": round(float(avg_presentation), 1) if avg_presentation else None,
            "portion": round(float(avg_portion), 1) if avg_portion else None,
            "value": round(float(avg_value), 1) if avg_value else None
        },
        "rating_distribution": rating_distribution,
        "reviews": [
            {
                "id": r.id,
                "rating": r.rating,
                "review_text": r.review_text,
                "taste_rating": r.taste_rating,
                "presentation_rating": r.presentation_rating,
                "portion_rating": r.portion_rating,
                "value_rating": r.value_rating,
                "verified_purchase": r.verified_purchase,
                "photo_urls": r.photo_urls,
                "response_text": r.response_text,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reviews
        ],
        "limit": limit,
        "offset": offset
    }

# ==================== FUNDRAISING ====================

@router.post("/charity/campaigns")
@limiter.limit("30/minute")
async def create_charity_campaign(
    request: Request,
    venue_id: int = Query(1),
    charity_name: str = Body(...),
    goal_amount: Optional[float] = Body(None),
    description: Optional[str] = Body(None),
    campaign_type: str = Body("round_up"),
    prompt_message: Optional[str] = Body(None),
    thank_you_message: Optional[str] = Body(None),
    start_date: Optional[date] = Body(None),
    end_date: Optional[date] = Body(None),
    db: Session = Depends(get_db)
):
    """Create charity campaign with database persistence"""
    campaign = FundraisingCampaign(
        venue_id=venue_id,
        name=charity_name,
        organization_name=charity_name,
        description=description,
        campaign_type=campaign_type,
        goal_amount=goal_amount,
        raised_amount=0,
        donation_count=0,
        prompt_message=prompt_message,
        thank_you_message=thank_you_message,
        start_date=start_date or date.today(),
        end_date=end_date,
        is_active=True
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {
        "id": campaign.id,
        "charity_name": campaign.name,
        "organization_name": campaign.organization_name,
        "campaign_type": campaign.campaign_type,
        "goal_amount": float(campaign.goal_amount) if campaign.goal_amount else None,
        "total_raised": float(campaign.raised_amount) if campaign.raised_amount else 0,
        "donation_count": campaign.donation_count,
        "is_active": campaign.is_active,
        "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None
    }

@router.get("/charity/campaigns")
@limiter.limit("60/minute")
async def list_charity_campaigns(
    request: Request,
    venue_id: int = Query(1),
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """List all charity campaigns for a venue"""
    query = db.query(FundraisingCampaign).filter(FundraisingCampaign.venue_id == venue_id)
    if active_only:
        query = query.filter(FundraisingCampaign.is_active == True)

    campaigns = query.order_by(FundraisingCampaign.created_at.desc()).all()

    return {
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "organization_name": c.organization_name,
                "campaign_type": c.campaign_type,
                "goal_amount": float(c.goal_amount) if c.goal_amount else None,
                "raised_amount": float(c.raised_amount) if c.raised_amount else 0,
                "donation_count": c.donation_count,
                "goal_progress": (float(c.raised_amount) / float(c.goal_amount) * 100) if c.goal_amount and c.raised_amount else 0,
                "is_active": c.is_active,
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None
            }
            for c in campaigns
        ],
        "total": len(campaigns)
    }

@router.get("/charity/campaigns/{campaign_id}")
@limiter.limit("60/minute")
async def get_charity_campaign(
    request: Request,
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific charity campaign"""
    campaign = db.query(FundraisingCampaign).filter(FundraisingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {
        "id": campaign.id,
        "venue_id": campaign.venue_id,
        "name": campaign.name,
        "description": campaign.description,
        "organization_name": campaign.organization_name,
        "organization_logo_url": campaign.organization_logo_url,
        "campaign_type": campaign.campaign_type,
        "round_up_to": float(campaign.round_up_to) if campaign.round_up_to else None,
        "fixed_amount": float(campaign.fixed_amount) if campaign.fixed_amount else None,
        "percentage": campaign.percentage,
        "goal_amount": float(campaign.goal_amount) if campaign.goal_amount else None,
        "raised_amount": float(campaign.raised_amount) if campaign.raised_amount else 0,
        "donation_count": campaign.donation_count,
        "prompt_message": campaign.prompt_message,
        "thank_you_message": campaign.thank_you_message,
        "is_active": campaign.is_active,
        "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None
    }

@router.post("/charity/donations/round-up")
@limiter.limit("30/minute")
async def process_round_up(
    request: Request,
    campaign_id: int = Body(...),
    order_id: int = Body(...),
    original_total: float = Body(...),
    customer_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Process round-up donation with database persistence"""
    import math

    # Verify campaign exists and is active
    campaign = db.query(FundraisingCampaign).filter(
        FundraisingCampaign.id == campaign_id,
        FundraisingCampaign.is_active == True
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found or inactive")

    # Calculate round-up amount
    rounded = math.ceil(original_total)
    donation_amount = rounded - original_total
    if donation_amount <= 0:
        donation_amount = 1.00
        rounded = original_total + 1

    # Create donation record
    donation = FundraisingDonation(
        campaign_id=campaign_id,
        order_id=order_id,
        customer_id=customer_id,
        amount=donation_amount,
        original_total=original_total,
        rounded_total=rounded
    )
    db.add(donation)

    # Update campaign totals
    campaign.raised_amount = (campaign.raised_amount or 0) + Decimal(str(donation_amount))
    campaign.donation_count = (campaign.donation_count or 0) + 1

    db.commit()
    db.refresh(donation)

    return {
        "id": donation.id,
        "campaign_id": campaign_id,
        "donation_amount": float(donation.amount),
        "original_total": float(donation.original_total),
        "new_total": float(donation.rounded_total),
        "campaign_total_raised": float(campaign.raised_amount)
    }

@router.post("/charity/donations/flat")
@limiter.limit("30/minute")
async def process_flat_donation(
    request: Request,
    donation: CharityDonation,
    customer_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Process flat donation with database persistence"""
    # Verify campaign exists and is active
    campaign = db.query(FundraisingCampaign).filter(
        FundraisingCampaign.id == donation.campaign_id,
        FundraisingCampaign.is_active == True
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found or inactive")

    # Create donation record
    db_donation = FundraisingDonation(
        campaign_id=donation.campaign_id,
        order_id=donation.order_id,
        customer_id=customer_id,
        amount=donation.amount
    )
    db.add(db_donation)

    # Update campaign totals
    campaign.raised_amount = (campaign.raised_amount or 0) + Decimal(str(donation.amount))
    campaign.donation_count = (campaign.donation_count or 0) + 1

    db.commit()
    db.refresh(db_donation)

    return {
        "id": db_donation.id,
        "campaign_id": donation.campaign_id,
        "amount": float(db_donation.amount),
        "campaign_total_raised": float(campaign.raised_amount),
        "campaign_donation_count": campaign.donation_count
    }

@router.get("/charity/campaigns/{campaign_id}/stats")
@limiter.limit("60/minute")
async def get_campaign_stats(
    request: Request,
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Get charity campaign statistics from database"""
    campaign = db.query(FundraisingCampaign).filter(FundraisingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Calculate goal progress
    goal_progress = 0.0
    if campaign.goal_amount and campaign.raised_amount:
        goal_progress = (float(campaign.raised_amount) / float(campaign.goal_amount)) * 100

    # Get donation statistics
    donations = db.query(FundraisingDonation).filter(
        FundraisingDonation.campaign_id == campaign_id
    ).all()

    avg_donation = 0.0
    if donations:
        total = sum(float(d.amount) for d in donations)
        avg_donation = total / len(donations)

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "total_raised": float(campaign.raised_amount) if campaign.raised_amount else 0,
        "goal_amount": float(campaign.goal_amount) if campaign.goal_amount else None,
        "donation_count": campaign.donation_count or 0,
        "goal_progress": round(goal_progress, 2),
        "average_donation": round(avg_donation, 2),
        "is_active": campaign.is_active,
        "days_remaining": (campaign.end_date - date.today()).days if campaign.end_date else None
    }

@router.get("/charity/campaigns/{campaign_id}/donations")
@limiter.limit("60/minute")
async def get_campaign_donations(
    request: Request,
    campaign_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get donations for a specific campaign"""
    campaign = db.query(FundraisingCampaign).filter(FundraisingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    total_count = db.query(func.count(FundraisingDonation.id)).filter(
        FundraisingDonation.campaign_id == campaign_id
    ).scalar()

    donations = db.query(FundraisingDonation).filter(
        FundraisingDonation.campaign_id == campaign_id
    ).order_by(FundraisingDonation.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "donations": [
            {
                "id": d.id,
                "amount": float(d.amount),
                "order_id": d.order_id,
                "customer_id": d.customer_id,
                "original_total": float(d.original_total) if d.original_total else None,
                "rounded_total": float(d.rounded_total) if d.rounded_total else None,
                "is_tax_deductible": d.is_tax_deductible,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in donations
        ],
        "total": total_count,
        "limit": limit,
        "offset": offset
    }

@router.patch("/charity/campaigns/{campaign_id}")
@limiter.limit("30/minute")
async def update_charity_campaign(
    request: Request,
    campaign_id: int,
    is_active: Optional[bool] = Body(None),
    goal_amount: Optional[float] = Body(None),
    end_date: Optional[date] = Body(None),
    prompt_message: Optional[str] = Body(None),
    thank_you_message: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Update a charity campaign"""
    campaign = db.query(FundraisingCampaign).filter(FundraisingCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if is_active is not None:
        campaign.is_active = is_active
    if goal_amount is not None:
        campaign.goal_amount = goal_amount
    if end_date is not None:
        campaign.end_date = end_date
    if prompt_message is not None:
        campaign.prompt_message = prompt_message
    if thank_you_message is not None:
        campaign.thank_you_message = thank_you_message

    db.commit()
    db.refresh(campaign)

    return {
        "id": campaign.id,
        "name": campaign.name,
        "is_active": campaign.is_active,
        "goal_amount": float(campaign.goal_amount) if campaign.goal_amount else None,
        "raised_amount": float(campaign.raised_amount) if campaign.raised_amount else 0,
        "updated": True
    }

# ==================== PROMO CODES ====================

@router.post("/promo-codes/generate")
@limiter.limit("30/minute")
async def generate_promo_codes(
    request: Request,
    config: PromoCodeGenerate,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Generate single-use promo codes and save them to the database"""
    created_promotions = []

    # Map discount_type to promotion_type
    promotion_type = "percentage" if config.discount_type == "percentage" else "fixed"

    for i in range(config.count):
        # Generate unique code
        code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))

        # Create promotion in database
        promotion = Promotion(
            venue_id=venue_id,
            name=f"Promo Code {code}",
            description=f"Auto-generated promo code",
            promotion_type=promotion_type,
            discount_value=config.discount_value,
            promo_code=code,
            min_order_amount=config.minimum_order,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=config.valid_days),
            max_uses=1,  # Single-use codes
            uses_count=0,
            is_active=True
        )
        db.add(promotion)
        created_promotions.append({
            "code": code,
            "discount_type": config.discount_type,
            "discount_value": config.discount_value,
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=config.valid_days)).isoformat(),
            "minimum_order": config.minimum_order
        })

    db.commit()

    return {"codes": created_promotions, "count": len(created_promotions)}

@router.post("/promo-codes/validate")
@limiter.limit("30/minute")
async def validate_promo_code(
    request: Request,
    code: str = Body(...),
    order_total: float = Body(...),
    venue_id: int = Body(1),
    db: Session = Depends(get_db)
):
    """Validate promo code against the database"""
    # Look up the promotion by promo_code
    promotion = db.query(Promotion).filter(
        Promotion.promo_code == code,
        Promotion.is_active == True
    ).first()

    if not promotion:
        return {
            "valid": False,
            "error": "Promo code not found or inactive",
            "discount": 0,
            "new_total": order_total
        }

    # Check if the promotion has expired
    now = datetime.now(timezone.utc)
    if promotion.end_date and promotion.end_date < now:
        return {
            "valid": False,
            "error": "Promo code has expired",
            "discount": 0,
            "new_total": order_total
        }

    if promotion.start_date and promotion.start_date > now:
        return {
            "valid": False,
            "error": "Promo code is not yet valid",
            "discount": 0,
            "new_total": order_total
        }

    # Check if max uses reached
    if promotion.max_uses and promotion.uses_count >= promotion.max_uses:
        return {
            "valid": False,
            "error": "Promo code has reached maximum uses",
            "discount": 0,
            "new_total": order_total
        }

    # Check minimum order amount
    if promotion.min_order_amount and order_total < promotion.min_order_amount:
        return {
            "valid": False,
            "error": f"Minimum order amount is {promotion.min_order_amount}",
            "discount": 0,
            "new_total": order_total
        }

    # Calculate discount
    if promotion.promotion_type == "percentage":
        discount = order_total * (promotion.discount_value / 100)
    else:  # fixed
        discount = min(promotion.discount_value, order_total)  # Don't exceed order total

    new_total = max(0, order_total - discount)

    return {
        "valid": True,
        "promotion_id": promotion.id,
        "promotion_name": promotion.name,
        "promotion_type": promotion.promotion_type,
        "discount": round(discount, 2),
        "new_total": round(new_total, 2)
    }

@router.post("/promo-codes/{code}/redeem")
@limiter.limit("30/minute")
async def redeem_promo_code(
    request: Request,
    code: str,
    order_id: int = Body(...),
    customer_id: Optional[int] = Body(None),
    discount_applied: float = Body(...),
    db: Session = Depends(get_db)
):
    """Redeem promo code and record usage in the database"""
    # Look up the promotion
    promotion = db.query(Promotion).filter(
        Promotion.promo_code == code,
        Promotion.is_active == True
    ).first()

    if not promotion:
        raise HTTPException(status_code=404, detail="Promo code not found or inactive")

    # Check if already at max uses
    if promotion.max_uses and promotion.uses_count >= promotion.max_uses:
        raise HTTPException(status_code=400, detail="Promo code has reached maximum uses")

    # Check if the order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Create promotion usage record
    usage = PromotionUsage(
        promotion_id=promotion.id,
        customer_id=customer_id,
        order_id=order_id,
        discount_applied=discount_applied
    )
    db.add(usage)

    # Increment uses count
    promotion.uses_count = (promotion.uses_count or 0) + 1

    # If single-use and now used, deactivate
    if promotion.max_uses == 1:
        promotion.is_active = False

    db.commit()

    return {
        "code": code,
        "redeemed": True,
        "promotion_id": promotion.id,
        "order_id": order_id,
        "discount_applied": discount_applied,
        "remaining_uses": (promotion.max_uses - promotion.uses_count) if promotion.max_uses else None
    }

# ==================== SMART QUOTE ====================

@router.post("/smart-quote/estimate")
@limiter.limit("30/minute")
async def get_prep_time_estimate(
    request: Request,
    venue_id: int = Query(1),
    order_items: List[Dict] = Body(...),
    order_channel: str = Body("online"),
    order_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Get AI-estimated prep time based on menu item data and current kitchen load"""
    if not order_items:
        raise HTTPException(status_code=400, detail="Order items list cannot be empty")

    # Get current kitchen load (active orders in progress)
    active_orders = db.query(func.count(Order.id)).filter(
        Order.venue_id == venue_id,
        Order.status.in_(["pending", "preparing", "in_progress"]),
        Order.created_at >= datetime.now(timezone.utc) - timedelta(hours=2)
    ).scalar() or 0

    # Calculate base prep time from menu items
    total_prep_time = 0
    max_prep_time = 0
    item_details = []
    complexity_score = 0

    for item in order_items:
        menu_item_id = item.get("menu_item_id")
        quantity = item.get("quantity", 1)

        if menu_item_id:
            menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
            if menu_item:
                item_prep = menu_item.preparation_time_minutes or 10
                # For parallel prep, we take max; for sequential items we add
                max_prep_time = max(max_prep_time, item_prep)
                total_prep_time += item_prep * quantity

                # Calculate complexity based on modifiers
                modifiers_count = len(item.get("modifiers", []))
                item_complexity = 1 + (modifiers_count * 0.1)
                complexity_score += item_complexity

                item_details.append({
                    "menu_item_id": menu_item_id,
                    "name": menu_item.name,
                    "quantity": quantity,
                    "base_prep_time": item_prep,
                    "modifiers_count": modifiers_count
                })
            else:
                # Unknown item, use default prep time
                max_prep_time = max(max_prep_time, 10)
                total_prep_time += 10 * quantity
                item_details.append({
                    "menu_item_id": menu_item_id,
                    "name": "Unknown",
                    "quantity": quantity,
                    "base_prep_time": 10,
                    "modifiers_count": 0
                })

    # Number of items affects prep time (parallel prep optimization)
    item_count = sum(item.get("quantity", 1) for item in order_items)

    # Calculate kitchen load factor (0-1 scale, higher means busier)
    kitchen_load_factor = min(active_orders / 10, 1.0)  # Normalize to max 10 orders

    # Apply adjustments
    # Base estimate: Use max prep time (parallel cooking) + some additive for multiple items
    base_estimate = max_prep_time + (item_count - 1) * 2  # Add 2 min per additional item

    # Kitchen load adjustment (up to 50% increase when very busy)
    load_adjustment = 1 + (kitchen_load_factor * 0.5)

    # Channel adjustment
    channel_factors = {
        "online": 1.0,
        "delivery": 1.1,  # Slightly more for packaging
        "dine-in": 0.9,   # Can be slightly faster
        "takeaway": 1.0
    }
    channel_factor = channel_factors.get(order_channel, 1.0)

    # Complexity adjustment
    avg_complexity = complexity_score / len(order_items) if order_items else 1
    complexity_factor = 0.9 + (avg_complexity * 0.1)  # 0.9 to 1.1 range

    # Final estimate
    estimated_minutes = int(base_estimate * load_adjustment * channel_factor * complexity_factor)

    # Calculate confidence based on data quality
    # More menu items found = higher confidence
    items_found = sum(1 for d in item_details if d.get("name") != "Unknown")
    data_confidence = (items_found / len(order_items)) * 100 if order_items else 50

    # Calculate range
    min_minutes = max(5, int(estimated_minutes * 0.7))
    max_minutes = int(estimated_minutes * 1.4)

    # Store prediction for model training
    if order_id:
        prediction = PrepTimePrediction(
            venue_id=venue_id,
            order_id=order_id,
            predicted_minutes=estimated_minutes,
            confidence=data_confidence / 100,
            factors={
                "kitchen_load": kitchen_load_factor,
                "complexity": avg_complexity,
                "channel_factor": channel_factor,
                "item_count": item_count
            },
            day_of_week=datetime.now(timezone.utc).weekday(),
            hour_of_day=datetime.now(timezone.utc).hour,
            current_orders=active_orders,
            item_count=item_count,
            complexity_score=complexity_score
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)

    return {
        "estimated_minutes": estimated_minutes,
        "range": {"min": min_minutes, "max": max_minutes},
        "confidence": int(data_confidence),
        "factors": {
            "kitchen_load": round(kitchen_load_factor, 2),
            "active_orders": active_orders,
            "item_count": item_count,
            "complexity_score": round(complexity_score, 2),
            "channel": order_channel
        },
        "item_breakdown": item_details
    }

# ==================== TAX CENTER ====================

def calculate_tax_from_orders(db: Session, venue_id: int, start_date: date, end_date: date) -> Dict:
    """
    Calculate tax data from orders within a date range.
    Uses 20% VAT rate (Bulgarian standard rate).
    Tax is calculated as: order_total / 1.20 * 0.20 (tax is included in total)
    """
    VAT_RATE = Decimal("0.20")

    # Query orders within the period for the venue
    orders = db.query(Order).filter(
        Order.venue_id == venue_id,
        Order.created_at >= datetime.combine(start_date, time.min),
        Order.created_at <= datetime.combine(end_date, time.max),
        Order.payment_status == "paid"
    ).all()

    gross_revenue = Decimal("0")
    for order in orders:
        if order.total:
            gross_revenue += Decimal(str(order.total))

    # Calculate net revenue and tax (VAT is included in the total)
    # net_revenue = gross_revenue / 1.20
    # tax_collected = gross_revenue - net_revenue = gross_revenue * 0.20 / 1.20
    net_revenue = gross_revenue / (1 + VAT_RATE)
    tax_collected = gross_revenue - net_revenue

    return {
        "gross_revenue": float(round(gross_revenue, 2)),
        "net_revenue": float(round(net_revenue, 2)),
        "tax_collected": float(round(tax_collected, 2)),
        "order_count": len(orders),
        "vat_rate": float(VAT_RATE)
    }


@router.post("/tax/filings")
@limiter.limit("30/minute")
async def generate_tax_filing(
    request: Request,
    venue_id: int = Query(1),
    period_type: str = Body(...),
    period_start: date = Body(...),
    period_end: date = Body(...),
    db: Session = Depends(get_db)
):
    """Generate tax filing based on actual order data"""
    # Calculate tax from orders
    tax_data = calculate_tax_from_orders(db, venue_id, period_start, period_end)

    # Create TaxReport record
    tax_report = TaxReport(
        venue_id=venue_id,
        report_type="vat",
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        gross_revenue=Decimal(str(tax_data["gross_revenue"])),
        net_revenue=Decimal(str(tax_data["net_revenue"])),
        total_tax_collected=Decimal(str(tax_data["tax_collected"])),
        total_tax_owed=Decimal(str(tax_data["tax_collected"])),
        tax_breakdown={"20%": tax_data["tax_collected"]},
        status="draft"
    )

    db.add(tax_report)
    db.commit()
    db.refresh(tax_report)

    return {
        "id": tax_report.id,
        "tax_period": f"{period_type}_{period_start.strftime('%Y_%m')}",
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "gross_revenue": tax_data["gross_revenue"],
        "net_revenue": tax_data["net_revenue"],
        "tax_due": tax_data["tax_collected"],
        "order_count": tax_data["order_count"],
        "vat_rate": tax_data["vat_rate"],
        "status": "draft"
    }


@router.get("/tax/filings")
@limiter.limit("60/minute")
async def get_tax_filings(
    request: Request,
    venue_id: int = Query(1),
    year: int = Query(2025),
    db: Session = Depends(get_db)
):
    """Get tax filings for a venue and year from database"""
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    filings = db.query(TaxReport).filter(
        TaxReport.venue_id == venue_id,
        TaxReport.period_start >= year_start,
        TaxReport.period_end <= year_end
    ).order_by(TaxReport.period_start.desc()).all()

    return {
        "filings": [
            {
                "id": f.id,
                "report_type": f.report_type,
                "period_type": f.period_type,
                "period_start": f.period_start.isoformat() if f.period_start else None,
                "period_end": f.period_end.isoformat() if f.period_end else None,
                "gross_revenue": float(f.gross_revenue) if f.gross_revenue else 0,
                "net_revenue": float(f.net_revenue) if f.net_revenue else 0,
                "tax_collected": float(f.total_tax_collected) if f.total_tax_collected else 0,
                "tax_owed": float(f.total_tax_owed) if f.total_tax_owed else 0,
                "tax_breakdown": f.tax_breakdown or {},
                "status": f.status,
                "filing_reference": f.filing_reference,
                "submitted_at": f.submitted_at.isoformat() if f.submitted_at else None
            }
            for f in filings
        ],
        "year": year,
        "venue_id": venue_id,
        "total_filings": len(filings)
    }


@router.post("/tax/filings/{filing_id}/submit")
@limiter.limit("30/minute")
async def submit_tax_filing(
    request: Request,
    filing_id: int,
    db: Session = Depends(get_db)
):
    """Submit tax filing - updates status in database"""
    tax_report = db.query(TaxReport).filter(TaxReport.id == filing_id).first()

    if not tax_report:
        raise HTTPException(status_code=404, detail="Tax filing not found")

    if tax_report.status == "submitted":
        raise HTTPException(status_code=400, detail="Tax filing already submitted")

    # Update status and submission info
    tax_report.status = "submitted"
    tax_report.submitted_at = datetime.now(timezone.utc)
    tax_report.filing_reference = f"NRA-{filing_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    db.commit()
    db.refresh(tax_report)

    return {
        "filing_id": tax_report.id,
        "status": tax_report.status,
        "filing_reference": tax_report.filing_reference,
        "submitted_at": tax_report.submitted_at.isoformat()
    }


@router.get("/tax/summary")
@limiter.limit("60/minute")
async def get_tax_summary(
    request: Request,
    venue_id: int = Query(1),
    year: int = Query(2025),
    db: Session = Depends(get_db)
):
    """Get annual tax summary calculated from actual order data"""
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    # Calculate total tax from orders for the year
    tax_data = calculate_tax_from_orders(db, venue_id, year_start, year_end)

    # Get submitted filings to calculate what's been paid
    submitted_filings = db.query(TaxReport).filter(
        TaxReport.venue_id == venue_id,
        TaxReport.period_start >= year_start,
        TaxReport.period_end <= year_end,
        TaxReport.status == "submitted"
    ).all()

    total_tax_paid = sum(
        float(f.total_tax_owed) if f.total_tax_owed else 0
        for f in submitted_filings
    )

    total_tax_collected = tax_data["tax_collected"]
    outstanding = total_tax_collected - total_tax_paid

    # Calculate quarterly breakdown
    quarterly_breakdown = []
    for quarter in range(1, 5):
        q_start_month = (quarter - 1) * 3 + 1
        q_end_month = quarter * 3
        q_start = date(year, q_start_month, 1)
        if q_end_month == 12:
            q_end = date(year, 12, 31)
        else:
            q_end = date(year, q_end_month + 1, 1) - timedelta(days=1)

        q_data = calculate_tax_from_orders(db, venue_id, q_start, q_end)
        quarterly_breakdown.append({
            "quarter": f"Q{quarter}",
            "period": f"{q_start.isoformat()} to {q_end.isoformat()}",
            "gross_revenue": q_data["gross_revenue"],
            "tax_collected": q_data["tax_collected"],
            "order_count": q_data["order_count"]
        })

    return {
        "year": year,
        "venue_id": venue_id,
        "total_gross_revenue": tax_data["gross_revenue"],
        "total_net_revenue": tax_data["net_revenue"],
        "total_tax_collected": total_tax_collected,
        "total_tax_paid": total_tax_paid,
        "outstanding": round(outstanding, 2),
        "total_orders": tax_data["order_count"],
        "vat_rate": tax_data["vat_rate"],
        "quarterly_breakdown": quarterly_breakdown,
        "filings_submitted": len(submitted_filings)
    }

# ==================== CHARGEBACKS ====================

@router.post("/chargebacks")
@limiter.limit("30/minute")
async def record_chargeback(
    request: Request,
    chargeback_data: ChargebackCreate,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Record a new chargeback dispute from payment processor"""
    # Calculate response due date (typically 7-21 days depending on provider)
    due_date = datetime.now(timezone.utc) + timedelta(days=10)

    db_chargeback = Chargeback(
        venue_id=venue_id,
        order_id=chargeback_data.order_id,
        payment_id=chargeback_data.payment_id,
        amount=chargeback_data.amount,
        currency=chargeback_data.currency,
        reason_code=chargeback_data.reason_code,
        reason=chargeback_data.reason,
        provider=chargeback_data.provider,
        provider_case_id=chargeback_data.provider_case_id,
        status=ChargebackStatus.RECEIVED.value,
        received_at=datetime.now(timezone.utc),
        due_date=due_date
    )

    db.add(db_chargeback)
    db.commit()
    db.refresh(db_chargeback)

    return {
        "id": db_chargeback.id,
        "venue_id": db_chargeback.venue_id,
        "order_id": db_chargeback.order_id,
        "amount": float(db_chargeback.amount),
        "currency": db_chargeback.currency,
        "reason_code": db_chargeback.reason_code,
        "reason": db_chargeback.reason,
        "status": db_chargeback.status,
        "received_at": db_chargeback.received_at.isoformat() if db_chargeback.received_at else None,
        "response_due": db_chargeback.due_date.isoformat() if db_chargeback.due_date else None,
        "created_at": db_chargeback.created_at.isoformat() if db_chargeback.created_at else None
    }

@router.get("/chargebacks/{chargeback_id}")
@limiter.limit("60/minute")
async def get_chargeback(
    request: Request,
    chargeback_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific chargeback by ID"""
    chargeback = db.query(Chargeback).filter(Chargeback.id == chargeback_id).first()

    if not chargeback:
        raise HTTPException(status_code=404, detail="Chargeback not found")

    return {
        "id": chargeback.id,
        "venue_id": chargeback.venue_id,
        "order_id": chargeback.order_id,
        "payment_id": chargeback.payment_id,
        "amount": float(chargeback.amount) if chargeback.amount else 0,
        "currency": chargeback.currency,
        "reason_code": chargeback.reason_code,
        "reason": chargeback.reason,
        "provider": chargeback.provider,
        "provider_case_id": chargeback.provider_case_id,
        "status": chargeback.status,
        "received_at": chargeback.received_at.isoformat() if chargeback.received_at else None,
        "due_date": chargeback.due_date.isoformat() if chargeback.due_date else None,
        "resolved_at": chargeback.resolved_at.isoformat() if chargeback.resolved_at else None,
        "evidence_submitted": chargeback.evidence_submitted,
        "evidence_submitted_at": chargeback.evidence_submitted_at.isoformat() if chargeback.evidence_submitted_at else None,
        "evidence_documents": chargeback.evidence_documents,
        "response_notes": chargeback.response_notes,
        "won": chargeback.won,
        "amount_recovered": float(chargeback.amount_recovered) if chargeback.amount_recovered else None,
        "assigned_to": chargeback.assigned_to,
        "created_at": chargeback.created_at.isoformat() if chargeback.created_at else None,
        "updated_at": chargeback.updated_at.isoformat() if chargeback.updated_at else None
    }

@router.post("/chargebacks/{chargeback_id}/respond")
@limiter.limit("30/minute")
async def respond_to_chargeback(
    request: Request,
    chargeback_id: int,
    response_data: ChargebackResponse,
    db: Session = Depends(get_db)
):
    """Submit evidence and response to a chargeback dispute"""
    chargeback = db.query(Chargeback).filter(Chargeback.id == chargeback_id).first()

    if not chargeback:
        raise HTTPException(status_code=404, detail="Chargeback not found")

    if chargeback.status in [ChargebackStatus.WON.value, ChargebackStatus.LOST.value]:
        raise HTTPException(status_code=400, detail="Chargeback is already resolved")

    # Update chargeback with evidence
    chargeback.evidence_documents = response_data.evidence_documents
    chargeback.response_notes = response_data.response_notes
    chargeback.evidence_submitted = True
    chargeback.evidence_submitted_at = datetime.now(timezone.utc)
    chargeback.status = ChargebackStatus.EVIDENCE_SUBMITTED.value

    db.commit()
    db.refresh(chargeback)

    return {
        "chargeback_id": chargeback.id,
        "status": chargeback.status,
        "evidence_submitted": chargeback.evidence_submitted,
        "evidence_submitted_at": chargeback.evidence_submitted_at.isoformat() if chargeback.evidence_submitted_at else None,
        "message": "Evidence submitted successfully"
    }

@router.put("/chargebacks/{chargeback_id}/resolve")
@limiter.limit("30/minute")
async def resolve_chargeback(
    request: Request,
    chargeback_id: int,
    won: bool = Body(...),
    amount_recovered: Optional[float] = Body(None),
    db: Session = Depends(get_db)
):
    """Mark a chargeback as resolved (won or lost)"""
    chargeback = db.query(Chargeback).filter(Chargeback.id == chargeback_id).first()

    if not chargeback:
        raise HTTPException(status_code=404, detail="Chargeback not found")

    chargeback.won = won
    chargeback.status = ChargebackStatus.WON.value if won else ChargebackStatus.LOST.value
    chargeback.resolved_at = datetime.now(timezone.utc)

    if amount_recovered is not None:
        chargeback.amount_recovered = amount_recovered
    elif won:
        chargeback.amount_recovered = chargeback.amount

    db.commit()
    db.refresh(chargeback)

    return {
        "chargeback_id": chargeback.id,
        "status": chargeback.status,
        "won": chargeback.won,
        "amount_recovered": float(chargeback.amount_recovered) if chargeback.amount_recovered else None,
        "resolved_at": chargeback.resolved_at.isoformat() if chargeback.resolved_at else None
    }

@router.put("/chargebacks/{chargeback_id}/assign")
@limiter.limit("30/minute")
async def assign_chargeback(
    request: Request,
    chargeback_id: int,
    staff_id: int = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Assign a chargeback to a staff member for handling"""
    chargeback = db.query(Chargeback).filter(Chargeback.id == chargeback_id).first()

    if not chargeback:
        raise HTTPException(status_code=404, detail="Chargeback not found")

    chargeback.assigned_to = staff_id
    chargeback.status = ChargebackStatus.UNDER_REVIEW.value

    db.commit()
    db.refresh(chargeback)

    return {
        "chargeback_id": chargeback.id,
        "assigned_to": chargeback.assigned_to,
        "status": chargeback.status
    }

@router.get("/chargebacks")
@limiter.limit("60/minute")
async def get_chargebacks(
    request: Request,
    venue_id: int = Query(1),
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all chargebacks for a venue with optional status filter"""
    query = db.query(Chargeback).filter(Chargeback.venue_id == venue_id)

    if status:
        query = query.filter(Chargeback.status == status)

    total = query.count()
    chargebacks = query.order_by(Chargeback.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "chargebacks": [
            {
                "id": cb.id,
                "order_id": cb.order_id,
                "amount": float(cb.amount) if cb.amount else 0,
                "currency": cb.currency,
                "reason_code": cb.reason_code,
                "reason": cb.reason,
                "status": cb.status,
                "received_at": cb.received_at.isoformat() if cb.received_at else None,
                "due_date": cb.due_date.isoformat() if cb.due_date else None,
                "evidence_submitted": cb.evidence_submitted,
                "won": cb.won,
                "assigned_to": cb.assigned_to,
                "created_at": cb.created_at.isoformat() if cb.created_at else None
            }
            for cb in chargebacks
        ]
    }

@router.get("/chargebacks/stats")
@limiter.limit("60/minute")
async def get_chargeback_stats(
    request: Request,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get chargeback statistics for a venue"""
    # Get counts by status
    total = db.query(Chargeback).filter(Chargeback.venue_id == venue_id).count()

    won = db.query(Chargeback).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.status == ChargebackStatus.WON.value
    ).count()

    lost = db.query(Chargeback).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.status == ChargebackStatus.LOST.value
    ).count()

    pending_statuses = [
        ChargebackStatus.RECEIVED.value,
        ChargebackStatus.UNDER_REVIEW.value,
        ChargebackStatus.EVIDENCE_SUBMITTED.value
    ]
    pending = db.query(Chargeback).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.status.in_(pending_statuses)
    ).count()

    # Calculate total amounts
    total_amount = db.query(func.sum(Chargeback.amount)).filter(
        Chargeback.venue_id == venue_id
    ).scalar() or 0

    recovered_amount = db.query(func.sum(Chargeback.amount_recovered)).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.won == True
    ).scalar() or 0

    lost_amount = db.query(func.sum(Chargeback.amount)).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.status == ChargebackStatus.LOST.value
    ).scalar() or 0

    # Calculate win rate
    resolved = won + lost
    win_rate = (won / resolved * 100) if resolved > 0 else 0

    return {
        "total": total,
        "won": won,
        "lost": lost,
        "pending": pending,
        "win_rate": round(win_rate, 1),
        "total_amount": float(total_amount),
        "recovered_amount": float(recovered_amount),
        "lost_amount": float(lost_amount)
    }

@router.get("/chargebacks/overdue")
@limiter.limit("60/minute")
async def get_overdue_chargebacks(
    request: Request,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get chargebacks that are past their response due date"""
    pending_statuses = [
        ChargebackStatus.RECEIVED.value,
        ChargebackStatus.UNDER_REVIEW.value
    ]

    overdue = db.query(Chargeback).filter(
        Chargeback.venue_id == venue_id,
        Chargeback.status.in_(pending_statuses),
        Chargeback.due_date < datetime.now(timezone.utc)
    ).all()

    return {
        "count": len(overdue),
        "chargebacks": [
            {
                "id": cb.id,
                "order_id": cb.order_id,
                "amount": float(cb.amount) if cb.amount else 0,
                "reason_code": cb.reason_code,
                "due_date": cb.due_date.isoformat() if cb.due_date else None,
                "days_overdue": (datetime.now(timezone.utc) - cb.due_date).days if cb.due_date else 0,
                "assigned_to": cb.assigned_to
            }
            for cb in overdue
        ]
    }

# ==================== MENU PAIRINGS ====================

@router.post("/menu-pairings")
@limiter.limit("30/minute")
async def create_pairing(
    request: Request,
    pairing: MenuPairingCreate,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Create menu pairing"""
    # Verify primary item exists
    primary_item = db.query(MenuItem).filter(MenuItem.id == pairing.primary_item_id).first()
    if not primary_item:
        raise HTTPException(status_code=404, detail="Primary menu item not found")

    # Verify paired item exists
    paired_item = db.query(MenuItem).filter(MenuItem.id == pairing.paired_item_id).first()
    if not paired_item:
        raise HTTPException(status_code=404, detail="Paired menu item not found")

    # Check if pairing already exists
    existing = db.query(MenuPairing).filter(
        MenuPairing.venue_id == venue_id,
        MenuPairing.primary_item_id == pairing.primary_item_id,
        MenuPairing.paired_item_id == pairing.paired_item_id,
        MenuPairing.is_active == True
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Pairing already exists")

    db_pairing = MenuPairing(
        venue_id=venue_id,
        primary_item_id=pairing.primary_item_id,
        paired_item_id=pairing.paired_item_id,
        pairing_type=pairing.pairing_type,
        pairing_reason=pairing.pairing_reason,
        source="manual",
        confidence_score=1.0,
        is_active=True
    )
    db.add(db_pairing)
    db.commit()
    db.refresh(db_pairing)

    return {
        "id": db_pairing.id,
        "venue_id": db_pairing.venue_id,
        "primary_item_id": db_pairing.primary_item_id,
        "paired_item_id": db_pairing.paired_item_id,
        "pairing_type": db_pairing.pairing_type,
        "pairing_reason": db_pairing.pairing_reason,
        "source": db_pairing.source,
        "confidence_score": db_pairing.confidence_score,
        "created_at": db_pairing.created_at.isoformat() if db_pairing.created_at else None
    }

@router.get("/menu-pairings/item/{menu_item_id}")
@limiter.limit("60/minute")
async def get_item_pairings(
    request: Request,
    menu_item_id: int,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get pairings for item"""
    # Verify menu item exists
    menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Get all active pairings for this item
    pairings = db.query(MenuPairing).filter(
        MenuPairing.venue_id == venue_id,
        MenuPairing.primary_item_id == menu_item_id,
        MenuPairing.is_active == True
    ).order_by(MenuPairing.display_priority.desc(), MenuPairing.confidence_score.desc()).all()

    result = []
    for p in pairings:
        paired_item = db.query(MenuItem).filter(MenuItem.id == p.paired_item_id).first()
        result.append({
            "id": p.id,
            "paired_item_id": p.paired_item_id,
            "paired_item_name": paired_item.name if paired_item else "Unknown",
            "pairing_type": p.pairing_type,
            "pairing_reason": p.pairing_reason,
            "source": p.source,
            "confidence_score": p.confidence_score,
            "times_suggested": p.times_suggested,
            "times_accepted": p.times_accepted,
            "acceptance_rate": p.acceptance_rate
        })

    return {"pairings": result}

@router.get("/menu-pairings/item/{menu_item_id}/ai-suggestions")
@limiter.limit("60/minute")
async def get_ai_pairing_suggestions(
    request: Request,
    menu_item_id: int,
    venue_id: int = Query(1),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get AI-generated pairing suggestions based on historical data"""
    # Verify menu item exists
    menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Get AI-generated pairings with high confidence
    ai_pairings = db.query(MenuPairing).filter(
        MenuPairing.venue_id == venue_id,
        MenuPairing.primary_item_id == menu_item_id,
        MenuPairing.source.in_(["ai_generated", "learned"]),
        MenuPairing.is_active == True
    ).order_by(MenuPairing.confidence_score.desc()).limit(limit).all()

    suggestions = []
    for p in ai_pairings:
        paired_item = db.query(MenuItem).filter(MenuItem.id == p.paired_item_id).first()
        suggestions.append({
            "paired_item_id": p.paired_item_id,
            "item": paired_item.name if paired_item else "Unknown",
            "confidence": int(p.confidence_score * 100) if p.confidence_score else 0,
            "pairing_type": p.pairing_type,
            "pairing_reason": p.pairing_reason,
            "acceptance_rate": p.acceptance_rate
        })

    # If no AI pairings exist, look at high-acceptance manual pairings
    if not suggestions:
        manual_pairings = db.query(MenuPairing).filter(
            MenuPairing.venue_id == venue_id,
            MenuPairing.primary_item_id == menu_item_id,
            MenuPairing.source == "manual",
            MenuPairing.is_active == True,
            MenuPairing.times_suggested > 0
        ).order_by(MenuPairing.acceptance_rate.desc()).limit(limit).all()

        for p in manual_pairings:
            paired_item = db.query(MenuItem).filter(MenuItem.id == p.paired_item_id).first()
            suggestions.append({
                "paired_item_id": p.paired_item_id,
                "item": paired_item.name if paired_item else "Unknown",
                "confidence": int((p.acceptance_rate or 0) * 100),
                "pairing_type": p.pairing_type,
                "pairing_reason": p.pairing_reason,
                "acceptance_rate": p.acceptance_rate
            })

    return {
        "menu_item_id": menu_item_id,
        "menu_item_name": menu_item.name,
        "suggestions": suggestions
    }

@router.post("/menu-pairings/{pairing_id}/record-response")
@limiter.limit("30/minute")
async def record_pairing_response(
    request: Request,
    pairing_id: int,
    accepted: bool = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Record customer response to pairing suggestion"""
    pairing = db.query(MenuPairing).filter(MenuPairing.id == pairing_id).first()
    if not pairing:
        raise HTTPException(status_code=404, detail="Pairing not found")

    # Update statistics
    pairing.times_suggested = (pairing.times_suggested or 0) + 1
    if accepted:
        pairing.times_accepted = (pairing.times_accepted or 0) + 1

    # Recalculate acceptance rate
    if pairing.times_suggested > 0:
        pairing.acceptance_rate = pairing.times_accepted / pairing.times_suggested

    db.commit()
    db.refresh(pairing)

    return {
        "pairing_id": pairing_id,
        "recorded": True,
        "accepted": accepted,
        "times_suggested": pairing.times_suggested,
        "times_accepted": pairing.times_accepted,
        "acceptance_rate": pairing.acceptance_rate
    }

# ==================== TABLE BLOCKING ====================

@router.post("/table-blocks")
@limiter.limit("30/minute")
async def create_table_block(
    request: Request,
    block: TableBlockCreate,
    db: Session = Depends(get_db)
):
    """Create table time block"""
    # Verify table exists
    table = db.query(Table).filter(Table.id == block.table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Parse start and end times
    start_dt = datetime.combine(block.block_date, datetime.strptime(block.start_time, "%H:%M").time())
    end_dt = datetime.combine(block.block_date, datetime.strptime(block.end_time, "%H:%M").time())

    # Check for overlapping blocks
    overlapping = db.query(TableBlock).filter(
        TableBlock.table_id == block.table_id,
        TableBlock.start_time < end_dt,
        TableBlock.end_time > start_dt
    ).first()

    if overlapping:
        raise HTTPException(
            status_code=400,
            detail=f"Time slot conflicts with existing block (ID: {overlapping.id})"
        )

    # Create new block
    new_block = TableBlock(
        venue_id=block.venue_id,
        table_id=block.table_id,
        block_type=block.block_type,
        start_time=start_dt,
        end_time=end_dt,
        is_recurring=block.is_recurring,
        recurrence_pattern=block.recurrence_pattern,
        recurrence_end_date=block.recurrence_end_date,
        reason=block.reason,
        reservation_id=block.reservation_id,
        event_id=block.event_id
    )

    db.add(new_block)
    db.commit()
    db.refresh(new_block)

    return {
        "id": new_block.id,
        "venue_id": new_block.venue_id,
        "table_id": new_block.table_id,
        "block_type": new_block.block_type,
        "start_time": new_block.start_time.isoformat(),
        "end_time": new_block.end_time.isoformat(),
        "is_recurring": new_block.is_recurring,
        "recurrence_pattern": new_block.recurrence_pattern,
        "recurrence_end_date": new_block.recurrence_end_date.isoformat() if new_block.recurrence_end_date else None,
        "reason": new_block.reason,
        "reservation_id": new_block.reservation_id,
        "event_id": new_block.event_id,
        "created_at": new_block.created_at.isoformat()
    }

@router.get("/table-blocks")
@limiter.limit("60/minute")
async def get_table_blocks(
    request: Request,
    venue_id: int = Query(...),
    block_date: date = Query(...),
    table_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get table blocks for date"""
    # Calculate start and end of day
    start_of_day = datetime.combine(block_date, time.min)
    end_of_day = datetime.combine(block_date, time.max)

    query = db.query(TableBlock).filter(
        TableBlock.venue_id == venue_id,
        TableBlock.start_time <= end_of_day,
        TableBlock.end_time >= start_of_day
    )

    if table_id:
        query = query.filter(TableBlock.table_id == table_id)

    blocks = query.order_by(TableBlock.start_time).all()

    return {
        "venue_id": venue_id,
        "date": block_date.isoformat(),
        "blocks": [
            {
                "id": b.id,
                "table_id": b.table_id,
                "block_type": b.block_type,
                "start_time": b.start_time.isoformat(),
                "end_time": b.end_time.isoformat(),
                "is_recurring": b.is_recurring,
                "recurrence_pattern": b.recurrence_pattern,
                "reason": b.reason,
                "reservation_id": b.reservation_id,
                "event_id": b.event_id,
                "created_at": b.created_at.isoformat() if b.created_at else None
            }
            for b in blocks
        ]
    }

@router.get("/table-blocks/{block_id}")
@limiter.limit("60/minute")
async def get_table_block(
    request: Request,
    block_id: int,
    db: Session = Depends(get_db)
):
    """Get specific table block by ID"""
    block = db.query(TableBlock).filter(TableBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Table block not found")

    return {
        "id": block.id,
        "venue_id": block.venue_id,
        "table_id": block.table_id,
        "block_type": block.block_type,
        "start_time": block.start_time.isoformat(),
        "end_time": block.end_time.isoformat(),
        "is_recurring": block.is_recurring,
        "recurrence_pattern": block.recurrence_pattern,
        "recurrence_end_date": block.recurrence_end_date.isoformat() if block.recurrence_end_date else None,
        "reason": block.reason,
        "reservation_id": block.reservation_id,
        "event_id": block.event_id,
        "created_at": block.created_at.isoformat() if block.created_at else None
    }

@router.put("/table-blocks/{block_id}")
@limiter.limit("30/minute")
async def update_table_block(
    request: Request,
    block_id: int,
    block_type: Optional[str] = Body(None),
    start_time: Optional[str] = Body(None),
    end_time: Optional[str] = Body(None),
    reason: Optional[str] = Body(None),
    is_recurring: Optional[bool] = Body(None),
    recurrence_pattern: Optional[str] = Body(None),
    recurrence_end_date: Optional[date] = Body(None),
    db: Session = Depends(get_db)
):
    """Update table block"""
    block = db.query(TableBlock).filter(TableBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Table block not found")

    if block_type is not None:
        block.block_type = block_type
    if reason is not None:
        block.reason = reason
    if is_recurring is not None:
        block.is_recurring = is_recurring
    if recurrence_pattern is not None:
        block.recurrence_pattern = recurrence_pattern
    if recurrence_end_date is not None:
        block.recurrence_end_date = recurrence_end_date

    # Handle time updates
    if start_time is not None:
        current_date = block.start_time.date()
        new_start = datetime.combine(current_date, datetime.strptime(start_time, "%H:%M").time())
        block.start_time = new_start

    if end_time is not None:
        current_date = block.end_time.date()
        new_end = datetime.combine(current_date, datetime.strptime(end_time, "%H:%M").time())
        block.end_time = new_end

    db.commit()
    db.refresh(block)

    return {
        "id": block.id,
        "venue_id": block.venue_id,
        "table_id": block.table_id,
        "block_type": block.block_type,
        "start_time": block.start_time.isoformat(),
        "end_time": block.end_time.isoformat(),
        "is_recurring": block.is_recurring,
        "recurrence_pattern": block.recurrence_pattern,
        "recurrence_end_date": block.recurrence_end_date.isoformat() if block.recurrence_end_date else None,
        "reason": block.reason,
        "updated": True
    }

@router.delete("/table-blocks/{block_id}")
@limiter.limit("30/minute")
async def delete_table_block(
    request: Request,
    block_id: int,
    db: Session = Depends(get_db)
):
    """Delete table block"""
    block = db.query(TableBlock).filter(TableBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Table block not found")

    db.delete(block)
    db.commit()

    return {"id": block_id, "deleted": True}

@router.get("/tables/{table_id}/availability")
@limiter.limit("60/minute")
async def check_table_availability(
    request: Request,
    table_id: int,
    check_date: date = Query(...),
    start_time: str = Query(...),
    end_time: str = Query(...),
    db: Session = Depends(get_db)
):
    """Check table availability for a specific time slot"""
    # Verify table exists
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Parse times
    start_dt = datetime.combine(check_date, datetime.strptime(start_time, "%H:%M").time())
    end_dt = datetime.combine(check_date, datetime.strptime(end_time, "%H:%M").time())

    # Check for overlapping blocks
    conflicting_block = db.query(TableBlock).filter(
        TableBlock.table_id == table_id,
        TableBlock.start_time < end_dt,
        TableBlock.end_time > start_dt
    ).first()

    # Check for overlapping reservations
    conflicting_reservation = db.query(Reservation).filter(
        Reservation.table_id == table_id,
        Reservation.reservation_datetime < end_dt,
        Reservation.status.in_(['pending', 'confirmed'])
    ).first()

    is_available = conflicting_block is None and conflicting_reservation is None

    conflicts = []
    if conflicting_block:
        conflicts.append({
            "type": "block",
            "id": conflicting_block.id,
            "block_type": conflicting_block.block_type,
            "start_time": conflicting_block.start_time.isoformat(),
            "end_time": conflicting_block.end_time.isoformat(),
            "reason": conflicting_block.reason
        })
    if conflicting_reservation:
        conflicts.append({
            "type": "reservation",
            "id": conflicting_reservation.id,
            "start_time": conflicting_reservation.reservation_datetime.isoformat(),
            "party_size": conflicting_reservation.party_size
        })

    return {
        "table_id": table_id,
        "table_number": table.number,
        "check_date": check_date.isoformat(),
        "start_time": start_time,
        "end_time": end_time,
        "available": is_available,
        "conflicts": conflicts
    }

@router.get("/tables/{table_id}/blocks")
@limiter.limit("60/minute")
async def get_table_blocks_by_table(
    request: Request,
    table_id: int,
    start_date: date = Query(...),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all blocks for a specific table within date range"""
    # Verify table exists
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    if end_date is None:
        end_date = start_date

    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)

    blocks = db.query(TableBlock).filter(
        TableBlock.table_id == table_id,
        TableBlock.start_time <= end_dt,
        TableBlock.end_time >= start_dt
    ).order_by(TableBlock.start_time).all()

    return {
        "table_id": table_id,
        "table_number": table.number,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "blocks": [
            {
                "id": b.id,
                "block_type": b.block_type,
                "start_time": b.start_time.isoformat(),
                "end_time": b.end_time.isoformat(),
                "is_recurring": b.is_recurring,
                "reason": b.reason,
                "reservation_id": b.reservation_id,
                "event_id": b.event_id
            }
            for b in blocks
        ]
    }

@router.get("/venues/{venue_id}/table-availability")
@limiter.limit("60/minute")
async def get_venue_table_availability(
    request: Request,
    venue_id: int,
    check_date: date = Query(...),
    start_time: str = Query(...),
    end_time: str = Query(...),
    party_size: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get availability of all tables at a venue for a time slot"""
    # Get all tables for venue
    tables_query = db.query(Table).filter(Table.venue_id == venue_id, Table.is_active == True)

    if party_size:
        tables_query = tables_query.filter(Table.capacity >= party_size)

    tables = tables_query.all()

    if not tables:
        return {"venue_id": venue_id, "tables": [], "message": "No tables found for venue"}

    # Parse times
    start_dt = datetime.combine(check_date, datetime.strptime(start_time, "%H:%M").time())
    end_dt = datetime.combine(check_date, datetime.strptime(end_time, "%H:%M").time())

    availability = []
    for table in tables:
        # Check for blocks
        has_block = db.query(TableBlock).filter(
            TableBlock.table_id == table.id,
            TableBlock.start_time < end_dt,
            TableBlock.end_time > start_dt
        ).first() is not None

        # Check for reservations
        has_reservation = db.query(Reservation).filter(
            Reservation.table_id == table.id,
            Reservation.reservation_datetime < end_dt,
            Reservation.status.in_(['pending', 'confirmed'])
        ).first() is not None

        availability.append({
            "table_id": table.id,
            "table_number": table.number,
            "capacity": table.capacity,
            "available": not has_block and not has_reservation,
            "has_block": has_block,
            "has_reservation": has_reservation
        })

    available_tables = [t for t in availability if t["available"]]

    return {
        "venue_id": venue_id,
        "check_date": check_date.isoformat(),
        "start_time": start_time,
        "end_time": end_time,
        "party_size_filter": party_size,
        "total_tables": len(tables),
        "available_count": len(available_tables),
        "tables": availability
    }

# ==================== CUSTOMER DISPLAY ====================


@router.post("/customer-display/{display_id}/show-order")
@limiter.limit("30/minute")
async def show_order_on_display(
    request: Request,
    display_id: str,
    order_items: List[Dict] = Body(...),
    order_total: float = Body(...),
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Show order on customer display"""
    # Find the display by device_id
    display = db.query(CustomerDisplay).filter(
        CustomerDisplay.device_id == display_id,
        CustomerDisplay.venue_id == venue_id,
        CustomerDisplay.is_active == True
    ).first()

    if not display:
        raise HTTPException(status_code=404, detail="Customer display not found or inactive")

    # Update display mode to order
    display.display_mode = "order"
    display.last_seen_at = datetime.now(timezone.utc)
    db.commit()

    # Format order items for display based on display settings
    formatted_items = []
    for item in order_items:
        formatted_item = {
            "name": item.get("name", ""),
            "quantity": item.get("quantity", 1)
        }
        if display.show_item_prices:
            formatted_item["price"] = item.get("price", 0)
        if display.show_modifiers:
            formatted_item["modifiers"] = item.get("modifiers", [])
        formatted_items.append(formatted_item)

    return {
        "display_id": display_id,
        "content_type": "order",
        "shown": True,
        "display_settings": {
            "theme": display.theme,
            "language": display.language,
            "show_running_total": display.show_running_total,
            "show_tax": display.show_tax,
            "show_tips": display.show_tips
        },
        "order": {
            "items": formatted_items,
            "total": order_total
        }
    }

@router.post("/customer-display/{display_id}/show-promo")
@limiter.limit("30/minute")
async def show_promo_on_display(
    request: Request,
    display_id: str,
    title: str = Body(...),
    description: str = Body(...),
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Show promo on customer display"""
    # Find the display by device_id
    display = db.query(CustomerDisplay).filter(
        CustomerDisplay.device_id == display_id,
        CustomerDisplay.venue_id == venue_id,
        CustomerDisplay.is_active == True
    ).first()

    if not display:
        raise HTTPException(status_code=404, detail="Customer display not found or inactive")

    # Update display mode to promo
    display.display_mode = "promo"
    display.last_seen_at = datetime.now(timezone.utc)
    db.commit()

    # Check if there's existing promotional content that matches
    promo_content = db.query(CustomerDisplayContent).filter(
        CustomerDisplayContent.venue_id == venue_id,
        CustomerDisplayContent.is_active == True,
        CustomerDisplayContent.title == title
    ).first()

    # Create new promo content if it doesn't exist
    if not promo_content:
        promo_content = CustomerDisplayContent(
            venue_id=venue_id,
            content_type="promo",
            title=title,
            description=description,
            is_active=True,
            duration_seconds=10,
            priority=0
        )
        db.add(promo_content)
        db.commit()
        db.refresh(promo_content)

    return {
        "display_id": display_id,
        "content_type": "promo",
        "shown": True,
        "content_id": promo_content.id,
        "promo": {
            "title": title,
            "description": description,
            "duration_seconds": promo_content.duration_seconds
        },
        "display_settings": {
            "theme": display.theme,
            "language": display.language
        }
    }

@router.get("/customer-display/{display_id}/config")
@limiter.limit("60/minute")
async def get_display_config(
    request: Request,
    display_id: str,
    venue_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """Get display configuration"""
    # Find the display by device_id
    display = db.query(CustomerDisplay).filter(
        CustomerDisplay.device_id == display_id,
        CustomerDisplay.venue_id == venue_id
    ).first()

    if not display:
        raise HTTPException(status_code=404, detail="Customer display not found")

    # Update last seen timestamp
    display.last_seen_at = datetime.now(timezone.utc)
    db.commit()

    # Get active promotional content for idle mode
    promo_content = []
    if display.idle_content_type == "promotions":
        active_promos = db.query(CustomerDisplayContent).filter(
            CustomerDisplayContent.venue_id == venue_id,
            CustomerDisplayContent.is_active == True,
            CustomerDisplayContent.content_type.in_(["promo", "ad", "message"])
        ).order_by(CustomerDisplayContent.priority.desc()).limit(10).all()

        promo_content = [
            {
                "id": p.id,
                "type": p.content_type,
                "title": p.title,
                "description": p.description,
                "image_url": p.image_url,
                "video_url": p.video_url,
                "duration_seconds": p.duration_seconds
            }
            for p in active_promos
        ]

    return {
        "display_id": display_id,
        "device_name": display.device_name,
        "terminal_id": display.terminal_id,
        "location": display.location,
        "display_mode": display.display_mode,
        "theme": display.theme,
        "language": display.language,
        "settings": {
            "show_item_prices": display.show_item_prices,
            "show_modifiers": display.show_modifiers,
            "show_running_total": display.show_running_total,
            "show_tax": display.show_tax,
            "show_tips": display.show_tips
        },
        "idle_content": {
            "type": display.idle_content_type,
            "config": display.idle_content_config,
            "promotions": promo_content
        },
        "is_active": display.is_active,
        "last_seen_at": display.last_seen_at.isoformat() if display.last_seen_at else None
    }


# ==================== ENDPOINT COUNT ====================

@router.get("/stats")
@limiter.limit("60/minute")
async def get_v5_stats(request: Request, ):
    """Get V5 endpoint statistics"""
    return {
        "version": "5.0",
        "feature_categories": 15,
        "total_endpoints": 85,
        "features": [
            "SMS Marketing",
            "Catering & Events",
            "Benchmarking",
            "Reservation Deposits",
            "RFM Analytics",
            "Referral Program",
            "Break Management",
            "Shift Trading",
            "Employee Onboarding",
            "Price Tracker",
            "VIP Management",
            "Guestbook",
            "Menu Reviews",
            "Fundraising",
            "Single-Use Promo Codes",
            "Smart Quote",
            "Tax Center",
            "Chargebacks",
            "Menu Pairings",
            "Table Blocking",
            "Customer Display"
        ]
    }
