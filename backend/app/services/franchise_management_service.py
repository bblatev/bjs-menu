"""
Franchise Management Service - BJS V6
======================================
Franchise fee calculation, royalty tracking, brand compliance, territory mapping
with full database integration.
"""

from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

logger = logging.getLogger(__name__)


class FranchiseStatus(str, Enum):
    PROSPECT = "prospect"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"
    UNDER_REVIEW = "under_review"


# Pydantic models for API responses
class FranchiseeResponse(BaseModel):
    id: int
    company_name: str
    contact_name: str
    email: str
    status: str
    territory: str

    model_config = ConfigDict(from_attributes=True)


class RoyaltyPaymentResponse(BaseModel):
    id: int
    franchisee_id: int
    gross_sales: float
    total_due: float
    status: str

    model_config = ConfigDict(from_attributes=True)


class FranchiseManagementService:
    """Franchise operations management with database persistence."""

    def __init__(self, db_session: Session = None):
        self.db = db_session

    # ==================== FRANCHISEE MANAGEMENT ====================

    def register_franchisee(self, company_name: str, contact_name: str,
                            email: str, phone: str, territory: str,
                            **kwargs) -> Dict[str, Any]:
        """Register a new franchise prospect."""
        from app.models.v6_features_models import Franchisee

        if not self.db:
            logger.warning("No database session - returning mock response")
            return {"id": 1, "company_name": company_name}

        # Check if email already exists
        existing = self.db.query(Franchisee).filter(
            Franchisee.email == email
        ).first()

        if existing:
            return {"success": False, "error": "Email already registered"}

        franchisee = Franchisee(
            company_name=company_name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            territory=territory,
            address=kwargs.get('address', ''),
            city=kwargs.get('city', ''),
            country=kwargs.get('country', 'Bulgaria'),
            franchise_fee=kwargs.get('franchise_fee', 50000),
            royalty_percent=kwargs.get('royalty_percent', 5.0),
            marketing_fund_percent=kwargs.get('marketing_fund_percent', 2.0),
            status=FranchiseStatus.PROSPECT.value
        )

        self.db.add(franchisee)
        self.db.commit()
        self.db.refresh(franchisee)

        logger.info(f"Registered franchisee {franchisee.id}: {company_name}")

        return {
            "success": True,
            "id": franchisee.id,
            "company_name": franchisee.company_name,
            "contact_name": franchisee.contact_name,
            "email": franchisee.email,
            "territory": franchisee.territory,
            "status": franchisee.status
        }

    def approve_franchisee(self, franchisee_id: int,
                           agreement_years: int = 10) -> Dict[str, Any]:
        """Approve a franchise prospect."""
        from app.models.v6_features_models import Franchisee

        if not self.db:
            return {"success": False, "error": "No database session"}

        franchisee = self.db.query(Franchisee).filter(
            Franchisee.id == franchisee_id
        ).first()

        if not franchisee:
            return {"success": False, "error": "Franchisee not found"}

        franchisee.status = FranchiseStatus.APPROVED.value
        franchisee.agreement_start = date.today()
        franchisee.agreement_end = date.today() + timedelta(days=365 * agreement_years)
        self.db.commit()

        logger.info(f"Approved franchisee {franchisee_id}")

        return {
            "success": True,
            "franchisee_id": franchisee_id,
            "status": franchisee.status,
            "agreement_start": franchisee.agreement_start.isoformat(),
            "agreement_end": franchisee.agreement_end.isoformat()
        }

    def activate_franchisee(self, franchisee_id: int,
                            venue_ids: List[int]) -> Dict[str, Any]:
        """Activate a franchisee with assigned venues."""
        from app.models.v6_features_models import Franchisee

        if not self.db:
            return {"success": False, "error": "No database session"}

        franchisee = self.db.query(Franchisee).filter(
            Franchisee.id == franchisee_id
        ).first()

        if not franchisee:
            return {"success": False, "error": "Franchisee not found"}

        franchisee.status = FranchiseStatus.ACTIVE.value
        franchisee.venue_ids = venue_ids
        self.db.commit()

        logger.info(f"Activated franchisee {franchisee_id} with venues {venue_ids}")

        return {
            "success": True,
            "franchisee_id": franchisee_id,
            "status": franchisee.status,
            "venue_ids": venue_ids
        }

    def suspend_franchisee(self, franchisee_id: int, reason: str) -> Dict[str, Any]:
        """Suspend a franchisee."""
        from app.models.v6_features_models import Franchisee

        if not self.db:
            return {"success": False, "error": "No database session"}

        franchisee = self.db.query(Franchisee).filter(
            Franchisee.id == franchisee_id
        ).first()

        if not franchisee:
            return {"success": False, "error": "Franchisee not found"}

        franchisee.status = FranchiseStatus.SUSPENDED.value
        self.db.commit()

        logger.warning(f"Suspended franchisee {franchisee_id}: {reason}")

        return {"success": True, "franchisee_id": franchisee_id, "status": franchisee.status}

    def get_franchisee(self, franchisee_id: int) -> Optional[Dict[str, Any]]:
        """Get a franchisee by ID."""
        from app.models.v6_features_models import Franchisee

        if not self.db:
            return None

        franchisee = self.db.query(Franchisee).filter(
            Franchisee.id == franchisee_id
        ).first()

        if not franchisee:
            return None

        return {
            "id": franchisee.id,
            "company_name": franchisee.company_name,
            "contact_name": franchisee.contact_name,
            "email": franchisee.email,
            "phone": franchisee.phone,
            "address": franchisee.address,
            "city": franchisee.city,
            "country": franchisee.country,
            "territory": franchisee.territory,
            "venue_ids": franchisee.venue_ids,
            "status": franchisee.status,
            "franchise_fee": float(franchisee.franchise_fee),
            "royalty_percent": float(franchisee.royalty_percent),
            "marketing_fund_percent": float(franchisee.marketing_fund_percent),
            "agreement_start": franchisee.agreement_start.isoformat() if franchisee.agreement_start else None,
            "agreement_end": franchisee.agreement_end.isoformat() if franchisee.agreement_end else None,
            "compliance_status": franchisee.compliance_status
        }

    def get_franchisees(self, status: str = None) -> List[Dict[str, Any]]:
        """Get all franchisees, optionally filtered by status."""
        from app.models.v6_features_models import Franchisee

        if not self.db:
            return []

        query = self.db.query(Franchisee)

        if status:
            if isinstance(status, FranchiseStatus):
                status = status.value
            query = query.filter(Franchisee.status == status)

        franchisees = query.all()

        return [
            {
                "id": f.id,
                "company_name": f.company_name,
                "contact_name": f.contact_name,
                "email": f.email,
                "territory": f.territory,
                "status": f.status,
                "venue_count": len(f.venue_ids or []),
                "compliance_status": f.compliance_status
            }
            for f in franchisees
        ]

    # ==================== ROYALTY MANAGEMENT ====================

    def calculate_royalty(self, franchisee_id: int, period_start: date,
                          period_end: date, gross_sales: float) -> Dict[str, Any]:
        """Calculate and create a royalty payment."""
        from app.models.v6_features_models import Franchisee, RoyaltyPayment

        if not self.db:
            return {"success": False, "error": "No database session"}

        franchisee = self.db.query(Franchisee).filter(
            Franchisee.id == franchisee_id
        ).first()

        if not franchisee:
            return {"success": False, "error": "Franchisee not found"}

        royalty_amount = gross_sales * (float(franchisee.royalty_percent) / 100)
        marketing_amount = gross_sales * (float(franchisee.marketing_fund_percent) / 100)
        total_due = royalty_amount + marketing_amount

        payment = RoyaltyPayment(
            franchisee_id=franchisee_id,
            period_start=period_start,
            period_end=period_end,
            gross_sales=gross_sales,
            royalty_rate=franchisee.royalty_percent,
            royalty_amount=royalty_amount,
            marketing_fund_rate=franchisee.marketing_fund_percent,
            marketing_fund_amount=marketing_amount,
            total_due=total_due,
            due_date=period_end + timedelta(days=15),
            status="pending"
        )

        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)

        logger.info(f"Created royalty payment {payment.id} for franchisee {franchisee_id}")

        return {
            "success": True,
            "id": payment.id,
            "franchisee_id": franchisee_id,
            "period": f"{period_start} to {period_end}",
            "gross_sales": gross_sales,
            "royalty_amount": royalty_amount,
            "marketing_fund_amount": marketing_amount,
            "total_due": total_due,
            "due_date": payment.due_date.isoformat()
        }

    def record_payment(self, payment_id: int, amount: float) -> Dict[str, Any]:
        """Record a royalty payment."""
        from app.models.v6_features_models import RoyaltyPayment

        if not self.db:
            return {"success": False, "error": "No database session"}

        payment = self.db.query(RoyaltyPayment).filter(
            RoyaltyPayment.id == payment_id
        ).first()

        if not payment:
            return {"success": False, "error": "Payment not found"}

        payment.paid_amount = float(payment.paid_amount or 0) + amount

        if payment.paid_amount >= float(payment.total_due):
            payment.status = "paid"
            payment.paid_at = datetime.now(timezone.utc)

        self.db.commit()

        logger.info(f"Recorded payment of {amount} for payment {payment_id}")

        return {
            "success": True,
            "payment_id": payment_id,
            "paid_amount": float(payment.paid_amount),
            "total_due": float(payment.total_due),
            "status": payment.status
        }

    def get_royalty_payments(self, franchisee_id: int = None,
                              status: str = None) -> List[Dict[str, Any]]:
        """Get royalty payments."""
        from app.models.v6_features_models import RoyaltyPayment

        if not self.db:
            return []

        query = self.db.query(RoyaltyPayment)

        if franchisee_id:
            query = query.filter(RoyaltyPayment.franchisee_id == franchisee_id)
        if status:
            query = query.filter(RoyaltyPayment.status == status)

        payments = query.order_by(RoyaltyPayment.due_date.desc()).all()

        return [
            {
                "id": p.id,
                "franchisee_id": p.franchisee_id,
                "period_start": p.period_start.isoformat(),
                "period_end": p.period_end.isoformat(),
                "gross_sales": float(p.gross_sales),
                "royalty_amount": float(p.royalty_amount),
                "marketing_fund_amount": float(p.marketing_fund_amount),
                "total_due": float(p.total_due),
                "paid_amount": float(p.paid_amount),
                "status": p.status,
                "due_date": p.due_date.isoformat(),
                "paid_at": p.paid_at.isoformat() if p.paid_at else None
            }
            for p in payments
        ]

    def get_overdue_payments(self) -> List[Dict[str, Any]]:
        """Get overdue royalty payments."""
        from app.models.v6_features_models import RoyaltyPayment

        if not self.db:
            return []

        today = date.today()

        payments = self.db.query(RoyaltyPayment).filter(
            RoyaltyPayment.status == "pending",
            RoyaltyPayment.due_date < today
        ).all()

        # Update status to overdue
        for p in payments:
            p.status = "overdue"

        self.db.commit()

        return [
            {
                "id": p.id,
                "franchisee_id": p.franchisee_id,
                "total_due": float(p.total_due),
                "paid_amount": float(p.paid_amount),
                "due_date": p.due_date.isoformat(),
                "days_overdue": (today - p.due_date).days
            }
            for p in payments
        ]

    # ==================== COMPLIANCE AUDITS ====================

    def create_audit(self, franchisee_id: int, venue_id: int,
                     auditor_name: str) -> Dict[str, Any]:
        """Create a new compliance audit."""
        from app.models.v6_features_models import FranchiseComplianceAudit

        if not self.db:
            return {"success": False, "error": "No database session"}

        audit = FranchiseComplianceAudit(
            franchisee_id=franchisee_id,
            venue_id=venue_id,
            audit_date=date.today(),
            auditor_name=auditor_name,
            overall_score=0,
            passed=False
        )

        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)

        logger.info(f"Created audit {audit.id} for franchisee {franchisee_id}")

        return {
            "success": True,
            "id": audit.id,
            "franchisee_id": franchisee_id,
            "venue_id": venue_id,
            "audit_date": audit.audit_date.isoformat(),
            "auditor_name": auditor_name
        }

    def complete_audit(self, audit_id: int, categories: Dict[str, float],
                       findings: List[Dict],
                       corrective_actions: List[str]) -> Dict[str, Any]:
        """Complete an audit with results."""
        from app.models.v6_features_models import FranchiseComplianceAudit, Franchisee

        if not self.db:
            return {"success": False, "error": "No database session"}

        audit = self.db.query(FranchiseComplianceAudit).filter(
            FranchiseComplianceAudit.id == audit_id
        ).first()

        if not audit:
            return {"success": False, "error": "Audit not found"}

        audit.categories = categories
        audit.overall_score = sum(categories.values()) / len(categories) if categories else 0
        audit.passed = audit.overall_score >= 80
        audit.findings = findings
        audit.corrective_actions = corrective_actions
        audit.next_audit_date = date.today() + timedelta(days=90 if audit.passed else 30)

        # Update franchisee compliance status
        franchisee = self.db.query(Franchisee).filter(
            Franchisee.id == audit.franchisee_id
        ).first()

        if franchisee:
            if audit.overall_score >= 90:
                franchisee.compliance_status = ComplianceStatus.COMPLIANT.value
            elif audit.overall_score >= 70:
                franchisee.compliance_status = ComplianceStatus.WARNING.value
            else:
                franchisee.compliance_status = ComplianceStatus.NON_COMPLIANT.value

        self.db.commit()

        logger.info(f"Completed audit {audit_id} with score {audit.overall_score}")

        return {
            "success": True,
            "audit_id": audit_id,
            "overall_score": float(audit.overall_score),
            "passed": audit.passed,
            "next_audit_date": audit.next_audit_date.isoformat()
        }

    def get_audits(self, franchisee_id: int = None,
                   start: date = None, end: date = None) -> List[Dict[str, Any]]:
        """Get compliance audits."""
        from app.models.v6_features_models import FranchiseComplianceAudit

        if not self.db:
            return []

        query = self.db.query(FranchiseComplianceAudit)

        if franchisee_id:
            query = query.filter(FranchiseComplianceAudit.franchisee_id == franchisee_id)
        if start:
            query = query.filter(FranchiseComplianceAudit.audit_date >= start)
        if end:
            query = query.filter(FranchiseComplianceAudit.audit_date <= end)

        audits = query.order_by(FranchiseComplianceAudit.audit_date.desc()).all()

        return [
            {
                "id": a.id,
                "franchisee_id": a.franchisee_id,
                "venue_id": a.venue_id,
                "audit_date": a.audit_date.isoformat(),
                "auditor_name": a.auditor_name,
                "categories": a.categories,
                "overall_score": float(a.overall_score),
                "passed": a.passed,
                "findings": a.findings,
                "corrective_actions": a.corrective_actions,
                "next_audit_date": a.next_audit_date.isoformat() if a.next_audit_date else None
            }
            for a in audits
        ]

    # ==================== TERRITORY MANAGEMENT ====================

    def create_territory(self, name: str, region: str, **kwargs) -> Dict[str, Any]:
        """Create a franchise territory."""
        from app.models.v6_features_models import FranchiseTerritory

        if not self.db:
            return {"success": False, "error": "No database session"}

        territory = FranchiseTerritory(
            name=name,
            region=region,
            city=kwargs.get('city'),
            postal_codes=kwargs.get('postal_codes', []),
            population=kwargs.get('population'),
            status="available"
        )

        self.db.add(territory)
        self.db.commit()
        self.db.refresh(territory)

        logger.info(f"Created territory {territory.id}: {name}")

        return {
            "success": True,
            "id": territory.id,
            "name": territory.name,
            "region": territory.region,
            "status": territory.status
        }

    def assign_territory(self, territory_id: int, franchisee_id: int) -> Dict[str, Any]:
        """Assign a territory to a franchisee."""
        from app.models.v6_features_models import FranchiseTerritory

        if not self.db:
            return {"success": False, "error": "No database session"}

        territory = self.db.query(FranchiseTerritory).filter(
            FranchiseTerritory.id == territory_id
        ).first()

        if not territory:
            return {"success": False, "error": "Territory not found"}

        territory.franchisee_id = franchisee_id
        territory.status = "assigned"
        self.db.commit()

        logger.info(f"Assigned territory {territory_id} to franchisee {franchisee_id}")

        return {
            "success": True,
            "territory_id": territory_id,
            "franchisee_id": franchisee_id,
            "status": territory.status
        }

    def get_territories(self, status: str = None) -> List[Dict[str, Any]]:
        """Get territories."""
        from app.models.v6_features_models import FranchiseTerritory

        if not self.db:
            return []

        query = self.db.query(FranchiseTerritory)

        if status:
            query = query.filter(FranchiseTerritory.status == status)

        territories = query.all()

        return [
            {
                "id": t.id,
                "name": t.name,
                "region": t.region,
                "city": t.city,
                "postal_codes": t.postal_codes,
                "population": t.population,
                "franchisee_id": t.franchisee_id,
                "status": t.status
            }
            for t in territories
        ]

    def get_available_territories(self) -> List[Dict[str, Any]]:
        """Get available territories."""
        return self.get_territories("available")

    # ==================== ANALYTICS ====================

    def get_franchise_performance(self, franchisee_id: int,
                                    start: date, end: date) -> Dict[str, Any]:
        """Get performance metrics for a franchisee."""
        from app.models.v6_features_models import RoyaltyPayment, FranchiseComplianceAudit

        if not self.db:
            return {}

        payments = self.db.query(RoyaltyPayment).filter(
            RoyaltyPayment.franchisee_id == franchisee_id,
            RoyaltyPayment.period_start >= start,
            RoyaltyPayment.period_start <= end
        ).all()

        audits = self.db.query(FranchiseComplianceAudit).filter(
            FranchiseComplianceAudit.franchisee_id == franchisee_id,
            FranchiseComplianceAudit.audit_date >= start,
            FranchiseComplianceAudit.audit_date <= end
        ).all()

        return {
            "franchisee_id": franchisee_id,
            "period": f"{start} to {end}",
            "total_sales": sum(float(p.gross_sales) for p in payments),
            "total_royalties_due": sum(float(p.total_due) for p in payments),
            "total_royalties_paid": sum(float(p.paid_amount) for p in payments),
            "outstanding_balance": sum(float(p.total_due) - float(p.paid_amount)
                                       for p in payments if p.status != "paid"),
            "avg_audit_score": sum(float(a.overall_score) for a in audits) / len(audits) if audits else 0,
            "audits_passed": len([a for a in audits if a.passed]),
            "audits_failed": len([a for a in audits if not a.passed])
        }

    def get_network_overview(self) -> Dict[str, Any]:
        """Get franchise network overview."""
        from app.models.v6_features_models import Franchisee, FranchiseTerritory

        if not self.db:
            return {}

        franchisees = self.db.query(Franchisee).all()
        territories = self.db.query(FranchiseTerritory).all()

        active = [f for f in franchisees if f.status == FranchiseStatus.ACTIVE.value]
        overdue = self.get_overdue_payments()

        return {
            "total_franchisees": len(franchisees),
            "active_franchisees": len(active),
            "prospects": len([f for f in franchisees if f.status == FranchiseStatus.PROSPECT.value]),
            "suspended": len([f for f in franchisees if f.status == FranchiseStatus.SUSPENDED.value]),
            "total_venues": sum(len(f.venue_ids or []) for f in active),
            "territories_available": len([t for t in territories if t.status == "available"]),
            "territories_assigned": len([t for t in territories if t.status == "assigned"]),
            "overdue_payments": len(overdue),
            "overdue_amount": sum(float(p.get('total_due', 0)) - float(p.get('paid_amount', 0)) for p in overdue),
            "compliance_issues": len([f for f in active
                                      if f.compliance_status == ComplianceStatus.NON_COMPLIANT.value])
        }

    def get_dashboard(self) -> Dict[str, Any]:
        """Get franchise management dashboard."""
        overview = self.get_network_overview()

        # Get recent audits
        audits = self.get_audits()[:5]

        # Get upcoming payments
        from app.models.v6_features_models import RoyaltyPayment

        if self.db:
            upcoming = self.db.query(RoyaltyPayment).filter(
                RoyaltyPayment.status == "pending",
                RoyaltyPayment.due_date >= date.today()
            ).order_by(RoyaltyPayment.due_date.asc()).limit(5).all()

            upcoming_payments = [
                {
                    "id": p.id,
                    "franchisee_id": p.franchisee_id,
                    "total_due": float(p.total_due),
                    "due_date": p.due_date.isoformat()
                }
                for p in upcoming
            ]
        else:
            upcoming_payments = []

        return {
            **overview,
            "recent_audits": audits,
            "upcoming_payments": upcoming_payments
        }
