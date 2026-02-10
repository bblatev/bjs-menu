"""Warehouse management API routes."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_

from app.db.session import DbSession
from app.models.operations import Warehouse as WarehouseModel, WarehouseTransfer

router = APIRouter()


# --------------- Pydantic Schemas ---------------


class Warehouse(BaseModel):
    id: str
    name: str
    code: str
    address: str
    type: str  # main, satellite, cold_storage
    capacity: int
    utilization_pct: float
    manager: str
    active: bool = True


class StockLevel(BaseModel):
    ingredient_id: str
    ingredient_name: str
    category: str
    quantity: float
    unit: str
    par_level: float
    reorder_point: float
    last_count: str
    status: str  # ok, low, critical, over


class Transfer(BaseModel):
    id: str
    from_warehouse: str
    to_warehouse: str
    status: str  # pending, in_transit, completed, cancelled
    items_count: int
    total_value: float
    created_by: str
    created_at: str
    completed_at: Optional[str] = None


class TransferCreate(BaseModel):
    from_warehouse: str
    to_warehouse: str
    status: str = "pending"
    items_count: int = 0
    total_value: float = 0.0
    created_by: str = ""
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: float = 0
    notes: Optional[str] = None


class WarehouseActivity(BaseModel):
    id: str
    warehouse_id: str
    warehouse_name: str
    activity_type: str  # receive, transfer_in, transfer_out, adjustment, count
    description: str
    quantity_change: float
    user: str
    timestamp: str


# --------------- Helper Functions ---------------


def _warehouse_type_to_code(wh: WarehouseModel) -> str:
    """Derive a short code from warehouse name."""
    if wh.name:
        parts = wh.name.split()
        return "".join(p[0].upper() for p in parts if p)
    return ""


def _warehouse_to_schema(wh: WarehouseModel) -> Warehouse:
    """Convert a Warehouse DB model to the response schema."""
    type_map = {"dry": "main", "cold": "cold_storage", "frozen": "cold_storage", "bar": "satellite"}
    return Warehouse(
        id=str(wh.id),
        name=wh.name or "",
        code=_warehouse_type_to_code(wh),
        address=wh.address or "",
        type=type_map.get(wh.type, wh.type or "main"),
        capacity=wh.capacity or 0,
        utilization_pct=0.0,
        manager=wh.manager or "",
        active=wh.active if wh.active is not None else True,
    )


def _transfer_to_schema(
    t: WarehouseTransfer,
    from_name: str,
    to_name: str,
) -> Transfer:
    """Convert a WarehouseTransfer DB model to the response schema."""
    return Transfer(
        id=str(t.id),
        from_warehouse=from_name,
        to_warehouse=to_name,
        status=t.status or "pending",
        items_count=1,
        total_value=float(t.quantity or 0),
        created_by=t.created_by or "",
        created_at=t.created_at.isoformat() + "Z" if t.created_at else "",
        completed_at=(t.completed_at.isoformat() + "Z") if t.completed_at else None,
    )


# --------------- Endpoints ---------------


@router.post("/")
async def create_warehouse(data: dict, db: DbSession):
    """Create a new warehouse."""
    wh = WarehouseModel(
        name=data.get("name", ""),
        address=data.get("address", ""),
        type=data.get("type", "dry"),
        capacity=data.get("capacity", 0),
        manager=data.get("manager", ""),
        active=True,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return _warehouse_to_schema(wh)


@router.get("/")
async def get_warehouses(db: DbSession):
    """Get all warehouses."""
    warehouses = db.query(WarehouseModel).all()
    return [_warehouse_to_schema(w) for w in warehouses]


@router.get("/stock-levels/")
async def get_all_stock_levels(db: DbSession, warehouse_id: Optional[str] = None):
    """Get stock levels for all warehouses or a specific one.

    Stock levels are derived from completed transfers into/out of warehouses.
    """
    query = db.query(WarehouseTransfer).filter(
        WarehouseTransfer.status == "completed"
    )
    if warehouse_id:
        wh_id = int(warehouse_id)
        query = query.filter(
            or_(
                WarehouseTransfer.to_warehouse_id == wh_id,
                WarehouseTransfer.from_warehouse_id == wh_id,
            )
        )
    transfers = query.all()

    product_map: dict = {}
    for t in transfers:
        pid = str(t.product_id) if t.product_id else str(t.id)
        if pid not in product_map:
            product_map[pid] = {
                "ingredient_id": pid,
                "ingredient_name": t.product_name or f"Product {pid}",
                "category": "General",
                "quantity": 0.0,
                "unit": "units",
                "par_level": 0.0,
                "reorder_point": 0.0,
                "last_count": t.created_at.strftime("%Y-%m-%d") if t.created_at else "",
            }
        qty = float(t.quantity or 0)
        if warehouse_id:
            wh_id = int(warehouse_id)
            if t.to_warehouse_id == wh_id:
                product_map[pid]["quantity"] += qty
            if t.from_warehouse_id == wh_id:
                product_map[pid]["quantity"] -= qty
        else:
            product_map[pid]["quantity"] += qty
        if t.created_at:
            product_map[pid]["last_count"] = t.created_at.strftime("%Y-%m-%d")

    result = []
    for data in product_map.values():
        q = data["quantity"]
        par = data["par_level"]
        reorder = data["reorder_point"]
        if par > 0 and q < reorder:
            status = "critical" if q <= 0 else "low"
        elif par > 0 and q > par:
            status = "over"
        else:
            status = "ok"
        result.append(
            StockLevel(
                ingredient_id=data["ingredient_id"],
                ingredient_name=data["ingredient_name"],
                category=data["category"],
                quantity=data["quantity"],
                unit=data["unit"],
                par_level=data["par_level"],
                reorder_point=data["reorder_point"],
                last_count=data["last_count"],
                status=status,
            )
        )
    return result


@router.get("/stock-levels/{warehouse_id}")
async def get_stock_levels(warehouse_id: str, db: DbSession):
    """Get stock levels for a warehouse."""
    wh = db.query(WarehouseModel).filter(WarehouseModel.id == int(warehouse_id)).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return await get_all_stock_levels(db=db, warehouse_id=warehouse_id)


@router.get("/transfers/")
async def get_transfers(db: DbSession):
    """Get all transfers."""
    transfers = db.query(WarehouseTransfer).order_by(WarehouseTransfer.created_at.desc()).all()

    # Build warehouse name lookup
    wh_ids = set()
    for t in transfers:
        if t.from_warehouse_id:
            wh_ids.add(t.from_warehouse_id)
        if t.to_warehouse_id:
            wh_ids.add(t.to_warehouse_id)

    wh_names: dict = {}
    if wh_ids:
        warehouses = db.query(WarehouseModel).filter(WarehouseModel.id.in_(wh_ids)).all()
        for w in warehouses:
            wh_names[w.id] = w.name or ""

    return [
        _transfer_to_schema(
            t,
            from_name=wh_names.get(t.from_warehouse_id, ""),
            to_name=wh_names.get(t.to_warehouse_id, ""),
        )
        for t in transfers
    ]


@router.post("/transfers/")
async def create_transfer(transfer: TransferCreate, db: DbSession):
    """Create a transfer."""
    # Resolve warehouse IDs from names or numeric IDs
    from_wh = None
    to_wh = None
    try:
        from_wh = db.query(WarehouseModel).filter(WarehouseModel.id == int(transfer.from_warehouse)).first()
    except (ValueError, TypeError):
        pass
    if not from_wh:
        from_wh = db.query(WarehouseModel).filter(WarehouseModel.name == transfer.from_warehouse).first()
    try:
        to_wh = db.query(WarehouseModel).filter(WarehouseModel.id == int(transfer.to_warehouse)).first()
    except (ValueError, TypeError):
        pass
    if not to_wh:
        to_wh = db.query(WarehouseModel).filter(WarehouseModel.name == transfer.to_warehouse).first()

    db_transfer = WarehouseTransfer(
        from_warehouse_id=from_wh.id if from_wh else None,
        to_warehouse_id=to_wh.id if to_wh else None,
        product_id=transfer.product_id,
        product_name=transfer.product_name or "",
        quantity=transfer.quantity,
        status=transfer.status,
        notes=transfer.notes,
        created_by=transfer.created_by,
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_transfer)
    db.commit()
    db.refresh(db_transfer)
    return {"success": True, "id": str(db_transfer.id)}


@router.put("/transfers/{transfer_id}/submit")
async def submit_transfer(transfer_id: int, db: DbSession):
    """Submit a draft transfer for approval (draft -> pending)."""
    transfer = db.query(WarehouseTransfer).filter(WarehouseTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    transfer.status = "pending"
    db.commit()
    return {"success": True, "id": str(transfer.id), "status": "pending"}


@router.put("/transfers/{transfer_id}/start")
async def start_transfer(transfer_id: int, db: DbSession):
    """Mark a transfer as in transit."""
    transfer = db.query(WarehouseTransfer).filter(WarehouseTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    transfer.status = "in_transit"
    db.commit()
    return {"success": True, "id": str(transfer.id), "status": "in_transit"}


@router.put("/transfers/{transfer_id}/complete")
async def complete_transfer(transfer_id: int, db: DbSession):
    """Mark a transfer as completed."""
    transfer = db.query(WarehouseTransfer).filter(WarehouseTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    transfer.status = "completed"
    transfer.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "id": str(transfer.id), "status": "completed"}


@router.put("/transfers/{transfer_id}/cancel")
async def cancel_transfer(transfer_id: int, db: DbSession):
    """Cancel a transfer."""
    transfer = db.query(WarehouseTransfer).filter(WarehouseTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    transfer.status = "cancelled"
    db.commit()
    return {"success": True, "id": str(transfer.id), "status": "cancelled"}


@router.get("/activities/")
async def get_activities(db: DbSession):
    """Get warehouse activities.

    Activities are derived from warehouse transfers.
    """
    transfers = (
        db.query(WarehouseTransfer)
        .order_by(WarehouseTransfer.created_at.desc())
        .limit(50)
        .all()
    )

    # Build warehouse name lookup
    wh_ids = set()
    for t in transfers:
        if t.from_warehouse_id:
            wh_ids.add(t.from_warehouse_id)
        if t.to_warehouse_id:
            wh_ids.add(t.to_warehouse_id)

    wh_names: dict = {}
    if wh_ids:
        warehouses = db.query(WarehouseModel).filter(WarehouseModel.id.in_(wh_ids)).all()
        for w in warehouses:
            wh_names[w.id] = w.name or ""

    activities = []
    for t in transfers:
        from_name = wh_names.get(t.from_warehouse_id, "Unknown")
        to_name = wh_names.get(t.to_warehouse_id, "Unknown")
        qty = float(t.quantity or 0)
        timestamp = t.created_at.isoformat() + "Z" if t.created_at else ""
        product_desc = t.product_name or f"Product #{t.product_id}" if t.product_id else "items"

        # Activity for the source warehouse (transfer_out)
        if t.from_warehouse_id:
            activities.append(
                WarehouseActivity(
                    id=f"{t.id}-out",
                    warehouse_id=str(t.from_warehouse_id),
                    warehouse_name=from_name,
                    activity_type="transfer_out",
                    description=f"Transfer {product_desc} to {to_name}",
                    quantity_change=-qty,
                    user=t.created_by or "",
                    timestamp=timestamp,
                )
            )

        # Activity for the destination warehouse (transfer_in)
        if t.to_warehouse_id:
            activities.append(
                WarehouseActivity(
                    id=f"{t.id}-in",
                    warehouse_id=str(t.to_warehouse_id),
                    warehouse_name=to_name,
                    activity_type="transfer_in",
                    description=f"Transfer {product_desc} from {from_name}",
                    quantity_change=qty,
                    user=t.created_by or "",
                    timestamp=timestamp,
                )
            )

    return activities
