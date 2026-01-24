"""POS integration routes."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.core.rbac import CurrentUser, RequireManager
from app.db.session import DbSession
from app.models.location import Location
from app.models.pos import PosRawEvent, PosSalesLine
from app.models.product import Product
from app.models.recipe import Recipe, RecipeLine
from app.models.stock import MovementReason, StockMovement, StockOnHand
from app.schemas.pos import PosConsumeResult, PosImportResult, PosSalesLineResponse

router = APIRouter()


@router.get("/status")
def get_pos_status(db: DbSession):
    """Get POS integration status."""
    # Count sales lines
    total_sales = db.query(PosSalesLine).count()
    unprocessed = db.query(PosSalesLine).filter(PosSalesLine.processed == False).count()

    return {
        "status": "connected",
        "pos_system": "Generic POS",
        "last_sync": datetime.utcnow().isoformat(),
        "total_sales_lines": total_sales,
        "unprocessed_lines": unprocessed,
        "features": {
            "real_time_sync": False,
            "csv_import": True,
            "api_integration": True,
        },
    }


@router.get("/sales", response_model=List[PosSalesLineResponse])
def list_sales_lines(
    db: DbSession,
    current_user: CurrentUser,
    processed: Optional[bool] = Query(None),
    limit: int = Query(100, le=1000),
):
    """List POS sales lines."""
    query = db.query(PosSalesLine)
    if processed is not None:
        query = query.filter(PosSalesLine.processed == processed)
    return query.order_by(PosSalesLine.ts.desc()).limit(limit).all()


@router.post("/import/csv", response_model=PosImportResult)
def import_pos_csv(
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
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a CSV")

    # Verify location exists
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    content = file.file.read().decode("utf-8")

    # Store raw event
    raw_event = PosRawEvent(
        source="csv",
        payload_json={"filename": file.filename, "location_id": location_id},
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
            except Exception:
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
def consume_sales(
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
    """
    # Get unprocessed sales lines
    query = db.query(PosSalesLine).filter(PosSalesLine.processed == False)
    if location_id:
        query = query.filter(PosSalesLine.location_id == location_id)

    sales_lines = query.all()

    processed = 0
    movements_created = 0
    unmatched = []
    errors = []

    for sales_line in sales_lines:
        try:
            # Find recipe by pos_item_id first, then by name
            recipe = None
            if sales_line.pos_item_id:
                recipe = (
                    db.query(Recipe)
                    .filter(Recipe.pos_item_id == sales_line.pos_item_id)
                    .first()
                )

            if not recipe:
                # Try matching by name (case-insensitive)
                recipe = (
                    db.query(Recipe)
                    .filter(Recipe.name.ilike(sales_line.name))
                    .first()
                )

            if not recipe:
                # Try partial match
                recipe = (
                    db.query(Recipe)
                    .filter(Recipe.pos_item_name.ilike(sales_line.name))
                    .first()
                )

            if not recipe:
                unmatched.append(sales_line.name)
                sales_line.processed = True  # Mark as processed anyway to avoid reprocessing
                continue

            # Calculate consumption for each recipe line
            multiplier = -sales_line.qty if not sales_line.is_refund else sales_line.qty

            for recipe_line in recipe.lines:
                # Calculate qty delta (negative for consumption, positive for refund)
                qty_delta = multiplier * recipe_line.qty

                # Create stock movement
                movement = StockMovement(
                    product_id=recipe_line.product_id,
                    location_id=sales_line.location_id,
                    qty_delta=qty_delta,
                    reason=MovementReason.REFUND.value if sales_line.is_refund else MovementReason.SALE.value,
                    ref_type="pos_sale",
                    ref_id=sales_line.id,
                    notes=f"POS: {sales_line.name} x {sales_line.qty}",
                )
                db.add(movement)
                movements_created += 1

                # Update stock on hand
                stock = (
                    db.query(StockOnHand)
                    .filter(
                        StockOnHand.product_id == recipe_line.product_id,
                        StockOnHand.location_id == sales_line.location_id,
                    )
                    .first()
                )

                if stock:
                    stock.qty += qty_delta
                else:
                    stock = StockOnHand(
                        product_id=recipe_line.product_id,
                        location_id=sales_line.location_id,
                        qty=qty_delta,
                    )
                    db.add(stock)

            sales_line.processed = True
            processed += 1

        except Exception as e:
            errors.append(f"Sales line {sales_line.id}: {str(e)}")

    db.commit()

    return PosConsumeResult(
        sales_processed=processed,
        movements_created=movements_created,
        unmatched_items=list(set(unmatched)),  # Deduplicate
        errors=errors[:20],
    )
