"""
Mobile Scanner API Endpoints
For handheld RFID scanners, barcode readers, and mobile inventory apps
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.core.rate_limit import limiter
from app.models import StaffUser
from app.services.v9_features.iot_service import IoTService

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class MobileScanRequest(BaseModel):
    """Single scan from mobile device"""
    scan_type: str = Field(..., description="rfid, barcode, qr")
    scan_data: str = Field(..., description="Scanned tag/barcode value")
    location_zone: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    device_id: Optional[str] = Field(None, description="Mobile device identifier")


class BatchScanRequest(BaseModel):
    """Batch of scans from mobile device"""
    scans: List[MobileScanRequest]
    session_id: Optional[str] = Field(None, description="Inventory count session ID")


class MobileInventoryStartRequest(BaseModel):
    """Start mobile inventory session"""
    count_type: str = Field("spot_check", description="full, zone, spot_check")
    zone: Optional[str] = None
    offline_mode: bool = Field(False, description="Enable offline data collection")


class OfflineSyncRequest(BaseModel):
    """Sync offline collected data"""
    device_id: str
    scans: List[Dict[str, Any]]
    collected_at: datetime


class StockLookupRequest(BaseModel):
    """Lookup stock by barcode"""
    barcode: str
    barcode_type: str = Field("ean13", description="ean13, ean8, upc, code128, qr")


class QuickReceiveRequest(BaseModel):
    """Quick receive items via scan"""
    barcode: str
    quantity: float = 1.0
    location_zone: str = "receiving"
    supplier_id: Optional[int] = None
    purchase_order_id: Optional[int] = None


class QuickDispenseRequest(BaseModel):
    """Quick dispense/use items"""
    barcode: str
    quantity: float = 1.0
    reason: str = Field("usage", description="usage, waste, transfer, sale")
    destination_zone: Optional[str] = None
    order_id: Optional[int] = None


# =============================================================================
# MOBILE SCAN ENDPOINTS
# =============================================================================

@router.post("/scan", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def process_mobile_scan(
    request: Request,
    data: MobileScanRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Process a single scan from mobile device.
    Automatically detects RFID tags vs barcodes.
    """
    result = {
        "scan_type": data.scan_type,
        "scan_data": data.scan_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "unknown"
    }

    if data.scan_type == "rfid":
        # Process RFID tag
        try:
            scan_result = IoTService.record_rfid_scan(
                db=db,
                venue_id=current_user.venue_id,
                reader_id=1,  # Virtual mobile reader
                tag_id=data.scan_data,
                read_type="mobile_scan",
                location_zone=data.location_zone,
                staff_user_id=current_user.id
            )
            result.update(scan_result)
            result["status"] = "success"
        except ValueError as e:
            result["status"] = "error"
            result["message"] = str(e)

    elif data.scan_type in ["barcode", "qr"]:
        # Lookup item by barcode
        from app.models import StockItem, MenuItem

        # Search stock items
        stock_item = db.query(StockItem).filter(
            StockItem.barcode == data.scan_data
        ).first()

        if stock_item:
            result["status"] = "found"
            result["item_type"] = "stock"
            result["item"] = {
                "id": stock_item.id,
                "name": stock_item.name,
                "sku": stock_item.sku,
                "quantity": stock_item.quantity,
                "unit": stock_item.unit,
                "location": stock_item.location
            }
        else:
            # Search menu items
            menu_item = db.query(MenuItem).filter(
                MenuItem.barcode == data.scan_data
            ).first()

            if menu_item:
                result["status"] = "found"
                result["item_type"] = "menu"
                result["item"] = {
                    "id": menu_item.id,
                    "name": menu_item.name,
                    "price": float(menu_item.price) if menu_item.price else 0,
                    "available": menu_item.is_available
                }
            else:
                result["status"] = "not_found"
                result["message"] = "Item not found in system"

    return result


@router.post("/scan/batch", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def process_batch_scans(
    request: Request,
    data: BatchScanRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Process batch of scans from mobile device.
    Useful for bulk inventory operations.
    """
    results = []
    success_count = 0
    error_count = 0

    for scan in data.scans:
        try:
            if scan.scan_type == "rfid":
                scan_result = IoTService.record_rfid_scan(
                    db=db,
                    venue_id=current_user.venue_id,
                    reader_id=1,
                    tag_id=scan.scan_data,
                    read_type="batch_scan",
                    location_zone=scan.location_zone,
                    staff_user_id=current_user.id
                )
                results.append({"data": scan.scan_data, "status": "success", "result": scan_result})
                success_count += 1
            else:
                results.append({"data": scan.scan_data, "status": "processed"})
                success_count += 1
        except Exception as e:
            results.append({"data": scan.scan_data, "status": "error", "message": str(e)})
            error_count += 1

    # Update inventory count if session provided
    if data.session_id:
        tag_ids = [s.scan_data for s in data.scans if s.scan_type == "rfid"]
        if tag_ids:
            try:
                IoTService.record_rfid_count_scan(
                    db=db,
                    count_id=data.session_id,
                    tag_ids=tag_ids
                )
            except Exception as e:
                logger.warning(f"Failed to record RFID count scan for session {data.session_id}: {e}")

    return {
        "total_scans": len(data.scans),
        "success": success_count,
        "errors": error_count,
        "results": results
    }


@router.post("/inventory/start", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def start_mobile_inventory(
    request: Request,
    data: MobileInventoryStartRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Start a mobile inventory count session.
    Returns session ID for tracking scans.
    """
    result = IoTService.start_rfid_inventory_count(
        db=db,
        venue_id=current_user.venue_id,
        count_type=data.count_type,
        started_by=current_user.id,
        zone=data.zone
    )

    result["offline_mode"] = data.offline_mode
    result["instructions"] = [
        "Scan all RFID tags in the designated area",
        "Use batch upload when returning to coverage",
        "Session expires after 24 hours"
    ]

    return result


@router.post("/inventory/{session_id}/complete", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def complete_mobile_inventory(
    request: Request,
    session_id: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Complete a mobile inventory count session."""
    try:
        return IoTService.complete_rfid_inventory_count(
            db=db,
            count_id=session_id,
            completed_by=current_user.id,
            notes=notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sync/offline", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def sync_offline_data(
    request: Request,
    data: OfflineSyncRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Sync offline collected scan data.
    Called when mobile device regains connectivity.
    """
    processed = 0
    errors = []

    for scan in data.scans:
        try:
            if scan.get("scan_type") == "rfid":
                IoTService.record_rfid_scan(
                    db=db,
                    venue_id=current_user.venue_id,
                    reader_id=1,
                    tag_id=scan.get("scan_data"),
                    read_type="offline_sync",
                    location_zone=scan.get("location_zone"),
                    staff_user_id=current_user.id
                )
            processed += 1
        except Exception as e:
            errors.append({"scan": scan, "error": str(e)})

    return {
        "device_id": data.device_id,
        "collected_at": data.collected_at.isoformat(),
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "total_scans": len(data.scans),
        "processed": processed,
        "errors": len(errors),
        "error_details": errors[:10]  # First 10 errors
    }


# =============================================================================
# QUICK OPERATIONS
# =============================================================================

@router.post("/quick/lookup", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def quick_stock_lookup(
    request: Request,
    data: StockLookupRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Quick lookup item by barcode.
    Returns stock level, location, and related info.
    """
    from app.models import StockItem

    item = db.query(StockItem).filter(
        StockItem.barcode == data.barcode,
        StockItem.venue_id == current_user.venue_id
    ).first()

    if not item:
        # Try by SKU
        item = db.query(StockItem).filter(
            StockItem.sku == data.barcode,
            StockItem.venue_id == current_user.venue_id
        ).first()

    if not item:
        return {
            "found": False,
            "barcode": data.barcode,
            "message": "Item not found"
        }

    # Check stock status
    status = "ok"
    if item.quantity <= 0:
        status = "out_of_stock"
    elif item.low_stock_threshold and item.quantity <= item.low_stock_threshold:
        status = "low_stock"

    return {
        "found": True,
        "item": {
            "id": item.id,
            "name": item.name,
            "sku": item.sku,
            "barcode": item.barcode,
            "quantity": item.quantity,
            "unit": item.unit,
            "location": item.location,
            "low_stock_threshold": item.low_stock_threshold,
            "cost_per_unit": float(item.cost_per_unit) if item.cost_per_unit else None
        },
        "status": status,
        "actions": ["receive", "dispense", "transfer", "count"]
    }


@router.post("/quick/receive", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def quick_receive_stock(
    request: Request,
    data: QuickReceiveRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Quick receive stock item via barcode scan.
    Increases stock quantity.
    """
    from app.models import StockItem

    item = db.query(StockItem).filter(
        StockItem.barcode == data.barcode,
        StockItem.venue_id == current_user.venue_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    old_quantity = item.quantity
    item.quantity += data.quantity
    item.location = data.location_zone

    db.commit()

    return {
        "success": True,
        "item_id": item.id,
        "item_name": item.name,
        "old_quantity": old_quantity,
        "received": data.quantity,
        "new_quantity": item.quantity,
        "location": data.location_zone
    }


@router.post("/quick/dispense", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def quick_dispense_stock(
    request: Request,
    data: QuickDispenseRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Quick dispense/use stock item via barcode scan.
    Decreases stock quantity.
    """
    from app.models import StockItem

    item = db.query(StockItem).filter(
        StockItem.barcode == data.barcode,
        StockItem.venue_id == current_user.venue_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.quantity < data.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Available: {item.quantity}"
        )

    old_quantity = item.quantity
    item.quantity -= data.quantity

    db.commit()

    return {
        "success": True,
        "item_id": item.id,
        "item_name": item.name,
        "old_quantity": old_quantity,
        "dispensed": data.quantity,
        "new_quantity": item.quantity,
        "reason": data.reason,
        "warning": "Low stock" if item.low_stock_threshold and item.quantity <= item.low_stock_threshold else None
    }


# =============================================================================
# DEVICE REGISTRATION
# =============================================================================

@router.post("/device/register", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def register_mobile_device(
    request: Request,
    device_id: str,
    device_name: str,
    device_type: str = "mobile_scanner",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Register a mobile scanning device.
    Required for offline sync and device tracking.
    """
    return IoTService.register_device(
        db=db,
        venue_id=current_user.venue_id,
        device_type=device_type,
        device_name=device_name,
        serial_number=device_id,
        location="mobile",
        configuration={"user_id": current_user.id}
    )


@router.get("/device/config", response_model=Dict[str, Any])
@limiter.limit("60/minute")
async def get_device_config(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get configuration for mobile scanning app.
    Includes zones, scan modes, and sync settings.
    """
    return {
        "venue_id": current_user.venue_id,
        "zones": ["warehouse", "kitchen", "bar", "storage", "receiving", "cold_storage"],
        "scan_modes": [
            {"id": "lookup", "name": "Stock Lookup", "icon": "search"},
            {"id": "receive", "name": "Receive Stock", "icon": "plus"},
            {"id": "dispense", "name": "Dispense", "icon": "minus"},
            {"id": "count", "name": "Inventory Count", "icon": "clipboard"},
            {"id": "transfer", "name": "Transfer", "icon": "arrow-right"}
        ],
        "sync_settings": {
            "auto_sync": True,
            "sync_interval_seconds": 30,
            "offline_max_scans": 1000,
            "compress_data": True
        },
        "scan_settings": {
            "vibrate_on_scan": True,
            "sound_on_scan": True,
            "continuous_scan": False,
            "scan_delay_ms": 500
        }
    }
