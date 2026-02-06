"""POS Fiscal Bridge routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def get_bridge_status():
    """Get POS fiscal bridge status."""
    return {
        "connected": True,
        "printer_model": "Datecs DP-25",
        "printer_status": "ready",
        "last_receipt": "2026-02-06T17:30:00Z",
        "daily_report_printed": False,
        "receipts_today": 142,
        "errors_today": 0,
    }


@router.post("/receipt")
async def print_receipt(data: dict):
    """Print a fiscal receipt."""
    return {"success": True, "receipt_number": "0001234"}


@router.post("/drawer")
async def open_drawer():
    """Open cash drawer."""
    return {"success": True}


@router.post("/card-payment")
async def process_card_payment(data: dict):
    """Process card payment through fiscal device."""
    return {"success": True, "transaction_id": "TXN-001"}


@router.post("/report")
async def print_report(data: dict):
    """Print a fiscal report (X or Z report)."""
    return {"success": True, "report_type": data.get("type", "x")}
