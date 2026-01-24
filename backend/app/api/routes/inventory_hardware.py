"""Inventory hardware routes - kegs, tanks, RFID, scales."""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from enum import Enum

from app.db.session import DbSession

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


# ==================== IN-MEMORY STORAGE ====================

_kegs = [
    {"id": 1, "product_id": 101, "product_name": "Heineken Draft", "size_liters": 50.0, "remaining_liters": 45.0, "status": "in_use", "tap_number": 1, "tapped_at": datetime.utcnow() - timedelta(days=2), "expires_at": datetime.utcnow() + timedelta(days=5), "location": "Bar"},
    {"id": 2, "product_id": 102, "product_name": "Stella Artois", "size_liters": 50.0, "remaining_liters": 50.0, "status": "full", "tap_number": None, "tapped_at": None, "expires_at": datetime.utcnow() + timedelta(days=30), "location": "Storage"},
    {"id": 3, "product_id": 103, "product_name": "Corona Draft", "size_liters": 30.0, "remaining_liters": 12.0, "status": "in_use", "tap_number": 2, "tapped_at": datetime.utcnow() - timedelta(days=5), "expires_at": datetime.utcnow() + timedelta(days=2), "location": "Bar"},
    {"id": 4, "product_id": 104, "product_name": "Guinness", "size_liters": 50.0, "remaining_liters": 0.0, "status": "empty", "tap_number": None, "tapped_at": None, "expires_at": None, "location": "Returns"},
    {"id": 5, "product_id": 101, "product_name": "Heineken Draft", "size_liters": 50.0, "remaining_liters": 50.0, "status": "full", "tap_number": None, "tapped_at": None, "expires_at": datetime.utcnow() + timedelta(days=45), "location": "Storage"},
]

_tanks = [
    {"id": 1, "name": "CO2 Tank Main", "product_id": 201, "product_name": "CO2", "capacity_liters": 100.0, "current_level_liters": 75.0, "status": "ok", "last_refill": datetime.utcnow() - timedelta(days=10), "sensor_id": "TANK-001"},
    {"id": 2, "name": "Nitrogen Tank", "product_id": 202, "product_name": "Nitrogen", "capacity_liters": 50.0, "current_level_liters": 45.0, "status": "ok", "last_refill": datetime.utcnow() - timedelta(days=5), "sensor_id": "TANK-002"},
    {"id": 3, "name": "Beer Gas Mix", "product_id": 203, "product_name": "Beer Gas 70/30", "capacity_liters": 75.0, "current_level_liters": 15.0, "status": "low", "last_refill": datetime.utcnow() - timedelta(days=20), "sensor_id": "TANK-003"},
    {"id": 4, "name": "CO2 Tank Backup", "product_id": 201, "product_name": "CO2", "capacity_liters": 100.0, "current_level_liters": 5.0, "status": "critical", "last_refill": datetime.utcnow() - timedelta(days=30), "sensor_id": "TANK-004"},
]

_rfid_tags = [
    {"id": 1, "tag_id": "RFID-001", "product_id": 301, "product_name": "Absolut Vodka 750ml", "quantity": 12, "unit": "bottles", "zone": "Bar", "status": "active", "last_seen": datetime.utcnow(), "location": "Shelf A1"},
    {"id": 2, "tag_id": "RFID-002", "product_id": 302, "product_name": "Jack Daniels 750ml", "quantity": 8, "unit": "bottles", "zone": "Bar", "status": "active", "last_seen": datetime.utcnow() - timedelta(hours=2), "location": "Shelf A2"},
    {"id": 3, "tag_id": "RFID-003", "product_id": 303, "product_name": "Tanqueray Gin 1L", "quantity": 6, "unit": "bottles", "zone": "Bar", "status": "active", "last_seen": datetime.utcnow() - timedelta(hours=1), "location": "Shelf A3"},
    {"id": 4, "tag_id": "RFID-004", "product_id": 304, "product_name": "Corona 24-pack", "quantity": 5, "unit": "cases", "zone": "Storage", "status": "active", "last_seen": datetime.utcnow() - timedelta(days=1), "location": "Rack B1"},
    {"id": 5, "tag_id": "RFID-005", "product_id": 305, "product_name": "Heineken 24-pack", "quantity": 8, "unit": "cases", "zone": "Storage", "status": "active", "last_seen": datetime.utcnow() - timedelta(hours=12), "location": "Rack B2"},
    {"id": 6, "tag_id": "RFID-006", "product_id": 306, "product_name": "Red Bull 12-pack", "quantity": 3, "unit": "cases", "zone": "Walk-in", "status": "active", "last_seen": datetime.utcnow() - timedelta(hours=6), "location": "Shelf C1"},
]

_count_sessions = []


# ==================== KEGS ====================

@router.get("/kegs")
def list_kegs(
    db: DbSession,
    status: Optional[str] = None,
    location: Optional[str] = None,
):
    """List all kegs with optional filtering."""
    kegs = _kegs
    if status:
        kegs = [k for k in kegs if k["status"] == status]
    if location:
        kegs = [k for k in kegs if k["location"] == location]

    # Add calculated fields
    for keg in kegs:
        keg["level_percentage"] = round((keg["remaining_liters"] / keg["size_liters"]) * 100, 1) if keg["size_liters"] > 0 else 0

    return {
        "kegs": kegs,
        "total": len(kegs),
        "summary": {
            "full": sum(1 for k in _kegs if k["status"] == "full"),
            "in_use": sum(1 for k in _kegs if k["status"] == "in_use"),
            "empty": sum(1 for k in _kegs if k["status"] == "empty"),
            "total_remaining_liters": sum(k["remaining_liters"] for k in _kegs),
        }
    }


@router.get("/kegs/{keg_id}")
def get_keg(db: DbSession, keg_id: int):
    """Get a specific keg."""
    keg = next((k for k in _kegs if k["id"] == keg_id), None)
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")
    keg["level_percentage"] = round((keg["remaining_liters"] / keg["size_liters"]) * 100, 1)
    return keg


@router.post("/kegs")
def create_keg(db: DbSession, keg: KegCreate):
    """Add a new keg to inventory."""
    new_id = max(k["id"] for k in _kegs) + 1 if _kegs else 1
    new_keg = {
        "id": new_id,
        **keg.model_dump(),
        "remaining_liters": keg.size_liters,
        "status": "full",
        "tap_number": None,
        "tapped_at": None,
        "expires_at": datetime.utcnow() + timedelta(days=60),
    }
    _kegs.append(new_keg)
    return new_keg


@router.post("/kegs/tap")
def tap_keg(
    db: DbSession,
    keg_id: int,
    tap_number: int,
):
    """Tap a keg (put it on a tap line)."""
    keg = next((k for k in _kegs if k["id"] == keg_id), None)
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")
    if keg["status"] != "full":
        raise HTTPException(status_code=400, detail="Can only tap full kegs")

    # Check if tap is already in use
    current_on_tap = next((k for k in _kegs if k["tap_number"] == tap_number and k["status"] == "in_use"), None)
    if current_on_tap:
        raise HTTPException(status_code=400, detail=f"Tap {tap_number} already has a keg")

    keg["status"] = "in_use"
    keg["tap_number"] = tap_number
    keg["tapped_at"] = datetime.utcnow()
    keg["location"] = "Bar"

    return {"status": "tapped", "keg": keg}


@router.post("/kegs/{keg_id}/pour")
def record_pour(
    db: DbSession,
    keg_id: int,
    liters: float,
):
    """Record a pour from a keg."""
    keg = next((k for k in _kegs if k["id"] == keg_id), None)
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")

    keg["remaining_liters"] = max(0, keg["remaining_liters"] - liters)
    if keg["remaining_liters"] == 0:
        keg["status"] = "empty"
        keg["tap_number"] = None

    return {"status": "recorded", "remaining_liters": keg["remaining_liters"]}


@router.post("/kegs/{keg_id}/empty")
def mark_keg_empty(db: DbSession, keg_id: int):
    """Mark a keg as empty."""
    keg = next((k for k in _kegs if k["id"] == keg_id), None)
    if not keg:
        raise HTTPException(status_code=404, detail="Keg not found")

    keg["status"] = "empty"
    keg["remaining_liters"] = 0
    keg["tap_number"] = None
    keg["location"] = "Returns"

    return {"status": "marked_empty", "keg": keg}


# ==================== TANKS ====================

@router.get("/tanks")
def list_tanks(
    db: DbSession,
    status: Optional[str] = None,
):
    """List all tanks."""
    tanks = _tanks
    if status:
        tanks = [t for t in tanks if t["status"] == status]

    # Calculate level percentages
    for tank in tanks:
        tank["level_percentage"] = round((tank["current_level_liters"] / tank["capacity_liters"]) * 100, 1) if tank["capacity_liters"] > 0 else 0

    return {
        "tanks": tanks,
        "total": len(tanks),
        "alerts": [t for t in tanks if t["status"] in ["low", "critical"]],
    }


@router.get("/tanks/{tank_id}")
def get_tank(db: DbSession, tank_id: int):
    """Get a specific tank."""
    tank = next((t for t in _tanks if t["id"] == tank_id), None)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")
    tank["level_percentage"] = round((tank["current_level_liters"] / tank["capacity_liters"]) * 100, 1)
    return tank


@router.post("/tanks")
def create_tank(db: DbSession, tank: TankCreate):
    """Add a new tank."""
    new_id = max(t["id"] for t in _tanks) + 1 if _tanks else 1
    new_tank = {
        "id": new_id,
        **tank.model_dump(),
        "current_level_liters": tank.capacity_liters,
        "status": "full",
        "last_refill": datetime.utcnow(),
    }
    _tanks.append(new_tank)
    return new_tank


@router.post("/tanks/level")
def update_tank_level(
    db: DbSession,
    tank_id: int,
    level: TankLevelUpdate,
):
    """Update tank level (from sensor or manual)."""
    tank = next((t for t in _tanks if t["id"] == tank_id), None)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")

    tank["current_level_liters"] = level.current_level_liters
    percentage = (level.current_level_liters / tank["capacity_liters"]) * 100

    # Update status based on level
    if percentage >= 90:
        tank["status"] = "full"
    elif percentage >= 50:
        tank["status"] = "ok"
    elif percentage >= 20:
        tank["status"] = "low"
    elif percentage > 0:
        tank["status"] = "critical"
    else:
        tank["status"] = "empty"

    return {"status": "updated", "tank": tank}


@router.post("/tanks/{tank_id}/refill")
def refill_tank(db: DbSession, tank_id: int):
    """Mark a tank as refilled."""
    tank = next((t for t in _tanks if t["id"] == tank_id), None)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")

    tank["current_level_liters"] = tank["capacity_liters"]
    tank["status"] = "full"
    tank["last_refill"] = datetime.utcnow()

    return {"status": "refilled", "tank": tank}


# ==================== RFID ====================

@router.get("/rfid/tags")
def list_rfid_tags(
    db: DbSession,
    zone: Optional[str] = None,
    status: Optional[str] = None,
):
    """List all RFID tags."""
    tags = _rfid_tags
    if zone:
        tags = [t for t in tags if t["zone"] == zone]
    if status:
        tags = [t for t in tags if t["status"] == status]

    return {
        "tags": tags,
        "total": len(tags),
        "zones": list(set(t["zone"] for t in _rfid_tags)),
    }


@router.get("/rfid/tags/status")
def get_rfid_status(db: DbSession):
    """Get RFID system status."""
    return {
        "total_tags": len(_rfid_tags),
        "active_tags": sum(1 for t in _rfid_tags if t["status"] == "active"),
        "zones": list(set(t["zone"] for t in _rfid_tags)),
        "last_scan": max(t["last_seen"] for t in _rfid_tags) if _rfid_tags else None,
        "system_status": "online",
    }


@router.get("/rfid/tags/{tag_id}")
def get_rfid_tag(db: DbSession, tag_id: str):
    """Get a specific RFID tag."""
    tag = next((t for t in _rfid_tags if t["tag_id"] == tag_id), None)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("/rfid/scan")
def record_rfid_scan(
    db: DbSession,
    tag_id: str,
    zone: Optional[str] = None,
    location: Optional[str] = None,
):
    """Record an RFID tag scan."""
    tag = next((t for t in _rfid_tags if t["tag_id"] == tag_id), None)

    if tag:
        tag["last_seen"] = datetime.utcnow()
        if zone:
            tag["zone"] = zone
        if location:
            tag["location"] = location

        return RFIDScanResult(
            tag_id=tag_id,
            product_id=tag["product_id"],
            product_name=tag["product_name"],
            quantity=tag["quantity"],
            recognized=True,
            timestamp=datetime.utcnow(),
        )
    else:
        return RFIDScanResult(
            tag_id=tag_id,
            recognized=False,
            timestamp=datetime.utcnow(),
        )


@router.get("/rfid/zones/summary")
def get_zones_summary(db: DbSession):
    """Get inventory summary by zone."""
    zones = {}
    for tag in _rfid_tags:
        zone = tag["zone"]
        if zone not in zones:
            zones[zone] = {"zone": zone, "total_tags": 0, "total_value": 0, "items": []}
        zones[zone]["total_tags"] += 1
        zones[zone]["items"].append({
            "product_name": tag["product_name"],
            "quantity": tag["quantity"],
            "unit": tag["unit"],
        })

    return {"zones": list(zones.values())}


@router.post("/rfid/inventory-count/start")
def start_rfid_inventory_count(
    db: DbSession,
    zone: str,
):
    """Start an RFID-based inventory count session."""
    session = {
        "id": len(_count_sessions) + 1,
        "zone": zone,
        "started_at": datetime.utcnow(),
        "completed_at": None,
        "tags_scanned": 0,
        "discrepancies": 0,
        "status": "in_progress",
    }
    _count_sessions.append(session)
    return {"status": "started", "session": session}


@router.post("/rfid/inventory-count/{session_id}/complete")
def complete_rfid_inventory_count(
    db: DbSession,
    session_id: int,
):
    """Complete an RFID inventory count session."""
    session = next((s for s in _count_sessions if s["id"] == session_id), None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session["completed_at"] = datetime.utcnow()
    session["status"] = "completed"

    # Count tags in the zone
    zone_tags = [t for t in _rfid_tags if t["zone"] == session["zone"]]
    session["tags_scanned"] = len(zone_tags)

    return {"status": "completed", "session": session}


@router.get("/rfid/inventory-count/sessions")
def list_inventory_count_sessions(db: DbSession):
    """List all inventory count sessions."""
    return {"sessions": _count_sessions, "total": len(_count_sessions)}
