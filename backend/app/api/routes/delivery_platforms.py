"""
Delivery Platform Integration API Endpoints
UberEats, DoorDash, OpenTable, Resy integrations
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

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

@router.get("/orders")
async def get_all_delivery_orders(
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
async def get_all_reservations(
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
async def accept_platform_order(
    platform: str,
    request: AcceptOrderRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accept an order from a delivery platform
    """
    manager = get_delivery_manager()
    result = await manager.accept_order(platform, request.order_id, request.prep_time_minutes)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    # Sync order to local database in background
    background_tasks.add_task(_sync_delivery_order, db, platform, request.order_id)

    return {
        "success": True,
        "platform": platform,
        "order_id": request.order_id,
        "status": "accepted",
        "prep_time_minutes": request.prep_time_minutes
    }


@router.post("/orders/{platform}/cancel")
async def cancel_platform_order(
    platform: str,
    request: CancelOrderRequest,
    current_user=Depends(get_current_user)
):
    """
    Cancel an order from a delivery platform
    """
    manager = get_delivery_manager()
    result = await manager.cancel_order(platform, request.order_id, request.reason)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {
        "success": True,
        "platform": platform,
        "order_id": request.order_id,
        "status": "cancelled"
    }


@router.post("/reservations/{platform}/confirm")
async def confirm_platform_reservation(
    platform: str,
    request: ConfirmReservationRequest,
    current_user=Depends(get_current_user)
):
    """
    Confirm a reservation from a platform
    """
    manager = get_delivery_manager()
    result = await manager.confirm_reservation(platform, request.reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {
        "success": True,
        "platform": platform,
        "reservation_id": request.reservation_id,
        "status": "confirmed"
    }


# =============================================================================
# UBER EATS ENDPOINTS
# =============================================================================

@router.get("/ubereats/orders")
async def get_ubereats_orders(
    current_user=Depends(get_current_user)
):
    """Get active UberEats orders"""
    service = get_uber_eats_service()
    result = await service.get_active_orders()

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, "orders": result.data}


@router.post("/ubereats/orders/accept")
async def accept_ubereats_order(
    request: AcceptOrderRequest,
    current_user=Depends(get_current_user)
):
    """Accept an UberEats order"""
    service = get_uber_eats_service()
    result = await service.accept_order(request.order_id, request.prep_time_minutes)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/ubereats/orders/deny")
async def deny_ubereats_order(
    request: DenyOrderRequest,
    current_user=Depends(get_current_user)
):
    """Deny an UberEats order"""
    service = get_uber_eats_service()
    result = await service.deny_order(request.order_id, request.reason)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/ubereats/orders/status")
async def update_ubereats_status(
    request: UpdateStatusRequest,
    current_user=Depends(get_current_user)
):
    """Update UberEats order status"""
    service = get_uber_eats_service()
    result = await service.update_order_status(request.order_id, request.status)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/ubereats/store/status")
async def set_ubereats_store_status(
    request: StoreStatusRequest,
    current_user=Depends(get_current_user)
):
    """Set UberEats store online/offline"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    service = get_uber_eats_service()
    result = await service.set_store_status(request.is_open)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/ubereats/webhook")
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
async def get_doordash_orders(
    current_user=Depends(get_current_user)
):
    """Get active DoorDash orders"""
    service = get_doordash_service()
    result = await service.get_active_orders()

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, "orders": result.data}


@router.post("/doordash/orders/accept")
async def accept_doordash_order(
    request: AcceptOrderRequest,
    current_user=Depends(get_current_user)
):
    """Accept a DoorDash order"""
    service = get_doordash_service()
    result = await service.accept_order(request.order_id, request.prep_time_minutes)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/doordash/orders/cancel")
async def cancel_doordash_order(
    request: CancelOrderRequest,
    current_user=Depends(get_current_user)
):
    """Cancel a DoorDash order"""
    service = get_doordash_service()
    result = await service.cancel_order(request.order_id, request.reason)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/doordash/orders/status")
async def update_doordash_status(
    request: UpdateStatusRequest,
    current_user=Depends(get_current_user)
):
    """Update DoorDash order status"""
    service = get_doordash_service()
    result = await service.update_order_status(request.order_id, request.status)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/doordash/drive/quote")
async def get_doordash_quote(
    request: DeliveryQuoteRequest,
    current_user=Depends(get_current_user)
):
    """Get DoorDash Drive delivery quote"""
    from decimal import Decimal

    service = get_doordash_service()
    result = await service.get_delivery_quote(
        request.pickup_address,
        request.dropoff_address,
        Decimal(str(request.order_value))
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/doordash/drive/create")
async def create_doordash_delivery(
    request: CreateDeliveryRequest,
    current_user=Depends(get_current_user)
):
    """Create a DoorDash Drive delivery"""
    from decimal import Decimal

    service = get_doordash_service()
    result = await service.create_delivery(
        request.pickup_address,
        request.dropoff_address,
        request.dropoff_phone,
        Decimal(str(request.order_value)),
        request.items
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, "delivery": result.data}


@router.post("/doordash/webhook")
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
async def get_opentable_reservations(
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
async def get_opentable_reservation(
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
async def confirm_opentable_reservation(
    request: ConfirmReservationRequest,
    current_user=Depends(get_current_user)
):
    """Confirm an OpenTable reservation"""
    service = get_opentable_service()
    result = await service.confirm_reservation(request.reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/opentable/reservations/cancel")
async def cancel_opentable_reservation(
    request: CancelReservationRequest,
    current_user=Depends(get_current_user)
):
    """Cancel an OpenTable reservation"""
    service = get_opentable_service()
    result = await service.cancel_reservation(request.reservation_id, request.reason)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/opentable/reservations/seat")
async def seat_opentable_reservation(
    request: SeatReservationRequest,
    current_user=Depends(get_current_user)
):
    """Mark OpenTable reservation as seated"""
    service = get_opentable_service()
    result = await service.seat_reservation(request.reservation_id, request.table_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/opentable/reservations/complete")
async def complete_opentable_reservation(
    request: ConfirmReservationRequest,
    current_user=Depends(get_current_user)
):
    """Mark OpenTable reservation as completed"""
    service = get_opentable_service()
    result = await service.complete_reservation(request.reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/opentable/webhook")
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
async def get_resy_reservations(
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
async def get_resy_reservation(
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
async def confirm_resy_reservation(
    request: ConfirmReservationRequest,
    current_user=Depends(get_current_user)
):
    """Confirm a Resy reservation"""
    service = get_resy_service()
    result = await service.confirm_reservation(request.reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/resy/reservations/cancel")
async def cancel_resy_reservation(
    request: CancelReservationRequest,
    current_user=Depends(get_current_user)
):
    """Cancel a Resy reservation"""
    service = get_resy_service()
    result = await service.cancel_reservation(request.reservation_id, request.reason)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.post("/resy/reservations/seat")
async def seat_resy_reservation(
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
async def resy_noshow(
    request: ConfirmReservationRequest,
    current_user=Depends(get_current_user)
):
    """Mark Resy reservation as no-show"""
    service = get_resy_service()
    result = await service.no_show(request.reservation_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, **result.data}


@router.get("/resy/availability")
async def get_resy_availability(
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
async def get_platform_info():
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
