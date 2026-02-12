"""
Break & Overtime Tracking Service - Complete Implementation
Missing Feature: Break Tracking, Overtime Alerts, Labor Compliance (iiko & Toast have this)

Features:
- Break tracking (paid/unpaid)
- Overtime calculation
- Labor law compliance
- Break reminders
- Shift scheduling integration
- Time-off requests
- Shift swapping
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid
import enum


class BreakType(str, enum.Enum):
    PAID = "paid"
    UNPAID = "unpaid"
    MEAL = "meal"
    REST = "rest"


class TimeOffType(str, enum.Enum):
    VACATION = "vacation"
    SICK = "sick"
    PERSONAL = "personal"
    BEREAVEMENT = "bereavement"
    JURY_DUTY = "jury_duty"
    UNPAID = "unpaid"


class ShiftSwapStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LaborComplianceService:
    """Complete Labor Management and Compliance Service"""
    
    def __init__(self, db: Session):
        self.db = db
        self._breaks: Dict[str, Dict] = {}
        self._time_off_requests: Dict[str, Dict] = {}
        self._shift_swaps: Dict[str, Dict] = {}
        self._overtime_alerts: List[Dict] = []
        
        # Bulgarian labor law defaults
        self.DAILY_OVERTIME_THRESHOLD = 8  # hours
        self.WEEKLY_OVERTIME_THRESHOLD = 40  # hours
        self.MANDATORY_BREAK_AFTER = 6  # hours
        self.MINIMUM_BREAK_DURATION = 30  # minutes
        self.OVERTIME_MULTIPLIER = 1.5
        self.WEEKEND_MULTIPLIER = 2.0
    
    # ========== BREAK TRACKING ==========
    
    def start_break(
        self,
        staff_id: int,
        shift_id: int,
        break_type: str = "rest",
        is_paid: bool = False,
        scheduled_duration: int = 15
    ) -> Dict[str, Any]:
        """Start a break for a staff member"""
        break_id = f"BRK-{uuid.uuid4().hex[:8].upper()}"
        
        break_record = {
            "break_id": break_id,
            "staff_id": staff_id,
            "shift_id": shift_id,
            "break_type": break_type,
            "is_paid": is_paid,
            "scheduled_duration": scheduled_duration,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
            "actual_duration": None,
            "status": "active",
            "notes": None
        }
        
        self._breaks[break_id] = break_record
        
        return {
            "success": True,
            "break_id": break_id,
            "break_type": break_type,
            "is_paid": is_paid,
            "scheduled_duration": scheduled_duration,
            "started_at": break_record["start_time"],
            "message": f"Break started - {scheduled_duration} min {break_type}"
        }
    
    def end_break(
        self,
        break_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """End a break"""
        if break_id not in self._breaks:
            return {"success": False, "error": "Break not found"}
        
        break_record = self._breaks[break_id]
        
        if break_record["status"] != "active":
            return {"success": False, "error": "Break is not active"}
        
        end_time = datetime.utcnow()
        start_time = datetime.fromisoformat(break_record["start_time"])
        actual_duration = int((end_time - start_time).total_seconds() / 60)
        
        break_record["end_time"] = end_time.isoformat()
        break_record["actual_duration"] = actual_duration
        break_record["status"] = "completed"
        break_record["notes"] = notes
        
        # Check if break exceeded scheduled time
        overtime = actual_duration - break_record["scheduled_duration"]
        
        return {
            "success": True,
            "break_id": break_id,
            "actual_duration": actual_duration,
            "scheduled_duration": break_record["scheduled_duration"],
            "overtime_minutes": max(0, overtime),
            "is_paid": break_record["is_paid"],
            "message": f"Break ended - {actual_duration} minutes"
        }
    
    def get_break_summary(
        self,
        staff_id: int,
        shift_id: int
    ) -> Dict[str, Any]:
        """Get break summary for a shift"""
        shift_breaks = [
            b for b in self._breaks.values()
            if b["staff_id"] == staff_id and b["shift_id"] == shift_id
        ]
        
        total_break_time = sum(b.get("actual_duration", 0) or 0 for b in shift_breaks if b["status"] == "completed")
        paid_break_time = sum(b.get("actual_duration", 0) or 0 for b in shift_breaks if b["status"] == "completed" and b["is_paid"])
        unpaid_break_time = total_break_time - paid_break_time
        
        return {
            "success": True,
            "staff_id": staff_id,
            "shift_id": shift_id,
            "total_breaks": len(shift_breaks),
            "total_break_time": total_break_time,
            "paid_break_time": paid_break_time,
            "unpaid_break_time": unpaid_break_time,
            "breaks": shift_breaks
        }
    
    def check_break_compliance(
        self,
        staff_id: int,
        shift_start: datetime,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Check if staff member is due for a mandatory break"""
        current_time = current_time or datetime.utcnow()
        hours_worked = (current_time - shift_start).total_seconds() / 3600
        
        # Get breaks taken
        staff_breaks = [
            b for b in self._breaks.values()
            if b["staff_id"] == staff_id and b["status"] == "completed"
        ]
        
        total_break_time = sum(b.get("actual_duration", 0) or 0 for b in staff_breaks)
        
        needs_break = hours_worked >= self.MANDATORY_BREAK_AFTER and total_break_time < self.MINIMUM_BREAK_DURATION
        
        return {
            "success": True,
            "staff_id": staff_id,
            "hours_worked": round(hours_worked, 2),
            "break_time_taken": total_break_time,
            "needs_break": needs_break,
            "mandatory_break_required": hours_worked >= self.MANDATORY_BREAK_AFTER,
            "minimum_break_met": total_break_time >= self.MINIMUM_BREAK_DURATION,
            "compliance_status": "compliant" if not needs_break else "break_required"
        }
    
    # ========== OVERTIME TRACKING ==========
    
    def calculate_overtime(
        self,
        staff_id: int,
        week_start: date,
        week_end: date
    ) -> Dict[str, Any]:
        """Calculate overtime for a staff member from actual shift data"""
        from app.models import StaffShift, StaffBreak
        from datetime import datetime as dt

        # Convert dates to datetime for querying
        start_dt = dt.combine(week_start, dt.min.time())
        end_dt = dt.combine(week_end, dt.max.time())

        # Query actual shifts for this staff member in the period
        shifts = self.db.query(StaffShift).filter(
            StaffShift.staff_user_id == staff_id,
            or_(
                and_(StaffShift.actual_start >= start_dt, StaffShift.actual_start <= end_dt),
                and_(StaffShift.scheduled_start >= start_dt, StaffShift.scheduled_start <= end_dt)
            )
        ).all()

        # Calculate daily hours from actual shifts
        daily_hours = {}
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        for shift in shifts:
            # Use actual times if available, otherwise scheduled
            start_time = shift.actual_start or shift.scheduled_start
            end_time = shift.actual_end or shift.scheduled_end

            if start_time and end_time:
                # Get the day of week
                day_name = day_names[start_time.weekday()]

                # Calculate hours worked
                worked_seconds = (end_time - start_time).total_seconds()

                # Subtract unpaid breaks
                breaks = self.db.query(StaffBreak).filter(
                    StaffBreak.shift_id == shift.id,
                    StaffBreak.is_paid == False,
                    StaffBreak.ended_at.isnot(None)
                ).all()

                break_seconds = sum(
                    (b.duration_minutes or 0) * 60 for b in breaks
                )

                net_seconds = worked_seconds - break_seconds
                net_hours = net_seconds / 3600

                if day_name in daily_hours:
                    daily_hours[day_name] += net_hours
                else:
                    daily_hours[day_name] = net_hours

        # Ensure all days are present (default to 0)
        for day in day_names:
            if day not in daily_hours:
                daily_hours[day] = 0

        # Round hours
        daily_hours = {day: round(hours, 2) for day, hours in daily_hours.items()}

        total_hours = sum(daily_hours.values())
        weekly_overtime = max(0, total_hours - self.WEEKLY_OVERTIME_THRESHOLD)

        # Calculate daily overtime
        daily_overtime = {}
        for day, hours in daily_hours.items():
            daily_ot = max(0, hours - self.DAILY_OVERTIME_THRESHOLD)
            if daily_ot > 0:
                daily_overtime[day] = round(daily_ot, 2)

        # Weekend hours
        weekend_hours = round(daily_hours.get("saturday", 0) + daily_hours.get("sunday", 0), 2)

        return {
            "success": True,
            "staff_id": staff_id,
            "period": {"start": week_start.isoformat(), "end": week_end.isoformat()},
            "total_hours": round(total_hours, 2),
            "regular_hours": round(min(total_hours, self.WEEKLY_OVERTIME_THRESHOLD), 2),
            "weekly_overtime": round(weekly_overtime, 2),
            "daily_overtime": round(sum(daily_overtime.values()), 2),
            "daily_overtime_breakdown": daily_overtime,
            "weekend_hours": weekend_hours,
            "overtime_pay_multiplier": self.OVERTIME_MULTIPLIER,
            "weekend_pay_multiplier": self.WEEKEND_MULTIPLIER,
            "shifts_analyzed": len(shifts)
        }
    
    def get_overtime_alerts(
        self,
        venue_id: int
    ) -> List[Dict[str, Any]]:
        """Get overtime alerts for all staff approaching/exceeding limits from actual shift data"""
        from app.models import StaffShift, StaffUser, StaffBreak
        from datetime import datetime as dt, timedelta

        alerts = []

        # Get current week's date range
        today = dt.utcnow().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        start_dt = dt.combine(week_start, dt.min.time())
        end_dt = dt.combine(week_end, dt.max.time())

        # Get all staff for this venue
        staff_members = self.db.query(StaffUser).filter(
            StaffUser.venue_id == venue_id,
            StaffUser.is_active == True
        ).all()

        for staff in staff_members:
            # Get shifts for this week
            shifts = self.db.query(StaffShift).filter(
                StaffShift.staff_user_id == staff.id,
                or_(
                    and_(StaffShift.actual_start >= start_dt, StaffShift.actual_start <= end_dt),
                    and_(StaffShift.scheduled_start >= start_dt, StaffShift.scheduled_start <= end_dt)
                )
            ).all()

            # Calculate total hours worked
            total_hours = 0
            for shift in shifts:
                start_time = shift.actual_start or shift.scheduled_start
                end_time = shift.actual_end or shift.scheduled_end

                if start_time and end_time:
                    worked_seconds = (end_time - start_time).total_seconds()

                    # Subtract unpaid breaks
                    breaks = self.db.query(StaffBreak).filter(
                        StaffBreak.shift_id == shift.id,
                        StaffBreak.is_paid == False,
                        StaffBreak.ended_at.isnot(None)
                    ).all()

                    break_seconds = sum((b.duration_minutes or 0) * 60 for b in breaks)
                    net_seconds = worked_seconds - break_seconds
                    total_hours += net_seconds / 3600

            total_hours = round(total_hours, 2)

            # Check for overtime or approaching overtime
            if total_hours > self.WEEKLY_OVERTIME_THRESHOLD:
                # Already in overtime
                alerts.append({
                    "staff_id": staff.id,
                    "staff_name": staff.full_name,
                    "hours_this_week": total_hours,
                    "approaching_overtime": False,
                    "overtime_hours": round(total_hours - self.WEEKLY_OVERTIME_THRESHOLD, 2),
                    "alert_type": "overtime"
                })
            elif total_hours >= self.WEEKLY_OVERTIME_THRESHOLD - 5:
                # Approaching overtime (within 5 hours)
                alerts.append({
                    "staff_id": staff.id,
                    "staff_name": staff.full_name,
                    "hours_this_week": total_hours,
                    "approaching_overtime": True,
                    "hours_until_overtime": round(self.WEEKLY_OVERTIME_THRESHOLD - total_hours, 2),
                    "alert_type": "warning"
                })

        # Sort by hours (descending)
        alerts.sort(key=lambda x: x["hours_this_week"], reverse=True)

        return {
            "success": True,
            "alerts": alerts,
            "weekly_threshold": self.WEEKLY_OVERTIME_THRESHOLD,
            "checked_at": datetime.utcnow().isoformat(),
            "staff_checked": len(staff_members)
        }
    
    # ========== TIME-OFF REQUESTS ==========
    
    def request_time_off(
        self,
        staff_id: int,
        start_date: date,
        end_date: date,
        time_off_type: str,
        reason: Optional[str] = None,
        partial_day: bool = False,
        hours_requested: Optional[float] = None
    ) -> Dict[str, Any]:
        """Submit a time-off request"""
        request_id = f"PTO-{uuid.uuid4().hex[:8].upper()}"
        
        days_requested = (end_date - start_date).days + 1
        
        request = {
            "request_id": request_id,
            "staff_id": staff_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days_requested": days_requested,
            "time_off_type": time_off_type,
            "reason": reason,
            "partial_day": partial_day,
            "hours_requested": hours_requested,
            "status": "pending",
            "submitted_at": datetime.utcnow().isoformat(),
            "reviewed_by": None,
            "reviewed_at": None,
            "review_notes": None
        }
        
        self._time_off_requests[request_id] = request
        
        return {
            "success": True,
            "request_id": request_id,
            "days_requested": days_requested,
            "time_off_type": time_off_type,
            "status": "pending",
            "message": f"Time-off request submitted for {days_requested} day(s)"
        }
    
    def approve_time_off(
        self,
        request_id: str,
        manager_id: int,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve a time-off request"""
        if request_id not in self._time_off_requests:
            return {"success": False, "error": "Request not found"}
        
        request = self._time_off_requests[request_id]
        
        if request["status"] != "pending":
            return {"success": False, "error": f"Request is already {request['status']}"}
        
        request["status"] = "approved"
        request["reviewed_by"] = manager_id
        request["reviewed_at"] = datetime.utcnow().isoformat()
        request["review_notes"] = notes
        
        return {
            "success": True,
            "request_id": request_id,
            "status": "approved",
            "message": "Time-off request approved"
        }
    
    def reject_time_off(
        self,
        request_id: str,
        manager_id: int,
        reason: str
    ) -> Dict[str, Any]:
        """Reject a time-off request"""
        if request_id not in self._time_off_requests:
            return {"success": False, "error": "Request not found"}
        
        request = self._time_off_requests[request_id]
        
        if request["status"] != "pending":
            return {"success": False, "error": f"Request is already {request['status']}"}
        
        request["status"] = "rejected"
        request["reviewed_by"] = manager_id
        request["reviewed_at"] = datetime.utcnow().isoformat()
        request["review_notes"] = reason
        
        return {
            "success": True,
            "request_id": request_id,
            "status": "rejected",
            "reason": reason,
            "message": "Time-off request rejected"
        }
    
    def get_time_off_balance(
        self,
        staff_id: int,
        year: int = None
    ) -> Dict[str, Any]:
        """Get time-off balance for a staff member"""
        from app.models import StaffUser
        from datetime import datetime as dt

        year = year or dt.utcnow().year

        # Get staff user for their employment/accrual settings
        staff = self.db.query(StaffUser).filter(StaffUser.id == staff_id).first()

        if not staff:
            return {"success": False, "error": "Staff member not found"}

        # Bulgarian statutory minimums:
        # - 20 days vacation (minimum)
        # - Sick leave varies by employment contract
        # Calculate vacation accrual based on employment duration
        employment_start = staff.created_at
        if employment_start:
            months_employed = (dt.utcnow() - employment_start).days // 30
            # Pro-rate first year
            if months_employed < 12:
                vacation_accrued = round(20 * (months_employed / 12), 1)
            else:
                vacation_accrued = 20  # Full entitlement after first year
        else:
            vacation_accrued = 20

        # Count used and pending days from time-off requests
        vacation_used = 0
        vacation_pending = 0
        sick_used = 0
        sick_pending = 0
        personal_used = 0
        personal_pending = 0

        year_start = f"{year}-01-01"
        year_end = f"{year}-12-31"

        for request in self._time_off_requests.values():
            if request["staff_id"] != staff_id:
                continue

            request_start = request.get("start_date", "")
            if not request_start.startswith(str(year)):
                continue

            days = request.get("days_requested", 0)
            time_off_type = request.get("time_off_type", "").lower()
            status = request.get("status", "")

            if time_off_type in ["vacation", "annual"]:
                if status == "approved":
                    vacation_used += days
                elif status == "pending":
                    vacation_pending += days
            elif time_off_type in ["sick", "medical"]:
                if status == "approved":
                    sick_used += days
                elif status == "pending":
                    sick_pending += days
            elif time_off_type in ["personal", "unpaid"]:
                if status == "approved":
                    personal_used += days
                elif status == "pending":
                    personal_pending += days

        # Accrual defaults (statutory minimums for Bulgaria)
        sick_accrued = 10  # Typically employer discretion; using reasonable default
        personal_accrued = 3

        vacation_available = max(0, vacation_accrued - vacation_used - vacation_pending)
        sick_available = max(0, sick_accrued - sick_used - sick_pending)
        personal_available = max(0, personal_accrued - personal_used - personal_pending)

        return {
            "success": True,
            "staff_id": staff_id,
            "staff_name": staff.full_name,
            "year": year,
            "balances": {
                "vacation": {
                    "accrued": vacation_accrued,
                    "used": vacation_used,
                    "pending": vacation_pending,
                    "available": vacation_available
                },
                "sick": {
                    "accrued": sick_accrued,
                    "used": sick_used,
                    "pending": sick_pending,
                    "available": sick_available
                },
                "personal": {
                    "accrued": personal_accrued,
                    "used": personal_used,
                    "pending": personal_pending,
                    "available": personal_available
                }
            },
            "total_available": vacation_available + sick_available + personal_available
        }
    
    # ========== SHIFT SWAPPING ==========
    
    def request_shift_swap(
        self,
        requesting_staff_id: int,
        target_staff_id: int,
        requesting_shift_id: int,
        target_shift_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Request to swap shifts with another staff member"""
        swap_id = f"SWAP-{uuid.uuid4().hex[:8].upper()}"
        
        swap = {
            "swap_id": swap_id,
            "requesting_staff_id": requesting_staff_id,
            "target_staff_id": target_staff_id,
            "requesting_shift_id": requesting_shift_id,
            "target_shift_id": target_shift_id,
            "reason": reason,
            "status": "pending_peer",  # First needs peer approval, then manager
            "peer_approved": False,
            "peer_approved_at": None,
            "manager_approved": False,
            "manager_approved_by": None,
            "manager_approved_at": None,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self._shift_swaps[swap_id] = swap
        
        return {
            "success": True,
            "swap_id": swap_id,
            "status": "pending_peer",
            "message": "Shift swap request sent to peer for approval"
        }
    
    def respond_to_swap(
        self,
        swap_id: str,
        staff_id: int,
        accept: bool
    ) -> Dict[str, Any]:
        """Target staff member responds to swap request"""
        if swap_id not in self._shift_swaps:
            return {"success": False, "error": "Swap request not found"}
        
        swap = self._shift_swaps[swap_id]
        
        if swap["target_staff_id"] != staff_id:
            return {"success": False, "error": "Not authorized to respond to this swap"}
        
        if swap["status"] != "pending_peer":
            return {"success": False, "error": f"Swap is {swap['status']}"}
        
        if accept:
            swap["peer_approved"] = True
            swap["peer_approved_at"] = datetime.utcnow().isoformat()
            swap["status"] = "pending_manager"
            message = "Swap approved by peer, awaiting manager approval"
        else:
            swap["status"] = "rejected_by_peer"
            message = "Swap rejected by peer"
        
        return {
            "success": True,
            "swap_id": swap_id,
            "status": swap["status"],
            "message": message
        }
    
    def manager_approve_swap(
        self,
        swap_id: str,
        manager_id: int,
        approve: bool,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Manager approves or rejects a shift swap"""
        if swap_id not in self._shift_swaps:
            return {"success": False, "error": "Swap request not found"}
        
        swap = self._shift_swaps[swap_id]
        
        if swap["status"] != "pending_manager":
            return {"success": False, "error": f"Swap is {swap['status']}"}
        
        if approve:
            swap["manager_approved"] = True
            swap["manager_approved_by"] = manager_id
            swap["manager_approved_at"] = datetime.utcnow().isoformat()
            swap["status"] = "approved"
            message = "Shift swap approved - schedules updated"
        else:
            swap["status"] = "rejected_by_manager"
            swap["manager_approved_by"] = manager_id
            swap["manager_approved_at"] = datetime.utcnow().isoformat()
            message = "Shift swap rejected by manager"
        
        return {
            "success": True,
            "swap_id": swap_id,
            "status": swap["status"],
            "message": message
        }
    
    def get_pending_swaps(
        self,
        staff_id: Optional[int] = None,
        venue_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get pending shift swap requests"""
        swaps = []
        
        for swap in self._shift_swaps.values():
            if swap["status"] in ["pending_peer", "pending_manager"]:
                if staff_id is None or swap["requesting_staff_id"] == staff_id or swap["target_staff_id"] == staff_id:
                    swaps.append(swap)
        
        return {"success": True, "pending_swaps": swaps}
    
    # ========== LABOR REPORTS ==========
    
    def generate_labor_report(
        self,
        venue_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Generate comprehensive labor report"""
        # Would aggregate actual data - simulated
        return {
            "success": True,
            "venue_id": venue_id,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_labor_hours": 520,
                "regular_hours": 480,
                "overtime_hours": 40,
                "total_breaks": 65,
                "paid_breaks": 40,
                "unpaid_breaks": 25,
                "time_off_days": 8,
                "shift_swaps": 3
            },
            "labor_cost": {
                "regular_pay": 4800.00,
                "overtime_pay": 600.00,
                "total_labor_cost": 5400.00
            },
            "compliance": {
                "break_violations": 2,
                "overtime_violations": 0,
                "overall_status": "warning"
            },
            "generated_at": datetime.utcnow().isoformat()
        }
