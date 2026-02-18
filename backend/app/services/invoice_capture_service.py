"""Automated Invoice Capture Service.

OCR-based invoice processing:
1. Upload photo/PDF of supplier invoice
2. Extract text via Tesseract OCR (configured in settings)
3. Parse supplier name, invoice number, date, line items, totals
4. Auto-match to existing suppliers and products
5. Create draft purchase order / goods received note
6. Flag discrepancies for review

Industry standard: MarketMan, BlueCart, xtraCHEF (Toast).
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin
from app.models.location import Location
from app.models.order import PurchaseOrder, PurchaseOrderLine, POStatus
from app.models.product import Product
from app.models.supplier import Supplier

logger = logging.getLogger(__name__)

# Directory where uploaded invoice images are stored
UPLOAD_DIR = Path("./data/invoice_uploads")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CapturedInvoice(Base, TimestampMixin):
    """An invoice captured via OCR."""

    __tablename__ = "captured_invoices"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"), index=True,
    )
    supplier_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True,
    )
    image_path: Mapped[str] = mapped_column(String(500))
    ocr_raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(
        String(20), default="pending",
    )  # pending, matched, approved, rejected
    matched_po_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Relationships
    location: Mapped["Location"] = relationship("Location", foreign_keys=[location_id])
    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier", foreign_keys=[supplier_id])
    lines: Mapped[List["CapturedInvoiceLine"]] = relationship(
        "CapturedInvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )


class CapturedInvoiceLine(Base):
    """A single line item parsed from a captured invoice."""

    __tablename__ = "captured_invoice_lines"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("captured_invoices.id", ondelete="CASCADE"), index=True,
    )
    description: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 3), nullable=True)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    total_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    matched_product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id"), nullable=True,
    )
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    # Relationships
    invoice: Mapped["CapturedInvoice"] = relationship(
        "CapturedInvoice", back_populates="lines",
    )
    matched_product: Mapped[Optional["Product"]] = relationship(
        "Product", foreign_keys=[matched_product_id],
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class InvoiceCaptureService:
    """Full pipeline: save -> OCR -> parse -> match -> store."""

    FUZZY_THRESHOLD = 0.6  # Minimum similarity for supplier/product matching

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def capture_invoice(
        self,
        image_data: bytes,
        filename: str,
        location_id: int,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run the full capture pipeline.

        1. Save the file to disk.
        2. Run Tesseract OCR.
        3. Parse structured data from raw text.
        4. Fuzzy-match supplier name to existing suppliers.
        5. Fuzzy-match line items to existing products.
        6. Persist CapturedInvoice + CapturedInvoiceLines.
        7. Return the resulting record.
        """
        # 1. Save
        image_path = self._save_file(image_data, filename)

        # 2. OCR
        raw_text = self.ocr_extract(str(image_path))

        # 3. Parse
        parsed = self.parse_invoice_text(raw_text)

        # 4. Match supplier
        supplier_match = self.match_supplier(parsed)
        supplier_id = supplier_match.get("supplier_id") if supplier_match else None

        # 5. Build invoice record
        invoice = CapturedInvoice(
            location_id=location_id,
            supplier_id=supplier_id,
            image_path=str(image_path),
            ocr_raw_text=raw_text,
            parsed_data=json.dumps(parsed, default=str),
            invoice_number=parsed.get("invoice_number"),
            invoice_date=parsed.get("invoice_date"),
            total_amount=parsed.get("total_amount"),
            currency=parsed.get("currency", "USD"),
            status="pending" if supplier_id is None else "matched",
            confidence_score=supplier_match.get("confidence", 0) if supplier_match else 0,
        )
        self.db.add(invoice)
        self.db.flush()  # Get ID for lines

        # 6. Match line items and persist
        line_items = parsed.get("line_items", [])
        matched_lines = self.match_line_items(line_items, supplier_id)
        for ml in matched_lines:
            line = CapturedInvoiceLine(
                invoice_id=invoice.id,
                description=ml["description"],
                quantity=ml.get("quantity"),
                unit_price=ml.get("unit_price"),
                total_price=ml.get("total_price"),
                matched_product_id=ml.get("matched_product_id"),
                confidence=ml.get("confidence", 0),
            )
            self.db.add(line)

        self.db.commit()
        self.db.refresh(invoice)

        logger.info(
            "Invoice captured: id=%s, supplier=%s, lines=%s, confidence=%.1f",
            invoice.id, supplier_id, len(matched_lines),
            invoice.confidence_score or 0,
        )

        return self._invoice_to_dict(invoice)

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------

    def ocr_extract(self, image_path: str) -> str:
        """Run Tesseract OCR on the given image file and return raw text."""
        tesseract_bin = settings.tesseract_path
        lang = settings.ocr_default_language
        dpi = settings.ocr_dpi

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        cmd = [
            tesseract_bin,
            image_path,
            "stdout",
            "-l", lang,
            "--dpi", str(dpi),
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.error("Tesseract failed: %s", result.stderr)
                return f"[OCR_ERROR] {result.stderr.strip()}"
            return result.stdout.strip()
        except FileNotFoundError:
            logger.error("Tesseract binary not found at %s", tesseract_bin)
            return "[OCR_ERROR] Tesseract not installed"
        except subprocess.TimeoutExpired:
            logger.error("Tesseract timed out for %s", image_path)
            return "[OCR_ERROR] OCR processing timed out"

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_invoice_text(self, raw_text: str) -> Dict[str, Any]:
        """Parse structured fields from OCR raw text.

        Returns dict with keys: supplier_name, invoice_number, invoice_date,
        total_amount, currency, line_items.
        """
        if not raw_text or raw_text.startswith("[OCR_ERROR]"):
            return {
                "supplier_name": None,
                "invoice_number": None,
                "invoice_date": None,
                "total_amount": None,
                "currency": "USD",
                "line_items": [],
                "raw_text_length": len(raw_text) if raw_text else 0,
            }

        lines = raw_text.split("\n")
        cleaned = [l.strip() for l in lines if l.strip()]

        result: Dict[str, Any] = {
            "supplier_name": self._extract_supplier_name(cleaned),
            "invoice_number": self._extract_invoice_number(raw_text),
            "invoice_date": self._extract_date(raw_text),
            "total_amount": self._extract_total(raw_text),
            "currency": self._extract_currency(raw_text),
            "line_items": self._extract_line_items(cleaned),
            "raw_text_length": len(raw_text),
        }

        return result

    # ------------------------------------------------------------------
    # Supplier matching
    # ------------------------------------------------------------------

    def match_supplier(
        self, parsed_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Fuzzy-match the supplier name from parsed data against existing
        suppliers.  Returns None if no match exceeds the threshold."""
        name = parsed_data.get("supplier_name")
        if not name:
            return None

        suppliers = self.db.query(Supplier).all()
        best_match: Optional[Supplier] = None
        best_score = 0.0

        name_lower = name.lower()
        for s in suppliers:
            score = SequenceMatcher(None, name_lower, s.name.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = s

        if best_match and best_score >= self.FUZZY_THRESHOLD:
            return {
                "supplier_id": best_match.id,
                "supplier_name": best_match.name,
                "confidence": round(best_score * 100, 1),
            }
        return None

    # ------------------------------------------------------------------
    # Line item matching
    # ------------------------------------------------------------------

    def match_line_items(
        self,
        line_items: List[Dict[str, Any]],
        supplier_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fuzzy-match each parsed line item description to existing products.

        If a supplier_id is provided, prefer products from that supplier.
        """
        if supplier_id:
            products = (
                self.db.query(Product)
                .filter(Product.supplier_id == supplier_id, Product.active == True)  # noqa: E712
                .all()
            )
        else:
            products = []

        # Fallback: all active products
        all_products = (
            self.db.query(Product)
            .filter(Product.active == True)  # noqa: E712
            .all()
        )

        matched: List[Dict[str, Any]] = []
        for item in line_items:
            desc = (item.get("description") or "").lower()
            if not desc:
                matched.append(item)
                continue

            # Search supplier products first, then all
            best_product: Optional[Product] = None
            best_score = 0.0

            for pool in [products, all_products]:
                for p in pool:
                    # Match against product name, barcode, SKU
                    name_score = SequenceMatcher(None, desc, p.name.lower()).ratio()
                    sku_score = 0.0
                    if p.sku:
                        sku_score = SequenceMatcher(None, desc, p.sku.lower()).ratio()
                    score = max(name_score, sku_score)
                    if score > best_score:
                        best_score = score
                        best_product = p
                if best_product and best_score >= self.FUZZY_THRESHOLD:
                    break  # Found a good match in the preferred pool

            result_item = dict(item)
            if best_product and best_score >= self.FUZZY_THRESHOLD:
                result_item["matched_product_id"] = best_product.id
                result_item["matched_product_name"] = best_product.name
                result_item["confidence"] = round(best_score * 100, 1)
            else:
                result_item["matched_product_id"] = None
                result_item["confidence"] = 0

            matched.append(result_item)

        return matched

    # ------------------------------------------------------------------
    # PO creation
    # ------------------------------------------------------------------

    def create_draft_po(
        self,
        invoice_id: int,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a draft PurchaseOrder from a captured invoice."""
        invoice = (
            self.db.query(CapturedInvoice)
            .filter(CapturedInvoice.id == invoice_id)
            .first()
        )
        if not invoice:
            raise ValueError(f"Captured invoice {invoice_id} not found")

        if invoice.matched_po_id:
            return {
                "status": "already_created",
                "po_id": invoice.matched_po_id,
            }

        if not invoice.supplier_id:
            raise ValueError("Cannot create PO: no supplier matched for this invoice")

        po = PurchaseOrder(
            supplier_id=invoice.supplier_id,
            location_id=invoice.location_id,
            status=POStatus.DRAFT,
            notes=f"Auto-generated from captured invoice #{invoice.id} ({invoice.invoice_number or 'no number'})",
        )
        self.db.add(po)
        self.db.flush()

        lines = (
            self.db.query(CapturedInvoiceLine)
            .filter(CapturedInvoiceLine.invoice_id == invoice_id)
            .all()
        )

        po_lines_created = 0
        for line in lines:
            if not line.matched_product_id:
                continue
            po_line = PurchaseOrderLine(
                po_id=po.id,
                product_id=line.matched_product_id,
                qty=line.quantity or Decimal("0"),
                unit_cost=line.unit_price or Decimal("0"),
            )
            self.db.add(po_line)
            po_lines_created += 1

        invoice.matched_po_id = po.id
        invoice.status = "matched"
        self.db.commit()

        logger.info(
            "Draft PO %s created from invoice %s with %s lines",
            po.id, invoice_id, po_lines_created,
        )

        return {
            "status": "created",
            "po_id": po.id,
            "lines_created": po_lines_created,
            "unmatched_lines": len(lines) - po_lines_created,
        }

    # ------------------------------------------------------------------
    # Approval / rejection
    # ------------------------------------------------------------------

    def approve_invoice(
        self,
        invoice_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """Approve a captured invoice and optionally process stock intake."""
        invoice = (
            self.db.query(CapturedInvoice)
            .filter(CapturedInvoice.id == invoice_id)
            .first()
        )
        if not invoice:
            raise ValueError(f"Captured invoice {invoice_id} not found")

        if invoice.status == "approved":
            return {"status": "already_approved", "invoice_id": invoice_id}

        invoice.status = "approved"
        invoice.reviewed_by = user_id
        self.db.commit()

        logger.info("Invoice %s approved by user %s", invoice_id, user_id)
        return {
            "status": "approved",
            "invoice_id": invoice_id,
            "reviewed_by": user_id,
        }

    def reject_invoice(
        self,
        invoice_id: int,
        user_id: int,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reject a captured invoice."""
        invoice = (
            self.db.query(CapturedInvoice)
            .filter(CapturedInvoice.id == invoice_id)
            .first()
        )
        if not invoice:
            raise ValueError(f"Captured invoice {invoice_id} not found")

        invoice.status = "rejected"
        invoice.reviewed_by = user_id
        if reason:
            invoice.notes = (invoice.notes or "") + f"\nRejected: {reason}"
        self.db.commit()

        logger.info("Invoice %s rejected by user %s: %s", invoice_id, user_id, reason)
        return {
            "status": "rejected",
            "invoice_id": invoice_id,
            "reason": reason,
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get a single captured invoice with lines."""
        invoice = (
            self.db.query(CapturedInvoice)
            .filter(CapturedInvoice.id == invoice_id)
            .first()
        )
        if not invoice:
            return None
        return self._invoice_to_dict(invoice)

    def list_invoices(
        self,
        location_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        supplier_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List captured invoices with optional filters."""
        query = self.db.query(CapturedInvoice)

        if location_id is not None:
            query = query.filter(CapturedInvoice.location_id == location_id)
        if status_filter:
            query = query.filter(CapturedInvoice.status == status_filter)
        if supplier_id is not None:
            query = query.filter(CapturedInvoice.supplier_id == supplier_id)

        total = query.count()
        invoices = (
            query.order_by(CapturedInvoice.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "invoices": [self._invoice_summary(inv) for inv in invoices],
        }

    def get_dashboard(self) -> Dict[str, Any]:
        """Stats dashboard for invoice capture."""
        total = self.db.query(CapturedInvoice).count()
        pending = (
            self.db.query(CapturedInvoice)
            .filter(CapturedInvoice.status == "pending")
            .count()
        )
        matched = (
            self.db.query(CapturedInvoice)
            .filter(CapturedInvoice.status == "matched")
            .count()
        )
        approved = (
            self.db.query(CapturedInvoice)
            .filter(CapturedInvoice.status == "approved")
            .count()
        )
        rejected = (
            self.db.query(CapturedInvoice)
            .filter(CapturedInvoice.status == "rejected")
            .count()
        )

        avg_confidence = (
            self.db.query(func.avg(CapturedInvoice.confidence_score))
            .filter(CapturedInvoice.confidence_score.isnot(None))
            .scalar()
        )

        total_lines = self.db.query(CapturedInvoiceLine).count()
        matched_lines = (
            self.db.query(CapturedInvoiceLine)
            .filter(CapturedInvoiceLine.matched_product_id.isnot(None))
            .count()
        )
        match_rate = (matched_lines / total_lines * 100) if total_lines > 0 else 0

        recent = (
            self.db.query(CapturedInvoice)
            .order_by(CapturedInvoice.created_at.desc())
            .limit(10)
            .all()
        )

        return {
            "totals": {
                "total": total,
                "pending": pending,
                "matched": matched,
                "approved": approved,
                "rejected": rejected,
            },
            "avg_confidence": round(float(avg_confidence), 1) if avg_confidence else 0,
            "line_match_rate": round(match_rate, 1),
            "total_lines": total_lines,
            "matched_lines": matched_lines,
            "recent_invoices": [self._invoice_summary(inv) for inv in recent],
        }

    # ------------------------------------------------------------------
    # Internal helpers: file saving
    # ------------------------------------------------------------------

    def _save_file(self, data: bytes, filename: str) -> Path:
        """Save uploaded image data to disk."""
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(filename).suffix or ".jpg"
        safe_name = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / safe_name
        file_path.write_bytes(data)
        return file_path

    # ------------------------------------------------------------------
    # Internal helpers: parsing
    # ------------------------------------------------------------------

    def _extract_supplier_name(self, lines: List[str]) -> Optional[str]:
        """Heuristic: the first non-empty line that isn't a date or number
        is likely the supplier/company name."""
        for line in lines[:5]:
            stripped = line.strip()
            if not stripped:
                continue
            # Skip lines that are mostly digits or dates
            if re.match(r"^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}$", stripped):
                continue
            if re.match(r"^[\d\s\.\,\-\+]+$", stripped):
                continue
            # Skip common header words
            lower = stripped.lower()
            if any(kw in lower for kw in ["invoice", "tax invoice", "bill", "receipt", "page"]):
                continue
            return stripped
        return None

    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number from common patterns."""
        patterns = [
            r"[Ii]nvoice\s*#?\s*:?\s*([A-Za-z0-9\-]+)",
            r"[Ii]nv\s*\.?\s*#?\s*:?\s*([A-Za-z0-9\-]+)",
            r"[Nn]o\s*\.?\s*:?\s*([A-Za-z0-9\-]+)",
            r"#\s*(\d{3,})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_date(self, text: str) -> Optional[date]:
        """Extract a date from common formats."""
        patterns = [
            (r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})", "%m/%d/%Y"),
            (r"(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})", "%Y/%m/%d"),
            (r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})", None),
        ]
        for pattern, fmt in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if fmt:
                        date_str = match.group(0).replace("-", "/").replace(".", "/")
                        return datetime.strptime(date_str, fmt).date()
                    else:
                        day = int(match.group(1))
                        month_str = match.group(2)[:3]
                        year = int(match.group(3))
                        months = {
                            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
                            "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
                            "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
                        }
                        month = months.get(month_str, 1)
                        return date(year, month, day)
                except (ValueError, KeyError):
                    continue
        return None

    def _extract_total(self, text: str) -> Optional[Decimal]:
        """Extract total amount from common patterns."""
        patterns = [
            r"[Tt]otal\s*:?\s*\$?\s*([\d,]+\.?\d*)",
            r"[Gg]rand\s+[Tt]otal\s*:?\s*\$?\s*([\d,]+\.?\d*)",
            r"[Aa]mount\s+[Dd]ue\s*:?\s*\$?\s*([\d,]+\.?\d*)",
            r"[Bb]alance\s+[Dd]ue\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    amount_str = match.group(1).replace(",", "")
                    return Decimal(amount_str)
                except InvalidOperation:
                    continue
        return None

    def _extract_currency(self, text: str) -> str:
        """Detect currency from text."""
        text_upper = text.upper()
        if "BGN" in text_upper or "lv" in text.lower():
            return "BGN"
        if "EUR" in text_upper:
            return "EUR"
        if "GBP" in text_upper:
            return "GBP"
        return "USD"

    def _extract_line_items(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Attempt to parse line items from OCR text lines.

        Looks for patterns like: description  qty  price  total
        """
        items: List[Dict[str, Any]] = []

        # Pattern: description followed by numbers (qty, unit_price, total)
        line_pattern = re.compile(
            r"^(.{3,}?)\s+"           # description (at least 3 chars)
            r"(\d+[\.,]?\d*)\s+"      # quantity
            r"[\$]?([\d,]+\.?\d*)\s*" # unit price
            r"[\$]?([\d,]+\.?\d*)$"   # total
        )

        # Simpler pattern: description and total only
        simple_pattern = re.compile(
            r"^(.{3,}?)\s+"
            r"[\$]?([\d,]+\.?\d*)$"
        )

        for line in lines:
            stripped = line.strip()
            if not stripped or len(stripped) < 5:
                continue

            # Skip header/footer lines
            lower = stripped.lower()
            if any(kw in lower for kw in [
                "subtotal", "total", "tax", "invoice", "date",
                "bill to", "ship to", "terms", "thank you", "page",
            ]):
                continue

            match = line_pattern.match(stripped)
            if match:
                try:
                    items.append({
                        "description": match.group(1).strip(),
                        "quantity": Decimal(match.group(2).replace(",", ".")),
                        "unit_price": Decimal(match.group(3).replace(",", "")),
                        "total_price": Decimal(match.group(4).replace(",", "")),
                    })
                    continue
                except InvalidOperation:
                    pass

            match = simple_pattern.match(stripped)
            if match:
                try:
                    total = Decimal(match.group(2).replace(",", ""))
                    if total > 0:
                        items.append({
                            "description": match.group(1).strip(),
                            "quantity": None,
                            "unit_price": None,
                            "total_price": total,
                        })
                except InvalidOperation:
                    pass

        return items

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def _invoice_to_dict(self, inv: CapturedInvoice) -> Dict[str, Any]:
        """Full invoice representation with lines."""
        lines = (
            self.db.query(CapturedInvoiceLine)
            .filter(CapturedInvoiceLine.invoice_id == inv.id)
            .all()
        )
        return {
            "id": inv.id,
            "location_id": inv.location_id,
            "supplier_id": inv.supplier_id,
            "supplier_name": inv.supplier.name if inv.supplier else None,
            "image_path": inv.image_path,
            "ocr_raw_text": inv.ocr_raw_text,
            "parsed_data": json.loads(inv.parsed_data) if inv.parsed_data else None,
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "total_amount": float(inv.total_amount) if inv.total_amount else None,
            "currency": inv.currency,
            "status": inv.status,
            "matched_po_id": inv.matched_po_id,
            "confidence_score": float(inv.confidence_score) if inv.confidence_score else None,
            "reviewed_by": inv.reviewed_by,
            "notes": inv.notes,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
            "lines": [
                {
                    "id": l.id,
                    "description": l.description,
                    "quantity": float(l.quantity) if l.quantity else None,
                    "unit_price": float(l.unit_price) if l.unit_price else None,
                    "total_price": float(l.total_price) if l.total_price else None,
                    "matched_product_id": l.matched_product_id,
                    "matched_product_name": l.matched_product.name if l.matched_product else None,
                    "confidence": float(l.confidence) if l.confidence else None,
                }
                for l in lines
            ],
        }

    def _invoice_summary(self, inv: CapturedInvoice) -> Dict[str, Any]:
        """Compact invoice representation for list views."""
        return {
            "id": inv.id,
            "location_id": inv.location_id,
            "supplier_id": inv.supplier_id,
            "supplier_name": inv.supplier.name if inv.supplier else None,
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "total_amount": float(inv.total_amount) if inv.total_amount else None,
            "currency": inv.currency,
            "status": inv.status,
            "confidence_score": float(inv.confidence_score) if inv.confidence_score else None,
            "line_count": len(inv.lines) if inv.lines else 0,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
