"""Enhanced Table Management API routes.

Closes table management gap (90% → 95%):
- Extended table states (dirty, maintenance, out_of_service)
- Guest-facing waitlist display with positions
- Turn time alerts for slow tables
- Server auto-load balancing
- Smart party-to-table matching
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, RequireManager
from app.services.table_enhancements_service import get_table_enhancements_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---- Schemas ----

class TableMetadataUpdate(BaseModel):
    table_id: int
    server_name: Optional[str] = None
    estimated_clear_time: Optional[str] = None
    maintenance_notes: Optional[str] = None
    accessibility: Optional[bool] = None
    high_chair_available: Optional[bool] = None


class MaintenanceRequest(BaseModel):
    table_id: int
    reason: str
    scheduled_at: Optional[str] = None
    estimated_duration_minutes: int = 30
    assigned_to: Optional[str] = None


class MaintenanceCompleteRequest(BaseModel):
    notes: Optional[str] = None


class PartyMatchRequest(BaseModel):
    party_size: int = Field(..., gt=0, le=50)
    preferences: Optional[Dict[str, Any]] = None


class TurnAlertConfig(BaseModel):
    threshold_minutes: int = Field(90, gt=0, le=300)


class LoadBalanceRequest(BaseModel):
    servers: List[Dict[str, Any]]
    table_assignments: List[Dict[str, Any]]


class ServerSuggestionRequest(BaseModel):
    table: Dict[str, Any]
    servers: List[Dict[str, Any]]
    table_assignments: List[Dict[str, Any]]


# ---- Routes ----

@router.get("/")
@limiter.limit("60/minute")
async def overview(request: Request):
    """Table enhancements overview."""
    return {
        "module": "table-enhancements",
        "features": [
            "Extended table states (dirty, maintenance, out_of_service)",
            "Guest-facing waitlist display",
            "Turn time alerts for slow tables",
            "Server auto-load balancing",
            "Smart party-to-table matching",
            "Maintenance scheduling and tracking",
        ],
    }


# ---- Extended States ----

@router.get("/states")
@limiter.limit("60/minute")
async def get_table_states(request: Request):
    """Get all supported table states with metadata."""
    svc = get_table_enhancements_service()
    return {"states": svc.get_extended_states()}


@router.get("/states/transitions")
@limiter.limit("60/minute")
async def get_state_transitions(request: Request):
    """Get allowed state transitions."""
    from app.services.table_enhancements_service import TABLE_STATE_TRANSITIONS
    return {"transitions": TABLE_STATE_TRANSITIONS}


# ---- Table Metadata ----

@router.put("/metadata")
@limiter.limit("30/minute")
async def update_table_metadata(request: Request, body: TableMetadataUpdate, user: CurrentUser):
    """Update extended table metadata (server name, clear time, etc.)."""
    svc = get_table_enhancements_service()
    from datetime import datetime
    clear_time = None
    if body.estimated_clear_time:
        try:
            clear_time = datetime.fromisoformat(body.estimated_clear_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format for estimated_clear_time")

    result = svc.set_table_metadata(
        table_id=body.table_id,
        server_name=body.server_name,
        estimated_clear_time=clear_time,
        maintenance_notes=body.maintenance_notes,
        accessibility=body.accessibility,
        high_chair_available=body.high_chair_available,
    )
    return {"success": True, "metadata": result}


@router.get("/metadata/{table_id}")
@limiter.limit("60/minute")
async def get_table_metadata(request: Request, table_id: int):
    """Get extended metadata for a table."""
    svc = get_table_enhancements_service()
    return svc.get_table_metadata(table_id)


# ---- Maintenance ----

@router.post("/maintenance")
@limiter.limit("20/minute")
async def schedule_maintenance(request: Request, body: MaintenanceRequest, user: RequireManager):
    """Schedule a table for maintenance."""
    svc = get_table_enhancements_service()
    from datetime import datetime
    scheduled = None
    if body.scheduled_at:
        try:
            scheduled = datetime.fromisoformat(body.scheduled_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format")

    result = svc.schedule_maintenance(
        table_id=body.table_id,
        reason=body.reason,
        scheduled_at=scheduled,
        estimated_duration_minutes=body.estimated_duration_minutes,
        assigned_to=body.assigned_to,
    )
    return {"success": True, "maintenance": result}


@router.post("/maintenance/{maintenance_id}/complete")
@limiter.limit("20/minute")
async def complete_maintenance(
    request: Request, maintenance_id: int, body: MaintenanceCompleteRequest, user: RequireManager
):
    """Mark maintenance as completed."""
    svc = get_table_enhancements_service()
    result = svc.complete_maintenance(maintenance_id, notes=body.notes)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"success": True, "maintenance": result}


@router.get("/maintenance")
@limiter.limit("30/minute")
async def get_maintenance_history(
    request: Request,
    user: CurrentUser,
    table_id: Optional[int] = None,
    status: Optional[str] = None,
):
    """Get maintenance history."""
    svc = get_table_enhancements_service()
    return {"maintenance": svc.get_maintenance_history(table_id=table_id, status=status)}


# ---- Guest Waitlist Display ----

@router.post("/waitlist-display")
@limiter.limit("60/minute")
async def get_waitlist_display(request: Request, entries: List[Dict[str, Any]]):
    """Generate guest-facing waitlist display data (public endpoint)."""
    svc = get_table_enhancements_service()
    return svc.get_guest_waitlist_display(entries)


@router.post("/waitlist-display/position")
@limiter.limit("60/minute")
async def get_guest_position(request: Request, entries: List[Dict[str, Any]], guest_id: int):
    """Get a specific guest's position in the waitlist."""
    svc = get_table_enhancements_service()
    result = svc.get_guest_position(entries, guest_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---- Turn Time Alerts ----

@router.post("/turn-alerts")
@limiter.limit("30/minute")
async def check_turn_alerts(
    request: Request, active_turns: List[Dict[str, Any]], config: Optional[TurnAlertConfig] = None, user: CurrentUser = None
):
    """Check active table turns for slow tables exceeding threshold."""
    svc = get_table_enhancements_service()
    threshold = config.threshold_minutes if config else 90
    alerts = svc.check_turn_time_alerts(active_turns, threshold_minutes=threshold)
    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "threshold_minutes": threshold,
    }


# ---- Server Load Balancing ----

@router.post("/load-balance")
@limiter.limit("30/minute")
async def calculate_workload(request: Request, body: LoadBalanceRequest, user: RequireManager):
    """Calculate server workloads for load balancing."""
    svc = get_table_enhancements_service()
    workloads = svc.calculate_server_workload(body.servers, body.table_assignments)
    return {"workloads": workloads}


@router.post("/load-balance/suggest")
@limiter.limit("30/minute")
async def suggest_server(request: Request, body: ServerSuggestionRequest, user: RequireManager):
    """Suggest the best server for a new table seating."""
    svc = get_table_enhancements_service()
    suggestion = svc.suggest_server_for_table(
        body.table, body.servers, body.table_assignments,
    )
    if "error" in suggestion:
        raise HTTPException(status_code=400, detail=suggestion["error"])
    return {"suggestion": suggestion}


# ---- Smart Party Matching ----

@router.post("/match-table")
@limiter.limit("30/minute")
async def match_party_to_table(
    request: Request,
    body: PartyMatchRequest,
    available_tables: List[Dict[str, Any]] = [],
    user: CurrentUser = None,
):
    """Smart match a party to the best available table."""
    svc = get_table_enhancements_service()
    matches = svc.match_party_to_table(
        party_size=body.party_size,
        available_tables=available_tables,
        preferences=body.preferences,
    )
    return {
        "matches": matches,
        "party_size": body.party_size,
        "preferences": body.preferences,
    }
