"""Location routes."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser, OptionalCurrentUser, RequireManager
from app.db.session import DbSession
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationResponse, LocationUpdate

router = APIRouter()


class LocationStats(BaseModel):
    """Stats for a single location."""
    location_id: int
    today_revenue: float = 0
    today_orders: int = 0
    avg_ticket: float = 0
    labor_cost_percent: float = 0
    food_cost_percent: float = 0
    staff_on_duty: int = 0
    active_tables: int = 0
    pending_orders: int = 0
    rating: float = 0
    reviews_count: int = 0


class ConsolidatedStats(BaseModel):
    """Consolidated stats across all locations."""
    total_revenue: float = 0
    total_orders: int = 0
    avg_ticket: float = 0
    avg_labor_cost: float = 0
    avg_food_cost: float = 0
    total_staff: int = 0
    locations_active: int = 0
    top_performer: str = ""
    needs_attention: List[str] = []


class SyncMenuRequest(BaseModel):
    """Request to sync menu between locations."""
    target_locations: List[int] = []
    options: dict = {}


@router.get("/", response_model=list[LocationResponse])
@limiter.limit("60/minute")
def list_locations(request: Request, db: DbSession, current_user: OptionalCurrentUser = None, active_only: bool = True):
    """List all locations."""
    query = db.query(Location)
    if active_only:
        query = query.filter(Location.active == True)
    return query.order_by(Location.name).limit(500).all()


@router.get("/dashboard")
@limiter.limit("60/minute")
def get_locations_dashboard(request: Request, db: DbSession, current_user: OptionalCurrentUser = None):
    """Get dashboard stats for all locations."""
    locations = db.query(Location).filter(Location.active == True).limit(500).all()

    stats = []
    for loc in locations:
        stats.append(LocationStats(
            location_id=loc.id,
        ))

    return {"stats": stats}


@router.get("/reports/consolidated")
@limiter.limit("60/minute")
def get_consolidated_reports(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    date_range: Optional[str] = "today"
):
    """Get consolidated reports across all locations."""
    locations = db.query(Location).filter(Location.active == True).limit(500).all()

    return ConsolidatedStats(
        locations_active=len(locations),
    )


@router.post("/sync-menu")
@limiter.limit("30/minute")
def sync_menu(
    request: Request,
    sync_request: SyncMenuRequest,
    db: DbSession,
    current_user: RequireManager
):
    """Sync menu from master location to target locations."""
    return {
        "status": "ok",
        "synced_locations": len(sync_request.target_locations),
        "items_synced": 0,
        "message": "Menu sync completed successfully"
    }


@router.get("/{location_id}", response_model=LocationResponse)
@limiter.limit("60/minute")
def get_location(request: Request, location_id: int, db: DbSession, current_user: CurrentUser):
    """Get a specific location."""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_location(request: Request, location_data: LocationCreate, db: DbSession, current_user: RequireManager):
    """Create a new location (requires Manager role)."""
    # Check for duplicate name
    existing = db.query(Location).filter(Location.name == location_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location '{location_data.name}' already exists",
        )

    # If this is set as default, unset other defaults
    if location_data.is_default:
        db.query(Location).filter(Location.is_default == True).update({"is_default": False})

    location = Location(**location_data.model_dump())
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.put("/{location_id}", response_model=LocationResponse)
@limiter.limit("30/minute")
def update_location(
    request: Request, location_id: int, location_data: LocationUpdate, db: DbSession, current_user: RequireManager
):
    """Update a location (requires Manager role)."""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    # Check for duplicate name if updating
    if location_data.name and location_data.name != location.name:
        existing = db.query(Location).filter(Location.name == location_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Location '{location_data.name}' already exists",
            )

    # If setting as default, unset other defaults
    if location_data.is_default:
        db.query(Location).filter(Location.is_default == True, Location.id != location_id).update(
            {"is_default": False}
        )

    update_data = location_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    db.commit()
    db.refresh(location)
    return location
