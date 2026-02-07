"""Supplier management v11 routes - extended supplier data."""

from fastapi import APIRouter

from app.db.session import DbSession
from app.models.supplier import Supplier

router = APIRouter()


@router.get("/expiring-documents")
async def get_expiring_documents(db: DbSession):
    """Get documents expiring soon across all suppliers."""
    # No dedicated document table; return empty until document tracking is added
    return []


@router.get("/contacts")
async def get_all_contacts(db: DbSession):
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


@router.get("/ratings")
async def get_all_ratings(db: DbSession):
    """Get supplier ratings summary."""
    suppliers = db.query(Supplier).order_by(Supplier.name).all()
    return [
        {"supplier_id": s.id, "name": s.name, "overall_rating": 0, "order_count": len(s.purchase_orders) if s.purchase_orders else 0}
        for s in suppliers
    ]


@router.get("/price-lists")
async def get_all_price_lists(db: DbSession):
    """Get all supplier price lists."""
    from app.models.price_lists import PriceList
    lists = db.query(PriceList).order_by(PriceList.id).all()
    return [
        {"id": pl.id, "name": pl.name, "active": pl.is_active if hasattr(pl, 'is_active') else True}
        for pl in lists
    ]


@router.get("/documents")
async def get_all_documents(db: DbSession):
    """Get all supplier documents."""
    return []


@router.get("/best-price/{item_id}")
async def get_best_price(item_id: str, db: DbSession):
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


@router.get("/{supplier_id}/contacts")
async def get_supplier_contacts(supplier_id: str, db: DbSession):
    """Get contacts for a specific supplier."""
    supplier = db.query(Supplier).filter(Supplier.id == int(supplier_id)).first()
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
async def get_supplier_price_lists(supplier_id: str, db: DbSession):
    """Get price lists for a specific supplier."""
    from app.models.invoice import PriceHistory
    histories = db.query(PriceHistory).filter(
        PriceHistory.supplier_id == int(supplier_id)
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
async def get_supplier_ratings(supplier_id: str, db: DbSession):
    """Get ratings for a specific supplier."""
    from app.models.order import PurchaseOrder
    from sqlalchemy import func
    order_count = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.supplier_id == int(supplier_id)
    ).scalar() or 0
    return {"supplier_id": supplier_id, "overall_rating": 0, "order_count": order_count, "reviews": []}


@router.get("/{supplier_id}/documents")
async def get_supplier_documents(supplier_id: str, db: DbSession):
    """Get documents for a specific supplier."""
    return []
