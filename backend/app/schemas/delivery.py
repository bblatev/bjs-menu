"""Delivery Aggregator schemas - DoorDash/Uber Eats style."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from app.models.delivery import DeliveryPlatform, DeliveryOrderStatus


# Delivery Integration

class DeliveryIntegrationBase(BaseModel):
    """Base delivery integration schema."""
    platform: DeliveryPlatform
    location_id: Optional[int] = None
    store_id: Optional[str] = None
    merchant_id: Optional[str] = None
    is_active: bool = True
    auto_accept_orders: bool = True
    auto_confirm_ready: bool = False
    prep_time_minutes: int = 20
    sync_inventory: bool = True
    commission_percent: Optional[float] = None


class DeliveryIntegrationCreate(DeliveryIntegrationBase):
    """Create delivery integration schema."""
    api_key: str
    api_secret: Optional[str] = None
    webhook_secret: Optional[str] = None


class DeliveryIntegrationUpdate(BaseModel):
    """Update delivery integration schema."""
    is_active: Optional[bool] = None
    auto_accept_orders: Optional[bool] = None
    auto_confirm_ready: Optional[bool] = None
    prep_time_minutes: Optional[int] = None
    sync_inventory: Optional[bool] = None
    commission_percent: Optional[float] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None


class DeliveryIntegrationResponse(DeliveryIntegrationBase):
    """Delivery integration response schema."""
    id: int
    webhook_url: Optional[str] = None
    is_menu_synced: bool = False
    last_menu_sync_at: Optional[datetime] = None
    last_order_received_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Delivery Orders

class DeliveryOrderItemBase(BaseModel):
    """Base delivery order item schema."""
    platform_item_id: Optional[str] = None
    item_name: str
    quantity: int = 1
    unit_price: float = 0.0
    total_price: float = 0.0
    modifiers: Optional[List[Dict[str, Any]]] = None
    special_instructions: Optional[str] = None


class DeliveryOrderItemResponse(DeliveryOrderItemBase):
    """Delivery order item response."""
    id: int
    order_id: int
    product_id: Optional[int] = None

    model_config = {"from_attributes": True}


class DeliveryOrderResponse(BaseModel):
    """Delivery order response schema."""
    id: int
    integration_id: int
    location_id: Optional[int] = None
    platform: DeliveryPlatform
    platform_order_id: str
    platform_display_id: Optional[str] = None
    status: DeliveryOrderStatus
    status_updated_at: Optional[datetime] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_instructions: Optional[str] = None
    subtotal: float = 0.0
    tax: float = 0.0
    delivery_fee: float = 0.0
    tip: float = 0.0
    total: float = 0.0
    platform_fee: float = 0.0
    net_payout: float = 0.0
    special_instructions: Optional[str] = None
    is_scheduled: bool = False
    scheduled_for: Optional[datetime] = None
    estimated_pickup_at: Optional[datetime] = None
    estimated_delivery_at: Optional[datetime] = None
    received_at: datetime
    confirmed_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    pos_order_id: Optional[int] = None
    sent_to_kds: bool = False
    kds_ticket_id: Optional[int] = None
    error_message: Optional[str] = None
    items: List[DeliveryOrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeliveryOrderStatusUpdate(BaseModel):
    """Update delivery order status."""
    status: DeliveryOrderStatus
    estimated_ready_minutes: Optional[int] = None


class DeliveryOrderAccept(BaseModel):
    """Accept delivery order."""
    prep_time_minutes: int = 20


class DeliveryOrderReject(BaseModel):
    """Reject delivery order."""
    reason: str
    out_of_stock_items: Optional[List[str]] = None


# Menu Sync

class MenuSyncResponse(BaseModel):
    """Menu sync result."""
    id: int
    integration_id: int
    sync_type: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: bool = False
    items_synced: int = 0
    items_failed: int = 0
    availability_changes: int = 0
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MenuSyncRequest(BaseModel):
    """Request menu sync."""
    integration_id: int
    full_sync: bool = True


# Item Availability (86 items)

class ItemAvailabilityUpdate(BaseModel):
    """Update item availability across platforms."""
    product_id: int
    is_available: bool
    reason: Optional[str] = None
    until: Optional[datetime] = None  # Auto re-enable after this time


class ItemAvailabilityResponse(BaseModel):
    """Item availability status."""
    id: int
    product_id: int
    location_id: Optional[int] = None
    is_available: bool = True
    unavailable_reason: Optional[str] = None
    unavailable_until: Optional[datetime] = None
    platforms_synced: Optional[Dict[str, bool]] = None
    last_sync_at: Optional[datetime] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class BulkAvailabilityUpdate(BaseModel):
    """Bulk update item availability."""
    items: List[ItemAvailabilityUpdate]


# Platform Mapping

class PlatformMappingBase(BaseModel):
    """Base platform mapping schema."""
    product_id: int
    integration_id: int
    platform_item_id: str
    platform_item_name: str


class PlatformMappingCreate(PlatformMappingBase):
    """Create platform mapping."""
    pass


class PlatformMappingResponse(PlatformMappingBase):
    """Platform mapping response."""
    id: int
    platform_price: Optional[float] = None
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


# Webhook Handling

class WebhookPayload(BaseModel):
    """Incoming webhook payload."""
    platform: DeliveryPlatform
    event_type: str
    payload: Dict[str, Any]
    signature: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook processing response."""
    status: str
    order_id: Optional[int] = None
    platform_order_id: Optional[str] = None
    message: Optional[str] = None


# Delivery Reports

class DeliverySummary(BaseModel):
    """Delivery summary statistics."""
    total_orders: int
    total_revenue: Decimal
    total_platform_fees: Decimal
    net_revenue: Decimal
    avg_order_value: Decimal
    by_platform: Dict[str, Dict[str, Any]]


class DeliveryPerformance(BaseModel):
    """Delivery performance metrics."""
    platform: DeliveryPlatform
    orders_count: int
    avg_prep_time_minutes: float
    avg_delivery_time_minutes: float
    on_time_rate: float
    cancellation_rate: float
    customer_rating: Optional[float] = None


class PlatformComparison(BaseModel):
    """Compare performance across platforms."""
    date_range: Dict[str, str]
    platforms: List[DeliveryPerformance]
    best_performer: str
    recommendations: List[str]
