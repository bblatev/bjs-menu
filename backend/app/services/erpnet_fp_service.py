"""
ErpNet.FP Service Stub
========================
Service stub for ErpNet.FP fiscal printer integration.
Provides a JSON REST API interface for Datecs Blue Cash 50
and other fiscal printers supported by ErpNet.FP.
"""

from decimal import Decimal
from typing import Optional, List, Dict, Any


class ErpNetFPService:
    """Stub service for ErpNet.FP fiscal printer operations.

    All methods are async to match the route file expectations.
    """

    def __init__(self, db=None):
        self.db = db

    async def get_status(self) -> dict:
        """Check ErpNet.FP server and printer status.

        Returns dict with server and printer status information.
        """
        return {
            "ok": True,
            "server": "ErpNet.FP",
            "version": "stub",
            "printers": [],
        }

    async def get_printers(self) -> list:
        """Get list of available fiscal printers.

        Returns list of printer info dicts.
        """
        return []

    async def print_fiscal_receipt(self, items: list, payments: list,
                                    unique_sale_number: str = None) -> dict:
        """Print a fiscal receipt.

        Args:
            items: List of dicts with 'text', 'quantity', 'unitPrice', 'taxGroup'.
            payments: List of dicts with 'amount', 'paymentType'.
            unique_sale_number: Optional unique sale number.

        Returns dict with success status and receipt_number.
        """
        return {
            "success": True,
            "receipt_number": None,
            "message": "Stub: fiscal receipt not actually printed",
        }

    async def print_x_report(self) -> dict:
        """Print X-report (daily summary without closing).

        Returns dict with report status.
        """
        return {"ok": True, "message": "Stub: X-report not actually printed"}

    async def print_z_report(self) -> dict:
        """Print Z-report (daily closing report).

        Returns dict with report status.
        """
        return {"ok": True, "message": "Stub: Z-report not actually printed"}

    async def cash_in(self, amount: Decimal) -> dict:
        """Cash in operation (service deposit).

        Args:
            amount: Amount to deposit.

        Returns dict with operation status.
        """
        return {"ok": True, "amount": float(amount)}

    async def cash_out(self, amount: Decimal) -> dict:
        """Cash out operation (service withdraw).

        Args:
            amount: Amount to withdraw.

        Returns dict with operation status.
        """
        return {"ok": True, "amount": float(amount)}

    async def print_duplicate(self) -> dict:
        """Print duplicate of last receipt.

        Returns dict with operation status.
        """
        return {"ok": True, "message": "Stub: duplicate not actually printed"}


# Singleton instance
_service_instance: Optional[ErpNetFPService] = None


def get_erpnet_fp_service(db=None) -> ErpNetFPService:
    """Get or create the ErpNet.FP service instance.

    Args:
        db: Optional database session (not used in stub).

    Returns:
        ErpNetFPService instance.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = ErpNetFPService(db=db)
    return _service_instance
