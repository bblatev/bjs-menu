"""Supplier management v11 routes - extended supplier data."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/expiring-documents")
async def get_expiring_documents():
    """Get documents expiring soon across all suppliers."""
    return [
        {"id": "1", "supplier_id": "1", "supplier_name": "Fresh Foods Ltd", "document_type": "health_certificate", "name": "Health Certificate", "expires_at": "2026-03-15", "days_remaining": 37, "status": "expiring_soon"},
        {"id": "2", "supplier_id": "2", "supplier_name": "BG Meats", "document_type": "insurance", "name": "Liability Insurance", "expires_at": "2026-02-28", "days_remaining": 22, "status": "expiring_soon"},
    ]


@router.get("/contacts")
async def get_all_contacts():
    """Get all supplier contacts."""
    return [
        {"id": "1", "supplier_id": "1", "name": "Ivan Petrov", "role": "Sales Manager", "email": "ivan@freshfoods.bg", "phone": "+359 888 111 222"},
        {"id": "2", "supplier_id": "2", "name": "Maria Georgieva", "role": "Account Manager", "email": "maria@bgmeats.bg", "phone": "+359 888 333 444"},
    ]


@router.get("/ratings")
async def get_all_ratings():
    """Get supplier ratings summary."""
    return [
        {"supplier_id": "1", "supplier_name": "Fresh Foods Ltd", "overall_rating": 4.5, "quality": 4.8, "delivery": 4.2, "pricing": 4.5, "total_reviews": 24},
        {"supplier_id": "2", "supplier_name": "BG Meats", "overall_rating": 4.2, "quality": 4.5, "delivery": 3.8, "pricing": 4.3, "total_reviews": 18},
    ]


@router.get("/price-lists")
async def get_all_price_lists():
    """Get all supplier price lists."""
    return [
        {"id": "1", "supplier_id": "1", "supplier_name": "Fresh Foods Ltd", "name": "Q1 2026 Prices", "valid_from": "2026-01-01", "valid_to": "2026-03-31", "items_count": 45, "status": "active"},
        {"id": "2", "supplier_id": "2", "supplier_name": "BG Meats", "name": "February 2026", "valid_from": "2026-02-01", "valid_to": "2026-02-28", "items_count": 22, "status": "active"},
    ]


@router.get("/documents")
async def get_all_documents():
    """Get all supplier documents."""
    return [
        {"id": "1", "supplier_id": "1", "supplier_name": "Fresh Foods Ltd", "type": "contract", "name": "Supply Agreement 2026", "uploaded_at": "2026-01-05", "status": "active"},
        {"id": "2", "supplier_id": "1", "supplier_name": "Fresh Foods Ltd", "type": "health_certificate", "name": "Health Certificate", "uploaded_at": "2025-03-15", "expires_at": "2026-03-15", "status": "active"},
    ]


@router.get("/best-price/{item_id}")
async def get_best_price(item_id: str):
    """Get best price across suppliers for an item."""
    return {"item_id": item_id, "best_price": 0, "supplier": None, "prices": []}


@router.get("/{supplier_id}/contacts")
async def get_supplier_contacts(supplier_id: str):
    """Get contacts for a specific supplier."""
    return []


@router.get("/{supplier_id}/price-lists")
async def get_supplier_price_lists(supplier_id: str):
    """Get price lists for a specific supplier."""
    return []


@router.get("/{supplier_id}/ratings")
async def get_supplier_ratings(supplier_id: str):
    """Get ratings for a specific supplier."""
    return {"supplier_id": supplier_id, "overall_rating": 0, "reviews": []}


@router.get("/{supplier_id}/documents")
async def get_supplier_documents(supplier_id: str):
    """Get documents for a specific supplier."""
    return []
