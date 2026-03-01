"""Hotel PMS, offline mode & mobile app"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and helpers
from app.api.routes.enterprise._shared import *
from app.api.routes.enterprise._shared import _load_config, _save_config, _DEFAULT_MOBILE_CONFIG

router = APIRouter()

# ==================== HOTEL PMS ====================

@router.get("/hotel-pms/connection")
@limiter.limit("60/minute")
def get_hotel_connection(request: Request, db: DbSession):
    """Get hotel PMS connection status."""
    # Check if we have a hotel-pms integration connected
    integration = db.query(IntegrationModel).filter(
        IntegrationModel.category == "hotel-pms",
        IntegrationModel.status == "connected"
    ).first()

    if not integration:
        return {"connected": False, "connection": None}

    return {"connected": True, "connection": {
        "id": integration.id,
        "hotel_name": integration.name,
        "pms_type": integration.config.get("pms_type") if integration.config else "unknown",
        "status": "connected",
        "api_endpoint": integration.config.get("api_endpoint") if integration.config else None,
        "connected_at": integration.connected_at.isoformat() if integration.connected_at else None,
    }}


@router.post("/hotel-pms/connect")
@limiter.limit("30/minute")
def connect_hotel_pms(
    request: Request,
    db: DbSession,
    hotel_name: str,
    pms_type: str,
    api_endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
):
    """Connect to a hotel PMS system."""
    # Check if already connected
    existing = db.query(IntegrationModel).filter(IntegrationModel.category == "hotel-pms").first()

    if existing:
        existing.name = hotel_name
        existing.status = "connected"
        existing.connected_at = datetime.now(timezone.utc)
        existing.config = {
            "pms_type": pms_type,
            "api_endpoint": api_endpoint,
            "api_key": api_key,
        }
    else:
        new_integration = IntegrationModel(
            integration_id=f"hotel-pms-{pms_type}",
            name=hotel_name,
            category="hotel-pms",
            description=f"{pms_type.upper()} Hotel PMS Integration",
            status="connected",
            connected_at=datetime.now(timezone.utc),
            config={
                "pms_type": pms_type,
                "api_endpoint": api_endpoint,
                "api_key": api_key,
            },
        )
        db.add(new_integration)

    db.commit()

    return {"status": "connected", "connection": {
        "hotel_name": hotel_name,
        "pms_type": pms_type,
        "api_endpoint": api_endpoint,
    }}


@router.post("/hotel-pms/disconnect")
@limiter.limit("30/minute")
def disconnect_hotel_pms(request: Request, db: DbSession):
    """Disconnect from hotel PMS."""
    integration = db.query(IntegrationModel).filter(IntegrationModel.category == "hotel-pms").first()
    if integration:
        integration.status = "disconnected"
        integration.connected_at = None
        db.commit()
    return {"status": "disconnected"}


@router.get("/hotel-pms/guests")
@limiter.limit("60/minute")
def get_hotel_guests(
    request: Request,
    db: DbSession,
    room_number: Optional[str] = None,
    vip_only: bool = False,
):
    """Get hotel guests."""
    query = db.query(HotelGuestModel)
    if room_number:
        query = query.filter(HotelGuestModel.room_number == room_number)
    if vip_only:
        query = query.filter(HotelGuestModel.vip_status.isnot(None))

    guests = query.limit(500).all()

    guest_list = [{
        "id": g.id,
        "room_number": g.room_number,
        "guest_name": g.guest_name,
        "check_in": g.check_in.isoformat() if g.check_in else None,
        "check_out": g.check_out.isoformat() if g.check_out else None,
        "vip_status": g.vip_status,
        "preferences": g.preferences,
    } for g in guests]

    return {"guests": guest_list, "total": len(guest_list)}


@router.post("/hotel-pms/sync-guests")
@limiter.limit("30/minute")
def sync_hotel_guests(request: Request, db: DbSession):
    """Sync guests from hotel PMS.

    In production, this would call the actual PMS API to fetch current guests.
    Currently returns the existing guest count since no PMS is connected.
    """
    integration = db.query(IntegrationModel).filter(IntegrationModel.category == "hotel-pms").first()

    if not integration or not integration.config or not integration.config.get("connected"):
        raise HTTPException(status_code=400, detail="Hotel PMS not connected. Configure PMS integration first.")

    # Update last sync timestamp
    integration.config = {**integration.config, "last_sync": datetime.now(timezone.utc).isoformat()}
    db.commit()

    guest_count = db.query(HotelGuestModel).count()
    return {"status": "synced", "guests_count": guest_count}


@router.get("/hotel-pms/charges")
@limiter.limit("60/minute")
def get_hotel_charges(request: Request, db: DbSession):
    """Get recent hotel room charges from guest orders linked to rooms."""
    from app.models.restaurant import GuestOrder
    # Find guest orders linked to hotel rooms (table_token starts with 'room-' convention)
    orders = db.query(GuestOrder).filter(
        GuestOrder.table_token.like("room-%"),
    ).order_by(GuestOrder.id.desc()).limit(50).all()
    charges = []
    for o in orders:
        room_number = o.table_token.replace("room-", "") if o.table_token else ""
        charges.append({
            "id": o.id,
            "room_number": room_number,
            "amount": float(o.total or 0),
            "description": f"Restaurant order #{o.id}",
            "order_id": o.id,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "status": str(o.status) if o.status else "unknown",
        })
    return charges


@router.post("/hotel-pms/charges")
@limiter.limit("30/minute")
def post_hotel_charge(
    request: Request,
    db: DbSession,
    charge: HotelCharge,
):
    """Post a charge to a hotel guest's room.

    Persists the charge as a GuestOrder linked to the room (using room-{number}
    table_token convention) so it appears in GET /hotel-pms/charges.
    In production with a connected PMS, would also forward to the PMS API.
    """
    from decimal import Decimal as D
    from app.models.restaurant import GuestOrder

    guest = db.query(HotelGuestModel).filter(HotelGuestModel.id == charge.guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")

    # Persist as a GuestOrder with room-based table_token so GET /hotel-pms/charges picks it up
    order = GuestOrder(
        table_token=f"room-{charge.room_number}",
        table_number=charge.room_number,
        status="served",
        order_type="dine-in",
        subtotal=D(str(charge.amount)),
        total=D(str(charge.amount)),
        customer_name=guest.guest_name,
        notes=charge.description,
        payment_status="paid",
        payment_method="room_charge",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "status": "posted",
        "charge_id": order.id,
        "guest": guest.guest_name,
        "room": charge.room_number,
        "amount": charge.amount,
        "order_id": order.id,
    }


# ==================== OFFLINE MODE ====================

@router.get("/offline/connectivity")
@limiter.limit("60/minute")
def get_offline_status(request: Request, db: DbSession):
    """Get offline/online connectivity status."""
    pending_count = db.query(OfflineQueueModel).filter(OfflineQueueModel.status == "pending").count()

    return OfflineStatus(
        is_online=True,
        last_sync=datetime.now(timezone.utc),
        pending_sync_count=pending_count,
        sync_queue_size=pending_count,
        offline_since=None,
    )


@router.get("/offline/sync-queue")
@limiter.limit("60/minute")
def get_sync_queue(request: Request, db: DbSession):
    """Get pending sync queue items."""
    items = db.query(OfflineQueueModel).filter(OfflineQueueModel.status == "pending").limit(500).all()

    item_list = [{
        "id": item.id,
        "type": item.item_type,
        "data": item.data,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "retry_count": item.retry_count,
        "status": item.status,
    } for item in items]

    return {"queue": item_list, "total": len(item_list)}


@router.post("/offline/sync")
@limiter.limit("30/minute")
def trigger_sync(request: Request, db: DbSession):
    """Trigger a sync of offline data."""
    pending_items = db.query(OfflineQueueModel).filter(OfflineQueueModel.status == "pending").limit(500).all()
    synced_count = len(pending_items)

    # Mark all as synced
    for item in pending_items:
        item.status = "synced"

    db.commit()

    return {
        "status": "synced",
        "items_synced": synced_count,
        "synced_at": datetime.now(timezone.utc),
    }


@router.post("/offline/queue")
@limiter.limit("30/minute")
def add_to_sync_queue(
    request: Request,
    db: DbSession,
    item_type: str,
    data: dict,
):
    """Add an item to the offline sync queue."""
    new_item = OfflineQueueModel(
        item_type=item_type,
        data=data,
        status="pending",
        retry_count=0,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return {"status": "queued", "item": {
        "id": new_item.id,
        "type": new_item.item_type,
        "status": new_item.status,
        "created_at": new_item.created_at.isoformat() if new_item.created_at else None,
    }}


# ==================== MOBILE APP ====================

@router.get("/mobile-app")
@limiter.limit("60/minute")
def get_mobile_app_config(request: Request, db: DbSession):
    """Get mobile app configuration."""
    return _load_config(db, "enterprise_mobile_app", _DEFAULT_MOBILE_CONFIG)


@router.put("/mobile-app")
@limiter.limit("30/minute")
def update_mobile_app_config(
    request: Request,
    db: DbSession,
    config: MobileAppConfig,
):
    """Update mobile app configuration."""
    data = config.model_dump()
    _save_config(db, "enterprise_mobile_app", data, "Mobile App Config")
    return data


@router.post("/mobile-app/build")
@limiter.limit("30/minute")
def trigger_mobile_build(
    request: Request,
    db: DbSession,
    platform: str = "both",  # ios, android, both
):
    """Trigger a new mobile app build."""
    mc = _load_config(db, "enterprise_mobile_app", _DEFAULT_MOBILE_CONFIG)
    builds = []
    platforms = ["ios", "android"] if platform == "both" else [platform]

    for p in platforms:
        build = {
            "build_id": f"BUILD-{p.upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "platform": p,
            "version": mc.get("version", "1.0.0"),
            "status": "building",
            "download_url": None,
            "created_at": datetime.now(timezone.utc),
        }
        builds.append(build)

    return {"status": "building", "builds": builds}


# ==================== INVOICE OCR ====================

@router.post("/invoice-ocr/upload")
@limiter.limit("30/minute")
async def upload_invoice_for_ocr(
    request: Request,
    db: DbSession,
    file: UploadFile = File(...),
):
    """Upload an invoice for OCR processing."""
    # Validate file type
    allowed_types = {"application/pdf", "image/jpeg", "image/png"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, JPEG, PNG")

    # Validate file size (10MB max)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size: 10MB")
    await file.seek(0)  # Reset for downstream use

    # Sanitize filename to prevent injection attacks
    safe_filename = sanitize_filename(file.filename) if file.filename else "unnamed"

    # Create OCR job
    job = OCRJobModel(
        filename=safe_filename,
        status="processing",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # OCR processing placeholder — actual OCR integration required
    # Job remains in "processing" status until an OCR service processes it
    db.commit()

    return {"status": "processing", "job": {
        "id": job.id,
        "filename": job.filename,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "confidence": job.confidence,
        "result": job.result,
    }}


@router.get("/invoice-ocr/jobs")
@limiter.limit("60/minute")
def get_ocr_jobs(
    request: Request,
    db: DbSession,
    status: Optional[str] = None,
):
    """Get OCR processing jobs."""
    query = db.query(OCRJobModel)
    if status:
        query = query.filter(OCRJobModel.status == status)

    jobs = query.limit(500).all()

    job_list = [{
        "id": job.id,
        "filename": job.filename,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "confidence": job.confidence,
        "result": job.result,
    } for job in jobs]

    return {"jobs": job_list, "total": len(job_list)}


@router.get("/invoice-ocr/jobs/{job_id}")
@limiter.limit("60/minute")
def get_ocr_job(request: Request, db: DbSession, job_id: int):
    """Get a specific OCR job."""
    job = db.query(OCRJobModel).filter(OCRJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": job.id,
        "filename": job.filename,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "confidence": job.confidence,
        "result": job.result,
    }


