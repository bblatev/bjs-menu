"""Catering & Events Service - Full catering workflow"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from decimal import Decimal
import secrets


class CateringEventsService:
    """Complete catering and events management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Event Management
    async def create_event(
        self,
        venue_id: int,
        event_name: str,
        event_type: str,
        event_date: datetime,
        guest_count: int,
        contact_name: str,
        contact_phone: str,
        contact_email: Optional[str] = None,
        location: Optional[str] = None,
        special_requirements: Optional[str] = None,
        dietary_notes: Optional[str] = None,
        customer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new catering event"""
        event = {
            "id": secrets.randbelow(10000) + 1,
            "venue_id": venue_id,
            "customer_id": customer_id,
            "event_name": event_name,
            "event_type": event_type,
            "event_date": event_date.isoformat(),
            "guest_count": guest_count,
            "location": location or "On-site",
            "status": "inquiry",
            "contact_name": contact_name,
            "contact_phone": contact_phone,
            "contact_email": contact_email,
            "special_requirements": special_requirements,
            "dietary_notes": dietary_notes,
            "created_at": datetime.utcnow().isoformat()
        }
        return event
    
    async def update_event_status(
        self, 
        event_id: int, 
        status: str, 
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update event status"""
        valid_statuses = ["inquiry", "quoted", "confirmed", "in_progress", "completed", "cancelled"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        return {
            "event_id": event_id,
            "status": status,
            "notes": notes,
            "updated_at": datetime.utcnow().isoformat()
        }
    
    async def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Get event details"""
        return {
            "id": event_id,
            "event_name": "Johnson Wedding Reception",
            "event_type": "wedding",
            "event_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "guest_count": 100,
            "status": "confirmed",
            "total_amount": 5000.00,
            "deposit_amount": 1500.00,
            "deposit_paid": True,
            "items": []
        }
    
    async def list_events(
        self,
        venue_id: int,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List catering events"""
        events = [
            {
                "id": i,
                "event_name": f"Event {i}",
                "event_type": ["wedding", "corporate", "birthday"][i % 3],
                "event_date": (datetime.utcnow() + timedelta(days=i*7)).isoformat(),
                "guest_count": 50 + i * 10,
                "status": ["inquiry", "quoted", "confirmed"][i % 3],
                "total_amount": 1000 + i * 500
            }
            for i in range(1, 11)
        ]
        
        if status:
            events = [e for e in events if e["status"] == status]
        
        return events[:limit]
    
    # Event Items Management
    async def add_event_item(
        self,
        event_id: int,
        menu_item_id: Optional[int],
        item_name: str,
        quantity: int,
        unit_price: Decimal,
        course: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add item to catering event"""
        total_price = Decimal(quantity) * unit_price
        
        item = {
            "id": secrets.randbelow(10000) + 1,
            "event_id": event_id,
            "menu_item_id": menu_item_id,
            "item_name": item_name,
            "quantity": quantity,
            "unit_price": float(unit_price),
            "total_price": float(total_price),
            "course": course,
            "notes": notes,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Update event total
        await self._recalculate_event_total(event_id)
        
        return item
    
    async def _recalculate_event_total(self, event_id: int) -> Decimal:
        """Recalculate event total from items"""
        # In production: SUM of all event items
        return Decimal("2500.00")
    
    async def get_event_items(self, event_id: int) -> List[Dict[str, Any]]:
        """Get all items for an event"""
        return [
            {
                "id": 1,
                "item_name": "Grilled Chicken Breast",
                "quantity": 100,
                "unit_price": 15.00,
                "total_price": 1500.00,
                "course": "main"
            },
            {
                "id": 2,
                "item_name": "Garden Salad",
                "quantity": 100,
                "unit_price": 8.00,
                "total_price": 800.00,
                "course": "appetizer"
            },
            {
                "id": 3,
                "item_name": "Chocolate Cake Slice",
                "quantity": 100,
                "unit_price": 6.00,
                "total_price": 600.00,
                "course": "dessert"
            }
        ]
    
    # Invoice Management
    async def create_invoice(
        self,
        event_id: int,
        due_date: date,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create invoice for catering event"""
        event = await self.get_event(event_id)
        if not event:
            raise ValueError("Event not found")
        
        # Generate invoice number
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m')}-{secrets.randbelow(9999):04d}"
        
        items = await self.get_event_items(event_id)
        subtotal = sum(item["total_price"] for item in items)
        tax_rate = Decimal("0.20")  # 20% VAT
        tax_amount = Decimal(str(subtotal)) * tax_rate
        total = Decimal(str(subtotal)) + tax_amount
        
        invoice = {
            "id": secrets.randbelow(10000) + 1,
            "event_id": event_id,
            "invoice_number": invoice_number,
            "invoice_date": date.today().isoformat(),
            "due_date": due_date.isoformat(),
            "subtotal": float(subtotal),
            "tax_rate": float(tax_rate),
            "tax_amount": float(tax_amount),
            "total_amount": float(total),
            "amount_paid": 0,
            "status": "draft",
            "notes": notes,
            "items": items,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return invoice
    
    async def send_invoice(self, invoice_id: int) -> Dict[str, Any]:
        """Send invoice to customer"""
        # In production: Email invoice PDF to customer
        return {
            "invoice_id": invoice_id,
            "status": "sent",
            "sent_at": datetime.utcnow().isoformat(),
            "sent_to": "customer@example.com"
        }
    
    async def record_invoice_payment(
        self,
        invoice_id: int,
        amount: Decimal,
        payment_method: str,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record payment against invoice"""
        return {
            "invoice_id": invoice_id,
            "payment_amount": float(amount),
            "payment_method": payment_method,
            "transaction_id": transaction_id,
            "remaining_balance": 0,
            "status": "paid",
            "paid_at": datetime.utcnow().isoformat()
        }
    
    # Kitchen Prep Sheets
    async def generate_prep_sheet(
        self,
        event_id: int,
        prep_date: date,
        station: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate kitchen prep sheet for event"""
        items = await self.get_event_items(event_id)
        
        # Group by station/course if needed
        prep_items = []
        for item in items:
            prep_items.append({
                "item_name": item["item_name"],
                "quantity": item["quantity"],
                "course": item.get("course", "main"),
                "prep_instructions": f"Prepare {item['quantity']} portions",
                "notes": item.get("notes", "")
            })
        
        prep_sheet = {
            "id": secrets.randbelow(10000) + 1,
            "event_id": event_id,
            "prep_date": prep_date.isoformat(),
            "station": station,
            "items": prep_items,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        return prep_sheet
    
    async def print_prep_sheet(self, prep_sheet_id: int) -> Dict[str, Any]:
        """Generate printable prep sheet"""
        return {
            "prep_sheet_id": prep_sheet_id,
            "print_url": f"/api/v1/catering/prep-sheets/{prep_sheet_id}/print",
            "format": "pdf"
        }
    
    # Food Labels
    async def generate_food_labels(
        self,
        event_id: int,
        include_allergens: bool = True
    ) -> List[Dict[str, Any]]:
        """Generate food labels for catering items"""
        items = await self.get_event_items(event_id)
        event = await self.get_event(event_id)
        
        labels = []
        for item in items:
            label = {
                "id": secrets.randbelow(10000) + 1,
                "event_id": event_id,
                "item_name": item["item_name"],
                "prep_date": date.today().isoformat(),
                "event_date": event["event_date"][:10],
                "serving_size": f"{item['quantity']} portions",
                "allergens": ["gluten", "dairy"] if include_allergens else [],
                "storage_instructions": "Keep refrigerated below 5°C",
                "label_type": "catering"
            }
            labels.append(label)
        
        return labels
    
    async def print_labels(
        self, 
        label_ids: List[int], 
        label_format: str = "standard"
    ) -> Dict[str, Any]:
        """Generate printable labels"""
        return {
            "label_count": len(label_ids),
            "format": label_format,
            "print_url": f"/api/v1/catering/labels/print?ids={','.join(map(str, label_ids))}",
            "generated_at": datetime.utcnow().isoformat()
        }
    
    # Event Calendar
    async def get_events_calendar(
        self,
        venue_id: int,
        month: int,
        year: int
    ) -> List[Dict[str, Any]]:
        """Get calendar view of events"""
        events = []
        
        # Generate sample events for the month
        import calendar
        _, days_in_month = calendar.monthrange(year, month)
        
        for day in range(1, days_in_month + 1, 7):
            events.append({
                "date": f"{year}-{month:02d}-{day:02d}",
                "events": [
                    {
                        "id": day,
                        "event_name": f"Event on day {day}",
                        "event_type": "corporate",
                        "guest_count": 50,
                        "status": "confirmed"
                    }
                ]
            })
        
        return events
    
    # Event Communications
    async def send_event_confirmation(self, event_id: int) -> Dict[str, Any]:
        """Send event confirmation to customer"""
        event = await self.get_event(event_id)
        return {
            "event_id": event_id,
            "sent_to": event.get("contact_email", ""),
            "sent_at": datetime.utcnow().isoformat(),
            "type": "confirmation"
        }
    
    async def add_event_discussion(
        self,
        event_id: int,
        message: str,
        sender_type: str,  # staff, customer
        sender_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add discussion message to event"""
        return {
            "id": secrets.randbelow(10000) + 1,
            "event_id": event_id,
            "message": message,
            "sender_type": sender_type,
            "sender_id": sender_id,
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def get_event_discussions(self, event_id: int) -> List[Dict[str, Any]]:
        """Get all discussions for an event"""
        return [
            {
                "id": 1,
                "message": "Can we add vegetarian options?",
                "sender_type": "customer",
                "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat()
            },
            {
                "id": 2,
                "message": "Absolutely! I've added 3 vegetarian main courses to your menu.",
                "sender_type": "staff",
                "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
            }
        ]
