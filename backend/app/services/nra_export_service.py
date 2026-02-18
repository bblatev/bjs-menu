"""Bulgarian NRA (National Revenue Agency) accounting export service.

Generates NRA-compliant XML files for:
- Sales journal (Дневник за продажбите)
- Purchase journal (Дневник за покупките)
- VAT declaration data (Справка-декларация по ЗДДС)
"""

import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Bulgarian VAT rates
VAT_STANDARD = Decimal("20")   # 20% standard rate
VAT_REDUCED = Decimal("9")     # 9% reduced rate (hotels)
VAT_ZERO = Decimal("0")        # 0% rate (exports, exempt)


class NRAExportService:
    """Generate NRA-compliant accounting exports."""

    def __init__(self, company_eik: str = "", company_name: str = "", vat_number: str = ""):
        self.company_eik = company_eik
        self.company_name = company_name
        self.vat_number = vat_number

    def generate_sales_journal_xml(
        self,
        period_start: date,
        period_end: date,
        sales: List[Dict[str, Any]],
    ) -> str:
        """Generate Sales Journal XML (Дневник за продажбите).

        Each sale entry should have:
            - doc_number: Invoice/receipt number
            - doc_date: Date of document
            - counterparty_name: Customer name
            - counterparty_eik: Customer EIK/EGN
            - tax_base_20: Taxable amount at 20%
            - vat_20: VAT amount at 20%
            - tax_base_9: Taxable amount at 9%
            - vat_9: VAT amount at 9%
            - tax_base_0: Exempt/zero-rate amount
            - total: Total amount with VAT
        """
        root = ET.Element("SalesJournal")
        root.set("xmlns", "urn:nra:sales-journal:v1")

        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "EIK").text = self.company_eik
        ET.SubElement(header, "CompanyName").text = self.company_name
        ET.SubElement(header, "VATNumber").text = self.vat_number
        ET.SubElement(header, "PeriodStart").text = period_start.isoformat()
        ET.SubElement(header, "PeriodEnd").text = period_end.isoformat()

        entries = ET.SubElement(root, "Entries")
        total_base_20 = Decimal("0")
        total_vat_20 = Decimal("0")
        total_base_9 = Decimal("0")
        total_vat_9 = Decimal("0")
        total_base_0 = Decimal("0")

        for i, sale in enumerate(sales, 1):
            entry = ET.SubElement(entries, "Entry")
            ET.SubElement(entry, "LineNumber").text = str(i)
            ET.SubElement(entry, "DocType").text = sale.get("doc_type", "01")
            ET.SubElement(entry, "DocNumber").text = str(sale.get("doc_number", ""))
            ET.SubElement(entry, "DocDate").text = str(sale.get("doc_date", ""))
            ET.SubElement(entry, "CounterpartyName").text = sale.get("counterparty_name", "")
            ET.SubElement(entry, "CounterpartyEIK").text = sale.get("counterparty_eik", "")

            base_20 = Decimal(str(sale.get("tax_base_20", 0)))
            vat_20 = Decimal(str(sale.get("vat_20", 0)))
            base_9 = Decimal(str(sale.get("tax_base_9", 0)))
            vat_9 = Decimal(str(sale.get("vat_9", 0)))
            base_0 = Decimal(str(sale.get("tax_base_0", 0)))

            ET.SubElement(entry, "TaxBase20").text = f"{base_20:.2f}"
            ET.SubElement(entry, "VAT20").text = f"{vat_20:.2f}"
            ET.SubElement(entry, "TaxBase9").text = f"{base_9:.2f}"
            ET.SubElement(entry, "VAT9").text = f"{vat_9:.2f}"
            ET.SubElement(entry, "TaxBase0").text = f"{base_0:.2f}"
            ET.SubElement(entry, "Total").text = f"{base_20 + vat_20 + base_9 + vat_9 + base_0:.2f}"

            total_base_20 += base_20
            total_vat_20 += vat_20
            total_base_9 += base_9
            total_vat_9 += vat_9
            total_base_0 += base_0

        totals = ET.SubElement(root, "Totals")
        ET.SubElement(totals, "TotalTaxBase20").text = f"{total_base_20:.2f}"
        ET.SubElement(totals, "TotalVAT20").text = f"{total_vat_20:.2f}"
        ET.SubElement(totals, "TotalTaxBase9").text = f"{total_base_9:.2f}"
        ET.SubElement(totals, "TotalVAT9").text = f"{total_vat_9:.2f}"
        ET.SubElement(totals, "TotalTaxBase0").text = f"{total_base_0:.2f}"
        ET.SubElement(totals, "GrandTotal").text = f"{total_base_20 + total_vat_20 + total_base_9 + total_vat_9 + total_base_0:.2f}"
        ET.SubElement(totals, "EntryCount").text = str(len(sales))

        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def generate_purchase_journal_xml(
        self,
        period_start: date,
        period_end: date,
        purchases: List[Dict[str, Any]],
    ) -> str:
        """Generate Purchase Journal XML (Дневник за покупките)."""
        root = ET.Element("PurchaseJournal")
        root.set("xmlns", "urn:nra:purchase-journal:v1")

        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "EIK").text = self.company_eik
        ET.SubElement(header, "CompanyName").text = self.company_name
        ET.SubElement(header, "VATNumber").text = self.vat_number
        ET.SubElement(header, "PeriodStart").text = period_start.isoformat()
        ET.SubElement(header, "PeriodEnd").text = period_end.isoformat()

        entries = ET.SubElement(root, "Entries")
        total_base = Decimal("0")
        total_vat = Decimal("0")
        total_full_credit = Decimal("0")

        for i, purchase in enumerate(purchases, 1):
            entry = ET.SubElement(entries, "Entry")
            ET.SubElement(entry, "LineNumber").text = str(i)
            ET.SubElement(entry, "DocType").text = purchase.get("doc_type", "01")
            ET.SubElement(entry, "DocNumber").text = str(purchase.get("doc_number", ""))
            ET.SubElement(entry, "DocDate").text = str(purchase.get("doc_date", ""))
            ET.SubElement(entry, "SupplierName").text = purchase.get("supplier_name", "")
            ET.SubElement(entry, "SupplierEIK").text = purchase.get("supplier_eik", "")
            ET.SubElement(entry, "SupplierVAT").text = purchase.get("supplier_vat", "")

            base = Decimal(str(purchase.get("tax_base", 0)))
            vat = Decimal(str(purchase.get("vat_amount", 0)))
            credit = Decimal(str(purchase.get("vat_credit", 0)))

            ET.SubElement(entry, "TaxBase").text = f"{base:.2f}"
            ET.SubElement(entry, "VATAmount").text = f"{vat:.2f}"
            ET.SubElement(entry, "VATCredit").text = f"{credit:.2f}"

            total_base += base
            total_vat += vat
            total_full_credit += credit

        totals = ET.SubElement(root, "Totals")
        ET.SubElement(totals, "TotalTaxBase").text = f"{total_base:.2f}"
        ET.SubElement(totals, "TotalVAT").text = f"{total_vat:.2f}"
        ET.SubElement(totals, "TotalVATCredit").text = f"{total_full_credit:.2f}"
        ET.SubElement(totals, "EntryCount").text = str(len(purchases))

        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def generate_vat_return(
        self,
        period_start: date,
        period_end: date,
        sales_totals: Dict[str, Decimal],
        purchase_totals: Dict[str, Decimal],
    ) -> Dict[str, Any]:
        """Generate VAT return summary data (Справка-декларация по ЗДДС)."""
        vat_collected = (
            sales_totals.get("total_vat_20", Decimal("0"))
            + sales_totals.get("total_vat_9", Decimal("0"))
        )
        vat_credit = purchase_totals.get("total_vat_credit", Decimal("0"))
        vat_due = vat_collected - vat_credit

        return {
            "period": f"{period_start.isoformat()} - {period_end.isoformat()}",
            "company_eik": self.company_eik,
            "company_name": self.company_name,
            "vat_number": self.vat_number,
            "sales_base_20": float(sales_totals.get("total_base_20", 0)),
            "sales_vat_20": float(sales_totals.get("total_vat_20", 0)),
            "sales_base_9": float(sales_totals.get("total_base_9", 0)),
            "sales_vat_9": float(sales_totals.get("total_vat_9", 0)),
            "sales_base_0": float(sales_totals.get("total_base_0", 0)),
            "total_vat_collected": float(vat_collected),
            "purchase_base": float(purchase_totals.get("total_base", 0)),
            "purchase_vat": float(purchase_totals.get("total_vat", 0)),
            "vat_credit": float(vat_credit),
            "vat_due": float(vat_due),
            "vat_refund": float(abs(vat_due)) if vat_due < 0 else 0,
        }


nra_export = NRAExportService()
