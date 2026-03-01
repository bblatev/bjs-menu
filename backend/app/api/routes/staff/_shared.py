"""Staff management routes - comprehensive CRUD for staff, shifts, time clock, performance, tips."""

import logging
from typing import List, Literal, Optional, Dict
from datetime import datetime, date, time, timedelta, timezone
from fastapi import APIRouter, HTTPException, Body, Query, Request
from sqlalchemy import func, and_, or_

from app.core.security import get_password_hash, verify_password
from app.db.session import DbSession
from app.models.staff import (
    StaffUser, Shift, TimeOffRequest, TimeClockEntry,
    TableAssignment, PerformanceMetric, PerformanceGoal,
    TipPool, TipDistribution
)
from app.core.rbac import RequireManager, RequireOwner, CurrentUser
from app.core.rate_limit import limiter
from app.schemas.pagination import paginate_query
from app.schemas.staff import (
    StaffCreate, StaffUpdate, StaffResponse,
    ShiftCreate, ShiftUpdate, ShiftResponse,
    TimeOffCreate, TimeOffResponse,
    TipPoolCreate, TipPoolResponse,
    TimeClockEntryResponse,
)

logger = logging.getLogger(__name__)



# ============== Helper Functions ==============

def _prefetch_staff_names(db: DbSession, staff_ids: List[int]) -> Dict[int, str]:
    """Batch fetch staff names to avoid N+1 queries."""
    if not staff_ids:
        return {}
    staff_list = db.query(StaffUser.id, StaffUser.full_name).filter(
        StaffUser.id.in_(staff_ids)
    ).all()
    return {s.id: s.full_name for s in staff_list}


def _staff_to_dict(staff: StaffUser) -> dict:
    """Convert StaffUser to response dict."""
    return {
        "id": staff.id,
        "name": staff.full_name,
        "full_name": staff.full_name,
        "role": staff.role,
        "active": staff.is_active,
        "has_pin": staff.pin_hash is not None,
        "hourly_rate": staff.hourly_rate,
        "max_hours_week": staff.max_hours_week,
        "color": staff.color,
        "commission_percentage": staff.commission_percentage if hasattr(staff, 'commission_percentage') and staff.commission_percentage is not None else 0.0,
        "service_fee_percentage": staff.service_fee_percentage if hasattr(staff, 'service_fee_percentage') and staff.service_fee_percentage is not None else 0.0,
        "auto_logout_after_close": staff.auto_logout_after_close if hasattr(staff, 'auto_logout_after_close') and staff.auto_logout_after_close is not None else False,
        "created_at": staff.created_at.isoformat() if staff.created_at else None,
        "last_login": staff.last_login.isoformat() if staff.last_login else None,
    }


def _shift_to_dict(shift: Shift, staff_name: str = None) -> dict:
    """Convert Shift to response dict."""
    return {
        "id": shift.id,
        "staff_id": shift.staff_id,
        "staff_name": staff_name,
        "date": shift.date.isoformat() if shift.date else None,
        "shift_type": shift.shift_type,
        "start_time": shift.start_time.strftime("%H:%M") if shift.start_time else None,
        "end_time": shift.end_time.strftime("%H:%M") if shift.end_time else None,
        "break_minutes": shift.break_minutes,
        "status": shift.status,
        "position": shift.position,
        "notes": shift.notes,
        "is_published": shift.is_published,
    }


def _time_entry_to_dict(entry: TimeClockEntry, staff_name: str = None) -> dict:
    """Convert TimeClockEntry to response dict."""
    return {
        "id": entry.id,
        "staff_id": entry.staff_id,
        "staff_name": staff_name,
        "clock_in": entry.clock_in.isoformat() if entry.clock_in else None,
        "clock_out": entry.clock_out.isoformat() if entry.clock_out else None,
        "break_start": entry.break_start.isoformat() if entry.break_start else None,
        "break_end": entry.break_end.isoformat() if entry.break_end else None,
        "total_hours": entry.total_hours,
        "break_hours": entry.break_hours,
        "status": entry.status,
        "clock_in_method": entry.clock_in_method,
    }


def _init_default_staff(db: DbSession):
    """Ensure at least one staff member exists (no-op if staff already present)."""
    pass


