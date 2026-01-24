"""Tables management routes - database-backed."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.restaurant import Table as TableModel

router = APIRouter()


class Table(BaseModel):
    """Table response model."""
    id: int
    number: str
    capacity: int
    status: str = "available"
    area: Optional[str] = None

    class Config:
        from_attributes = True


class TableCreate(BaseModel):
    """Create table request."""
    table_number: Optional[str] = None
    number: Optional[str] = None
    capacity: int = 4
    area: Optional[str] = None
    status: str = "available"


class TableUpdate(BaseModel):
    """Update table request."""
    number: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[str] = None
    area: Optional[str] = None


def _init_default_tables(db: DbSession):
    """Initialize default tables if none exist."""
    count = db.query(TableModel).count()
    if count == 0:
        default_tables = [
            {"number": "1", "capacity": 4, "area": "Main Floor"},
            {"number": "2", "capacity": 4, "area": "Main Floor"},
            {"number": "3", "capacity": 2, "area": "Main Floor"},
            {"number": "4", "capacity": 6, "area": "Main Floor"},
            {"number": "5", "capacity": 4, "area": "Main Floor"},
            {"number": "6", "capacity": 8, "area": "Main Floor"},
            {"number": "7", "capacity": 2, "area": "Main Floor"},
            {"number": "8", "capacity": 4, "area": "Main Floor"},
            {"number": "9", "capacity": 4, "area": "Main Floor"},
            {"number": "10", "capacity": 6, "area": "Main Floor"},
            {"number": "Bar 1", "capacity": 2, "area": "Bar Area"},
            {"number": "Bar 2", "capacity": 2, "area": "Bar Area"},
            {"number": "Bar 3", "capacity": 2, "area": "Bar Area"},
            {"number": "Bar 4", "capacity": 2, "area": "Bar Area"},
            {"number": "Patio 1", "capacity": 4, "area": "Patio"},
            {"number": "Patio 2", "capacity": 4, "area": "Patio"},
            {"number": "Patio 3", "capacity": 6, "area": "Patio"},
            {"number": "VIP 1", "capacity": 8, "area": "VIP Section"},
            {"number": "VIP 2", "capacity": 10, "area": "VIP Section"},
            {"number": "Private", "capacity": 12, "area": "VIP Section"},
        ]
        for t in default_tables:
            table = TableModel(
                number=t["number"],
                capacity=t["capacity"],
                area=t["area"],
                status="available",
                token=f"table{t['number'].lower().replace(' ', '')}",
            )
            db.add(table)
        db.commit()


@router.get("/", response_model=List[Table])
def list_tables(
    db: DbSession,
    location_id: Optional[int] = None,
    status: Optional[str] = None,
):
    """List all tables."""
    _init_default_tables(db)

    query = db.query(TableModel)
    if location_id:
        query = query.filter(TableModel.location_id == location_id)
    if status:
        query = query.filter(TableModel.status == status)

    tables = query.all()
    return tables


@router.get("/sections")
def get_table_sections(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get table sections/zones."""
    _init_default_tables(db)

    # Get distinct areas
    tables = db.query(TableModel).all()
    sections = {}
    for table in tables:
        area = table.area or "Main Floor"
        if area not in sections:
            sections[area] = {"id": len(sections) + 1, "name": area, "tables": []}
        sections[area]["tables"].append(table.id)

    return list(sections.values())


@router.get("/summary/stats")
def get_table_stats(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """Get table statistics."""
    _init_default_tables(db)

    query = db.query(TableModel)
    if location_id:
        query = query.filter(TableModel.location_id == location_id)

    tables = query.all()
    total = len(tables)
    occupied = sum(1 for t in tables if t.status == "occupied")
    reserved = sum(1 for t in tables if t.status == "reserved")
    available = sum(1 for t in tables if t.status == "available")
    cleaning = sum(1 for t in tables if t.status == "cleaning")

    return {
        "total_tables": total,
        "occupied": occupied,
        "reserved": reserved,
        "available": available,
        "cleaning": cleaning,
        "occupancy_rate": round(occupied / total * 100, 1) if total > 0 else 0
    }


@router.get("/{table_id}", response_model=Table)
def get_table(
    db: DbSession,
    table_id: int,
):
    """Get a specific table."""
    table = db.query(TableModel).filter(TableModel.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    return table


@router.post("/", response_model=Table)
def create_table(
    db: DbSession,
    table: TableCreate,
):
    """Create a new table."""
    table_number = table.table_number or table.number
    if not table_number:
        # Auto-generate number
        max_id = db.query(TableModel).count() + 1
        table_number = str(max_id)

    new_table = TableModel(
        number=table_number,
        capacity=table.capacity,
        area=table.area,
        status=table.status,
        token=f"table{table_number.lower().replace(' ', '')}",
    )
    db.add(new_table)
    db.commit()
    db.refresh(new_table)
    return new_table


@router.put("/{table_id}", response_model=Table)
def update_table(
    db: DbSession,
    table_id: int,
    table: TableUpdate,
):
    """Update a table."""
    db_table = db.query(TableModel).filter(TableModel.id == table_id).first()
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")

    if table.number is not None:
        db_table.number = table.number
    if table.capacity is not None:
        db_table.capacity = table.capacity
    if table.status is not None:
        db_table.status = table.status
    if table.area is not None:
        db_table.area = table.area

    db_table.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_table)
    return db_table


@router.delete("/{table_id}")
def delete_table(
    db: DbSession,
    table_id: int,
):
    """Delete a table."""
    db_table = db.query(TableModel).filter(TableModel.id == table_id).first()
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")

    db.delete(db_table)
    db.commit()
    return {"status": "deleted", "table_id": table_id}


@router.post("/{table_id}/occupy")
def occupy_table(
    db: DbSession,
    table_id: int,
):
    """Mark table as occupied."""
    db_table = db.query(TableModel).filter(TableModel.id == table_id).first()
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")

    db_table.status = "occupied"
    db_table.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_table)
    return {"status": "ok", "table": {"id": db_table.id, "number": db_table.number, "status": db_table.status}}


@router.post("/{table_id}/free")
def free_table(
    db: DbSession,
    table_id: int,
):
    """Mark table as available."""
    db_table = db.query(TableModel).filter(TableModel.id == table_id).first()
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")

    db_table.status = "available"
    db_table.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_table)
    return {"status": "ok", "table": {"id": db_table.id, "number": db_table.number, "status": db_table.status}}


@router.post("/{table_id}/reserve")
def reserve_table(
    db: DbSession,
    table_id: int,
):
    """Mark table as reserved."""
    db_table = db.query(TableModel).filter(TableModel.id == table_id).first()
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")

    db_table.status = "reserved"
    db_table.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_table)
    return {"status": "ok", "table": {"id": db_table.id, "number": db_table.number, "status": db_table.status}}


@router.post("/{table_id}/cleaning")
def set_table_cleaning(
    db: DbSession,
    table_id: int,
):
    """Mark table as cleaning."""
    db_table = db.query(TableModel).filter(TableModel.id == table_id).first()
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")

    db_table.status = "cleaning"
    db_table.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_table)
    return {"status": "ok", "table": {"id": db_table.id, "number": db_table.number, "status": db_table.status}}
