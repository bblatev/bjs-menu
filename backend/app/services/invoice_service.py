"""Invoice OCR & AP Automation Service - Toast xtraCHEF style."""

import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.invoice import (
    Invoice, InvoiceLine, PriceHistory, PriceAlert, GLCode,
    InvoiceStatus, InvoiceCaptureMethod
)
from app.models.product import Product
from app.models.supplier import Supplier
from app.services.ai.ocr_service import extract_text_from_image


class InvoiceOCRService:
    """Process invoices using OCR and extract structured data."""

    # Common invoice patterns
    INVOICE_NUMBER_PATTERNS = [
        r'invoice\s*#?\s*:?\s*(\w+[\w\-]+)',
        r'inv\s*#?\s*:?\s*(\w+[\w\-]+)',
        r'bill\s*#?\s*:?\s*(\w+[\w\-]+)',
        r'reference\s*#?\s*:?\s*(\w+[\w\-]+)',
    ]

    DATE_PATTERNS = [
        r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})',
        r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s+\d{4})',
    ]

    AMOUNT_PATTERNS = [
        r'total\s*:?\s*\$?\s*([\d,]+\.?\d*)',
        r'amount\s+due\s*:?\s*\$?\s*([\d,]+\.?\d*)',
        r'balance\s+due\s*:?\s*\$?\s*([\d,]+\.?\d*)',
        r'grand\s+total\s*:?\s*\$?\s*([\d,]+\.?\d*)',
    ]

    def __init__(self, db: Session):
        self.db = db

    async def process_invoice_image(
        self,
        image_path: str,
        location_id: Optional[int] = None,
        capture_method: InvoiceCaptureMethod = InvoiceCaptureMethod.UPLOAD
    ) -> Invoice:
        """Process an invoice image and create invoice record."""

        # Extract text using OCR
        ocr_result = await extract_text_from_image(image_path)
        raw_text = ocr_result.get("text", "") if isinstance(ocr_result, dict) else str(ocr_result)

        # Parse extracted text
        parsed_data = self._parse_invoice_text(raw_text)

        # Try to match supplier
        supplier_id = self._match_supplier(parsed_data.get("vendor_name"), raw_text)

        # Create invoice record
        invoice = Invoice(
            supplier_id=supplier_id,
            location_id=location_id,
            invoice_number=parsed_data.get("invoice_number"),
            invoice_date=parsed_data.get("invoice_date"),
            due_date=parsed_data.get("due_date"),
            subtotal=parsed_data.get("subtotal", 0.0),
            tax_amount=parsed_data.get("tax", 0.0),
            total_amount=parsed_data.get("total", 0.0),
            capture_method=capture_method,
            original_image_path=image_path,
            ocr_raw_text=raw_text,
            ocr_confidence=parsed_data.get("confidence", 0.0),
            ocr_processed_at=datetime.utcnow(),
            status=InvoiceStatus.NEEDS_REVIEW if not parsed_data.get("invoice_number") else InvoiceStatus.PENDING
        )

        self.db.add(invoice)
        self.db.flush()

        # Parse line items
        line_items = self._parse_line_items(raw_text)
        for item in line_items:
            product_id = self._match_product(item.get("description"), item.get("code"))

            line = InvoiceLine(
                invoice_id=invoice.id,
                product_id=product_id,
                item_description=item.get("description"),
                item_code=item.get("code"),
                quantity=item.get("quantity", 1),
                unit_of_measure=item.get("uom"),
                unit_price=item.get("unit_price", 0),
                line_total=item.get("total", 0),
                gl_code=self._auto_assign_gl_code(item.get("description"))
            )

            # Check for price changes
            if product_id and supplier_id:
                line.previous_price, line.price_change_percent = self._check_price_change(
                    product_id, supplier_id, item.get("unit_price", 0)
                )
                if line.price_change_percent and abs(line.price_change_percent) > 10:
                    line.price_alert_triggered = True

            self.db.add(line)

        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def _parse_invoice_text(self, text: str) -> Dict[str, Any]:
        """Parse invoice text to extract structured data."""
        text_lower = text.lower()
        result = {"confidence": 0.0}
        matches = 0

        # Extract invoice number
        for pattern in self.INVOICE_NUMBER_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                result["invoice_number"] = match.group(1).upper()
                matches += 1
                break

        # Extract dates
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Try multiple date formats
                    for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%m-%d-%Y"]:
                        try:
                            result["invoice_date"] = datetime.strptime(date_str, fmt)
                            matches += 1
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
                break

        # Extract total amount
        for pattern in self.AMOUNT_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(",", "")
                    result["total"] = float(amount_str)
                    matches += 1
                except ValueError:
                    pass
                break

        # Extract tax if present
        tax_match = re.search(r'tax\s*:?\s*\$?\s*([\d,]+\.?\d*)', text_lower)
        if tax_match:
            try:
                result["tax"] = float(tax_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # Calculate subtotal
        if result.get("total") and result.get("tax"):
            result["subtotal"] = result["total"] - result["tax"]

        # Confidence based on matches
        result["confidence"] = min(matches / 3, 1.0)

        return result

    def _parse_line_items(self, text: str) -> List[Dict[str, Any]]:
        """Parse line items from invoice text."""
        items = []

        # Pattern for line items: code/qty/description/price
        line_pattern = r'(\d+)\s+([A-Z0-9\-]+)?\s*(.+?)\s+\$?([\d,]+\.?\d*)\s*$'

        lines = text.split('\n')
        for line in lines:
            match = re.search(line_pattern, line, re.IGNORECASE)
            if match:
                items.append({
                    "quantity": int(match.group(1)),
                    "code": match.group(2),
                    "description": match.group(3).strip(),
                    "total": float(match.group(4).replace(",", ""))
                })

        return items

    def _match_supplier(self, vendor_name: Optional[str], full_text: str) -> Optional[int]:
        """Try to match invoice to existing supplier."""
        if not vendor_name and not full_text:
            return None

        # Get all suppliers
        suppliers = self.db.query(Supplier).filter(Supplier.is_active == True).all()

        for supplier in suppliers:
            # Check if supplier name appears in text
            if supplier.name and supplier.name.lower() in full_text.lower():
                return supplier.id
            # Check for partial matches
            if vendor_name and supplier.name:
                if vendor_name.lower() in supplier.name.lower() or supplier.name.lower() in vendor_name.lower():
                    return supplier.id

        return None

    def _match_product(self, description: Optional[str], code: Optional[str]) -> Optional[int]:
        """Try to match line item to existing product."""
        if code:
            product = self.db.query(Product).filter(
                Product.sku == code
            ).first()
            if product:
                return product.id

        if description:
            # Fuzzy match by name
            product = self.db.query(Product).filter(
                func.lower(Product.name).contains(description.lower()[:20])
            ).first()
            if product:
                return product.id

        return None

    def _auto_assign_gl_code(self, description: Optional[str]) -> Optional[str]:
        """Auto-assign GL code based on keywords."""
        if not description:
            return None

        description_lower = description.lower()

        # Get GL codes with auto-assign keywords
        gl_codes = self.db.query(GLCode).filter(
            GLCode.is_active == True,
            GLCode.auto_assign_keywords.isnot(None)
        ).all()

        for gl in gl_codes:
            if gl.auto_assign_keywords:
                for keyword in gl.auto_assign_keywords:
                    if keyword.lower() in description_lower:
                        return gl.code

        return None

    def _check_price_change(
        self,
        product_id: int,
        supplier_id: int,
        new_price: float
    ) -> Tuple[Optional[float], Optional[float]]:
        """Check if price has changed from last purchase."""
        last_price = self.db.query(PriceHistory).filter(
            PriceHistory.product_id == product_id,
            PriceHistory.supplier_id == supplier_id
        ).order_by(PriceHistory.recorded_at.desc()).first()

        if last_price and last_price.price > 0:
            change_percent = ((new_price - last_price.price) / last_price.price) * 100
            return last_price.price, change_percent

        return None, None


class APAutomationService:
    """Accounts Payable automation and approval workflows."""

    def __init__(self, db: Session):
        self.db = db

    def get_pending_invoices(
        self,
        location_id: Optional[int] = None,
        status: Optional[InvoiceStatus] = None
    ) -> List[Invoice]:
        """Get invoices pending approval."""
        query = self.db.query(Invoice)

        if location_id:
            query = query.filter(Invoice.location_id == location_id)

        if status:
            query = query.filter(Invoice.status == status)
        else:
            query = query.filter(Invoice.status.in_([
                InvoiceStatus.PENDING,
                InvoiceStatus.NEEDS_REVIEW
            ]))

        return query.order_by(Invoice.created_at.desc()).all()

    def process_approval(
        self,
        invoice_id: int,
        approver_id: int,
        action: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an approval action (approve/reject)."""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return {"error": "Invoice not found"}

        if action == "approve":
            invoice.status = InvoiceStatus.APPROVED
            invoice.approved_by = approver_id
            invoice.approved_at = datetime.utcnow()
            if notes:
                invoice.notes = notes

            # Record price history for all line items
            for line in invoice.lines:
                if line.product_id and invoice.supplier_id:
                    price_history = PriceHistory(
                        product_id=line.product_id,
                        supplier_id=invoice.supplier_id,
                        price=line.unit_price,
                        unit_of_measure=line.unit_of_measure,
                        source_invoice_id=invoice.id
                    )
                    self.db.add(price_history)
        elif action == "reject":
            invoice.status = InvoiceStatus.REJECTED
            invoice.approved_by = approver_id
            invoice.approved_at = datetime.utcnow()
            invoice.rejection_reason = notes
        else:
            return {"error": f"Invalid action: {action}"}

        self.db.commit()
        self.db.refresh(invoice)
        return {"invoice": invoice}

    def approve_invoice(
        self,
        invoice_id: int,
        user_id: int,
        gl_code: Optional[str] = None
    ) -> Invoice:
        """Approve an invoice."""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")

        invoice.status = InvoiceStatus.APPROVED
        invoice.approved_by = user_id
        invoice.approved_at = datetime.utcnow()

        if gl_code:
            invoice.gl_code = gl_code

        # Record price history for all line items
        for line in invoice.lines:
            if line.product_id and invoice.supplier_id:
                price_history = PriceHistory(
                    product_id=line.product_id,
                    supplier_id=invoice.supplier_id,
                    price=line.unit_price,
                    unit_of_measure=line.unit_of_measure,
                    source_invoice_id=invoice.id
                )
                self.db.add(price_history)

        self.db.commit()
        return invoice

    def reject_invoice(
        self,
        invoice_id: int,
        user_id: int,
        reason: str
    ) -> Invoice:
        """Reject an invoice."""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")

        invoice.status = InvoiceStatus.REJECTED
        invoice.approved_by = user_id
        invoice.approved_at = datetime.utcnow()
        invoice.rejection_reason = reason

        self.db.commit()
        return invoice

    def mark_paid(
        self,
        invoice_id: int,
        payment_reference: Optional[str] = None
    ) -> Invoice:
        """Mark invoice as paid."""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")

        invoice.status = InvoiceStatus.PAID
        invoice.payment_date = datetime.utcnow()
        invoice.payment_reference = payment_reference

        self.db.commit()
        return invoice


class PriceTrackingService:
    """Track and alert on price changes."""

    def __init__(self, db: Session):
        self.db = db

    def get_price_history(
        self,
        product_id: int,
        supplier_id: Optional[int] = None,
        days: int = 365
    ) -> List[PriceHistory]:
        """Get price history for a product."""
        query = self.db.query(PriceHistory).filter(
            PriceHistory.product_id == product_id,
            PriceHistory.recorded_at >= datetime.utcnow() - timedelta(days=days)
        )

        if supplier_id:
            query = query.filter(PriceHistory.supplier_id == supplier_id)

        return query.order_by(PriceHistory.recorded_at.desc()).all()

    def get_price_trends(
        self,
        product_ids: Optional[List[int]] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get price trends for products."""
        query = self.db.query(
            PriceHistory.product_id,
            func.min(PriceHistory.price).label("min_price"),
            func.max(PriceHistory.price).label("max_price"),
            func.avg(PriceHistory.price).label("avg_price"),
        ).filter(
            PriceHistory.recorded_at >= datetime.utcnow() - timedelta(days=days)
        )

        if product_ids:
            query = query.filter(PriceHistory.product_id.in_(product_ids))

        query = query.group_by(PriceHistory.product_id)

        results = []
        for row in query.all():
            # Get current price
            current = self.db.query(PriceHistory).filter(
                PriceHistory.product_id == row.product_id
            ).order_by(PriceHistory.recorded_at.desc()).first()

            # Get price from start of period
            start_price = self.db.query(PriceHistory).filter(
                PriceHistory.product_id == row.product_id,
                PriceHistory.recorded_at >= datetime.utcnow() - timedelta(days=days)
            ).order_by(PriceHistory.recorded_at.asc()).first()

            change_percent = 0
            if start_price and start_price.price > 0 and current:
                change_percent = ((current.price - start_price.price) / start_price.price) * 100

            results.append({
                "product_id": row.product_id,
                "min_price": row.min_price,
                "max_price": row.max_price,
                "avg_price": row.avg_price,
                "current_price": current.price if current else None,
                "change_percent": change_percent,
                "trend": "up" if change_percent > 5 else "down" if change_percent < -5 else "stable"
            })

        return results

    def check_price_alerts(self) -> List[Dict[str, Any]]:
        """Check all active price alerts and return triggered ones."""
        alerts = self.db.query(PriceAlert).filter(PriceAlert.is_active == True).all()
        triggered = []

        for alert in alerts:
            # Get latest price
            latest = self.db.query(PriceHistory).filter(
                PriceHistory.product_id == alert.product_id
            )
            if alert.supplier_id:
                latest = latest.filter(PriceHistory.supplier_id == alert.supplier_id)

            latest = latest.order_by(PriceHistory.recorded_at.desc()).first()

            if not latest:
                continue

            # Get previous price for comparison
            previous = self.db.query(PriceHistory).filter(
                PriceHistory.product_id == alert.product_id,
                PriceHistory.recorded_at < latest.recorded_at
            )
            if alert.supplier_id:
                previous = previous.filter(PriceHistory.supplier_id == alert.supplier_id)

            previous = previous.order_by(PriceHistory.recorded_at.desc()).first()

            trigger_reason = None

            # Check threshold percent
            if previous and alert.threshold_percent:
                change = ((latest.price - previous.price) / previous.price) * 100
                if abs(change) >= alert.threshold_percent:
                    trigger_reason = f"Price changed by {change:.1f}%"

            # Check max price
            if alert.max_price and latest.price > alert.max_price:
                trigger_reason = f"Price ${latest.price:.2f} exceeds max ${alert.max_price:.2f}"

            if trigger_reason:
                # Update alert
                alert.last_triggered_at = datetime.utcnow()
                alert.trigger_count += 1

                triggered.append({
                    "alert_id": alert.id,
                    "product_id": alert.product_id,
                    "supplier_id": alert.supplier_id,
                    "current_price": latest.price,
                    "previous_price": previous.price if previous else None,
                    "reason": trigger_reason
                })

        self.db.commit()
        return triggered

    def create_price_alert(
        self,
        product_id: int,
        alert_type: str,
        threshold_percent: Optional[float] = None,
        max_price: Optional[float] = None,
        supplier_id: Optional[int] = None
    ) -> PriceAlert:
        """Create a new price alert."""
        alert = PriceAlert(
            product_id=product_id,
            supplier_id=supplier_id,
            alert_type=alert_type,
            threshold_percent=threshold_percent,
            max_price=max_price
        )

        self.db.add(alert)
        self.db.commit()
        return alert
