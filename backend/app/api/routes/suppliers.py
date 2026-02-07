"""Supplier routes."""

from fastapi import APIRouter, HTTPException, status

from app.core.rbac import RequireManager, CurrentUser, OptionalCurrentUser
from app.db.session import DbSession
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse

router = APIRouter()


@router.get("/", response_model=list[SupplierResponse])
def list_suppliers(db: DbSession, current_user: OptionalCurrentUser = None):
    """List all suppliers."""
    return db.query(Supplier).order_by(Supplier.name).all()


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int, db: DbSession, current_user: CurrentUser):
    """Get a specific supplier."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier


@router.post("/", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(request: SupplierCreate, db: DbSession, current_user: RequireManager):
    """Create a new supplier (requires Manager role)."""
    supplier = Supplier(**request.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int, request: SupplierUpdate, db: DbSession, current_user: RequireManager
):
    """Update a supplier (requires Manager role)."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/performance/stats")
def get_supplier_performance_stats(db: DbSession, current_user: OptionalCurrentUser = None):
    """Get supplier performance statistics."""
    from sqlalchemy import func
    total = db.query(func.count(Supplier.id)).scalar() or 0
    # Count purchase orders per supplier for basic stats
    from app.models.order import PurchaseOrder
    total_orders = db.query(func.count(PurchaseOrder.id)).scalar() or 0
    return {
        "total_suppliers": total,
        "total_orders": total_orders,
        "avg_lead_time": 0,
        "avg_fill_rate": 0,
        "on_time_delivery_pct": 0,
    }
