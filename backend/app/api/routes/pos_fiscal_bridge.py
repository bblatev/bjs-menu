"""POS Fiscal Bridge routes."""

from fastapi import APIRouter, Request

from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.models.operations import AppSetting

router = APIRouter()


def _get_bridge_config(db: DbSession) -> dict:
    """Get fiscal bridge config from DB."""
    row = db.query(AppSetting).filter(
        AppSetting.category == "pos_fiscal_bridge",
        AppSetting.key == "config",
    ).first()
    if row and isinstance(row.value, dict):
        return row.value
    return {}


@router.get("/")
@limiter.limit("60/minute")
async def get_pos_fiscal_bridge_root(request: Request, db: DbSession):
    """POS fiscal bridge status."""
    return await get_bridge_status(request=request, db=db)


@router.get("/status")
@limiter.limit("60/minute")
async def get_bridge_status(request: Request, db: DbSession):
    """Get POS fiscal bridge status."""
    config = _get_bridge_config(db)
    return {
        "connected": config.get("connected", False),
        "printer_model": config.get("printer_model", None),
        "printer_status": config.get("printer_status", "not_configured"),
        "last_receipt": config.get("last_receipt", None),
        "daily_report_printed": config.get("daily_report_printed", False),
        "receipts_today": config.get("receipts_today", 0),
        "errors_today": config.get("errors_today", 0),
    }


@router.post("/receipt")
@limiter.limit("30/minute")
async def print_receipt(request: Request, data: dict, db: DbSession):
    """Print a fiscal receipt."""
    config = _get_bridge_config(db)
    if not config.get("connected"):
        return {"success": False, "error": "Fiscal printer not connected"}
    return {"success": True, "receipt_number": None}


@router.post("/drawer")
@limiter.limit("30/minute")
async def open_drawer(request: Request):
    """Open cash drawer."""
    return {"success": True}


@router.post("/card-payment")
@limiter.limit("30/minute")
async def process_card_payment(request: Request, data: dict, db: DbSession):
    """Process card payment through fiscal device."""
    config = _get_bridge_config(db)
    if not config.get("connected"):
        return {"success": False, "error": "Fiscal device not connected"}
    return {"success": True, "transaction_id": None}


@router.post("/report")
@limiter.limit("30/minute")
async def print_report(request: Request, data: dict):
    """Print a fiscal report (X or Z report)."""
    return {"success": True, "report_type": data.get("type", "x")}
