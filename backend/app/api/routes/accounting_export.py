"""
Bulgarian Accounting Export API Routes (Gap 2)

Provides export endpoints for AtomS3 and other Bulgarian accounting software:
- Sales journal export
- Purchase journal export
- GL chart of accounts
- VAT declaration data
"""

from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO

from app.db.session import DbSession
from app.models.restaurant import Check, CheckItem, CheckPayment
from app.models.invoice import Invoice, InvoiceLine
from app.services.atoms3_export_service import (
    AtomS3ExportService,
    ExportFormat,
    SalesEntry,
    PurchaseEntry,
    DocumentType,
    VATCategory,
)

router = APIRouter()


# ============== Endpoints ==============

@router.get("/formats")
def list_export_formats():
    """List available export formats."""
    return {
        "formats": [
            {
                "id": "atoms3",
                "name": "AtomS3 (Microinvest)",
                "description": "Export for AtomS3 accounting software",
                "file_formats": ["csv", "xml", "json"],
            },
            {
                "id": "excel",
                "name": "Microsoft Excel",
                "description": "Export to Excel spreadsheet",
                "file_formats": ["xlsx"],
            },
            {
                "id": "nap",
                "name": "НАП / NAP",
                "description": "Bulgarian National Revenue Agency format",
                "file_formats": ["xml"],
            },
        ],
        "default": "atoms3",
    }


@router.get("/gl-accounts")
def get_gl_chart_of_accounts():
    """Get GL chart of accounts for Bulgarian accounting."""
    accounts = []
    for key, account in AtomS3ExportService.GL_ACCOUNTS.items():
        accounts.append({
            "key": key,
            "code": account.code,
            "name_bg": account.name_bg,
            "name_en": account.name_en,
            "account_type": account.account_type,
        })

    return {
        "accounts": accounts,
        "description": "Bulgarian chart of accounts mapping for POS transactions",
    }


@router.get("/gl-accounts/download")
def download_gl_chart_of_accounts():
    """Download GL chart of accounts as CSV."""
    csv_content = AtomS3ExportService.export_gl_chart_of_accounts()

    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=gl_chart_of_accounts.csv"
        },
    )


@router.get("/sales-journal")
def export_sales_journal(
    db: DbSession,
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    format: str = Query("csv", description="Export format: csv, xml, json"),
    location_id: Optional[int] = Query(None),
):
    """
    Export sales journal for AtomS3.

    Exports all closed checks within the date range in AtomS3-compatible format.
    """
    from datetime import timedelta
    if not start_date:
        start_date = (datetime.now().date() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().date().strftime("%Y-%m-%d")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    try:
        export_format = ExportFormat(format.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid format: {format}")

    # Query closed checks
    query = db.query(Check).filter(
        Check.status == "closed",
        Check.closed_at >= datetime.combine(start, datetime.min.time()),
        Check.closed_at <= datetime.combine(end, datetime.max.time()),
    )
    if location_id:
        query = query.filter(Check.location_id == location_id)

    checks = query.all()

    # Convert to SalesEntry format
    entries = []
    for check in checks:
        # Calculate VAT (assuming 20% standard rate)
        gross = float(check.total or 0)
        net = gross / 1.20
        vat = gross - net

        # Determine payment method
        payments = check.payments or []
        payment_method = "Каса"  # Default to cash
        gl_debit = "501"  # Cash account
        if payments:
            if any(p.payment_type == "credit" for p in payments):
                payment_method = "Карта"
                gl_debit = "411"  # Card receivables
            elif any(p.payment_type == "card" for p in payments):
                payment_method = "Карта"
                gl_debit = "411"

        entry = SalesEntry(
            document_number=f"R{check.id:08d}",
            document_date=check.closed_at.date() if check.closed_at else date.today(),
            document_type=DocumentType.RECEIPT,
            customer_name="Клиент" if not check.notes else check.notes[:50],
            customer_eik=None,
            customer_vat=None,
            description=f"Маса {check.table_id or 'N/A'}, {check.guest_count or 1} гости",
            net_amount=Decimal(str(net)),
            vat_amount=Decimal(str(vat)),
            gross_amount=Decimal(str(gross)),
            vat_category=VATCategory.VAT_20,
            payment_method=payment_method,
            gl_account_debit=gl_debit,
            gl_account_credit="702",  # Sales revenue
            location_id=check.location_id,
            operator_id=str(check.server_id) if check.server_id else None,
        )
        entries.append(entry)

    # Generate export
    content = AtomS3ExportService.export_sales_journal(
        entries=entries,
        format=export_format,
        period_start=start,
        period_end=end,
    )

    # Determine content type and filename
    content_types = {
        ExportFormat.CSV: "text/csv; charset=utf-8",
        ExportFormat.XML: "application/xml; charset=utf-8",
        ExportFormat.JSON: "application/json; charset=utf-8",
    }
    extensions = {
        ExportFormat.CSV: "csv",
        ExportFormat.XML: "xml",
        ExportFormat.JSON: "json",
    }

    filename = f"sales_journal_{start_date}_{end_date}.{extensions[export_format]}"

    return Response(
        content=content,
        media_type=content_types[export_format],
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@router.get("/sales-journal/preview")
def preview_sales_journal(
    db: DbSession,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    location_id: Optional[int] = Query(None),
    limit: int = Query(10),
):
    """Preview sales journal data before export."""
    from datetime import timedelta
    if not start_date:
        start_date = (datetime.now().date() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().date().strftime("%Y-%m-%d")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    query = db.query(Check).filter(
        Check.status == "closed",
        Check.closed_at >= datetime.combine(start, datetime.min.time()),
        Check.closed_at <= datetime.combine(end, datetime.max.time()),
    )
    if location_id:
        query = query.filter(Check.location_id == location_id)

    total_count = query.count()
    checks = query.limit(limit).all()

    # Calculate totals
    all_checks = query.all()
    total_gross = sum(float(c.total or 0) for c in all_checks)
    total_net = total_gross / 1.20
    total_vat = total_gross - total_net

    preview_entries = []
    for check in checks:
        gross = float(check.total or 0)
        net = gross / 1.20
        vat = gross - net

        preview_entries.append({
            "document_number": f"R{check.id:08d}",
            "document_date": check.closed_at.strftime("%d.%m.%Y") if check.closed_at else "",
            "description": f"Маса {check.table_id or 'N/A'}",
            "net_amount": round(net, 2),
            "vat_amount": round(vat, 2),
            "gross_amount": round(gross, 2),
        })

    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "summary": {
            "total_documents": total_count,
            "total_net": round(total_net, 2),
            "total_vat": round(total_vat, 2),
            "total_gross": round(total_gross, 2),
        },
        "preview_entries": preview_entries,
        "showing": len(preview_entries),
    }


@router.get("/purchase-journal")
def export_purchase_journal(
    db: DbSession,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("csv"),
    location_id: Optional[int] = Query(None),
):
    """
    Export purchase journal for AtomS3.

    Exports all invoices within the date range.
    """
    from datetime import timedelta
    if not start_date:
        start_date = (datetime.now().date() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().date().strftime("%Y-%m-%d")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    try:
        export_format = ExportFormat(format.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid format: {format}")

    # Query invoices
    query = db.query(Invoice).filter(
        Invoice.invoice_date >= start,
        Invoice.invoice_date <= end,
    )
    if location_id:
        query = query.filter(Invoice.location_id == location_id)

    invoices = query.all()

    # Convert to PurchaseEntry format
    entries = []
    for inv in invoices:
        gross = float(inv.total_amount or 0)
        net = gross / 1.20
        vat = gross - net

        entry = PurchaseEntry(
            document_number=f"P{inv.id:08d}",
            document_date=inv.created_at.date() if inv.created_at else date.today(),
            supplier_invoice_number=inv.invoice_number or "",
            supplier_invoice_date=inv.invoice_date or date.today(),
            supplier_name=getattr(inv, 'supplier_name', None) or "Доставчик",
            supplier_eik=None,
            supplier_vat=None,
            description=inv.notes or f"Фактура {inv.invoice_number}",
            net_amount=Decimal(str(net)),
            vat_amount=Decimal(str(vat)),
            gross_amount=Decimal(str(gross)),
            vat_category=VATCategory.VAT_20,
            gl_account_debit="302",  # Inventory
            gl_account_credit="401",  # Suppliers payable
        )
        entries.append(entry)

    content = AtomS3ExportService.export_purchase_journal(entries, export_format)

    content_types = {
        ExportFormat.CSV: "text/csv; charset=utf-8",
        ExportFormat.JSON: "application/json; charset=utf-8",
    }
    extensions = {
        ExportFormat.CSV: "csv",
        ExportFormat.JSON: "json",
    }

    filename = f"purchase_journal_{start_date}_{end_date}.{extensions.get(export_format, 'csv')}"

    return Response(
        content=content,
        media_type=content_types.get(export_format, "text/csv"),
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@router.get("/vat-declaration")
def get_vat_declaration_data(
    db: DbSession,
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020, le=2100),
    location_id: Optional[int] = Query(None),
):
    """
    Get VAT declaration data for a specific month.

    Returns structured data for Bulgarian VAT declaration (справка-декларация по ЗДДС).
    """
    # Calculate date range for the month
    if not month:
        month = datetime.now().month
    if not year:
        year = datetime.now().year
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    # Get sales
    sales_query = db.query(Check).filter(
        Check.status == "closed",
        Check.closed_at >= datetime.combine(start, datetime.min.time()),
        Check.closed_at < datetime.combine(end, datetime.min.time()),
    )
    if location_id:
        sales_query = sales_query.filter(Check.location_id == location_id)

    checks = sales_query.all()

    sales_entries = []
    for check in checks:
        gross = float(check.total or 0)
        net = gross / 1.20
        vat = gross - net

        sales_entries.append(SalesEntry(
            document_number=f"R{check.id:08d}",
            document_date=check.closed_at.date() if check.closed_at else date.today(),
            document_type=DocumentType.RECEIPT,
            customer_name="Клиент",
            customer_eik=None,
            customer_vat=None,
            description="",
            net_amount=Decimal(str(net)),
            vat_amount=Decimal(str(vat)),
            gross_amount=Decimal(str(gross)),
            vat_category=VATCategory.VAT_20,
            payment_method="",
            gl_account_debit="",
            gl_account_credit="",
        ))

    # Get purchases
    purchase_query = db.query(Invoice).filter(
        Invoice.invoice_date >= start,
        Invoice.invoice_date < end,
    )
    if location_id:
        purchase_query = purchase_query.filter(Invoice.location_id == location_id)

    invoices = purchase_query.all()

    purchase_entries = []
    for inv in invoices:
        gross = float(inv.total_amount or 0)
        net = gross / 1.20
        vat = gross - net

        purchase_entries.append(PurchaseEntry(
            document_number=f"P{inv.id:08d}",
            document_date=inv.created_at.date() if inv.created_at else date.today(),
            supplier_invoice_number=inv.invoice_number or "",
            supplier_invoice_date=inv.invoice_date or date.today(),
            supplier_name=getattr(inv, 'supplier_name', None) or "",
            supplier_eik=None,
            supplier_vat=None,
            description="",
            net_amount=Decimal(str(net)),
            vat_amount=Decimal(str(vat)),
            gross_amount=Decimal(str(gross)),
            vat_category=VATCategory.VAT_20,
            gl_account_debit="",
            gl_account_credit="",
        ))

    # Generate VAT declaration data
    vat_data = AtomS3ExportService.export_vat_declaration_data(
        sales_entries=sales_entries,
        purchase_entries=purchase_entries,
        period_month=month,
        period_year=year,
    )

    return vat_data


@router.get("/atoms3/settings")
def get_atoms3_settings():
    """Get AtomS3 export settings and mappings."""
    return {
        "gl_account_mappings": {
            key: {
                "code": acc.code,
                "name_bg": acc.name_bg,
                "name_en": acc.name_en,
            }
            for key, acc in AtomS3ExportService.GL_ACCOUNTS.items()
        },
        "vat_categories": [
            {"code": "20", "name": "Стандартна 20%", "description": "Standard VAT rate"},
            {"code": "9", "name": "Намалена 9%", "description": "Reduced rate for tourism"},
            {"code": "0", "name": "Нулева", "description": "Zero rate"},
            {"code": "N", "name": "Освободена", "description": "VAT exempt"},
        ],
        "document_types": [
            {"code": "invoice", "name_bg": "Фактура", "name_en": "Invoice"},
            {"code": "credit_note", "name_bg": "Кредитно известие", "name_en": "Credit Note"},
            {"code": "debit_note", "name_bg": "Дебитно известие", "name_en": "Debit Note"},
            {"code": "receipt", "name_bg": "Касова бележка", "name_en": "Receipt"},
            {"code": "protocol", "name_bg": "Протокол", "name_en": "Protocol"},
        ],
        "export_encoding": "UTF-8",
        "date_format": "DD.MM.YYYY",
        "decimal_separator": ".",
        "field_separator": ";",
    }
