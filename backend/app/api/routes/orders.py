"""Purchase order routes."""

from __future__ import annotations

import io
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse

from app.core.rbac import CurrentUser, RequireManager
from app.db.session import DbSession
from app.models.location import Location
from app.models.order import POStatus, PurchaseOrder, PurchaseOrderLine
from app.models.product import Product
from app.models.stock import StockOnHand
from app.models.supplier import Supplier
from app.schemas.order import (
    CreateOrdersFromSuggestions,
    OrderSuggestion,
    OrderSuggestionsResponse,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
)
from app.services.order_service import generate_pdf, generate_whatsapp_text, generate_xlsx

router = APIRouter()


@router.get("/suggestions", response_model=OrderSuggestionsResponse)
def get_order_suggestions(
    db: DbSession,
    current_user: CurrentUser,
    location_id: int = Query(..., description="Location to check stock for"),
):
    """
    Get order suggestions based on current stock vs target stock.

    Returns products where current stock is below target stock,
    grouped by supplier.
    """
    # Verify location exists
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    # Get all active products with their current stock
    products = db.query(Product).filter(Product.active == True).all()

    suggestions = []
    by_supplier = defaultdict(list)

    for product in products:
        # Get current stock for this location
        stock = (
            db.query(StockOnHand)
            .filter(
                StockOnHand.product_id == product.id,
                StockOnHand.location_id == location_id,
            )
            .first()
        )
        current_qty = stock.qty if stock else Decimal("0")

        # Calculate suggested order quantity
        if current_qty < product.target_stock:
            suggested_qty = product.target_stock - current_qty

            # Get supplier name
            supplier_name = None
            if product.supplier_id:
                supplier = db.query(Supplier).filter(Supplier.id == product.supplier_id).first()
                supplier_name = supplier.name if supplier else None

            suggestion = OrderSuggestion(
                product_id=product.id,
                product_name=product.name,
                barcode=product.barcode,
                supplier_id=product.supplier_id,
                supplier_name=supplier_name,
                current_stock=current_qty,
                min_stock=product.min_stock,
                target_stock=product.target_stock,
                suggested_qty=suggested_qty,
                unit=product.unit,
                pack_size=product.pack_size,
                lead_time_days=product.lead_time_days,
            )
            suggestions.append(suggestion)

            # Group by supplier
            supplier_key = product.supplier_id or 0  # 0 for no supplier
            by_supplier[supplier_key].append(suggestion)

    return OrderSuggestionsResponse(
        location_id=location_id,
        suggestions=suggestions,
        by_supplier=dict(by_supplier),
    )


@router.get("/stats")
def get_order_stats_summary(db: DbSession):
    """Get order statistics."""
    total = db.query(PurchaseOrder).count()
    return {"total_orders": total, "pending": 0, "in_progress": 0, "completed": 0, "total_revenue": 0}


@router.get("/", response_model=List[PurchaseOrderResponse])
def list_orders(
    db: DbSession,
    current_user: CurrentUser,
    supplier_id: Optional[int] = Query(None),
    status_filter: Optional[POStatus] = Query(None, alias="status"),
):
    """List purchase orders with optional filters."""
    query = db.query(PurchaseOrder)
    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)
    if status_filter:
        query = query.filter(PurchaseOrder.status == status_filter)
    return query.order_by(PurchaseOrder.created_at.desc()).all()


@router.get("/{order_id}", response_model=PurchaseOrderResponse)
def get_order(order_id: int, db: DbSession, current_user: CurrentUser):
    """Get a specific purchase order."""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post("/", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(request: PurchaseOrderCreate, db: DbSession, current_user: RequireManager):
    """Create a new purchase order."""
    # Verify supplier and location exist
    supplier = db.query(Supplier).filter(Supplier.id == request.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

    location = db.query(Location).filter(Location.id == request.location_id).first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    # Create order
    order = PurchaseOrder(
        supplier_id=request.supplier_id,
        location_id=request.location_id,
        notes=request.notes,
        created_by=current_user.user_id,
    )
    db.add(order)
    db.flush()

    # Add lines
    for line_data in request.lines:
        # Verify product exists
        product = db.query(Product).filter(Product.id == line_data.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {line_data.product_id} not found",
            )

        line = PurchaseOrderLine(
            po_id=order.id,
            product_id=line_data.product_id,
            qty=line_data.qty,
            unit_cost=line_data.unit_cost or product.cost_price,
        )
        db.add(line)

    db.commit()
    db.refresh(order)
    return order


@router.post("/from-suggestions", response_model=list[PurchaseOrderResponse])
def create_orders_from_suggestions(
    request: CreateOrdersFromSuggestions,
    db: DbSession,
    current_user: RequireManager,
):
    """Create purchase orders from order suggestions."""
    # Get suggestions
    suggestions_response = get_order_suggestions(db=db, current_user=current_user, location_id=request.location_id)

    created_orders = []

    for supplier_id, suggestions in suggestions_response.by_supplier.items():
        if supplier_id == 0:
            continue  # Skip products without supplier

        if request.supplier_ids and supplier_id not in request.supplier_ids:
            continue

        # Create order for this supplier
        order = PurchaseOrder(
            supplier_id=supplier_id,
            location_id=request.location_id,
            created_by=current_user.user_id,
        )
        db.add(order)
        db.flush()

        for suggestion in suggestions:
            line = PurchaseOrderLine(
                po_id=order.id,
                product_id=suggestion.product_id,
                qty=suggestion.suggested_qty,
            )
            db.add(line)

        created_orders.append(order)

    db.commit()

    # Refresh all orders
    for order in created_orders:
        db.refresh(order)

    return created_orders


@router.get("/{order_id}/export/whatsapp")
def export_order_whatsapp(order_id: int, db: DbSession, current_user: CurrentUser):
    """Export purchase order as WhatsApp-ready text."""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    text = generate_whatsapp_text(order, db)
    return {"text": text}


@router.get("/{order_id}/export/pdf")
def export_order_pdf(order_id: int, db: DbSession, current_user: CurrentUser):
    """Export purchase order as PDF."""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    pdf_bytes = generate_pdf(order, db)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=PO-{order.id}.pdf"},
    )


@router.get("/{order_id}/export/xlsx")
def export_order_xlsx(order_id: int, db: DbSession, current_user: CurrentUser):
    """Export purchase order as Excel file."""
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    xlsx_bytes = generate_xlsx(order, db)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=PO-{order.id}.xlsx"},
    )


@router.put("/{order_id}/status")
def update_order_status(
    order_id: int,
    db: DbSession,
    current_user: RequireManager,
    new_status: POStatus = Query(...),
):
    """Update purchase order status. When marking as RECEIVED, stock is added automatically."""
    from app.services.stock_deduction_service import StockDeductionService

    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order.status = new_status
    stock_result = None

    if new_status == POStatus.SENT:
        order.sent_at = datetime.now(timezone.utc)
    elif new_status == POStatus.RECEIVED:
        order.received_at = datetime.now(timezone.utc)

        # Add stock for all PO lines
        stock_service = StockDeductionService(db)
        po_lines = [
            {
                "product_id": line.product_id,
                "received_qty": float(line.qty),
                "unit_cost": float(line.unit_cost) if line.unit_cost else None,
            }
            for line in order.lines
        ]
        stock_result = stock_service.receive_purchase_order(
            po_lines=po_lines,
            location_id=order.location_id,
            po_id=order.id,
            created_by=current_user.user_id,
        )

    db.commit()
    db.refresh(order)

    result = {
        "id": order.id,
        "status": order.status.value,
        "received_at": order.received_at.isoformat() if order.received_at else None,
    }
    if stock_result:
        result["stock_additions"] = stock_result

    return result


# ==================== PARTIAL RECEIVING ====================

from pydantic import BaseModel as PydanticBaseModel


class ReceivingLineItem(PydanticBaseModel):
    product_id: int
    received_qty: float
    unit_cost: Optional[float] = None
    notes: Optional[str] = None
    batch_number: Optional[str] = None
    expiration_date: Optional[str] = None


class ReceivingRequest(PydanticBaseModel):
    lines: List[ReceivingLineItem]
    notes: Optional[str] = None


@router.post("/{order_id}/receive")
def receive_order(
    order_id: int,
    request: ReceivingRequest,
    db: DbSession,
    current_user: RequireManager,
):
    """
    Receive goods from a purchase order (supports partial receiving).

    For each line:
    - Creates StockMovement(reason=PURCHASE)
    - Updates StockOnHand
    - Optionally creates InventoryBatch for shelf-life tracking
    - Updates product cost price

    Supports partial receiving: you can receive some items now and more later.
    """
    from app.services.stock_deduction_service import StockDeductionService
    from app.models.stock import StockMovement, MovementReason, StockOnHand

    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status == POStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot receive a cancelled order")

    stock_service = StockDeductionService(db)
    po_lines = [
        {
            "product_id": line.product_id,
            "received_qty": line.received_qty,
            "unit_cost": line.unit_cost,
        }
        for line in request.lines
    ]
    stock_result = stock_service.receive_purchase_order(
        po_lines=po_lines,
        location_id=order.location_id,
        po_id=order.id,
        created_by=current_user.user_id,
    )

    # Create inventory batches if expiration dates provided
    batches_created = []
    for line in request.lines:
        if line.batch_number or line.expiration_date:
            try:
                from app.models.advanced_features import InventoryBatch
                from datetime import date as date_type

                exp_date = None
                if line.expiration_date:
                    exp_date = datetime.strptime(line.expiration_date, "%Y-%m-%d").date()

                batch = InventoryBatch(
                    product_id=line.product_id,
                    location_id=order.location_id,
                    batch_number=line.batch_number or f"PO{order.id}-{line.product_id}",
                    received_quantity=Decimal(str(line.received_qty)),
                    current_quantity=Decimal(str(line.received_qty)),
                    received_date=datetime.now(timezone.utc).date(),
                    expiration_date=exp_date,
                    unit_cost=Decimal(str(line.unit_cost)) if line.unit_cost else None,
                    is_expired=exp_date < datetime.now(timezone.utc).date() if exp_date else False,
                )
                db.add(batch)
                batches_created.append({
                    "product_id": line.product_id,
                    "batch_number": batch.batch_number,
                    "expiration_date": line.expiration_date,
                })
            except Exception:
                pass  # Batch creation is optional

    # Update PO status to RECEIVED if not already
    if order.status != POStatus.RECEIVED:
        order.status = POStatus.RECEIVED
        order.received_at = datetime.now(timezone.utc)

    if request.notes:
        order.notes = (order.notes or "") + f"\nReceived: {request.notes}"

    db.commit()
    db.refresh(order)

    return {
        "status": "received",
        "po_id": order.id,
        "stock_result": stock_result,
        "batches_created": batches_created,
    }
