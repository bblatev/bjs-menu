"""Supplier routes - consolidated from suppliers.py + suppliers_v11.py."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, status
from sqlalchemy import func

from app.core.rbac import RequireManager, CurrentUser, OptionalCurrentUser
from app.db.session import DbSession
from app.models.supplier import Supplier, SupplierDocument
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse

router = APIRouter()


# ==================== CORE CRUD ====================

@router.get("/", response_model=list[SupplierResponse])
def list_suppliers(db: DbSession, current_user: OptionalCurrentUser = None):
    """List all suppliers."""
    return db.query(Supplier).order_by(Supplier.name).all()


@router.get("/performance")
def get_supplier_performance(db: DbSession, current_user: OptionalCurrentUser = None):
    """Get supplier performance metrics list."""
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return [
        {
            "id": s.id,
            "supplier_name": s.name,
            "on_time_pct": 0,
            "fill_rate_pct": 0,
            "avg_lead_days": 0,
            "total_orders": 0,
            "quality_score": 0,
        }
        for s in suppliers
    ]


@router.get("/performance/stats")
def get_supplier_performance_stats(db: DbSession, current_user: OptionalCurrentUser = None):
    """Get supplier performance statistics."""
    total = db.query(func.count(Supplier.id)).scalar() or 0
    from app.models.order import PurchaseOrder
    total_orders = db.query(func.count(PurchaseOrder.id)).scalar() or 0
    return {
        "total_suppliers": total,
        "total_orders": total_orders,
        "avg_lead_time": 0,
        "avg_fill_rate": 0,
        "on_time_delivery_pct": 0,
    }


# ==================== DOCUMENTS ====================

@router.get("/expiring-documents")
def get_expiring_documents(db: DbSession):
    """Get documents expiring soon across all suppliers."""
    cutoff = datetime.utcnow() + timedelta(days=30)
    docs = db.query(SupplierDocument).filter(
        SupplierDocument.expiration_date.isnot(None),
        SupplierDocument.expiration_date <= cutoff,
    ).order_by(SupplierDocument.expiration_date.asc()).all()
    return [
        {
            "id": d.id,
            "supplier_id": d.supplier_id,
            "name": d.name,
            "document_type": d.document_type,
            "expiration_date": d.expiration_date.isoformat() if d.expiration_date else None,
            "days_until_expiry": (d.expiration_date - datetime.utcnow()).days if d.expiration_date else None,
        }
        for d in docs
    ]


@router.get("/documents")
def get_all_documents(db: DbSession):
    """Get all supplier documents."""
    docs = db.query(SupplierDocument).order_by(SupplierDocument.id.desc()).all()
    return [
        {
            "id": d.id,
            "supplier_id": d.supplier_id,
            "name": d.name,
            "document_type": d.document_type,
            "file_path": d.file_path,
            "expiration_date": d.expiration_date.isoformat() if d.expiration_date else None,
            "notes": d.notes,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.post("/documents")
def create_document(db: DbSession, data: dict = Body(...)):
    """Upload/register a document for a supplier."""
    supplier_id = data.get("supplier_id")
    if not supplier_id:
        return {"error": "supplier_id required"}
    supplier = db.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
    if not supplier:
        return {"error": "Supplier not found"}
    exp_date = None
    if data.get("expiration_date"):
        try:
            exp_date = datetime.fromisoformat(data["expiration_date"])
        except (ValueError, TypeError):
            pass
    doc = SupplierDocument(
        supplier_id=int(supplier_id),
        name=data.get("name", "Untitled"),
        document_type=data.get("document_type", "other"),
        file_path=data.get("file_path"),
        expiration_date=exp_date,
        notes=data.get("notes"),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"success": True, "id": doc.id, "message": "Document registered"}


# ==================== CONTACTS ====================

@router.get("/contacts")
def get_all_contacts(db: DbSession):
    """Get all supplier contacts."""
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return [
        {
            "supplier_id": s.id,
            "name": s.name,
            "phone": s.contact_phone,
            "email": s.contact_email,
            "address": s.address,
        }
        for s in suppliers
        if s.contact_phone or s.contact_email
    ]


@router.post("/contacts")
def create_contact(db: DbSession, data: dict = Body(...)):
    """Add a contact to a supplier. Updates the supplier's contact info."""
    supplier_id = data.get("supplier_id")
    if not supplier_id:
        return {"error": "supplier_id required"}
    supplier = db.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
    if not supplier:
        return {"error": "Supplier not found"}
    if data.get("phone"):
        supplier.contact_phone = data["phone"]
    if data.get("email"):
        supplier.contact_email = data["email"]
    db.commit()
    return {"success": True, "supplier_id": supplier.id}


# ==================== RATINGS ====================

@router.get("/ratings")
def get_all_ratings(db: DbSession):
    """Get supplier ratings summary."""
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return [
        {"supplier_id": s.id, "name": s.name, "overall_rating": 0, "order_count": len(s.purchase_orders) if s.purchase_orders else 0}
        for s in suppliers
    ]


@router.post("/ratings")
def create_rating(db: DbSession, data: dict = Body(...)):
    """Add a rating for a supplier."""
    supplier_id = data.get("supplier_id")
    if not supplier_id:
        return {"error": "supplier_id required"}
    supplier = db.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
    if not supplier:
        return {"error": "Supplier not found"}
    supplier.notes = (supplier.notes or "") + f"\nRating: Q={data.get('quality_score',0)} D={data.get('delivery_score',0)} P={data.get('price_score',0)} - {data.get('notes','')}"
    db.commit()
    return {"success": True, "supplier_id": supplier.id}


# ==================== PRICE LISTS ====================

@router.get("/price-lists")
def get_all_price_lists(db: DbSession):
    """Get all supplier price lists."""
    from app.models.price_lists import PriceList
    lists = db.query(PriceList).order_by(PriceList.id).all()
    return [
        {"id": pl.id, "name": pl.name, "active": pl.is_active if hasattr(pl, 'is_active') else True}
        for pl in lists
    ]


@router.post("/price-lists")
def create_price_list(db: DbSession, data: dict = Body(...)):
    """Create a price list."""
    from app.models.price_lists import PriceList
    name = data.get("name", "")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    code = name.lower().replace(" ", "_").replace("-", "_")
    existing = db.query(PriceList).filter(PriceList.code == code).first()
    if existing:
        code = f"{code}_{data.get('supplier_id', 0)}"
    # Still check uniqueness after adding supplier_id suffix
    existing2 = db.query(PriceList).filter(PriceList.code == code).first()
    if existing2:
        import time
        code = f"{code}_{int(time.time())}"
    pl = PriceList(name=name, code=code)
    db.add(pl)
    db.commit()
    db.refresh(pl)
    return {"success": True, "id": pl.id}


# ==================== BEST PRICE ====================

@router.get("/best-price/{item_id}")
def get_best_price(item_id: str, db: DbSession):
    """Get best price across suppliers for an item."""
    from app.models.invoice import PriceHistory
    histories = db.query(PriceHistory).filter(
        PriceHistory.product_id == int(item_id)
    ).order_by(PriceHistory.price).all()
    prices = [
        {"supplier_id": h.supplier_id, "price": float(h.price or 0), "date": h.recorded_at.isoformat() if h.recorded_at else None}
        for h in histories
    ]
    best = prices[0]["price"] if prices else 0
    best_supplier = prices[0]["supplier_id"] if prices else None
    return {"item_id": item_id, "best_price": best, "supplier": best_supplier, "prices": prices}


# ==================== PER-SUPPLIER ENDPOINTS ====================

@router.get("/{supplier_id}/contacts")
def get_supplier_contacts(supplier_id: int, db: DbSession):
    """Get contacts for a specific supplier."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        return []
    contacts = []
    if supplier.contact_phone or supplier.contact_email:
        contacts.append({
            "name": supplier.name,
            "phone": supplier.contact_phone,
            "email": supplier.contact_email,
            "role": "primary",
        })
    return contacts


@router.get("/{supplier_id}/price-lists")
def get_supplier_price_lists(supplier_id: int, db: DbSession):
    """Get price lists for a specific supplier."""
    from app.models.invoice import PriceHistory
    histories = db.query(PriceHistory).filter(
        PriceHistory.supplier_id == supplier_id
    ).order_by(PriceHistory.recorded_at.desc()).limit(50).all()
    return [
        {
            "product_id": h.product_id,
            "unit_price": float(h.price or 0),
            "date": h.recorded_at.isoformat() if h.recorded_at else None,
        }
        for h in histories
    ]


@router.get("/{supplier_id}/ratings")
def get_supplier_ratings(supplier_id: int, db: DbSession):
    """Get ratings for a specific supplier."""
    from app.models.order import PurchaseOrder
    order_count = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.supplier_id == supplier_id
    ).scalar() or 0
    return {"supplier_id": supplier_id, "overall_rating": 0, "order_count": order_count, "reviews": []}


@router.get("/{supplier_id}/documents")
def get_supplier_documents(supplier_id: int, db: DbSession):
    """Get documents for a specific supplier."""
    docs = db.query(SupplierDocument).filter(
        SupplierDocument.supplier_id == supplier_id
    ).order_by(SupplierDocument.id.desc()).all()
    return [
        {
            "id": d.id,
            "supplier_id": d.supplier_id,
            "name": d.name,
            "document_type": d.document_type,
            "file_path": d.file_path,
            "expiration_date": d.expiration_date.isoformat() if d.expiration_date else None,
            "notes": d.notes,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


# ==================== SINGLE SUPPLIER (must be last - catches {supplier_id}) ====================

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
