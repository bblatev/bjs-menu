"""
AtomS3 Bulgarian Accounting Export Service (Gap 2)

This service provides export functionality to AtomS3 accounting software format.
AtomS3 (by Microinvest) is one of the most popular accounting systems in Bulgaria.

Export formats supported:
- Sales journal export (XML/CSV)
- Purchase journal export (XML/CSV)
- GL (General Ledger) postings
- Customer/Supplier master data
- Inventory movements

Bulgarian accounting requirements:
- Dates in DD.MM.YYYY format
- Amounts with 2 decimal places
- Bulgarian character encoding (Windows-1251 or UTF-8)
- VAT breakdown by rate category
"""

import os
import csv
import json
from io import StringIO, BytesIO
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import xml.etree.ElementTree as ET


class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    XML = "xml"
    JSON = "json"


class DocumentType(str, Enum):
    """Bulgarian accounting document types."""
    INVOICE = "invoice"           # Фактура
    CREDIT_NOTE = "credit_note"   # Кредитно известие
    DEBIT_NOTE = "debit_note"     # Дебитно известие
    RECEIPT = "receipt"           # Касова бележка
    PROTOCOL = "protocol"         # Протокол


class VATCategory(str, Enum):
    """Bulgarian VAT categories for accounting."""
    VAT_20 = "20"      # Standard 20%
    VAT_9 = "9"        # Reduced 9% (tourism)
    VAT_0 = "0"        # Zero rate
    VAT_EXEMPT = "N"   # Exempt


@dataclass
class GLAccount:
    """General Ledger account mapping."""
    code: str
    name_bg: str
    name_en: str
    account_type: str  # asset, liability, equity, revenue, expense


@dataclass
class SalesEntry:
    """Sales journal entry for AtomS3 export."""
    document_number: str
    document_date: date
    document_type: DocumentType
    customer_name: str
    customer_eik: Optional[str]  # Bulgarian tax ID (EIK/BULSTAT)
    customer_vat: Optional[str]  # VAT number
    description: str
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    vat_category: VATCategory
    payment_method: str
    gl_account_debit: str
    gl_account_credit: str
    location_id: Optional[int] = None
    operator_id: Optional[str] = None


@dataclass
class PurchaseEntry:
    """Purchase journal entry for AtomS3 export."""
    document_number: str
    document_date: date
    supplier_invoice_number: str
    supplier_invoice_date: date
    supplier_name: str
    supplier_eik: Optional[str]
    supplier_vat: Optional[str]
    description: str
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    vat_category: VATCategory
    gl_account_debit: str
    gl_account_credit: str


class AtomS3ExportService:
    """Service for exporting data to AtomS3 accounting format."""

    # Default GL account mappings for Bulgarian chart of accounts
    GL_ACCOUNTS = {
        # Revenue accounts (група 70)
        "sales_food": GLAccount("702", "Приходи от продажба на храни", "Food Sales Revenue", "revenue"),
        "sales_beverage": GLAccount("702", "Приходи от продажба на напитки", "Beverage Sales Revenue", "revenue"),
        "sales_service": GLAccount("703", "Приходи от услуги", "Service Revenue", "revenue"),

        # Asset accounts
        "cash": GLAccount("501", "Каса в лева", "Cash BGN", "asset"),
        "bank": GLAccount("503", "Разплащателна сметка в лева", "Bank Account BGN", "asset"),
        "card_receivable": GLAccount("411", "Вземания по разчети с клиенти", "Card Receivables", "asset"),
        "inventory_food": GLAccount("302", "Материали - храни", "Food Inventory", "asset"),
        "inventory_beverage": GLAccount("302", "Материали - напитки", "Beverage Inventory", "asset"),

        # Liability accounts
        "vat_payable": GLAccount("453", "Разчети за ДДС", "VAT Payable", "liability"),
        "suppliers_payable": GLAccount("401", "Доставчици", "Accounts Payable", "liability"),

        # Expense accounts
        "cost_of_goods": GLAccount("601", "Разходи за материали", "Cost of Goods Sold", "expense"),
        "labor_expense": GLAccount("604", "Разходи за заплати", "Labor Expense", "expense"),
    }

    @classmethod
    def format_bulgarian_date(cls, d: date) -> str:
        """Format date in Bulgarian format DD.MM.YYYY."""
        return d.strftime("%d.%m.%Y")

    @classmethod
    def format_amount(cls, amount: Decimal) -> str:
        """Format amount with 2 decimal places."""
        return f"{float(amount):.2f}"

    @classmethod
    def export_sales_journal(
        cls,
        entries: List[SalesEntry],
        format: ExportFormat = ExportFormat.CSV,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> str:
        """
        Export sales journal to AtomS3 format.
        """
        if format == ExportFormat.CSV:
            return cls._export_sales_csv(entries)
        elif format == ExportFormat.XML:
            return cls._export_sales_xml(entries, period_start, period_end)
        elif format == ExportFormat.JSON:
            return cls._export_sales_json(entries)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @classmethod
    def _export_sales_csv(cls, entries: List[SalesEntry]) -> str:
        """Export sales to CSV format compatible with AtomS3."""
        output = StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        # Header row (Bulgarian column names for AtomS3)
        headers = [
            "Номер документ",      # Document number
            "Дата",                # Date
            "Тип документ",        # Document type
            "Клиент",              # Customer name
            "ЕИК/БУЛСТАТ",         # Tax ID
            "ДДС номер",           # VAT number
            "Описание",            # Description
            "Нето",                # Net amount
            "ДДС",                 # VAT amount
            "Бруто",               # Gross amount
            "ДДС категория",       # VAT category
            "Начин плащане",       # Payment method
            "Дебит сметка",        # Debit GL account
            "Кредит сметка",       # Credit GL account
        ]
        writer.writerow(headers)

        # Data rows
        for entry in entries:
            row = [
                entry.document_number,
                cls.format_bulgarian_date(entry.document_date),
                entry.document_type.value,
                entry.customer_name,
                entry.customer_eik or "",
                entry.customer_vat or "",
                entry.description,
                cls.format_amount(entry.net_amount),
                cls.format_amount(entry.vat_amount),
                cls.format_amount(entry.gross_amount),
                entry.vat_category.value,
                entry.payment_method,
                entry.gl_account_debit,
                entry.gl_account_credit,
            ]
            writer.writerow(row)

        return output.getvalue()

    @classmethod
    def _export_sales_xml(
        cls,
        entries: List[SalesEntry],
        period_start: Optional[date],
        period_end: Optional[date],
    ) -> str:
        """Export sales to XML format compatible with AtomS3."""
        root = ET.Element("SalesJournal")
        root.set("version", "1.0")
        root.set("encoding", "UTF-8")

        # Metadata
        meta = ET.SubElement(root, "Metadata")
        ET.SubElement(meta, "ExportDate").text = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        ET.SubElement(meta, "Software").text = "BJS Menu POS"
        ET.SubElement(meta, "Format").text = "AtomS3"
        if period_start:
            ET.SubElement(meta, "PeriodStart").text = cls.format_bulgarian_date(period_start)
        if period_end:
            ET.SubElement(meta, "PeriodEnd").text = cls.format_bulgarian_date(period_end)
        ET.SubElement(meta, "RecordCount").text = str(len(entries))

        # Summary
        summary = ET.SubElement(root, "Summary")
        total_net = sum(e.net_amount for e in entries)
        total_vat = sum(e.vat_amount for e in entries)
        total_gross = sum(e.gross_amount for e in entries)
        ET.SubElement(summary, "TotalNet").text = cls.format_amount(total_net)
        ET.SubElement(summary, "TotalVAT").text = cls.format_amount(total_vat)
        ET.SubElement(summary, "TotalGross").text = cls.format_amount(total_gross)

        # VAT breakdown
        vat_breakdown = ET.SubElement(summary, "VATBreakdown")
        vat_by_category: Dict[str, Decimal] = {}
        for entry in entries:
            cat = entry.vat_category.value
            vat_by_category[cat] = vat_by_category.get(cat, Decimal("0")) + entry.vat_amount
        for cat, amount in vat_by_category.items():
            vat_cat = ET.SubElement(vat_breakdown, "VATCategory")
            vat_cat.set("rate", cat)
            vat_cat.text = cls.format_amount(amount)

        # Entries
        entries_elem = ET.SubElement(root, "Entries")
        for entry in entries:
            entry_elem = ET.SubElement(entries_elem, "Entry")
            ET.SubElement(entry_elem, "DocumentNumber").text = entry.document_number
            ET.SubElement(entry_elem, "DocumentDate").text = cls.format_bulgarian_date(entry.document_date)
            ET.SubElement(entry_elem, "DocumentType").text = entry.document_type.value
            ET.SubElement(entry_elem, "CustomerName").text = entry.customer_name
            ET.SubElement(entry_elem, "CustomerEIK").text = entry.customer_eik or ""
            ET.SubElement(entry_elem, "CustomerVAT").text = entry.customer_vat or ""
            ET.SubElement(entry_elem, "Description").text = entry.description
            ET.SubElement(entry_elem, "NetAmount").text = cls.format_amount(entry.net_amount)
            ET.SubElement(entry_elem, "VATAmount").text = cls.format_amount(entry.vat_amount)
            ET.SubElement(entry_elem, "GrossAmount").text = cls.format_amount(entry.gross_amount)
            ET.SubElement(entry_elem, "VATCategory").text = entry.vat_category.value
            ET.SubElement(entry_elem, "PaymentMethod").text = entry.payment_method
            ET.SubElement(entry_elem, "DebitAccount").text = entry.gl_account_debit
            ET.SubElement(entry_elem, "CreditAccount").text = entry.gl_account_credit

        return ET.tostring(root, encoding="unicode", method="xml")

    @classmethod
    def _export_sales_json(cls, entries: List[SalesEntry]) -> str:
        """Export sales to JSON format."""
        data = {
            "export_info": {
                "format": "AtomS3",
                "export_date": datetime.utcnow().isoformat(),
                "software": "BJS Menu POS",
                "record_count": len(entries),
            },
            "summary": {
                "total_net": float(sum(e.net_amount for e in entries)),
                "total_vat": float(sum(e.vat_amount for e in entries)),
                "total_gross": float(sum(e.gross_amount for e in entries)),
            },
            "entries": [
                {
                    "document_number": e.document_number,
                    "document_date": cls.format_bulgarian_date(e.document_date),
                    "document_type": e.document_type.value,
                    "customer_name": e.customer_name,
                    "customer_eik": e.customer_eik,
                    "customer_vat": e.customer_vat,
                    "description": e.description,
                    "net_amount": float(e.net_amount),
                    "vat_amount": float(e.vat_amount),
                    "gross_amount": float(e.gross_amount),
                    "vat_category": e.vat_category.value,
                    "payment_method": e.payment_method,
                    "gl_account_debit": e.gl_account_debit,
                    "gl_account_credit": e.gl_account_credit,
                }
                for e in entries
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @classmethod
    def export_purchase_journal(
        cls,
        entries: List[PurchaseEntry],
        format: ExportFormat = ExportFormat.CSV,
    ) -> str:
        """Export purchase journal to AtomS3 format."""
        if format == ExportFormat.CSV:
            return cls._export_purchases_csv(entries)
        elif format == ExportFormat.JSON:
            return cls._export_purchases_json(entries)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @classmethod
    def _export_purchases_csv(cls, entries: List[PurchaseEntry]) -> str:
        """Export purchases to CSV format."""
        output = StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        headers = [
            "Номер документ",
            "Дата документ",
            "Фактура доставчик №",
            "Дата фактура доставчик",
            "Доставчик",
            "ЕИК/БУЛСТАТ",
            "ДДС номер",
            "Описание",
            "Нето",
            "ДДС",
            "Бруто",
            "ДДС категория",
            "Дебит сметка",
            "Кредит сметка",
        ]
        writer.writerow(headers)

        for entry in entries:
            row = [
                entry.document_number,
                cls.format_bulgarian_date(entry.document_date),
                entry.supplier_invoice_number,
                cls.format_bulgarian_date(entry.supplier_invoice_date),
                entry.supplier_name,
                entry.supplier_eik or "",
                entry.supplier_vat or "",
                entry.description,
                cls.format_amount(entry.net_amount),
                cls.format_amount(entry.vat_amount),
                cls.format_amount(entry.gross_amount),
                entry.vat_category.value,
                entry.gl_account_debit,
                entry.gl_account_credit,
            ]
            writer.writerow(row)

        return output.getvalue()

    @classmethod
    def _export_purchases_json(cls, entries: List[PurchaseEntry]) -> str:
        """Export purchases to JSON format."""
        data = {
            "export_info": {
                "format": "AtomS3",
                "export_date": datetime.utcnow().isoformat(),
                "software": "BJS Menu POS",
                "record_count": len(entries),
            },
            "entries": [
                {
                    "document_number": e.document_number,
                    "document_date": cls.format_bulgarian_date(e.document_date),
                    "supplier_invoice_number": e.supplier_invoice_number,
                    "supplier_invoice_date": cls.format_bulgarian_date(e.supplier_invoice_date),
                    "supplier_name": e.supplier_name,
                    "supplier_eik": e.supplier_eik,
                    "supplier_vat": e.supplier_vat,
                    "description": e.description,
                    "net_amount": float(e.net_amount),
                    "vat_amount": float(e.vat_amount),
                    "gross_amount": float(e.gross_amount),
                    "vat_category": e.vat_category.value,
                    "gl_account_debit": e.gl_account_debit,
                    "gl_account_credit": e.gl_account_credit,
                }
                for e in entries
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @classmethod
    def export_gl_chart_of_accounts(cls) -> str:
        """Export GL chart of accounts for AtomS3 setup."""
        output = StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

        headers = ["Код сметка", "Наименование BG", "Наименование EN", "Тип"]
        writer.writerow(headers)

        for key, account in cls.GL_ACCOUNTS.items():
            writer.writerow([
                account.code,
                account.name_bg,
                account.name_en,
                account.account_type,
            ])

        return output.getvalue()

    @classmethod
    def export_vat_declaration_data(
        cls,
        sales_entries: List[SalesEntry],
        purchase_entries: List[PurchaseEntry],
        period_month: int,
        period_year: int,
    ) -> Dict[str, Any]:
        """
        Generate data for Bulgarian VAT declaration (справка-декларация по ЗДДС).

        Returns structured data that can be used to fill VAT declaration forms.
        """
        # Calculate totals
        sales_by_vat: Dict[str, Dict[str, Decimal]] = {}
        for entry in sales_entries:
            cat = entry.vat_category.value
            if cat not in sales_by_vat:
                sales_by_vat[cat] = {"net": Decimal("0"), "vat": Decimal("0")}
            sales_by_vat[cat]["net"] += entry.net_amount
            sales_by_vat[cat]["vat"] += entry.vat_amount

        purchases_by_vat: Dict[str, Dict[str, Decimal]] = {}
        for entry in purchase_entries:
            cat = entry.vat_category.value
            if cat not in purchases_by_vat:
                purchases_by_vat[cat] = {"net": Decimal("0"), "vat": Decimal("0")}
            purchases_by_vat[cat]["net"] += entry.net_amount
            purchases_by_vat[cat]["vat"] += entry.vat_amount

        total_sales_vat = sum(v["vat"] for v in sales_by_vat.values())
        total_purchases_vat = sum(v["vat"] for v in purchases_by_vat.values())
        vat_due = total_sales_vat - total_purchases_vat

        return {
            "period": {
                "month": period_month,
                "year": period_year,
                "period_string": f"{period_month:02d}.{period_year}",
            },
            "sales": {
                "by_vat_rate": {
                    k: {"net": float(v["net"]), "vat": float(v["vat"])}
                    for k, v in sales_by_vat.items()
                },
                "total_net": float(sum(e.net_amount for e in sales_entries)),
                "total_vat": float(total_sales_vat),
                "total_gross": float(sum(e.gross_amount for e in sales_entries)),
                "invoice_count": len(sales_entries),
            },
            "purchases": {
                "by_vat_rate": {
                    k: {"net": float(v["net"]), "vat": float(v["vat"])}
                    for k, v in purchases_by_vat.items()
                },
                "total_net": float(sum(e.net_amount for e in purchase_entries)),
                "total_vat": float(total_purchases_vat),
                "total_gross": float(sum(e.gross_amount for e in purchase_entries)),
                "invoice_count": len(purchase_entries),
            },
            "vat_calculation": {
                "output_vat": float(total_sales_vat),
                "input_vat": float(total_purchases_vat),
                "vat_due": float(vat_due),
                "vat_refund": float(-vat_due) if vat_due < 0 else 0,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
