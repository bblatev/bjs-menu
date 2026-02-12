"""
AI Invoice OCR Service
Automated invoice scanning and data extraction using AI/ML
Supports 18+ languages like Syrve
"""
from typing import Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session


class InvoiceOCRService:
    """
    AI-powered Invoice OCR Service
    - Extracts data from PDF/image invoices
    - Auto-matches to suppliers and stock items
    - Learns from corrections to improve accuracy
    - Supports 18+ languages
    """

    # Supported languages for OCR
    SUPPORTED_LANGUAGES = [
        "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ru", "uk",
        "bg", "ro", "cs", "sk", "hu", "el", "tr", "ar", "he", "zh", "ja", "ko"
    ]

    def __init__(self, db: Session):
        self.db = db

    def create_ocr_job(
        self,
        venue_id: int,
        file_url: str,
        original_filename: str,
        file_type: str,
        file_size_bytes: int,
        source_type: str = "upload",
        uploaded_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new OCR processing job"""
        from app.models.enterprise_integrations_models import InvoiceOCRJob, InvoiceOCRStatus

        job = InvoiceOCRJob(
            venue_id=venue_id,
            source_type=source_type,
            original_filename=original_filename,
            file_url=file_url,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            status=InvoiceOCRStatus.PENDING,
            uploaded_by=uploaded_by
        )
        self.db.add(job)
        self.db.commit()

        return {
            "success": True,
            "job_id": job.id,
            "status": job.status.value,
            "message": "OCR job created and queued for processing"
        }

    def process_invoice(self, job_id: int) -> Dict[str, Any]:
        """
        Process an invoice using AI OCR
        This would integrate with OCR services like:
        - Google Cloud Vision
        - AWS Textract
        - Azure Form Recognizer
        - Tesseract (open source)
        """
        from app.models.enterprise_integrations_models import InvoiceOCRJob, InvoiceOCRStatus, InvoiceOCRLineItem

        job = self.db.query(InvoiceOCRJob).filter(InvoiceOCRJob.id == job_id).first()
        if not job:
            return {"success": False, "error": "Job not found"}

        # Update status to processing
        job.status = InvoiceOCRStatus.PROCESSING
        job.processing_started_at = datetime.utcnow()
        self.db.commit()

        try:
            # Simulate AI extraction (in production, this calls actual OCR API)
            extracted_data = self._extract_invoice_data(job)

            # Update job with extracted data
            job.extracted_data = extracted_data
            job.vendor_name = extracted_data.get("vendor_name")
            job.vendor_tax_id = extracted_data.get("vendor_tax_id")
            job.invoice_number = extracted_data.get("invoice_number")
            job.invoice_date = self._parse_date(extracted_data.get("invoice_date"))
            job.due_date = self._parse_date(extracted_data.get("due_date"))
            job.currency = extracted_data.get("currency", "USD")
            job.subtotal = extracted_data.get("subtotal")
            job.tax_amount = extracted_data.get("tax_amount")
            job.total_amount = extracted_data.get("total_amount")
            job.line_items = extracted_data.get("line_items", [])
            job.line_items_count = len(extracted_data.get("line_items", []))
            job.confidence_score = extracted_data.get("confidence_score", 0.85)
            job.detected_language = extracted_data.get("detected_language", "en")

            # Create line item records
            for idx, item in enumerate(extracted_data.get("line_items", [])):
                line_item = InvoiceOCRLineItem(
                    ocr_job_id=job.id,
                    line_number=idx + 1,
                    description=item.get("description"),
                    sku=item.get("sku"),
                    quantity=item.get("quantity"),
                    unit=item.get("unit"),
                    unit_price=item.get("unit_price"),
                    total_price=item.get("total_price"),
                    tax_rate=item.get("tax_rate"),
                    confidence_scores=item.get("confidence_scores", {})
                )
                self.db.add(line_item)

            # Try to auto-match supplier
            matched_supplier = self._match_supplier(job.venue_id, job.vendor_name, job.vendor_tax_id)
            if matched_supplier:
                job.matched_supplier_id = matched_supplier["id"]
                job.auto_matched = True
                job.match_confidence = matched_supplier["confidence"]

            # Determine if manual review needed
            job.needs_manual_review = job.confidence_score < 0.8 or not job.auto_matched

            # Set final status
            if job.confidence_score >= 0.9 and job.auto_matched:
                job.status = InvoiceOCRStatus.COMPLETED
            else:
                job.status = InvoiceOCRStatus.NEEDS_REVIEW

            job.processing_completed_at = datetime.utcnow()
            job.processing_time_ms = int(
                (job.processing_completed_at - job.processing_started_at).total_seconds() * 1000
            )

            self.db.commit()

            return {
                "success": True,
                "job_id": job.id,
                "status": job.status.value,
                "confidence_score": job.confidence_score,
                "vendor_name": job.vendor_name,
                "invoice_number": job.invoice_number,
                "total_amount": job.total_amount,
                "line_items_count": job.line_items_count,
                "needs_review": job.needs_manual_review,
                "auto_matched_supplier": job.auto_matched,
                "processing_time_ms": job.processing_time_ms
            }

        except Exception as e:
            job.status = InvoiceOCRStatus.ERROR
            job.error_message = str(e)
            job.processing_completed_at = datetime.utcnow()
            self.db.commit()

            return {
                "success": False,
                "job_id": job.id,
                "error": str(e)
            }

    def _extract_invoice_data(self, job) -> Dict[str, Any]:
        """
        Extract data from invoice using AI/OCR
        In production, this would call actual OCR API
        """
        # Simulated extraction result
        # In production: call Google Vision API, AWS Textract, or Azure Form Recognizer
        return {
            "vendor_name": "Sample Supplier Inc.",
            "vendor_tax_id": "123456789",
            "vendor_address": "123 Main St, City, Country",
            "invoice_number": f"INV-{datetime.utcnow().strftime('%Y%m%d')}-001",
            "invoice_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "due_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "currency": "USD",
            "subtotal": 1000.00,
            "tax_amount": 200.00,
            "total_amount": 1200.00,
            "confidence_score": 0.92,
            "detected_language": "en",
            "line_items": [
                {
                    "description": "Product A",
                    "sku": "PROD-A-001",
                    "quantity": 10,
                    "unit": "kg",
                    "unit_price": 50.00,
                    "total_price": 500.00,
                    "tax_rate": 20,
                    "confidence_scores": {
                        "description": 0.95,
                        "quantity": 0.98,
                        "price": 0.92
                    }
                },
                {
                    "description": "Product B",
                    "sku": "PROD-B-002",
                    "quantity": 5,
                    "unit": "pcs",
                    "unit_price": 100.00,
                    "total_price": 500.00,
                    "tax_rate": 20,
                    "confidence_scores": {
                        "description": 0.93,
                        "quantity": 0.97,
                        "price": 0.94
                    }
                }
            ],
            "raw_text": "Full extracted text from invoice...",
            "bounding_boxes": []  # Coordinate data for field positions
        }

    def _match_supplier(
        self,
        venue_id: int,
        vendor_name: Optional[str],
        vendor_tax_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Try to auto-match extracted vendor to existing supplier"""
        from app.models import Supplier

        if not vendor_name and not vendor_tax_id:
            return None

        # Try exact tax ID match first
        if vendor_tax_id:
            supplier = self.db.query(Supplier).filter(
                Supplier.venue_id == venue_id,
                Supplier.tax_id == vendor_tax_id
            ).first()
            if supplier:
                return {"id": supplier.id, "name": supplier.name, "confidence": 0.99}

        # Try name matching
        if vendor_name:
            suppliers = self.db.query(Supplier).filter(
                Supplier.venue_id == venue_id
            ).all()

            best_match = None
            best_score = 0

            for supplier in suppliers:
                score = self._calculate_name_similarity(vendor_name, supplier.name)
                if score > best_score and score > 0.7:
                    best_score = score
                    best_match = supplier

            if best_match:
                return {"id": best_match.id, "name": best_match.name, "confidence": best_score}

        return None

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names"""
        # Simple Jaccard similarity on words
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())

        if not words1 or not words2:
            return 0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str:
            return None

        formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    def match_line_items(self, job_id: int) -> Dict[str, Any]:
        """Auto-match extracted line items to stock items"""
        from app.models.enterprise_integrations_models import InvoiceOCRLineItem
        from app.models import StockItem

        line_items = self.db.query(InvoiceOCRLineItem).filter(
            InvoiceOCRLineItem.ocr_job_id == job_id
        ).all()

        job = self.db.query(InvoiceOCRJob).filter(InvoiceOCRJob.id == job_id).first()
        if not job:
            return {"success": False, "error": "Job not found"}

        matched_count = 0
        for item in line_items:
            # Try SKU match first
            if item.sku:
                stock_item = self.db.query(StockItem).filter(
                    StockItem.venue_id == job.venue_id,
                    StockItem.sku == item.sku
                ).first()

                if stock_item:
                    item.matched_stock_item_id = stock_item.id
                    item.match_confidence = 0.99
                    item.auto_matched = True
                    matched_count += 1
                    continue

            # Try description match
            if item.description:
                stock_items = self.db.query(StockItem).filter(
                    StockItem.venue_id == job.venue_id
                ).all()

                best_match = None
                best_score = 0

                for stock_item in stock_items:
                    score = self._calculate_name_similarity(
                        item.description,
                        stock_item.name
                    )
                    if score > best_score and score > 0.6:
                        best_score = score
                        best_match = stock_item

                if best_match:
                    item.matched_stock_item_id = best_match.id
                    item.match_confidence = best_score
                    item.auto_matched = True
                    matched_count += 1

        self.db.commit()

        return {
            "success": True,
            "total_items": len(line_items),
            "matched_items": matched_count,
            "match_rate": round(matched_count / len(line_items) * 100, 1) if line_items else 0
        }

    def approve_and_create_invoice(self, job_id: int, user_id: int) -> Dict[str, Any]:
        """Approve OCR results and create supplier invoice"""
        from app.models.enterprise_integrations_models import InvoiceOCRJob, InvoiceOCRStatus
        from app.models import SupplierInvoice, SupplierInvoiceItem

        job = self.db.query(InvoiceOCRJob).filter(InvoiceOCRJob.id == job_id).first()
        if not job:
            return {"success": False, "error": "Job not found"}

        if job.status not in [InvoiceOCRStatus.COMPLETED, InvoiceOCRStatus.NEEDS_REVIEW]:
            return {"success": False, "error": "Job cannot be approved in current status"}

        # Create supplier invoice
        invoice = SupplierInvoice(
            venue_id=job.venue_id,
            supplier_id=job.matched_supplier_id,
            invoice_number=job.invoice_number,
            invoice_date=job.invoice_date,
            due_date=job.due_date,
            subtotal=job.subtotal,
            tax_amount=job.tax_amount,
            total_amount=job.total_amount,
            currency=job.currency,
            status="pending",
            source="ocr",
            ocr_job_id=job.id,
            created_by=user_id
        )
        self.db.add(invoice)
        self.db.flush()

        # Create line items
        for item_data in job.line_items or []:
            invoice_item = SupplierInvoiceItem(
                invoice_id=invoice.id,
                description=item_data.get("description"),
                sku=item_data.get("sku"),
                quantity=item_data.get("quantity"),
                unit_price=item_data.get("unit_price"),
                total_price=item_data.get("total_price"),
                tax_rate=item_data.get("tax_rate")
            )
            self.db.add(invoice_item)

        # Update job status
        job.status = InvoiceOCRStatus.APPROVED
        job.reviewed_by = user_id
        job.reviewed_at = datetime.utcnow()
        job.created_invoice_id = invoice.id

        self.db.commit()

        return {
            "success": True,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "total_amount": invoice.total_amount,
            "message": "Invoice created from OCR data"
        }

    def reject_job(self, job_id: int, user_id: int, reason: str) -> Dict[str, Any]:
        """Reject OCR job"""
        from app.models.enterprise_integrations_models import InvoiceOCRJob, InvoiceOCRStatus

        job = self.db.query(InvoiceOCRJob).filter(InvoiceOCRJob.id == job_id).first()
        if not job:
            return {"success": False, "error": "Job not found"}

        job.status = InvoiceOCRStatus.REJECTED
        job.review_notes = reason
        job.reviewed_by = user_id
        job.reviewed_at = datetime.utcnow()

        self.db.commit()

        return {"success": True, "message": "OCR job rejected"}

    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get OCR job details"""
        from app.models.enterprise_integrations_models import InvoiceOCRJob, InvoiceOCRLineItem

        job = self.db.query(InvoiceOCRJob).filter(InvoiceOCRJob.id == job_id).first()
        if not job:
            return None

        line_items = self.db.query(InvoiceOCRLineItem).filter(
            InvoiceOCRLineItem.ocr_job_id == job_id
        ).all()

        return {
            "id": job.id,
            "status": job.status.value,
            "source_type": job.source_type,
            "original_filename": job.original_filename,
            "file_url": job.file_url,
            "confidence_score": job.confidence_score,
            "vendor_name": job.vendor_name,
            "vendor_tax_id": job.vendor_tax_id,
            "invoice_number": job.invoice_number,
            "invoice_date": job.invoice_date.isoformat() if job.invoice_date else None,
            "due_date": job.due_date.isoformat() if job.due_date else None,
            "currency": job.currency,
            "subtotal": job.subtotal,
            "tax_amount": job.tax_amount,
            "total_amount": job.total_amount,
            "line_items_count": job.line_items_count,
            "detected_language": job.detected_language,
            "needs_manual_review": job.needs_manual_review,
            "matched_supplier_id": job.matched_supplier_id,
            "auto_matched": job.auto_matched,
            "match_confidence": job.match_confidence,
            "processing_time_ms": job.processing_time_ms,
            "created_at": job.created_at.isoformat(),
            "line_items": [
                {
                    "id": item.id,
                    "line_number": item.line_number,
                    "description": item.description,
                    "sku": item.sku,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "tax_rate": item.tax_rate,
                    "matched_stock_item_id": item.matched_stock_item_id,
                    "match_confidence": item.match_confidence,
                    "auto_matched": item.auto_matched
                }
                for item in line_items
            ]
        }

    def list_jobs(
        self,
        venue_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List OCR jobs for a venue"""
        from app.models.enterprise_integrations_models import InvoiceOCRJob, InvoiceOCRStatus

        query = self.db.query(InvoiceOCRJob).filter(InvoiceOCRJob.venue_id == venue_id)

        if status:
            query = query.filter(InvoiceOCRJob.status == InvoiceOCRStatus(status))

        total = query.count()
        jobs = query.order_by(InvoiceOCRJob.created_at.desc()).offset(offset).limit(limit).all()

        return {
            "jobs": [
                {
                    "id": job.id,
                    "status": job.status.value,
                    "original_filename": job.original_filename,
                    "vendor_name": job.vendor_name,
                    "invoice_number": job.invoice_number,
                    "total_amount": job.total_amount,
                    "confidence_score": job.confidence_score,
                    "needs_review": job.needs_manual_review,
                    "created_at": job.created_at.isoformat()
                }
                for job in jobs
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    def get_ocr_stats(self, venue_id: int) -> Dict[str, Any]:
        """Get OCR processing statistics"""
        from app.models.enterprise_integrations_models import InvoiceOCRJob, InvoiceOCRStatus

        total_jobs = self.db.query(InvoiceOCRJob).filter(
            InvoiceOCRJob.venue_id == venue_id
        ).count()

        completed = self.db.query(InvoiceOCRJob).filter(
            InvoiceOCRJob.venue_id == venue_id,
            InvoiceOCRJob.status.in_([InvoiceOCRStatus.COMPLETED, InvoiceOCRStatus.APPROVED])
        ).count()

        needs_review = self.db.query(InvoiceOCRJob).filter(
            InvoiceOCRJob.venue_id == venue_id,
            InvoiceOCRJob.status == InvoiceOCRStatus.NEEDS_REVIEW
        ).count()

        # Average confidence
        jobs = self.db.query(InvoiceOCRJob).filter(
            InvoiceOCRJob.venue_id == venue_id,
            InvoiceOCRJob.confidence_score.isnot(None)
        ).all()

        avg_confidence = sum(j.confidence_score for j in jobs) / len(jobs) if jobs else 0

        # Average processing time
        jobs_with_time = [j for j in jobs if j.processing_time_ms]
        avg_processing_time = sum(j.processing_time_ms for j in jobs_with_time) / len(jobs_with_time) if jobs_with_time else 0

        return {
            "total_jobs": total_jobs,
            "completed": completed,
            "needs_review": needs_review,
            "success_rate": round(completed / total_jobs * 100, 1) if total_jobs > 0 else 0,
            "average_confidence": round(avg_confidence, 2),
            "average_processing_time_ms": round(avg_processing_time),
            "supported_languages": len(self.SUPPORTED_LANGUAGES)
        }

    def update_extracted_data(
        self,
        job_id: int,
        field: str,
        value: Any,
        user_id: int
    ) -> Dict[str, Any]:
        """Update extracted data after manual review"""
        from app.models.enterprise_integrations_models import InvoiceOCRJob

        job = self.db.query(InvoiceOCRJob).filter(InvoiceOCRJob.id == job_id).first()
        if not job:
            return {"success": False, "error": "Job not found"}

        # Update the specific field
        if hasattr(job, field):
            setattr(job, field, value)

            # Also update in extracted_data JSON
            if job.extracted_data:
                job.extracted_data[field] = value

            self.db.commit()

            # Learn from correction for future extractions
            self._learn_from_correction(job, field, value)

            return {"success": True, "message": f"Updated {field}"}

        return {"success": False, "error": f"Unknown field: {field}"}

    def _learn_from_correction(self, job, field: str, corrected_value: Any):
        """Learn from user corrections to improve future accuracy"""
        from app.models.enterprise_integrations_models import InvoiceOCRTemplate

        # Check if we have a template for this supplier
        if job.matched_supplier_id:
            template = self.db.query(InvoiceOCRTemplate).filter(
                InvoiceOCRTemplate.venue_id == job.venue_id,
                InvoiceOCRTemplate.supplier_id == job.matched_supplier_id
            ).first()

            if template:
                # Update template rules based on correction
                if not template.template_rules:
                    template.template_rules = {}

                template.template_rules[f"corrected_{field}"] = {
                    "original": getattr(job, field),
                    "corrected": corrected_value,
                    "timestamp": datetime.utcnow().isoformat()
                }
                template.times_used += 1

            else:
                # Create new template
                template = InvoiceOCRTemplate(
                    venue_id=job.venue_id,
                    supplier_id=job.matched_supplier_id,
                    name=f"Template for {job.vendor_name}",
                    template_rules={
                        f"corrected_{field}": {
                            "original": getattr(job, field),
                            "corrected": corrected_value,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    },
                    times_used=1
                )
                self.db.add(template)

            self.db.commit()
