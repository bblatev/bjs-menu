"""Staff shifts API routes (v5 compatibility)."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class StaffMember(BaseModel):
    id: str
    name: str
    role: str
    email: str
    phone: str
    hourly_rate: float
    status: str  # active, on_leave, inactive


class Shift(BaseModel):
    id: str
    staff_id: str
    staff_name: str
    role: str
    date: str
    start_time: str
    end_time: str
    break_minutes: int = 0
    status: str  # scheduled, in_progress, completed, missed
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    notes: Optional[str] = None


@router.get("/staff")
async def get_staff():
    """Get all staff members."""
    return [
        StaffMember(id="1", name="John Doe", role="Server", email="john@bjsbar.com", phone="+359888111222", hourly_rate=12.50, status="active"),
        StaffMember(id="2", name="Jane Smith", role="Bartender", email="jane@bjsbar.com", phone="+359888333444", hourly_rate=14.00, status="active"),
        StaffMember(id="3", name="Mike Johnson", role="Chef", email="mike@bjsbar.com", phone="+359888555666", hourly_rate=18.00, status="active"),
        StaffMember(id="4", name="Sarah Williams", role="Host", email="sarah@bjsbar.com", phone="+359888777888", hourly_rate=11.00, status="active"),
    ]


@router.get("/shifts")
async def get_shifts(date: str = Query(None), staff_id: str = Query(None)):
    """Get shifts with optional filters."""
    return [
        Shift(id="1", staff_id="1", staff_name="John Doe", role="Server", date="2026-02-01", start_time="10:00", end_time="18:00", break_minutes=30, status="completed", actual_start="09:55", actual_end="18:05"),
        Shift(id="2", staff_id="2", staff_name="Jane Smith", role="Bartender", date="2026-02-01", start_time="16:00", end_time="00:00", break_minutes=30, status="in_progress", actual_start="15:58"),
        Shift(id="3", staff_id="3", staff_name="Mike Johnson", role="Chef", date="2026-02-01", start_time="08:00", end_time="16:00", break_minutes=30, status="completed", actual_start="08:00", actual_end="16:10"),
        Shift(id="4", staff_id="1", staff_name="John Doe", role="Server", date="2026-02-02", start_time="10:00", end_time="18:00", break_minutes=30, status="scheduled"),
    ]


@router.get("/shifts/{shift_id}")
async def get_shift(shift_id: str):
    """Get a specific shift."""
    return Shift(id=shift_id, staff_id="1", staff_name="John Doe", role="Server", date="2026-02-01", start_time="10:00", end_time="18:00", break_minutes=30, status="completed")


@router.post("/shifts")
async def create_shift(shift: Shift):
    """Create a new shift."""
    return {"success": True, "id": "new-id"}


@router.put("/shifts/{shift_id}")
async def update_shift(shift_id: str, shift: Shift):
    """Update a shift."""
    return {"success": True}


@router.delete("/shifts/{shift_id}")
async def delete_shift(shift_id: str):
    """Delete a shift."""
    return {"success": True}


# ==================== CATERING ====================

@router.get("/catering/events")
async def get_catering_events():
    """Get catering events."""
    return [
        {"id": "1", "name": "Corporate Lunch", "date": "2026-02-15", "guest_count": 50, "status": "confirmed", "total": 2500.00, "package": "Premium Buffet", "contact": "John Smith", "phone": "+359888123456"},
        {"id": "2", "name": "Wedding Reception", "date": "2026-03-01", "guest_count": 120, "status": "pending", "total": 8400.00, "package": "Wedding Package", "contact": "Maria Ivanova", "phone": "+359888654321"},
        {"id": "3", "name": "Birthday Party", "date": "2026-02-20", "guest_count": 30, "status": "confirmed", "total": 1200.00, "package": "Party Package", "contact": "Peter Petrov", "phone": "+359888111222"},
    ]


@router.get("/catering/packages")
async def get_catering_packages():
    """Get catering packages."""
    return [
        {"id": "1", "name": "Premium Buffet", "price_per_person": 50.00, "min_guests": 20, "includes": ["appetizers", "main course", "dessert", "drinks"], "active": True},
        {"id": "2", "name": "Wedding Package", "price_per_person": 70.00, "min_guests": 50, "includes": ["cocktail hour", "3-course meal", "wedding cake", "open bar"], "active": True},
        {"id": "3", "name": "Party Package", "price_per_person": 40.00, "min_guests": 10, "includes": ["finger food", "drinks", "dessert"], "active": True},
        {"id": "4", "name": "Business Lunch", "price_per_person": 25.00, "min_guests": 10, "includes": ["soup", "main course", "soft drinks"], "active": True},
    ]


@router.get("/catering/staff")
async def get_catering_staff():
    """Get staff available for catering events."""
    return [
        {"id": "1", "name": "Ivan Dimitrov", "role": "Chef", "available": True, "events_this_month": 3},
        {"id": "2", "name": "Elena Georgieva", "role": "Server", "available": True, "events_this_month": 5},
        {"id": "3", "name": "Nikolay Stoyanov", "role": "Bartender", "available": False, "events_this_month": 2},
    ]


# ==================== SMS MARKETING ====================

@router.get("/sms/campaigns")
async def get_sms_campaigns():
    """Get SMS marketing campaigns."""
    return [
        {"id": "1", "name": "Weekend Special", "status": "active", "recipients": 450, "sent": 448, "delivered": 440, "opened": 320, "clicked": 85, "message": "This weekend only! 20% off all cocktails. Visit BJ's Bar!", "scheduled_at": "2026-02-07T10:00:00Z", "created_at": "2026-02-05T14:00:00Z"},
        {"id": "2", "name": "Happy Hour Reminder", "status": "completed", "recipients": 380, "sent": 380, "delivered": 375, "opened": 290, "clicked": 120, "message": "Happy Hour 4-7 PM today! Half-price drinks at BJ's!", "scheduled_at": "2026-02-05T15:00:00Z", "created_at": "2026-02-05T10:00:00Z"},
        {"id": "3", "name": "New Menu Launch", "status": "draft", "recipients": 0, "sent": 0, "delivered": 0, "opened": 0, "clicked": 0, "message": "Exciting new menu items just dropped! Come try them today.", "scheduled_at": None, "created_at": "2026-02-06T09:00:00Z"},
    ]


@router.get("/sms/stats")
async def get_sms_stats():
    """Get SMS marketing statistics."""
    return {
        "total_campaigns": 15,
        "total_sent": 5200,
        "total_delivered": 5100,
        "delivery_rate": 98.1,
        "avg_open_rate": 72.5,
        "avg_click_rate": 18.3,
        "credits_remaining": 2500,
        "monthly_spend": 125.00,
    }


@router.post("/sms/campaigns/{campaign_id}/send")
async def send_sms_campaign(campaign_id: str):
    """Send an SMS campaign."""
    return {"success": True, "campaign_id": campaign_id, "status": "sending"}
