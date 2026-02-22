"""Purchase Orders API routes - database-backed.

Includes advanced PO features (templates, approval workflows, supplier invoices,
three-way matching, GRN, analytics) merged from enhanced_inventory_endpoints.py.
"""

import logging
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from app.core.rate_limit import limiter
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from app.db.session import DbSession, get_db
from app.core.rbac import get_current_user
from app.models.order import PurchaseOrder as PurchaseOrderModel, PurchaseOrderLine, POStatus
from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.location import Location

_po_logger = logging.getLogger(__name__)

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
@limiter.limit("60/minute")
def get_purchase_orders(
    request: Request,
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
@limiter.limit("30/minute")
def create_purchase_order(request: Request, db: DbSession = None, body: CreatePORequest = None):
    """Create a new purchase order."""
    supplier = db.query(Supplier).filter(Supplier.id == body.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    po = PurchaseOrderModel(
        supplier_id=body.supplier_id,
        location_id=body.location_id,
        status=POStatus.DRAFT,
        notes=body.notes,
    )
    db.add(po)
    db.flush()

    for item in body.items:
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
@limiter.limit("60/minute")
def get_approvals(request: Request, db: DbSession):
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
@limiter.limit("60/minute")
def get_grns(request: Request, db: DbSession):
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
@limiter.limit("60/minute")
def get_invoices(request: Request, db: DbSession):
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
@limiter.limit("60/minute")
def get_three_way_matches(request: Request, db: DbSession):
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
@limiter.limit("30/minute")
def approve_purchase_order(request: Request, db: DbSession, po_id: int):
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
@limiter.limit("30/minute")
def reject_purchase_order(request: Request, db: DbSession, po_id: int):
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
@limiter.limit("30/minute")
def approve_approval(request: Request, db: DbSession, approval_id: int):
    """Approve an approval request (same as approving the PO)."""
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == approval_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Approval request not found")
    po.status = POStatus.SENT
    po.sent_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "message": f"Approval for PO-{po.id:04d} approved"}


@router.post("/approvals/{approval_id}/reject")
@limiter.limit("30/minute")
def reject_approval(request: Request, db: DbSession, approval_id: int):
    """Reject an approval request."""
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == approval_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Approval request not found")
    po.status = POStatus.CANCELLED
    db.commit()
    return {"success": True, "message": f"Approval for PO-{po.id:04d} rejected"}


@router.post("/{po_id}/receive", response_model=ReceiveGoodsResponse)
@limiter.limit("30/minute")
def receive_purchase_order(
    request: Request,
    db: DbSession = None,
    po_id: int = None,
    body: ReceiveGoodsRequest = None,
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
        if body and body.received_quantities:
            qty_to_receive = Decimal(str(body.received_quantities.get(str(line.id), line.qty)))
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
    if body and body.notes:
        po.notes = (po.notes or "") + f"\nReceived: {body.notes}"
    db.commit()

    return ReceiveGoodsResponse(
        status="received",
        po_id=po_id,
        stock_added=len(items_received),
        movements_created=movements_created,
        items_received=items_received
    )


@router.put("/{po_id}")
@limiter.limit("30/minute")
def update_purchase_order(request: Request, db: DbSession = None, po_id: int = None, data: dict = None):
    """Update a purchase order."""
    from fastapi import Body
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if data is None:
        data = {}
    if "status" in data:
        try:
            po.status = POStatus(data["status"])
        except ValueError:
            pass
    if "notes" in data:
        po.notes = data["notes"]
    db.commit()
    db.refresh(po)
    return _po_to_response(po, db)


@router.get("/{po_id}")
@limiter.limit("60/minute")
def get_purchase_order(request: Request, db: DbSession, po_id: int):
    """Get a specific purchase order."""
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return _po_to_response(po, db)


# ==================== ADVANCED PO FEATURES ====================
# (merged from enhanced_inventory_endpoints.py)

# --- Schemas ---


class POTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    supplier_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[Dict[str, Any]] = None
    items: List[Dict[str, Any]]


class POApprovalCreate(BaseModel):
    purchase_order_id: int
    action: str  # "approve" or "reject"
    notes: Optional[str] = None


class SupplierInvoiceCreate(BaseModel):
    supplier_id: int
    invoice_number: str
    invoice_date: date
    due_date: Optional[date] = None
    subtotal: Decimal
    tax_amount: Decimal = Decimal("0")
    total_amount: Decimal
    currency: str = "BGN"
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    file_url: Optional[str] = None
    purchase_order_id: Optional[int] = None
    items: List[Dict[str, Any]]


class GRNCreate(BaseModel):
    purchase_order_id: Optional[int] = None
    supplier_id: int
    warehouse_id: Optional[int] = None
    received_date: Optional[date] = None
    notes: Optional[str] = None
    items: List[Dict[str, Any]]


# --- Endpoints ---


@router.get("/templates/list")
@limiter.limit("60/minute")
def get_po_templates(
    request: Request,
    venue_id: int = Query(1, description="Venue ID"),
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get purchase order templates."""
    try:
        from app.models.enhanced_inventory import PurchaseOrderTemplate

        query = db.query(PurchaseOrderTemplate).filter(
            PurchaseOrderTemplate.venue_id == venue_id,
            PurchaseOrderTemplate.is_active == True,
        )
        if supplier_id:
            query = query.filter(PurchaseOrderTemplate.supplier_id == supplier_id)
        return query.all()
    except Exception as e:
        _po_logger.error(f"Error fetching PO templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch PO templates")


@router.post("/templates/create")
@limiter.limit("30/minute")
def create_po_template(
    request: Request,
    venue_id: int,
    data: POTemplateCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a purchase order template."""
    try:
        from app.models.enhanced_inventory import PurchaseOrderTemplate

        template_data = data.model_dump(exclude={"items"})
        template = PurchaseOrderTemplate(
            venue_id=venue_id,
            supplier_id=template_data.get("supplier_id"),
            template_name=template_data.get("name", ""),
            description=template_data.get("description"),
            items=data.items,
            is_active=True,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template
    except Exception as e:
        db.rollback()
        _po_logger.error(f"Error creating PO template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create PO template")


@router.post("/from-template/{template_id}")
@limiter.limit("30/minute")
def create_po_from_template(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a purchase order from a template."""
    try:
        from app.services.inventory_management_service import AdvancedPurchaseOrderService

        service = AdvancedPurchaseOrderService(db)
        po = service.create_from_template(
            template_id=template_id,
            created_by=current_user.id,
        )
        if not po:
            raise HTTPException(status_code=404, detail="Template not found")
        return po
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        _po_logger.error(f"Error creating PO from template: {e}")
        raise HTTPException(status_code=500, detail="Failed to create PO from template")


@router.get("/{po_id}/approval-history")
@limiter.limit("60/minute")
def get_po_approval_history(
    request: Request,
    po_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get approval history for a purchase order."""
    try:
        from app.models.enhanced_inventory import PurchaseOrderApproval

        return db.query(PurchaseOrderApproval).filter(
            PurchaseOrderApproval.purchase_order_id == po_id
        ).order_by(PurchaseOrderApproval.approval_level).all()
    except Exception as e:
        _po_logger.error(f"Error fetching PO approvals: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch PO approvals")


@router.post("/approval-action")
@limiter.limit("30/minute")
def submit_po_approval(
    request: Request,
    data: POApprovalCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit approval/rejection for a purchase order."""
    try:
        from app.models.enhanced_inventory import PurchaseOrderApproval
        from app.services.inventory_management_service import AdvancedPurchaseOrderService

        approval = db.query(PurchaseOrderApproval).filter(
            PurchaseOrderApproval.purchase_order_id == data.purchase_order_id,
            PurchaseOrderApproval.status == "pending",
        ).first()

        if not approval:
            raise HTTPException(status_code=400, detail="No pending approval found")

        service = AdvancedPurchaseOrderService(db)
        result, all_approved = service.process_approval(
            approval_id=approval.id,
            approved_by=current_user.id,
            approved=data.action == "approve",
            comments=data.notes,
        )

        if not result:
            raise HTTPException(status_code=400, detail="Approval action failed")
        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        _po_logger.error(f"Error processing PO approval: {e}")
        raise HTTPException(status_code=500, detail="Failed to process PO approval")


@router.get("/pending-approvals")
@limiter.limit("60/minute")
def get_pending_approval_pos(
    request: Request,
    venue_id: int = Query(1, description="Venue ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get purchase orders pending approval."""
    try:
        from app.models.enhanced_inventory import PurchaseOrderApproval

        pending_approvals = db.query(PurchaseOrderApproval).filter(
            PurchaseOrderApproval.status == "pending"
        ).all()
        po_ids = [a.purchase_order_id for a in pending_approvals]
        if not po_ids:
            return []
        return db.query(PurchaseOrderModel).filter(
            PurchaseOrderModel.location_id == venue_id,
            PurchaseOrderModel.id.in_(po_ids),
        ).all()
    except Exception as e:
        _po_logger.error(f"Error fetching pending approval POs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch pending approval POs")


@router.get("/supplier-invoices")
@limiter.limit("60/minute")
def get_supplier_invoices(
    request: Request,
    venue_id: int = Query(1, description="Venue ID"),
    supplier_id: Optional[int] = None,
    inv_status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get supplier invoices (enhanced model)."""
    try:
        from app.models.enhanced_inventory import SupplierInvoice

        query = db.query(SupplierInvoice).filter(SupplierInvoice.venue_id == venue_id)
        if supplier_id:
            query = query.filter(SupplierInvoice.supplier_id == supplier_id)
        if inv_status:
            query = query.filter(SupplierInvoice.status == inv_status)

        return query.order_by(SupplierInvoice.invoice_date.desc()).limit(limit).offset(offset).all()
    except Exception as e:
        _po_logger.error(f"Error fetching supplier invoices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch supplier invoices")


@router.post("/supplier-invoices")
@limiter.limit("30/minute")
def create_supplier_invoice(
    request: Request,
    venue_id: int,
    data: SupplierInvoiceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a supplier invoice."""
    try:
        from app.services.inventory_management_service import AdvancedPurchaseOrderService

        service = AdvancedPurchaseOrderService(db)
        invoice_data = data.model_dump(exclude={"items"})
        invoice = service.create_invoice(
            venue_id=venue_id,
            supplier_id=invoice_data.get("supplier_id"),
            invoice_number=invoice_data.get("invoice_number", ""),
            invoice_date=invoice_data.get("invoice_date"),
            items=data.items,
            created_by=current_user.id,
            purchase_order_id=invoice_data.get("purchase_order_id"),
        )
        return invoice
    except Exception as e:
        db.rollback()
        _po_logger.error(f"Error creating supplier invoice: {e}")
        raise HTTPException(status_code=500, detail="Failed to create supplier invoice")


@router.post("/supplier-invoices/{invoice_id}/match")
@limiter.limit("30/minute")
def perform_three_way_match(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Perform three-way matching (PO, GRN, Invoice)."""
    try:
        from app.services.inventory_management_service import AdvancedPurchaseOrderService

        service = AdvancedPurchaseOrderService(db)
        result = service.three_way_match(invoice_id)
        if not result:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        _po_logger.error(f"Error performing three-way match: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform three-way match")


@router.get("/goods-received-notes")
@limiter.limit("60/minute")
def get_goods_received_notes(
    request: Request,
    venue_id: int = Query(1, description="Venue ID"),
    purchase_order_id: Optional[int] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get goods received notes (enhanced model)."""
    try:
        from app.models.enhanced_inventory import GoodsReceivedNote

        query = db.query(GoodsReceivedNote).filter(GoodsReceivedNote.venue_id == venue_id)
        if purchase_order_id:
            query = query.filter(GoodsReceivedNote.purchase_order_id == purchase_order_id)

        return query.order_by(GoodsReceivedNote.delivery_date.desc()).limit(limit).offset(offset).all()
    except Exception as e:
        _po_logger.error(f"Error fetching GRN: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch goods received notes")


@router.post("/goods-received-notes")
@limiter.limit("30/minute")
def create_goods_received_note(
    request: Request,
    venue_id: int,
    data: GRNCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a goods received note (receive items from PO)."""
    try:
        from app.services.inventory_management_service import AdvancedPurchaseOrderService

        service = AdvancedPurchaseOrderService(db)
        grn = service.create_grn(
            venue_id=venue_id,
            supplier_id=data.supplier_id,
            items=data.items,
            received_by=current_user.id,
            purchase_order_id=data.purchase_order_id,
            warehouse_id=data.warehouse_id,
        )
        return grn
    except Exception as e:
        db.rollback()
        _po_logger.error(f"Error creating GRN: {e}")
        raise HTTPException(status_code=500, detail="Failed to create goods received note")


@router.get("/analytics/summary")
@limiter.limit("60/minute")
def get_po_analytics(
    request: Request,
    venue_id: int = Query(1, description="Venue ID"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get purchase order analytics."""
    try:
        from app.services.inventory_management_service import AdvancedPurchaseOrderService

        service = AdvancedPurchaseOrderService(db)
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        analytics = service.get_analytics(
            venue_id=venue_id,
            period_start=start_date,
            period_end=end_date,
        )
        return analytics
    except Exception as e:
        _po_logger.error(f"Error fetching PO analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch PO analytics")
