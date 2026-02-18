"""
Floor Plan API Endpoints
Interactive floor plan management with drag-and-drop table positioning
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.core.rate_limit import limiter
from app.models import (
    StaffUser, Table, Order, FloorPlan,
    FloorPlanTablePosition, FloorPlanArea, OrderStatus
)
from app.schemas import (
    FloorPlanCreate, FloorPlanResponse,
    FloorPlanTablePosition as FloorPlanTablePositionSchema,
    FloorPlanAreaCreate
)

router = APIRouter()


@router.post("/", response_model=FloorPlanResponse)
@limiter.limit("30/minute")
async def create_floor_plan(
    request: Request,
    data: FloorPlanCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):

    """Create a new floor plan"""
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Deactivate other floor plans for this venue
    db.query(FloorPlan).filter(
        FloorPlan.venue_id == current_user.venue_id
    ).update({"is_active": False})

    floor_plan = FloorPlan(
        venue_id=current_user.venue_id,
        name=data.name,
        width=data.width,
        height=data.height,
        background_image=data.background_image,
        is_active=True
    )
    db.add(floor_plan)
    db.flush()

    # Add table positions
    for table_pos in data.tables:
        # Verify table exists and belongs to venue
        table = db.query(Table).filter(
            Table.id == table_pos.table_id,
            Table.location_id == current_user.venue_id
        ).first()
        if not table:
            continue

        position = FloorPlanTablePosition(
            floor_plan_id=floor_plan.id,
            table_id=table_pos.table_id,
            x=table_pos.x,
            y=table_pos.y,
            width=table_pos.width,
            height=table_pos.height,
            rotation=table_pos.rotation,
            shape=table_pos.shape
        )
        db.add(position)

    # Add areas
    for area_data in data.areas:
        area = FloorPlanArea(
            floor_plan_id=floor_plan.id,
            name=area_data.name,
            color=area_data.color,
            x=area_data.x,
            y=area_data.y,
            width=area_data.width,
            height=area_data.height
        )
        db.add(area)

    db.commit()
    db.refresh(floor_plan)

    return _format_floor_plan_response(floor_plan, db, current_user.venue_id)


@router.get("/", response_model=List[FloorPlanResponse])
@limiter.limit("60/minute")
async def list_floor_plans(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all floor plans for the venue"""
    floor_plans = db.query(FloorPlan).filter(
        FloorPlan.venue_id == current_user.venue_id
    ).order_by(FloorPlan.is_active.desc(), FloorPlan.created_at.desc()).all()

    return [_format_floor_plan_response(fp, db, current_user.venue_id) for fp in floor_plans]


@router.get("/active", response_model=FloorPlanResponse)
@limiter.limit("60/minute")
async def get_active_floor_plan(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get the active floor plan with real-time table status"""
    floor_plan = db.query(FloorPlan).filter(
        FloorPlan.venue_id == current_user.venue_id,
        FloorPlan.is_active == True
    ).first()

    if not floor_plan:
        return {"id": 0, "name": "Default", "venue_id": current_user.venue_id,
                "is_active": False, "tables": [], "areas": [],
                "table_positions": [], "layout_data": {"tables": []}}

    return _format_floor_plan_response(floor_plan, db, current_user.venue_id, include_status=True)


@router.get("/{floor_plan_id}", response_model=FloorPlanResponse)
@limiter.limit("60/minute")
async def get_floor_plan(
    request: Request,
    floor_plan_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get floor plan details"""
    floor_plan = db.query(FloorPlan).filter(
        FloorPlan.id == floor_plan_id,
        FloorPlan.venue_id == current_user.venue_id
    ).first()

    if not floor_plan:
        raise HTTPException(status_code=404, detail="Floor plan not found")

    return _format_floor_plan_response(floor_plan, db, current_user.venue_id)


@router.put("/{floor_plan_id}", response_model=FloorPlanResponse)
@limiter.limit("30/minute")
async def update_floor_plan(
    request: Request,
    floor_plan_id: int,
    data: FloorPlanCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update a floor plan"""
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    floor_plan = db.query(FloorPlan).filter(
        FloorPlan.id == floor_plan_id,
        FloorPlan.venue_id == current_user.venue_id
    ).first()

    if not floor_plan:
        raise HTTPException(status_code=404, detail="Floor plan not found")

    # Update basic info
    floor_plan.name = data.name
    floor_plan.width = data.width
    floor_plan.height = data.height
    floor_plan.background_image = data.background_image

    # Delete existing positions and areas
    db.query(FloorPlanTablePosition).filter(
        FloorPlanTablePosition.floor_plan_id == floor_plan.id
    ).delete()
    db.query(FloorPlanArea).filter(
        FloorPlanArea.floor_plan_id == floor_plan.id
    ).delete()

    # Add new table positions
    for table_pos in data.tables:
        table = db.query(Table).filter(
            Table.id == table_pos.table_id,
            Table.location_id == current_user.venue_id
        ).first()
        if not table:
            continue

        position = FloorPlanTablePosition(
            floor_plan_id=floor_plan.id,
            table_id=table_pos.table_id,
            x=table_pos.x,
            y=table_pos.y,
            width=table_pos.width,
            height=table_pos.height,
            rotation=table_pos.rotation,
            shape=table_pos.shape
        )
        db.add(position)

    # Add new areas
    for area_data in data.areas:
        area = FloorPlanArea(
            floor_plan_id=floor_plan.id,
            name=area_data.name,
            color=area_data.color,
            x=area_data.x,
            y=area_data.y,
            width=area_data.width,
            height=area_data.height
        )
        db.add(area)

    db.commit()
    db.refresh(floor_plan)

    return _format_floor_plan_response(floor_plan, db, current_user.venue_id)


@router.put("/{floor_plan_id}/table/{table_id}/position")
@limiter.limit("30/minute")
async def update_table_position(
    request: Request,
    floor_plan_id: int,
    table_id: int,
    position: FloorPlanTablePositionSchema,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update a single table's position (for drag-and-drop)"""
    floor_plan = db.query(FloorPlan).filter(
        FloorPlan.id == floor_plan_id,
        FloorPlan.venue_id == current_user.venue_id
    ).first()

    if not floor_plan:
        raise HTTPException(status_code=404, detail="Floor plan not found")

    table_position = db.query(FloorPlanTablePosition).filter(
        FloorPlanTablePosition.floor_plan_id == floor_plan_id,
        FloorPlanTablePosition.table_id == table_id
    ).first()

    if table_position:
        # Update existing
        table_position.x = position.x
        table_position.y = position.y
        table_position.width = position.width
        table_position.height = position.height
        table_position.rotation = position.rotation
        table_position.shape = position.shape
    else:
        # Create new
        table_position = FloorPlanTablePosition(
            floor_plan_id=floor_plan_id,
            table_id=table_id,
            x=position.x,
            y=position.y,
            width=position.width,
            height=position.height,
            rotation=position.rotation,
            shape=position.shape
        )
        db.add(table_position)

    db.commit()

    return {"message": "Table position updated"}


@router.put("/{floor_plan_id}/activate")
@limiter.limit("30/minute")
async def activate_floor_plan(
    request: Request,
    floor_plan_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Set a floor plan as the active one"""
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    floor_plan = db.query(FloorPlan).filter(
        FloorPlan.id == floor_plan_id,
        FloorPlan.venue_id == current_user.venue_id
    ).first()

    if not floor_plan:
        raise HTTPException(status_code=404, detail="Floor plan not found")

    # Deactivate all others
    db.query(FloorPlan).filter(
        FloorPlan.venue_id == current_user.venue_id
    ).update({"is_active": False})

    floor_plan.is_active = True
    db.commit()

    return {"message": "Floor plan activated"}


@router.delete("/{floor_plan_id}")
@limiter.limit("30/minute")
async def delete_floor_plan(
    request: Request,
    floor_plan_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Delete a floor plan"""
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    floor_plan = db.query(FloorPlan).filter(
        FloorPlan.id == floor_plan_id,
        FloorPlan.venue_id == current_user.venue_id
    ).first()

    if not floor_plan:
        raise HTTPException(status_code=404, detail="Floor plan not found")

    if floor_plan.is_active:
        raise HTTPException(status_code=400, detail="Cannot delete active floor plan")

    db.delete(floor_plan)
    db.commit()

    return {"message": "Floor plan deleted"}


@router.get("/tables/status")
@limiter.limit("60/minute")
async def get_table_statuses(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get real-time status of all tables"""
    tables = db.query(Table).filter(
        Table.location_id == current_user.venue_id
    ).all()

    statuses = []
    for table in tables:
        # Check for active orders
        active_orders = db.query(Order).filter(
            Order.table_id == table.id,
            Order.status.in_([
                OrderStatus.NEW, OrderStatus.ACCEPTED,
                OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED
            ])
        ).all()

        # Determine status
        if not active_orders:
            status = "available"
        elif any(o.payment_status == "pending" for o in active_orders):
            status = "occupied"
        else:
            status = "paid"

        # Calculate total for occupied tables
        total = sum(o.total or 0 for o in active_orders)

        statuses.append({
            "table_id": table.id,
            "table_number": table.number,
            "seats": table.seats,
            "status": status,
            "order_count": len(active_orders),
            "total": round(total, 2),
            "oldest_order_time": min(o.created_at for o in active_orders).isoformat() if active_orders else None
        })

    return statuses


def _format_floor_plan_response(
    floor_plan: FloorPlan,
    db: Session,
    venue_id: int,
    include_status: bool = False
) -> FloorPlanResponse:
    """Format floor plan for response"""
    # Get table positions
    tables = []
    for pos in floor_plan.table_positions:
        table_data = FloorPlanTablePositionSchema(
            table_id=pos.table_id,
            x=pos.x,
            y=pos.y,
            width=pos.width,
            height=pos.height,
            rotation=pos.rotation,
            shape=pos.shape
        )

        if include_status:
            # Add real-time status
            active_orders = db.query(Order).filter(
                Order.table_id == pos.table_id,
                Order.status.in_([
                    OrderStatus.NEW, OrderStatus.ACCEPTED,
                    OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.SERVED
                ])
            ).all()

            table = pos.table
            table_data_dict = table_data.model_dump()
            table_data_dict["table_number"] = table.number if table else "?"
            table_data_dict["seats"] = table.seats if table else 0
            table_data_dict["status"] = "occupied" if active_orders else "available"
            table_data_dict["order_count"] = len(active_orders)
            table_data_dict["total"] = sum(o.total or 0 for o in active_orders)
            tables.append(table_data_dict)
        else:
            tables.append(table_data)

    # Get areas
    areas = [
        FloorPlanAreaCreate(
            name=area.name,
            color=area.color,
            x=area.x,
            y=area.y,
            width=area.width,
            height=area.height
        )
        for area in floor_plan.areas
    ]

    return FloorPlanResponse(
        id=floor_plan.id,
        name=floor_plan.name,
        venue_id=floor_plan.venue_id,
        width=floor_plan.width,
        height=floor_plan.height,
        background_image=floor_plan.background_image,
        tables=tables,
        areas=areas,
        created_at=floor_plan.created_at,
        updated_at=floor_plan.updated_at
    )
