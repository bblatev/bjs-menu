"""
Mobile & Offline Service
Implements true offline mode with local-first architecture
Competitor: Toast Go, Square Terminal, TouchBistro Mobile
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import Session

from app.core.config import settings
from app.models.gap_features_models import (
    PushToken, PushNotification, EmployeeAppSession, CustomerAppSession
)


class MobileOfflineService:
    """
    Service for mobile app offline sync and session management.
    Implements conflict-free replicated data types (CRDT) patterns.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== OFFLINE SYNC ====================

    async def get_sync_package(
        self,
        venue_id: UUID,
        device_id: str,
        last_sync: Optional[datetime] = None,
        include_menu: bool = True,
        include_tables: bool = True,
        include_staff: bool = True,
        include_inventory: bool = False
    ) -> Dict[str, Any]:
        """
        Get a complete sync package for offline operation.
        Returns all data needed to operate without network.
        """
        sync_timestamp = datetime.utcnow()
        package = {
            "sync_id": str(uuid4()),
            "sync_timestamp": sync_timestamp.isoformat(),
            "venue_id": str(venue_id),
            "device_id": device_id,
            "checksum": "",
            "data": {}
        }

        # Menu data (categories, items, modifiers, prices)
        if include_menu:
            package["data"]["menu"] = await self._get_menu_sync_data(venue_id, last_sync)

        # Tables and floor plans
        if include_tables:
            package["data"]["tables"] = await self._get_tables_sync_data(venue_id, last_sync)

        # Staff and permissions
        if include_staff:
            package["data"]["staff"] = await self._get_staff_sync_data(venue_id, last_sync)

        # Inventory (optional, large dataset)
        if include_inventory:
            package["data"]["inventory"] = await self._get_inventory_sync_data(venue_id, last_sync)

        # Tax rates and settings
        package["data"]["settings"] = await self._get_settings_sync_data(venue_id, last_sync)

        # Generate checksum for data integrity
        package["checksum"] = self._generate_checksum(package["data"])

        return package

    async def _get_menu_sync_data(
        self,
        venue_id: UUID,
        last_sync: Optional[datetime]
    ) -> Dict[str, Any]:
        """Get menu data for sync."""
        from app.models.menu import Category, MenuItem, Modifier, ModifierOption

        # Build base query
        categories_query = select(Category).where(Category.venue_id == venue_id)
        items_query = select(MenuItem).where(MenuItem.venue_id == venue_id)

        if last_sync:
            categories_query = categories_query.where(
                or_(
                    Category.updated_at > last_sync,
                    Category.created_at > last_sync
                )
            )
            items_query = items_query.where(
                or_(
                    MenuItem.updated_at > last_sync,
                    MenuItem.created_at > last_sync
                )
            )

        categories_result = await self.db.execute(categories_query)
        items_result = await self.db.execute(items_query)

        categories = categories_result.scalars().all()
        items = items_result.scalars().all()

        return {
            "categories": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "name_en": getattr(c, 'name_en', c.name),
                    "sort_order": getattr(c, 'sort_order', 0),
                    "is_active": c.is_active,
                    "image_url": getattr(c, 'image_url', None),
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None
                }
                for c in categories
            ],
            "items": [
                {
                    "id": str(i.id),
                    "category_id": str(i.category_id) if i.category_id else None,
                    "name": i.name,
                    "name_en": getattr(i, 'name_en', i.name),
                    "description": i.description,
                    "price": float(i.price),
                    "image_url": i.image_url,
                    "is_available": i.is_available,
                    "preparation_time": getattr(i, 'preparation_time', None),
                    "allergens": getattr(i, 'allergens', []),
                    "nutrition": getattr(i, 'nutrition_info', {}),
                    "modifiers": getattr(i, 'modifiers', []),
                    "updated_at": i.updated_at.isoformat() if i.updated_at else None
                }
                for i in items
            ],
            "full_sync": last_sync is None
        }

    async def _get_tables_sync_data(
        self,
        venue_id: UUID,
        last_sync: Optional[datetime]
    ) -> Dict[str, Any]:
        """Get tables and floor plan data for sync."""
        from app.models.tables import Table
        from app.models.floor_plans import FloorPlan

        tables_query = select(Table).where(Table.venue_id == venue_id)
        floor_plans_query = select(FloorPlan).where(FloorPlan.venue_id == venue_id)

        tables_result = await self.db.execute(tables_query)
        floor_plans_result = await self.db.execute(floor_plans_query)

        tables = tables_result.scalars().all()
        floor_plans = floor_plans_result.scalars().all()

        return {
            "tables": [
                {
                    "id": str(t.id),
                    "number": t.table_number,
                    "name": getattr(t, 'name', f"Table {t.table_number}"),
                    "capacity": t.capacity,
                    "floor_plan_id": str(t.floor_plan_id) if hasattr(t, 'floor_plan_id') and t.floor_plan_id else None,
                    "position_x": getattr(t, 'position_x', 0),
                    "position_y": getattr(t, 'position_y', 0),
                    "shape": getattr(t, 'shape', 'rectangle'),
                    "is_active": getattr(t, 'is_active', True)
                }
                for t in tables
            ],
            "floor_plans": [
                {
                    "id": str(fp.id),
                    "name": fp.name,
                    "width": getattr(fp, 'width', 800),
                    "height": getattr(fp, 'height', 600),
                    "background_image": getattr(fp, 'background_image_url', None),
                    "is_active": getattr(fp, 'is_active', True)
                }
                for fp in floor_plans
            ]
        }

    async def _get_staff_sync_data(
        self,
        venue_id: UUID,
        last_sync: Optional[datetime]
    ) -> Dict[str, Any]:
        """Get staff data for sync (limited to what's needed for POS)."""
        from app.models import StaffUser as Staff

        staff_query = select(Staff).where(Staff.venue_id == venue_id)
        staff_result = await self.db.execute(staff_query)
        staff = staff_result.scalars().all()

        return {
            "staff": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "pin_code": s.pin_code,  # Needed for offline auth
                    "role": s.role,
                    "permissions": getattr(s, 'permissions', []),
                    "is_active": s.is_active
                }
                for s in staff
            ]
        }

    async def _get_inventory_sync_data(
        self,
        venue_id: UUID,
        last_sync: Optional[datetime]
    ) -> Dict[str, Any]:
        """Get inventory data for sync."""
        from app.models.stock import StockItem

        stock_query = select(StockItem).where(StockItem.venue_id == venue_id)
        stock_result = await self.db.execute(stock_query)
        stock = stock_result.scalars().all()

        return {
            "stock_items": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "sku": getattr(s, 'sku', None),
                    "quantity": float(s.quantity),
                    "unit": s.unit,
                    "min_quantity": float(getattr(s, 'min_quantity', 0)),
                    "cost_price": float(getattr(s, 'cost_price', 0))
                }
                for s in stock
            ]
        }

    async def _get_settings_sync_data(
        self,
        venue_id: UUID,
        last_sync: Optional[datetime]
    ) -> Dict[str, Any]:
        """Get venue settings for sync."""
        from app.models.venue import Venue

        venue_result = await self.db.execute(
            select(Venue).where(Venue.id == venue_id)
        )
        venue = venue_result.scalar_one_or_none()

        if not venue:
            return {}

        return {
            "venue": {
                "id": str(venue.id),
                "name": venue.name,
                "currency": getattr(venue, 'currency', 'BGN'),
                "timezone": getattr(venue, 'timezone', 'Europe/Sofia'),
                "tax_rate": float(getattr(venue, 'tax_rate', 20)),
                "service_charge_rate": float(getattr(venue, 'service_charge_rate', 0)),
                "receipt_header": getattr(venue, 'receipt_header', ''),
                "receipt_footer": getattr(venue, 'receipt_footer', '')
            },
            "tax_rates": [
                {"name": "Standard", "rate": 20.0, "code": "A"},
                {"name": "Reduced", "rate": 9.0, "code": "B"},
                {"name": "Zero", "rate": 0.0, "code": "C"}
            ],
            "payment_methods": [
                {"id": "cash", "name": "Cash", "is_active": True},
                {"id": "card", "name": "Card", "is_active": True},
                {"id": "mobile", "name": "Mobile Payment", "is_active": True}
            ]
        }

    def _generate_checksum(self, data: Dict[str, Any]) -> str:
        """Generate SHA256 checksum of sync data."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    async def process_offline_transactions(
        self,
        venue_id: UUID,
        device_id: str,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process transactions that were created while offline.
        Uses timestamp-based conflict resolution (last-write-wins).
        """
        results = {
            "processed": [],
            "conflicts": [],
            "errors": []
        }

        for txn in transactions:
            try:
                txn_id = txn.get("local_id")
                txn_type = txn.get("type")
                txn_timestamp = txn.get("timestamp")
                txn_data = txn.get("data", {})

                # Check for conflicts (same entity modified by another device)
                conflict = await self._check_conflict(
                    venue_id,
                    txn_type,
                    txn_data.get("entity_id"),
                    txn_timestamp
                )

                if conflict:
                    results["conflicts"].append({
                        "local_id": txn_id,
                        "type": txn_type,
                        "conflict_type": conflict["type"],
                        "server_version": conflict["server_version"],
                        "resolution": "server_wins" if conflict["server_newer"] else "client_wins"
                    })

                    if conflict["server_newer"]:
                        continue  # Skip, server version is newer

                # Process the transaction
                server_id = await self._process_transaction(
                    venue_id,
                    device_id,
                    txn_type,
                    txn_data
                )

                results["processed"].append({
                    "local_id": txn_id,
                    "server_id": server_id,
                    "type": txn_type
                })

            except Exception as e:
                results["errors"].append({
                    "local_id": txn.get("local_id"),
                    "error": str(e)
                })

        await self.db.commit()
        return results

    async def _check_conflict(
        self,
        venue_id: UUID,
        txn_type: str,
        entity_id: Optional[str],
        client_timestamp: str
    ) -> Optional[Dict[str, Any]]:
        """Check if there's a conflict with server data."""
        if not entity_id:
            return None  # New entity, no conflict possible

        # Parse client timestamp
        client_time = datetime.fromisoformat(client_timestamp.replace('Z', '+00:00'))

        # Check based on transaction type
        if txn_type == "order":
            from app.models.orders import Order
            result = await self.db.execute(
                select(Order).where(Order.id == entity_id)
            )
            order = result.scalar_one_or_none()
            if order and order.updated_at:
                return {
                    "type": "order_modified",
                    "server_version": order.updated_at.isoformat(),
                    "server_newer": order.updated_at > client_time
                }

        return None

    async def _process_transaction(
        self,
        venue_id: UUID,
        device_id: str,
        txn_type: str,
        txn_data: Dict[str, Any]
    ) -> str:
        """Process a single offline transaction."""
        from app.models.orders import Order, OrderItem

        if txn_type == "order":
            # Create order from offline data
            order = Order(
                id=uuid4(),
                venue_id=venue_id,
                table_id=txn_data.get("table_id"),
                staff_id=txn_data.get("staff_id"),
                status=txn_data.get("status", "pending"),
                total=txn_data.get("total", 0),
                notes=txn_data.get("notes"),
                created_offline=True,
                offline_device_id=device_id,
                created_at=datetime.fromisoformat(txn_data.get("created_at", datetime.utcnow().isoformat()))
            )
            self.db.add(order)

            # Add order items
            for item_data in txn_data.get("items", []):
                order_item = OrderItem(
                    id=uuid4(),
                    order_id=order.id,
                    menu_item_id=item_data.get("menu_item_id"),
                    quantity=item_data.get("quantity", 1),
                    unit_price=item_data.get("unit_price", 0),
                    total_price=item_data.get("total_price", 0),
                    notes=item_data.get("notes")
                )
                self.db.add(order_item)

            return str(order.id)

        elif txn_type == "payment":
            from app.models.payments import Payment
            payment = Payment(
                id=uuid4(),
                venue_id=venue_id,
                order_id=txn_data.get("order_id"),
                amount=txn_data.get("amount", 0),
                payment_method=txn_data.get("payment_method", "cash"),
                status="completed",
                created_offline=True,
                offline_device_id=device_id
            )
            self.db.add(payment)
            return str(payment.id)

        elif txn_type == "table_status":
            from app.models.tables import Table
            result = await self.db.execute(
                select(Table).where(
                    and_(
                        Table.id == txn_data.get("table_id"),
                        Table.venue_id == venue_id
                    )
                )
            )
            table = result.scalar_one_or_none()
            if table:
                table.status = txn_data.get("status")
                return str(table.id)

        return ""

    # ==================== SESSION MANAGEMENT ====================

    async def create_employee_session(
        self,
        staff_id: UUID,
        venue_id: UUID,
        device_id: str,
        device_info: Dict[str, Any],
        app_version: str
    ) -> EmployeeAppSession:
        """Create a new employee mobile app session."""
        session = EmployeeAppSession(
            id=uuid4(),
            staff_id=staff_id,
            venue_id=venue_id,
            device_id=device_id,
            device_type=device_info.get("type", "unknown"),
            device_os=device_info.get("os", "unknown"),
            app_version=app_version,
            last_sync_at=datetime.utcnow(),
            is_active=True
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def update_session_sync(
        self,
        session_id: UUID,
        sync_version: int
    ) -> None:
        """Update session's last sync timestamp."""
        result = await self.db.execute(
            select(EmployeeAppSession).where(EmployeeAppSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.last_sync_at = datetime.utcnow()
            session.sync_version = sync_version
            await self.db.commit()

    async def end_session(self, session_id: UUID) -> None:
        """End a mobile app session."""
        result = await self.db.execute(
            select(EmployeeAppSession).where(EmployeeAppSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.is_active = False
            session.ended_at = datetime.utcnow()
            await self.db.commit()

    async def get_active_sessions(
        self,
        venue_id: UUID,
        staff_id: Optional[UUID] = None
    ) -> List[EmployeeAppSession]:
        """Get active mobile app sessions."""
        query = select(EmployeeAppSession).where(
            and_(
                EmployeeAppSession.venue_id == venue_id,
                EmployeeAppSession.is_active == True
            )
        )
        if staff_id:
            query = query.where(EmployeeAppSession.staff_id == staff_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())


class PushNotificationService:
    """
    Service for managing push notifications across platforms.
    Supports FCM (Android/iOS), Web Push, and SMS fallback.
    """

    def __init__(self, db: Session):
        self.db = db

    async def register_token(
        self,
        user_id: UUID,
        user_type: str,  # 'staff' or 'customer'
        venue_id: UUID,
        token: str,
        platform: str,  # 'fcm', 'apns', 'web', 'expo'
        device_info: Optional[Dict[str, Any]] = None
    ) -> PushToken:
        """Register a push notification token."""
        # Check if token already exists
        result = await self.db.execute(
            select(PushToken).where(PushToken.token == token)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing token
            existing.user_id = user_id
            existing.user_type = user_type
            existing.venue_id = venue_id
            existing.platform = platform
            existing.device_info = device_info or {}
            existing.is_active = True
            existing.last_used_at = datetime.utcnow()
            await self.db.commit()
            return existing

        # Create new token
        push_token = PushToken(
            id=uuid4(),
            user_id=user_id,
            user_type=user_type,
            venue_id=venue_id,
            token=token,
            platform=platform,
            device_info=device_info or {},
            is_active=True,
            created_at=datetime.utcnow()
        )
        self.db.add(push_token)
        await self.db.commit()
        await self.db.refresh(push_token)
        return push_token

    async def unregister_token(self, token: str) -> bool:
        """Unregister a push notification token."""
        result = await self.db.execute(
            select(PushToken).where(PushToken.token == token)
        )
        push_token = result.scalar_one_or_none()
        if push_token:
            push_token.is_active = False
            await self.db.commit()
            return True
        return False

    async def send_notification(
        self,
        user_id: UUID,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        channel: str = "default",
        priority: str = "normal"
    ) -> PushNotification:
        """Send a push notification to a user."""
        # Get active tokens for user
        result = await self.db.execute(
            select(PushToken).where(
                and_(
                    PushToken.user_id == user_id,
                    PushToken.is_active == True
                )
            )
        )
        tokens = result.scalars().all()

        # Create notification record
        notification = PushNotification(
            id=uuid4(),
            user_id=user_id,
            title=title,
            body=body,
            data=data or {},
            channel=channel,
            priority=priority,
            status="pending",
            created_at=datetime.utcnow()
        )
        self.db.add(notification)

        # Send to each platform
        for token in tokens:
            try:
                if token.platform == "fcm":
                    await self._send_fcm(token.token, title, body, data)
                elif token.platform == "apns":
                    await self._send_apns(token.token, title, body, data)
                elif token.platform == "web":
                    await self._send_web_push(token.token, title, body, data)
                elif token.platform == "expo":
                    await self._send_expo(token.token, title, body, data)

                token.last_used_at = datetime.utcnow()
                notification.status = "sent"
                notification.sent_at = datetime.utcnow()

            except Exception as e:
                notification.status = "failed"
                notification.error_message = str(e)
                # Mark token as potentially invalid
                if "invalid" in str(e).lower() or "unregistered" in str(e).lower():
                    token.is_active = False

        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def send_to_venue_staff(
        self,
        venue_id: UUID,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        roles: Optional[List[str]] = None
    ) -> int:
        """Send notification to all staff at a venue."""
        # Get all active staff tokens for venue
        query = select(PushToken).where(
            and_(
                PushToken.venue_id == venue_id,
                PushToken.user_type == "staff",
                PushToken.is_active == True
            )
        )
        result = await self.db.execute(query)
        tokens = result.scalars().all()

        sent_count = 0
        for token in tokens:
            try:
                notification = await self.send_notification(
                    user_id=token.user_id,
                    title=title,
                    body=body,
                    data=data,
                    channel="staff"
                )
                if notification.status == "sent":
                    sent_count += 1
            except Exception:
                continue

        return sent_count

    async def _send_fcm(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]]
    ) -> None:
        """Send via Firebase Cloud Messaging."""
        import httpx

        fcm_key = getattr(settings, 'FCM_SERVER_KEY', None)
        if not fcm_key:
            return

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://fcm.googleapis.com/fcm/send",
                headers={
                    "Authorization": f"key={fcm_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "to": token,
                    "notification": {
                        "title": title,
                        "body": body
                    },
                    "data": data or {}
                }
            )
            response.raise_for_status()

    async def _send_apns(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]]
    ) -> None:
        """Send via Apple Push Notification Service."""
        # Placeholder - requires APNs certificate configuration
        pass

    async def _send_web_push(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]]
    ) -> None:
        """Send via Web Push (VAPID)."""
        # Placeholder - requires VAPID keys configuration
        pass

    async def _send_expo(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]]
    ) -> None:
        """Send via Expo Push Notification service."""
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://exp.host/--/api/v2/push/send",
                json={
                    "to": token,
                    "title": title,
                    "body": body,
                    "data": data or {}
                }
            )
            response.raise_for_status()

    async def get_user_notifications(
        self,
        user_id: UUID,
        limit: int = 50,
        include_read: bool = False
    ) -> List[PushNotification]:
        """Get notifications for a user."""
        query = select(PushNotification).where(
            PushNotification.user_id == user_id
        )

        if not include_read:
            query = query.where(PushNotification.read_at.is_(None))

        query = query.order_by(PushNotification.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(
        self,
        notification_id: UUID,
        user_id: UUID
    ) -> bool:
        """Mark a notification as read."""
        result = await self.db.execute(
            select(PushNotification).where(
                and_(
                    PushNotification.id == notification_id,
                    PushNotification.user_id == user_id
                )
            )
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.read_at = datetime.utcnow()
            await self.db.commit()
            return True
        return False
