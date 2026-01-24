"""Export service: Generate order drafts, CSVs, PDFs, and email templates."""

import csv
import io
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
import logging

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.reconciliation import (
    ReorderProposal,
    SupplierOrderDraft,
    OrderDraftStatus,
)
from app.models.supplier import Supplier
from app.models.product import Product
from app.core.config import settings

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting order drafts to various formats."""

    def __init__(self, db: Session):
        self.db = db
        self.export_dir = getattr(settings, 'EXPORT_DIR', '/tmp/exports')
        os.makedirs(self.export_dir, exist_ok=True)

    def create_order_drafts(
        self,
        session_id: int,
        requested_delivery_date: Optional[datetime] = None,
        clear_previous: bool = True,
    ) -> List[SupplierOrderDraft]:
        """
        Create supplier order drafts from reorder proposals.
        Groups proposals by supplier.
        """
        # Clear previous drafts if requested
        if clear_previous:
            self.db.query(SupplierOrderDraft).filter(
                SupplierOrderDraft.session_id == session_id
            ).delete()

        # Get included proposals
        proposals = (
            self.db.query(ReorderProposal)
            .filter(ReorderProposal.session_id == session_id)
            .filter(ReorderProposal.included == True)
            .all()
        )

        if not proposals:
            logger.warning(f"No included proposals for session {session_id}")
            return []

        # Get product info
        product_ids = list(set(p.product_id for p in proposals))
        products = {
            p.id: p
            for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()
        }

        # Group by supplier
        supplier_proposals: Dict[int, List[ReorderProposal]] = {}
        for proposal in proposals:
            supplier_id = proposal.supplier_id or 0
            if supplier_id not in supplier_proposals:
                supplier_proposals[supplier_id] = []
            supplier_proposals[supplier_id].append(proposal)

        drafts = []

        for supplier_id, props in supplier_proposals.items():
            if supplier_id == 0:
                continue  # Skip products without supplier

            # Build line items for payload
            line_items = []
            total_qty = Decimal("0")
            total_value = Decimal("0")

            for prop in props:
                product = products.get(prop.product_id)
                order_qty = prop.user_qty if prop.user_qty is not None else prop.rounded_qty

                line_item = {
                    "product_id": prop.product_id,
                    "product_name": product.name if product else "Unknown",
                    "barcode": product.barcode if product else None,
                    "sku": getattr(product, 'sku', None) if product else None,
                    "qty": float(order_qty),
                    "pack_size": prop.pack_size,
                    "unit_cost": float(prop.unit_cost) if prop.unit_cost else None,
                    "line_total": float(order_qty * prop.unit_cost) if prop.unit_cost else None,
                }
                line_items.append(line_item)
                total_qty += order_qty
                if prop.unit_cost:
                    total_value += order_qty * prop.unit_cost

            # Create draft
            draft = SupplierOrderDraft(
                session_id=session_id,
                supplier_id=supplier_id,
                status=OrderDraftStatus.DRAFT,
                payload_json=json.dumps(line_items),
                line_count=len(line_items),
                total_qty=total_qty,
                total_value=total_value if total_value > 0 else None,
                requested_delivery_date=requested_delivery_date,
            )

            self.db.add(draft)
            drafts.append(draft)

        self.db.flush()

        logger.info(f"Created {len(drafts)} order drafts for session {session_id}")
        return drafts

    def export_to_csv(
        self,
        draft_id: int,
    ) -> str:
        """
        Export order draft to CSV file.
        Returns the file path.
        """
        draft = self.db.query(SupplierOrderDraft).filter(
            SupplierOrderDraft.id == draft_id
        ).first()

        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        supplier = self.db.query(Supplier).filter(
            Supplier.id == draft.supplier_id
        ).first()

        # Parse line items
        line_items = json.loads(draft.payload_json) if draft.payload_json else []

        # Generate filename
        supplier_name = supplier.name.replace(" ", "_") if supplier else "Unknown"
        filename = f"order_{draft.id}_{supplier_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.export_dir, filename)

        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header row
            writer.writerow([
                "Product Name",
                "Barcode",
                "SKU",
                "Quantity",
                "Pack Size",
                "Unit Cost",
                "Line Total",
            ])

            # Data rows
            for item in line_items:
                writer.writerow([
                    item.get("product_name", ""),
                    item.get("barcode", ""),
                    item.get("sku", ""),
                    item.get("qty", 0),
                    item.get("pack_size", 1),
                    item.get("unit_cost", ""),
                    item.get("line_total", ""),
                ])

            # Total row
            writer.writerow([])
            writer.writerow(["", "", "", "Total Qty:", float(draft.total_qty), "Total Value:", float(draft.total_value) if draft.total_value else ""])

        # Update draft with export path
        draft.exported_csv_path = filepath
        if draft.status == OrderDraftStatus.DRAFT:
            draft.status = OrderDraftStatus.EXPORTED

        self.db.flush()

        logger.info(f"Exported draft {draft_id} to CSV: {filepath}")
        return filepath

    def export_to_pdf(
        self,
        draft_id: int,
    ) -> str:
        """
        Export order draft to PDF file.
        Returns the file path.
        """
        draft = self.db.query(SupplierOrderDraft).filter(
            SupplierOrderDraft.id == draft_id
        ).first()

        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        supplier = self.db.query(Supplier).filter(
            Supplier.id == draft.supplier_id
        ).first()

        # Parse line items
        line_items = json.loads(draft.payload_json) if draft.payload_json else []

        # Generate filename
        supplier_name = supplier.name.replace(" ", "_") if supplier else "Unknown"
        filename = f"order_{draft.id}_{supplier_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(self.export_dir, filename)

        # Create PDF
        doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=20,
        )

        elements = []

        # Title
        elements.append(Paragraph(f"Purchase Order - Draft #{draft.id}", title_style))

        # Supplier info
        if supplier:
            elements.append(Paragraph(f"<b>Supplier:</b> {supplier.name}", styles["Normal"]))
            if supplier.contact_phone:
                elements.append(Paragraph(f"<b>Phone:</b> {supplier.contact_phone}", styles["Normal"]))
            if supplier.contact_email:
                elements.append(Paragraph(f"<b>Email:</b> {supplier.contact_email}", styles["Normal"]))

        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))

        if draft.requested_delivery_date:
            elements.append(Paragraph(
                f"<b>Requested Delivery:</b> {draft.requested_delivery_date.strftime('%Y-%m-%d')}",
                styles["Normal"]
            ))

        elements.append(Spacer(1, 1 * cm))

        # Items table
        table_data = [["#", "Product", "Barcode", "Qty", "Pack", "Unit Cost", "Total"]]

        for idx, item in enumerate(line_items, 1):
            table_data.append([
                str(idx),
                str(item.get("product_name", ""))[:30],  # Truncate long names
                str(item.get("barcode", "")) or "",
                str(item.get("qty", 0)),
                str(item.get("pack_size", 1)),
                f"{item.get('unit_cost', 0):.2f}" if item.get("unit_cost") else "-",
                f"{item.get('line_total', 0):.2f}" if item.get("line_total") else "-",
            ])

        # Add total row
        table_data.append([
            "", "", "", "", "",
            "Total:",
            f"{float(draft.total_value):.2f}" if draft.total_value else "-"
        ])

        table = Table(table_data, colWidths=[1 * cm, 6 * cm, 3 * cm, 2 * cm, 1.5 * cm, 2 * cm, 2 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -2), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))

        elements.append(table)

        # Notes
        if draft.notes:
            elements.append(Spacer(1, 1 * cm))
            elements.append(Paragraph(f"<b>Notes:</b> {draft.notes}", styles["Normal"]))

        doc.build(elements)

        # Update draft with export path
        draft.exported_pdf_path = filepath
        if draft.status == OrderDraftStatus.DRAFT:
            draft.status = OrderDraftStatus.EXPORTED

        self.db.flush()

        logger.info(f"Exported draft {draft_id} to PDF: {filepath}")
        return filepath

    def generate_email_template(
        self,
        draft_id: int,
        business_name: str = "Our Business",
    ) -> Dict:
        """
        Generate email template for a supplier order draft.
        Returns dict with subject, body, and attachment paths.
        """
        draft = self.db.query(SupplierOrderDraft).filter(
            SupplierOrderDraft.id == draft_id
        ).first()

        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        supplier = self.db.query(Supplier).filter(
            Supplier.id == draft.supplier_id
        ).first()

        # Parse line items for summary
        line_items = json.loads(draft.payload_json) if draft.payload_json else []

        # Build email subject
        supplier_name = supplier.name if supplier else "Supplier"
        subject = f"Purchase Order - {business_name} - {datetime.now().strftime('%Y-%m-%d')}"

        # Build email body
        lines = []
        lines.append(f"Dear {supplier_name} Team,")
        lines.append("")
        lines.append(f"Please find attached our purchase order with {draft.line_count} items.")
        lines.append("")

        if draft.requested_delivery_date:
            lines.append(f"Requested delivery date: {draft.requested_delivery_date.strftime('%Y-%m-%d')}")
            lines.append("")

        lines.append("Order Summary:")
        lines.append(f"  - Total items: {draft.line_count}")
        lines.append(f"  - Total quantity: {float(draft.total_qty)}")
        if draft.total_value:
            lines.append(f"  - Estimated value: ${float(draft.total_value):.2f}")
        lines.append("")

        # Top items preview
        lines.append("Items include:")
        for item in line_items[:5]:  # Show first 5 items
            lines.append(f"  - {item.get('product_name', 'Unknown')}: {item.get('qty', 0)} units")
        if len(line_items) > 5:
            lines.append(f"  ... and {len(line_items) - 5} more items")
        lines.append("")

        if draft.notes:
            lines.append(f"Notes: {draft.notes}")
            lines.append("")

        lines.append("Please confirm receipt and expected delivery date.")
        lines.append("")
        lines.append("Best regards,")
        lines.append(business_name)

        body = "\n".join(lines)

        # Collect attachment paths
        attachments = []
        if draft.exported_csv_path:
            attachments.append(draft.exported_csv_path)
        if draft.exported_pdf_path:
            attachments.append(draft.exported_pdf_path)

        return {
            "draft_id": draft_id,
            "supplier_name": supplier_name,
            "supplier_email": supplier.contact_email if supplier else None,
            "subject": subject,
            "body": body,
            "attachment_paths": attachments,
        }

    def generate_whatsapp_text(
        self,
        draft_id: int,
    ) -> str:
        """Generate WhatsApp-ready text for a supplier order."""
        draft = self.db.query(SupplierOrderDraft).filter(
            SupplierOrderDraft.id == draft_id
        ).first()

        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        supplier = self.db.query(Supplier).filter(
            Supplier.id == draft.supplier_id
        ).first()

        # Parse line items
        line_items = json.loads(draft.payload_json) if draft.payload_json else []

        lines = []
        lines.append(f"*PURCHASE ORDER #{draft.id}*")
        lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        if supplier:
            lines.append(f"Supplier: {supplier.name}")
        lines.append("")
        lines.append("*Items:*")

        for item in line_items:
            qty = item.get("qty", 0)
            name = item.get("product_name", "Unknown")
            lines.append(f"• {name}: {qty}")

        lines.append("")
        lines.append(f"Total items: {draft.line_count}")
        lines.append(f"Total quantity: {float(draft.total_qty)}")

        if draft.total_value:
            lines.append(f"Total value: ${float(draft.total_value):.2f}")

        if draft.requested_delivery_date:
            lines.append("")
            lines.append(f"Requested delivery: {draft.requested_delivery_date.strftime('%Y-%m-%d')}")

        if draft.notes:
            lines.append("")
            lines.append(f"Notes: {draft.notes}")

        return "\n".join(lines)

    def finalize_draft(
        self,
        draft_id: int,
    ) -> SupplierOrderDraft:
        """Mark a draft as finalized (ready for sending)."""
        draft = self.db.query(SupplierOrderDraft).filter(
            SupplierOrderDraft.id == draft_id
        ).first()

        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        draft.status = OrderDraftStatus.FINALIZED
        self.db.flush()

        return draft

    def mark_as_sent(
        self,
        draft_id: int,
    ) -> SupplierOrderDraft:
        """Mark a draft as sent to supplier."""
        draft = self.db.query(SupplierOrderDraft).filter(
            SupplierOrderDraft.id == draft_id
        ).first()

        if not draft:
            raise ValueError(f"Draft {draft_id} not found")

        draft.status = OrderDraftStatus.SENT
        draft.email_sent_at = datetime.now()
        self.db.flush()

        return draft


def create_and_export_orders(
    db: Session,
    session_id: int,
    requested_delivery_date: Optional[datetime] = None,
    export_csv: bool = True,
    export_pdf: bool = True,
) -> Dict:
    """
    Convenience function to create drafts and export them.
    Returns summary with draft info and file paths.
    """
    service = ExportService(db)

    # Create drafts
    drafts = service.create_order_drafts(session_id, requested_delivery_date)

    result = {
        "session_id": session_id,
        "drafts_created": len(drafts),
        "orders": [],
    }

    for draft in drafts:
        order_info = {
            "draft_id": draft.id,
            "supplier_id": draft.supplier_id,
            "line_count": draft.line_count,
            "total_qty": float(draft.total_qty),
            "total_value": float(draft.total_value) if draft.total_value else None,
            "csv_path": None,
            "pdf_path": None,
        }

        if export_csv:
            order_info["csv_path"] = service.export_to_csv(draft.id)

        if export_pdf:
            order_info["pdf_path"] = service.export_to_pdf(draft.id)

        result["orders"].append(order_info)

    return result
