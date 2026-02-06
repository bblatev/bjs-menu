"""Warehouse management API routes."""

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


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


class WarehouseActivity(BaseModel):
    id: str
    warehouse_id: str
    warehouse_name: str
    activity_type: str  # receive, transfer_in, transfer_out, adjustment, count
    description: str
    quantity_change: float
    user: str
    timestamp: str


@router.get("/")
async def get_warehouses():
    """Get all warehouses."""
    return [
        Warehouse(id="1", name="Main Kitchen", code="MK", address="Main Building", type="main", capacity=500, utilization_pct=72.5, manager="Chef Mike"),
        Warehouse(id="2", name="Bar Storage", code="BS", address="Bar Area", type="satellite", capacity=200, utilization_pct=85.0, manager="Bar Manager"),
        Warehouse(id="3", name="Cold Storage", code="CS", address="Basement", type="cold_storage", capacity=300, utilization_pct=68.0, manager="Chef Mike"),
    ]


@router.get("/stock-levels/")
async def get_all_stock_levels(warehouse_id: Optional[str] = None):
    """Get stock levels for all warehouses or a specific one."""
    return [
        StockLevel(ingredient_id="1", ingredient_name="Tomatoes", category="Produce", quantity=25, unit="kg", par_level=30, reorder_point=10, last_count="2026-02-01", status="ok"),
        StockLevel(ingredient_id="2", ingredient_name="Beef Ribeye", category="Meat", quantity=8, unit="kg", par_level=15, reorder_point=5, last_count="2026-02-01", status="low"),
        StockLevel(ingredient_id="3", ingredient_name="Olive Oil", category="Pantry", quantity=12, unit="L", par_level=10, reorder_point=4, last_count="2026-02-01", status="over"),
        StockLevel(ingredient_id="4", ingredient_name="Mozzarella", category="Dairy", quantity=5, unit="kg", par_level=8, reorder_point=3, last_count="2026-02-01", status="low"),
        StockLevel(ingredient_id="5", ingredient_name="Flour", category="Pantry", quantity=45, unit="kg", par_level=20, reorder_point=10, last_count="2026-02-01", status="over"),
    ]


@router.get("/stock-levels/{warehouse_id}")
async def get_stock_levels(warehouse_id: str):
    """Get stock levels for a warehouse."""
    return [
        StockLevel(ingredient_id="1", ingredient_name="Tomatoes", category="Produce", quantity=25, unit="kg", par_level=30, reorder_point=10, last_count="2026-02-01", status="ok"),
        StockLevel(ingredient_id="2", ingredient_name="Beef Ribeye", category="Meat", quantity=8, unit="kg", par_level=15, reorder_point=5, last_count="2026-02-01", status="low"),
        StockLevel(ingredient_id="3", ingredient_name="Olive Oil", category="Pantry", quantity=12, unit="L", par_level=10, reorder_point=4, last_count="2026-02-01", status="over"),
    ]


@router.get("/transfers/")
async def get_transfers():
    """Get all transfers."""
    return [
        Transfer(id="1", from_warehouse="Main Kitchen", to_warehouse="Bar Storage", status="completed", items_count=5, total_value=250.00, created_by="Manager", created_at="2026-01-30T10:00:00Z", completed_at="2026-01-30T11:00:00Z"),
        Transfer(id="2", from_warehouse="Cold Storage", to_warehouse="Main Kitchen", status="in_transit", items_count=8, total_value=450.00, created_by="Chef Mike", created_at="2026-02-01T09:00:00Z"),
    ]


@router.post("/transfers/")
async def create_transfer(transfer: Transfer):
    """Create a transfer."""
    return {"success": True, "id": "new-id"}


@router.get("/activities/")
async def get_activities():
    """Get warehouse activities."""
    return [
        WarehouseActivity(id="1", warehouse_id="1", warehouse_name="Main Kitchen", activity_type="receive", description="Received PO-2026-004", quantity_change=150, user="Staff", timestamp="2026-02-01T10:00:00Z"),
        WarehouseActivity(id="2", warehouse_id="2", warehouse_name="Bar Storage", activity_type="transfer_in", description="Transfer from Main Kitchen", quantity_change=25, user="Bar Staff", timestamp="2026-01-30T11:00:00Z"),
        WarehouseActivity(id="3", warehouse_id="1", warehouse_name="Main Kitchen", activity_type="adjustment", description="Waste adjustment - spoilage", quantity_change=-5, user="Chef Mike", timestamp="2026-01-29T16:00:00Z"),
    ]
