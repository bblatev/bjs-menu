"""
Compliance & Audit Service - Section X
Immutable audit logs, fiscal archives, NRA compliance, age verification
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import hashlib
import json
import uuid


class ComplianceService:
    """Service for compliance, audit trails, and regulatory requirements."""
    
    # ==================== IMMUTABLE AUDIT LOG ====================
    
    @staticmethod
    def log_action(
        db: Session,
        venue_id: int,
        user_id: int,
        action_type: str,
        entity_type: str,
        entity_id: int,
        action_details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log an action to the immutable audit log.
        Uses blockchain-style checksums for integrity verification.
        """
        from app.models.advanced_features_v9 import ImmutableAuditLog
        
        # Get the previous log entry for chaining
        previous = db.query(ImmutableAuditLog).filter(
            ImmutableAuditLog.venue_id == venue_id
        ).order_by(ImmutableAuditLog.id.desc()).first()
        
        previous_checksum = previous.checksum if previous else "GENESIS"
        
        # Create the log entry
        log_data = {
            "venue_id": venue_id,
            "user_id": user_id,
            "action_type": action_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action_details": action_details,
            "timestamp": datetime.utcnow().isoformat(),
            "previous_checksum": previous_checksum
        }
        
        # Generate checksum
        data_string = json.dumps(log_data, sort_keys=True)
        checksum = hashlib.sha256(data_string.encode()).hexdigest()
        
        log = ImmutableAuditLog(
            venue_id=venue_id,
            user_id=user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            action_details=action_details,
            ip_address=ip_address,
            user_agent=user_agent,
            previous_checksum=previous_checksum,
            checksum=checksum
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        
        return {
            "id": log.id,
            "action_type": action_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "checksum": checksum,
            "logged_at": log.created_at.isoformat()
        }
    
    @staticmethod
    def verify_audit_chain(
        db: Session,
        venue_id: int,
        start_id: Optional[int] = None,
        end_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Verify the integrity of the audit log chain."""
        from app.models.advanced_features_v9 import ImmutableAuditLog
        
        query = db.query(ImmutableAuditLog).filter(
            ImmutableAuditLog.venue_id == venue_id
        )
        
        if start_id:
            query = query.filter(ImmutableAuditLog.id >= start_id)
        if end_id:
            query = query.filter(ImmutableAuditLog.id <= end_id)
        
        logs = query.order_by(ImmutableAuditLog.id.asc()).all()
        
        if not logs:
            return {"verified": True, "message": "No logs to verify", "entries_checked": 0}
        
        errors = []
        previous_checksum = "GENESIS" if not start_id else None
        
        for log in logs:
            if previous_checksum is None:
                # First log after start_id, just get its previous
                previous_checksum = log.previous_checksum
            else:
                # Verify chain
                if log.previous_checksum != previous_checksum:
                    errors.append({
                        "log_id": log.id,
                        "error": "Chain broken - previous checksum mismatch",
                        "expected": previous_checksum,
                        "found": log.previous_checksum
                    })
            
            # Verify self checksum
            log_data = {
                "venue_id": log.venue_id,
                "actor_id": log.actor_id,
                "event_type": log.event_type,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "after_state": log.after_state,
                "timestamp": log.created_at.isoformat() if log.created_at else log.event_timestamp.isoformat(),
                "previous_checksum": log.previous_checksum
            }
            expected_checksum = hashlib.sha256(
                json.dumps(log_data, sort_keys=True).encode()
            ).hexdigest()
            
            if log.checksum != expected_checksum:
                errors.append({
                    "log_id": log.id,
                    "error": "Checksum mismatch - log may have been tampered",
                    "expected": expected_checksum,
                    "found": log.checksum
                })
            
            previous_checksum = log.checksum
        
        return {
            "verified": len(errors) == 0,
            "entries_checked": len(logs),
            "errors": errors,
            "first_entry_id": logs[0].id if logs else None,
            "last_entry_id": logs[-1].id if logs else None,
            "verification_timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def get_audit_logs(
        db: Session,
        venue_id: int,
        action_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit logs with filters."""
        from app.models.advanced_features_v9 import ImmutableAuditLog
        
        query = db.query(ImmutableAuditLog).filter(
            ImmutableAuditLog.venue_id == venue_id
        )
        
        if action_type:
            query = query.filter(ImmutableAuditLog.action_type == action_type)
        if entity_type:
            query = query.filter(ImmutableAuditLog.entity_type == entity_type)
        if user_id:
            query = query.filter(ImmutableAuditLog.user_id == user_id)
        if start_date:
            query = query.filter(ImmutableAuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(ImmutableAuditLog.created_at <= end_date)
        
        logs = query.order_by(ImmutableAuditLog.created_at.desc()).limit(limit).all()
        
        return [{
            "id": l.id,
            "user_id": l.user_id,
            "action_type": l.action_type,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "action_details": l.action_details,
            "ip_address": l.ip_address,
            "checksum": l.checksum[:16] + "...",  # Truncated for display
            "created_at": l.created_at.isoformat()
        } for l in logs]
    
    # ==================== FISCAL ARCHIVE ====================
    
    @staticmethod
    def archive_fiscal_receipt(
        db: Session,
        venue_id: int,
        order_id: int,
        receipt_number: str,
        fiscal_device_id: str,
        receipt_data: Dict[str, Any],
        signature: str
    ) -> Dict[str, Any]:
        """Archive a fiscal receipt for compliance."""
        from app.models.advanced_features_v9 import FiscalArchive
        
        archive = FiscalArchive(
            venue_id=venue_id,
            order_id=order_id,
            receipt_number=receipt_number,
            fiscal_device_id=fiscal_device_id,
            receipt_data=receipt_data,
            signature=signature,
            archived_at=datetime.utcnow()
        )
        db.add(archive)
        db.commit()
        db.refresh(archive)
        
        return {
            "id": archive.id,
            "receipt_number": receipt_number,
            "order_id": order_id,
            "archived_at": archive.archived_at.isoformat(),
            "message": "Receipt archived successfully"
        }
    
    @staticmethod
    def get_fiscal_archive(
        db: Session,
        venue_id: int,
        start_date: date,
        end_date: date,
        receipt_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get fiscal archive for a period."""
        from app.models.advanced_features_v9 import FiscalArchive
        
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        query = db.query(FiscalArchive).filter(
            FiscalArchive.venue_id == venue_id,
            FiscalArchive.archived_at >= start_dt,
            FiscalArchive.archived_at <= end_dt
        )
        
        if receipt_number:
            query = query.filter(FiscalArchive.receipt_number == receipt_number)
        
        receipts = query.order_by(FiscalArchive.archived_at.desc()).all()
        
        return {
            "venue_id": venue_id,
            "period": {"start": str(start_date), "end": str(end_date)},
            "total_receipts": len(receipts),
            "receipts": [{
                "id": r.id,
                "receipt_number": r.receipt_number,
                "order_id": r.order_id,
                "fiscal_device_id": r.fiscal_device_id,
                "archived_at": r.archived_at.isoformat()
            } for r in receipts]
        }
    
    # ==================== NRA EXPORT ====================
    
    @staticmethod
    def create_nra_export(
        db: Session,
        venue_id: int,
        export_type: str,  # "daily", "monthly", "inspection"
        start_date: date,
        end_date: date,
        requested_by: int
    ) -> Dict[str, Any]:
        """Create NRA export package for Bulgarian tax authority."""
        from app.models.advanced_features_v9 import NRAExportLog, FiscalArchive
        
        # Get fiscal data for the period
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        receipts = db.query(FiscalArchive).filter(
            FiscalArchive.venue_id == venue_id,
            FiscalArchive.archived_at >= start_dt,
            FiscalArchive.archived_at <= end_dt
        ).all()
        
        # Calculate totals from receipt data
        total_amount = Decimal("0")
        total_vat = Decimal("0")
        vat_by_rate = {}  # Track VAT by rate for NRA reporting

        receipts_data = []
        for r in receipts:
            receipt_info = {
                "receipt_number": r.receipt_number,
                "order_id": r.order_id,
                "fiscal_device_id": r.fiscal_device_id,
                "signature": r.signature,
                "data": r.receipt_data
            }
            receipts_data.append(receipt_info)

            # Extract totals from receipt_data
            if r.receipt_data:
                # Handle different possible structures of receipt_data
                receipt_total = Decimal("0")
                receipt_vat = Decimal("0")

                # Try to get total from common fields
                if isinstance(r.receipt_data, dict):
                    # Direct total field
                    if "total" in r.receipt_data:
                        receipt_total = Decimal(str(r.receipt_data["total"]))
                    elif "total_amount" in r.receipt_data:
                        receipt_total = Decimal(str(r.receipt_data["total_amount"]))
                    elif "grand_total" in r.receipt_data:
                        receipt_total = Decimal(str(r.receipt_data["grand_total"]))

                    # VAT fields
                    if "vat" in r.receipt_data:
                        receipt_vat = Decimal(str(r.receipt_data["vat"]))
                    elif "vat_amount" in r.receipt_data:
                        receipt_vat = Decimal(str(r.receipt_data["vat_amount"]))
                    elif "tax" in r.receipt_data:
                        receipt_vat = Decimal(str(r.receipt_data["tax"]))

                    # VAT breakdown by rate (NRA requirement)
                    if "vat_breakdown" in r.receipt_data:
                        for rate, amount in r.receipt_data["vat_breakdown"].items():
                            rate_key = str(rate)
                            vat_by_rate[rate_key] = vat_by_rate.get(rate_key, Decimal("0")) + Decimal(str(amount))

                    # Sum from items if no total
                    if receipt_total == 0 and "items" in r.receipt_data:
                        for item in r.receipt_data["items"]:
                            if isinstance(item, dict):
                                item_total = Decimal(str(item.get("total", 0) or item.get("amount", 0) or 0))
                                receipt_total += item_total
                                item_vat = Decimal(str(item.get("vat", 0) or item.get("tax", 0) or 0))
                                receipt_vat += item_vat

                total_amount += receipt_total
                total_vat += receipt_vat

        # Generate export data
        export_data = {
            "header": {
                "venue_id": venue_id,
                "export_type": export_type,
                "period_start": str(start_date),
                "period_end": str(end_date),
                "generated_at": datetime.utcnow().isoformat(),
                "receipt_count": len(receipts),
                "total_amount": str(total_amount),
                "total_vat": str(total_vat),
                "vat_by_rate": {k: str(v) for k, v in vat_by_rate.items()}
            },
            "receipts": receipts_data
        }
        
        # Generate checksum
        checksum = hashlib.sha256(
            json.dumps(export_data, sort_keys=True, default=str).encode()
        ).hexdigest()
        
        # Create export log
        export_log = NRAExportLog(
            venue_id=venue_id,
            export_type=export_type,
            period_start=start_date,
            period_end=end_date,
            receipt_count=len(receipts),
            total_amount=total_amount,
            total_vat=total_vat,
            export_data=export_data,
            checksum=checksum,
            requested_by=requested_by,
            status="completed"
        )
        db.add(export_log)
        db.commit()
        db.refresh(export_log)
        
        return {
            "id": export_log.id,
            "export_type": export_type,
            "period": {"start": str(start_date), "end": str(end_date)},
            "receipt_count": len(receipts),
            "checksum": checksum,
            "status": "completed",
            "generated_at": export_log.created_at.isoformat()
        }
    
    @staticmethod
    def get_nra_exports(
        db: Session,
        venue_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get list of NRA exports."""
        from app.models.advanced_features_v9 import NRAExportLog
        
        exports = db.query(NRAExportLog).filter(
            NRAExportLog.venue_id == venue_id
        ).order_by(NRAExportLog.created_at.desc()).limit(limit).all()
        
        return [{
            "id": e.id,
            "export_type": e.export_type,
            "period_start": str(e.period_start),
            "period_end": str(e.period_end),
            "receipt_count": e.receipt_count,
            "total_amount": float(e.total_amount) if e.total_amount else 0,
            "status": e.status,
            "checksum": e.checksum[:16] + "...",
            "created_at": e.created_at.isoformat()
        } for e in exports]
    
    # ==================== AGE VERIFICATION ====================
    
    @staticmethod
    def log_age_verification(
        db: Session,
        venue_id: int,
        staff_id: int,
        order_id: Optional[int],
        verification_method: str,  # "id_check", "passport", "driving_license", "visual"
        guest_birth_date: Optional[date] = None,
        document_number: Optional[str] = None,
        verification_passed: bool = True,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log an age verification for compliance."""
        from app.models.advanced_features_v9 import AgeVerificationLog
        
        log = AgeVerificationLog(
            venue_id=venue_id,
            staff_id=staff_id,
            order_id=order_id,
            verification_method=verification_method,
            guest_birth_date=guest_birth_date,
            document_number_hash=hashlib.sha256(document_number.encode()).hexdigest() if document_number else None,
            verification_passed=verification_passed,
            notes=notes
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        
        return {
            "id": log.id,
            "order_id": order_id,
            "verification_method": verification_method,
            "verification_passed": verification_passed,
            "logged_at": log.created_at.isoformat()
        }
    
    @staticmethod
    def get_age_verification_report(
        db: Session,
        venue_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get age verification report for compliance."""
        from app.models.advanced_features_v9 import AgeVerificationLog
        
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        logs = db.query(AgeVerificationLog).filter(
            AgeVerificationLog.venue_id == venue_id,
            AgeVerificationLog.created_at >= start_dt,
            AgeVerificationLog.created_at <= end_dt
        ).all()
        
        by_method = {}
        by_staff = {}
        failed_count = 0
        
        for log in logs:
            by_method[log.verification_method] = by_method.get(log.verification_method, 0) + 1
            by_staff[log.staff_id] = by_staff.get(log.staff_id, 0) + 1
            if not log.verification_passed:
                failed_count += 1
        
        return {
            "venue_id": venue_id,
            "period": {"start": str(start_date), "end": str(end_date)},
            "total_verifications": len(logs),
            "passed": len(logs) - failed_count,
            "failed": failed_count,
            "by_method": by_method,
            "by_staff": by_staff,
            "compliance_rate": round((len(logs) - failed_count) / len(logs) * 100, 1) if logs else 100
        }
    
    # ==================== GDPR COMPLIANCE ====================

    @staticmethod
    def process_data_deletion_request(
        db: Session,
        venue_id: int,
        customer_id: int,
        requested_by: int,
        reason: str
    ) -> Dict[str, Any]:
        """Process GDPR data deletion request - anonymize personal data."""
        from app.models.advanced_features_v9 import (
            GuestPreference, CustomerLifetimeValue, AgeVerificationLog
        )
        from app.models import Customer, Order, Reservation

        request_id = str(uuid.uuid4())
        anonymized_items = []

        # Get the customer record
        customer = db.query(Customer).filter(
            Customer.id == customer_id,
            Customer.venue_id == venue_id
        ).first()

        if not customer:
            return {
                "request_id": request_id,
                "customer_id": customer_id,
                "status": "failed",
                "message": "Customer not found",
                "requested_at": datetime.utcnow().isoformat()
            }

        # Anonymize customer personal data
        anonymized_name = f"DELETED_USER_{customer_id}"
        original_email = customer.email

        customer.name = anonymized_name
        customer.email = f"deleted_{customer_id}@anonymized.local"
        customer.phone = None
        customer.notes = f"[GDPR Deletion - {datetime.utcnow().isoformat()}]"
        customer.allergies = None
        customer.dietary_preferences = None
        customer.favorite_items = None
        customer.tags = None
        customer.marketing_consent = False
        customer.birthday = None
        anonymized_items.append("customer_profile")

        # Delete guest preferences
        prefs_deleted = db.query(GuestPreference).filter(
            GuestPreference.customer_id == customer_id
        ).delete()
        if prefs_deleted:
            anonymized_items.append("preferences")

        # Delete CLV data
        clv_deleted = db.query(CustomerLifetimeValue).filter(
            CustomerLifetimeValue.customer_id == customer_id
        ).delete()
        if clv_deleted:
            anonymized_items.append("clv_data")

        # Anonymize age verification logs (keep for compliance but remove PII)
        age_logs = db.query(AgeVerificationLog).filter(
            AgeVerificationLog.venue_id == venue_id
        ).all()
        for log in age_logs:
            if log.notes and str(customer_id) in log.notes:
                log.notes = "[ANONYMIZED]"
                log.guest_birth_date = None
                log.document_number_hash = None
        if age_logs:
            anonymized_items.append("age_verification_logs")

        # Anonymize reservations (keep for business records but remove PII)
        reservations = db.query(Reservation).filter(
            Reservation.customer_id == customer_id
        ).all()
        for res in reservations:
            if hasattr(res, 'guest_name'):
                res.guest_name = anonymized_name
            if hasattr(res, 'guest_phone'):
                res.guest_phone = None
            if hasattr(res, 'guest_email'):
                res.guest_email = None
            if hasattr(res, 'special_requests'):
                res.special_requests = "[ANONYMIZED]"
        if reservations:
            anonymized_items.append("reservations")

        # Log the deletion request in audit log
        ComplianceService.log_action(
            db=db,
            venue_id=venue_id,
            user_id=requested_by,
            action_type="gdpr_deletion",
            entity_type="customer",
            entity_id=customer_id,
            action_details={
                "reason": reason,
                "original_email_hash": hashlib.sha256(original_email.encode()).hexdigest() if original_email else None,
                "anonymized_items": anonymized_items,
                "request_id": request_id
            }
        )

        db.commit()

        return {
            "request_id": request_id,
            "customer_id": customer_id,
            "status": "completed",
            "message": "Personal data has been anonymized/deleted per GDPR requirements.",
            "anonymized_items": anonymized_items,
            "completed_at": datetime.utcnow().isoformat()
        }

    @staticmethod
    def generate_data_export(
        db: Session,
        venue_id: int,
        customer_id: int
    ) -> Dict[str, Any]:
        """Generate GDPR data export for a customer - compile all personal data."""
        from app.models.advanced_features_v9 import (
            GuestPreference, CustomerLifetimeValue
        )
        from app.models import Customer, Order, OrderItem, Reservation

        export_id = str(uuid.uuid4())
        export_data = {
            "export_id": export_id,
            "customer_id": customer_id,
            "generated_at": datetime.utcnow().isoformat(),
            "data_categories": {}
        }

        # Get customer profile
        customer = db.query(Customer).filter(
            Customer.id == customer_id,
            Customer.venue_id == venue_id
        ).first()

        if not customer:
            return {
                "export_id": export_id,
                "customer_id": customer_id,
                "status": "failed",
                "message": "Customer not found",
                "requested_at": datetime.utcnow().isoformat()
            }

        # Personal profile data
        export_data["data_categories"]["personal_profile"] = {
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "preferred_language": customer.preferred_language,
            "allergies": customer.allergies,
            "dietary_preferences": customer.dietary_preferences,
            "favorite_items": customer.favorite_items,
            "tags": customer.tags,
            "birthday": customer.birthday.isoformat() if customer.birthday else None,
            "loyalty_points": customer.loyalty_points,
            "loyalty_tier": customer.loyalty_tier,
            "marketing_consent": customer.marketing_consent,
            "created_at": customer.created_at.isoformat() if customer.created_at else None
        }

        # Preferences
        prefs = db.query(GuestPreference).filter(
            GuestPreference.customer_id == customer_id
        ).first()
        if prefs:
            export_data["data_categories"]["preferences"] = {
                "dietary_restrictions": prefs.dietary_restrictions,
                "allergies": prefs.allergies,
                "preferred_table_ids": prefs.preferred_table_ids,
                "preferred_areas": prefs.preferred_areas,
                "seating_notes": prefs.seating_notes,
                "preferred_waiter_ids": prefs.preferred_waiter_ids,
                "communication_preference": prefs.communication_preference,
                "language_preference": prefs.language_preference,
                "celebration_dates": prefs.celebration_dates,
                "favorite_drinks": prefs.favorite_drinks,
                "wine_preferences": prefs.wine_preferences,
                "is_vip": prefs.is_vip,
                "requires_accessibility": prefs.requires_accessibility
            }

        # Order history
        orders = db.query(Order).filter(
            Order.customer_id == customer_id
        ).all()
        export_data["data_categories"]["order_history"] = []
        for order in orders:
            items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            export_data["data_categories"]["order_history"].append({
                "order_id": order.id,
                "date": order.created_at.isoformat() if order.created_at else None,
                "total": float(order.total) if order.total else 0,
                "status": order.status,
                "items": [{"name": getattr(i, 'name', 'Item'), "quantity": i.quantity, "price": float(i.price) if i.price else 0} for i in items]
            })

        # Reservations
        reservations = db.query(Reservation).filter(
            Reservation.customer_id == customer_id
        ).all()
        export_data["data_categories"]["reservations"] = []
        for res in reservations:
            export_data["data_categories"]["reservations"].append({
                "reservation_id": res.id,
                "date": res.reservation_date.isoformat() if hasattr(res, 'reservation_date') and res.reservation_date else None,
                "party_size": getattr(res, 'party_size', None),
                "status": res.status,
                "special_requests": getattr(res, 'special_requests', None)
            })

        # CLV data (analytics about the customer)
        clv = db.query(CustomerLifetimeValue).filter(
            CustomerLifetimeValue.customer_id == customer_id
        ).first()
        if clv:
            export_data["data_categories"]["analytics"] = {
                "total_spend": float(clv.total_spend) if clv.total_spend else 0,
                "visit_count": clv.visit_count,
                "average_order_value": float(clv.average_order_value) if clv.average_order_value else 0,
                "customer_segment": clv.segment,
                "first_visit": clv.first_visit_date.isoformat() if clv.first_visit_date else None,
                "last_visit": clv.last_visit_date.isoformat() if clv.last_visit_date else None
            }

        # Log the export request
        ComplianceService.log_action(
            db=db,
            venue_id=venue_id,
            user_id=customer_id,  # Self-request
            action_type="gdpr_export",
            entity_type="customer",
            entity_id=customer_id,
            action_details={
                "export_id": export_id,
                "categories_exported": list(export_data["data_categories"].keys())
            }
        )

        db.commit()

        return {
            "export_id": export_id,
            "customer_id": customer_id,
            "status": "completed",
            "message": "Data export generated successfully.",
            "data": export_data,
            "generated_at": datetime.utcnow().isoformat()
        }


# Class aliases for backwards compatibility with endpoint imports
ImmutableAuditService = ComplianceService
FiscalArchiveService = ComplianceService
NRAExportService = ComplianceService
AgeVerificationService = ComplianceService

