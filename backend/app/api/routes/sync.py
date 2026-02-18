"""Sync routes for mobile offline-first synchronization."""


from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, Request

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
from app.core.rate_limit import limiter

router = APIRouter()


@router.get("/")
@limiter.limit("60/minute")
def get_sync_root(request: Request, db: DbSession):
    """Sync status overview."""
    return get_sync_changes(request=request, db=db, since=None)


@router.get("/changes")
@limiter.limit("60/minute")
def get_sync_changes(
    request: Request,
    db: DbSession,
    since: Optional[datetime] = Query(None, description="Get changes since this timestamp"),
):
    """Get pending sync changes for mobile offline mode."""
    from app.models.restaurant import MenuItem, Table

    # Apply since-filter when a timestamp is provided
    product_q = db.query(Product)
    menu_q = db.query(MenuItem)
    table_q = db.query(Table)
    supplier_q = db.query(Supplier)

    if since:
        product_q = product_q.filter(Product.updated_at > since)
        menu_q = menu_q.filter(MenuItem.updated_at > since)
        table_q = table_q.filter(Table.updated_at > since)
        supplier_q = supplier_q.filter(Supplier.updated_at > since)

    return {
        "has_changes": True,
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "changes": {
            "products": product_q.count(),
            "menu_items": menu_q.count(),
            "tables": table_q.count(),
            "suppliers": supplier_q.count(),
        },
        "pending_uploads": 0,
    }


@router.get("/pull", response_model=SyncPullResponse)
@limiter.limit("60/minute")
def sync_pull(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    since: Optional[datetime] = Query(None, description="Get changes since this timestamp"),
):
    """
    Pull master data updates from server.

    Returns products, suppliers, locations, and stock levels
    that have been updated since the given timestamp.
    """
    # Get updated products (filter by updated_at via TimestampMixin)
    products_query = db.query(Product)
    if since:
        products_query = products_query.filter(Product.updated_at > since)
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
            updated_at=p.updated_at if hasattr(p, 'updated_at') else None,
        )
        for p in products_query.all()
    ]

    # Get updated suppliers (filter by updated_at via TimestampMixin)
    suppliers_query = db.query(Supplier)
    if since:
        suppliers_query = suppliers_query.filter(Supplier.updated_at > since)
    suppliers = [
        SyncSupplierData(
            id=s.id,
            name=s.name,
            contact_phone=s.contact_phone,
            contact_email=s.contact_email,
            updated_at=s.updated_at if hasattr(s, 'updated_at') else None,
        )
        for s in suppliers_query.all()
    ]

    # Get updated locations (filter by updated_at via TimestampMixin)
    locations_query = db.query(Location)
    if since:
        locations_query = locations_query.filter(Location.updated_at > since)
    locations = [
        SyncLocationData(
            id=l.id,
            name=l.name,
            is_default=l.is_default,
            active=l.active,
            updated_at=l.updated_at if hasattr(l, 'updated_at') else None,
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
@limiter.limit("30/minute")
def sync_push(
    request: Request,
    body: SyncPushRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Push inventory sessions from mobile to server.

    Accepts sessions with their lines created offline.
    Returns ID mappings for local IDs to server IDs.
    Detects conflicts when a session with the same location + started_at already exists.
    """
    sessions_created = 0
    lines_created = 0
    conflicts = []
    id_mappings = {}

    for session_data in body.sessions:
        # Conflict detection: check for duplicate by location_id + started_at
        existing = db.query(InventorySession).filter(
            InventorySession.location_id == session_data.location_id,
            InventorySession.started_at == session_data.started_at,
        ).first()

        if existing:
            conflicts.append({
                "local_id": session_data.local_id,
                "server_id": existing.id,
                "reason": "duplicate_session",
                "message": f"Session already exists for location {session_data.location_id} at {session_data.started_at}",
            })
            id_mappings[session_data.local_id] = existing.id
            continue

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
