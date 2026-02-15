"""
Multi-Location Management Service - Production Ready
Full database integration with SQLAlchemy models
"""

from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import uuid

from app.models.v31_models import (
    Location, LocationGroup, LocationGroupMember,
    LocationStaffAssignment, InventoryTransfer, InventoryTransferItem
)
from app.models import Stock


class MultiLocationService:
    """Production-ready Multi-Location Management Service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== LOCATION MANAGEMENT ==========
    
    def create_location(
        self,
        name: str,
        code: str,
        address: Dict[str, str],
        contact: Dict[str, str],
        timezone: str = "Europe/Sofia",
        currency: str = "EUR",
        location_type: str = "standard",
        copy_menu_from: Optional[int] = None,
        copy_settings_from: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new location in database"""
        
        # Check if code already exists
        existing = self.db.query(Location).filter(Location.code == code).first()
        if existing:
            return {"success": False, "error": f"Location code '{code}' already exists"}
        
        # Create location
        location = Location(
            code=code,
            name=name,
            location_type=location_type,
            street=address.get("street"),
            city=address.get("city"),
            region=address.get("region"),
            postal_code=address.get("postal_code"),
            country=address.get("country", "Bulgaria"),
            phone=contact.get("phone"),
            email=contact.get("email"),
            timezone=timezone,
            currency=currency,
            status="coming_soon",
            is_primary=False
        )
        
        # Copy settings from existing location
        if copy_settings_from:
            source = self.db.query(Location).filter(Location.id == copy_settings_from).first()
            if source:
                location.operating_hours = source.operating_hours
                location.features = source.features
                location.settings = source.settings
        
        # Set menu source
        if copy_menu_from:
            location.menu_source_id = copy_menu_from
            location.menu_sync_enabled = True
        
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        
        return {
            "success": True,
            "location_id": location.id,
            "code": location.code,
            "name": location.name,
            "status": location.status,
            "message": f"Location '{name}' created successfully"
        }
    
    def update_location(
        self,
        location_id: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update location details"""
        location = self.db.query(Location).filter(Location.id == location_id).first()
        if not location:
            return {"success": False, "error": "Location not found"}
        
        # Prevent changing primary status directly
        if "is_primary" in updates:
            del updates["is_primary"]
        
        # Update allowed fields
        allowed_fields = [
            "name", "street", "city", "region", "postal_code", "country",
            "phone", "email", "timezone", "currency", "operating_hours",
            "features", "settings", "latitude", "longitude"
        ]
        
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(location, key, value)
        
        self.db.commit()
        
        return {
            "success": True,
            "location_id": location_id,
            "message": "Location updated successfully"
        }
    
    def set_location_status(
        self,
        location_id: int,
        status: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Set location status"""
        valid_statuses = ["active", "inactive", "temporarily_closed", "coming_soon"]
        
        if status not in valid_statuses:
            return {"success": False, "error": f"Invalid status. Use: {valid_statuses}"}
        
        location = self.db.query(Location).filter(Location.id == location_id).first()
        if not location:
            return {"success": False, "error": "Location not found"}
        
        location.status = status
        self.db.commit()
        
        return {
            "success": True,
            "location_id": location_id,
            "status": status,
            "message": f"Location status set to {status}"
        }
    
    def get_location(self, location_id: int) -> Dict[str, Any]:
        """Get location details"""
        location = self.db.query(Location).filter(Location.id == location_id).first()
        if not location:
            return {"success": False, "error": "Location not found"}
        
        return {
            "success": True,
            "location": {
                "id": location.id,
                "code": location.code,
                "name": location.name,
                "location_type": location.location_type,
                "address": {
                    "street": location.street,
                    "city": location.city,
                    "region": location.region,
                    "postal_code": location.postal_code,
                    "country": location.country
                },
                "contact": {
                    "phone": location.phone,
                    "email": location.email
                },
                "timezone": location.timezone,
                "currency": location.currency,
                "status": location.status,
                "is_primary": location.is_primary,
                "operating_hours": location.operating_hours,
                "features": location.features,
                "created_at": location.created_at.isoformat() if location.created_at else None
            }
        }
    
    def list_locations(
        self,
        status: Optional[str] = None,
        include_metrics: bool = False
    ) -> Dict[str, Any]:
        """List all locations"""
        query = self.db.query(Location)
        
        if status:
            query = query.filter(Location.status == status)
        
        locations = query.all()
        
        result = []
        for loc in locations:
            loc_data = {
                "id": loc.id,
                "code": loc.code,
                "name": loc.name,
                "location_type": loc.location_type,
                "city": loc.city,
                "status": loc.status,
                "is_primary": loc.is_primary
            }
            
            if include_metrics:
                loc_data["metrics"] = self._get_location_metrics(loc.id)
            
            result.append(loc_data)
        
        return {
            "success": True,
            "locations": result,
            "total": len(result),
            "active": len([l for l in result if l["status"] == "active"])
        }
    
    def _get_location_metrics(self, location_id: int) -> Dict[str, Any]:
        """Get real metrics for a location from database"""
        # Query actual orders and sales
        from app.models import Order
        
        today = date.today()
        
        # Today's sales
        today_sales = self.db.query(func.sum(Order.total)).filter(
            and_(
                Order.venue_id == location_id,
                func.date(Order.created_at) == today,
                Order.status.in_(["completed", "paid"])
            )
        ).scalar() or 0
        
        # Today's orders
        today_orders = self.db.query(func.count(Order.id)).filter(
            and_(
                Order.venue_id == location_id,
                func.date(Order.created_at) == today
            )
        ).scalar() or 0
        
        return {
            "today_sales": float(today_sales),
            "today_orders": today_orders,
            "avg_ticket": round(float(today_sales) / today_orders, 2) if today_orders > 0 else 0,
        }
    
    # ========== LOCATION GROUPS ==========
    
    def create_location_group(
        self,
        name: str,
        description: str,
        location_ids: List[int]
    ) -> Dict[str, Any]:
        """Create a location group"""
        group = LocationGroup(
            name=name,
            description=description
        )
        self.db.add(group)
        self.db.flush()
        
        # Add members
        for loc_id in location_ids:
            location = self.db.query(Location).filter(Location.id == loc_id).first()
            if location:
                member = LocationGroupMember(
                    group_id=group.id,
                    location_id=loc_id
                )
                self.db.add(member)
        
        self.db.commit()
        
        return {
            "success": True,
            "group_id": group.id,
            "name": name,
            "member_count": len(location_ids)
        }
    
    # ========== STAFF MANAGEMENT ==========
    
    def assign_staff_to_location(
        self,
        staff_id: int,
        location_id: int,
        role: str,
        is_primary: bool = True
    ) -> Dict[str, Any]:
        """Assign staff to a location"""
        location = self.db.query(Location).filter(Location.id == location_id).first()
        if not location:
            return {"success": False, "error": "Location not found"}
        
        assignment = LocationStaffAssignment(
            location_id=location_id,
            staff_id=staff_id,
            role=role,
            is_primary=is_primary
        )
        self.db.add(assignment)
        self.db.commit()
        
        return {
            "success": True,
            "staff_id": staff_id,
            "location_id": location_id,
            "role": role,
            "message": f"Staff assigned to {location.name}"
        }
    
    def get_location_staff(self, location_id: int) -> Dict[str, Any]:
        """Get all staff assigned to a location"""
        location = self.db.query(Location).filter(Location.id == location_id).first()
        if not location:
            return {"success": False, "error": "Location not found"}
        
        assignments = self.db.query(LocationStaffAssignment).filter(
            LocationStaffAssignment.location_id == location_id
        ).all()
        
        staff_list = []
        for a in assignments:
            staff_list.append({
                "staff_id": a.staff_id,
                "role": a.role,
                "is_primary": a.is_primary,
                "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None
            })
        
        return {
            "success": True,
            "location_id": location_id,
            "location_name": location.name,
            "staff": staff_list,
            "total_staff": len(staff_list)
        }
    
    # ========== INVENTORY TRANSFERS ==========
    
    def create_inventory_transfer(
        self,
        from_location_id: int,
        to_location_id: int,
        items: List[Dict[str, Any]],
        notes: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create inventory transfer between locations"""
        # Validate locations
        from_loc = self.db.query(Location).filter(Location.id == from_location_id).first()
        to_loc = self.db.query(Location).filter(Location.id == to_location_id).first()
        
        if not from_loc or not to_loc:
            return {"success": False, "error": "Invalid location(s)"}
        
        # Create transfer
        transfer_code = f"TRF-{uuid.uuid4().hex[:8].upper()}"
        
        transfer = InventoryTransfer(
            transfer_code=transfer_code,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            status="pending",
            notes=notes,
            created_by=created_by
        )
        self.db.add(transfer)
        self.db.flush()
        
        # Add items
        total_items = 0
        total_value = 0
        
        for item in items:
            transfer_item = InventoryTransferItem(
                transfer_id=transfer.id,
                stock_item_id=item["stock_item_id"],
                quantity_sent=item["quantity"],
                unit=item.get("unit"),
                unit_cost=item.get("unit_cost", 0)
            )
            self.db.add(transfer_item)
            total_items += item["quantity"]
            total_value += item["quantity"] * item.get("unit_cost", 0)
        
        self.db.commit()
        
        return {
            "success": True,
            "transfer_id": transfer.id,
            "transfer_code": transfer_code,
            "from_location": from_loc.name,
            "to_location": to_loc.name,
            "total_items": total_items,
            "total_value": float(total_value),
            "status": "pending"
        }
    
    def ship_inventory_transfer(self, transfer_id: int) -> Dict[str, Any]:
        """Mark transfer as shipped"""
        transfer = self.db.query(InventoryTransfer).filter(
            InventoryTransfer.id == transfer_id
        ).first()
        
        if not transfer:
            return {"success": False, "error": "Transfer not found"}
        
        transfer.status = "shipped"
        transfer.shipped_at = datetime.now(timezone.utc)
        self.db.commit()
        
        return {
            "success": True,
            "transfer_id": transfer_id,
            "status": "shipped"
        }
    
    def receive_inventory_transfer(
        self,
        transfer_id: int,
        received_items: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Mark transfer as received and update inventory"""
        transfer = self.db.query(InventoryTransfer).filter(
            InventoryTransfer.id == transfer_id
        ).first()
        
        if not transfer:
            return {"success": False, "error": "Transfer not found"}
        
        transfer.status = "received"
        transfer.received_at = datetime.now(timezone.utc)
        
        # Update received quantities if provided
        if received_items:
            for item_data in received_items:
                item = self.db.query(InventoryTransferItem).filter(
                    and_(
                        InventoryTransferItem.transfer_id == transfer_id,
                        InventoryTransferItem.stock_item_id == item_data["stock_item_id"]
                    )
                ).first()
                if item:
                    item.quantity_received = item_data.get("quantity_received", item.quantity_sent)
        
        # Update actual stock levels at destination location
        # Get items from transfer if received_items not provided
        transfer_items = received_items or []
        if not transfer_items:
            # Query transfer items from database
            transfer_items = [
                {"item_id": ti.stock_item_id, "quantity_received": ti.quantity_sent}
                for ti in transfer.items
            ] if hasattr(transfer, 'items') else []
        
        for item_data in transfer_items:
            dest_stock = self.db.query(Stock).filter(
                Stock.location_id == transfer.destination_id,
                Stock.item_id == item_data.get("item_id")
            ).first()
            if dest_stock:
                dest_stock.quantity += item_data.get("quantity_received", item_data.get("quantity_sent", 0))
            else:
                # Create new stock entry at destination
                new_stock = Stock(
                    location_id=transfer.destination_id,
                    item_id=item_data.get("item_id"),
                    quantity=item_data.get("quantity_received", item_data.get("quantity_sent", 0))
                )
                self.db.add(new_stock)
        
        self.db.commit()
        
        return {
            "success": True,
            "transfer_id": transfer_id,
            "status": "received"
        }
    
    # ========== CONSOLIDATED REPORTING ==========
    
    def get_consolidated_sales_report(
        self,
        start_date: date,
        end_date: date,
        location_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Get consolidated sales report from database"""
        from app.models import Order
        
        query = self.db.query(
            Location.id,
            Location.name,
            func.sum(Order.total).label('sales'),
            func.count(Order.id).label('orders')
        ).join(
            Order, Order.venue_id == Location.id
        ).filter(
            and_(
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date,
                Order.status.in_(["completed", "paid"])
            )
        ).group_by(Location.id, Location.name)
        
        if location_ids:
            query = query.filter(Location.id.in_(location_ids))
        
        results = query.all()
        
        location_data = []
        total_sales = 0
        total_orders = 0
        
        for row in results:
            sales = float(row.sales or 0)
            orders = row.orders or 0
            
            location_data.append({
                "location_id": row.id,
                "location_name": row.name,
                "sales": sales,
                "orders": orders,
                "avg_ticket": round(sales / orders, 2) if orders > 0 else 0
            })
            
            total_sales += sales
            total_orders += orders
        
        # Calculate percentages
        for loc in location_data:
            loc["percentage_of_total"] = round(loc["sales"] / total_sales * 100, 1) if total_sales > 0 else 0
        
        return {
            "success": True,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_sales": total_sales,
                "total_orders": total_orders,
                "avg_ticket": round(total_sales / total_orders, 2) if total_orders > 0 else 0,
                "locations_count": len(location_data)
            },
            "by_location": sorted(location_data, key=lambda x: x["sales"], reverse=True),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def get_enterprise_dashboard(self) -> Dict[str, Any]:
        """Get enterprise dashboard with real data"""
        locations = self.db.query(Location).all()
        active_locations = [l for l in locations if l.status == "active"]
        
        # Count staff assignments
        total_staff = self.db.query(func.count(LocationStaffAssignment.id)).scalar() or 0
        
        # Count pending transfers
        pending_transfers = self.db.query(func.count(InventoryTransfer.id)).filter(
            InventoryTransfer.status == "pending"
        ).scalar() or 0
        
        # Get today's totals
        from app.models import Order
        today = date.today()
        
        today_stats = self.db.query(
            func.sum(Order.total).label('sales'),
            func.count(Order.id).label('orders')
        ).filter(
            and_(
                func.date(Order.created_at) == today,
                Order.status.in_(["completed", "paid"])
            )
        ).first()
        
        today_sales = float(today_stats.sales or 0)
        today_orders = today_stats.orders or 0
        
        return {
            "success": True,
            "overview": {
                "total_locations": len(locations),
                "active_locations": len(active_locations),
                "total_staff": total_staff,
                "pending_transfers": pending_transfers
            },
            "today_metrics": {
                "total_sales": today_sales,
                "total_orders": today_orders,
                "avg_ticket": round(today_sales / today_orders, 2) if today_orders > 0 else 0
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
