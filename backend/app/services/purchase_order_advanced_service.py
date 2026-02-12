"""
Advanced Purchase Order Management Service
Complete business logic for:
- Returns to Suppliers & Credit Notes
- PO Amendments & Change Orders
- Blanket/Standing Purchase Orders
- Purchase Requisitions
- Landed Cost Calculation
- Financial Integration (AP, Aging)
- Consolidated Multi-Location Purchasing
- Enhanced Quality Control
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional, List
from datetime import datetime, date

from app.models.purchase_order_advanced import (
    # Returns & Credit Notes
    SupplierReturn, SupplierReturnItem, SupplierCreditNote, SupplierCreditNoteItem,
    CreditNoteApplication, SupplierDebitNote,
    ReturnStatus, ReturnReason, CreditNoteStatus, CreditNoteType,
    # Amendments
    PurchaseOrderAmendment, PurchaseOrderVersionHistory,
    AmendmentType, AmendmentStatus,
    # Blanket Orders
    BlanketPurchaseOrder, BlanketPurchaseOrderItem, BlanketOrderRelease, BlanketOrderReleaseItem,
    BlanketOrderStatus,
    # Requisitions
    PurchaseRequisition, PurchaseRequisitionItem, RequisitionApproval, RequisitionToPO,
    RequisitionStatus, RequisitionPriority,
    # Landed Cost
    LandedCostConfig, PurchaseOrderLandedCost, LandedCostAllocation,
    # Financial
    SupplierPayment, PaymentAllocation, SupplierAccountBalance, InvoiceAgingSnapshot, PaymentTermsConfig,
    PaymentStatus,
    # Consolidated
    ConsolidatedPurchaseOrder, ConsolidatedOrderVenue, ConsolidatedOrderItem,
    ConsolidatedOrderStatus,
    # Quality Control
    QualityControlChecklist, QualityControlInspection, QualityIssue,
    QCStatus,
    # Reorder & Partial Delivery
    StockReorderConfig, ReorderAlert, PartialDeliverySchedule, PartialDeliveryItem, BackorderTracking,
)
from app.models import PurchaseOrder, PurchaseOrderItem, StockItem, PurchaseOrderStatus
from app.schemas.purchase_order_advanced import (
    SupplierReturnCreate, SupplierReturnShip, SupplierReturnConfirmReceipt, SupplierCreditNoteCreate,
    CreditNoteApplicationCreate, PurchaseOrderAmendmentCreate, BlanketPurchaseOrderCreate,
    BlanketReleaseCreate,
    PurchaseRequisitionCreate, RequisitionToPOConvert, PurchaseOrderLandedCostCreate,
    SupplierPaymentCreate, ConsolidatedPurchaseOrderCreate, QualityControlChecklistCreate,
    QualityControlInspectionCreate, QualityControlInspectionUpdate,
    QualityIssueCreate, StockReorderConfigCreate,
    PartialDeliveryScheduleCreate,
    BackorderTrackingCreate, BackorderTrackingUpdate,
)


class SupplierReturnService:
    """Service for managing supplier returns"""

    @staticmethod
    def generate_return_number(db: Session, venue_id: int) -> str:
        today = date.today()
        prefix = f"RTN-{venue_id}-{today.strftime('%Y%m%d')}"
        count = db.query(SupplierReturn).filter(
            SupplierReturn.return_number.like(f"{prefix}%")
        ).count()
        return f"{prefix}-{count + 1:04d}"

    @staticmethod
    def create_return(db: Session, data: SupplierReturnCreate, user_id: int) -> SupplierReturn:
        return_number = SupplierReturnService.generate_return_number(db, data.venue_id)

        # Calculate totals
        subtotal = sum(item.quantity_to_return * item.unit_price for item in data.items)

        supplier_return = SupplierReturn(
            venue_id=data.venue_id,
            supplier_id=data.supplier_id,
            return_number=return_number,
            purchase_order_id=data.purchase_order_id,
            grn_id=data.grn_id,
            invoice_id=data.invoice_id,
            return_date=data.return_date,
            return_reason=data.return_reason,
            reason_details=data.reason_details,
            notes=data.notes,
            supplier_instructions=data.supplier_instructions,
            subtotal=subtotal,
            total_value=subtotal,
            expected_credit=subtotal,
            created_by=user_id,
            status=ReturnStatus.DRAFT
        )
        db.add(supplier_return)
        db.flush()

        for item_data in data.items:
            item = SupplierReturnItem(
                supplier_return_id=supplier_return.id,
                stock_item_id=item_data.stock_item_id,
                po_item_id=item_data.po_item_id,
                grn_item_id=item_data.grn_item_id,
                item_name=item_data.item_name,
                sku=item_data.sku,
                unit=item_data.unit,
                quantity_to_return=item_data.quantity_to_return,
                unit_price=item_data.unit_price,
                total_value=item_data.quantity_to_return * item_data.unit_price,
                return_reason=item_data.return_reason,
                condition=item_data.condition,
                batch_number=item_data.batch_number,
                expiry_date=item_data.expiry_date,
                disposition=item_data.disposition,
                notes=item_data.notes
            )
            db.add(item)

        db.commit()
        db.refresh(supplier_return)
        return supplier_return

    @staticmethod
    def submit_for_approval(db: Session, return_id: int) -> SupplierReturn:
        supplier_return = db.query(SupplierReturn).filter(SupplierReturn.id == return_id).first()
        if supplier_return and supplier_return.status == ReturnStatus.DRAFT:
            supplier_return.status = ReturnStatus.PENDING_APPROVAL
            db.commit()
            db.refresh(supplier_return)
        return supplier_return

    @staticmethod
    def approve_return(db: Session, return_id: int, user_id: int) -> SupplierReturn:
        supplier_return = db.query(SupplierReturn).filter(SupplierReturn.id == return_id).first()
        if supplier_return and supplier_return.status == ReturnStatus.PENDING_APPROVAL:
            supplier_return.status = ReturnStatus.APPROVED
            supplier_return.approved_by = user_id
            supplier_return.approved_at = datetime.utcnow()
            db.commit()
            db.refresh(supplier_return)
        return supplier_return

    @staticmethod
    def ship_return(db: Session, return_id: int, data: SupplierReturnShip) -> SupplierReturn:
        supplier_return = db.query(SupplierReturn).filter(SupplierReturn.id == return_id).first()
        if supplier_return and supplier_return.status == ReturnStatus.APPROVED:
            supplier_return.status = ReturnStatus.SHIPPED
            supplier_return.carrier = data.carrier
            supplier_return.tracking_number = data.tracking_number
            supplier_return.shipping_cost = data.shipping_cost or 0
            supplier_return.shipped_date = data.shipped_date or date.today()

            # Update item shipped quantities
            for item in supplier_return.items:
                item.quantity_shipped = item.quantity_to_return

            db.commit()
            db.refresh(supplier_return)
        return supplier_return

    @staticmethod
    def confirm_supplier_receipt(db: Session, return_id: int, data: SupplierReturnConfirmReceipt) -> SupplierReturn:
        supplier_return = db.query(SupplierReturn).filter(SupplierReturn.id == return_id).first()
        if supplier_return and supplier_return.status == ReturnStatus.SHIPPED:
            supplier_return.status = ReturnStatus.RECEIVED_BY_SUPPLIER
            supplier_return.received_by_supplier_date = data.received_by_supplier_date

            # Update item received quantities
            for item_update in data.items:
                item = db.query(SupplierReturnItem).filter(
                    SupplierReturnItem.id == item_update.get('item_id')
                ).first()
                if item:
                    item.quantity_received_back = item_update.get('quantity_received_back', item.quantity_shipped)

            db.commit()
            db.refresh(supplier_return)
        return supplier_return

    @staticmethod
    def get_returns(
        db: Session,
        venue_id: int,
        supplier_id: Optional[int] = None,
        status: Optional[ReturnStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[SupplierReturn]:
        query = db.query(SupplierReturn).filter(SupplierReturn.venue_id == venue_id)
        if supplier_id:
            query = query.filter(SupplierReturn.supplier_id == supplier_id)
        if status:
            query = query.filter(SupplierReturn.status == status)
        return query.order_by(SupplierReturn.created_at.desc()).offset(skip).limit(limit).all()


class SupplierCreditNoteService:
    """Service for managing supplier credit notes"""

    @staticmethod
    def generate_cn_number(db: Session, venue_id: int) -> str:
        today = date.today()
        prefix = f"CN-{venue_id}-{today.strftime('%Y%m%d')}"
        count = db.query(SupplierCreditNote).filter(
            SupplierCreditNote.credit_note_number.like(f"{prefix}%")
        ).count()
        return f"{prefix}-{count + 1:04d}"

    @staticmethod
    def create_credit_note(db: Session, data: SupplierCreditNoteCreate, user_id: int) -> SupplierCreditNote:
        credit_note = SupplierCreditNote(
            venue_id=data.venue_id,
            supplier_id=data.supplier_id,
            credit_note_number=data.credit_note_number or SupplierCreditNoteService.generate_cn_number(db, data.venue_id),
            supplier_reference=data.supplier_reference,
            credit_type=data.credit_type,
            supplier_return_id=data.supplier_return_id,
            invoice_id=data.invoice_id,
            purchase_order_id=data.purchase_order_id,
            credit_date=data.credit_date,
            received_date=data.received_date,
            expiry_date=data.expiry_date,
            subtotal=data.subtotal,
            tax_amount=data.tax_amount,
            total_amount=data.total_amount,
            amount_remaining=data.total_amount,
            currency=data.currency,
            exchange_rate=data.exchange_rate,
            reason=data.reason,
            notes=data.notes,
            document_url=data.document_url,
            created_by=user_id,
            status=CreditNoteStatus.PENDING
        )
        db.add(credit_note)
        db.flush()

        for item_data in data.items:
            item = SupplierCreditNoteItem(
                credit_note_id=credit_note.id,
                stock_item_id=item_data.stock_item_id,
                return_item_id=item_data.return_item_id,
                description=item_data.description,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                amount=item_data.amount,
                tax_rate=item_data.tax_rate,
                tax_amount=item_data.tax_amount
            )
            db.add(item)

        # Update supplier return if linked
        if data.supplier_return_id:
            supplier_return = db.query(SupplierReturn).filter(
                SupplierReturn.id == data.supplier_return_id
            ).first()
            if supplier_return:
                supplier_return.status = ReturnStatus.CREDIT_ISSUED
                supplier_return.credit_received = data.total_amount

        db.commit()
        db.refresh(credit_note)
        return credit_note

    @staticmethod
    def apply_credit(db: Session, data: CreditNoteApplicationCreate, user_id: int) -> CreditNoteApplication:
        credit_note = db.query(SupplierCreditNote).filter(
            SupplierCreditNote.id == data.credit_note_id
        ).first()

        if not credit_note or credit_note.amount_remaining < data.amount_applied:
            raise ValueError("Insufficient credit balance")

        application = CreditNoteApplication(
            credit_note_id=data.credit_note_id,
            invoice_id=data.invoice_id,
            payment_id=data.payment_id,
            amount_applied=data.amount_applied,
            applied_date=data.applied_date,
            applied_by=user_id,
            notes=data.notes
        )
        db.add(application)

        credit_note.amount_applied += data.amount_applied
        credit_note.amount_remaining -= data.amount_applied

        if credit_note.amount_remaining <= 0:
            credit_note.status = CreditNoteStatus.APPLIED

        db.commit()
        db.refresh(application)
        return application

    @staticmethod
    def get_credit_notes(
        db: Session,
        venue_id: int,
        supplier_id: Optional[int] = None,
        status: Optional[CreditNoteStatus] = None,
        with_balance_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> List[SupplierCreditNote]:
        query = db.query(SupplierCreditNote).filter(SupplierCreditNote.venue_id == venue_id)
        if supplier_id:
            query = query.filter(SupplierCreditNote.supplier_id == supplier_id)
        if status:
            query = query.filter(SupplierCreditNote.status == status)
        if with_balance_only:
            query = query.filter(SupplierCreditNote.amount_remaining > 0)
        return query.order_by(SupplierCreditNote.credit_date.desc()).offset(skip).limit(limit).all()


class PurchaseOrderAmendmentService:
    """Service for managing PO amendments and version history"""

    @staticmethod
    def create_version_snapshot(db: Session, po: PurchaseOrder, change_type: str,
                                 summary: str = None, amendment_id: int = None, user_id: int = None):
        # Get current max version
        max_version = db.query(func.max(PurchaseOrderVersionHistory.version_number)).filter(
            PurchaseOrderVersionHistory.purchase_order_id == po.id
        ).scalar() or 0

        snapshot = PurchaseOrderVersionHistory(
            purchase_order_id=po.id,
            version_number=max_version + 1,
            full_snapshot={
                'order_number': po.order_number,
                'status': po.status.value if po.status else None,
                'supplier_id': po.supplier_id,
                'order_date': po.order_date.isoformat() if po.order_date else None,
                'expected_date': po.expected_date.isoformat() if po.expected_date else None,
                'subtotal': float(po.subtotal) if po.subtotal else 0,
                'tax_amount': float(po.tax_amount) if po.tax_amount else 0,
                'total': float(po.total) if po.total else 0,
                'notes': po.notes
            },
            items_snapshot=[{
                'id': item.id,
                'item_name': item.item_name,
                'quantity_ordered': float(item.quantity_ordered),
                'quantity_received': float(item.quantity_received) if item.quantity_received else 0,
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price)
            } for item in po.items],
            change_type=change_type,
            change_summary=summary,
            amendment_id=amendment_id,
            changed_by=user_id
        )
        db.add(snapshot)
        return snapshot

    @staticmethod
    def create_amendment(db: Session, data: PurchaseOrderAmendmentCreate, user_id: int) -> PurchaseOrderAmendment:
        po = db.query(PurchaseOrder).filter(PurchaseOrder.id == data.purchase_order_id).first()
        if not po:
            raise ValueError("Purchase order not found")

        # Get next amendment number
        max_amendment = db.query(func.max(PurchaseOrderAmendment.amendment_number)).filter(
            PurchaseOrderAmendment.purchase_order_id == data.purchase_order_id
        ).scalar() or 0

        # Create version snapshot before amendment
        PurchaseOrderAmendmentService.create_version_snapshot(
            db, po, 'before_amendment', f"Before amendment {max_amendment + 1}", user_id=user_id
        )

        amendment = PurchaseOrderAmendment(
            purchase_order_id=data.purchase_order_id,
            amendment_number=max_amendment + 1,
            amendment_type=data.amendment_type,
            previous_values={
                'subtotal': float(po.subtotal) if po.subtotal else 0,
                'total': float(po.total) if po.total else 0
            },
            new_values=data.new_values,
            affected_items=[item.dict() for item in data.affected_items] if data.affected_items else None,
            previous_total=po.total,
            reason=data.reason,
            requested_by=user_id,
            status=AmendmentStatus.PENDING
        )
        db.add(amendment)
        db.commit()
        db.refresh(amendment)
        return amendment

    @staticmethod
    def approve_amendment(db: Session, amendment_id: int, user_id: int) -> PurchaseOrderAmendment:
        amendment = db.query(PurchaseOrderAmendment).filter(
            PurchaseOrderAmendment.id == amendment_id
        ).first()

        if amendment and amendment.status == AmendmentStatus.PENDING:
            amendment.status = AmendmentStatus.APPROVED
            amendment.approved_by = user_id
            amendment.approved_at = datetime.utcnow()
            db.commit()
            db.refresh(amendment)
        return amendment

    @staticmethod
    def apply_amendment(db: Session, amendment_id: int, user_id: int) -> PurchaseOrderAmendment:
        amendment = db.query(PurchaseOrderAmendment).filter(
            PurchaseOrderAmendment.id == amendment_id
        ).first()

        if not amendment or amendment.status != AmendmentStatus.APPROVED:
            raise ValueError("Amendment not approved")

        po = amendment.purchase_order

        # Apply item changes
        if amendment.affected_items:
            for change in amendment.affected_items:
                if change.get('field') and change.get('item_id'):
                    item = db.query(PurchaseOrderItem).filter(
                        PurchaseOrderItem.id == change['item_id']
                    ).first()
                    if item:
                        setattr(item, change['field'], change['new_value'])

        # Apply PO-level changes
        if amendment.new_values:
            for field, value in amendment.new_values.items():
                if hasattr(po, field):
                    setattr(po, field, value)

        # Recalculate totals
        po.subtotal = sum(item.quantity_ordered * item.unit_price for item in po.items)
        po.total = po.subtotal + (po.tax_amount or 0)

        amendment.new_total = po.total
        amendment.variance = po.total - (amendment.previous_total or 0)
        amendment.status = AmendmentStatus.APPLIED
        amendment.applied_at = datetime.utcnow()

        # Create version snapshot after amendment
        PurchaseOrderAmendmentService.create_version_snapshot(
            db, po, 'amended', f"Amendment {amendment.amendment_number} applied",
            amendment_id=amendment.id, user_id=user_id
        )

        db.commit()
        db.refresh(amendment)
        return amendment

    @staticmethod
    def get_version_history(db: Session, po_id: int) -> List[PurchaseOrderVersionHistory]:
        return db.query(PurchaseOrderVersionHistory).filter(
            PurchaseOrderVersionHistory.purchase_order_id == po_id
        ).order_by(PurchaseOrderVersionHistory.version_number.desc()).all()


class BlanketPurchaseOrderService:
    """Service for managing blanket/standing purchase orders"""

    @staticmethod
    def generate_blanket_number(db: Session, venue_id: int) -> str:
        today = date.today()
        prefix = f"BPO-{venue_id}-{today.strftime('%Y%m')}"
        count = db.query(BlanketPurchaseOrder).filter(
            BlanketPurchaseOrder.blanket_number.like(f"{prefix}%")
        ).count()
        return f"{prefix}-{count + 1:04d}"

    @staticmethod
    def create_blanket_order(db: Session, data: BlanketPurchaseOrderCreate, user_id: int) -> BlanketPurchaseOrder:
        blanket = BlanketPurchaseOrder(
            venue_id=data.venue_id,
            supplier_id=data.supplier_id,
            blanket_number=BlanketPurchaseOrderService.generate_blanket_number(db, data.venue_id),
            contract_reference=data.contract_reference,
            start_date=data.start_date,
            end_date=data.end_date,
            agreement_type=data.agreement_type,
            total_quantity_limit=data.total_quantity_limit,
            total_value_limit=data.total_value_limit,
            quantity_remaining=data.total_quantity_limit,
            value_remaining=data.total_value_limit,
            payment_terms=data.payment_terms,
            delivery_terms=data.delivery_terms,
            price_protection=data.price_protection,
            volume_discounts=data.volume_discounts,
            terms_and_conditions=data.terms_and_conditions,
            notes=data.notes,
            contract_document_url=data.contract_document_url,
            auto_renew=data.auto_renew,
            renewal_notice_days=data.renewal_notice_days,
            created_by=user_id,
            status=BlanketOrderStatus.DRAFT
        )
        db.add(blanket)
        db.flush()

        for item_data in data.items:
            item = BlanketPurchaseOrderItem(
                blanket_order_id=blanket.id,
                stock_item_id=item_data.stock_item_id,
                item_name=item_data.item_name,
                sku=item_data.sku,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                price_valid_until=item_data.price_valid_until,
                min_order_quantity=item_data.min_order_quantity,
                max_order_quantity=item_data.max_order_quantity,
                total_quantity_limit=item_data.total_quantity_limit,
                quantity_remaining=item_data.total_quantity_limit,
                volume_discounts=item_data.volume_discounts,
                notes=item_data.notes
            )
            db.add(item)

        db.commit()
        db.refresh(blanket)
        return blanket

    @staticmethod
    def create_release(db: Session, data: BlanketReleaseCreate, user_id: int) -> BlanketOrderRelease:
        blanket = db.query(BlanketPurchaseOrder).filter(
            BlanketPurchaseOrder.id == data.blanket_order_id
        ).first()

        if not blanket or blanket.status != BlanketOrderStatus.ACTIVE:
            raise ValueError("Blanket order not active")

        # Get next release number
        max_release = db.query(func.max(BlanketOrderRelease.release_number)).filter(
            BlanketOrderRelease.blanket_order_id == data.blanket_order_id
        ).scalar() or 0

        release = BlanketOrderRelease(
            blanket_order_id=data.blanket_order_id,
            release_number=max_release + 1,
            release_date=data.release_date,
            expected_delivery=data.expected_delivery,
            created_by=user_id,
            status="draft"
        )
        db.add(release)
        db.flush()

        total_quantity = 0
        total_value = 0

        for item_data in data.items:
            blanket_item = db.query(BlanketPurchaseOrderItem).filter(
                BlanketPurchaseOrderItem.id == item_data.blanket_item_id
            ).first()

            if not blanket_item:
                continue

            unit_price = item_data.unit_price or blanket_item.unit_price
            total_price = item_data.quantity * unit_price

            release_item = BlanketOrderReleaseItem(
                release_id=release.id,
                blanket_item_id=item_data.blanket_item_id,
                quantity=item_data.quantity,
                unit_price=unit_price,
                total_price=total_price,
                notes=item_data.notes
            )
            db.add(release_item)

            # Update blanket item quantities
            blanket_item.quantity_released += item_data.quantity
            if blanket_item.quantity_remaining:
                blanket_item.quantity_remaining -= item_data.quantity

            total_quantity += item_data.quantity
            total_value += total_price

        release.total_quantity = total_quantity
        release.total_value = total_value

        # Update blanket totals
        blanket.quantity_released += total_quantity
        blanket.value_released += total_value
        if blanket.quantity_remaining:
            blanket.quantity_remaining -= total_quantity
        if blanket.value_remaining:
            blanket.value_remaining -= total_value

        db.commit()
        db.refresh(release)
        return release

    @staticmethod
    def convert_release_to_po(db: Session, release_id: int, user_id: int) -> PurchaseOrder:
        release = db.query(BlanketOrderRelease).filter(
            BlanketOrderRelease.id == release_id
        ).first()

        if not release:
            raise ValueError("Release not found")

        blanket = release.blanket_order

        # Create PO from release
        order_number = f"PO-{blanket.venue_id}-{date.today().strftime('%Y%m%d')}-{release.release_number:04d}"

        po = PurchaseOrder(
            venue_id=blanket.venue_id,
            supplier_id=blanket.supplier_id,
            order_number=order_number,
            status=PurchaseOrderStatus.DRAFT,
            order_date=datetime.utcnow(),
            expected_date=release.expected_delivery,
            subtotal=release.total_value,
            total=release.total_value,
            notes=f"Generated from Blanket PO {blanket.blanket_number}, Release #{release.release_number}",
            created_by=user_id
        )
        db.add(po)
        db.flush()

        for release_item in release.items:
            blanket_item = release_item.blanket_item
            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                stock_item_id=blanket_item.stock_item_id,
                item_name=blanket_item.item_name,
                sku=blanket_item.sku,
                unit=blanket_item.unit,
                quantity_ordered=release_item.quantity,
                unit_price=release_item.unit_price,
                total_price=release_item.total_price
            )
            db.add(po_item)

        release.purchase_order_id = po.id
        release.status = "ordered"

        db.commit()
        db.refresh(po)
        return po


class PurchaseRequisitionService:
    """Service for managing purchase requisitions"""

    @staticmethod
    def generate_requisition_number(db: Session, venue_id: int) -> str:
        today = date.today()
        prefix = f"REQ-{venue_id}-{today.strftime('%Y%m%d')}"
        count = db.query(PurchaseRequisition).filter(
            PurchaseRequisition.requisition_number.like(f"{prefix}%")
        ).count()
        return f"{prefix}-{count + 1:04d}"

    @staticmethod
    def create_requisition(db: Session, data: PurchaseRequisitionCreate, user_id: int) -> PurchaseRequisition:
        requisition = PurchaseRequisition(
            venue_id=data.venue_id,
            requisition_number=PurchaseRequisitionService.generate_requisition_number(db, data.venue_id),
            department=data.department,
            cost_center=data.cost_center,
            request_date=data.request_date,
            required_by_date=data.required_by_date,
            priority=data.priority,
            budget_code=data.budget_code,
            budget_available=data.budget_available,
            suggested_supplier_id=data.suggested_supplier_id,
            business_justification=data.business_justification,
            notes=data.notes,
            requested_by=user_id,
            status=RequisitionStatus.DRAFT
        )
        db.add(requisition)
        db.flush()

        estimated_total = 0
        for item_data in data.items:
            item_total = (item_data.estimated_unit_price or 0) * item_data.quantity_requested
            item = PurchaseRequisitionItem(
                requisition_id=requisition.id,
                stock_item_id=item_data.stock_item_id,
                item_description=item_data.item_description,
                specifications=item_data.specifications,
                quantity_requested=item_data.quantity_requested,
                unit=item_data.unit,
                estimated_unit_price=item_data.estimated_unit_price,
                estimated_total=item_total,
                suggested_supplier_id=item_data.suggested_supplier_id,
                notes=item_data.notes
            )
            db.add(item)
            estimated_total += item_total

        requisition.estimated_total = estimated_total

        db.commit()
        db.refresh(requisition)
        return requisition

    @staticmethod
    def submit_requisition(db: Session, requisition_id: int) -> PurchaseRequisition:
        requisition = db.query(PurchaseRequisition).filter(
            PurchaseRequisition.id == requisition_id
        ).first()

        if requisition and requisition.status == RequisitionStatus.DRAFT:
            requisition.status = RequisitionStatus.SUBMITTED
            requisition.submitted_at = datetime.utcnow()
            db.commit()
            db.refresh(requisition)
        return requisition

    @staticmethod
    def approve_requisition(db: Session, requisition_id: int, user_id: int, comments: str = None) -> PurchaseRequisition:
        requisition = db.query(PurchaseRequisition).filter(
            PurchaseRequisition.id == requisition_id
        ).first()

        if requisition and requisition.status in [RequisitionStatus.SUBMITTED, RequisitionStatus.PENDING_APPROVAL]:
            requisition.status = RequisitionStatus.APPROVED

            # Record approval
            approval = RequisitionApproval(
                requisition_id=requisition_id,
                approval_level=1,
                approval_type="manager",
                status="approved",
                approved_by=user_id,
                approved_at=datetime.utcnow(),
                comments=comments
            )
            db.add(approval)

            db.commit()
            db.refresh(requisition)
        return requisition

    @staticmethod
    def convert_to_po(db: Session, data: RequisitionToPOConvert, user_id: int) -> PurchaseOrder:
        requisition = db.query(PurchaseRequisition).filter(
            PurchaseRequisition.id == data.requisition_id
        ).first()

        if not requisition or requisition.status != RequisitionStatus.APPROVED:
            raise ValueError("Requisition not approved")

        # Create PO
        order_number = f"PO-{requisition.venue_id}-{date.today().strftime('%Y%m%d')}-{requisition.id:04d}"

        subtotal = sum(item.get('quantity', 0) * item.get('unit_price', 0) for item in data.items)

        po = PurchaseOrder(
            venue_id=requisition.venue_id,
            supplier_id=data.supplier_id,
            order_number=order_number,
            status=PurchaseOrderStatus.DRAFT,
            order_date=datetime.utcnow(),
            expected_date=requisition.required_by_date,
            subtotal=subtotal,
            total=subtotal,
            notes=f"Generated from Requisition {requisition.requisition_number}",
            created_by=user_id
        )
        db.add(po)
        db.flush()

        items_converted = []
        for item_data in data.items:
            req_item = db.query(PurchaseRequisitionItem).filter(
                PurchaseRequisitionItem.id == item_data.get('req_item_id')
            ).first()

            if not req_item:
                continue

            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                stock_item_id=req_item.stock_item_id,
                item_name=req_item.item_description,
                unit=req_item.unit,
                quantity_ordered=item_data.get('quantity', req_item.quantity_requested),
                unit_price=item_data.get('unit_price', req_item.estimated_unit_price or 0),
                total_price=item_data.get('quantity', req_item.quantity_requested) * item_data.get('unit_price', req_item.estimated_unit_price or 0)
            )
            db.add(po_item)
            db.flush()

            # Update requisition item
            req_item.quantity_converted += item_data.get('quantity', req_item.quantity_requested)
            if req_item.quantity_converted >= req_item.quantity_requested:
                req_item.fully_converted = True

            items_converted.append({
                'req_item_id': req_item.id,
                'po_item_id': po_item.id,
                'quantity': item_data.get('quantity', req_item.quantity_requested)
            })

        # Create conversion record
        conversion = RequisitionToPO(
            requisition_id=requisition.id,
            purchase_order_id=po.id,
            converted_by=user_id,
            items_converted=items_converted
        )
        db.add(conversion)

        # Update requisition status
        all_converted = all(item.fully_converted for item in requisition.items)
        if all_converted:
            requisition.status = RequisitionStatus.CONVERTED
            requisition.converted_to_po = True
        else:
            requisition.status = RequisitionStatus.PARTIALLY_CONVERTED

        db.commit()
        db.refresh(po)
        return po


class LandedCostService:
    """Service for landed cost calculations"""

    @staticmethod
    def create_landed_cost(db: Session, data: PurchaseOrderLandedCostCreate, user_id: int) -> PurchaseOrderLandedCost:
        total_additional = (
            data.freight_cost + data.customs_duty + data.import_tax +
            data.customs_broker_fee + data.handling_fee + data.insurance_cost +
            data.inspection_fee + data.other_costs
        )

        landed_cost = PurchaseOrderLandedCost(
            purchase_order_id=data.purchase_order_id,
            grn_id=data.grn_id,
            merchandise_cost=data.merchandise_cost,
            freight_cost=data.freight_cost,
            freight_allocation_method=data.freight_allocation_method or "value",
            customs_duty=data.customs_duty,
            import_tax=data.import_tax,
            customs_broker_fee=data.customs_broker_fee,
            handling_fee=data.handling_fee,
            insurance_cost=data.insurance_cost,
            inspection_fee=data.inspection_fee,
            other_costs=data.other_costs,
            other_costs_description=data.other_costs_description,
            total_additional_costs=total_additional,
            total_landed_cost=data.merchandise_cost + total_additional,
            currency=data.currency,
            exchange_rate=data.exchange_rate,
            documents=data.documents,
            notes=data.notes,
            status="draft"
        )
        db.add(landed_cost)
        db.flush()

        # Create allocations
        for item_data in data.items:
            allocation = LandedCostAllocation(
                landed_cost_id=landed_cost.id,
                po_item_id=item_data.po_item_id,
                stock_item_id=item_data.stock_item_id,
                quantity=item_data.quantity,
                weight=item_data.weight,
                volume=item_data.volume,
                merchandise_value=item_data.merchandise_value,
                original_unit_cost=item_data.merchandise_value / item_data.quantity if item_data.quantity else 0,
                landed_unit_cost=item_data.merchandise_value / item_data.quantity if item_data.quantity else 0
            )
            db.add(allocation)

        db.commit()
        db.refresh(landed_cost)
        return landed_cost

    @staticmethod
    def calculate_allocations(db: Session, landed_cost_id: int, user_id: int) -> PurchaseOrderLandedCost:
        landed_cost = db.query(PurchaseOrderLandedCost).filter(
            PurchaseOrderLandedCost.id == landed_cost_id
        ).first()

        if not landed_cost:
            raise ValueError("Landed cost record not found")

        allocations = landed_cost.items
        method = landed_cost.freight_allocation_method or "value"

        # Calculate totals for allocation basis
        total_value = sum(a.merchandise_value for a in allocations)
        total_weight = sum(a.weight or 0 for a in allocations)
        total_volume = sum(a.volume or 0 for a in allocations)
        total_quantity = sum(a.quantity for a in allocations)

        for allocation in allocations:
            # Determine allocation ratio based on method
            if method == "value" and total_value > 0:
                ratio = float(allocation.merchandise_value) / float(total_value)
            elif method == "weight" and total_weight > 0:
                ratio = float(allocation.weight or 0) / float(total_weight)
            elif method == "volume" and total_volume > 0:
                ratio = float(allocation.volume or 0) / float(total_volume)
            elif method == "quantity" and total_quantity > 0:
                ratio = float(allocation.quantity) / float(total_quantity)
            else:
                ratio = 1 / len(allocations) if allocations else 0

            # Allocate costs
            allocation.allocated_freight = float(landed_cost.freight_cost) * ratio
            allocation.allocated_customs = float(landed_cost.customs_duty + landed_cost.import_tax) * ratio
            allocation.allocated_handling = float(landed_cost.handling_fee + landed_cost.customs_broker_fee) * ratio
            allocation.allocated_other = float(landed_cost.insurance_cost + landed_cost.inspection_fee + landed_cost.other_costs) * ratio
            allocation.total_allocated = (
                allocation.allocated_freight + allocation.allocated_customs +
                allocation.allocated_handling + allocation.allocated_other
            )

            # Calculate landed unit cost
            if allocation.quantity > 0:
                allocation.landed_unit_cost = (
                    float(allocation.merchandise_value) + float(allocation.total_allocated)
                ) / float(allocation.quantity)
                allocation.cost_increase_pct = (
                    (allocation.landed_unit_cost - float(allocation.original_unit_cost)) /
                    float(allocation.original_unit_cost) * 100
                ) if allocation.original_unit_cost else 0

        # Calculate average cost increase
        if total_value > 0:
            landed_cost.average_cost_increase_pct = (
                float(landed_cost.total_additional_costs) / float(total_value) * 100
            )

        landed_cost.status = "calculated"
        landed_cost.calculated_by = user_id
        landed_cost.calculated_at = datetime.utcnow()

        db.commit()
        db.refresh(landed_cost)
        return landed_cost

    @staticmethod
    def apply_to_inventory(db: Session, landed_cost_id: int, user_id: int) -> PurchaseOrderLandedCost:
        landed_cost = db.query(PurchaseOrderLandedCost).filter(
            PurchaseOrderLandedCost.id == landed_cost_id
        ).first()

        if not landed_cost or landed_cost.status != "calculated":
            raise ValueError("Landed cost not calculated")

        for allocation in landed_cost.items:
            if allocation.stock_item_id:
                stock_item = db.query(StockItem).filter(
                    StockItem.id == allocation.stock_item_id
                ).first()
                if stock_item:
                    stock_item.cost_per_unit = allocation.landed_unit_cost
                    allocation.applied_to_stock = True
                    allocation.applied_at = datetime.utcnow()

        landed_cost.status = "applied"
        landed_cost.applied_by = user_id
        landed_cost.applied_at = datetime.utcnow()

        db.commit()
        db.refresh(landed_cost)
        return landed_cost


class FinancialIntegrationService:
    """Service for accounts payable and financial integration"""

    @staticmethod
    def generate_payment_number(db: Session, venue_id: int) -> str:
        today = date.today()
        prefix = f"PAY-{venue_id}-{today.strftime('%Y%m%d')}"
        count = db.query(SupplierPayment).filter(
            SupplierPayment.payment_number.like(f"{prefix}%")
        ).count()
        return f"{prefix}-{count + 1:04d}"

    @staticmethod
    def create_payment(db: Session, data: SupplierPaymentCreate, user_id: int) -> SupplierPayment:
        net_payment = data.payment_amount - data.discount_taken - data.credits_applied

        payment = SupplierPayment(
            venue_id=data.venue_id,
            supplier_id=data.supplier_id,
            payment_number=FinancialIntegrationService.generate_payment_number(db, data.venue_id),
            payment_reference=data.payment_reference,
            payment_date=data.payment_date,
            payment_method=data.payment_method,
            payment_amount=data.payment_amount,
            discount_taken=data.discount_taken,
            credits_applied=data.credits_applied,
            net_payment=net_payment,
            currency=data.currency,
            exchange_rate=data.exchange_rate,
            bank_account=data.bank_account,
            notes=data.notes,
            created_by=user_id,
            status="pending"
        )
        db.add(payment)
        db.flush()

        for alloc_data in data.allocations:
            allocation = PaymentAllocation(
                payment_id=payment.id,
                invoice_id=alloc_data.invoice_id,
                allocated_amount=alloc_data.allocated_amount,
                discount_amount=alloc_data.discount_amount,
                allocation_date=data.payment_date,
                notes=alloc_data.notes
            )
            db.add(allocation)

        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def update_supplier_balance(db: Session, venue_id: int, supplier_id: int):
        """Recalculate supplier account balance"""
        from app.models.enhanced_inventory import SupplierInvoice

        balance = db.query(SupplierAccountBalance).filter(
            and_(
                SupplierAccountBalance.venue_id == venue_id,
                SupplierAccountBalance.supplier_id == supplier_id
            )
        ).first()

        if not balance:
            balance = SupplierAccountBalance(
                venue_id=venue_id,
                supplier_id=supplier_id
            )
            db.add(balance)

        # Calculate totals
        total_invoiced = db.query(func.sum(SupplierInvoice.total_amount)).filter(
            and_(
                SupplierInvoice.venue_id == venue_id,
                SupplierInvoice.supplier_id == supplier_id
            )
        ).scalar() or 0

        total_paid = db.query(func.sum(PaymentAllocation.allocated_amount)).join(
            SupplierPayment
        ).filter(
            and_(
                SupplierPayment.venue_id == venue_id,
                SupplierPayment.supplier_id == supplier_id,
                SupplierPayment.status == "completed"
            )
        ).scalar() or 0

        total_credits = db.query(func.sum(SupplierCreditNote.total_amount)).filter(
            and_(
                SupplierCreditNote.venue_id == venue_id,
                SupplierCreditNote.supplier_id == supplier_id,
                SupplierCreditNote.status != CreditNoteStatus.CANCELLED
            )
        ).scalar() or 0

        balance.total_invoiced = total_invoiced
        balance.total_paid = total_paid
        balance.total_credits = total_credits
        balance.current_balance = total_invoiced - total_paid - total_credits

        # Calculate aging
        today = date.today()

        # Get unpaid invoices
        unpaid_invoices = db.query(SupplierInvoice).filter(
            and_(
                SupplierInvoice.venue_id == venue_id,
                SupplierInvoice.supplier_id == supplier_id,
                SupplierInvoice.payment_status != "paid"
            )
        ).all()

        balance.current_amount = 0
        balance.aging_1_30 = 0
        balance.aging_31_60 = 0
        balance.aging_61_90 = 0
        balance.aging_over_90 = 0

        for invoice in unpaid_invoices:
            due_date = invoice.due_date
            if not due_date:
                continue

            days_overdue = (today - due_date).days if due_date < today else 0
            amount = float(invoice.total_amount) - float(invoice.amount_paid or 0)

            if days_overdue <= 0:
                balance.current_amount += amount
            elif days_overdue <= 30:
                balance.aging_1_30 += amount
            elif days_overdue <= 60:
                balance.aging_31_60 += amount
            elif days_overdue <= 90:
                balance.aging_61_90 += amount
            else:
                balance.aging_over_90 += amount

        db.commit()
        return balance

    @staticmethod
    def create_aging_snapshot(db: Session, venue_id: int) -> InvoiceAgingSnapshot:
        """Create periodic aging snapshot for reporting"""
        today = date.today()

        # Check if snapshot exists for today
        existing = db.query(InvoiceAgingSnapshot).filter(
            and_(
                InvoiceAgingSnapshot.venue_id == venue_id,
                InvoiceAgingSnapshot.snapshot_date == today
            )
        ).first()

        if existing:
            return existing

        # Get all supplier balances
        balances = db.query(SupplierAccountBalance).filter(
            SupplierAccountBalance.venue_id == venue_id
        ).all()

        snapshot = InvoiceAgingSnapshot(
            venue_id=venue_id,
            snapshot_date=today,
            total_outstanding=sum(b.current_balance for b in balances),
            current_total=sum(b.current_amount for b in balances),
            aging_1_30_total=sum(b.aging_1_30 for b in balances),
            aging_31_60_total=sum(b.aging_31_60 for b in balances),
            aging_61_90_total=sum(b.aging_61_90 for b in balances),
            aging_over_90_total=sum(b.aging_over_90 for b in balances),
            supplier_breakdown=[{
                'supplier_id': b.supplier_id,
                'current': float(b.current_amount),
                'aging_1_30': float(b.aging_1_30),
                'aging_31_60': float(b.aging_31_60),
                'aging_61_90': float(b.aging_61_90),
                'aging_over_90': float(b.aging_over_90),
                'total': float(b.current_balance)
            } for b in balances],
            invoice_count=len(balances),
            overdue_count=sum(1 for b in balances if b.aging_1_30 + b.aging_31_60 + b.aging_61_90 + b.aging_over_90 > 0)
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot


class QualityControlService:
    """Service for quality control inspections"""

    @staticmethod
    def generate_inspection_number(db: Session, venue_id: int) -> str:
        today = date.today()
        prefix = f"QC-{venue_id}-{today.strftime('%Y%m%d')}"
        count = db.query(QualityControlInspection).filter(
            QualityControlInspection.inspection_number.like(f"{prefix}%")
        ).count()
        return f"{prefix}-{count + 1:04d}"

    @staticmethod
    def create_checklist(db: Session, data: QualityControlChecklistCreate) -> QualityControlChecklist:
        checklist = QualityControlChecklist(
            venue_id=data.venue_id,
            name=data.name,
            description=data.description,
            applies_to_category=data.applies_to_category,
            applies_to_supplier_id=data.applies_to_supplier_id,
            checklist_items=[item.dict() for item in data.checklist_items],
            requires_photos=data.requires_photos,
            requires_temperature=data.requires_temperature,
            auto_reject_threshold=data.auto_reject_threshold,
            is_active=True
        )
        db.add(checklist)
        db.commit()
        db.refresh(checklist)
        return checklist

    @staticmethod
    def create_inspection(db: Session, data: QualityControlInspectionCreate, user_id: int) -> QualityControlInspection:
        inspection = QualityControlInspection(
            venue_id=data.venue_id,
            grn_id=data.grn_id,
            grn_item_id=data.grn_item_id,
            stock_item_id=data.stock_item_id,
            checklist_id=data.checklist_id,
            inspection_number=QualityControlService.generate_inspection_number(db, data.venue_id),
            checklist_responses=[r.dict() for r in data.checklist_responses] if data.checklist_responses else None,
            temperature_reading=data.temperature_reading,
            temperature_unit=data.temperature_unit,
            photos=data.photos,
            documents=data.documents,
            disposition=data.disposition,
            disposition_reason=data.disposition_reason,
            notes=data.notes,
            inspected_by=user_id,
            status=QCStatus.PENDING
        )
        db.add(inspection)
        db.commit()
        db.refresh(inspection)
        return inspection

    @staticmethod
    def complete_inspection(db: Session, inspection_id: int, data: QualityControlInspectionUpdate, user_id: int) -> QualityControlInspection:
        inspection = db.query(QualityControlInspection).filter(
            QualityControlInspection.id == inspection_id
        ).first()

        if not inspection:
            raise ValueError("Inspection not found")

        if data.checklist_responses:
            inspection.checklist_responses = data.checklist_responses
            # Calculate pass/fail counts
            passed = sum(1 for r in data.checklist_responses if r.get('passed', False))
            failed = len(data.checklist_responses) - passed
            inspection.items_passed = passed
            inspection.items_failed = failed
            if len(data.checklist_responses) > 0:
                inspection.overall_score = (passed / len(data.checklist_responses)) * 100

        if data.status:
            inspection.status = data.status
        if data.temperature_reading:
            inspection.temperature_reading = data.temperature_reading
        if data.photos:
            inspection.photos = data.photos
        if data.quantity_accepted is not None:
            inspection.quantity_accepted = data.quantity_accepted
        if data.quantity_rejected is not None:
            inspection.quantity_rejected = data.quantity_rejected
        if data.quantity_quarantined is not None:
            inspection.quantity_quarantined = data.quantity_quarantined
        if data.disposition:
            inspection.disposition = data.disposition
        if data.disposition_reason:
            inspection.disposition_reason = data.disposition_reason
        if data.requires_follow_up is not None:
            inspection.requires_follow_up = data.requires_follow_up
        if data.follow_up_notes:
            inspection.follow_up_notes = data.follow_up_notes
        if data.notes:
            inspection.notes = data.notes

        inspection.reviewed_by = user_id
        inspection.reviewed_at = datetime.utcnow()

        db.commit()
        db.refresh(inspection)
        return inspection

    @staticmethod
    def create_quality_issue(db: Session, data: QualityIssueCreate, user_id: int) -> QualityIssue:
        # Generate issue number
        today = date.today()
        prefix = f"QI-{data.venue_id}-{today.strftime('%Y%m%d')}"
        count = db.query(QualityIssue).filter(
            QualityIssue.issue_number.like(f"{prefix}%")
        ).count()
        issue_number = f"{prefix}-{count + 1:04d}"

        issue = QualityIssue(
            venue_id=data.venue_id,
            supplier_id=data.supplier_id,
            inspection_id=data.inspection_id,
            grn_id=data.grn_id,
            po_id=data.po_id,
            stock_item_id=data.stock_item_id,
            issue_number=issue_number,
            issue_type=data.issue_type,
            severity=data.severity,
            description=data.description,
            affected_quantity=data.affected_quantity,
            affected_value=data.affected_value,
            corrective_action_required=data.corrective_action_required,
            corrective_action=data.corrective_action,
            corrective_action_deadline=data.corrective_action_deadline,
            credit_requested=data.credit_requested,
            reported_by=user_id,
            status="open"
        )
        db.add(issue)
        db.commit()
        db.refresh(issue)
        return issue


class StockReorderService:
    """Service for stock reorder management"""

    @staticmethod
    def create_reorder_config(db: Session, data: StockReorderConfigCreate) -> StockReorderConfig:
        config = StockReorderConfig(
            venue_id=data.venue_id,
            stock_item_id=data.stock_item_id,
            min_stock_level=data.min_stock_level,
            max_stock_level=data.max_stock_level,
            safety_stock=data.safety_stock,
            reorder_quantity=data.reorder_quantity,
            reorder_method=data.reorder_method,
            days_of_supply=data.days_of_supply,
            lead_time_days=data.lead_time_days,
            lead_time_variance_days=data.lead_time_variance_days,
            seasonal_adjustments=data.seasonal_adjustments,
            warehouse_id=data.warehouse_id,
            preferred_supplier_id=data.preferred_supplier_id,
            auto_order_enabled=data.auto_order_enabled,
            auto_order_threshold=data.auto_order_threshold,
            require_approval=data.require_approval,
            abc_class=data.abc_class,
            is_active=True
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def check_reorder_levels(db: Session, venue_id: int) -> List[ReorderAlert]:
        """Check all items against their reorder levels and create alerts"""
        configs = db.query(StockReorderConfig).filter(
            and_(
                StockReorderConfig.venue_id == venue_id,
                StockReorderConfig.is_active == True
            )
        ).all()

        alerts = []
        for config in configs:
            stock_item = db.query(StockItem).filter(
                StockItem.id == config.stock_item_id
            ).first()

            if not stock_item:
                continue

            current_stock = float(stock_item.current_quantity or 0)
            min_level = float(config.min_stock_level)
            safety_stock = float(config.safety_stock or 0)

            # Check for existing active alert
            existing_alert = db.query(ReorderAlert).filter(
                and_(
                    ReorderAlert.venue_id == venue_id,
                    ReorderAlert.stock_item_id == config.stock_item_id,
                    ReorderAlert.status == "active"
                )
            ).first()

            if existing_alert:
                continue

            alert_type = None
            priority = "normal"

            if current_stock <= 0:
                alert_type = "stockout"
                priority = "critical"
            elif current_stock <= safety_stock:
                alert_type = "below_safety"
                priority = "high"
            elif current_stock <= min_level:
                alert_type = "below_min"
                priority = "normal"

            if alert_type:
                # Calculate suggested quantity
                if config.reorder_method == "to_max":
                    suggested_qty = float(config.max_stock_level) - current_stock
                elif config.reorder_method == "fixed_qty":
                    suggested_qty = float(config.reorder_quantity or 0)
                else:
                    suggested_qty = float(config.max_stock_level) - current_stock

                alert = ReorderAlert(
                    venue_id=venue_id,
                    stock_item_id=config.stock_item_id,
                    alert_type=alert_type,
                    current_stock=current_stock,
                    min_level=min_level,
                    suggested_quantity=suggested_qty,
                    suggested_supplier_id=config.preferred_supplier_id,
                    priority=priority,
                    status="active"
                )
                db.add(alert)
                alerts.append(alert)

        db.commit()
        return alerts

    @staticmethod
    def get_active_alerts(db: Session, venue_id: int) -> List[ReorderAlert]:
        return db.query(ReorderAlert).filter(
            and_(
                ReorderAlert.venue_id == venue_id,
                ReorderAlert.status == "active"
            )
        ).order_by(
            ReorderAlert.priority.desc(),
            ReorderAlert.created_at.desc()
        ).all()


class PartialDeliveryService:
    """Service for managing partial deliveries"""

    @staticmethod
    def create_delivery_schedule(db: Session, data: PartialDeliveryScheduleCreate) -> PartialDeliverySchedule:
        # Get next delivery number
        max_delivery = db.query(func.max(PartialDeliverySchedule.delivery_number)).filter(
            PartialDeliverySchedule.purchase_order_id == data.purchase_order_id
        ).scalar() or 0

        schedule = PartialDeliverySchedule(
            purchase_order_id=data.purchase_order_id,
            delivery_number=max_delivery + 1,
            expected_date=data.expected_date,
            shipping_reference=data.shipping_reference,
            carrier=data.carrier,
            tracking_number=data.tracking_number,
            notes=data.notes,
            status="scheduled"
        )
        db.add(schedule)
        db.flush()

        total_quantity = 0
        total_value = 0

        for item_data in data.items:
            po_item = db.query(PurchaseOrderItem).filter(
                PurchaseOrderItem.id == item_data.po_item_id
            ).first()

            item = PartialDeliveryItem(
                schedule_id=schedule.id,
                po_item_id=item_data.po_item_id,
                quantity_scheduled=item_data.quantity_scheduled,
                notes=item_data.notes
            )
            db.add(item)

            total_quantity += item_data.quantity_scheduled
            if po_item:
                total_value += item_data.quantity_scheduled * float(po_item.unit_price)

        schedule.total_quantity = total_quantity
        schedule.total_value = total_value

        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def create_backorder(db: Session, data: BackorderTrackingCreate) -> BackorderTracking:
        backorder = BackorderTracking(
            venue_id=data.venue_id,
            purchase_order_id=data.purchase_order_id,
            po_item_id=data.po_item_id,
            quantity_backordered=data.quantity_backordered,
            original_expected_date=data.original_expected_date,
            new_expected_date=data.new_expected_date,
            supplier_notes=data.supplier_notes,
            notes=data.notes,
            status="pending"
        )
        db.add(backorder)
        db.commit()
        db.refresh(backorder)
        return backorder

    @staticmethod
    def update_backorder(db: Session, backorder_id: int, data: BackorderTrackingUpdate) -> BackorderTracking:
        backorder = db.query(BackorderTracking).filter(
            BackorderTracking.id == backorder_id
        ).first()

        if not backorder:
            raise ValueError("Backorder not found")

        for field, value in data.dict(exclude_unset=True).items():
            setattr(backorder, field, value)

        db.commit()
        db.refresh(backorder)
        return backorder


class ConsolidatedPurchasingService:
    """Service for consolidated multi-location purchasing"""

    @staticmethod
    def generate_consolidated_number(db: Session, tenant_id: int) -> str:
        today = date.today()
        prefix = f"CPO-{tenant_id}-{today.strftime('%Y%m%d')}"
        count = db.query(ConsolidatedPurchaseOrder).filter(
            ConsolidatedPurchaseOrder.consolidated_number.like(f"{prefix}%")
        ).count()
        return f"{prefix}-{count + 1:04d}"

    @staticmethod
    def create_consolidated_order(db: Session, data: ConsolidatedPurchaseOrderCreate, user_id: int) -> ConsolidatedPurchaseOrder:
        consolidated = ConsolidatedPurchaseOrder(
            tenant_id=data.tenant_id,
            supplier_id=data.supplier_id,
            consolidated_number=ConsolidatedPurchasingService.generate_consolidated_number(db, data.tenant_id),
            collection_start=data.collection_start,
            collection_end=data.collection_end,
            expected_delivery=data.expected_delivery,
            delivery_warehouse_id=data.delivery_warehouse_id,
            delivery_address=data.delivery_address,
            notes=data.notes,
            venue_count=len(data.venue_orders),
            created_by=user_id,
            status=ConsolidatedOrderStatus.DRAFT
        )
        db.add(consolidated)
        db.flush()

        # Add venue participations
        for venue_data in data.venue_orders:
            venue_order = ConsolidatedOrderVenue(
                consolidated_order_id=consolidated.id,
                venue_id=venue_data.venue_id,
                source_requisition_id=venue_data.source_requisition_id,
                notes=venue_data.notes
            )
            db.add(venue_order)

        # Add consolidated items
        total_quantity = 0
        subtotal = 0

        for item_data in data.items:
            net_price = item_data.unit_price * (1 - item_data.volume_discount_pct / 100)
            total_price = item_data.total_quantity * net_price

            item = ConsolidatedOrderItem(
                consolidated_order_id=consolidated.id,
                stock_item_id=item_data.stock_item_id,
                item_name=item_data.item_name,
                sku=item_data.sku,
                unit=item_data.unit,
                total_quantity=item_data.total_quantity,
                unit_price=item_data.unit_price,
                volume_discount_pct=item_data.volume_discount_pct,
                net_unit_price=net_price,
                total_price=total_price,
                venue_breakdown=item_data.venue_breakdown,
                notes=item_data.notes
            )
            db.add(item)

            total_quantity += item_data.total_quantity
            subtotal += total_price

        consolidated.total_quantity = total_quantity
        consolidated.subtotal = subtotal
        consolidated.total = subtotal

        db.commit()
        db.refresh(consolidated)
        return consolidated

    @staticmethod
    def distribute_to_venues(db: Session, consolidated_id: int, user_id: int) -> List[PurchaseOrder]:
        """Create individual POs for each venue from the consolidated order"""
        consolidated = db.query(ConsolidatedPurchaseOrder).filter(
            ConsolidatedPurchaseOrder.id == consolidated_id
        ).first()

        if not consolidated or consolidated.status != ConsolidatedOrderStatus.ORDERED:
            raise ValueError("Consolidated order not in ordered status")

        generated_pos = []

        for venue_order in consolidated.venue_orders:
            # Calculate venue's items from breakdown
            venue_items = []
            venue_total = 0

            for item in consolidated.items:
                for breakdown in item.venue_breakdown:
                    if breakdown.get('venue_id') == venue_order.venue_id:
                        venue_items.append({
                            'item': item,
                            'quantity': breakdown.get('quantity', 0),
                            'amount': breakdown.get('amount', 0)
                        })
                        venue_total += breakdown.get('amount', 0)
                        break

            if not venue_items:
                continue

            # Create PO for this venue
            order_number = f"PO-{venue_order.venue_id}-{date.today().strftime('%Y%m%d')}-CPO{consolidated.id}"

            po = PurchaseOrder(
                venue_id=venue_order.venue_id,
                supplier_id=consolidated.supplier_id,
                order_number=order_number,
                status=PurchaseOrderStatus.ORDERED,
                order_date=consolidated.order_date,
                expected_date=consolidated.expected_delivery,
                subtotal=venue_total,
                total=venue_total,
                notes=f"Distributed from Consolidated PO {consolidated.consolidated_number}",
                created_by=user_id
            )
            db.add(po)
            db.flush()

            for venue_item in venue_items:
                item = venue_item['item']
                po_item = PurchaseOrderItem(
                    purchase_order_id=po.id,
                    stock_item_id=item.stock_item_id,
                    item_name=item.item_name,
                    sku=item.sku,
                    unit=item.unit,
                    quantity_ordered=venue_item['quantity'],
                    unit_price=float(item.net_unit_price),
                    total_price=venue_item['amount']
                )
                db.add(po_item)

            venue_order.generated_po_id = po.id
            venue_order.distribution_status = "in_transit"
            generated_pos.append(po)

        consolidated.status = ConsolidatedOrderStatus.DISTRIBUTING
        db.commit()

        return generated_pos
