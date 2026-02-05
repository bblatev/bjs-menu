"""Purchase Orders API routes."""

from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter()


# --- Pydantic Models ---

class POItem(BaseModel):
    id: str
    ingredient_id: str
    ingredient_name: str
    quantity_ordered: float
    quantity_received: float = 0
    unit: str
    unit_price: float
    total_price: float
    notes: Optional[str] = None


class PurchaseOrder(BaseModel):
    id: str
    po_number: str
    supplier_id: str
    supplier_name: str
    venue_id: str = "1"
    warehouse_id: str
    warehouse_name: str
    status: str  # draft, pending_approval, approved, sent, partial, received, cancelled
    order_date: str
    expected_date: str
    total_amount: float
    currency: str = "BGN"
    items: List[POItem]
    created_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


class GRNItem(BaseModel):
    id: str
    po_item_id: str
    ingredient_name: str
    quantity_ordered: float
    quantity_received: float
    quantity_accepted: float
    quantity_rejected: float = 0
    rejection_reason: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    unit: str


class GoodsReceivedNote(BaseModel):
    id: str
    grn_number: str
    purchase_order_id: str
    po_number: str
    supplier_id: str
    supplier_name: str
    warehouse_id: str
    received_date: str
    received_by: str
    status: str  # pending, inspected, accepted, partial, rejected
    items: List[GRNItem]
    notes: Optional[str] = None
    temperature_check: Optional[float] = None
    quality_score: Optional[float] = None
    created_at: str


class InvoiceItem(BaseModel):
    id: str
    ingredient_name: str
    quantity_invoiced: float
    quantity_received: float
    unit_price_invoiced: float
    unit_price_ordered: float
    total_price: float
    variance_amount: float = 0
    unit: str


class Invoice(BaseModel):
    id: str
    invoice_number: str
    supplier_invoice_number: str
    purchase_order_id: str
    po_number: str
    grn_id: Optional[str] = None
    grn_number: Optional[str] = None
    supplier_id: str
    supplier_name: str
    invoice_date: str
    due_date: str
    status: str  # pending, matched, variance, approved, paid, disputed
    subtotal: float
    tax_amount: float
    total_amount: float
    amount_paid: float = 0
    currency: str = "BGN"
    matching_status: str = "pending"  # pending, matched, variance
    variance_amount: Optional[float] = None
    items: List[InvoiceItem]
    created_at: str


class ApprovalRequest(BaseModel):
    id: str
    type: str  # purchase_order, invoice, variance
    reference_id: str
    reference_number: str
    supplier_name: str
    amount: float
    requested_by: str
    requested_at: str
    status: str = "pending"  # pending, approved, rejected
    urgency: str = "medium"  # low, medium, high
    notes: Optional[str] = None


class MatchItem(BaseModel):
    ingredient_name: str
    po_qty: float
    grn_qty: float
    invoice_qty: float
    po_price: float
    invoice_price: float
    qty_variance: float = 0
    price_variance: float = 0


class ThreeWayMatch(BaseModel):
    po_id: str
    po_number: str
    grn_id: Optional[str] = None
    grn_number: Optional[str] = None
    invoice_id: Optional[str] = None
    invoice_number: Optional[str] = None
    supplier_name: str
    po_total: float
    grn_total: Optional[float] = None
    invoice_total: Optional[float] = None
    status: str = "pending"  # pending, partial, matched, variance
    quantity_variance: float = 0
    price_variance: float = 0
    items: List[MatchItem]


# --- Mock Data ---

MOCK_PURCHASE_ORDERS = [
    PurchaseOrder(
        id="1",
        po_number="PO-2026-001",
        supplier_id="1",
        supplier_name="Fresh Farm Produce",
        warehouse_id="1",
        warehouse_name="Main Kitchen",
        status="pending_approval",
        order_date="2026-01-28",
        expected_date="2026-02-03",
        total_amount=2450.00,
        items=[
            POItem(id="1", ingredient_id="1", ingredient_name="Tomatoes", quantity_ordered=50, quantity_received=0, unit="kg", unit_price=3.50, total_price=175.00),
            POItem(id="2", ingredient_id="2", ingredient_name="Onions", quantity_ordered=30, quantity_received=0, unit="kg", unit_price=2.00, total_price=60.00),
            POItem(id="3", ingredient_id="3", ingredient_name="Potatoes", quantity_ordered=100, quantity_received=0, unit="kg", unit_price=1.80, total_price=180.00),
            POItem(id="4", ingredient_id="4", ingredient_name="Carrots", quantity_ordered=40, quantity_received=0, unit="kg", unit_price=2.50, total_price=100.00),
        ],
        created_by="Manager",
        notes="Weekly vegetable order",
        created_at="2026-01-28T10:00:00Z"
    ),
    PurchaseOrder(
        id="2",
        po_number="PO-2026-002",
        supplier_id="2",
        supplier_name="Quality Meats Ltd",
        warehouse_id="2",
        warehouse_name="Cold Storage",
        status="approved",
        order_date="2026-01-27",
        expected_date="2026-02-01",
        total_amount=5800.00,
        items=[
            POItem(id="5", ingredient_id="5", ingredient_name="Beef Ribeye", quantity_ordered=25, quantity_received=0, unit="kg", unit_price=45.00, total_price=1125.00),
            POItem(id="6", ingredient_id="6", ingredient_name="Chicken Breast", quantity_ordered=40, quantity_received=0, unit="kg", unit_price=18.00, total_price=720.00),
            POItem(id="7", ingredient_id="7", ingredient_name="Pork Tenderloin", quantity_ordered=30, quantity_received=0, unit="kg", unit_price=22.00, total_price=660.00),
        ],
        created_by="Head Chef",
        approved_by="Manager",
        approved_at="2026-01-27T14:30:00Z",
        created_at="2026-01-27T09:00:00Z"
    ),
    PurchaseOrder(
        id="3",
        po_number="PO-2026-003",
        supplier_id="3",
        supplier_name="Beverage Distributors",
        warehouse_id="3",
        warehouse_name="Bar Storage",
        status="partial",
        order_date="2026-01-25",
        expected_date="2026-01-30",
        total_amount=3200.00,
        items=[
            POItem(id="8", ingredient_id="8", ingredient_name="Vodka Premium", quantity_ordered=24, quantity_received=24, unit="bottles", unit_price=35.00, total_price=840.00),
            POItem(id="9", ingredient_id="9", ingredient_name="Whiskey 12yr", quantity_ordered=12, quantity_received=8, unit="bottles", unit_price=55.00, total_price=660.00),
            POItem(id="10", ingredient_id="10", ingredient_name="Red Wine House", quantity_ordered=48, quantity_received=48, unit="bottles", unit_price=12.00, total_price=576.00),
        ],
        created_by="Bar Manager",
        approved_by="Manager",
        approved_at="2026-01-25T11:00:00Z",
        notes="Monthly bar restock",
        created_at="2026-01-25T08:00:00Z"
    ),
    PurchaseOrder(
        id="4",
        po_number="PO-2026-004",
        supplier_id="1",
        supplier_name="Fresh Farm Produce",
        warehouse_id="1",
        warehouse_name="Main Kitchen",
        status="received",
        order_date="2026-01-20",
        expected_date="2026-01-25",
        total_amount=1850.00,
        items=[
            POItem(id="11", ingredient_id="1", ingredient_name="Tomatoes", quantity_ordered=40, quantity_received=40, unit="kg", unit_price=3.50, total_price=140.00),
            POItem(id="12", ingredient_id="11", ingredient_name="Lettuce", quantity_ordered=20, quantity_received=20, unit="kg", unit_price=4.00, total_price=80.00),
        ],
        created_by="Manager",
        approved_by="Owner",
        approved_at="2026-01-20T12:00:00Z",
        created_at="2026-01-20T08:00:00Z"
    ),
]

MOCK_GRNS = [
    GoodsReceivedNote(
        id="1",
        grn_number="GRN-2026-001",
        purchase_order_id="3",
        po_number="PO-2026-003",
        supplier_id="3",
        supplier_name="Beverage Distributors",
        warehouse_id="3",
        received_date="2026-01-30",
        received_by="Bar Staff",
        status="partial",
        items=[
            GRNItem(id="1", po_item_id="8", ingredient_name="Vodka Premium", quantity_ordered=24, quantity_received=24, quantity_accepted=24, unit="bottles", batch_number="VD2026-001"),
            GRNItem(id="2", po_item_id="9", ingredient_name="Whiskey 12yr", quantity_ordered=12, quantity_received=8, quantity_accepted=8, unit="bottles", batch_number="WH2026-015"),
            GRNItem(id="3", po_item_id="10", ingredient_name="Red Wine House", quantity_ordered=48, quantity_received=48, quantity_accepted=48, unit="bottles", batch_number="RW2026-088", expiry_date="2028-12-31"),
        ],
        temperature_check=18.5,
        quality_score=95,
        notes="4 bottles of Whiskey on backorder",
        created_at="2026-01-30T14:00:00Z"
    ),
    GoodsReceivedNote(
        id="2",
        grn_number="GRN-2026-002",
        purchase_order_id="4",
        po_number="PO-2026-004",
        supplier_id="1",
        supplier_name="Fresh Farm Produce",
        warehouse_id="1",
        received_date="2026-01-25",
        received_by="Kitchen Staff",
        status="accepted",
        items=[
            GRNItem(id="4", po_item_id="11", ingredient_name="Tomatoes", quantity_ordered=40, quantity_received=40, quantity_accepted=38, quantity_rejected=2, rejection_reason="Bruised", unit="kg", batch_number="TM2026-112", expiry_date="2026-02-05"),
            GRNItem(id="5", po_item_id="12", ingredient_name="Lettuce", quantity_ordered=20, quantity_received=20, quantity_accepted=20, unit="kg", batch_number="LT2026-089", expiry_date="2026-02-01"),
        ],
        temperature_check=4.2,
        quality_score=92,
        created_at="2026-01-25T10:30:00Z"
    ),
]

MOCK_INVOICES = [
    Invoice(
        id="1",
        invoice_number="INV-2026-001",
        supplier_invoice_number="FFP-78542",
        purchase_order_id="4",
        po_number="PO-2026-004",
        grn_id="2",
        grn_number="GRN-2026-002",
        supplier_id="1",
        supplier_name="Fresh Farm Produce",
        invoice_date="2026-01-26",
        due_date="2026-02-10",
        status="matched",
        subtotal=1820.00,
        tax_amount=364.00,
        total_amount=2184.00,
        matching_status="matched",
        items=[
            InvoiceItem(id="1", ingredient_name="Tomatoes", quantity_invoiced=38, quantity_received=38, unit_price_invoiced=3.50, unit_price_ordered=3.50, total_price=133.00, unit="kg"),
            InvoiceItem(id="2", ingredient_name="Lettuce", quantity_invoiced=20, quantity_received=20, unit_price_invoiced=4.00, unit_price_ordered=4.00, total_price=80.00, unit="kg"),
        ],
        created_at="2026-01-26T09:00:00Z"
    ),
    Invoice(
        id="2",
        invoice_number="INV-2026-002",
        supplier_invoice_number="BD-2026-445",
        purchase_order_id="3",
        po_number="PO-2026-003",
        grn_id="1",
        grn_number="GRN-2026-001",
        supplier_id="3",
        supplier_name="Beverage Distributors",
        invoice_date="2026-01-31",
        due_date="2026-02-15",
        status="variance",
        subtotal=2856.00,
        tax_amount=571.20,
        total_amount=3427.20,
        matching_status="variance",
        variance_amount=220.00,
        items=[
            InvoiceItem(id="3", ingredient_name="Vodka Premium", quantity_invoiced=24, quantity_received=24, unit_price_invoiced=36.00, unit_price_ordered=35.00, total_price=864.00, variance_amount=24.00, unit="bottles"),
            InvoiceItem(id="4", ingredient_name="Whiskey 12yr", quantity_invoiced=12, quantity_received=8, unit_price_invoiced=55.00, unit_price_ordered=55.00, total_price=660.00, variance_amount=220.00, unit="bottles"),
            InvoiceItem(id="5", ingredient_name="Red Wine House", quantity_invoiced=48, quantity_received=48, unit_price_invoiced=12.00, unit_price_ordered=12.00, total_price=576.00, unit="bottles"),
        ],
        created_at="2026-01-31T11:00:00Z"
    ),
    Invoice(
        id="3",
        invoice_number="INV-2026-003",
        supplier_invoice_number="QM-98765",
        purchase_order_id="2",
        po_number="PO-2026-002",
        supplier_id="2",
        supplier_name="Quality Meats Ltd",
        invoice_date="2026-02-01",
        due_date="2026-02-16",
        status="pending",
        subtotal=5800.00,
        tax_amount=1160.00,
        total_amount=6960.00,
        matching_status="pending",
        items=[
            InvoiceItem(id="6", ingredient_name="Beef Ribeye", quantity_invoiced=25, quantity_received=0, unit_price_invoiced=45.00, unit_price_ordered=45.00, total_price=1125.00, unit="kg"),
            InvoiceItem(id="7", ingredient_name="Chicken Breast", quantity_invoiced=40, quantity_received=0, unit_price_invoiced=18.00, unit_price_ordered=18.00, total_price=720.00, unit="kg"),
            InvoiceItem(id="8", ingredient_name="Pork Tenderloin", quantity_invoiced=30, quantity_received=0, unit_price_invoiced=22.00, unit_price_ordered=22.00, total_price=660.00, unit="kg"),
        ],
        created_at="2026-02-01T08:00:00Z"
    ),
]

MOCK_APPROVALS = [
    ApprovalRequest(
        id="1",
        type="purchase_order",
        reference_id="1",
        reference_number="PO-2026-001",
        supplier_name="Fresh Farm Produce",
        amount=2450.00,
        requested_by="Manager",
        requested_at="2026-01-28T10:00:00Z",
        urgency="medium",
        notes="Weekly vegetable order - standard quantities"
    ),
    ApprovalRequest(
        id="2",
        type="variance",
        reference_id="2",
        reference_number="INV-2026-002",
        supplier_name="Beverage Distributors",
        amount=220.00,
        requested_by="System",
        requested_at="2026-01-31T11:30:00Z",
        urgency="high",
        notes="Price variance on Vodka (+24 BGN) and quantity variance on Whiskey (4 bottles short)"
    ),
    ApprovalRequest(
        id="3",
        type="purchase_order",
        reference_id="2",
        reference_number="PO-2026-002",
        supplier_name="Quality Meats Ltd",
        amount=5800.00,
        requested_by="Head Chef",
        requested_at="2026-01-27T09:00:00Z",
        status="approved"
    ),
]

MOCK_THREE_WAY_MATCHES = [
    ThreeWayMatch(
        po_id="4",
        po_number="PO-2026-004",
        grn_id="2",
        grn_number="GRN-2026-002",
        invoice_id="1",
        invoice_number="INV-2026-001",
        supplier_name="Fresh Farm Produce",
        po_total=1850.00,
        grn_total=1820.00,
        invoice_total=2184.00,
        status="matched",
        quantity_variance=0,
        price_variance=0,
        items=[
            MatchItem(ingredient_name="Tomatoes", po_qty=40, grn_qty=38, invoice_qty=38, po_price=3.50, invoice_price=3.50, qty_variance=0, price_variance=0),
            MatchItem(ingredient_name="Lettuce", po_qty=20, grn_qty=20, invoice_qty=20, po_price=4.00, invoice_price=4.00, qty_variance=0, price_variance=0),
        ]
    ),
    ThreeWayMatch(
        po_id="3",
        po_number="PO-2026-003",
        grn_id="1",
        grn_number="GRN-2026-001",
        invoice_id="2",
        invoice_number="INV-2026-002",
        supplier_name="Beverage Distributors",
        po_total=3200.00,
        grn_total=2856.00,
        invoice_total=3427.20,
        status="variance",
        quantity_variance=4,
        price_variance=24.00,
        items=[
            MatchItem(ingredient_name="Vodka Premium", po_qty=24, grn_qty=24, invoice_qty=24, po_price=35.00, invoice_price=36.00, qty_variance=0, price_variance=24.00),
            MatchItem(ingredient_name="Whiskey 12yr", po_qty=12, grn_qty=8, invoice_qty=12, po_price=55.00, invoice_price=55.00, qty_variance=4, price_variance=0),
            MatchItem(ingredient_name="Red Wine House", po_qty=48, grn_qty=48, invoice_qty=48, po_price=12.00, invoice_price=12.00, qty_variance=0, price_variance=0),
        ]
    ),
    ThreeWayMatch(
        po_id="2",
        po_number="PO-2026-002",
        supplier_name="Quality Meats Ltd",
        po_total=5800.00,
        status="pending",
        quantity_variance=0,
        price_variance=0,
        items=[
            MatchItem(ingredient_name="Beef Ribeye", po_qty=25, grn_qty=0, invoice_qty=25, po_price=45.00, invoice_price=45.00),
            MatchItem(ingredient_name="Chicken Breast", po_qty=40, grn_qty=0, invoice_qty=40, po_price=18.00, invoice_price=18.00),
            MatchItem(ingredient_name="Pork Tenderloin", po_qty=30, grn_qty=0, invoice_qty=30, po_price=22.00, invoice_price=22.00),
        ]
    ),
]


# --- API Endpoints ---

@router.get("/")
async def get_purchase_orders():
    """Get all purchase orders."""
    return MOCK_PURCHASE_ORDERS


@router.get("/grns/")
async def get_grns():
    """Get all goods received notes."""
    return MOCK_GRNS


@router.get("/invoices/")
async def get_invoices():
    """Get all invoices."""
    return MOCK_INVOICES


@router.get("/approvals/")
async def get_approvals():
    """Get all approval requests."""
    return MOCK_APPROVALS


@router.get("/three-way-matches/")
async def get_three_way_matches():
    """Get all three-way matches."""
    return MOCK_THREE_WAY_MATCHES


@router.post("/{po_id}/approve")
async def approve_purchase_order(po_id: str):
    """Approve a purchase order."""
    for po in MOCK_PURCHASE_ORDERS:
        if po.id == po_id:
            po.status = "approved"
            po.approved_by = "Admin"
            po.approved_at = datetime.utcnow().isoformat()
            # Update corresponding approval
            for approval in MOCK_APPROVALS:
                if approval.reference_id == po_id and approval.type == "purchase_order":
                    approval.status = "approved"
            return {"success": True, "message": f"Purchase order {po.po_number} approved"}
    raise HTTPException(status_code=404, detail="Purchase order not found")


@router.post("/{po_id}/reject")
async def reject_purchase_order(po_id: str):
    """Reject a purchase order."""
    for po in MOCK_PURCHASE_ORDERS:
        if po.id == po_id:
            po.status = "cancelled"
            # Update corresponding approval
            for approval in MOCK_APPROVALS:
                if approval.reference_id == po_id and approval.type == "purchase_order":
                    approval.status = "rejected"
            return {"success": True, "message": f"Purchase order {po.po_number} rejected"}
    raise HTTPException(status_code=404, detail="Purchase order not found")


@router.post("/approvals/{approval_id}/approve")
async def approve_variance(approval_id: str):
    """Approve a variance or other approval request."""
    for approval in MOCK_APPROVALS:
        if approval.id == approval_id:
            approval.status = "approved"
            return {"success": True, "message": f"Approval {approval.reference_number} approved"}
    raise HTTPException(status_code=404, detail="Approval request not found")


@router.post("/approvals/{approval_id}/reject")
async def reject_variance(approval_id: str):
    """Reject a variance or other approval request."""
    for approval in MOCK_APPROVALS:
        if approval.id == approval_id:
            approval.status = "rejected"
            return {"success": True, "message": f"Approval {approval.reference_number} rejected"}
    raise HTTPException(status_code=404, detail="Approval request not found")


@router.get("/{po_id}")
async def get_purchase_order(po_id: str):
    """Get a specific purchase order."""
    for po in MOCK_PURCHASE_ORDERS:
        if po.id == po_id:
            return po
    raise HTTPException(status_code=404, detail="Purchase order not found")


# ==================== DATABASE-BACKED ENDPOINTS ====================
# These endpoints use actual database models and update real inventory

from decimal import Decimal
from app.db.session import DbSession
from app.models.order import PurchaseOrder as PurchaseOrderModel, PurchaseOrderLine, POStatus
from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.product import Product


class ReceiveGoodsRequest(BaseModel):
    """Request to receive goods from a PO."""
    received_quantities: Optional[dict] = None  # {line_id: qty_received}
    notes: Optional[str] = None


class ReceiveGoodsResponse(BaseModel):
    """Response after receiving goods."""
    status: str
    po_id: int
    stock_added: int
    movements_created: int
    items_received: List[dict]


@router.post("/db/{po_id}/receive", response_model=ReceiveGoodsResponse)
def receive_purchase_order(
    db: DbSession,
    po_id: int,
    request: ReceiveGoodsRequest = None,
):
    """
    Receive goods from a purchase order (DATABASE-BACKED).

    This endpoint:
    1. Updates PurchaseOrder status to RECEIVED
    2. Creates StockMovement records (reason=PURCHASE) for each line
    3. Updates StockOnHand for each product at the PO location

    Use this for actual inventory management.
    """
    # Get the purchase order
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if po.status == POStatus.RECEIVED:
        raise HTTPException(status_code=400, detail="Purchase order already received")

    if po.status == POStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot receive cancelled purchase order")

    # Get all PO lines
    lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po_id).all()
    if not lines:
        raise HTTPException(status_code=400, detail="Purchase order has no items")

    items_received = []
    movements_created = 0

    for line in lines:
        # Determine quantity to receive (use request override or full qty)
        qty_to_receive = line.qty
        if request and request.received_quantities:
            qty_to_receive = Decimal(str(request.received_quantities.get(str(line.id), line.qty)))

        if qty_to_receive <= 0:
            continue

        # Get or create StockOnHand record
        stock = db.query(StockOnHand).filter(
            StockOnHand.product_id == line.product_id,
            StockOnHand.location_id == po.location_id
        ).first()

        if not stock:
            stock = StockOnHand(
                product_id=line.product_id,
                location_id=po.location_id,
                qty=Decimal("0")
            )
            db.add(stock)
            db.flush()

        # Update stock quantity (ADD inventory)
        old_qty = stock.qty
        stock.qty += qty_to_receive

        # Create stock movement record
        product = db.query(Product).filter(Product.id == line.product_id).first()
        movement = StockMovement(
            product_id=line.product_id,
            location_id=po.location_id,
            qty_delta=qty_to_receive,  # Positive for receiving goods
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

    # Update PO status
    po.status = POStatus.RECEIVED
    po.received_at = datetime.utcnow()
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


@router.get("/db/list")
def list_db_purchase_orders(
    db: DbSession,
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    limit: int = 100,
):
    """List purchase orders from database (not mock data)."""
    query = db.query(PurchaseOrderModel)

    if status:
        query = query.filter(PurchaseOrderModel.status == status)
    if supplier_id:
        query = query.filter(PurchaseOrderModel.supplier_id == supplier_id)

    pos = query.order_by(PurchaseOrderModel.created_at.desc()).limit(limit).all()

    result = []
    for po in pos:
        lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).all()
        total = sum(float(line.qty * (line.unit_cost or 0)) for line in lines)

        result.append({
            "id": po.id,
            "supplier_id": po.supplier_id,
            "location_id": po.location_id,
            "status": po.status.value if po.status else "draft",
            "created_at": po.created_at.isoformat() if po.created_at else None,
            "sent_at": po.sent_at.isoformat() if po.sent_at else None,
            "received_at": po.received_at.isoformat() if po.received_at else None,
            "notes": po.notes,
            "total_amount": total,
            "line_count": len(lines)
        })

    return {"purchase_orders": result, "total": len(result)}


@router.get("/db/{po_id}")
def get_db_purchase_order(db: DbSession, po_id: int):
    """Get a specific purchase order from database."""
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    lines = db.query(PurchaseOrderLine).filter(PurchaseOrderLine.po_id == po.id).all()

    line_data = []
    for line in lines:
        product = db.query(Product).filter(Product.id == line.product_id).first()
        line_data.append({
            "id": line.id,
            "product_id": line.product_id,
            "product_name": product.name if product else "Unknown",
            "qty": float(line.qty),
            "unit": product.unit if product else "pcs",
            "unit_cost": float(line.unit_cost) if line.unit_cost else 0,
            "total": float(line.qty * (line.unit_cost or 0))
        })

    return {
        "id": po.id,
        "supplier_id": po.supplier_id,
        "location_id": po.location_id,
        "status": po.status.value if po.status else "draft",
        "created_at": po.created_at.isoformat() if po.created_at else None,
        "sent_at": po.sent_at.isoformat() if po.sent_at else None,
        "received_at": po.received_at.isoformat() if po.received_at else None,
        "notes": po.notes,
        "lines": line_data,
        "total_amount": sum(l["total"] for l in line_data)
    }
