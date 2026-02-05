"""Sync routes for mobile offline-first synchronization."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query

from app.core.rbac import CurrentUser
from app.db.session import DbSession
from app.models.inventory import InventoryLine, InventorySession
from app.models.location import Location
from app.models.product import Product
from app.models.stock import StockOnHand
from app.models.supplier import Supplier
from app.schemas.sync import (
    SyncLocationData,
    SyncProductData,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncStockData,
    SyncSupplierData,
)

router = APIRouter()


@router.get("/changes")
def get_sync_changes(
    db: DbSession,
    since: Optional[datetime] = Query(None, description="Get changes since this timestamp"),
):
    """Get pending sync changes for mobile offline mode."""
    from app.models.restaurant import MenuItem, Table

    # Return summary of changes
    return {
        "has_changes": True,
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "changes": {
            "products": db.query(Product).count(),
            "menu_items": db.query(MenuItem).count(),
            "tables": db.query(Table).count(),
            "suppliers": db.query(Supplier).count(),
        },
        "pending_uploads": 0,
    }


@router.get("/pull", response_model=SyncPullResponse)
def sync_pull(
    db: DbSession,
    current_user: CurrentUser,
    since: Optional[datetime] = Query(None, description="Get changes since this timestamp"),
):
    """
    Pull master data updates from server.

    Returns products, suppliers, locations, and stock levels
    that have been updated since the given timestamp.
    """
    # Get updated products
    products_query = db.query(Product)
    # Note: Product model doesn't have updated_at, so we return all active products
    products = [
        SyncProductData(
            id=p.id,
            name=p.name,
            barcode=p.barcode,
            supplier_id=p.supplier_id,
            pack_size=p.pack_size,
            unit=p.unit,
            min_stock=p.min_stock,
            target_stock=p.target_stock,
            ai_label=p.ai_label,
            active=p.active,
            updated_at=None,
        )
        for p in products_query.all()
    ]

    # Get updated suppliers
    suppliers_query = db.query(Supplier)
    # Note: Supplier model doesn't have updated_at, so we return all suppliers
    suppliers = [
        SyncSupplierData(
            id=s.id,
            name=s.name,
            contact_phone=s.contact_phone,
            contact_email=s.contact_email,
            updated_at=None,
        )
        for s in suppliers_query.all()
    ]

    # Get updated locations
    locations_query = db.query(Location)
    # Note: Location model doesn't have updated_at, so we return all locations
    locations = [
        SyncLocationData(
            id=l.id,
            name=l.name,
            is_default=l.is_default,
            active=l.active,
            updated_at=None,
        )
        for l in locations_query.all()
    ]

    # Get updated stock levels
    stock_query = db.query(StockOnHand)
    if since:
        stock_query = stock_query.filter(StockOnHand.updated_at > since)
    stock = [
        SyncStockData(
            product_id=s.product_id,
            location_id=s.location_id,
            qty=s.qty,
            updated_at=s.updated_at,
        )
        for s in stock_query.all()
    ]

    return SyncPullResponse(
        products=products,
        suppliers=suppliers,
        locations=locations,
        stock=stock,
        server_timestamp=datetime.now(timezone.utc),
    )


@router.post("/push", response_model=SyncPushResponse)
def sync_push(
    request: SyncPushRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Push inventory sessions from mobile to server.

    Accepts sessions with their lines created offline.
    Returns ID mappings for local IDs to server IDs.
    """
    sessions_created = 0
    lines_created = 0
    conflicts = []
    id_mappings = {}

    for session_data in request.sessions:
        # Check for duplicate by local_id (idempotency)
        # In a real implementation, you might store local_id on the server
        # For now, we just create new sessions

        session = InventorySession(
            location_id=session_data.location_id,
            status=session_data.status,
            started_at=session_data.started_at,
            committed_at=session_data.committed_at,
            notes=session_data.notes,
            created_by=current_user.user_id,
        )
        db.add(session)
        db.flush()

        id_mappings[session_data.local_id] = session.id
        sessions_created += 1

        for line_data in session_data.lines:
            line = InventoryLine(
                session_id=session.id,
                product_id=line_data.product_id,
                counted_qty=line_data.counted_qty,
                method=line_data.method,
                confidence=line_data.confidence,
                counted_at=line_data.counted_at,
            )
            db.add(line)
            lines_created += 1

            # Map line local_id if needed
            id_mappings[line_data.local_id] = line.id

    db.commit()

    return SyncPushResponse(
        sessions_created=sessions_created,
        lines_created=lines_created,
        conflicts=conflicts,
        server_timestamp=datetime.now(timezone.utc),
        id_mappings=id_mappings,
    )
