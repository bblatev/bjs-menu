"""Purchase Orders API routes - database-backed."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, model_validator

from app.db.session import DbSession
from app.models.order import PurchaseOrder as PurchaseOrderModel, PurchaseOrderLine, POStatus
from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.location import Location

router = APIRouter()


# --- Pydantic Models ---

class POItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity_ordered: float
    unit: str
    unit_price: float
    total_price: float


class PurchaseOrderResponse(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str
    location_id: int
    location_name: str
    status: str
    total_amount: float
    line_count: int
    items: List[POItemResponse] = []
    created_by: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    sent_at: Optional[str] = None
    received_at: Optional[str] = None


class CreatePORequest(BaseModel):
    supplier_id: int
    location_id: int
    items: Optional[List[dict]] = None  # [{"product_id": 1, "qty": 10, "unit_cost": 3.50}]
    lines: Optional[List[dict]] = None  # Alias for items
    notes: Optional[str] = None

    @model_validator(mode="after")
    def normalize_items(self):
        """Accept both 'items' and 'lines' as the line items field."""
        if not self.items and self.lines:
            self.items = self.lines
        if not self.items:
            self.items = []
        return self


class ReceiveGoodsRequest(BaseModel):
    received_quantities: Optional[dict] = None  # {line_id: qty_received}
    notes: Optional[str] = None


class ReceiveGoodsResponse(BaseModel):
    status: str
    po_id: int
    stock_added: int
    movements_created: int
    items_received: List[dict]


# --- Helpers ---

def _po_to_response(po: PurchaseOrderModel, db) -> dict:
    """Convert a PurchaseOrder model to a response dict."""
    supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
    location = db.query(Location).filter(Location.id == po.location_id).first()
    lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).all()

    items = []
    total = Decimal("0")
    for line in lines:
        product = db.query(Product).filter(Product.id == line.product_id).first()
        line_total = float(line.qty * (line.unit_cost or 0))
        total += line.qty * (line.unit_cost or 0)
        items.append({
            "id": line.id,
            "product_id": line.product_id,
            "product_name": product.name if product else "Unknown",
            "quantity_ordered": float(line.qty),
            "unit": product.unit if product else "pcs",
            "unit_price": float(line.unit_cost or 0),
            "total_price": line_total,
        })

    return {
        "id": po.id,
        "supplier_id": po.supplier_id,
        "supplier_name": supplier.name if supplier else "Unknown",
        "location_id": po.location_id,
        "location_name": location.name if location else "Unknown",
        "status": po.status.value if po.status else "draft",
        "total_amount": float(total),
        "line_count": len(lines),
        "items": items,
        "created_by": po.created_by,
        "notes": po.notes,
        "created_at": po.created_at.isoformat() if po.created_at else None,
        "sent_at": po.sent_at.isoformat() if po.sent_at else None,
        "received_at": po.received_at.isoformat() if po.received_at else None,
    }


# --- API Endpoints ---

@router.get("/")
def get_purchase_orders(
    db: DbSession,
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    limit: int = Query(100, le=500),
):
    """Get all purchase orders."""
    query = db.query(PurchaseOrderModel)
    if status:
        try:
            query = query.filter(PurchaseOrderModel.status == POStatus(status))
        except ValueError:
            pass
    if supplier_id:
        query = query.filter(PurchaseOrderModel.supplier_id == supplier_id)

    pos = query.order_by(PurchaseOrderModel.created_at.desc()).limit(limit).all()
    return [_po_to_response(po, db) for po in pos]


@router.post("/")
def create_purchase_order(db: DbSession, request: CreatePORequest):
    """Create a new purchase order."""
    supplier = db.query(Supplier).filter(Supplier.id == request.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    po = PurchaseOrderModel(
        supplier_id=request.supplier_id,
        location_id=request.location_id,
        status=POStatus.DRAFT,
        notes=request.notes,
    )
    db.add(po)
    db.flush()

    for item in request.items:
        line = PurchaseOrderLine(
            po_id=po.id,
            product_id=item["product_id"],
            qty=Decimal(str(item.get("qty") or item.get("quantity", 0))),
            unit_cost=Decimal(str(item.get("unit_cost") or item.get("unit_price", 0))) if (item.get("unit_cost") or item.get("unit_price")) else None,
        )
        db.add(line)

    db.commit()
    db.refresh(po)
    return _po_to_response(po, db)


@router.get("/approvals/")
def get_approvals(db: DbSession):
    """Get purchase orders pending approval (status=draft or sent)."""
    pending = db.query(PurchaseOrderModel).filter(
        PurchaseOrderModel.status.in_([POStatus.DRAFT, POStatus.SENT])
    ).order_by(PurchaseOrderModel.created_at.desc()).all()

    approvals = []
    for po in pending:
        supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
        lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).all()
        total = sum(float(line.qty * (line.unit_cost or 0)) for line in lines)
        approvals.append({
            "id": po.id,
            "type": "purchase_order",
            "reference_id": str(po.id),
            "reference_number": f"PO-{po.id:04d}",
            "supplier_name": supplier.name if supplier else "Unknown",
            "amount": total,
            "requested_by": f"User #{po.created_by}" if po.created_by else "System",
            "requested_at": po.created_at.isoformat() if po.created_at else None,
            "status": "pending" if po.status == POStatus.DRAFT else "sent",
            "urgency": "medium",
            "notes": po.notes,
        })
    return approvals


@router.get("/grns/")
def get_grns(db: DbSession):
    """Get goods received notes (received purchase orders)."""
    received = db.query(PurchaseOrderModel).filter(
        PurchaseOrderModel.status == POStatus.RECEIVED
    ).order_by(PurchaseOrderModel.received_at.desc()).all()

    grns = []
    for po in received:
        supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
        lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).all()
        items = []
        for line in lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            items.append({
                "id": line.id,
                "po_item_id": str(line.id),
                "ingredient_name": product.name if product else "Unknown",
                "quantity_ordered": float(line.qty),
                "quantity_received": float(line.qty),
                "quantity_accepted": float(line.qty),
                "quantity_rejected": 0,
                "unit": product.unit if product else "pcs",
            })
        grns.append({
            "id": po.id,
            "grn_number": f"GRN-{po.id:04d}",
            "purchase_order_id": str(po.id),
            "po_number": f"PO-{po.id:04d}",
            "supplier_id": str(po.supplier_id),
            "supplier_name": supplier.name if supplier else "Unknown",
            "warehouse_id": str(po.location_id),
            "received_date": po.received_at.strftime("%Y-%m-%d") if po.received_at else None,
            "received_by": None,
            "status": "accepted",
            "items": items,
            "notes": po.notes,
            "created_at": po.received_at.isoformat() if po.received_at else None,
        })
    return grns


@router.get("/invoices/")
def get_invoices(db: DbSession):
    """Get invoices linked to purchase orders (received POs as invoiceable items)."""
    received = db.query(PurchaseOrderModel).filter(
        PurchaseOrderModel.status == POStatus.RECEIVED
    ).order_by(PurchaseOrderModel.received_at.desc()).all()

    invoices = []
    for po in received:
        supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
        lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).all()
        subtotal = sum(float(line.qty * (line.unit_cost or 0)) for line in lines)
        tax = subtotal * 0.2  # 20% VAT
        items = []
        for line in lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            line_total = float(line.qty * (line.unit_cost or 0))
            items.append({
                "id": str(line.id),
                "ingredient_name": product.name if product else "Unknown",
                "quantity_invoiced": float(line.qty),
                "quantity_received": float(line.qty),
                "unit_price_invoiced": float(line.unit_cost or 0),
                "unit_price_ordered": float(line.unit_cost or 0),
                "total_price": line_total,
                "variance_amount": 0,
                "unit": product.unit if product else "pcs",
            })
        invoices.append({
            "id": str(po.id),
            "invoice_number": f"INV-{po.id:04d}",
            "supplier_invoice_number": "",
            "purchase_order_id": str(po.id),
            "po_number": f"PO-{po.id:04d}",
            "grn_id": str(po.id),
            "grn_number": f"GRN-{po.id:04d}",
            "supplier_id": str(po.supplier_id),
            "supplier_name": supplier.name if supplier else "Unknown",
            "invoice_date": po.received_at.strftime("%Y-%m-%d") if po.received_at else None,
            "due_date": "",
            "status": "matched",
            "subtotal": subtotal,
            "tax_amount": round(tax, 2),
            "total_amount": round(subtotal + tax, 2),
            "amount_paid": 0,
            "matching_status": "matched",
            "items": items,
            "created_at": po.received_at.isoformat() if po.received_at else None,
        })
    return invoices


@router.get("/three-way-matches/")
def get_three_way_matches(db: DbSession):
    """Get three-way match data (PO vs received vs invoiced)."""
    pos = db.query(PurchaseOrderModel).order_by(PurchaseOrderModel.created_at.desc()).limit(50).all()

    matches = []
    for po in pos:
        supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
        lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).all()
        po_total = sum(float(line.qty * (line.unit_cost or 0)) for line in lines)

        is_received = po.status == POStatus.RECEIVED
        items = []
        for line in lines:
            product = db.query(Product).filter(Product.id == line.product_id).first()
            items.append({
                "ingredient_name": product.name if product else "Unknown",
                "po_qty": float(line.qty),
                "grn_qty": float(line.qty) if is_received else 0,
                "invoice_qty": float(line.qty) if is_received else 0,
                "po_price": float(line.unit_cost or 0),
                "invoice_price": float(line.unit_cost or 0),
                "qty_variance": 0,
                "price_variance": 0,
            })

        status = "matched" if is_received else ("pending" if po.status != POStatus.CANCELLED else "cancelled")
        matches.append({
            "po_id": str(po.id),
            "po_number": f"PO-{po.id:04d}",
            "grn_id": str(po.id) if is_received else None,
            "grn_number": f"GRN-{po.id:04d}" if is_received else None,
            "invoice_id": str(po.id) if is_received else None,
            "invoice_number": f"INV-{po.id:04d}" if is_received else None,
            "supplier_name": supplier.name if supplier else "Unknown",
            "po_total": po_total,
            "grn_total": po_total if is_received else None,
            "invoice_total": po_total if is_received else None,
            "status": status,
            "quantity_variance": 0,
            "price_variance": 0,
            "items": items,
        })
    return matches


@router.post("/{po_id}/approve")
def approve_purchase_order(db: DbSession, po_id: int):
    """Approve a purchase order (transition from DRAFT to SENT)."""
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status not in (POStatus.DRAFT,):
        raise HTTPException(status_code=400, detail=f"Cannot approve PO in status '{po.status.value}'")
    po.status = POStatus.SENT
    po.sent_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "message": f"Purchase order PO-{po.id:04d} approved and sent"}


@router.post("/{po_id}/reject")
def reject_purchase_order(db: DbSession, po_id: int):
    """Reject/cancel a purchase order."""
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status == POStatus.RECEIVED:
        raise HTTPException(status_code=400, detail="Cannot reject already received PO")
    po.status = POStatus.CANCELLED
    db.commit()
    return {"success": True, "message": f"Purchase order PO-{po.id:04d} rejected"}


@router.post("/approvals/{approval_id}/approve")
def approve_approval(db: DbSession, approval_id: int):
    """Approve an approval request (same as approving the PO)."""
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == approval_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Approval request not found")
    po.status = POStatus.SENT
    po.sent_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "message": f"Approval for PO-{po.id:04d} approved"}


@router.post("/approvals/{approval_id}/reject")
def reject_approval(db: DbSession, approval_id: int):
    """Reject an approval request."""
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == approval_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Approval request not found")
    po.status = POStatus.CANCELLED
    db.commit()
    return {"success": True, "message": f"Approval for PO-{po.id:04d} rejected"}


@router.post("/{po_id}/receive", response_model=ReceiveGoodsResponse)
def receive_purchase_order(
    db: DbSession,
    po_id: int,
    request: ReceiveGoodsRequest = None,
):
    """
    Receive goods from a purchase order.

    Updates PurchaseOrder status to RECEIVED, creates StockMovement records,
    and updates StockOnHand for each product.
    """
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if po.status == POStatus.RECEIVED:
        raise HTTPException(status_code=400, detail="Purchase order already received")
    if po.status == POStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot receive cancelled purchase order")

    lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po_id).all()
    if not lines:
        raise HTTPException(status_code=400, detail="Purchase order has no items")

    items_received = []
    movements_created = 0

    for line in lines:
        qty_to_receive = line.qty
        if request and request.received_quantities:
            qty_to_receive = Decimal(str(request.received_quantities.get(str(line.id), line.qty)))
        if qty_to_receive <= 0:
            continue

        stock = db.query(StockOnHand).filter(
            StockOnHand.product_id == line.product_id,
            StockOnHand.location_id == po.location_id
        ).first()
        if not stock:
            stock = StockOnHand(product_id=line.product_id, location_id=po.location_id, qty=Decimal("0"))
            db.add(stock)
            db.flush()

        old_qty = stock.qty
        stock.qty += qty_to_receive

        product = db.query(Product).filter(Product.id == line.product_id).first()
        movement = StockMovement(
            product_id=line.product_id,
            location_id=po.location_id,
            qty_delta=qty_to_receive,
            reason=MovementReason.PURCHASE.value,
            ref_type="purchase_order",
            ref_id=po_id,
            notes=f"Received from PO #{po_id}: {product.name if product else 'Unknown'} x{qty_to_receive}"
        )
        db.add(movement)
        movements_created += 1

        items_received.append({
            "product_id": line.product_id,
            "product_name": product.name if product else "Unknown",
            "qty_received": float(qty_to_receive),
            "old_stock": float(old_qty),
            "new_stock": float(stock.qty),
            "unit": product.unit if product else "pcs"
        })

    po.status = POStatus.RECEIVED
    po.received_at = datetime.now(timezone.utc)
    if request and request.notes:
        po.notes = (po.notes or "") + f"\nReceived: {request.notes}"
    db.commit()

    return ReceiveGoodsResponse(
        status="received",
        po_id=po_id,
        stock_added=len(items_received),
        movements_created=movements_created,
        items_received=items_received
    )


@router.get("/{po_id}")
def get_purchase_order(db: DbSession, po_id: int):
    """Get a specific purchase order."""
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return _po_to_response(po, db)
