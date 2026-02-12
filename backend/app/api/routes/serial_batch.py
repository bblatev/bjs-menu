"""
Serial/Batch Numbers API Endpoints
Complete tracking, warranty management, and expiry handling
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from app.db.session import get_db
from app.services.serial_batch_service import SerialBatchService
from pydantic import BaseModel, Field



router = APIRouter()


# ==================== SCHEMAS ====================

class SerialNumberCreate(BaseModel):
    """Create new serial number tracking"""
    stock_item_id: int
    serial_number: str = Field(..., min_length=1, max_length=100)
    batch_number: Optional[str] = None
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    supplier_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    warranty_months: Optional[int] = None
    current_location: Optional[str] = None
    notes: Optional[str] = None


class SerialNumberResponse(BaseModel):
    """Serial number details"""
    id: int
    stock_item_id: int
    stock_item_name: str
    serial_number: str
    batch_number: Optional[str]
    manufacture_date: Optional[date]
    expiry_date: Optional[date]
    supplier_name: Optional[str]
    warranty_months: Optional[int]
    warranty_expires: Optional[date]
    status: str
    current_location: Optional[str]
    sold_to_customer: Optional[str]
    sold_date: Optional[datetime]
    created_at: datetime


class SerialHistoryEntry(BaseModel):
    """History event for serial number"""
    id: int
    event_type: str
    event_date: datetime
    from_location: Optional[str]
    to_location: Optional[str]
    staff_name: Optional[str]
    customer_name: Optional[str]
    notes: Optional[str]


class BatchCreate(BaseModel):
    """Create batch tracking"""
    batch_number: str = Field(..., min_length=1, max_length=50)
    stock_item_id: int
    quantity_received: int = Field(..., gt=0)
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    supplier_id: Optional[int] = None
    auto_writeoff: bool = True


class BatchResponse(BaseModel):
    """Batch details"""
    id: int
    batch_number: str
    stock_item_id: int
    stock_item_name: str
    quantity_received: int
    quantity_remaining: int
    manufacture_date: Optional[date]
    expiry_date: Optional[date]
    days_until_expiry: Optional[int]
    supplier_name: Optional[str]
    status: str
    auto_writeoff: bool
    received_date: datetime


class WriteoffRequest(BaseModel):
    """Batch writeoff request"""
    quantity: Optional[int] = None  # None = writeoff all
    reason: str = Field(..., min_length=1)
    staff_id: int


# ==================== SERIAL NUMBER ENDPOINTS ====================

@router.post(
    "/serial-numbers",
    response_model=SerialNumberResponse,
    summary="Register serial number",
    description="Register a new item with serial number for complete tracking"
)
def create_serial_number(
    data: SerialNumberCreate,
    db: Session = Depends(get_db)
):
    """
    Register new serial number
    
    Use for:
    - High-value items (electronics, alcohol)
    - Items with warranty
    - Items requiring traceability
    - Regulated products
    """
    service = SerialBatchService(db)
    
    try:
        serial = service.register_serial_number(
            stock_item_id=data.stock_item_id,
            serial_number=data.serial_number,
            batch_number=data.batch_number,
            manufacture_date=data.manufacture_date,
            expiry_date=data.expiry_date,
            supplier_id=data.supplier_id,
            purchase_order_id=data.purchase_order_id,
            warranty_months=data.warranty_months,
            current_location=data.current_location,
            notes=data.notes
        )
        
        return serial
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/serial-numbers/{serial_number}",
    response_model=SerialNumberResponse,
    summary="Get serial number",
    description="Get complete details for a serial number"
)
def get_serial_number(
    serial_number: str,
    db: Session = Depends(get_db)
):
    """
    Get serial number details
    
    Returns complete information including:
    - Current status and location
    - Warranty information
    - Purchase/sale details
    - Supplier information
    """
    service = SerialBatchService(db)
    serial = service.get_serial_number(serial_number)
    
    if not serial:
        raise HTTPException(
            status_code=404,
            detail=f"Serial number {serial_number} not found"
        )
    
    return serial


@router.get(
    "/serial-numbers/{serial_number}/history",
    response_model=List[SerialHistoryEntry],
    summary="Get serial number history",
    description="Get complete history of events for a serial number"
)
def get_serial_history(
    serial_number: str,
    db: Session = Depends(get_db)
):
    """
    Get complete history for serial number
    
    Returns chronological list of all events:
    - Received from supplier
    - Moved between locations
    - Sold to customer
    - Returned
    - Warranty claims
    - Status changes
    """
    service = SerialBatchService(db)
    history = service.get_serial_history(serial_number)
    
    if history is None:
        raise HTTPException(
            status_code=404,
            detail=f"Serial number {serial_number} not found"
        )
    
    return history


@router.get(
    "/serial-numbers",
    response_model=List[SerialNumberResponse],
    summary="List serial numbers",
    description="List serial numbers with filters"
)
def list_serial_numbers(
    stock_item_id: Optional[int] = None,
    status: Optional[str] = None,
    expiring_days: Optional[int] = Query(None, description="Find items expiring within N days"),
    warranty_expiring_days: Optional[int] = Query(None, description="Find items with warranty expiring within N days"),
    supplier_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List serial numbers with filters
    
    Filters:
    - stock_item_id: Items of specific type
    - status: in_stock, sold, returned, expired, destroyed
    - expiring_days: Items expiring soon
    - warranty_expiring_days: Warranties expiring soon
    - supplier_id: From specific supplier
    """
    service = SerialBatchService(db)
    
    serials = service.list_serial_numbers(
        stock_item_id=stock_item_id,
        status=status,
        expiring_days=expiring_days,
        warranty_expiring_days=warranty_expiring_days,
        supplier_id=supplier_id,
        skip=skip,
        limit=limit
    )
    
    return serials


@router.patch(
    "/serial-numbers/{serial_number}/status",
    response_model=SerialNumberResponse,
    summary="Update serial number status",
    description="Update status of a serial number"
)
def update_serial_status(
    serial_number: str,
    status: str = Query(..., description="New status: in_stock, sold, returned, expired, destroyed"),
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Update serial number status
    
    Valid statuses:
    - in_stock: Available in inventory
    - sold: Sold to customer
    - returned: Returned by customer
    - expired: Past expiry date
    - destroyed: Disposed/written off
    """
    valid_statuses = ['in_stock', 'sold', 'returned', 'expired', 'destroyed']
    
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    service = SerialBatchService(db)
    
    try:
        serial = service.update_serial_status(
            serial_number=serial_number,
            new_status=status,
            reason=reason
        )
        
        return serial
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/serial-numbers/{serial_number}/move",
    response_model=SerialNumberResponse,
    summary="Move serial number",
    description="Move item to different location"
)
def move_serial_number(
    serial_number: str,
    to_location: str,
    staff_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Move serial number to new location
    
    Creates history entry for tracking
    """
    service = SerialBatchService(db)
    
    try:
        serial = service.move_serial_number(
            serial_number=serial_number,
            to_location=to_location,
            staff_id=staff_id,
            notes=notes
        )
        
        return serial
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== BATCH TRACKING ENDPOINTS ====================

@router.post(
    "/batches",
    response_model=BatchResponse,
    summary="Create batch",
    description="Create new batch tracking for items with expiry"
)
def create_batch(
    data: BatchCreate,
    db: Session = Depends(get_db)
):
    """
    Create batch tracking
    
    Use for:
    - Food items with expiry dates
    - Ingredients with shelf life
    - Products with best-before dates
    - Items requiring FIFO/FEFO management
    """
    service = SerialBatchService(db)
    
    try:
        batch = service.create_batch(
            batch_number=data.batch_number,
            stock_item_id=data.stock_item_id,
            quantity_received=data.quantity_received,
            manufacture_date=data.manufacture_date,
            expiry_date=data.expiry_date,
            supplier_id=data.supplier_id,
            auto_writeoff=data.auto_writeoff
        )
        
        return batch
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/batches",
    response_model=List[BatchResponse],
    summary="List batches",
    description="List batches with filters"
)
def list_batches(
    stock_item_id: Optional[int] = None,
    status: Optional[str] = None,
    expiring_days: Optional[int] = Query(None, description="Find batches expiring within N days"),
    supplier_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List batches with filters
    
    Filters:
    - stock_item_id: Batches of specific item
    - status: active, depleted, expired
    - expiring_days: Batches expiring soon (urgent action needed)
    - supplier_id: From specific supplier
    """
    service = SerialBatchService(db)
    
    batches = service.list_batches(
        stock_item_id=stock_item_id,
        status=status,
        expiring_days=expiring_days,
        supplier_id=supplier_id,
        skip=skip,
        limit=limit
    )
    
    return batches


@router.get(
    "/batches/expiring",
    response_model=List[BatchResponse],
    summary="Get expiring batches",
    description="Get batches that are expiring soon and need action"
)
def get_expiring_batches(
    days: int = Query(7, description="Days until expiry"),
    venue_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get batches expiring soon
    
    Use for:
    - Daily expiry checks
    - Discount planning (sell before expiry)
    - Waste prevention
    - Inventory management
    
    Default: 7 days (1 week warning)
    """
    service = SerialBatchService(db)
    
    batches = service.get_expiring_batches(days=days, venue_id=venue_id)
    
    return batches


@router.post(
    "/batches/{batch_id}/writeoff",
    summary="Writeoff batch",
    description="Manually writeoff expired or damaged batch"
)
def writeoff_batch(
    batch_id: int,
    data: WriteoffRequest,
    db: Session = Depends(get_db)
):
    """
    Writeoff batch (manual)
    
    Use for:
    - Expired items
    - Damaged goods
    - Quality issues
    - Spoilage
    
    If quantity not specified, writes off entire batch
    """
    service = SerialBatchService(db)
    
    try:
        result = service.writeoff_batch(
            batch_id=batch_id,
            quantity=data.quantity,
            reason=data.reason,
            staff_id=data.staff_id
        )
        
        return {
            "success": True,
            "batch_id": batch_id,
            "quantity_written_off": result['quantity'],
            "reason": data.reason,
            "message": f"Batch {result['batch_number']} written off"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/batches/auto-expire",
    summary="Run auto-expiry",
    description="Automatically expire all batches past expiry date"
)
def run_auto_expire(
    db: Session = Depends(get_db)
):
    """
    Run automatic expiry process
    
    Expires all batches with:
    - expiry_date in the past
    - auto_writeoff = true
    - status = active
    
    This should be run daily (e.g., via cron job)
    """
    service = SerialBatchService(db)
    
    result = service.auto_expire_batches()
    
    return {
        "success": True,
        "expired_count": result['count'],
        "batches_expired": result['batches'],
        "message": f"Expired {result['count']} batches"
    }


@router.get(
    "/batches/{batch_number}/items",
    summary="Get batch items",
    description="Get all items in a specific batch"
)
def get_batch_items(
    batch_number: str,
    db: Session = Depends(get_db)
):
    """
    Get all items in a batch
    
    Returns list of serial numbers if batch has individual tracking
    """
    service = SerialBatchService(db)
    
    items = service.get_batch_items(batch_number)
    
    if items is None:
        raise HTTPException(
            status_code=404,
            detail=f"Batch {batch_number} not found"
        )
    
    return {
        "batch_number": batch_number,
        "items": items
    }


# ==================== REPORTING ====================

@router.get(
    "/serial-numbers/warranty/expiring",
    summary="Get expiring warranties",
    description="Get items with warranties expiring soon"
)
def get_expiring_warranties(
    days: int = Query(30, description="Days until warranty expiry"),
    db: Session = Depends(get_db)
):
    """
    Get items with warranties expiring soon
    
    Use for:
    - Proactive customer notifications
    - Extended warranty offers
    - Customer service
    """
    service = SerialBatchService(db)
    
    items = service.get_expiring_warranties(days)
    
    return {
        "count": len(items),
        "days": days,
        "items": items
    }


@router.get(
    "/batches/report",
    summary="Get batch report",
    description="Get comprehensive batch tracking report"
)
def get_batch_report(
    venue_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Get batch tracking report
    
    Returns:
    - Total batches
    - Active batches
    - Expired batches
    - Expiring soon
    - Total value at risk
    """
    service = SerialBatchService(db)
    
    report = service.get_batch_report(
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return report
