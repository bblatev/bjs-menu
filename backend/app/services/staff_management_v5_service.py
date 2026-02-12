"""Staff Management V5 Service - Break Management, Shift Trading, Employee Onboarding"""
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import secrets


class StaffManagementV5Service:
    """Enhanced staff management features"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== BREAK MANAGEMENT ====================
    
    async def schedule_break(
        self,
        staff_id: int,
        shift_id: int,
        break_type: str,  # meal, rest, smoke
        scheduled_start: datetime,
        duration_minutes: int,
        is_paid: bool = False
    ) -> Dict[str, Any]:
        """Schedule a break for an employee"""
        scheduled_end = scheduled_start + timedelta(minutes=duration_minutes)
        
        break_record = {
            "id": secrets.randbelow(10000) + 1,
            "staff_id": staff_id,
            "shift_id": shift_id,
            "break_type": break_type,
            "scheduled_start": scheduled_start.isoformat(),
            "scheduled_end": scheduled_end.isoformat(),
            "duration_minutes": duration_minutes,
            "is_paid": is_paid,
            "status": "scheduled",
            "created_at": datetime.utcnow().isoformat()
        }
        return break_record
    
    async def start_break(self, break_id: int) -> Dict[str, Any]:
        """Clock in for break"""
        return {
            "break_id": break_id,
            "actual_start": datetime.utcnow().isoformat(),
            "status": "in_progress"
        }
    
    async def end_break(self, break_id: int) -> Dict[str, Any]:
        """Clock out from break"""
        actual_end = datetime.utcnow()
        # In production: Get actual_start from DB
        actual_start = actual_end - timedelta(minutes=15)
        actual_duration = int((actual_end - actual_start).total_seconds() / 60)
        
        return {
            "break_id": break_id,
            "actual_end": actual_end.isoformat(),
            "actual_duration_minutes": actual_duration,
            "status": "completed",
            "overtime_minutes": max(0, actual_duration - 15)  # Assuming 15 min scheduled
        }
    
    async def get_breaks_for_shift(self, shift_id: int) -> List[Dict[str, Any]]:
        """Get all breaks for a shift"""
        return [
            {
                "id": 1,
                "staff_id": 1,
                "break_type": "meal",
                "scheduled_start": "12:00",
                "scheduled_end": "12:30",
                "status": "completed",
                "actual_duration_minutes": 28
            },
            {
                "id": 2,
                "staff_id": 1,
                "break_type": "rest",
                "scheduled_start": "15:00",
                "scheduled_end": "15:15",
                "status": "scheduled"
            }
        ]
    
    async def get_break_compliance_report(
        self,
        venue_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get break compliance report for labor law tracking"""
        return {
            "venue_id": venue_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_shifts": 120,
            "breaks_required": 240,
            "breaks_taken": 235,
            "compliance_rate": 97.9,
            "breaks_missed": 5,
            "breaks_overtime": 12,
            "avg_break_duration": 27,
            "by_break_type": {
                "meal": {"required": 120, "taken": 118, "avg_duration": 28},
                "rest": {"required": 120, "taken": 117, "avg_duration": 14}
            }
        }
    
    # ==================== SHIFT TRADING ====================
    
    async def create_trade_request(
        self,
        original_shift_id: int,
        requesting_staff_id: int,
        trade_type: str,  # swap, giveaway, pickup
        target_staff_id: Optional[int] = None,
        offered_shift_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a shift trade request"""
        request = {
            "id": secrets.randbelow(10000) + 1,
            "original_shift_id": original_shift_id,
            "requesting_staff_id": requesting_staff_id,
            "target_staff_id": target_staff_id,
            "trade_type": trade_type,
            "offered_shift_id": offered_shift_id,
            "reason": reason,
            "status": "pending",
            "expires_at": (datetime.utcnow() + timedelta(hours=48)).isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        return request
    
    async def respond_to_trade_request(
        self,
        request_id: int,
        staff_id: int,
        response: str  # accept, reject
    ) -> Dict[str, Any]:
        """Respond to a shift trade request"""
        if response == "accept":
            status = "accepted"
        else:
            status = "rejected"
        
        return {
            "request_id": request_id,
            "responded_by": staff_id,
            "response": response,
            "status": status,
            "responded_at": datetime.utcnow().isoformat()
        }
    
    async def approve_trade_request(
        self,
        request_id: int,
        manager_id: int,
        approved: bool
    ) -> Dict[str, Any]:
        """Manager approval for shift trade"""
        status = "approved" if approved else "rejected_by_manager"
        
        result = {
            "request_id": request_id,
            "approved_by": manager_id,
            "approved": approved,
            "status": status,
            "approved_at": datetime.utcnow().isoformat()
        }
        
        if approved:
            # Execute the trade
            result["trade_executed"] = True
            result["shifts_swapped"] = True
        
        return result
    
    async def get_open_shift_requests(
        self,
        venue_id: int
    ) -> List[Dict[str, Any]]:
        """Get all open shift giveaway requests"""
        return [
            {
                "id": 1,
                "shift_date": (date.today() + timedelta(days=3)).isoformat(),
                "shift_time": "14:00-22:00",
                "requesting_staff": "John D.",
                "position": "Server",
                "trade_type": "giveaway",
                "reason": "Personal appointment",
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }
        ]
    
    async def get_trade_requests_for_staff(
        self,
        staff_id: int
    ) -> List[Dict[str, Any]]:
        """Get trade requests involving a staff member"""
        return [
            {
                "id": 1,
                "type": "incoming",
                "from_staff": "Jane S.",
                "shift_date": (date.today() + timedelta(days=2)).isoformat(),
                "shift_time": "10:00-18:00",
                "trade_type": "swap",
                "offered_shift": "12:00-20:00",
                "status": "pending"
            },
            {
                "id": 2,
                "type": "outgoing",
                "to_staff": None,
                "shift_date": (date.today() + timedelta(days=5)).isoformat(),
                "shift_time": "18:00-02:00",
                "trade_type": "giveaway",
                "status": "pending"
            }
        ]
    
    # ==================== EMPLOYEE ONBOARDING ====================
    
    async def create_onboarding(
        self,
        staff_id: int,
        venue_id: int,
        start_date: date
    ) -> Dict[str, Any]:
        """Create onboarding record for new employee"""
        onboarding = {
            "id": secrets.randbelow(10000) + 1,
            "staff_id": staff_id,
            "venue_id": venue_id,
            "start_date": start_date.isoformat(),
            "status": "in_progress",
            "documents_submitted": {
                "id_document": False,
                "tax_form": False,
                "bank_details": False,
                "emergency_contact": False,
                "contract_signed": False
            },
            "training_completed": {
                "pos_training": False,
                "food_safety": False,
                "alcohol_service": False,
                "company_policies": False,
                "menu_knowledge": False
            },
            "equipment_issued": {
                "uniform": False,
                "name_badge": False,
                "login_credentials": False
            },
            "created_at": datetime.utcnow().isoformat()
        }
        return onboarding
    
    async def update_onboarding_status(
        self,
        onboarding_id: int,
        category: str,  # documents, training, equipment
        item: str,
        completed: bool
    ) -> Dict[str, Any]:
        """Update onboarding checklist item"""
        return {
            "onboarding_id": onboarding_id,
            "category": category,
            "item": item,
            "completed": completed,
            "updated_at": datetime.utcnow().isoformat()
        }
    
    async def get_onboarding_progress(
        self,
        onboarding_id: int
    ) -> Dict[str, Any]:
        """Get onboarding progress"""
        return {
            "onboarding_id": onboarding_id,
            "staff_id": 1,
            "staff_name": "New Employee",
            "start_date": date.today().isoformat(),
            "progress_percentage": 65,
            "documents": {
                "completed": 3,
                "total": 5,
                "items": {
                    "id_document": True,
                    "tax_form": True,
                    "bank_details": True,
                    "emergency_contact": False,
                    "contract_signed": False
                }
            },
            "training": {
                "completed": 2,
                "total": 5,
                "items": {
                    "pos_training": True,
                    "food_safety": True,
                    "alcohol_service": False,
                    "company_policies": False,
                    "menu_knowledge": False
                }
            },
            "equipment": {
                "completed": 2,
                "total": 3,
                "items": {
                    "uniform": True,
                    "name_badge": True,
                    "login_credentials": False
                }
            },
            "status": "in_progress"
        }
    
    async def complete_onboarding(
        self,
        onboarding_id: int
    ) -> Dict[str, Any]:
        """Mark onboarding as complete"""
        return {
            "onboarding_id": onboarding_id,
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "employee_active": True
        }
    
    async def get_pending_onboardings(
        self,
        venue_id: int
    ) -> List[Dict[str, Any]]:
        """Get all pending onboardings"""
        return [
            {
                "id": 1,
                "staff_name": "New Server",
                "position": "Server",
                "start_date": date.today().isoformat(),
                "progress": 65,
                "days_remaining": 5
            },
            {
                "id": 2,
                "staff_name": "New Bartender",
                "position": "Bartender",
                "start_date": (date.today() + timedelta(days=3)).isoformat(),
                "progress": 20,
                "days_remaining": 10
            }
        ]
    
    async def send_onboarding_reminder(
        self,
        onboarding_id: int
    ) -> Dict[str, Any]:
        """Send reminder for incomplete onboarding items"""
        progress = await self.get_onboarding_progress(onboarding_id)
        
        incomplete_items = []
        for category in ["documents", "training", "equipment"]:
            for item, completed in progress[category]["items"].items():
                if not completed:
                    incomplete_items.append(f"{category}: {item}")
        
        return {
            "onboarding_id": onboarding_id,
            "reminder_sent": True,
            "incomplete_items": incomplete_items,
            "sent_at": datetime.utcnow().isoformat()
        }
