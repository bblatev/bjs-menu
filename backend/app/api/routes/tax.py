"""Tax management API routes."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.operations import TaxFiling as TaxFilingModel
from app.core.rate_limit import limiter

router = APIRouter()


# --------------- Pydantic Schemas ---------------


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


# --------------- Helpers ---------------


def _filing_to_schema(filing: TaxFilingModel) -> TaxFiling:
    """Convert a TaxFiling DB model to the response schema."""
    return TaxFiling(
        id=str(filing.id),
        period=filing.period or "",
        year=filing.year or 0,
        type="vat",
        gross_sales=float(filing.total_revenue or 0),
        taxable_amount=float(filing.total_revenue or 0),
        tax_due=float(filing.total_tax or 0),
        status=filing.status or "pending",
        due_date=filing.due_date.isoformat() if filing.due_date else "",
        filed_date=filing.filed_at.isoformat() if filing.filed_at else None,
    )


# --------------- Endpoints ---------------


@router.get("/filings")
@limiter.limit("60/minute")
async def get_tax_filings(request: Request, db: DbSession, year: int = Query(2026)):
    """Get tax filings for a year."""
    filings = db.query(TaxFilingModel).filter(TaxFilingModel.year == year).all()
    return [_filing_to_schema(f) for f in filings]


@router.get("/summary")
@limiter.limit("60/minute")
async def get_tax_summary(request: Request, db: DbSession):
    """Get tax summary."""
    # Aggregate from all filings to build the summary
    result = db.query(
        func.coalesce(func.sum(TaxFilingModel.total_revenue), 0).label("total_revenue"),
        func.coalesce(func.sum(TaxFilingModel.total_tax), 0).label("total_tax"),
    ).first()

    total_revenue = float(result.total_revenue) if result else 0.0
    total_tax = float(result.total_tax) if result else 0.0

    # Get the next upcoming filing by due_date for filings that are still pending
    next_filing = (
        db.query(TaxFilingModel)
        .filter(TaxFilingModel.status == "pending")
        .order_by(TaxFilingModel.due_date.asc())
        .first()
    )
    next_filing_date = next_filing.due_date.isoformat() if next_filing and next_filing.due_date else ""

    # Compute paid filings total for vat_paid
    paid_result = db.query(
        func.coalesce(func.sum(TaxFilingModel.total_tax), 0).label("paid_tax"),
    ).filter(TaxFilingModel.status == "paid").first()

    total_paid = float(paid_result.paid_tax) if paid_result else 0.0

    return TaxSummary(
        total_vat_collected=total_revenue,
        total_vat_paid=total_paid,
        net_vat_liability=total_tax - total_paid,
        income_tax_due=total_tax,
        next_filing_date=next_filing_date,
    )


@router.post("/filings/{filing_id}/file")
@limiter.limit("30/minute")
async def file_tax_return(request: Request, filing_id: str, db: DbSession):
    """Mark a tax filing as filed."""
    try:
        numeric_id = int(filing_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid filing ID: {filing_id}. Must be a numeric value.")
    filing = db.query(TaxFilingModel).filter(TaxFilingModel.id == numeric_id).first()
    if not filing:
        raise HTTPException(status_code=404, detail=f"Tax filing {filing_id} not found")

    filing.status = "filed"
    filing.filed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(filing)

    return {"success": True, "message": f"Tax filing {filing_id} marked as filed"}
