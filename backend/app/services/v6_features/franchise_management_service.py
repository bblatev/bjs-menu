"""
Franchise Management Service Stub
==================================
Service stub for V6 franchise management features including
franchisee registration, royalty calculations, and compliance audits.
"""

from datetime import date
from enum import Enum


class FranchiseStatus(Enum):
    """Franchise application status."""
    pending = "pending"
    approved = "approved"
    active = "active"
    suspended = "suspended"
    terminated = "terminated"


class FranchiseResult:
    """Simple data object for franchise results."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class FranchiseManagementService:
    """Service for franchise management operations."""

    def __init__(self, db=None):
        self.db = db

    def register_franchisee(self, company_name: str, contact_name: str, email: str,
                            phone: str, territory: str, address: str = "",
                            city: str = "") -> FranchiseResult:
        """Register a new franchisee."""
        return FranchiseResult(
            id=f"FR-1",
            company_name=company_name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            territory=territory,
            status="pending",
        )

    def get_franchisees(self, status: FranchiseStatus = None) -> list:
        """Get all franchisees, optionally filtered by status."""
        return []

    def approve_franchisee(self, franchisee_id: str, agreement_years: int = 10) -> FranchiseResult:
        """Approve a franchisee application."""
        return FranchiseResult(
            id=franchisee_id,
            status="approved",
        )

    def calculate_royalty(self, franchisee_id: str, period_start: date,
                          period_end: date, gross_sales: float) -> FranchiseResult:
        """Calculate royalty payment for a franchisee."""
        royalty_amount = round(gross_sales * 0.06, 2)
        return FranchiseResult(
            id=f"ROY-{franchisee_id}-1",
            franchisee_id=franchisee_id,
            period_start=str(period_start),
            period_end=str(period_end),
            gross_sales=gross_sales,
            royalty_amount=royalty_amount,
        )

    def get_franchise_performance(self, franchisee_id: str, start: date, end: date) -> dict:
        """Get performance metrics for a franchisee."""
        return {
            "franchisee_id": franchisee_id,
            "revenue": 0.0,
            "orders": 0,
            "avg_ticket": 0.0,
        }

    def create_audit(self, franchisee_id: str, venue_id: int, auditor_name: str) -> FranchiseResult:
        """Create a compliance audit for a franchisee."""
        return FranchiseResult(
            id=f"AUDIT-{franchisee_id}-1",
            franchisee_id=franchisee_id,
            venue_id=venue_id,
            auditor_name=auditor_name,
            status="scheduled",
        )

    def get_network_overview(self) -> dict:
        """Get franchise network overview."""
        return {
            "total_franchisees": 0,
            "active": 0,
            "pending": 0,
            "total_locations": 0,
            "network_revenue": 0.0,
        }
