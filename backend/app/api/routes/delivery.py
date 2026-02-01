"""Delivery Aggregator routes - DoorDash/Uber Eats style."""

from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Query, Request, Header

from app.db.session import DbSession
from app.models.delivery import (
    DeliveryIntegration, DeliveryOrder, DeliveryPlatformMapping,
    DeliveryPlatform, DeliveryOrderStatus, ItemAvailability, MenuSync
)
from app.services.delivery_service import (
    DeliveryAggregatorService, MenuSyncService,
    DeliveryWebhookHandler, DeliveryReportingService
)
from app.schemas.delivery import (
    DeliveryIntegrationCreate, DeliveryIntegrationUpdate, DeliveryIntegrationResponse,
    DeliveryOrderResponse, DeliveryOrderStatusUpdate,
    DeliveryOrderAccept, DeliveryOrderReject,
    MenuSyncRequest, MenuSyncResponse,
    ItemAvailabilityUpdate, ItemAvailabilityResponse, BulkAvailabilityUpdate,
    PlatformMappingCreate, PlatformMappingResponse,
    WebhookResponse,
    DeliverySummary, DeliveryPerformance
)

router = APIRouter()


# Root endpoint

@router.get("/")
def get_delivery_status(db: DbSession):
    """Get delivery aggregator status overview."""
    service = DeliveryAggregatorService(db)
    integrations = service.get_all_integrations()
    active_count = len([i for i in integrations if i.is_active])

    return {
        "status": "active" if active_count > 0 else "inactive",
        "total_integrations": len(integrations),
        "active_integrations": active_count,
        "platforms": ["uber_eats", "doordash", "wolt", "glovo", "deliveroo"],
        "pending_orders": 0,
    }


# Integrations

@router.get("/integrations/", response_model=List[DeliveryIntegrationResponse])
def list_integrations(
    db: DbSession,
    location_id: Optional[int] = None,
):
    """List delivery platform integrations."""
    service = DeliveryAggregatorService(db)
    return service.get_all_integrations(location_id)


@router.get("/integrations/{integration_id}", response_model=DeliveryIntegrationResponse)
def get_integration(db: DbSession, integration_id: int):
    """Get integration by ID."""
    integration = db.query(DeliveryIntegration).filter(
        DeliveryIntegration.id == integration_id
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


@router.post("/integrations/", response_model=DeliveryIntegrationResponse)
def create_integration(
    db: DbSession,
    integration: DeliveryIntegrationCreate,
):
    """Create a new delivery platform integration."""
    db_integration = DeliveryIntegration(**integration.model_dump())
    db.add(db_integration)
    db.commit()
    db.refresh(db_integration)
    return db_integration


@router.put("/integrations/{integration_id}", response_model=DeliveryIntegrationResponse)
def update_integration(
    db: DbSession,
    integration_id: int,
    integration: DeliveryIntegrationUpdate,
):
    """Update an integration."""
    db_integration = db.query(DeliveryIntegration).filter(
        DeliveryIntegration.id == integration_id
    ).first()
    if not db_integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    for key, value in integration.model_dump(exclude_unset=True).items():
        setattr(db_integration, key, value)

    db.commit()
    db.refresh(db_integration)
    return db_integration


@router.delete("/integrations/{integration_id}")
def delete_integration(db: DbSession, integration_id: int):
    """Deactivate an integration."""
    integration = db.query(DeliveryIntegration).filter(
        DeliveryIntegration.id == integration_id
    ).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration.is_active = False
    db.commit()
    return {"status": "deactivated"}


# Orders

@router.get("/orders/", response_model=List[DeliveryOrderResponse])
def list_orders(
    db: DbSession,
    location_id: Optional[int] = None,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
):
    """List delivery orders."""
    query = db.query(DeliveryOrder)

    if location_id:
        query = query.filter(DeliveryOrder.location_id == location_id)
    if platform:
        query = query.filter(DeliveryOrder.platform == platform)
    if status:
        query = query.filter(DeliveryOrder.status == status)
    if date_from:
        query = query.filter(DeliveryOrder.received_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(DeliveryOrder.received_at <= datetime.combine(date_to, datetime.max.time()))

    return query.order_by(DeliveryOrder.received_at.desc()).offset(skip).limit(limit).all()


@router.get("/orders/{order_id}", response_model=DeliveryOrderResponse)
def get_order(db: DbSession, order_id: int):
    """Get delivery order by ID."""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/orders/{order_id}/accept", response_model=DeliveryOrderResponse)
async def accept_order(
    db: DbSession,
    order_id: int,
    accept: DeliveryOrderAccept,
):
    """Accept a delivery order."""
    service = DeliveryAggregatorService(db)

    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.estimated_prep_minutes = accept.prep_time_minutes

    order = await service.update_order_status(order_id, DeliveryOrderStatus.CONFIRMED)
    return order


@router.post("/orders/{order_id}/reject")
async def reject_order(
    db: DbSession,
    order_id: int,
    reject: DeliveryOrderReject,
):
    """Reject a delivery order."""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.rejection_reason = reject.reason
    order.status = DeliveryOrderStatus.CANCELLED
    db.commit()

    return {"status": "rejected", "reason": reject.reason}


@router.post("/orders/{order_id}/status", response_model=DeliveryOrderResponse)
async def update_order_status(
    db: DbSession,
    order_id: int,
    status_update: DeliveryOrderStatusUpdate,
):
    """Update delivery order status."""
    service = DeliveryAggregatorService(db)
    try:
        order = await service.update_order_status(order_id, status_update.status)
        return order
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/orders/{order_id}/ready", response_model=DeliveryOrderResponse)
async def mark_order_ready(db: DbSession, order_id: int):
    """Mark order as ready for pickup."""
    service = DeliveryAggregatorService(db)
    try:
        order = await service.update_order_status(order_id, DeliveryOrderStatus.READY_FOR_PICKUP)
        return order
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Menu Sync

@router.post("/menu/sync", response_model=MenuSyncResponse)
async def sync_menu(db: DbSession, request: MenuSyncRequest):
    """Sync menu to a delivery platform."""
    service = MenuSyncService(db)
    result = await service.sync_menu_to_platform(
        integration_id=request.integration_id,
        full_sync=request.full_sync
    )
    return result


@router.get("/menu/sync-history/{integration_id}", response_model=List[MenuSyncResponse])
def get_sync_history(
    db: DbSession,
    integration_id: int,
    limit: int = 10,
):
    """Get menu sync history for an integration."""
    return db.query(MenuSync).filter(
        MenuSync.integration_id == integration_id
    ).order_by(MenuSync.started_at.desc()).limit(limit).all()


# Item Availability (86 items)

@router.get("/availability/", response_model=List[ItemAvailabilityResponse])
def list_item_availability(
    db: DbSession,
    unavailable_only: bool = False,
):
    """List item availability status."""
    query = db.query(ItemAvailability)
    if unavailable_only:
        query = query.filter(ItemAvailability.is_available == False)
    return query.all()


@router.post("/availability/", response_model=ItemAvailabilityResponse)
async def update_item_availability(
    db: DbSession,
    update: ItemAvailabilityUpdate,
):
    """Update item availability (86 an item)."""
    service = MenuSyncService(db)
    result = await service.update_item_availability(
        product_id=update.product_id,
        is_available=update.is_available,
        reason=update.reason
    )
    return result


@router.post("/availability/bulk")
async def bulk_update_availability(
    db: DbSession,
    updates: BulkAvailabilityUpdate,
):
    """Bulk update item availability."""
    service = MenuSyncService(db)
    results = []

    for update in updates.items:
        result = await service.update_item_availability(
            product_id=update.product_id,
            is_available=update.is_available,
            reason=update.reason
        )
        results.append(result)

    return {"updated": len(results), "results": results}


# Platform Mappings

@router.get("/mappings/{integration_id}", response_model=List[PlatformMappingResponse])
def list_platform_mappings(db: DbSession, integration_id: int):
    """List product-to-platform mappings."""
    return db.query(DeliveryPlatformMapping).filter(
        DeliveryPlatformMapping.integration_id == integration_id
    ).all()


@router.post("/mappings/", response_model=PlatformMappingResponse)
def create_platform_mapping(
    db: DbSession,
    mapping: PlatformMappingCreate,
):
    """Create a product-to-platform mapping."""
    db_mapping = DeliveryPlatformMapping(**mapping.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


@router.delete("/mappings/{mapping_id}")
def delete_platform_mapping(db: DbSession, mapping_id: int):
    """Delete a platform mapping."""
    mapping = db.query(DeliveryPlatformMapping).filter(
        DeliveryPlatformMapping.id == mapping_id
    ).first()
    if mapping:
        db.delete(mapping)
        db.commit()
    return {"status": "deleted"}


# Webhooks

@router.post("/webhook/{platform}", response_model=WebhookResponse)
async def handle_webhook(
    db: DbSession,
    platform: str,
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
):
    """Handle incoming webhook from delivery platform."""
    try:
        platform_enum = DeliveryPlatform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid platform")

    body = await request.body()
    payload = await request.json()

    handler = DeliveryWebhookHandler(db)

    # Verify webhook signature
    if x_signature:
        if not handler.verify_webhook(platform_enum, x_signature, body):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Process webhook
    event_type = payload.get("event_type", payload.get("type", "order.created"))
    result = await handler.handle_webhook(platform_enum, event_type, payload)

    return WebhookResponse(
        status=result.get("status", "success"),
        order_id=result.get("order_id"),
        platform_order_id=result.get("platform_order_id"),
        message=result.get("message")
    )


# Reports

@router.get("/reports/summary", response_model=DeliverySummary)
def get_delivery_summary(
    db: DbSession,
    location_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Get delivery orders summary."""
    service = DeliveryReportingService(db)

    start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None

    return service.get_delivery_summary(location_id, start_dt, end_dt)


@router.get("/reports/performance/{platform}", response_model=DeliveryPerformance)
def get_platform_performance(
    db: DbSession,
    platform: str,
    location_id: Optional[int] = None,
    days: int = 30,
):
    """Get performance metrics for a specific platform."""
    try:
        platform_enum = DeliveryPlatform(platform)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid platform")

    from datetime import timedelta

    start_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(DeliveryOrder).filter(
        DeliveryOrder.platform == platform_enum,
        DeliveryOrder.received_at >= start_date
    )

    if location_id:
        query = query.filter(DeliveryOrder.location_id == location_id)

    orders = query.all()

    if not orders:
        return DeliveryPerformance(
            platform=platform_enum,
            orders_count=0,
            avg_prep_time_minutes=0,
            avg_delivery_time_minutes=0,
            on_time_rate=0,
            cancellation_rate=0,
            customer_rating=None
        )

    # Calculate metrics
    total = len(orders)
    cancelled = len([o for o in orders if o.status == DeliveryOrderStatus.CANCELLED])

    prep_times = []
    for o in orders:
        if o.confirmed_at and o.ready_at:
            prep_times.append((o.ready_at - o.confirmed_at).total_seconds() / 60)

    delivery_times = []
    for o in orders:
        if o.picked_up_at and o.delivered_at:
            delivery_times.append((o.delivered_at - o.picked_up_at).total_seconds() / 60)

    return DeliveryPerformance(
        platform=platform_enum,
        orders_count=total,
        avg_prep_time_minutes=sum(prep_times) / len(prep_times) if prep_times else 0,
        avg_delivery_time_minutes=sum(delivery_times) / len(delivery_times) if delivery_times else 0,
        on_time_rate=((total - cancelled) / total * 100) if total > 0 else 0,
        cancellation_rate=(cancelled / total * 100) if total > 0 else 0,
        customer_rating=None
    )
