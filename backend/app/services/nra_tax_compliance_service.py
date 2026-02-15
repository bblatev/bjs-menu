"""
NRA Tax Compliance Service - BJS V6
====================================
Bulgarian NRA real-time reporting, SAF-T export, GDPR, e-invoice
with full database integration.
"""

from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class TaxDocumentType(str, Enum):
    FISCAL_RECEIPT = "fiscal_receipt"
    INVOICE = "invoice"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    STORNO = "storno"


class VATRate(str, Enum):
    STANDARD = "20"  # 20% standard
    REDUCED = "9"    # 9% reduced (hotels, restaurants)
    ZERO = "0"       # 0% exempt


class NRAReportStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ERROR = "error"


# Pydantic models for API responses
class FiscalDocumentResponse(BaseModel):
    id: int
    document_type: str
    document_number: str
    total_with_vat: float
    unique_sale_number: str

    model_config = ConfigDict(from_attributes=True)


class NRAReportResponse(BaseModel):
    id: int
    report_type: str
    period_start: date
    period_end: date
    total_sales: float
    status: str

    model_config = ConfigDict(from_attributes=True)


class NRATaxComplianceService:
    """Bulgarian NRA tax compliance and reporting with database persistence."""

    # NRA API endpoints (production)
    NRA_ENDPOINTS = {
        "test": "https://demo.taxadmin.minfin.bg/api/v1",
        "production": "https://portal.nra.bg/api/v1"
    }

    VAT_RATES = {
        VATRate.STANDARD: 0.20,
        VATRate.REDUCED: 0.09,
        VATRate.ZERO: 0.00
    }

    def __init__(self, db_session: Session = None, environment: str = "test"):
        self.db = db_session
        self.environment = environment
        self._fiscal_memory_counter: int = 0

    # ==================== FISCAL DOCUMENTS ====================

    def create_fiscal_receipt(self, venue_id: int, order_id: int,
                               items: List[Dict], payment_method: str,
                               fiscal_printer_id: str = "BC50MX") -> Dict[str, Any]:
        """Create fiscal receipt for NRA compliance."""
        from app.models.v6_features_models import FiscalDocument

        if not self.db:
            logger.warning("No database session - returning mock response")
            return {"id": 1, "venue_id": venue_id}

        # Calculate VAT breakdown
        subtotal_by_vat = {r.value: 0.0 for r in VATRate}
        vat_by_rate = {r.value: 0.0 for r in VATRate}

        for item in items:
            vat_rate = item.get("vat_rate", VATRate.STANDARD.value)
            amount = item.get("price", 0) * item.get("quantity", 1)
            vat_amount = amount * self.VAT_RATES.get(VATRate(vat_rate), 0.20)

            subtotal_by_vat[vat_rate] = subtotal_by_vat.get(vat_rate, 0) + amount
            vat_by_rate[vat_rate] = vat_by_rate.get(vat_rate, 0) + vat_amount

        total_without_vat = sum(subtotal_by_vat.values())
        total_vat = sum(vat_by_rate.values())

        # Get next document number from database
        last_doc = self.db.query(FiscalDocument).filter(
            FiscalDocument.venue_id == venue_id,
            FiscalDocument.fiscal_memory_number == fiscal_printer_id
        ).order_by(FiscalDocument.id.desc()).first()

        doc_counter = 1
        if last_doc and last_doc.document_number:
            try:
                doc_counter = int(last_doc.document_number) + 1
            except ValueError:
                doc_counter = 1

        # Generate unique sale number (УНП)
        unique_sale_number = f"{fiscal_printer_id}-{venue_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{doc_counter:06d}"

        # Generate fiscal sign (would be from fiscal device in production)
        fiscal_sign = self._generate_fiscal_sign(unique_sale_number, total_without_vat + total_vat)

        # Generate QR code data
        qr_data = self._generate_qr_code(unique_sale_number, total_without_vat + total_vat, fiscal_sign)

        document = FiscalDocument(
            venue_id=venue_id,
            order_id=order_id,
            document_type=TaxDocumentType.FISCAL_RECEIPT.value,
            document_number=f"{doc_counter:08d}",
            fiscal_memory_number=fiscal_printer_id,
            items=items,
            subtotal_by_vat=subtotal_by_vat,
            vat_by_rate=vat_by_rate,
            total_without_vat=total_without_vat,
            total_vat=total_vat,
            total_with_vat=total_without_vat + total_vat,
            payment_method=payment_method,
            unique_sale_number=unique_sale_number,
            fiscal_sign=fiscal_sign,
            qr_code=qr_data,
            issued_at=datetime.now(timezone.utc)
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        logger.info(f"Created fiscal receipt {document.id} for order {order_id}")

        return {
            "success": True,
            "id": document.id,
            "document_number": document.document_number,
            "unique_sale_number": document.unique_sale_number,
            "total_with_vat": float(document.total_with_vat),
            "fiscal_sign": document.fiscal_sign,
            "qr_code": document.qr_code
        }

    def create_invoice(self, venue_id: int, order_id: int, items: List[Dict],
                       payment_method: str, customer_vat_number: str,
                       customer_name: str, customer_address: str,
                       fiscal_printer_id: str = "BC50MX") -> Dict[str, Any]:
        """Create invoice with customer details."""
        from app.models.v6_features_models import FiscalDocument

        if not self.db:
            return {"success": False, "error": "No database session"}

        # Calculate VAT breakdown
        subtotal_by_vat = {r.value: 0.0 for r in VATRate}
        vat_by_rate = {r.value: 0.0 for r in VATRate}

        for item in items:
            vat_rate = item.get("vat_rate", VATRate.STANDARD.value)
            amount = item.get("price", 0) * item.get("quantity", 1)
            vat_amount = amount * self.VAT_RATES.get(VATRate(vat_rate), 0.20)

            subtotal_by_vat[vat_rate] = subtotal_by_vat.get(vat_rate, 0) + amount
            vat_by_rate[vat_rate] = vat_by_rate.get(vat_rate, 0) + vat_amount

        total_without_vat = sum(subtotal_by_vat.values())
        total_vat = sum(vat_by_rate.values())

        # Get next invoice number
        last_doc = self.db.query(FiscalDocument).filter(
            FiscalDocument.venue_id == venue_id,
            FiscalDocument.document_type == TaxDocumentType.INVOICE.value
        ).order_by(FiscalDocument.id.desc()).first()

        doc_counter = 1
        if last_doc and last_doc.document_number:
            try:
                doc_counter = int(last_doc.document_number.replace('INV-', '')) + 1
            except ValueError:
                doc_counter = 1

        unique_sale_number = f"INV-{venue_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{doc_counter:06d}"
        fiscal_sign = self._generate_fiscal_sign(unique_sale_number, total_without_vat + total_vat)
        qr_data = self._generate_qr_code(unique_sale_number, total_without_vat + total_vat, fiscal_sign)

        document = FiscalDocument(
            venue_id=venue_id,
            order_id=order_id,
            document_type=TaxDocumentType.INVOICE.value,
            document_number=f"INV-{doc_counter:06d}",
            fiscal_memory_number=fiscal_printer_id,
            customer_vat_number=customer_vat_number,
            customer_name=customer_name,
            customer_address=customer_address,
            items=items,
            subtotal_by_vat=subtotal_by_vat,
            vat_by_rate=vat_by_rate,
            total_without_vat=total_without_vat,
            total_vat=total_vat,
            total_with_vat=total_without_vat + total_vat,
            payment_method=payment_method,
            unique_sale_number=unique_sale_number,
            fiscal_sign=fiscal_sign,
            qr_code=qr_data,
            issued_at=datetime.now(timezone.utc)
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        logger.info(f"Created invoice {document.id} for customer {customer_vat_number}")

        return {
            "success": True,
            "id": document.id,
            "document_number": document.document_number,
            "unique_sale_number": document.unique_sale_number,
            "total_with_vat": float(document.total_with_vat),
            "customer_vat_number": customer_vat_number
        }

    def create_storno(self, original_document_id: int, reason: str) -> Dict[str, Any]:
        """Create storno/reversal document."""
        from app.models.v6_features_models import FiscalDocument

        if not self.db:
            return {"success": False, "error": "No database session"}

        original = self.db.query(FiscalDocument).filter(
            FiscalDocument.id == original_document_id
        ).first()

        if not original:
            return {"success": False, "error": "Original document not found"}

        # Get next storno number
        last_storno = self.db.query(FiscalDocument).filter(
            FiscalDocument.venue_id == original.venue_id,
            FiscalDocument.document_type == TaxDocumentType.STORNO.value
        ).order_by(FiscalDocument.id.desc()).first()

        storno_counter = 1
        if last_storno and last_storno.document_number:
            try:
                storno_counter = int(last_storno.document_number.replace('S', '')) + 1
            except ValueError:
                storno_counter = 1

        unique_sale_number = f"{original.fiscal_memory_number}-{original.venue_id}-STORNO-{storno_counter:06d}"
        fiscal_sign = self._generate_fiscal_sign(unique_sale_number, -float(original.total_with_vat))

        storno = FiscalDocument(
            venue_id=original.venue_id,
            order_id=original.order_id,
            document_type=TaxDocumentType.STORNO.value,
            document_number=f"S{storno_counter:07d}",
            fiscal_memory_number=original.fiscal_memory_number,
            items=original.items,
            subtotal_by_vat={k: -v for k, v in (original.subtotal_by_vat or {}).items()},
            vat_by_rate={k: -v for k, v in (original.vat_by_rate or {}).items()},
            total_without_vat=-float(original.total_without_vat),
            total_vat=-float(original.total_vat),
            total_with_vat=-float(original.total_with_vat),
            payment_method=original.payment_method,
            unique_sale_number=unique_sale_number,
            fiscal_sign=fiscal_sign,
            qr_code=self._generate_qr_code(unique_sale_number, -float(original.total_with_vat), fiscal_sign),
            issued_at=datetime.now(timezone.utc)
        )

        self.db.add(storno)
        self.db.commit()
        self.db.refresh(storno)

        logger.info(f"Created storno {storno.id} for document {original_document_id}: {reason}")

        return {
            "success": True,
            "id": storno.id,
            "document_number": storno.document_number,
            "original_document_id": original_document_id,
            "total_with_vat": float(storno.total_with_vat)
        }

    def get_documents(self, venue_id: int, start: date = None,
                      end: date = None, doc_type: str = None) -> List[Dict[str, Any]]:
        """Get fiscal documents."""
        from app.models.v6_features_models import FiscalDocument

        if not self.db:
            return []

        query = self.db.query(FiscalDocument).filter(
            FiscalDocument.venue_id == venue_id
        )

        if start:
            query = query.filter(func.date(FiscalDocument.issued_at) >= start)
        if end:
            query = query.filter(func.date(FiscalDocument.issued_at) <= end)
        if doc_type:
            if isinstance(doc_type, TaxDocumentType):
                doc_type = doc_type.value
            query = query.filter(FiscalDocument.document_type == doc_type)

        documents = query.order_by(FiscalDocument.issued_at.desc()).all()

        return [
            {
                "id": d.id,
                "document_type": d.document_type,
                "document_number": d.document_number,
                "unique_sale_number": d.unique_sale_number,
                "total_without_vat": float(d.total_without_vat),
                "total_vat": float(d.total_vat),
                "total_with_vat": float(d.total_with_vat),
                "payment_method": d.payment_method,
                "issued_at": d.issued_at.isoformat(),
                "sent_to_nra": d.sent_to_nra,
                "nra_status": d.nra_status
            }
            for d in documents
        ]

    def _generate_fiscal_sign(self, usn: str, amount: float) -> str:
        """Generate fiscal signature (simplified - real implementation uses fiscal device)."""
        data = f"{usn}:{amount:.2f}:{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16].upper()

    def _generate_qr_code(self, usn: str, amount: float, sign: str) -> str:
        """Generate QR code data for fiscal receipt."""
        return f"https://check.nra.bg/{usn}*{amount:.2f}*{sign}"

    # ==================== NRA REPORTING ====================

    def generate_daily_report(self, venue_id: int, report_date: date) -> Dict[str, Any]:
        """Generate daily Z-report for NRA."""
        from app.models.v6_features_models import FiscalDocument, NRAReport

        if not self.db:
            return {"success": False, "error": "No database session"}

        # Check if report already exists
        existing = self.db.query(NRAReport).filter(
            NRAReport.venue_id == venue_id,
            NRAReport.report_type == "daily",
            NRAReport.period_start == report_date
        ).first()

        if existing:
            return {
                "success": True,
                "id": existing.id,
                "message": "Report already exists",
                "status": existing.status
            }

        documents = self.db.query(FiscalDocument).filter(
            FiscalDocument.venue_id == venue_id,
            func.date(FiscalDocument.issued_at) == report_date
        ).all()

        receipts = [d for d in documents if d.document_type == TaxDocumentType.FISCAL_RECEIPT.value]
        stornos = [d for d in documents if d.document_type == TaxDocumentType.STORNO.value]

        sales_by_vat = {r.value: 0.0 for r in VATRate}
        vat_by_rate = {r.value: 0.0 for r in VATRate}
        sales_by_payment = {}

        for doc in receipts:
            for rate, amount in (doc.subtotal_by_vat or {}).items():
                sales_by_vat[rate] = sales_by_vat.get(rate, 0) + float(amount)
            for rate, amount in (doc.vat_by_rate or {}).items():
                vat_by_rate[rate] = vat_by_rate.get(rate, 0) + float(amount)
            pm = doc.payment_method
            sales_by_payment[pm] = sales_by_payment.get(pm, 0) + float(doc.total_with_vat)

        report = NRAReport(
            venue_id=venue_id,
            report_type="daily",
            period_start=report_date,
            period_end=report_date,
            total_sales=sum(float(d.total_with_vat) for d in receipts),
            total_vat=sum(float(d.total_vat) for d in receipts),
            total_receipts=len(receipts),
            total_stornos=len(stornos),
            sales_by_vat_rate=sales_by_vat,
            vat_by_rate=vat_by_rate,
            sales_by_payment_method=sales_by_payment,
            generated_at=datetime.now(timezone.utc)
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        logger.info(f"Generated daily report {report.id} for venue {venue_id}")

        return {
            "success": True,
            "id": report.id,
            "report_type": "daily",
            "period": report_date.isoformat(),
            "total_sales": float(report.total_sales),
            "total_vat": float(report.total_vat),
            "total_receipts": report.total_receipts
        }

    def generate_monthly_report(self, venue_id: int, year: int, month: int) -> Dict[str, Any]:
        """Generate monthly report for NRA."""
        from app.models.v6_features_models import FiscalDocument, NRAReport

        if not self.db:
            return {"success": False, "error": "No database session"}

        period_start = date(year, month, 1)
        if month == 12:
            period_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(year, month + 1, 1) - timedelta(days=1)

        documents = self.db.query(FiscalDocument).filter(
            FiscalDocument.venue_id == venue_id,
            func.date(FiscalDocument.issued_at) >= period_start,
            func.date(FiscalDocument.issued_at) <= period_end
        ).all()

        receipts = [d for d in documents if d.document_type in
                    [TaxDocumentType.FISCAL_RECEIPT.value, TaxDocumentType.INVOICE.value]]
        stornos = [d for d in documents if d.document_type == TaxDocumentType.STORNO.value]

        sales_by_vat = {r.value: 0.0 for r in VATRate}
        vat_by_rate = {r.value: 0.0 for r in VATRate}
        sales_by_payment = {}

        for doc in receipts:
            for rate, amount in (doc.subtotal_by_vat or {}).items():
                sales_by_vat[rate] = sales_by_vat.get(rate, 0) + float(amount)
            for rate, amount in (doc.vat_by_rate or {}).items():
                vat_by_rate[rate] = vat_by_rate.get(rate, 0) + float(amount)
            pm = doc.payment_method
            sales_by_payment[pm] = sales_by_payment.get(pm, 0) + float(doc.total_with_vat)

        report = NRAReport(
            venue_id=venue_id,
            report_type="monthly",
            period_start=period_start,
            period_end=period_end,
            total_sales=sum(float(d.total_with_vat) for d in receipts),
            total_vat=sum(float(d.total_vat) for d in receipts),
            total_receipts=len(receipts),
            total_stornos=len(stornos),
            sales_by_vat_rate=sales_by_vat,
            vat_by_rate=vat_by_rate,
            sales_by_payment_method=sales_by_payment,
            generated_at=datetime.now(timezone.utc)
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        logger.info(f"Generated monthly report {report.id} for {year}-{month:02d}")

        return {
            "success": True,
            "id": report.id,
            "report_type": "monthly",
            "period": f"{year}-{month:02d}",
            "total_sales": float(report.total_sales),
            "total_vat": float(report.total_vat),
            "total_receipts": report.total_receipts
        }

    def send_report_to_nra(self, report_id: int) -> Dict[str, Any]:
        """Send report to NRA (simulated)."""
        from app.models.v6_features_models import NRAReport

        if not self.db:
            return {"success": False, "error": "No database session"}

        report = self.db.query(NRAReport).filter(
            NRAReport.id == report_id
        ).first()

        if not report:
            return {"success": False, "error": "Report not found"}

        # In production, would call NRA API
        report.status = NRAReportStatus.SENT.value
        report.sent_at = datetime.now(timezone.utc)
        report.nra_reference = f"NRA-REF-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Simulate acceptance
        report.status = NRAReportStatus.ACCEPTED.value

        self.db.commit()

        logger.info(f"Sent report {report_id} to NRA: {report.nra_reference}")

        return {
            "success": True,
            "report_id": report_id,
            "nra_reference": report.nra_reference,
            "status": report.status
        }

    def get_reports(self, venue_id: int, report_type: str = None,
                    start: date = None, end: date = None) -> List[Dict[str, Any]]:
        """Get NRA reports."""
        from app.models.v6_features_models import NRAReport

        if not self.db:
            return []

        query = self.db.query(NRAReport).filter(
            NRAReport.venue_id == venue_id
        )

        if report_type:
            query = query.filter(NRAReport.report_type == report_type)
        if start:
            query = query.filter(NRAReport.period_start >= start)
        if end:
            query = query.filter(NRAReport.period_end <= end)

        reports = query.order_by(NRAReport.period_start.desc()).all()

        return [
            {
                "id": r.id,
                "report_type": r.report_type,
                "period_start": r.period_start.isoformat(),
                "period_end": r.period_end.isoformat(),
                "total_sales": float(r.total_sales),
                "total_vat": float(r.total_vat),
                "total_receipts": r.total_receipts,
                "status": r.status,
                "nra_reference": r.nra_reference,
                "generated_at": r.generated_at.isoformat(),
                "sent_at": r.sent_at.isoformat() if r.sent_at else None
            }
            for r in reports
        ]

    # ==================== SAF-T EXPORT ====================

    def generate_saft_export(self, venue_id: int, start: date, end: date) -> Dict[str, Any]:
        """Generate SAF-T (Standard Audit File for Tax) export."""
        from app.models.v6_features_models import FiscalDocument

        if not self.db:
            return {}

        documents = self.db.query(FiscalDocument).filter(
            FiscalDocument.venue_id == venue_id,
            func.date(FiscalDocument.issued_at) >= start,
            func.date(FiscalDocument.issued_at) <= end
        ).all()

        return {
            "header": {
                "audit_file_version": "2.0",
                "audit_file_country": "BG",
                "audit_file_date_created": datetime.now(timezone.utc).isoformat(),
                "software_company": "BJS POS",
                "software_version": "6.0",
                "selection_criteria": {
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat()
                }
            },
            "master_files": {
                "general_ledger_accounts": [],
                "customers": [],
                "suppliers": []
            },
            "source_documents": {
                "sales_invoices": [
                    {
                        "invoice_no": d.document_number,
                        "invoice_date": d.issued_at.isoformat(),
                        "total_invoice": float(d.total_with_vat),
                        "vat_amount": float(d.total_vat),
                        "lines": d.items
                    }
                    for d in documents if d.document_type in
                    [TaxDocumentType.FISCAL_RECEIPT.value, TaxDocumentType.INVOICE.value]
                ]
            }
        }

    # ==================== GDPR CONSENT ====================

    def record_consent(self, venue_id: int, customer_id: int, consent_type: str,
                       consented: bool, consent_text: str, **kwargs) -> Dict[str, Any]:
        """Record GDPR consent."""
        from app.models.v6_features_models import GDPRConsent

        if not self.db:
            return {"success": False, "error": "No database session"}

        # Check if consent already exists
        existing = self.db.query(GDPRConsent).filter(
            GDPRConsent.customer_id == customer_id,
            GDPRConsent.consent_type == consent_type
        ).first()

        if existing:
            existing.consented = consented
            existing.consent_text = consent_text
            existing.ip_address = kwargs.get('ip_address')
            existing.user_agent = kwargs.get('user_agent')
            if consented:
                existing.given_at = datetime.now(timezone.utc)
                existing.withdrawn_at = None
            else:
                existing.withdrawn_at = datetime.now(timezone.utc)
            consent = existing
        else:
            consent = GDPRConsent(
                venue_id=venue_id,
                customer_id=customer_id,
                consent_type=consent_type,
                consented=consented,
                consent_text=consent_text,
                ip_address=kwargs.get('ip_address'),
                user_agent=kwargs.get('user_agent'),
                given_at=datetime.now(timezone.utc)
            )
            self.db.add(consent)

        self.db.commit()
        self.db.refresh(consent)

        return {
            "success": True,
            "id": consent.id,
            "customer_id": customer_id,
            "consent_type": consent_type,
            "consented": consent.consented
        }

    def withdraw_consent(self, consent_id: int) -> Dict[str, Any]:
        """Withdraw GDPR consent."""
        from app.models.v6_features_models import GDPRConsent

        if not self.db:
            return {"success": False, "error": "No database session"}

        consent = self.db.query(GDPRConsent).filter(
            GDPRConsent.id == consent_id
        ).first()

        if not consent:
            return {"success": False, "error": "Consent not found"}

        consent.consented = False
        consent.withdrawn_at = datetime.now(timezone.utc)
        self.db.commit()

        return {"success": True, "consent_id": consent_id, "withdrawn": True}

    def get_customer_consents(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get all consents for a customer."""
        from app.models.v6_features_models import GDPRConsent

        if not self.db:
            return []

        consents = self.db.query(GDPRConsent).filter(
            GDPRConsent.customer_id == customer_id
        ).all()

        return [
            {
                "id": c.id,
                "consent_type": c.consent_type,
                "consented": c.consented,
                "given_at": c.given_at.isoformat(),
                "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None
            }
            for c in consents
        ]

    def export_customer_data(self, customer_id: int) -> Dict[str, Any]:
        """GDPR data export for customer."""
        from app.models.v6_features_models import GDPRConsent, FiscalDocument

        if not self.db:
            return {}

        consents = self.db.query(GDPRConsent).filter(
            GDPRConsent.customer_id == customer_id
        ).all()

        # Get invoices for customer (by VAT number if available)
        documents = []

        return {
            "customer_id": customer_id,
            "export_date": datetime.now(timezone.utc).isoformat(),
            "consents": [
                {
                    "consent_type": c.consent_type,
                    "consented": c.consented,
                    "given_at": c.given_at.isoformat()
                }
                for c in consents
            ],
            "documents": documents
        }

    def delete_customer_data(self, customer_id: int) -> Dict[str, Any]:
        """GDPR right to be forgotten."""
        from app.models.v6_features_models import GDPRConsent

        if not self.db:
            return {"success": False, "error": "No database session"}

        # Remove consents
        deleted = self.db.query(GDPRConsent).filter(
            GDPRConsent.customer_id == customer_id
        ).delete()

        self.db.commit()

        logger.info(f"Deleted GDPR data for customer {customer_id}")

        return {
            "success": True,
            "customer_id": customer_id,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "consents_deleted": deleted
        }

    # ==================== DASHBOARD ====================

    def get_compliance_dashboard(self, venue_id: int) -> Dict[str, Any]:
        """Get compliance dashboard data."""
        from app.models.v6_features_models import FiscalDocument, NRAReport

        if not self.db:
            return {}

        today = date.today()
        month_start = date(today.year, today.month, 1)

        # Today's documents
        docs_today = self.db.query(FiscalDocument).filter(
            FiscalDocument.venue_id == venue_id,
            func.date(FiscalDocument.issued_at) == today
        ).all()

        # Month's documents
        docs_month = self.db.query(FiscalDocument).filter(
            FiscalDocument.venue_id == venue_id,
            func.date(FiscalDocument.issued_at) >= month_start
        ).all()

        # Pending reports
        pending_reports = self.db.query(NRAReport).filter(
            NRAReport.venue_id == venue_id,
            NRAReport.status == NRAReportStatus.PENDING.value
        ).count()

        receipts_today = [d for d in docs_today if d.document_type == TaxDocumentType.FISCAL_RECEIPT.value]
        stornos_today = [d for d in docs_today if d.document_type == TaxDocumentType.STORNO.value]

        return {
            "date": today.isoformat(),
            "receipts_today": len(receipts_today),
            "stornos_today": len(stornos_today),
            "sales_today": sum(float(d.total_with_vat) for d in receipts_today),
            "vat_today": sum(float(d.total_vat) for d in receipts_today),
            "receipts_mtd": len([d for d in docs_month
                                 if d.document_type == TaxDocumentType.FISCAL_RECEIPT.value]),
            "sales_mtd": sum(float(d.total_with_vat) for d in docs_month
                             if d.document_type == TaxDocumentType.FISCAL_RECEIPT.value),
            "vat_mtd": sum(float(d.total_vat) for d in docs_month
                           if d.document_type == TaxDocumentType.FISCAL_RECEIPT.value),
            "pending_reports": pending_reports
        }
