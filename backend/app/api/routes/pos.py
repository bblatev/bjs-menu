"""POS integration routes - using database for bar tabs."""

import csv
import io
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status

from pydantic import BaseModel

from app.core.file_utils import sanitize_filename
from app.core.rbac import CurrentUser, OptionalCurrentUser, RequireManager
from app.db.session import DbSession
from app.models.location import Location
from app.models.pos import PosRawEvent, PosSalesLine
from app.models.product import Product
from app.models.recipe import Recipe, RecipeLine
from app.models.stock import MovementReason, StockMovement, StockOnHand
from app.models.hardware import BarTab as BarTabModel
from app.schemas.pos import PosConsumeResult, PosImportResult, PosSalesLineResponse
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


class BarTabCreate(BaseModel):
    customer_name: str
    seat_number: Optional[int] = None
    card_on_file: bool = False


class BarTabItemAdd(BaseModel):
    menu_item_id: int
    quantity: int = 1
    notes: Optional[str] = None


@router.get("/status")
@limiter.limit("60/minute")
def get_pos_status(request: Request, db: DbSession):
    """Get POS integration status."""
    # Count sales lines
    total_sales = db.query(PosSalesLine).count()
    unprocessed = db.query(PosSalesLine).filter(PosSalesLine.processed == False).count()

    return {
        "status": "connected",
        "pos_system": None,
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "total_sales_lines": total_sales,
        "unprocessed_lines": unprocessed,
        "features": {
            "real_time_sync": False,
            "csv_import": True,
            "api_integration": True,
        },
    }


@router.get("/menu")
@limiter.limit("60/minute")
def get_pos_menu(request: Request, db: DbSession):
    """Get menu items for POS terminal."""
    # Try MenuItem first, fallback to Product
    from app.models.restaurant import MenuItem
    items = db.query(MenuItem).filter(MenuItem.available == True).all()
    if items:
        return {
            "items": [
                {
                    "id": i.id,
                    "name": i.name,
                    "price": float(i.price) if i.price else 0,
                    "category": i.category or "Other",
                    "available": i.available,
                }
                for i in items
            ]
        }
    # Fallback to products
    products = db.query(Product).all()
    return {
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "price": float(p.unit_cost) if p.unit_cost else 0,
                "category": p.category or "Other",
                "available": True,
            }
            for p in products
        ]
    }


@router.get("/tables")
@limiter.limit("60/minute")
def get_pos_tables(request: Request, db: DbSession):
    """Get table status for POS terminal."""
    from app.models.restaurant import Table
    tables = db.query(Table).all()
    return {
        "tables": [
            {
                "id": t.id,
                "number": t.number,
                "capacity": t.capacity,
                "status": t.status,
                "area": t.area,
            }
            for t in tables
        ]
    }


@router.get("/sales", response_model=List[PosSalesLineResponse])
@limiter.limit("60/minute")
def list_sales_lines(
    request: Request,
    db: DbSession,
    current_user: OptionalCurrentUser = None,
    processed: Optional[bool] = Query(None),
    limit: int = Query(100, le=1000),
):
    """List POS sales lines."""
    query = db.query(PosSalesLine)
    if processed is not None:
        query = query.filter(PosSalesLine.processed == processed)
    return query.order_by(PosSalesLine.ts.desc()).limit(limit).all()


@router.post("/import/csv", response_model=PosImportResult)
@limiter.limit("30/minute")
def import_pos_csv(
    request: Request,
    db: DbSession,
    current_user: RequireManager,
    file: UploadFile = File(...),
    location_id: int = Query(..., description="Location for the sales"),
):
    """
    Import POS sales data from CSV file.

    CSV format: timestamp,item_id,item_name,qty,is_refund
    - timestamp: ISO format datetime
    - item_id: POS system item ID (optional)
    - item_name: Item name as shown in POS
    - qty: Quantity sold (positive number)
    - is_refund: true/false (optional, default false)
    """
    # Validate file extension
    safe_filename = sanitize_filename(file.filename) if file.filename else "upload.csv"
    if not safe_filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a CSV")

    # Verify location exists
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    content = file.file.read().decode("utf-8")

    # Store raw event with sanitized filename
    raw_event = PosRawEvent(
        source="csv",
        payload_json={"filename": safe_filename, "location_id": location_id},
    )
    db.add(raw_event)
    db.flush()

    reader = csv.DictReader(io.StringIO(content))

    imported = 0
    skipped = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            # Parse timestamp
            ts_str = row.get("timestamp", "").strip()
            if not ts_str:
                errors.append(f"Row {row_num}: Missing timestamp")
                skipped += 1
                continue

            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"Row {row_num}: Invalid timestamp format")
                skipped += 1
                continue

            # Parse other fields
            item_id = row.get("item_id", "").strip() or None
            item_name = row.get("item_name", "").strip()
            if not item_name:
                errors.append(f"Row {row_num}: Missing item_name")
                skipped += 1
                continue

            try:
                qty = Decimal(row.get("qty", "1"))
            except Exception as e:
                logger.warning(f"POS import row {row_num}: invalid qty value '{row.get('qty')}': {e}")
                errors.append(f"Row {row_num}: Invalid qty")
                skipped += 1
                continue

            is_refund = row.get("is_refund", "false").lower() in ("true", "1", "yes")

            # Create sales line
            sales_line = PosSalesLine(
                ts=ts,
                pos_item_id=item_id,
                name=item_name,
                qty=qty,
                is_refund=is_refund,
                location_id=location_id,
                raw_event_id=raw_event.id,
            )
            db.add(sales_line)
            imported += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            skipped += 1

    # Mark raw event as processed
    raw_event.processed = True
    db.commit()

    return PosImportResult(
        source="csv",
        rows_imported=imported,
        rows_skipped=skipped,
        errors=errors[:20],  # Limit error messages
    )


@router.post("/consume", response_model=PosConsumeResult)
@limiter.limit("30/minute")
def consume_sales(
    request: Request,
    db: DbSession,
    current_user: RequireManager,
    location_id: Optional[int] = Query(None, description="Process only this location"),
):
    """
    Convert unprocessed POS sales lines to stock movements using recipes/BOM.

    For each sales line:
    1. Find matching recipe by pos_item_id or name
    2. For each recipe line, calculate consumption based on qty sold
    3. Create stock movements (negative for sales, positive for refunds)
    4. Update stock on hand
    5. Mark sales line as processed

    Uses StockDeductionService for consistent stock deduction logic.
    """
    from app.services.stock_deduction_service import StockDeductionService

    # Get unprocessed sales lines
    query = db.query(PosSalesLine).filter(PosSalesLine.processed == False)
    if location_id:
        query = query.filter(PosSalesLine.location_id == location_id)

    sales_lines = query.all()

    processed = 0
    movements_created = 0
    unmatched = []
    errors = []

    stock_service = StockDeductionService(db)

    for sales_line in sales_lines:
        try:
            # Find recipe using the service
            recipe = stock_service.find_recipe_by_pos_data(
                pos_item_id=sales_line.pos_item_id,
                name=sales_line.name
            )

            if not recipe:
                unmatched.append(sales_line.name)
                sales_line.processed = True  # Mark as processed anyway to avoid reprocessing
                continue

            # Deduct stock using the service
            result = stock_service.deduct_for_recipe(
                recipe=recipe,
                quantity=sales_line.qty,
                location_id=sales_line.location_id,
                is_refund=sales_line.is_refund,
                reference_type="pos_sale",
                reference_id=sales_line.id,
                notes=f"POS: {sales_line.name} x {sales_line.qty}",
            )

            movements_created += result.get("movements_created", 0)
            sales_line.processed = True
            processed += 1

        except Exception as e:
            logger.warning(f"Failed to consume POS sales line {sales_line.id}: {e}")
            errors.append(f"Sales line {sales_line.id}: {str(e)}")

    db.commit()

    return PosConsumeResult(
        sales_processed=processed,
        movements_created=movements_created,
        unmatched_items=list(set(unmatched)),  # Deduplicate
        errors=errors[:20],
    )


# ==================== BAR TABS (DATABASE) ====================

@router.get("/bar-tabs")
@limiter.limit("60/minute")
def list_bar_tabs(request: Request, db: DbSession):
    """List all open bar tabs."""
    tabs = db.query(BarTabModel).filter(BarTabModel.status == "open").all()

    tab_list = [{
        "id": tab.id,
        "customer_name": tab.customer_name,
        "seat_number": tab.seat_number,
        "card_on_file": tab.card_on_file,
        "status": tab.status,
        "items": tab.items or [],
        "subtotal": tab.subtotal,
        "tax": tab.tax,
        "total": tab.total,
        "created_at": tab.created_at.isoformat() if tab.created_at else None,
    } for tab in tabs]

    return {
        "tabs": tab_list,
        "total": len(tab_list)
    }


@router.post("/bar-tabs")
@limiter.limit("30/minute")
def create_bar_tab(request: Request, db: DbSession, tab: BarTabCreate):
    """Create a new bar tab."""
    new_tab = BarTabModel(
        customer_name=tab.customer_name,
        seat_number=tab.seat_number,
        card_on_file=tab.card_on_file,
        status="open",
        items=[],
        subtotal=0.0,
        tax=0.0,
        tip=0.0,
        total=0.0,
    )
    db.add(new_tab)
    db.commit()
    db.refresh(new_tab)

    return {"status": "created", "tab": {
        "id": new_tab.id,
        "customer_name": new_tab.customer_name,
        "seat_number": new_tab.seat_number,
        "card_on_file": new_tab.card_on_file,
        "status": new_tab.status,
        "items": new_tab.items or [],
        "subtotal": new_tab.subtotal,
        "tax": new_tab.tax,
        "total": new_tab.total,
        "created_at": new_tab.created_at.isoformat() if new_tab.created_at else None,
    }}


@router.get("/bar-tabs/{tab_id}")
@limiter.limit("60/minute")
def get_bar_tab(request: Request, db: DbSession, tab_id: int):
    """Get a specific bar tab."""
    tab = db.query(BarTabModel).filter(BarTabModel.id == tab_id).first()
    if not tab:
        raise HTTPException(status_code=404, detail="Bar tab not found")

    return {
        "id": tab.id,
        "customer_name": tab.customer_name,
        "seat_number": tab.seat_number,
        "card_on_file": tab.card_on_file,
        "status": tab.status,
        "items": tab.items or [],
        "subtotal": tab.subtotal,
        "tax": tab.tax,
        "total": tab.total,
        "created_at": tab.created_at.isoformat() if tab.created_at else None,
    }


@router.post("/bar-tabs/{tab_id}/items")
@limiter.limit("30/minute")
def add_item_to_tab(request: Request, tab_id: int, item: BarTabItemAdd, db: DbSession):
    """Add item to bar tab."""
    from app.models.restaurant import MenuItem

    tab = db.query(BarTabModel).filter(BarTabModel.id == tab_id).first()
    if not tab:
        raise HTTPException(status_code=404, detail="Bar tab not found")

    menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    item_total = float(menu_item.price) * item.quantity

    # Get current items or initialize empty list
    items = list(tab.items) if tab.items else []
    items.append({
        "menu_item_id": menu_item.id,
        "name": menu_item.name,
        "quantity": item.quantity,
        "price": float(menu_item.price),
        "total": item_total,
        "notes": item.notes,
    })

    # Update tab
    tab.items = items
    tab.subtotal = sum(i["total"] for i in items)
    tab.tax = tab.subtotal * 0.1  # 10% tax
    tab.total = tab.subtotal + tab.tax

    db.commit()
    db.refresh(tab)

    return {"status": "ok", "tab": {
        "id": tab.id,
        "customer_name": tab.customer_name,
        "items": tab.items,
        "subtotal": tab.subtotal,
        "tax": tab.tax,
        "total": tab.total,
    }}


@router.post("/bar-tabs/{tab_id}/close")
@limiter.limit("30/minute")
def close_bar_tab(request: Request, db: DbSession, tab_id: int, payment_method: str = Query("card")):
    """Close a bar tab."""
    tab = db.query(BarTabModel).filter(BarTabModel.id == tab_id).first()
    if not tab:
        raise HTTPException(status_code=404, detail="Bar tab not found")

    tab.status = "closed"
    tab.closed_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "closed", "tab": {
        "id": tab.id,
        "customer_name": tab.customer_name,
        "status": tab.status,
        "total": tab.total,
        "payment_method": payment_method,
        "closed_at": tab.closed_at.isoformat() if tab.closed_at else None,
    }}


@router.delete("/bar-tabs/{tab_id}")
@limiter.limit("30/minute")
def void_bar_tab(request: Request, db: DbSession, tab_id: int, reason: str = Query("voided")):
    """Void/delete a bar tab."""
    tab = db.query(BarTabModel).filter(BarTabModel.id == tab_id).first()
    if not tab:
        raise HTTPException(status_code=404, detail="Bar tab not found")

    tab.status = "void"
    db.commit()

    return {"status": "voided", "tab_id": tab_id, "reason": reason}
