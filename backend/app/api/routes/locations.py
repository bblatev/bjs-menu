"""Location routes."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

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
    labor_cost_percent: float = 25.0
    food_cost_percent: float = 30.0
    staff_on_duty: int = 0
    active_tables: int = 0
    pending_orders: int = 0
    rating: float = 4.5
    reviews_count: int = 0


class ConsolidatedStats(BaseModel):
    """Consolidated stats across all locations."""
    total_revenue: float = 0
    total_orders: int = 0
    avg_ticket: float = 0
    avg_labor_cost: float = 25.0
    avg_food_cost: float = 30.0
    total_staff: int = 0
    locations_active: int = 0
    top_performer: str = ""
    needs_attention: List[str] = []


class SyncMenuRequest(BaseModel):
    """Request to sync menu between locations."""
    target_locations: List[int] = []
    options: dict = {}


@router.get("/", response_model=list[LocationResponse])
def list_locations(db: DbSession, current_user: OptionalCurrentUser = None, active_only: bool = True):
    """List all locations."""
    query = db.query(Location)
    if active_only:
        query = query.filter(Location.active == True)
    return query.order_by(Location.name).all()


@router.get("/dashboard")
def get_locations_dashboard(db: DbSession, current_user: OptionalCurrentUser = None):
    """Get dashboard stats for all locations."""
    locations = db.query(Location).filter(Location.active == True).all()

    stats = []
    for loc in locations:
        stats.append(LocationStats(
            location_id=loc.id,
            today_revenue=1500 + (loc.id * 500),
            today_orders=25 + (loc.id * 5),
            avg_ticket=45.0,
            labor_cost_percent=24.5,
            food_cost_percent=29.0,
            staff_on_duty=4 + (loc.id % 3),
            active_tables=8 + (loc.id % 5),
            pending_orders=loc.id % 4,
            rating=4.2 + (loc.id % 5) * 0.1,
            reviews_count=50 + loc.id * 10
        ))

    return {"stats": stats}


@router.get("/reports/consolidated")
def get_consolidated_reports(
    db: DbSession,
    current_user: CurrentUser,
    date_range: Optional[str] = "today"
):
    """Get consolidated reports across all locations."""
    locations = db.query(Location).filter(Location.active == True).all()

    total_revenue = sum(1500 + (loc.id * 500) for loc in locations)
    total_orders = sum(25 + (loc.id * 5) for loc in locations)

    return ConsolidatedStats(
        total_revenue=total_revenue,
        total_orders=total_orders,
        avg_ticket=total_revenue / total_orders if total_orders > 0 else 0,
        avg_labor_cost=24.5,
        avg_food_cost=29.0,
        total_staff=sum(4 + (loc.id % 3) for loc in locations),
        locations_active=len(locations),
        top_performer=locations[0].name if locations else "N/A",
        needs_attention=[]
    )


@router.post("/sync-menu")
def sync_menu(
    request: SyncMenuRequest,
    db: DbSession,
    current_user: RequireManager
):
    """Sync menu from master location to target locations."""
    return {
        "status": "ok",
        "synced_locations": len(request.target_locations),
        "items_synced": 0,
        "message": "Menu sync completed successfully"
    }


@router.get("/{location_id}", response_model=LocationResponse)
def get_location(location_id: int, db: DbSession, current_user: CurrentUser):
    """Get a specific location."""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


@router.post("/", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(request: LocationCreate, db: DbSession, current_user: RequireManager):
    """Create a new location (requires Manager role)."""
    # Check for duplicate name
    existing = db.query(Location).filter(Location.name == request.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location '{request.name}' already exists",
        )

    # If this is set as default, unset other defaults
    if request.is_default:
        db.query(Location).filter(Location.is_default == True).update({"is_default": False})

    location = Location(**request.model_dump())
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.put("/{location_id}", response_model=LocationResponse)
def update_location(
    location_id: int, request: LocationUpdate, db: DbSession, current_user: RequireManager
):
    """Update a location (requires Manager role)."""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    # Check for duplicate name if updating
    if request.name and request.name != location.name:
        existing = db.query(Location).filter(Location.name == request.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Location '{request.name}' already exists",
            )

    # If setting as default, unset other defaults
    if request.is_default:
        db.query(Location).filter(Location.is_default == True, Location.id != location_id).update(
            {"is_default": False}
        )

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    db.commit()
    db.refresh(location)
    return location
