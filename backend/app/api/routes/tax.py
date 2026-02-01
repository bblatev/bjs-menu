"""Tax management API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class TaxFiling(BaseModel):
    id: str
    period: str
    year: int
    type: str  # vat, income, corporate
    gross_sales: float
    taxable_amount: float
    tax_due: float
    status: str  # pending, filed, paid
    due_date: str
    filed_date: Optional[str] = None


class TaxSummary(BaseModel):
    total_vat_collected: float
    total_vat_paid: float
    net_vat_liability: float
    income_tax_due: float
    next_filing_date: str


@router.get("/filings")
async def get_tax_filings(year: int = Query(2026)):
    """Get tax filings for a year."""
    return [
        TaxFiling(id="1", period="January", year=year, type="vat", gross_sales=85000.00, taxable_amount=70833.33, tax_due=14166.67, status="paid", due_date="2026-02-14", filed_date="2026-02-10"),
        TaxFiling(id="2", period="February", year=year, type="vat", gross_sales=0.00, taxable_amount=0.00, tax_due=0.00, status="pending", due_date="2026-03-14"),
        TaxFiling(id="3", period="Q4 2025", year=2025, type="corporate", gross_sales=320000.00, taxable_amount=48000.00, tax_due=4800.00, status="filed", due_date="2026-03-31", filed_date="2026-01-15"),
    ]


@router.get("/summary")
async def get_tax_summary():
    """Get tax summary."""
    return TaxSummary(
        total_vat_collected=42500.00,
        total_vat_paid=28000.00,
        net_vat_liability=14500.00,
        income_tax_due=4800.00,
        next_filing_date="2026-02-14"
    )


@router.post("/filings/{filing_id}/file")
async def file_tax_return(filing_id: str):
    """Mark a tax filing as filed."""
    return {"success": True, "message": f"Tax filing {filing_id} marked as filed"}
