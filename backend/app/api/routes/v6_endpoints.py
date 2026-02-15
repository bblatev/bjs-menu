"""
V6 API Endpoints - Enterprise Extensions
=========================================
Complete API routes for all V6 features.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime, date, timezone
from pydantic import BaseModel
import uuid

from app.db.session import get_db
from app.services.v6_features.advanced_payments_service import AdvancedPaymentsService
from app.services.v6_features.queue_waitlist_service import QueueWaitlistService
from app.services.v6_features.haccp_food_safety_service import HACCPFoodSafetyService
from app.services.v6_features.cloud_kitchen_service import CloudKitchenService
from app.services.v6_features.franchise_management_service import FranchiseManagementService
from app.services.v6_features.drive_thru_service import DriveThruService
from app.services.v6_features.financial_management_service import FinancialManagementService
from app.services.v6_features.nra_tax_compliance_service import NRATaxComplianceService

# Import database models
from app.models import (
    DeliveryZone, DeliveryDriver, AggregatorOrder
)
from app.models.hardware import Integration
from app.core.rate_limit import limiter


router = APIRouter(tags=["V6 Features"])


# ==================== PYDANTIC MODELS ====================

class PlatformConnectRequest(BaseModel):
    platform: str
    api_key: str
    api_secret: str
    store_id: str
    auto_accept: bool = False
    commission_percent: float = 30.0

class DeliveryZoneCreate(BaseModel):
    name: str
    center_lat: float
    center_lng: float
    radius_km: float = 5.0
    delivery_fee: float = 3.0
    min_order_amount: float = 15.0

class DriverCreate(BaseModel):
    name: str
    phone: str
    vehicle_type: str = "car"
    vehicle_plate: Optional[str] = None

class GiftCardCreate(BaseModel):
    amount: float
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    message: Optional[str] = None

class WaitlistAdd(BaseModel):
    customer_name: str
    customer_phone: str
    party_size: int
    notes: Optional[str] = None
    seating_preference: Optional[str] = None

class CCPCreate(BaseModel):
    name: str
    location: str
    hazard_type: str
    critical_limit_min: Optional[float] = None
    critical_limit_max: Optional[float] = None

class TemperatureRecord(BaseModel):
    ccp_id: str
    temperature: float
    zone: str
    recorded_by: str

class BatchRegister(BaseModel):
    item_name: str
    batch_number: str
    expiry_date: date
    quantity: float
    unit: str
    storage_location: str
    allergens: List[str] = []

class VirtualBrandCreate(BaseModel):
    name: str
    cuisine_type: str
    description: str = ""
    platforms: List[str] = []

class KitchenStationCreate(BaseModel):
    name: str
    station_type: str
    max_concurrent_orders: int = 5

class FranchiseeRegister(BaseModel):
    company_name: str
    contact_name: str
    email: str
    phone: str
    address: str
    city: str
    territory: str

class ExpenseCreate(BaseModel):
    category: str
    description: str
    amount: float
    date: date
    vendor: Optional[str] = None
    recurring: bool = False


# ==================== DELIVERY AGGREGATOR ENDPOINTS ====================

@router.post("/{venue_id}/delivery/connect")
@limiter.limit("30/minute")
async def connect_delivery_platform(request: Request, venue_id: int, body_data: PlatformConnectRequest, db: Session = Depends(get_db)):
    """Connect to delivery platform (Glovo, Wolt, Bolt Food, Foodpanda, Uber Eats)"""
    # Check if already connected
    existing = db.query(Integration).filter(
        Integration.venue_id == venue_id,
        Integration.integration_id == body_data.platform,
        Integration.category == "delivery",
        Integration.status == "connected"
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"Platform {body_data.platform} is already connected")

    # Create new integration
    integration = Integration(
        venue_id=venue_id,
        integration_id=body_data.platform,
        integration_name=body_data.platform.replace("_", " ").title(),
        category="delivery",
        status="connected",
        credentials={
            "api_key": body_data.api_key,
            "api_secret": body_data.api_secret,
            "store_id": body_data.store_id
        },
        settings={
            "auto_accept": body_data.auto_accept,
            "commission_percent": body_data.commission_percent
        },
        sync_frequency="realtime",
        last_sync_at=datetime.now(timezone.utc),
        last_sync_status="success"
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)

    return {
        "success": True,
        "platform": body_data.platform,
        "venue_id": venue_id,
        "connected": True,
        "integration_id": integration.id
    }


@router.delete("/{venue_id}/delivery/{platform}/disconnect")
@limiter.limit("30/minute")
async def disconnect_delivery_platform(request: Request, venue_id: int, platform: str, db: Session = Depends(get_db)):
    """Disconnect from delivery platform"""
    integration = db.query(Integration).filter(
        Integration.venue_id == venue_id,
        Integration.integration_id == platform,
        Integration.category == "delivery",
        Integration.status == "connected"
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail=f"Platform {platform} is not connected")

    integration.status = "disconnected"
    integration.disconnected_at = datetime.now(timezone.utc)
    db.commit()

    return {"success": True, "platform": platform, "disconnected": True}


@router.get("/{venue_id}/delivery/platforms")
@limiter.limit("60/minute")
async def get_connected_platforms(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get all connected delivery platforms"""
    integrations = db.query(Integration).filter(
        Integration.venue_id == venue_id,
        Integration.category == "delivery",
        Integration.status == "connected"
    ).all()

    platforms = []
    for i in integrations:
        platforms.append({
            "platform": i.integration_id,
            "name": i.integration_name,
            "connected_at": i.connected_at.isoformat() if i.connected_at else None,
            "last_sync": i.last_sync_at.isoformat() if i.last_sync_at else None,
            "settings": i.settings or {}
        })

    return {"venue_id": venue_id, "platforms": platforms, "count": len(platforms)}


@router.get("/{venue_id}/delivery/orders")
@limiter.limit("60/minute")
async def get_aggregator_orders(request: Request, venue_id: int, status: Optional[str] = None, platform: Optional[str] = None, db: Session = Depends(get_db)):
    """Get orders from delivery platforms"""
    query = db.query(AggregatorOrder).filter(AggregatorOrder.venue_id == venue_id)

    if status:
        query = query.filter(AggregatorOrder.status == status)
    if platform:
        query = query.filter(AggregatorOrder.platform == platform)

    orders = query.order_by(AggregatorOrder.ordered_at.desc()).limit(100).all()

    orders_data = []
    for o in orders:
        orders_data.append({
            "id": o.aggregator_order_id,
            "platform": o.platform,
            "platform_order_id": o.platform_order_id,
            "status": o.status,
            "customer_name": o.customer_name,
            "customer_phone": o.customer_phone,
            "customer_address": o.customer_address,
            "items": o.items or [],
            "subtotal": float(o.subtotal or 0),
            "delivery_fee": float(o.delivery_fee or 0),
            "tip": float(o.tip or 0),
            "total": float(o.total or 0),
            "commission_amount": float(o.commission_amount or 0),
            "net_revenue": float(o.net_revenue or 0),
            "ordered_at": o.ordered_at.isoformat() if o.ordered_at else None,
            "accepted_at": o.accepted_at.isoformat() if o.accepted_at else None,
            "ready_at": o.ready_at.isoformat() if o.ready_at else None,
            "driver_name": o.driver_name,
            "driver_phone": o.driver_phone
        })

    return {"venue_id": venue_id, "orders": orders_data, "count": len(orders_data)}


@router.post("/{venue_id}/delivery/orders/{order_id}/accept")
@limiter.limit("30/minute")
async def accept_aggregator_order(request: Request, venue_id: int, order_id: str, prep_time: int = 20, db: Session = Depends(get_db)):
    """Accept order from delivery platform"""
    order = db.query(AggregatorOrder).filter(
        AggregatorOrder.venue_id == venue_id,
        AggregatorOrder.aggregator_order_id == order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"Order cannot be accepted, current status: {order.status}")

    order.status = "accepted"
    order.accepted_at = datetime.now(timezone.utc)
    order.prep_time_minutes = prep_time
    db.commit()

    return {"success": True, "order_id": order_id, "status": "accepted", "prep_time": prep_time}


@router.post("/{venue_id}/delivery/orders/{order_id}/reject")
@limiter.limit("30/minute")
async def reject_aggregator_order(request: Request, venue_id: int, order_id: str, reason: str = "", db: Session = Depends(get_db)):
    """Reject order from delivery platform"""
    order = db.query(AggregatorOrder).filter(
        AggregatorOrder.venue_id == venue_id,
        AggregatorOrder.aggregator_order_id == order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    if order.status not in ["pending", "accepted"]:
        raise HTTPException(status_code=400, detail=f"Order cannot be rejected, current status: {order.status}")

    order.status = "rejected"
    order.rejection_reason = reason
    db.commit()

    return {"success": True, "order_id": order_id, "status": "rejected", "reason": reason}


@router.post("/{venue_id}/delivery/orders/{order_id}/ready")
@limiter.limit("30/minute")
async def mark_delivery_order_ready(request: Request, venue_id: int, order_id: str, db: Session = Depends(get_db)):
    """Mark order as ready for pickup by driver"""
    order = db.query(AggregatorOrder).filter(
        AggregatorOrder.venue_id == venue_id,
        AggregatorOrder.aggregator_order_id == order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    if order.status not in ["accepted", "preparing"]:
        raise HTTPException(status_code=400, detail=f"Order cannot be marked ready, current status: {order.status}")

    order.status = "ready_for_pickup"
    order.ready_at = datetime.now(timezone.utc)
    db.commit()

    return {"success": True, "order_id": order_id, "status": "ready_for_pickup"}


@router.post("/{venue_id}/delivery/zones")
@limiter.limit("30/minute")
async def create_delivery_zone(request: Request, venue_id: int, zone: DeliveryZoneCreate, db: Session = Depends(get_db)):
    """Create delivery zone for own fleet"""
    zone_id = f"ZONE-{uuid.uuid4().hex[:8].upper()}"

    new_zone = DeliveryZone(
        venue_id=venue_id,
        zone_id=zone_id,
        name=zone.name,
        min_order=zone.min_order_amount,
        delivery_fee=zone.delivery_fee,
        estimated_time=30,  # Default estimated time
        polygon=[{"lat": zone.center_lat, "lng": zone.center_lng, "radius_km": zone.radius_km}],
        is_active=True
    )
    db.add(new_zone)
    db.commit()
    db.refresh(new_zone)

    return {
        "success": True,
        "zone_id": zone_id,
        "zone": {
            "id": new_zone.id,
            "zone_id": zone_id,
            "name": zone.name,
            "center_lat": zone.center_lat,
            "center_lng": zone.center_lng,
            "radius_km": zone.radius_km,
            "delivery_fee": zone.delivery_fee,
            "min_order_amount": zone.min_order_amount
        }
    }


@router.get("/{venue_id}/delivery/zones")
@limiter.limit("60/minute")
async def get_delivery_zones(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get all delivery zones"""
    zones = db.query(DeliveryZone).filter(
        DeliveryZone.venue_id == venue_id,
        DeliveryZone.is_active == True
    ).all()

    zones_data = []
    for z in zones:
        polygon = z.polygon or []
        center = polygon[0] if polygon else {}
        zones_data.append({
            "id": z.id,
            "zone_id": z.zone_id,
            "name": z.name,
            "min_order_amount": float(z.min_order or 0),
            "delivery_fee": float(z.delivery_fee or 0),
            "estimated_time": z.estimated_time,
            "center_lat": center.get("lat"),
            "center_lng": center.get("lng"),
            "radius_km": center.get("radius_km"),
            "is_active": z.is_active
        })

    return {"venue_id": venue_id, "zones": zones_data, "count": len(zones_data)}


@router.post("/{venue_id}/delivery/drivers")
@limiter.limit("30/minute")
async def add_delivery_driver(request: Request, venue_id: int, driver: DriverCreate, db: Session = Depends(get_db)):
    """Add driver to own delivery fleet"""
    new_driver = DeliveryDriver(
        venue_id=venue_id,
        name=driver.name,
        phone=driver.phone,
        vehicle_type=driver.vehicle_type,
        vehicle_registration=driver.vehicle_plate,
        is_active=True,
        is_available=True
    )
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)

    return {
        "success": True,
        "driver_id": new_driver.id,
        "driver": {
            "id": new_driver.id,
            "name": driver.name,
            "phone": driver.phone,
            "vehicle_type": driver.vehicle_type,
            "vehicle_plate": driver.vehicle_plate,
            "is_available": True
        }
    }


@router.get("/{venue_id}/delivery/drivers")
@limiter.limit("60/minute")
async def get_delivery_drivers(request: Request, venue_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all drivers"""
    query = db.query(DeliveryDriver).filter(
        DeliveryDriver.venue_id == venue_id,
        DeliveryDriver.is_active == True
    )

    if status == "available":
        query = query.filter(DeliveryDriver.is_available == True)
    elif status == "busy":
        query = query.filter(DeliveryDriver.is_available == False)

    drivers = query.all()

    drivers_data = []
    for d in drivers:
        drivers_data.append({
            "id": d.id,
            "name": d.name,
            "phone": d.phone,
            "vehicle_type": d.vehicle_type,
            "vehicle_plate": d.vehicle_registration,
            "is_available": d.is_available,
            "current_lat": d.current_latitude,
            "current_lng": d.current_longitude,
            "last_location_update": d.last_location_update.isoformat() if d.last_location_update else None
        })

    return {"venue_id": venue_id, "drivers": drivers_data, "count": len(drivers_data)}


@router.post("/{venue_id}/delivery/drivers/{driver_id}/location")
@limiter.limit("30/minute")
async def update_driver_location(request: Request, venue_id: int, driver_id: str, lat: float = Body(...), lng: float = Body(...), db: Session = Depends(get_db)):
    """Update driver GPS location"""
    try:
        driver_id_int = int(driver_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid driver ID")

    driver = db.query(DeliveryDriver).filter(
        DeliveryDriver.id == driver_id_int,
        DeliveryDriver.venue_id == venue_id
    ).first()

    if not driver:
        raise HTTPException(status_code=404, detail=f"Driver {driver_id} not found")

    driver.current_latitude = lat
    driver.current_longitude = lng
    driver.last_location_update = datetime.now(timezone.utc)
    db.commit()

    return {"success": True, "driver_id": driver_id, "lat": lat, "lng": lng}


@router.get("/{venue_id}/delivery/stats")
@limiter.limit("60/minute")
async def get_delivery_stats(request: Request, venue_id: int, start: datetime = Query(...), end: datetime = Query(...), db: Session = Depends(get_db)):
    """Get delivery platform statistics"""
    # Get all orders in the date range
    orders = db.query(AggregatorOrder).filter(
        AggregatorOrder.venue_id == venue_id,
        AggregatorOrder.ordered_at >= start,
        AggregatorOrder.ordered_at <= end
    ).all()

    # Calculate stats by platform
    by_platform = {}
    total_orders = 0
    total_revenue = 0.0
    total_commission = 0.0
    total_net = 0.0

    for o in orders:
        platform = o.platform
        if platform not in by_platform:
            by_platform[platform] = {
                "orders": 0,
                "revenue": 0.0,
                "commission": 0.0,
                "net": 0.0,
                "avg_order_value": 0.0
            }

        by_platform[platform]["orders"] += 1
        by_platform[platform]["revenue"] += float(o.total or 0)
        by_platform[platform]["commission"] += float(o.commission_amount or 0)
        by_platform[platform]["net"] += float(o.net_revenue or 0)

        total_orders += 1
        total_revenue += float(o.total or 0)
        total_commission += float(o.commission_amount or 0)
        total_net += float(o.net_revenue or 0)

    # Calculate averages
    for platform in by_platform:
        if by_platform[platform]["orders"] > 0:
            by_platform[platform]["avg_order_value"] = by_platform[platform]["revenue"] / by_platform[platform]["orders"]

    return {
        "venue_id": venue_id,
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat()
        },
        "stats": {
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "total_commission": round(total_commission, 2),
            "net_revenue": round(total_net, 2),
            "avg_order_value": round(total_revenue / total_orders, 2) if total_orders > 0 else 0,
            "by_platform": by_platform
        }
    }


# ==================== ADVANCED PAYMENTS ====================

@router.post("/{venue_id}/gift-cards")
@limiter.limit("30/minute")
async def create_gift_card(request: Request, venue_id: int, card: GiftCardCreate, db: Session = Depends(get_db)):
    """Create gift card"""
    service = AdvancedPaymentsService(db)
    result = service.create_gift_card(
        venue_id=venue_id,
        amount=card.amount,
        recipient_name=card.recipient_name,
        recipient_email=card.recipient_email,
        message=card.message
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create gift card"))
    return {
        "success": True,
        "gift_card_id": result["id"],
        "code": result["code"],
        "amount": result["amount"],
        "expires_at": result["expires_at"]
    }

@router.get("/{venue_id}/gift-cards/{code}/balance")
@limiter.limit("60/minute")
async def check_gift_card_balance(request: Request, venue_id: int, code: str, db: Session = Depends(get_db)):
    """Check gift card balance"""
    service = AdvancedPaymentsService(db)
    result = service.check_gift_card_balance(code)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Card not found"))
    return {"code": code, "balance": result["balance"], "status": result["status"]}

@router.post("/{venue_id}/gift-cards/{code}/redeem")
@limiter.limit("30/minute")
async def redeem_gift_card(request: Request, venue_id: int, code: str, amount: float = Body(...), db: Session = Depends(get_db)):
    """Redeem gift card (PIN validation removed - using code-only redemption)"""
    service = AdvancedPaymentsService(db)
    result = service.redeem_gift_card(code=code, amount=amount)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Redemption failed"))
    return {"success": True, "redeemed": amount, "remaining": result["remaining_balance"]}

@router.post("/{venue_id}/customers/{customer_id}/wallet")
@limiter.limit("30/minute")
async def create_customer_wallet(request: Request, venue_id: int, customer_id: int, db: Session = Depends(get_db)):
    """Create or get customer wallet"""
    service = AdvancedPaymentsService(db)
    result = service.get_or_create_wallet(venue_id, customer_id)
    return {"success": True, "wallet_id": result["id"], "balance": result["balance"]}

@router.post("/{venue_id}/customers/{customer_id}/wallet/add")
@limiter.limit("30/minute")
async def add_wallet_funds(request: Request, venue_id: int, customer_id: int, amount: float = Body(...), db: Session = Depends(get_db)):
    """Add funds to wallet"""
    service = AdvancedPaymentsService(db)
    # First get or create the wallet
    wallet_result = service.get_or_create_wallet(venue_id, customer_id)
    result = service.add_funds(wallet_id=wallet_result["id"], amount=amount)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to add funds"))
    return {"success": True, "new_balance": result["new_balance"]}

@router.post("/{venue_id}/payments/crypto")
@limiter.limit("30/minute")
async def create_crypto_payment(request: Request, venue_id: int, order_id: int = Body(...), amount: float = Body(...), crypto_type: str = Body("btc"), db: Session = Depends(get_db)):
    """Create cryptocurrency payment"""
    service = AdvancedPaymentsService(db)
    result = service.create_crypto_payment(
        venue_id=venue_id,
        order_id=order_id,
        amount_fiat=amount,
        crypto_type=crypto_type
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create crypto payment"))
    return {
        "success": True,
        "payment_id": result["payment_id"],
        "wallet_address": result["wallet_address"],
        "amount_crypto": result["amount_crypto"],
        "exchange_rate": result["exchange_rate"],
        "payment_uri": result["payment_uri"],
        "expires_at": result["expires_at"]
    }

@router.post("/{venue_id}/payments/bnpl")
@limiter.limit("30/minute")
async def create_bnpl_plan(request: Request, venue_id: int, order_id: int = Body(...), customer_id: int = Body(...), total: float = Body(...), installments: int = Body(3), db: Session = Depends(get_db)):
    """Create Buy Now Pay Later plan"""
    service = AdvancedPaymentsService(db)
    result = service.create_bnpl_plan(
        venue_id=venue_id,
        order_id=order_id,
        customer_id=customer_id,
        total_amount=total,
        installments=installments
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create BNPL plan"))
    return {
        "success": True,
        "plan_id": result["plan_id"],
        "installment_amount": result["installment_amount"],
        "first_payment_date": result["first_payment_date"]
    }


# ==================== QUEUE & WAITLIST ====================

@router.post("/{venue_id}/waitlist")
@limiter.limit("30/minute")
async def add_to_waitlist(request: Request, venue_id: int, entry: WaitlistAdd, db: Session = Depends(get_db)):
    """Add party to waitlist"""
    service = QueueWaitlistService(db)
    result = service.add_to_waitlist(
        venue_id=venue_id,
        customer_name=entry.customer_name,
        customer_phone=entry.customer_phone,
        party_size=entry.party_size,
        notes=entry.notes,
        seating_preference=entry.seating_preference
    )
    return {
        "success": True,
        "entry_id": result.id,
        "position": result.position,
        "estimated_wait": result.estimated_wait_minutes
    }

@router.get("/{venue_id}/waitlist")
@limiter.limit("60/minute")
async def get_waitlist(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get current waitlist"""
    service = QueueWaitlistService(db)
    entries = service.get_waitlist(venue_id)
    return {"venue_id": venue_id, "entries": [e.model_dump() for e in entries], "count": len(entries)}

@router.post("/{venue_id}/waitlist/{entry_id}/notify")
@limiter.limit("30/minute")
async def notify_party(request: Request, venue_id: int, entry_id: str, db: Session = Depends(get_db)):
    """Notify party that table is ready"""
    service = QueueWaitlistService(db)
    result = service.notify_party(entry_id)
    return {"success": True, "entry_id": entry_id, "notified": result.get("notified", True)}

@router.post("/{venue_id}/waitlist/{entry_id}/seat")
@limiter.limit("30/minute")
async def seat_party(request: Request, venue_id: int, entry_id: str, table_id: int = Body(...), db: Session = Depends(get_db)):
    """Mark party as seated"""
    service = QueueWaitlistService(db)
    result = service.seat_party(entry_id, table_id)
    return {"success": True, "entry_id": entry_id, "table_id": table_id, "seated": True}

@router.delete("/{venue_id}/waitlist/{entry_id}")
@limiter.limit("30/minute")
async def cancel_waitlist_entry(request: Request, venue_id: int, entry_id: str, db: Session = Depends(get_db)):
    """Cancel waitlist entry"""
    service = QueueWaitlistService(db)
    service.cancel_entry(entry_id)
    return {"success": True, "entry_id": entry_id, "cancelled": True}

@router.get("/{venue_id}/waitlist/stats")
@limiter.limit("60/minute")
async def get_waitlist_stats(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get waitlist statistics"""
    service = QueueWaitlistService(db)
    stats = service.get_stats(venue_id)
    return {"venue_id": venue_id, "current_waiting": stats.get("current_count", 0), "avg_wait": stats.get("avg_wait_minutes", 0)}


# ==================== HACCP FOOD SAFETY ====================

@router.post("/{venue_id}/haccp/ccp")
@limiter.limit("30/minute")
async def create_critical_control_point(request: Request, venue_id: int, ccp: CCPCreate, db: Session = Depends(get_db)):
    """Create Critical Control Point"""
    service = HACCPFoodSafetyService(db)
    result = service.create_ccp(
        venue_id=venue_id,
        name=ccp.name,
        location=ccp.location,
        hazard_type=ccp.hazard_type,
        critical_limit_min=ccp.critical_limit_min,
        critical_limit_max=ccp.critical_limit_max
    )
    return {"success": True, "ccp_id": result.id, "ccp": result.model_dump()}

@router.get("/{venue_id}/haccp/ccp")
@limiter.limit("60/minute")
async def get_critical_control_points(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get all CCPs"""
    service = HACCPFoodSafetyService(db)
    ccps = service.get_ccps(venue_id)
    return {"venue_id": venue_id, "ccps": [c.model_dump() for c in ccps]}

@router.post("/{venue_id}/haccp/temperature")
@limiter.limit("30/minute")
async def record_temperature(request: Request, venue_id: int, reading: TemperatureRecord, db: Session = Depends(get_db)):
    """Record temperature reading"""
    service = HACCPFoodSafetyService(db)
    result = service.record_temperature(
        venue_id=venue_id,
        ccp_id=reading.ccp_id,
        temperature=reading.temperature,
        zone=reading.zone,
        recorded_by=reading.recorded_by
    )
    return {"success": True, "reading_id": result.id, "within_limits": result.within_limits}

@router.get("/{venue_id}/haccp/temperature")
@limiter.limit("60/minute")
async def get_temperature_readings(request: Request, venue_id: int, ccp_id: Optional[str] = None, start: date = Query(...), end: date = Query(...), db: Session = Depends(get_db)):
    """Get temperature readings"""
    service = HACCPFoodSafetyService(db)
    readings = service.get_temperature_readings(venue_id, ccp_id, start, end)
    return {"venue_id": venue_id, "readings": [r.model_dump() for r in readings]}

@router.post("/{venue_id}/haccp/batch")
@limiter.limit("30/minute")
async def register_food_batch(request: Request, venue_id: int, batch: BatchRegister, db: Session = Depends(get_db)):
    """Register food batch for tracking"""
    service = HACCPFoodSafetyService(db)
    result = service.register_batch(
        venue_id=venue_id,
        item_name=batch.item_name,
        batch_number=batch.batch_number,
        expiry_date=batch.expiry_date,
        quantity=batch.quantity,
        unit=batch.unit,
        storage_location=batch.storage_location,
        allergens=batch.allergens
    )
    return {"success": True, "batch_id": result.id}

@router.get("/{venue_id}/haccp/batches/expiring")
@limiter.limit("60/minute")
async def get_expiring_food_batches(request: Request, venue_id: int, days: int = 3, db: Session = Depends(get_db)):
    """Get batches expiring soon"""
    service = HACCPFoodSafetyService(db)
    batches = service.get_expiring_batches(venue_id, days)
    return {"venue_id": venue_id, "expiring_batches": [b.model_dump() for b in batches]}

@router.get("/{venue_id}/haccp/report")
@limiter.limit("60/minute")
async def get_haccp_compliance_report(request: Request, venue_id: int, start: date = Query(...), end: date = Query(...), db: Session = Depends(get_db)):
    """Generate HACCP compliance report"""
    service = HACCPFoodSafetyService(db)
    report = service.generate_haccp_report(venue_id, start, end)
    return report


# ==================== CLOUD KITCHEN ====================

@router.post("/{venue_id}/cloud-kitchen/brands")
@limiter.limit("30/minute")
async def create_virtual_brand(request: Request, venue_id: int, brand: VirtualBrandCreate, db: Session = Depends(get_db)):
    """Create virtual brand for cloud kitchen"""
    service = CloudKitchenService(db)
    result = service.create_brand(
        venue_id=venue_id,
        name=brand.name,
        cuisine_type=brand.cuisine_type,
        description=brand.description,
        platforms=brand.platforms
    )
    return {"success": True, "brand_id": result.id, "brand": result.model_dump()}

@router.get("/{venue_id}/cloud-kitchen/brands")
@limiter.limit("60/minute")
async def get_virtual_brands(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get all virtual brands"""
    service = CloudKitchenService(db)
    brands = service.get_brands(venue_id)
    return {"venue_id": venue_id, "brands": [b.model_dump() for b in brands]}

@router.put("/{venue_id}/cloud-kitchen/brands/{brand_id}")
@limiter.limit("30/minute")
async def update_virtual_brand(request: Request, venue_id: int, brand_id: str, updates: Dict = Body(...), db: Session = Depends(get_db)):
    """Update virtual brand"""
    service = CloudKitchenService(db)
    result = service.update_virtual_brand(brand_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail=f"Brand {brand_id} not found")
    return {"success": True, "brand_id": brand_id}

@router.post("/{venue_id}/cloud-kitchen/brands/{brand_id}/pause")
@limiter.limit("30/minute")
async def pause_virtual_brand(request: Request, venue_id: int, brand_id: str, db: Session = Depends(get_db)):
    """Pause virtual brand"""
    service = CloudKitchenService(db)
    result = service.pause_brand(brand_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Brand {brand_id} not found")
    return {"success": True, "brand_id": brand_id, "status": "paused"}

@router.post("/{venue_id}/cloud-kitchen/brands/{brand_id}/activate")
@limiter.limit("30/minute")
async def activate_virtual_brand(request: Request, venue_id: int, brand_id: str, db: Session = Depends(get_db)):
    """Activate virtual brand"""
    service = CloudKitchenService(db)
    result = service.activate_brand(brand_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Brand {brand_id} not found")
    return {"success": True, "brand_id": brand_id, "status": "active"}

@router.post("/{venue_id}/cloud-kitchen/stations")
@limiter.limit("30/minute")
async def create_kitchen_station(request: Request, venue_id: int, station: KitchenStationCreate, db: Session = Depends(get_db)):
    """Create kitchen station"""
    service = CloudKitchenService(db)
    result = service.create_station(
        venue_id=venue_id,
        name=station.name,
        station_type=station.station_type,
        max_concurrent_orders=station.max_concurrent_orders
    )
    return {"success": True, "station_id": result.id}

@router.get("/{venue_id}/cloud-kitchen/stations")
@limiter.limit("60/minute")
async def get_kitchen_stations(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get all kitchen stations"""
    service = CloudKitchenService(db)
    stations = service.get_stations(venue_id)
    return {"venue_id": venue_id, "stations": [s.model_dump() for s in stations]}

@router.get("/{venue_id}/cloud-kitchen/performance")
@limiter.limit("60/minute")
async def get_cloud_kitchen_performance(request: Request, venue_id: int, start: datetime = Query(...), end: datetime = Query(...), db: Session = Depends(get_db)):
    """Get cloud kitchen performance metrics"""
    service = CloudKitchenService(db)
    performance = service.get_brand_performance(venue_id, start, end)
    return {"venue_id": venue_id, "brands": performance}


# ==================== FRANCHISE MANAGEMENT ====================

@router.post("/franchise/franchisees")
@limiter.limit("30/minute")
async def register_franchisee(request: Request, franchisee: FranchiseeRegister, db: Session = Depends(get_db)):
    """Register new franchisee"""
    service = FranchiseManagementService(db)
    result = service.register_franchisee(
        company_name=franchisee.company_name,
        contact_name=franchisee.contact_name,
        email=franchisee.email,
        phone=franchisee.phone,
        territory=franchisee.territory,
        address=franchisee.address,
        city=franchisee.city
    )
    return {"success": True, "franchisee_id": result.id, "franchisee": result.model_dump()}

@router.get("/franchise/franchisees")
@limiter.limit("60/minute")
async def get_all_franchisees(request: Request, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all franchisees"""
    service = FranchiseManagementService(db)
    from app.services.v6_features.franchise_management_service import FranchiseStatus
    status_enum = FranchiseStatus(status) if status else None
    franchisees = service.get_franchisees(status=status_enum)
    return {"franchisees": [f.model_dump() for f in franchisees], "count": len(franchisees)}

@router.post("/franchise/franchisees/{franchisee_id}/approve")
@limiter.limit("30/minute")
async def approve_franchisee(request: Request, franchisee_id: str, agreement_years: int = 10, db: Session = Depends(get_db)):
    """Approve franchisee application"""
    service = FranchiseManagementService(db)
    result = service.approve_franchisee(franchisee_id, agreement_years)
    return {"success": True, "franchisee_id": result.id, "status": result.status}

@router.post("/franchise/franchisees/{franchisee_id}/royalty")
@limiter.limit("30/minute")
async def calculate_royalty(request: Request, franchisee_id: str, period_start: date = Body(...), period_end: date = Body(...), gross_sales: float = Body(...), db: Session = Depends(get_db)):
    """Calculate royalty payment"""
    service = FranchiseManagementService(db)
    result = service.calculate_royalty(franchisee_id, period_start, period_end, gross_sales)
    return {"success": True, "payment_id": result.id, "royalty_due": result.royalty_amount, "payment": result.model_dump()}

@router.get("/franchise/franchisees/{franchisee_id}/performance")
@limiter.limit("60/minute")
async def get_franchisee_performance(request: Request, franchisee_id: str, start: date = Query(...), end: date = Query(...), db: Session = Depends(get_db)):
    """Get franchisee performance metrics"""
    service = FranchiseManagementService(db)
    performance = service.get_franchise_performance(franchisee_id, start, end)
    return {"franchisee_id": franchisee_id, "performance": performance}

@router.post("/franchise/audits")
@limiter.limit("30/minute")
async def create_compliance_audit(request: Request, franchisee_id: str = Body(...), venue_id: int = Body(...), auditor_name: str = Body(...), db: Session = Depends(get_db)):
    """Create compliance audit"""
    service = FranchiseManagementService(db)
    result = service.create_audit(franchisee_id, venue_id, auditor_name)
    return {"success": True, "audit_id": result.id, "audit": result.model_dump()}

@router.get("/franchise/network-overview")
@limiter.limit("60/minute")
async def get_franchise_network_overview(request: Request, db: Session = Depends(get_db)):
    """Get franchise network overview"""
    service = FranchiseManagementService(db)
    overview = service.get_network_overview()
    return overview


# ==================== DRIVE-THRU ====================

@router.post("/{venue_id}/drive-thru/lanes")
@limiter.limit("30/minute")
async def create_drive_thru_lane(request: Request, venue_id: int, lane_number: int = Body(...), lane_type: str = Body("standard"), db: Session = Depends(get_db)):
    """Create drive-thru lane"""
    service = DriveThruService(db)
    result = service.create_lane(venue_id, lane_number, lane_type)
    if not result.get("success", True):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create lane"))
    return {"success": True, "lane_id": result.get("id"), "lane": result}

@router.get("/{venue_id}/drive-thru/lanes")
@limiter.limit("60/minute")
async def get_drive_thru_lanes(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get all drive-thru lanes"""
    service = DriveThruService(db)
    lanes = service.get_lanes(venue_id)
    return {"venue_id": venue_id, "lanes": lanes}

@router.post("/{venue_id}/drive-thru/lanes/{lane_id}/open")
@limiter.limit("30/minute")
async def open_lane(request: Request, venue_id: int, lane_id: str, db: Session = Depends(get_db)):
    """Open drive-thru lane"""
    service = DriveThruService(db)
    try:
        lane_id_int = int(lane_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid lane ID")
    result = service.open_lane(lane_id_int)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", f"Lane {lane_id} not found"))
    return {"success": True, "lane_id": result.get("lane_id"), "status": result.get("status")}

@router.post("/{venue_id}/drive-thru/lanes/{lane_id}/close")
@limiter.limit("30/minute")
async def close_lane(request: Request, venue_id: int, lane_id: str, db: Session = Depends(get_db)):
    """Close drive-thru lane"""
    service = DriveThruService(db)
    try:
        lane_id_int = int(lane_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid lane ID")
    result = service.close_lane(lane_id_int)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", f"Lane {lane_id} not found"))
    return {"success": True, "lane_id": result.get("lane_id"), "status": result.get("status")}

@router.post("/{venue_id}/drive-thru/vehicle")
@limiter.limit("30/minute")
async def register_vehicle(request: Request, venue_id: int, lane_id: str = Body(...), license_plate: Optional[str] = Body(None), db: Session = Depends(get_db)):
    """Register vehicle in drive-thru"""
    service = DriveThruService(db)
    try:
        lane_id_int = int(lane_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid lane ID")
    result = service.register_vehicle(venue_id, lane_id_int, license_plate)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to register vehicle"))
    return {"success": True, "vehicle_id": result.get("id"), "vehicle": result}

@router.post("/{venue_id}/drive-thru/vehicle/{vehicle_id}/complete")
@limiter.limit("30/minute")
async def complete_vehicle_order(request: Request, venue_id: int, vehicle_id: str, db: Session = Depends(get_db)):
    """Complete vehicle order and exit"""
    service = DriveThruService(db)
    try:
        vehicle_id_int = int(vehicle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid vehicle ID")
    result = service.complete_pickup(vehicle_id_int)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", f"Vehicle {vehicle_id} not found"))
    return {"success": True, "vehicle_id": result.get("vehicle_id"), "total_time_seconds": result.get("total_time_seconds", 0), "vehicle": result}

@router.get("/{venue_id}/drive-thru/stats")
@limiter.limit("60/minute")
async def get_drive_thru_stats(request: Request, venue_id: int, db: Session = Depends(get_db)):
    """Get drive-thru statistics"""
    service = DriveThruService(db)
    stats = service.get_stats(venue_id)
    return {"venue_id": venue_id, **stats}


# ==================== FINANCIAL MANAGEMENT ====================

@router.post("/{venue_id}/finance/expenses")
@limiter.limit("30/minute")
async def create_expense(request: Request, venue_id: int, expense: ExpenseCreate, created_by: int = 1, db: Session = Depends(get_db)):
    """Create expense record"""
    service = FinancialManagementService(db)
    from app.services.v6_features.financial_management_service import ExpenseCategory
    result = service.create_expense(
        venue_id=venue_id,
        category=ExpenseCategory(expense.category),
        amount=expense.amount,
        description=expense.description,
        date=expense.date,
        vendor=expense.vendor,
        receipt_url=getattr(expense, 'receipt_url', None),
        created_by=created_by
    )
    return {"success": True, "expense_id": result.id, "expense": result.model_dump()}

@router.get("/{venue_id}/finance/expenses")
@limiter.limit("60/minute")
async def get_expenses(request: Request, venue_id: int, start: date = Query(...), end: date = Query(...), category: Optional[str] = None, db: Session = Depends(get_db)):
    """Get expenses"""
    service = FinancialManagementService(db)
    from app.services.v6_features.financial_management_service import ExpenseCategory
    category_enum = ExpenseCategory(category) if category else None
    expenses = service.get_expenses(venue_id, start, end, category_enum)
    total = sum(e.amount for e in expenses)
    return {"venue_id": venue_id, "expenses": [e.model_dump() for e in expenses], "total": total}

@router.get("/{venue_id}/finance/expenses/summary")
@limiter.limit("60/minute")
async def get_expense_summary(request: Request, venue_id: int, start: date = Query(...), end: date = Query(...), db: Session = Depends(get_db)):
    """Get expense summary by category"""
    service = FinancialManagementService(db)
    summary = service.get_expense_summary(venue_id, start, end)
    return {"venue_id": venue_id, **summary}

@router.get("/{venue_id}/finance/cash-flow/forecast")
@limiter.limit("60/minute")
async def get_cash_flow_forecast(request: Request, venue_id: int, days: int = 30, db: Session = Depends(get_db)):
    """Get cash flow forecast"""
    service = FinancialManagementService(db)
    forecast = service.forecast_cash_flow(venue_id, days)
    return {"venue_id": venue_id, "forecast": [f.model_dump() for f in forecast]}

@router.get("/{venue_id}/finance/break-even")
@limiter.limit("60/minute")
async def get_break_even_analysis(request: Request, venue_id: int, start: date = Query(...), end: date = Query(...), revenue: float = Query(...), avg_check: float = Query(...), db: Session = Depends(get_db)):
    """Get break-even analysis"""
    service = FinancialManagementService(db)
    analysis = service.calculate_break_even(venue_id, start, end, revenue, avg_check)
    return {"venue_id": venue_id, **analysis}

@router.get("/{venue_id}/finance/profit-margins")
@limiter.limit("60/minute")
async def get_profit_margins(request: Request, venue_id: int, start: date = Query(...), end: date = Query(...), revenue: float = Query(...), db: Session = Depends(get_db)):
    """Get profit margin analysis"""
    service = FinancialManagementService(db)
    margins = service.get_profit_margins(venue_id, start, end, revenue)
    return {"venue_id": venue_id, **margins}

@router.post("/{venue_id}/finance/budget/{category}")
@limiter.limit("30/minute")
async def set_budget(request: Request, venue_id: int, category: str, monthly_budget: float = Body(...), db: Session = Depends(get_db)):
    """Set monthly budget for category"""
    service = FinancialManagementService(db)
    from app.services.v6_features.financial_management_service import ExpenseCategory
    result = service.set_budget(venue_id, ExpenseCategory(category), monthly_budget)
    return {"success": True, "category": category, "budget": result.get("budget"), "budget_data": result}

@router.get("/{venue_id}/finance/budget/status")
@limiter.limit("60/minute")
async def get_budget_status(request: Request, venue_id: int, month: date = Query(...), db: Session = Depends(get_db)):
    """Get budget status"""
    service = FinancialManagementService(db)
    status = service.get_budget_status(venue_id, month)
    return {"venue_id": venue_id, **status}


# ==================== NRA TAX COMPLIANCE ====================

@router.post("/{venue_id}/nra/fiscal-receipt")
@limiter.limit("30/minute")
async def create_fiscal_receipt(request: Request, venue_id: int, order_id: str = Body(...), items: List[Dict] = Body(...), payment_method: str = Body(...), db: Session = Depends(get_db)):
    """Create fiscal receipt for NRA"""
    service = NRATaxComplianceService(db)
    result = service.create_fiscal_receipt(venue_id, order_id, items, payment_method)
    return {"success": True, "document_id": result.id, "unique_sale_number": result.unique_sale_number, "qr_code": result.qr_code, "receipt": result.model_dump()}

@router.post("/{venue_id}/nra/storno/{document_id}")
@limiter.limit("30/minute")
async def create_storno(request: Request, venue_id: int, document_id: str, reason: str = Body(...), db: Session = Depends(get_db)):
    """Create storno/reversal document"""
    service = NRATaxComplianceService(db)
    result = service.create_storno(document_id, reason)
    return {"success": True, "storno_id": result.id, "storno": result.model_dump()}

@router.get("/{venue_id}/nra/daily-report")
@limiter.limit("60/minute")
async def get_daily_z_report(request: Request, venue_id: int, report_date: date = Query(...), db: Session = Depends(get_db)):
    """Get daily Z-report for NRA"""
    service = NRATaxComplianceService(db)
    report = service.generate_daily_report(venue_id, report_date)
    return {"venue_id": venue_id, "report_date": str(report_date), "report": report.model_dump()}

@router.post("/{venue_id}/nra/report/{report_id}/send")
@limiter.limit("30/minute")
async def send_report_to_nra(request: Request, venue_id: int, report_id: str, db: Session = Depends(get_db)):
    """Send report to NRA"""
    service = NRATaxComplianceService(db)
    result = service.send_report_to_nra(report_id)
    return {"success": True, **result}

@router.get("/{venue_id}/nra/saft-export")
@limiter.limit("60/minute")
async def export_saft(request: Request, venue_id: int, start: date = Query(...), end: date = Query(...), db: Session = Depends(get_db)):
    """Export SAF-T format for tax audit"""
    service = NRATaxComplianceService(db)
    result = service.generate_saft_export(venue_id, start, end)
    return {"venue_id": venue_id, "format": "SAF-T", **result}

@router.post("/{venue_id}/gdpr/consent")
@limiter.limit("30/minute")
async def record_gdpr_consent(request: Request, venue_id: int, customer_id: int = Body(...), consent_type: str = Body(...), consented: bool = Body(...), consent_text: str = Body(""), db: Session = Depends(get_db)):
    """Record GDPR consent"""
    service = NRATaxComplianceService(db)
    result = service.record_consent(venue_id, customer_id, consent_type, consented, consent_text)
    return {"success": True, "consent_id": result.id, "consent": result.model_dump()}

@router.get("/{venue_id}/gdpr/customer/{customer_id}/data")
@limiter.limit("60/minute")
async def export_customer_data(request: Request, venue_id: int, customer_id: int, db: Session = Depends(get_db)):
    """GDPR data export for customer"""
    service = NRATaxComplianceService(db)
    data = service.export_customer_data(customer_id)
    return {"customer_id": customer_id, **data}

@router.delete("/{venue_id}/gdpr/customer/{customer_id}")
@limiter.limit("30/minute")
async def delete_customer_data(request: Request, venue_id: int, customer_id: int, db: Session = Depends(get_db)):
    """GDPR right to be forgotten"""
    service = NRATaxComplianceService(db)
    result = service.delete_customer_data(customer_id)
    return {"success": True, "customer_id": customer_id, **result}
