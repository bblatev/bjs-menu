"""
Table Merge/Split API
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import (
    TableMerge, TableMergeItem, Table, Order, OrderItem, StaffUser
)


router = APIRouter()


# Schemas
class TableMergeCreate(BaseModel):
    primary_table_id: int
    secondary_table_ids: List[int]
    notes: Optional[str] = None


class TableMergeResponse(BaseModel):
    id: int
    venue_id: int
    primary_table_id: int
    merged_at: datetime
    merged_by: Optional[int]
    is_active: bool
    notes: Optional[str]
    secondary_tables: List[int]

    model_config = ConfigDict(from_attributes=True)


class TableSplitRequest(BaseModel):
    table_id: int
    new_table_id: int
    order_item_ids: List[int]


# Merge Tables
@router.post("/", response_model=TableMergeResponse)
@limiter.limit("30/minute")
def merge_tables(
    request: Request,
    data: TableMergeCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Merge multiple tables into one primary table"""
    # Validate primary table
    primary = db.query(Table).filter(
        Table.id == data.primary_table_id,
        Table.venue_id == current_user.venue_id
    ).first()
    if not primary:
        raise HTTPException(status_code=404, detail="Primary table not found")

    # Validate secondary tables
    secondary_tables = db.query(Table).filter(
        Table.id.in_(data.secondary_table_ids),
        Table.venue_id == current_user.venue_id
    ).all()

    if len(secondary_tables) != len(data.secondary_table_ids):
        raise HTTPException(status_code=404, detail="One or more secondary tables not found")

    # Create merge record
    merge = TableMerge(
        venue_id=current_user.venue_id,
        primary_table_id=data.primary_table_id,
        merged_by=current_user.id,
        notes=data.notes,
        is_active=True
    )
    db.add(merge)
    db.flush()

    # Add merge items for each secondary table
    for table in secondary_tables:
        merge_item = TableMergeItem(
            merge_id=merge.id,
            secondary_table_id=table.id
        )
        db.add(merge_item)

        # Move orders from secondary to primary
        orders = db.query(Order).filter(
            Order.table_id == table.id,
            Order.status.in_(["pending", "preparing", "ready"])
        ).all()
        for order in orders:
            order.original_table_id = order.table_id
            order.table_id = data.primary_table_id

        # Mark secondary table as merged
        table.status = "merged"
        table.merged_into = data.primary_table_id

    # Update primary table capacity
    total_capacity = primary.capacity + sum(t.capacity for t in secondary_tables)
    primary.merged_capacity = total_capacity

    db.commit()
    db.refresh(merge)

    return {
        **merge.__dict__,
        "secondary_tables": data.secondary_table_ids
    }


@router.get("/", response_model=List[TableMergeResponse])
@limiter.limit("60/minute")
def list_merges(
    request: Request,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List table merges"""
    query = db.query(TableMerge).filter(TableMerge.venue_id == current_user.venue_id)

    if active_only:
        query = query.filter(TableMerge.is_active == True)

    merges = query.order_by(TableMerge.merged_at.desc()).all()

    result = []
    for merge in merges:
        items = db.query(TableMergeItem).filter(TableMergeItem.merge_id == merge.id).all()
        result.append({
            **merge.__dict__,
            "secondary_tables": [item.secondary_table_id for item in items]
        })

    return result


@router.post("/{merge_id}/unmerge")
@limiter.limit("30/minute")
def unmerge_tables(
    request: Request,
    merge_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Unmerge tables back to separate tables"""
    merge = db.query(TableMerge).filter(
        TableMerge.id == merge_id,
        TableMerge.venue_id == current_user.venue_id,
        TableMerge.is_active == True
    ).first()

    if not merge:
        raise HTTPException(status_code=404, detail="Active merge not found")

    # Get merge items
    items = db.query(TableMergeItem).filter(TableMergeItem.merge_id == merge.id).all()

    # Restore secondary tables
    for item in items:
        table = db.query(Table).filter(Table.id == item.secondary_table_id).first()
        if table:
            table.status = "available"
            table.merged_into = None

    # Reset primary table
    primary = db.query(Table).filter(Table.id == merge.primary_table_id).first()
    if primary:
        primary.merged_capacity = None

    # Mark merge as inactive
    merge.is_active = False
    merge.unmerged_at = datetime.now(timezone.utc)
    merge.unmerged_by = current_user.id

    db.commit()

    return {"message": "Tables unmerged successfully", "merge_id": merge_id}


# Split Orders Between Tables
@router.post("/split-order")
@limiter.limit("30/minute")
def split_order_to_table(
    request: Request,
    data: TableSplitRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Split specific items from one table's order to another table"""
    # Validate tables
    source_table = db.query(Table).filter(
        Table.id == data.table_id,
        Table.venue_id == current_user.venue_id
    ).first()
    target_table = db.query(Table).filter(
        Table.id == data.new_table_id,
        Table.venue_id == current_user.venue_id
    ).first()

    if not source_table or not target_table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Get items to move
    items = db.query(OrderItem).filter(
        OrderItem.id.in_(data.order_item_ids)
    ).all()

    if not items:
        raise HTTPException(status_code=404, detail="Order items not found")

    # Create new order for target table
    new_order = Order(
        venue_id=current_user.venue_id,
        table_id=data.new_table_id,
        staff_user_id=current_user.id,
        status="pending",
        notes=f"Split from table {source_table.table_number}",
        total=0
    )
    db.add(new_order)
    db.flush()

    # Move items to new order
    total = 0
    for item in items:
        original_order_id = item.order_id
        item.order_id = new_order.id
        total += item.unit_price * item.quantity

        # Update original order total
        original_order = db.query(Order).filter(Order.id == original_order_id).first()
        if original_order:
            original_order.total -= item.unit_price * item.quantity

    new_order.total = total

    db.commit()

    return {
        "message": "Items moved to new table",
        "new_order_id": new_order.id,
        "items_moved": len(items),
        "total": total
    }


@router.get("/table/{table_id}/merged-info")
@limiter.limit("60/minute")
def get_merge_info(
    request: Request,
    table_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get merge info for a table"""
    table = db.query(Table).filter(
        Table.id == table_id,
        Table.venue_id == current_user.venue_id
    ).first()

    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    # Check if this table is a primary in a merge
    merge = db.query(TableMerge).filter(
        TableMerge.primary_table_id == table_id,
        TableMerge.is_active == True
    ).first()

    if merge:
        items = db.query(TableMergeItem).filter(TableMergeItem.merge_id == merge.id).all()
        return {
            "is_merged": True,
            "is_primary": True,
            "merge_id": merge.id,
            "secondary_tables": [item.secondary_table_id for item in items],
            "merged_capacity": table.merged_capacity
        }

    # Check if this table is merged into another
    if table.merged_into:
        return {
            "is_merged": True,
            "is_primary": False,
            "merged_into": table.merged_into
        }

    return {"is_merged": False}
