"""Inventory hardware routes - kegs, tanks, RFID, scales - using database."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from enum import Enum

from app.db.session import DbSession
from app.models.hardware import (
    Keg as KegModel,
    Tank as TankModel,
    RFIDTag as RFIDTagModel,
    InventoryCountSession as CountSessionModel,
)

router = APIRouter()


# ==================== SCHEMAS ====================

class KegStatus(str, Enum):
    FULL = "full"
    IN_USE = "in_use"
    EMPTY = "empty"
    MAINTENANCE = "maintenance"


class TankStatus(str, Enum):
    FULL = "full"
    OK = "ok"
    LOW = "low"
    CRITICAL = "critical"
    EMPTY = "empty"


class RFIDTagStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOST = "lost"


class Keg(BaseModel):
    id: int
    product_id: int
    product_name: str
    size_liters: float
    remaining_liters: float
    status: KegStatus
    tap_number: Optional[int] = None
    tapped_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    location: str = "Bar"


class KegCreate(BaseModel):
    product_id: int
    product_name: str
    size_liters: float = 50.0
    location: str = "Bar"


class Tank(BaseModel):
    id: int
    name: str
    product_id: int
    product_name: str
    capacity_liters: float
    current_level_liters: float
    level_percentage: float
    status: TankStatus
    last_refill: Optional[datetime] = None
    sensor_id: Optional[str] = None


class TankCreate(BaseModel):
    name: str
    product_id: int
    product_name: str
    capacity_liters: float
    sensor_id: Optional[str] = None


class TankLevelUpdate(BaseModel):
    current_level_liters: float


class RFIDTag(BaseModel):
    id: int
    tag_id: str
    product_id: int
    product_name: str
    quantity: float
    unit: str
    zone: str
    status: RFIDTagStatus
    last_seen: datetime
    location: Optional[str] = None


class RFIDScanResult(BaseModel):
    tag_id: str
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: Optional[float] = None
    recognized: bool
    timestamp: datetime


class RFIDZoneSummary(BaseModel):
    zone: str
    total_tags: int
    total_value: float
    items: List[dict]


class InventoryCountSession(BaseModel):
    id: int
    zone: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    tags_scanned: int
    discrepancies: int
    status: str


# ==================== KEGS ====================

@router.get("/kegs")
def list_kegs(
    db: DbSession,
    status: Optional[str] = None,
    location: Optional[str] = None,
):
    """List all kegs with optional filtering."""
    query = db.query(KegModel)
    if status:
        query = query.filter(KegModel.status == status)
    if location:
        query = query.filter(KegModel.location == location)

    kegs = query.all()

    # Convert to dict and add calculated fields
    keg_list = []
    for keg in kegs:
        keg_dict = {
            "id": keg.id,
            "product_id": keg.product_id,
            "product_name": keg.product_name,
            "size_liters": keg.size_liters,
            "remaining_liters": keg.remaining_liters,
            "status": keg.status,
            "tap_number": keg.tap_number,
            "tapped_at": keg.tapped_at,
            "expires_at": keg.expires_at,
            "location": keg.location,
            "level_percentage": round((keg.remaining_liters / keg.size_liters) * 100, 1) if keg.size_liters > 0 else 0
        }
        keg_list.append(keg_dict)

    # Get all kegs for summary
    all_kegs = db.query(KegModel).all()

    return {
        "kegs": keg_list,
        "total": len(keg_list),
        "summary": {
            "full": sum(1 for k in all_kegs if k.status == "full"),
            "in_use": sum(1 for k in all_kegs if k.status == "in_use"),
            "empty": sum(1 for k in all_kegs if k.status == "empty"),
            "total_remaining_liters": sum(k.remaining_liters for k in all_kegs),
        }
    }


@router.get("/kegs/{keg_id}")
def get_keg(db: DbSession, keg_id: int):
    """Get a specific keg."""
    keg = db.query(KegModel).filter(KegModel.id == keg_id).first()
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")

    return {
        "id": keg.id,
        "product_id": keg.product_id,
        "product_name": keg.product_name,
        "size_liters": keg.size_liters,
        "remaining_liters": keg.remaining_liters,
        "status": keg.status,
        "tap_number": keg.tap_number,
        "tapped_at": keg.tapped_at,
        "expires_at": keg.expires_at,
        "location": keg.location,
        "level_percentage": round((keg.remaining_liters / keg.size_liters) * 100, 1) if keg.size_liters > 0 else 0
    }


@router.post("/kegs")
def create_keg(db: DbSession, keg: KegCreate):
    """Add a new keg to inventory."""
    new_keg = KegModel(
        product_id=keg.product_id,
        product_name=keg.product_name,
        size_liters=keg.size_liters,
        remaining_liters=keg.size_liters,
        status="full",
        location=keg.location,
        expires_at=datetime.now(timezone.utc) + timedelta(days=60),
    )
    db.add(new_keg)
    db.commit()
    db.refresh(new_keg)

    return {
        "id": new_keg.id,
        "product_id": new_keg.product_id,
        "product_name": new_keg.product_name,
        "size_liters": new_keg.size_liters,
        "remaining_liters": new_keg.remaining_liters,
        "status": new_keg.status,
        "tap_number": new_keg.tap_number,
        "tapped_at": new_keg.tapped_at,
        "expires_at": new_keg.expires_at,
        "location": new_keg.location,
    }


@router.post("/kegs/tap")
def tap_keg(
    db: DbSession,
    keg_id: int,
    tap_number: int,
):
    """Tap a keg (put it on a tap line)."""
    keg = db.query(KegModel).filter(KegModel.id == keg_id).first()
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")
    if keg.status != "full":
        raise HTTPException(status_code=400, detail="Can only tap full kegs")

    # Check if tap is already in use
    current_on_tap = db.query(KegModel).filter(
        KegModel.tap_number == tap_number,
        KegModel.status == "in_use"
    ).first()
    if current_on_tap:
        raise HTTPException(status_code=400, detail=f"Tap {tap_number} already has a keg")

    keg.status = "in_use"
    keg.tap_number = tap_number
    keg.tapped_at = datetime.now(timezone.utc)
    keg.location = "Bar"
    db.commit()

    return {"status": "tapped", "keg": {
        "id": keg.id,
        "product_id": keg.product_id,
        "product_name": keg.product_name,
        "status": keg.status,
        "tap_number": keg.tap_number,
        "tapped_at": keg.tapped_at,
    }}


@router.post("/kegs/{keg_id}/pour")
def record_pour(
    db: DbSession,
    keg_id: int,
    liters: float,
):
    """Record a pour from a keg."""
    keg = db.query(KegModel).filter(KegModel.id == keg_id).first()
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")

    keg.remaining_liters = max(0, keg.remaining_liters - liters)
    if keg.remaining_liters == 0:
        keg.status = "empty"
        keg.tap_number = None
    db.commit()

    return {"status": "recorded", "remaining_liters": keg.remaining_liters}


@router.post("/kegs/{keg_id}/empty")
def mark_keg_empty(db: DbSession, keg_id: int):
    """Mark a keg as empty."""
    keg = db.query(KegModel).filter(KegModel.id == keg_id).first()
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")

    keg.status = "empty"
    keg.remaining_liters = 0
    keg.tap_number = None
    keg.location = "Returns"
    db.commit()

    return {"status": "marked_empty", "keg": {
        "id": keg.id,
        "product_name": keg.product_name,
        "status": keg.status,
        "location": keg.location,
    }}


# ==================== TANKS ====================

@router.get("/tanks")
def list_tanks(
    db: DbSession,
    status: Optional[str] = None,
):
    """List all tanks."""
    query = db.query(TankModel)
    if status:
        query = query.filter(TankModel.status == status)

    tanks = query.all()

    tank_list = []
    alerts = []
    for tank in tanks:
        level_percentage = round((tank.current_level_liters / tank.capacity_liters) * 100, 1) if tank.capacity_liters > 0 else 0
        tank_dict = {
            "id": tank.id,
            "name": tank.name,
            "product_id": tank.product_id,
            "product_name": tank.product_name,
            "capacity_liters": tank.capacity_liters,
            "current_level_liters": tank.current_level_liters,
            "level_percentage": level_percentage,
            "status": tank.status,
            "last_refill": tank.last_refill,
            "sensor_id": tank.sensor_id,
        }
        tank_list.append(tank_dict)
        if tank.status in ["low", "critical"]:
            alerts.append(tank_dict)

    return {
        "tanks": tank_list,
        "total": len(tank_list),
        "alerts": alerts,
    }


@router.get("/tanks/{tank_id}")
def get_tank(db: DbSession, tank_id: int):
    """Get a specific tank."""
    tank = db.query(TankModel).filter(TankModel.id == tank_id).first()
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")

    return {
        "id": tank.id,
        "name": tank.name,
        "product_id": tank.product_id,
        "product_name": tank.product_name,
        "capacity_liters": tank.capacity_liters,
        "current_level_liters": tank.current_level_liters,
        "level_percentage": round((tank.current_level_liters / tank.capacity_liters) * 100, 1) if tank.capacity_liters > 0 else 0,
        "status": tank.status,
        "last_refill": tank.last_refill,
        "sensor_id": tank.sensor_id,
    }


@router.post("/tanks")
def create_tank(db: DbSession, tank: TankCreate):
    """Add a new tank."""
    new_tank = TankModel(
        name=tank.name,
        product_id=tank.product_id,
        product_name=tank.product_name,
        capacity_liters=tank.capacity_liters,
        current_level_liters=tank.capacity_liters,
        status="full",
        last_refill=datetime.now(timezone.utc),
        sensor_id=tank.sensor_id,
    )
    db.add(new_tank)
    db.commit()
    db.refresh(new_tank)

    return {
        "id": new_tank.id,
        "name": new_tank.name,
        "product_id": new_tank.product_id,
        "product_name": new_tank.product_name,
        "capacity_liters": new_tank.capacity_liters,
        "current_level_liters": new_tank.current_level_liters,
        "status": new_tank.status,
        "last_refill": new_tank.last_refill,
        "sensor_id": new_tank.sensor_id,
    }


@router.post("/tanks/level")
def update_tank_level(
    db: DbSession,
    tank_id: int,
    level: TankLevelUpdate,
):
    """Update tank level (from sensor or manual)."""
    tank = db.query(TankModel).filter(TankModel.id == tank_id).first()
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")

    tank.current_level_liters = level.current_level_liters
    percentage = (level.current_level_liters / tank.capacity_liters) * 100

    # Update status based on level
    if percentage >= 90:
        tank.status = "full"
    elif percentage >= 50:
        tank.status = "ok"
    elif percentage >= 20:
        tank.status = "low"
    elif percentage > 0:
        tank.status = "critical"
    else:
        tank.status = "empty"

    db.commit()

    return {"status": "updated", "tank": {
        "id": tank.id,
        "name": tank.name,
        "current_level_liters": tank.current_level_liters,
        "status": tank.status,
    }}


@router.post("/tanks/{tank_id}/refill")
def refill_tank(db: DbSession, tank_id: int):
    """Mark a tank as refilled."""
    tank = db.query(TankModel).filter(TankModel.id == tank_id).first()
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")

    tank.current_level_liters = tank.capacity_liters
    tank.status = "full"
    tank.last_refill = datetime.now(timezone.utc)
    db.commit()

    return {"status": "refilled", "tank": {
        "id": tank.id,
        "name": tank.name,
        "current_level_liters": tank.current_level_liters,
        "status": tank.status,
        "last_refill": tank.last_refill,
    }}


# ==================== RFID ====================

@router.get("/rfid/tags")
def list_rfid_tags(
    db: DbSession,
    zone: Optional[str] = None,
    status: Optional[str] = None,
):
    """List all RFID tags."""
    query = db.query(RFIDTagModel)
    if zone:
        query = query.filter(RFIDTagModel.zone == zone)
    if status:
        query = query.filter(RFIDTagModel.status == status)

    tags = query.all()

    tag_list = [{
        "id": tag.id,
        "tag_id": tag.tag_id,
        "product_id": tag.product_id,
        "product_name": tag.product_name,
        "quantity": tag.quantity,
        "unit": tag.unit,
        "zone": tag.zone,
        "status": tag.status,
        "last_seen": tag.last_seen,
        "location": tag.location,
    } for tag in tags]

    # Get all zones
    all_tags = db.query(RFIDTagModel).all()
    zones = list(set(t.zone for t in all_tags))

    return {
        "tags": tag_list,
        "total": len(tag_list),
        "zones": zones,
    }


@router.get("/rfid/tags/status")
def get_rfid_status(db: DbSession):
    """Get RFID system status."""
    tags = db.query(RFIDTagModel).all()

    return {
        "total_tags": len(tags),
        "active_tags": sum(1 for t in tags if t.status == "active"),
        "zones": list(set(t.zone for t in tags)),
        "last_scan": max((t.last_seen for t in tags), default=None) if tags else None,
        "system_status": "online",
    }


@router.get("/rfid/tags/{tag_id}")
def get_rfid_tag(db: DbSession, tag_id: str):
    """Get a specific RFID tag."""
    tag = db.query(RFIDTagModel).filter(RFIDTagModel.tag_id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    return {
        "id": tag.id,
        "tag_id": tag.tag_id,
        "product_id": tag.product_id,
        "product_name": tag.product_name,
        "quantity": tag.quantity,
        "unit": tag.unit,
        "zone": tag.zone,
        "status": tag.status,
        "last_seen": tag.last_seen,
        "location": tag.location,
    }


@router.post("/rfid/scan")
def record_rfid_scan(
    db: DbSession,
    tag_id: str,
    zone: Optional[str] = None,
    location: Optional[str] = None,
):
    """Record an RFID tag scan."""
    tag = db.query(RFIDTagModel).filter(RFIDTagModel.tag_id == tag_id).first()

    if tag:
        tag.last_seen = datetime.now(timezone.utc)
        if zone:
            tag.zone = zone
        if location:
            tag.location = location
        db.commit()

        return RFIDScanResult(
            tag_id=tag_id,
            product_id=tag.product_id,
            product_name=tag.product_name,
            quantity=tag.quantity,
            recognized=True,
            timestamp=datetime.now(timezone.utc),
        )
    else:
        return RFIDScanResult(
            tag_id=tag_id,
            recognized=False,
            timestamp=datetime.now(timezone.utc),
        )


@router.get("/rfid/zones/summary")
def get_zones_summary(db: DbSession):
    """Get inventory summary by zone."""
    tags = db.query(RFIDTagModel).all()

    zones = {}
    for tag in tags:
        zone = tag.zone
        if zone not in zones:
            zones[zone] = {"zone": zone, "total_tags": 0, "total_value": 0, "items": []}
        zones[zone]["total_tags"] += 1
        zones[zone]["items"].append({
            "product_name": tag.product_name,
            "quantity": tag.quantity,
            "unit": tag.unit,
        })

    return {"zones": list(zones.values())}


@router.post("/rfid/inventory-count/start")
def start_rfid_inventory_count(
    db: DbSession,
    zone: str,
):
    """Start an RFID-based inventory count session."""
    session = CountSessionModel(
        zone=zone,
        started_at=datetime.now(timezone.utc),
        tags_scanned=0,
        discrepancies=0,
        status="in_progress",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {"status": "started", "session": {
        "id": session.id,
        "zone": session.zone,
        "started_at": session.started_at,
        "status": session.status,
    }}


@router.post("/rfid/inventory-count/{session_id}/complete")
def complete_rfid_inventory_count(
    db: DbSession,
    session_id: int,
):
    """Complete an RFID inventory count session."""
    session = db.query(CountSessionModel).filter(CountSessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.completed_at = datetime.now(timezone.utc)
    session.status = "completed"

    # Count tags in the zone
    zone_tags = db.query(RFIDTagModel).filter(RFIDTagModel.zone == session.zone).count()
    session.tags_scanned = zone_tags
    db.commit()

    return {"status": "completed", "session": {
        "id": session.id,
        "zone": session.zone,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "tags_scanned": session.tags_scanned,
        "status": session.status,
    }}


@router.get("/rfid/inventory-count/sessions")
def list_inventory_count_sessions(db: DbSession):
    """List all inventory count sessions."""
    sessions = db.query(CountSessionModel).all()

    session_list = [{
        "id": s.id,
        "zone": s.zone,
        "started_at": s.started_at,
        "completed_at": s.completed_at,
        "tags_scanned": s.tags_scanned,
        "discrepancies": s.discrepancies,
        "status": s.status,
    } for s in sessions]

    return {"sessions": session_list, "total": len(session_list)}
