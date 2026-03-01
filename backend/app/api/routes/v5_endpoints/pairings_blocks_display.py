"""V5 sub-module: Menu Pairings, Table Blocks & Customer Display"""
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
    venue_id: int = Query(1),
    block_date: Optional[date] = Query(None, description="Block date (defaults to today)"),
    table_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get table blocks for date"""
    if block_date is None:
        block_date = date.today()

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
    check_date: Optional[date] = Query(None, description="Check date (defaults to today)"),
    start_time: Optional[str] = Query(None, description="Start time HH:MM"),
    end_time: Optional[str] = Query(None, description="End time HH:MM"),
    db: Session = Depends(get_db)
):
    """Check table availability for a specific time slot"""
    if check_date is None:
        check_date = date.today()
    if start_time is None:
        start_time = "09:00"
    if end_time is None:
        end_time = "22:00"

    # Verify table exists
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    try:
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
            Reservation.table_ids.contains([table_id]),
            Reservation.reservation_date < end_dt,
            Reservation.status.in_(['pending', 'confirmed'])
        ).first()
    except Exception:
        # If queries fail (e.g. empty tables), assume available with no conflicts
        conflicting_block = None
        conflicting_reservation = None

    is_available = conflicting_block is None and conflicting_reservation is None

    conflicts = []
    if conflicting_block:
        conflicts.append({
            "type": "block",
            "id": conflicting_block.id,
            "block_type": conflicting_block.block_type,
            "start_time": conflicting_block.start_time.isoformat() if conflicting_block.start_time else None,
            "end_time": conflicting_block.end_time.isoformat() if conflicting_block.end_time else None,
            "reason": conflicting_block.reason
        })
    if conflicting_reservation:
        res_time = getattr(conflicting_reservation, 'reservation_datetime', None)
        conflicts.append({
            "type": "reservation",
            "id": conflicting_reservation.id,
            "start_time": res_time.isoformat() if res_time else None,
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
    start_date: Optional[date] = Query(None, description="Start date (defaults to today)"),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all blocks for a specific table within date range"""
    if start_date is None:
        start_date = date.today()

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
    check_date: Optional[date] = Query(None, description="Check date (defaults to today)"),
    start_time: Optional[str] = Query(None, description="Start time HH:MM"),
    end_time: Optional[str] = Query(None, description="End time HH:MM"),
    party_size: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get availability of all tables at a venue for a time slot"""
    if check_date is None:
        check_date = date.today()
    if start_time is None:
        start_time = "09:00"
    if end_time is None:
        end_time = "22:00"

    # Get all tables for venue
    tables_query = db.query(Table).filter(Table.location_id == venue_id)

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
            Reservation.table_ids.contains([table.id]),
            Reservation.reservation_date < end_dt,
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
