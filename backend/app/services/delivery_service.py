"""Delivery Aggregator Integration Service - DoorDash/Uber Eats/Deliverect style."""

import httpx
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.delivery import (
    DeliveryIntegration, DeliveryOrder, DeliveryOrderItem,
    MenuSync, ItemAvailability, DeliveryPlatformMapping,
    DeliveryPlatform, DeliveryOrderStatus
)
from app.models.product import Product


class DeliveryAggregatorService:
    """Base service for delivery platform integrations."""

    def __init__(self, db: Session):
        self.db = db

    def get_integration(
        self,
        platform: DeliveryPlatform,
        location_id: Optional[int] = None
    ) -> Optional[DeliveryIntegration]:
        """Get delivery integration configuration."""
        query = self.db.query(DeliveryIntegration).filter(
            DeliveryIntegration.platform == platform,
            DeliveryIntegration.is_active == True
        )
        if location_id:
            query = query.filter(DeliveryIntegration.location_id == location_id)

        return query.first()

    def get_all_integrations(
        self,
        location_id: Optional[int] = None
    ) -> List[DeliveryIntegration]:
        """Get all active delivery integrations."""
        query = self.db.query(DeliveryIntegration).filter(
            DeliveryIntegration.is_active == True
        )
        if location_id:
            query = query.filter(DeliveryIntegration.location_id == location_id)

        return query.all()

    async def process_incoming_order(
        self,
        platform: DeliveryPlatform,
        payload: Dict[str, Any]
    ) -> DeliveryOrder:
        """Process an incoming order from a delivery platform."""
        integration = self.get_integration(platform)
        if not integration:
            raise ValueError(f"No active integration for {platform}")

        # Create order record
        order = DeliveryOrder(
            integration_id=integration.id,
            location_id=integration.location_id,
            platform=platform,
            platform_order_id=payload.get("order_id", ""),
            platform_display_id=payload.get("display_id"),
            status=DeliveryOrderStatus.RECEIVED,
            customer_name=payload.get("customer", {}).get("name"),
            customer_phone=payload.get("customer", {}).get("phone"),
            delivery_address=payload.get("delivery_address"),
            delivery_instructions=payload.get("delivery_instructions"),
            subtotal=payload.get("subtotal", 0),
            tax=payload.get("tax", 0),
            delivery_fee=payload.get("delivery_fee", 0),
            tip=payload.get("tip", 0),
            total=payload.get("total", 0),
            special_instructions=payload.get("special_instructions"),
            is_scheduled=payload.get("is_scheduled", False),
            scheduled_for=payload.get("scheduled_for"),
            estimated_pickup_at=payload.get("estimated_pickup_time"),
            raw_payload=payload
        )

        try:
            with self.db.begin_nested():
                self.db.add(order)
                self.db.flush()

                # Process order items
                for item_data in payload.get("items", []):
                    # Try to map to local product
                    product_id = self._map_platform_item(
                        integration.id,
                        item_data.get("id"),
                        item_data.get("name")
                    )

                    item = DeliveryOrderItem(
                        order_id=order.id,
                        platform_item_id=item_data.get("id"),
                        item_name=item_data.get("name", "Unknown"),
                        quantity=item_data.get("quantity", 1),
                        unit_price=item_data.get("unit_price", 0),
                        total_price=item_data.get("total_price", 0),
                        modifiers=item_data.get("modifiers"),
                        special_instructions=item_data.get("special_instructions"),
                        product_id=product_id
                    )
                    self.db.add(item)

                # Auto-accept if configured
                if integration.auto_accept_orders:
                    order.status = DeliveryOrderStatus.CONFIRMED
                    order.confirmed_at = datetime.now(timezone.utc)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to process incoming delivery order: {str(e)}")

        # Send to KDS if configured
        if integration.auto_accept_orders:
            await self._send_to_kds(order)

        return order

    def _map_platform_item(
        self,
        integration_id: int,
        platform_item_id: Optional[str],
        item_name: Optional[str]
    ) -> Optional[int]:
        """Map platform item to local product."""
        if platform_item_id:
            mapping = self.db.query(DeliveryPlatformMapping).filter(
                DeliveryPlatformMapping.integration_id == integration_id,
                DeliveryPlatformMapping.platform_item_id == platform_item_id
            ).first()
            if mapping:
                return mapping.product_id

        # Try fuzzy match by name
        if item_name:
            product = self.db.query(Product).filter(
                Product.name.ilike(f"%{item_name[:30]}%")
            ).first()
            if product:
                return product.id

        return None

    async def _send_to_kds(self, order: DeliveryOrder) -> None:
        """Send order to Kitchen Display System."""
        # This would integrate with KDS
        # For now, just mark as sent
        order.sent_to_kds = True
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            import logging
            logging.getLogger(__name__).warning(f"Failed to mark order as sent to KDS: {e}")

    async def update_order_status(
        self,
        order_id: int,
        new_status: DeliveryOrderStatus
    ) -> DeliveryOrder:
        """Update order status and notify platform."""
        order = self.db.query(DeliveryOrder).filter(
            DeliveryOrder.id == order_id
        ).first()

        if not order:
            raise ValueError("Order not found")

        order.status = new_status
        order.status_updated_at = datetime.now(timezone.utc)

        # Set timestamps based on status
        if new_status == DeliveryOrderStatus.CONFIRMED:
            order.confirmed_at = datetime.now(timezone.utc)
        elif new_status == DeliveryOrderStatus.READY_FOR_PICKUP:
            order.ready_at = datetime.now(timezone.utc)
        elif new_status == DeliveryOrderStatus.PICKED_UP:
            order.picked_up_at = datetime.now(timezone.utc)
        elif new_status == DeliveryOrderStatus.DELIVERED:
            order.delivered_at = datetime.now(timezone.utc)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to update delivery order status: {str(e)}")

        # Notify platform
        await self._notify_platform_status(order)

        return order

    async def _notify_platform_status(self, order: DeliveryOrder) -> None:
        """Notify delivery platform of status change via their API."""
        integration = self.db.query(DeliveryIntegration).filter(
            DeliveryIntegration.id == order.integration_id
        ).first()

        if not integration or not integration.api_key:
            return

        status_payload = {
            "order_id": order.platform_order_id,
            "status": order.status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        platform_urls = {
            DeliveryPlatform.UBER_EATS: "https://api.uber.com/v1/eats/orders/{order_id}/status",
            DeliveryPlatform.DOORDASH: "https://openapi.doordash.com/drive/v2/deliveries/{order_id}",
            DeliveryPlatform.WOLT: "https://restaurant-api.wolt.com/v1/orders/{order_id}/status",
            DeliveryPlatform.GLOVO: "https://storeapi.glovoapp.com/webhook/stores/orders/{order_id}",
            DeliveryPlatform.DELIVEROO: "https://api.deliveroo.com/order/v1/orders/{order_id}/status",
        }

        url_template = platform_urls.get(order.platform)
        if not url_template:
            return

        url = url_template.format(order_id=order.platform_order_id)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.put(
                    url,
                    json=status_payload,
                    headers={
                        "Authorization": f"Bearer {integration.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code >= 400:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Platform status update failed for {order.platform.value}: "
                        f"{response.status_code} {response.text[:200]}"
                    )
        except httpx.RequestError as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Platform status update request failed for {order.platform.value}: {e}"
            )


class MenuSyncService:
    """Sync menu with delivery platforms."""

    def __init__(self, db: Session):
        self.db = db

    async def sync_menu_to_platform(
        self,
        integration_id: int,
        full_sync: bool = True
    ) -> MenuSync:
        """Sync menu to a delivery platform."""
        integration = self.db.query(DeliveryIntegration).filter(
            DeliveryIntegration.id == integration_id
        ).first()

        if not integration:
            raise ValueError("Integration not found")

        sync_record = MenuSync(
            integration_id=integration_id,
            sync_type="full" if full_sync else "incremental",
            started_at=datetime.now(timezone.utc)
        )
        self.db.add(sync_record)
        self.db.flush()

        try:
            # Get products to sync
            products = self.db.query(Product).filter(
                Product.is_active == True
            ).all()

            items_synced = 0
            items_failed = 0

            for product in products:
                try:
                    await self._sync_product(integration, product)
                    items_synced += 1
                except Exception as e:
                    items_failed += 1

            sync_record.success = True
            sync_record.items_synced = items_synced
            sync_record.items_failed = items_failed
            sync_record.completed_at = datetime.now(timezone.utc)

            integration.is_menu_synced = True
            integration.last_menu_sync_at = datetime.now(timezone.utc)

        except Exception as e:
            sync_record.success = False
            sync_record.error_message = str(e)
            sync_record.completed_at = datetime.now(timezone.utc)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to save menu sync record: {str(e)}")
        return sync_record

    async def _sync_product(
        self,
        integration: DeliveryIntegration,
        product: Product
    ) -> None:
        """Sync a single product to platform."""
        # Check for existing mapping
        mapping = self.db.query(DeliveryPlatformMapping).filter(
            DeliveryPlatformMapping.integration_id == integration.id,
            DeliveryPlatformMapping.product_id == product.id
        ).first()

        # Build product data for platform
        product_data = {
            "name": product.name,
            "description": product.description,
            "price": product.sell_price,
            "is_available": product.is_active
        }

        # This would call the platform API
        # For now, just update mapping
        if not mapping:
            mapping = DeliveryPlatformMapping(
                product_id=product.id,
                integration_id=integration.id,
                platform_item_id=f"{integration.platform}_{product.id}",
                platform_item_name=product.name
            )
            self.db.add(mapping)

    async def update_item_availability(
        self,
        product_id: int,
        is_available: bool,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update item availability across all platforms (86 item)."""
        # Update local availability record
        availability = self.db.query(ItemAvailability).filter(
            ItemAvailability.product_id == product_id
        ).first()

        if not availability:
            availability = ItemAvailability(product_id=product_id)
            self.db.add(availability)

        availability.is_available = is_available
        availability.unavailable_reason = reason if not is_available else None
        availability.updated_at = datetime.now(timezone.utc)

        # Get all active integrations
        integrations = self.db.query(DeliveryIntegration).filter(
            DeliveryIntegration.is_active == True,
            DeliveryIntegration.sync_inventory == True
        ).all()

        results = {}
        for integration in integrations:
            try:
                await self._update_platform_availability(
                    integration, product_id, is_available
                )
                results[integration.platform.value] = True
            except Exception as e:
                results[integration.platform.value] = False

        availability.platforms_synced = results
        availability.last_sync_at = datetime.now(timezone.utc)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to update item availability: {str(e)}")

        return {
            "product_id": product_id,
            "is_available": is_available,
            "platforms_updated": results
        }

    async def _update_platform_availability(
        self,
        integration: DeliveryIntegration,
        product_id: int,
        is_available: bool
    ) -> None:
        """Update item availability on a specific delivery platform."""
        mapping = self.db.query(DeliveryPlatformMapping).filter(
            DeliveryPlatformMapping.integration_id == integration.id,
            DeliveryPlatformMapping.product_id == product_id
        ).first()

        if not mapping or not integration.api_key:
            return

        availability_payload = {
            "item_id": mapping.platform_item_id,
            "is_available": is_available,
        }

        platform_urls = {
            DeliveryPlatform.UBER_EATS: "https://api.uber.com/v1/eats/stores/{store_id}/menus/items/{item_id}",
            DeliveryPlatform.DOORDASH: "https://openapi.doordash.com/drive/v2/menus/items/{item_id}/availability",
            DeliveryPlatform.WOLT: "https://restaurant-api.wolt.com/v1/restaurants/{store_id}/items/{item_id}/availability",
            DeliveryPlatform.GLOVO: "https://storeapi.glovoapp.com/webhook/stores/{store_id}/products/{item_id}",
            DeliveryPlatform.DELIVEROO: "https://api.deliveroo.com/menu/v1/items/{item_id}/availability",
        }

        url_template = platform_urls.get(integration.platform)
        if not url_template:
            return

        url = url_template.format(
            store_id=integration.store_id or "",
            item_id=mapping.platform_item_id,
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.patch(
                    url,
                    json=availability_payload,
                    headers={
                        "Authorization": f"Bearer {integration.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code >= 400:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Availability update failed for {integration.platform.value}: "
                        f"{response.status_code}"
                    )
        except httpx.RequestError as e:
            import logging
            logging.getLogger(__name__).warning(
                f"Availability update request failed for {integration.platform.value}: {e}"
            )


class DeliveryWebhookHandler:
    """Handle webhooks from delivery platforms."""

    def __init__(self, db: Session):
        self.db = db
        self.aggregator = DeliveryAggregatorService(db)

    def verify_webhook(
        self,
        platform: DeliveryPlatform,
        signature: str,
        payload: bytes
    ) -> bool:
        """Verify webhook signature."""
        integration = self.aggregator.get_integration(platform)
        if not integration or not integration.webhook_secret:
            return False

        # Calculate expected signature
        expected = hmac.new(
            integration.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    async def handle_webhook(
        self,
        platform: DeliveryPlatform,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle incoming webhook event."""
        handlers = {
            "order.created": self._handle_new_order,
            "order.updated": self._handle_order_update,
            "order.cancelled": self._handle_order_cancel,
            "menu.update_required": self._handle_menu_update_request,
        }

        handler = handlers.get(event_type)
        if handler:
            return await handler(platform, payload)

        return {"status": "unhandled", "event_type": event_type}

    async def _handle_new_order(
        self,
        platform: DeliveryPlatform,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle new order webhook."""
        order = await self.aggregator.process_incoming_order(platform, payload)
        return {
            "status": "success",
            "order_id": order.id,
            "platform_order_id": order.platform_order_id
        }

    async def _handle_order_update(
        self,
        platform: DeliveryPlatform,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle order update webhook."""
        platform_order_id = payload.get("order_id")
        new_status = payload.get("status")

        order = self.db.query(DeliveryOrder).filter(
            DeliveryOrder.platform_order_id == platform_order_id,
            DeliveryOrder.platform == platform
        ).first()

        if order and new_status:
            # Map platform status to our status
            status_map = {
                "picked_up": DeliveryOrderStatus.PICKED_UP,
                "delivered": DeliveryOrderStatus.DELIVERED,
                "cancelled": DeliveryOrderStatus.CANCELLED
            }
            if new_status in status_map:
                await self.aggregator.update_order_status(
                    order.id, status_map[new_status]
                )

        return {"status": "success"}

    async def _handle_order_cancel(
        self,
        platform: DeliveryPlatform,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle order cancellation webhook."""
        platform_order_id = payload.get("order_id")

        order = self.db.query(DeliveryOrder).filter(
            DeliveryOrder.platform_order_id == platform_order_id,
            DeliveryOrder.platform == platform
        ).first()

        if order:
            await self.aggregator.update_order_status(
                order.id, DeliveryOrderStatus.CANCELLED
            )

        return {"status": "success"}

    async def _handle_menu_update_request(
        self,
        platform: DeliveryPlatform,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle menu update request from platform."""
        integration = self.aggregator.get_integration(platform)
        if integration:
            sync_service = MenuSyncService(self.db)
            await sync_service.sync_menu_to_platform(integration.id)

        return {"status": "success"}


class DeliveryReportingService:
    """Generate delivery-related reports."""

    def __init__(self, db: Session):
        self.db = db

    def get_delivery_summary(
        self,
        location_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get summary of delivery orders."""
        from sqlalchemy import func

        query = self.db.query(DeliveryOrder)

        if location_id:
            query = query.filter(DeliveryOrder.location_id == location_id)
        if start_date:
            query = query.filter(DeliveryOrder.received_at >= start_date)
        if end_date:
            query = query.filter(DeliveryOrder.received_at <= end_date)

        orders = query.all()

        # Group by platform
        by_platform = {}
        for order in orders:
            platform = order.platform.value
            if platform not in by_platform:
                by_platform[platform] = {
                    "count": 0,
                    "total_revenue": 0,
                    "total_fees": 0,
                    "net_revenue": 0
                }

            by_platform[platform]["count"] += 1
            by_platform[platform]["total_revenue"] += order.total or 0
            by_platform[platform]["total_fees"] += order.platform_fee or 0
            by_platform[platform]["net_revenue"] += order.net_payout or 0

        return {
            "total_orders": len(orders),
            "total_revenue": sum(o.total or 0 for o in orders),
            "total_platform_fees": sum(o.platform_fee or 0 for o in orders),
            "net_revenue": sum(o.net_payout or 0 for o in orders),
            "by_platform": by_platform,
            "avg_order_value": sum(o.total or 0 for o in orders) / len(orders) if orders else 0
        }
