"""
Delivery Platform Integration API Endpoints
UberEats, DoorDash, OpenTable, Resy integrations
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.core.rbac import get_current_user
from app.services.delivery_integrations import (
    get_delivery_manager,
    get_uber_eats_service,
    get_doordash_service,
    get_opentable_service,
    get_resy_service
)


router = APIRouter(tags=["Delivery Platform Integrations"])
logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMAS
# =============================================================================

class AcceptOrderRequest(BaseModel):
    order_id: str
    prep_time_minutes: int = Field(default=20, ge=5, le=120)


class DenyOrderRequest(BaseModel):
    order_id: str
    reason: str


class CancelOrderRequest(BaseModel):
    order_id: str
    reason: str


class UpdateStatusRequest(BaseModel):
    order_id: str
    status: str = Field(..., description="preparing, ready_for_pickup")


class ConfirmReservationRequest(BaseModel):
    reservation_id: str


class CancelReservationRequest(BaseModel):
    reservation_id: str
    reason: str


class SeatReservationRequest(BaseModel):
    reservation_id: str
    table_id: int


class StoreStatusRequest(BaseModel):
    is_open: bool


class DeliveryQuoteRequest(BaseModel):
    pickup_address: str
    dropoff_address: str
    order_value: float


class CreateDeliveryRequest(BaseModel):
    pickup_address: str
    dropoff_address: str
    dropoff_phone: str
    order_value: float
    items: List[dict]


# =============================================================================
# UNIFIED ENDPOINTS
# =============================================================================

@router.get("/")
@limiter.limit("60/minute")
async def get_delivery_platforms_root(request: Request, db: Session = Depends(get_db)):
    """Delivery platforms overview."""
    return {"module": "delivery-platforms", "status": "active", "platforms": ["ubereats", "doordash", "opentable"], "endpoints": ["/orders", "/reservations"]}


@router.get("/orders")
@limiter.limit("60/minute")
async def get_all_delivery_orders(
    request: Request,
    current_user=Depends(get_current_user)
):
    """
    Get all active orders from all delivery platforms
    """
    manager = get_delivery_manager()
    orders = await manager.get_all_active_orders()

    return {
        "success": True,
        "orders": orders,
        "total_count": sum(len(v) for v in orders.values())
    }


@router.get("/reservations")
@limiter.limit("60/minute")
async def get_all_reservations(
    request: Request,
    date: str,
    current_user=Depends(get_current_user)
):
    """
    Get all reservations from all platforms for a date
    """
    manager = get_delivery_manager()
    reservations = await manager.get_all_reservations(date)

    return {
        "success": True,
        "date": date,
        "reservations": reservations,
        "total_count": sum(len(v) for v in reservations.values())
    }


@router.post("/orders/{platform}/accept")
@limiter.limit("30/minute")
async def accept_platform_order(
    request: Request,
    platform: str,
    body: AcceptOrderRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accept an order from a delivery platform
    """
    manager = get_delivery_manager()
    result = await manager.accept_order(platform, body.order_id, body.prep_time_minutes)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    # Sync order to local database in background
    background_tasks.add_task(_sync_delivery_order, db, platform, body.order_id)

    return {
        "success": True,
        "platform": platform,
        "order_id": body.order_id,
        "status": "accepted",
        "prep_time_minutes": body.prep_time_minutes
    }


@router.post("/orders/{platform}/cancel")
@limiter.limit("30/minute")
async def cancel_platform_order(
    request: Request,
    platform: str,
    body: CancelOrderRequest,
    current_user=Depends(get_current_user)
):
    """
    Cancel an order from a delivery platform
    """
    manager = get_delivery_manager()
    result = await manager.cancel_order(platform, body.order_id, body.reason)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {
        "success": True,
        "platform": platform,
        "order_id": body.order_id,
        "status": "cancelled"
    }


@router.post("/reservations/{platform}/confirm")
@limiter.limit("30/minute")
async def confirm_platform_reservation(
    request: Request,
    platform: str,
    body: ConfirmReservationRequest,
    current_user=Depends(get_current_user)
):
    """
    Confirm a reservation from a platform
    """
    manager = get_delivery_manager()
    result = await manager.confirm_reservation(platform, body.reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {
        "success": True,
        "platform": platform,
        "reservation_id": body.reservation_id,
        "status": "confirmed"
    }


# =============================================================================
# UBER EATS ENDPOINTS
# =============================================================================

@router.get("/ubereats/orders")
@limiter.limit("60/minute")
async def get_ubereats_orders(
    request: Request,
    current_user=Depends(get_current_user)
):
    """Get active UberEats orders"""
    service = get_uber_eats_service()
    result = await service.get_active_orders()

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, "orders": result.data}


@router.post("/ubereats/orders/accept")
@limiter.limit("30/minute")
async def accept_ubereats_order(
    request: Request,
    body: AcceptOrderRequest,
    current_user=Depends(get_current_user)
):
    """Accept an UberEats order"""
    service = get_uber_eats_service()
    result = await service.accept_order(body.order_id, body.prep_time_minutes)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/ubereats/orders/deny")
@limiter.limit("30/minute")
async def deny_ubereats_order(
    request: Request,
    body: DenyOrderRequest,
    current_user=Depends(get_current_user)
):
    """Deny an UberEats order"""
    service = get_uber_eats_service()
    result = await service.deny_order(body.order_id, body.reason)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/ubereats/orders/status")
@limiter.limit("30/minute")
async def update_ubereats_status(
    request: Request,
    body: UpdateStatusRequest,
    current_user=Depends(get_current_user)
):
    """Update UberEats order status"""
    service = get_uber_eats_service()
    result = await service.update_order_status(body.order_id, body.status)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/ubereats/store/status")
@limiter.limit("30/minute")
async def set_ubereats_store_status(
    request: Request,
    body: StoreStatusRequest,
    current_user=Depends(get_current_user)
):
    """Set UberEats store online/offline"""
    if current_user.role not in ["owner", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    service = get_uber_eats_service()
    result = await service.set_store_status(body.is_open)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/ubereats/webhook")
@limiter.limit("30/minute")
async def ubereats_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle UberEats webhooks"""
    try:
        body = await request.body()
        signature = request.headers.get("X-Uber-Signature", "")

        service = get_uber_eats_service()
        if not service.verify_webhook(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

        payload = await request.json()
        order = service.parse_webhook(payload)

        if order:
            background_tasks.add_task(_process_delivery_order, db, order)
            logger.info(f"UberEats webhook processed: {payload.get('event_type')}")

        return {"status": "OK"}

    except Exception as e:
        logger.error(f"UberEats webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# =============================================================================
# DOORDASH ENDPOINTS
# =============================================================================

@router.get("/doordash/orders")
@limiter.limit("60/minute")
async def get_doordash_orders(
    request: Request,
    current_user=Depends(get_current_user)
):
    """Get active DoorDash orders"""
    service = get_doordash_service()
    result = await service.get_active_orders()

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, "orders": result.data}


@router.post("/doordash/orders/accept")
@limiter.limit("30/minute")
async def accept_doordash_order(
    request: Request,
    body: AcceptOrderRequest,
    current_user=Depends(get_current_user)
):
    """Accept a DoorDash order"""
    service = get_doordash_service()
    result = await service.accept_order(body.order_id, body.prep_time_minutes)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/doordash/orders/cancel")
@limiter.limit("30/minute")
async def cancel_doordash_order(
    request: Request,
    body: CancelOrderRequest,
    current_user=Depends(get_current_user)
):
    """Cancel a DoorDash order"""
    service = get_doordash_service()
    result = await service.cancel_order(body.order_id, body.reason)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/doordash/orders/status")
@limiter.limit("30/minute")
async def update_doordash_status(
    request: Request,
    body: UpdateStatusRequest,
    current_user=Depends(get_current_user)
):
    """Update DoorDash order status"""
    service = get_doordash_service()
    result = await service.update_order_status(body.order_id, body.status)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/doordash/drive/quote")
@limiter.limit("30/minute")
async def get_doordash_quote(
    request: Request,
    body: DeliveryQuoteRequest,
    current_user=Depends(get_current_user)
):
    """Get DoorDash Drive delivery quote"""
    from decimal import Decimal

    service = get_doordash_service()
    result = await service.get_delivery_quote(
        body.pickup_address,
        body.dropoff_address,
        Decimal(str(body.order_value))
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/doordash/drive/create")
@limiter.limit("30/minute")
async def create_doordash_delivery(
    request: Request,
    body: CreateDeliveryRequest,
    current_user=Depends(get_current_user)
):
    """Create a DoorDash Drive delivery"""
    from decimal import Decimal

    service = get_doordash_service()
    result = await service.create_delivery(
        body.pickup_address,
        body.dropoff_address,
        body.dropoff_phone,
        Decimal(str(body.order_value)),
        body.items
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, "delivery": result.data}


@router.post("/doordash/webhook")
@limiter.limit("30/minute")
async def doordash_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle DoorDash webhooks"""
    try:
        body = await request.body()
        signature = request.headers.get("X-DoorDash-Signature", "")

        service = get_doordash_service()
        if not service.verify_webhook(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

        payload = await request.json()
        order = service.parse_webhook(payload)

        if order:
            background_tasks.add_task(_process_delivery_order, db, order)
            logger.info(f"DoorDash webhook processed: {payload.get('event_type')}")

        return {"status": "OK"}

    except Exception as e:
        logger.error(f"DoorDash webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# =============================================================================
# OPENTABLE ENDPOINTS
# =============================================================================

@router.get("/opentable/reservations")
@limiter.limit("60/minute")
async def get_opentable_reservations(
    request: Request,
    date: Optional[str] = None,
    status: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Get OpenTable reservations"""
    service = get_opentable_service()
    result = await service.get_reservations(date=date, status=status)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, "reservations": result.data}


@router.get("/opentable/reservations/{reservation_id}")
@limiter.limit("60/minute")
async def get_opentable_reservation(
    request: Request,
    reservation_id: str,
    current_user=Depends(get_current_user)
):
    """Get a specific OpenTable reservation"""
    service = get_opentable_service()
    result = await service.get_reservation(reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, "reservation": result.data}


@router.post("/opentable/reservations/confirm")
@limiter.limit("30/minute")
async def confirm_opentable_reservation(
    request: Request,
    body: ConfirmReservationRequest,
    current_user=Depends(get_current_user)
):
    """Confirm an OpenTable reservation"""
    service = get_opentable_service()
    result = await service.confirm_reservation(body.reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/opentable/reservations/cancel")
@limiter.limit("30/minute")
async def cancel_opentable_reservation(
    request: Request,
    body: CancelReservationRequest,
    current_user=Depends(get_current_user)
):
    """Cancel an OpenTable reservation"""
    service = get_opentable_service()
    result = await service.cancel_reservation(body.reservation_id, body.reason)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/opentable/reservations/seat")
@limiter.limit("30/minute")
async def seat_opentable_reservation(
    request: Request,
    body: SeatReservationRequest,
    current_user=Depends(get_current_user)
):
    """Mark OpenTable reservation as seated"""
    service = get_opentable_service()
    result = await service.seat_reservation(body.reservation_id, body.table_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/opentable/reservations/complete")
@limiter.limit("30/minute")
async def complete_opentable_reservation(
    request: Request,
    body: ConfirmReservationRequest,
    current_user=Depends(get_current_user)
):
    """Mark OpenTable reservation as completed"""
    service = get_opentable_service()
    result = await service.complete_reservation(body.reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/opentable/webhook")
@limiter.limit("30/minute")
async def opentable_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle OpenTable webhooks"""
    try:
        body = await request.body()
        signature = request.headers.get("X-OpenTable-Signature", "")

        service = get_opentable_service()
        if not service.verify_webhook(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

        payload = await request.json()
        reservation = service.parse_webhook(payload)

        if reservation:
            background_tasks.add_task(_process_reservation, db, reservation)
            logger.info(f"OpenTable webhook processed: {payload.get('event_type')}")

        return {"status": "OK"}

    except Exception as e:
        logger.error(f"OpenTable webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# =============================================================================
# RESY ENDPOINTS
# =============================================================================

@router.get("/resy/reservations")
@limiter.limit("60/minute")
async def get_resy_reservations(
    request: Request,
    date: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Get Resy reservations"""
    service = get_resy_service()
    result = await service.get_reservations(date=date)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, "reservations": result.data}


@router.get("/resy/reservations/{reservation_id}")
@limiter.limit("60/minute")
async def get_resy_reservation(
    request: Request,
    reservation_id: str,
    current_user=Depends(get_current_user)
):
    """Get a specific Resy reservation"""
    service = get_resy_service()
    result = await service.get_reservation(reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, "reservation": result.data}


@router.post("/resy/reservations/confirm")
@limiter.limit("30/minute")
async def confirm_resy_reservation(
    request: Request,
    body: ConfirmReservationRequest,
    current_user=Depends(get_current_user)
):
    """Confirm a Resy reservation"""
    service = get_resy_service()
    result = await service.confirm_reservation(body.reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/resy/reservations/cancel")
@limiter.limit("30/minute")
async def cancel_resy_reservation(
    request: Request,
    body: CancelReservationRequest,
    current_user=Depends(get_current_user)
):
    """Cancel a Resy reservation"""
    service = get_resy_service()
    result = await service.cancel_reservation(body.reservation_id, body.reason)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/resy/reservations/seat")
@limiter.limit("30/minute")
async def seat_resy_reservation(
    request: Request,
    reservation_id: str,
    table_number: str,
    current_user=Depends(get_current_user)
):
    """Mark Resy reservation as seated"""
    service = get_resy_service()
    result = await service.seat_reservation(reservation_id, table_number)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/resy/reservations/noshow")
@limiter.limit("30/minute")
async def resy_noshow(
    request: Request,
    body: ConfirmReservationRequest,
    current_user=Depends(get_current_user)
):
    """Mark Resy reservation as no-show"""
    service = get_resy_service()
    result = await service.no_show(body.reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.get("/resy/availability")
@limiter.limit("60/minute")
async def get_resy_availability(
    request: Request,
    date: str,
    party_size: int = 2,
    current_user=Depends(get_current_user)
):
    """Get Resy availability for a date"""
    service = get_resy_service()
    result = await service.get_availability(date, party_size)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/resy/webhook")
@limiter.limit("30/minute")
async def resy_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle Resy webhooks"""
    try:
        body = await request.body()
        signature = request.headers.get("X-Resy-Signature", "")

        service = get_resy_service()
        if not service.verify_webhook(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

        payload = await request.json()
        reservation = service.parse_webhook(payload)

        if reservation:
            background_tasks.add_task(_process_reservation, db, reservation)
            logger.info(f"Resy webhook processed: {payload.get('type')}")

        return {"status": "OK"}

    except Exception as e:
        logger.error(f"Resy webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# =============================================================================
# PLATFORM INFO
# =============================================================================

@router.get("/platforms")
@limiter.limit("60/minute")
async def get_platform_info(request: Request):
    """Get available delivery and reservation platforms"""
    return {
        "delivery_platforms": [
            {
                "id": "uber_eats",
                "name": "UberEats",
                "type": "delivery",
                "features": ["orders", "menu_sync", "store_status"],
                "webhook_url": "/api/v1/delivery-platforms/ubereats/webhook"
            },
            {
                "id": "doordash",
                "name": "DoorDash",
                "type": "delivery",
                "features": ["orders", "drive", "quotes"],
                "webhook_url": "/api/v1/delivery-platforms/doordash/webhook"
            }
        ],
        "reservation_platforms": [
            {
                "id": "opentable",
                "name": "OpenTable",
                "type": "reservation",
                "features": ["reservations", "availability", "guest_management"],
                "webhook_url": "/api/v1/delivery-platforms/opentable/webhook"
            },
            {
                "id": "resy",
                "name": "Resy",
                "type": "reservation",
                "features": ["reservations", "availability", "noshow"],
                "webhook_url": "/api/v1/delivery-platforms/resy/webhook"
            }
        ]
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _sync_delivery_order(db: Session, platform: str, order_id: str):
    """Sync delivery order to local database"""
    try:
        # Get order details from platform
        manager = get_delivery_manager()
        service = manager.get_service(platform)

        if service and hasattr(service, 'get_active_orders'):
            result = await service.get_active_orders()
            if result.success:
                for order in result.data:
                    if order.id == order_id or order.external_id == order_id:
                        await _process_delivery_order(db, order)
                        break

    except Exception as e:
        logger.error(f"Failed to sync delivery order: {e}")


async def _process_delivery_order(db: Session, order):
    """Process incoming delivery order"""
    try:
        from app.models import Order, Customer

        # Check if order already exists
        existing = db.query(Order).filter(
            Order.external_order_id == order.external_id
        ).first()

        if existing:
            # Update status
            existing.status = order.status
            db.commit()
            return

        # Create or find customer
        customer = None
        if order.customer_phone:
            customer = db.query(Customer).filter(
                Customer.phone == order.customer_phone
            ).first()

            if not customer:
                customer = Customer(
                    name=order.customer_name,
                    phone=order.customer_phone,
                    source=order.platform
                )
                db.add(customer)
                db.flush()

        # Create order
        new_order = Order(
            venue_id=1,  # Default venue
            customer_id=customer.id if customer else None,
            order_type="delivery",
            status=order.status,
            source=order.platform,
            external_order_id=order.external_id,
            subtotal=float(order.subtotal),
            tax_amount=float(order.tax),
            delivery_fee=float(order.delivery_fee),
            tip_amount=float(order.tip),
            total_amount=float(order.total),
            notes=order.special_instructions,
            delivery_address=order.customer_address
        )
        db.add(new_order)
        db.commit()

        logger.info(f"Created order from {order.platform}: {new_order.id}")

    except Exception as e:
        logger.error(f"Failed to process delivery order: {e}")
        db.rollback()


async def _process_reservation(db: Session, reservation):
    """Process incoming reservation"""
    try:
        from app.models import Reservation as ReservationModel, Customer

        # Check if reservation already exists
        existing = db.query(ReservationModel).filter(
            ReservationModel.external_id == reservation.external_id
        ).first()

        if existing:
            existing.status = reservation.status
            db.commit()
            return

        # Create or find customer
        customer = None
        if reservation.customer_email:
            customer = db.query(Customer).filter(
                Customer.email == reservation.customer_email
            ).first()

            if not customer:
                customer = Customer(
                    name=reservation.customer_name,
                    email=reservation.customer_email,
                    phone=reservation.customer_phone,
                    source=reservation.platform
                )
                db.add(customer)
                db.flush()

        # Create reservation
        new_reservation = ReservationModel(
            venue_id=1,
            customer_id=customer.id if customer else None,
            customer_name=reservation.customer_name,
            customer_email=reservation.customer_email,
            customer_phone=reservation.customer_phone,
            party_size=reservation.party_size,
            date=reservation.date,
            time=reservation.time,
            status=reservation.status,
            source=reservation.platform,
            external_id=reservation.external_id,
            special_requests=reservation.special_requests
        )
        db.add(new_reservation)
        db.commit()

        logger.info(f"Created reservation from {reservation.platform}: {new_reservation.id}")

    except Exception as e:
        logger.error(f"Failed to process reservation: {e}")
        db.rollback()
