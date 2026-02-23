"""Supplier routes - consolidated from suppliers.py + suppliers_v11.py.

Includes advanced supplier features (contact update, price list items)
merged from enhanced_inventory_endpoints.py.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Request, status
from sqlalchemy import func

from app.core.rbac import RequireManager, CurrentUser, OptionalCurrentUser
from app.db.session import DbSession
from app.models.supplier import Supplier, SupplierDocument
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse
from app.core.rate_limit import limiter

_supplier_logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== CORE CRUD ====================

@router.get("/", response_model=list[SupplierResponse])
@limiter.limit("60/minute")
def list_suppliers(request: Request, db: DbSession, current_user: OptionalCurrentUser = None):
    """List all suppliers."""
    return db.query(Supplier).order_by(Supplier.name).limit(500).all()


@router.get("/performance")
@limiter.limit("60/minute")
def get_supplier_performance(request: Request, db: DbSession, current_user: OptionalCurrentUser = None):
    """Get supplier performance metrics list."""
    suppliers = db.query(Supplier).order_by(Supplier.name).limit(500).all()
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
@limiter.limit("60/minute")
def get_supplier_performance_stats(request: Request, db: DbSession, current_user: OptionalCurrentUser = None):
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
@limiter.limit("60/minute")
def get_expiring_documents(request: Request, db: DbSession):
    """Get documents expiring soon across all suppliers."""
    cutoff = datetime.now(timezone.utc) + timedelta(days=30)
    docs = db.query(SupplierDocument).filter(
        SupplierDocument.expiration_date.isnot(None),
        SupplierDocument.expiration_date <= cutoff,
    ).order_by(SupplierDocument.expiration_date.asc()).limit(500).all()
    return [
        {
            "id": d.id,
            "supplier_id": d.supplier_id,
            "name": d.name,
            "document_type": d.document_type,
            "expiration_date": d.expiration_date.isoformat() if d.expiration_date else None,
            "days_until_expiry": (d.expiration_date - datetime.now(timezone.utc)).days if d.expiration_date else None,
        }
        for d in docs
    ]


@router.get("/documents")
@limiter.limit("60/minute")
def get_all_documents(request: Request, db: DbSession):
    """Get all supplier documents."""
    docs = db.query(SupplierDocument).order_by(SupplierDocument.id.desc()).limit(500).all()
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
@limiter.limit("30/minute")
def create_document(request: Request, db: DbSession, data: dict = Body(...)):
    """Upload/register a document for a supplier."""
    supplier_id = data.get("supplier_id")
    if not supplier_id:
        raise HTTPException(status_code=400, detail="supplier_id required")
    try:
        supplier_id = int(supplier_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="supplier_id must be a number")
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    exp_date = None
    if data.get("expiration_date"):
        try:
            exp_date = datetime.fromisoformat(data["expiration_date"])
        except (ValueError, TypeError):
            pass
    doc = SupplierDocument(
        supplier_id=supplier_id,
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
@limiter.limit("60/minute")
def get_all_contacts(request: Request, db: DbSession):
    """Get all supplier contacts."""
    suppliers = db.query(Supplier).order_by(Supplier.name).limit(500).all()
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
@limiter.limit("30/minute")
def create_contact(request: Request, db: DbSession, data: dict = Body(...)):
    """Add a contact to a supplier. Updates the supplier's contact info."""
    supplier_id = data.get("supplier_id")
    if not supplier_id:
        raise HTTPException(status_code=400, detail="supplier_id required")
    try:
        supplier_id = int(supplier_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="supplier_id must be a number")
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if data.get("phone"):
        supplier.contact_phone = data["phone"]
    if data.get("email"):
        supplier.contact_email = data["email"]
    db.commit()
    return {"success": True, "supplier_id": supplier.id}


# ==================== RATINGS ====================

@router.get("/ratings")
@limiter.limit("60/minute")
def get_all_ratings(request: Request, db: DbSession):
    """Get supplier ratings summary."""
    suppliers = db.query(Supplier).order_by(Supplier.name).limit(500).all()
    return [
        {"supplier_id": s.id, "name": s.name, "overall_rating": 0, "order_count": len(s.purchase_orders) if s.purchase_orders else 0}
        for s in suppliers
    ]


@router.post("/ratings")
@limiter.limit("30/minute")
def create_rating(request: Request, db: DbSession, data: dict = Body(...)):
    """Add a rating for a supplier."""
    supplier_id = data.get("supplier_id")
    if not supplier_id:
        raise HTTPException(status_code=400, detail="supplier_id required")
    try:
        supplier_id = int(supplier_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="supplier_id must be a number")
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    supplier.notes = (supplier.notes or "") + f"\nRating: Q={data.get('quality_score',0)} D={data.get('delivery_score',0)} P={data.get('price_score',0)} - {data.get('notes','')}"
    db.commit()
    return {"success": True, "supplier_id": supplier.id}


# ==================== PRICE LISTS ====================

@router.get("/price-lists")
@limiter.limit("60/minute")
def get_all_price_lists(request: Request, db: DbSession):
    """Get all supplier price lists."""
    from app.models.price_lists import PriceList
    lists = db.query(PriceList).order_by(PriceList.id).limit(500).all()
    return [
        {"id": pl.id, "name": pl.name, "active": pl.is_active if hasattr(pl, 'is_active') else True}
        for pl in lists
    ]


@router.post("/price-lists")
@limiter.limit("30/minute")
def create_price_list(request: Request, db: DbSession, data: dict = Body(...)):
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
@limiter.limit("60/minute")
def get_best_price(request: Request, item_id: int, db: DbSession):
    """Get best price across suppliers for an item."""
    from app.models.invoice import PriceHistory
    histories = db.query(PriceHistory).filter(
        PriceHistory.product_id == item_id
    ).order_by(PriceHistory.price).limit(100).all()
    prices = [
        {"supplier_id": h.supplier_id, "price": float(h.price or 0), "date": h.recorded_at.isoformat() if h.recorded_at else None}
        for h in histories
    ]
    best = prices[0]["price"] if prices else 0
    best_supplier = prices[0]["supplier_id"] if prices else None
    return {"item_id": item_id, "best_price": best, "supplier": best_supplier, "prices": prices}


# ==================== PER-SUPPLIER ENDPOINTS ====================

@router.get("/{supplier_id}/contacts")
@limiter.limit("60/minute")
def get_supplier_contacts(request: Request, supplier_id: int, db: DbSession):
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
@limiter.limit("60/minute")
def get_supplier_price_lists(request: Request, supplier_id: int, db: DbSession):
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
@limiter.limit("60/minute")
def get_supplier_ratings(request: Request, supplier_id: int, db: DbSession):
    """Get ratings for a specific supplier."""
    from app.models.order import PurchaseOrder
    order_count = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.supplier_id == supplier_id
    ).scalar() or 0
    return {"supplier_id": supplier_id, "overall_rating": 0, "order_count": order_count, "reviews": []}


@router.get("/{supplier_id}/documents")
@limiter.limit("60/minute")
def get_supplier_documents(request: Request, supplier_id: int, db: DbSession):
    """Get documents for a specific supplier."""
    docs = db.query(SupplierDocument).filter(
        SupplierDocument.supplier_id == supplier_id
    ).order_by(SupplierDocument.id.desc()).limit(500).all()
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


# ==================== PRICE COMPARISON, SCORECARDS, SUSTAINABILITY, CONTRACTS ====================

@router.get("/price-comparison")
@limiter.limit("60/minute")
def get_price_comparison(request: Request, db: DbSession, product_id: Optional[int] = None):
    """Compare prices across suppliers for products."""
    from app.models.invoice import PriceHistory
    from app.models.product import Product

    query = db.query(PriceHistory)
    if product_id:
        query = query.filter(PriceHistory.product_id == product_id)
    histories = query.order_by(PriceHistory.recorded_at.desc()).limit(500).all()

    # Group by product
    by_product = {}
    for h in histories:
        pid = h.product_id
        if pid not in by_product:
            product = db.query(Product).filter(Product.id == pid).first()
            by_product[pid] = {
                "product_id": pid,
                "product_name": product.name if product else f"Product {pid}",
                "suppliers": [],
            }
        supplier = db.query(Supplier).filter(Supplier.id == h.supplier_id).first()
        by_product[pid]["suppliers"].append({
            "supplier_id": h.supplier_id,
            "supplier_name": supplier.name if supplier else f"Supplier {h.supplier_id}",
            "price": float(h.price or 0),
            "date": h.recorded_at.isoformat() if h.recorded_at else None,
        })

    comparisons = list(by_product.values())
    # Find best price per product
    for comp in comparisons:
        if comp["suppliers"]:
            best = min(comp["suppliers"], key=lambda x: x["price"])
            comp["best_price"] = best["price"]
            comp["best_supplier"] = best["supplier_name"]

    return {"comparisons": comparisons, "total": len(comparisons)}


@router.get("/best-prices")
@limiter.limit("60/minute")
def get_best_prices(request: Request, db: DbSession):
    """Get best available price for each product across all suppliers."""
    from app.models.invoice import PriceHistory
    from app.models.product import Product
    from sqlalchemy import func as sqlfunc

    # Get the minimum price per product
    subquery = db.query(
        PriceHistory.product_id,
        sqlfunc.min(PriceHistory.price).label("best_price"),
    ).group_by(PriceHistory.product_id).subquery()

    results = db.query(
        subquery.c.product_id,
        subquery.c.best_price,
    ).limit(200).all()

    best_prices = []
    for row in results:
        product = db.query(Product).filter(Product.id == row.product_id).first()
        # Find which supplier has this best price
        best_record = db.query(PriceHistory).filter(
            PriceHistory.product_id == row.product_id,
            PriceHistory.price == row.best_price,
        ).first()
        supplier = db.query(Supplier).filter(Supplier.id == best_record.supplier_id).first() if best_record else None
        best_prices.append({
            "product_id": row.product_id,
            "product_name": product.name if product else f"Product {row.product_id}",
            "best_price": float(row.best_price),
            "supplier_id": best_record.supplier_id if best_record else None,
            "supplier_name": supplier.name if supplier else None,
        })

    return {"best_prices": best_prices, "total": len(best_prices)}


@router.get("/scorecards")
@limiter.limit("60/minute")
def get_all_scorecards(request: Request, db: DbSession):
    """Get scorecards for all suppliers."""
    from app.models.order import PurchaseOrder
    suppliers = db.query(Supplier).order_by(Supplier.name).limit(500).all()
    scorecards = []
    for s in suppliers:
        order_count = db.query(func.count(PurchaseOrder.id)).filter(
            PurchaseOrder.supplier_id == s.id
        ).scalar() or 0
        scorecards.append({
            "supplier_id": s.id,
            "supplier_name": s.name,
            "overall_score": 0,
            "quality_score": 0,
            "delivery_score": 0,
            "price_score": 0,
            "communication_score": 0,
            "total_orders": order_count,
            "on_time_delivery_pct": 0,
            "fill_rate_pct": 0,
        })
    return {"scorecards": scorecards, "total": len(scorecards)}


@router.get("/sustainable-sourcing")
@limiter.limit("60/minute")
def get_sustainable_sourcing(request: Request, db: DbSession):
    """Get sustainable sourcing metrics and certifications."""
    suppliers = db.query(Supplier).order_by(Supplier.name).limit(500).all()
    supplier_data = []
    for s in suppliers:
        # Check for sustainability-related documents
        docs = db.query(SupplierDocument).filter(
            SupplierDocument.supplier_id == s.id,
            SupplierDocument.document_type.in_(["organic_cert", "sustainability", "fair_trade", "local_farm"]),
        ).all()
        supplier_data.append({
            "supplier_id": s.id,
            "supplier_name": s.name,
            "certifications": [d.name for d in docs],
            "is_local": False,
            "sustainability_score": len(docs) * 25,
        })
    local_count = 0
    certified_count = len([s for s in supplier_data if s["certifications"]])
    return {
        "suppliers": supplier_data,
        "total_suppliers": len(supplier_data),
        "certified_count": certified_count,
        "local_count": local_count,
        "sustainability_score_avg": round(sum(s["sustainability_score"] for s in supplier_data) / len(supplier_data), 1) if supplier_data else 0,
    }


# ==================== ADVANCED SUPPLIER FEATURES ====================
# (merged from enhanced_inventory_endpoints.py)


@router.put("/contacts/{contact_id}")
@limiter.limit("30/minute")
def update_supplier_contact(
    request: Request,
    contact_id: int,
    data: dict = Body(...),
    db: DbSession = None,
):
    """Update a supplier contact."""
    try:
        from app.models.enhanced_inventory import SupplierContact

        contact = db.query(SupplierContact).filter(SupplierContact.id == contact_id).first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        for key, value in data.items():
            if key != "supplier_id" and hasattr(contact, key):
                setattr(contact, key, value)

        db.commit()
        db.refresh(contact)
        return contact
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        _supplier_logger.error(f"Error updating supplier contact: {e}")
        raise HTTPException(status_code=500, detail="Failed to update supplier contact")


@router.get("/price-lists/{price_list_id}/items")
@limiter.limit("60/minute")
def get_price_list_items(
    request: Request,
    price_list_id: int,
    db: DbSession = None,
):
    """Get items in a price list."""
    try:
        from app.models.enhanced_inventory import SupplierPriceListItem

        return db.query(SupplierPriceListItem).filter(
            SupplierPriceListItem.price_list_id == price_list_id
        ).all()
    except Exception as e:
        _supplier_logger.error(f"Error fetching price list items: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch price list items")


@router.get("/{supplier_id}/scorecard")
@limiter.limit("60/minute")
def get_supplier_scorecard(request: Request, supplier_id: int, db: DbSession):
    """Get performance scorecard for a specific supplier."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    from app.models.order import PurchaseOrder
    order_count = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.supplier_id == supplier_id
    ).scalar() or 0

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier.name,
        "overall_score": 0,
        "quality_score": 0,
        "delivery_score": 0,
        "price_score": 0,
        "communication_score": 0,
        "total_orders": order_count,
        "on_time_delivery_pct": 0,
        "fill_rate_pct": 0,
        "avg_lead_time_days": 0,
        "return_rate_pct": 0,
        "last_review_date": None,
    }


@router.get("/{supplier_id}/contracts")
@limiter.limit("60/minute")
def get_supplier_contracts(request: Request, supplier_id: int, db: DbSession):
    """Get contracts for a specific supplier."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Look for contract-type documents
    docs = db.query(SupplierDocument).filter(
        SupplierDocument.supplier_id == supplier_id,
        SupplierDocument.document_type.in_(["contract", "agreement", "sla"]),
    ).order_by(SupplierDocument.id.desc()).all()

    contracts = [
        {
            "id": d.id,
            "name": d.name,
            "document_type": d.document_type,
            "file_path": d.file_path,
            "expiration_date": d.expiration_date.isoformat() if d.expiration_date else None,
            "notes": d.notes,
            "status": "active" if not d.expiration_date or d.expiration_date > datetime.now(timezone.utc) else "expired",
        }
        for d in docs
    ]
    return {"supplier_id": supplier_id, "contracts": contracts, "total": len(contracts)}


# ==================== SINGLE SUPPLIER (must be last - catches {supplier_id}) ====================

@router.get("/{supplier_id}", response_model=SupplierResponse)
@limiter.limit("60/minute")
def get_supplier(request: Request, supplier_id: int, db: DbSession, current_user: CurrentUser):
    """Get a specific supplier."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier


@router.post("/", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_supplier(request: Request, body: SupplierCreate, db: DbSession, current_user: RequireManager):
    """Create a new supplier (requires Manager role)."""
    supplier = Supplier(**body.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
@limiter.limit("30/minute")
def update_supplier(
    request: Request, supplier_id: int, body: SupplierUpdate, db: DbSession, current_user: RequireManager
):
    """Update a supplier (requires Manager role)."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)
    return supplier
