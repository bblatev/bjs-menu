"""
Hardware SDK & BNPL API Endpoints
Phase 8: Hardware management, Terminal SDK, and Buy Now Pay Later integration
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rbac import get_current_user, get_current_venue
from app.core.rate_limit import limiter
from app.models import StaffUser as Staff


router = APIRouter()


# ==================== SCHEMAS ====================

# Hardware
class DeviceRegistrationRequest(BaseModel):
    device_type: str
    serial_number: str
    manufacturer: str
    model: str
    firmware_version: Optional[str] = None
    connection_type: str = "usb"
    connection_params: Optional[Dict[str, Any]] = None
    capabilities: Optional[List[str]] = None
    station_id: Optional[UUID] = None


class DeviceAuthRequest(BaseModel):
    device_id: UUID
    device_token: str


class DeviceStatusUpdate(BaseModel):
    status: str
    status_details: Optional[Dict[str, Any]] = None


class TerminalCommandRequest(BaseModel):
    command: str
    params: Dict[str, Any] = {}


class PrintReceiptRequest(BaseModel):
    receipt_data: Dict[str, Any]
    copies: int = 1


class CustomerDisplayRequest(BaseModel):
    lines: List[str]


# BNPL
class BNPLConfigRequest(BaseModel):
    provider: str
    credentials: Dict[str, Any]
    settings: Optional[Dict[str, Any]] = None


class BNPLSessionRequest(BaseModel):
    provider: str
    order_id: UUID
    amount: float
    currency: str = "USD"
    customer_info: Optional[Dict[str, Any]] = None
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None


class BNPLRefundRequest(BaseModel):
    amount: Optional[float] = None
    reason: Optional[str] = None


# ==================== HARDWARE DEVICE ENDPOINTS ====================

@router.post("/hardware/devices")
@limiter.limit("30/minute")
async def register_device(
    request: Request,
    body: DeviceRegistrationRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: UUID = Depends(get_current_venue)
):
    """Register a new hardware device."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    result = await service.register_device(
        venue_id=venue_id,
        station_id=body.station_id,
        device_type=body.device_type,
        serial_number=body.serial_number,
        manufacturer=body.manufacturer,
        model=body.model,
        firmware_version=body.firmware_version,
        connection_type=body.connection_type,
        connection_params=body.connection_params,
        capabilities=body.capabilities
    )
    return result


@router.post("/hardware/devices/authenticate")
@limiter.limit("30/minute")
async def authenticate_device(
    request: Request,
    body: DeviceAuthRequest,
    db: Session = Depends(get_db)
):
    """Authenticate a hardware device."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    result = await service.authenticate_device(
        device_id=body.device_id,
        device_token=body.device_token
    )

    if not result:
        raise HTTPException(status_code=401, detail="Invalid device credentials")

    return result


@router.get("/hardware/devices")
@limiter.limit("60/minute")
async def list_devices(
    request: Request,
    device_type: Optional[str] = None,
    station_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: UUID = Depends(get_current_venue)
):
    """List hardware devices for venue."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    devices = await service.get_venue_devices(
        venue_id=venue_id,
        device_type=device_type,
        station_id=station_id
    )
    return {"devices": devices}


@router.get("/hardware/devices/{device_id}")
@limiter.limit("60/minute")
async def get_device(
    request: Request,
    device_id: UUID,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get device details."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    # Would need to implement get_device method
    return {"device_id": str(device_id)}


@router.put("/hardware/devices/{device_id}/status")
@limiter.limit("30/minute")
async def update_device_status(
    request: Request,
    device_id: UUID,
    body: DeviceStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update device status (called by device)."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    success = await service.update_device_status(
        device_id=device_id,
        status=body.status,
        status_details=body.status_details
    )

    if not success:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"status": "updated"}


@router.delete("/hardware/devices/{device_id}")
@limiter.limit("30/minute")
async def deactivate_device(
    request: Request,
    device_id: UUID,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Deactivate a hardware device."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    success = await service.deactivate_device(device_id)

    if not success:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"status": "deactivated"}


@router.get("/hardware/devices/{device_id}/diagnostics")
@limiter.limit("60/minute")
async def run_diagnostics(
    request: Request,
    device_id: UUID,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Run diagnostics on a device."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    try:
        diagnostics = await service.run_device_diagnostics(device_id)
        return diagnostics
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/hardware/devices/{device_id}/logs")
@limiter.limit("60/minute")
async def get_device_logs(
    request: Request,
    device_id: UUID,
    limit: int = 100,
    since: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get device activity logs."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    logs = await service.get_device_logs(
        device_id=device_id,
        limit=limit,
        since=since
    )
    return {"logs": logs}


# ==================== TERMINAL SDK ENDPOINTS ====================

@router.post("/hardware/terminals/{device_id}/sessions")
@limiter.limit("30/minute")
async def create_terminal_session(
    request: Request,
    device_id: UUID,
    session_type: str = "payment",
    db: Session = Depends(get_db)
):
    """Create a terminal session."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    session = await service.create_terminal_session(
        device_id=device_id,
        session_type=session_type
    )
    return session


@router.post("/hardware/terminals/{device_id}/commands")
@limiter.limit("30/minute")
async def send_terminal_command(
    request: Request,
    device_id: UUID,
    body: TerminalCommandRequest,
    db: Session = Depends(get_db)
):
    """Send a command to a terminal."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    try:
        result = await service.send_terminal_command(
            device_id=device_id,
            command=body.command,
            params=body.params
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/hardware/terminals/commands/{command_id}")
@limiter.limit("60/minute")
async def get_command_result(
    request: Request,
    command_id: UUID,
    db: Session = Depends(get_db)
):
    """Get the result of a terminal command."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    result = await service.get_command_result(command_id)

    if not result:
        raise HTTPException(status_code=404, detail="Command not found")

    return result


@router.put("/hardware/terminals/commands/{command_id}")
@limiter.limit("30/minute")
async def update_command_result(
    request: Request,
    command_id: UUID,
    status: str = Body(...),
    result: Optional[Dict[str, Any]] = Body(None),
    error: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """Update command result (called by device)."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    success = await service.update_command_result(
        command_id=command_id,
        status=status,
        result=result,
        error=error
    )

    if not success:
        raise HTTPException(status_code=404, detail="Command not found")

    return {"status": "updated"}


# ==================== PRINTER ENDPOINTS ====================

@router.post("/hardware/printers/{device_id}/print")
@limiter.limit("30/minute")
async def print_receipt(
    request: Request,
    device_id: UUID,
    body: PrintReceiptRequest,
    db: Session = Depends(get_db)
):
    """Print a receipt."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    result = await service.print_receipt(
        device_id=device_id,
        receipt_data=body.receipt_data,
        copies=body.copies
    )
    return result


@router.post("/hardware/cash-drawers/{device_id}/open")
@limiter.limit("30/minute")
async def open_cash_drawer(
    request: Request,
    device_id: UUID,
    db: Session = Depends(get_db)
):
    """Open cash drawer."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    result = await service.open_cash_drawer(device_id)
    return result


@router.post("/hardware/displays/{device_id}/message")
@limiter.limit("30/minute")
async def display_message(
    request: Request,
    device_id: UUID,
    body: CustomerDisplayRequest,
    db: Session = Depends(get_db)
):
    """Display message on customer display."""
    from app.services.hardware_sdk_service import HardwareSDKService

    service = HardwareSDKService(db)
    result = await service.display_customer_message(
        device_id=device_id,
        lines=body.lines
    )
    return result


# ==================== BNPL ENDPOINTS ====================

@router.post("/bnpl/configure")
@limiter.limit("30/minute")
async def configure_bnpl_provider(
    request: Request,
    body: BNPLConfigRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: UUID = Depends(get_current_venue)
):
    """Configure a BNPL provider."""
    from app.services.hardware_sdk_service import BNPLService

    service = BNPLService(db)
    result = await service.configure_provider(
        venue_id=venue_id,
        provider=body.provider,
        credentials=body.credentials,
        settings=body.settings
    )
    return result


@router.get("/bnpl/providers")
@limiter.limit("60/minute")
async def get_enabled_providers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: UUID = Depends(get_current_venue)
):
    """Get enabled BNPL providers."""
    from app.services.hardware_sdk_service import BNPLService

    service = BNPLService(db)
    providers = await service.get_enabled_providers(venue_id)
    return {"providers": providers}


@router.post("/bnpl/sessions")
@limiter.limit("30/minute")
async def create_bnpl_session(
    request: Request,
    body: BNPLSessionRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: UUID = Depends(get_current_venue)
):
    """Create a BNPL checkout session."""
    from app.services.hardware_sdk_service import BNPLService

    service = BNPLService(db)
    try:
        result = await service.create_bnpl_session(
            venue_id=venue_id,
            provider=body.provider,
            order_id=body.order_id,
            amount=body.amount,
            currency=body.currency,
            customer_info=body.customer_info,
            return_url=body.return_url,
            cancel_url=body.cancel_url
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bnpl/transactions/{transaction_id}")
@limiter.limit("60/minute")
async def get_bnpl_transaction(
    request: Request,
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Get BNPL transaction details."""
    from app.services.hardware_sdk_service import BNPLService

    service = BNPLService(db)
    transaction = await service.get_transaction(transaction_id)

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return transaction


@router.post("/bnpl/transactions/{transaction_id}/capture")
@limiter.limit("30/minute")
async def capture_bnpl_payment(
    request: Request,
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Capture an authorized BNPL payment."""
    from app.services.hardware_sdk_service import BNPLService

    service = BNPLService(db)
    try:
        result = await service.capture_bnpl_payment(transaction_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bnpl/transactions/{transaction_id}/refund")
@limiter.limit("30/minute")
async def refund_bnpl_payment(
    request: Request,
    transaction_id: UUID,
    body: BNPLRefundRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user)
):
    """Refund a BNPL payment."""
    from app.services.hardware_sdk_service import BNPLService

    service = BNPLService(db)
    try:
        result = await service.refund_bnpl_payment(
            transaction_id=transaction_id,
            amount=body.amount,
            reason=body.reason
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bnpl/transactions")
@limiter.limit("60/minute")
async def list_bnpl_transactions(
    request: Request,
    provider: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: UUID = Depends(get_current_venue)
):
    """List BNPL transactions."""
    from app.services.hardware_sdk_service import BNPLService

    service = BNPLService(db)
    transactions, total = await service.get_venue_transactions(
        venue_id=venue_id,
        provider=provider,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    return {"transactions": transactions, "total": total}


@router.post("/bnpl/webhooks/{provider}")
@limiter.limit("30/minute")
async def handle_bnpl_webhook(
    request: Request,
    provider: str,
    payload: Dict[str, Any] = Body(...),
    signature: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle BNPL provider webhook."""
    from app.services.hardware_sdk_service import BNPLService

    service = BNPLService(db)
    result = await service.handle_webhook(
        provider=provider,
        payload=payload,
        signature=signature
    )
    return result


# ==================== DEVICE TYPES INFO ====================

@router.get("/hardware/device-types")
@limiter.limit("60/minute")
async def get_device_types(request: Request):
    """Get supported device types and their capabilities."""
    from app.services.hardware_sdk_service import HardwareDevice

    return {"device_types": HardwareDevice.DEVICE_TYPES}


@router.get("/bnpl/provider-info")
@limiter.limit("60/minute")
async def get_bnpl_provider_info(request: Request):
    """Get information about supported BNPL providers."""
    return {
        "providers": [
            {
                "id": "klarna",
                "name": "Klarna",
                "description": "Pay in 4 interest-free payments",
                "countries": ["US", "UK", "DE", "SE", "NO", "FI", "DK", "NL", "BE", "AT"],
                "min_amount": 35,
                "max_amount": 1000
            },
            {
                "id": "affirm",
                "name": "Affirm",
                "description": "Pay over time with monthly payments",
                "countries": ["US", "CA"],
                "min_amount": 50,
                "max_amount": 17500
            },
            {
                "id": "afterpay",
                "name": "Afterpay",
                "description": "Pay in 4 interest-free installments",
                "countries": ["US", "AU", "NZ"],
                "min_amount": 1,
                "max_amount": 2000
            },
            {
                "id": "clearpay",
                "name": "Clearpay",
                "description": "Pay in 4 interest-free installments",
                "countries": ["UK", "ES", "FR", "IT"],
                "min_amount": 1,
                "max_amount": 1000
            },
            {
                "id": "zip",
                "name": "Zip",
                "description": "Buy now, pay later",
                "countries": ["US", "AU", "NZ", "UK"],
                "min_amount": 35,
                "max_amount": 1500
            }
        ]
    }
