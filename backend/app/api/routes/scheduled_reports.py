"""Scheduled Reports API routes.

Manage automated report generation and email delivery.
"""

from typing import Optional, List
from datetime import time
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from app.services.scheduled_reports_service import (
    get_scheduled_reports_service,
    ReportFrequency,
    ReportFormat,
    ReportType,
)
from app.core.rate_limit import limiter

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateScheduleRequest(BaseModel):
    name: str
    report_type: str  # daily_sales, weekly_sales, etc.
    frequency: str  # daily, weekly, monthly
    format: str = "pdf"  # pdf, excel, csv
    recipients: List[str]  # Email addresses
    time_of_day: str = "06:00"  # HH:MM format
    day_of_week: Optional[int] = None  # 0=Monday for weekly
    day_of_month: Optional[int] = None  # 1-28 for monthly
    venue_id: Optional[int] = None
    parameters: dict = {}


class UpdateScheduleRequest(BaseModel):
    name: Optional[str] = None
    recipients: Optional[List[str]] = None
    time_of_day: Optional[str] = None
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    parameters: Optional[dict] = None
    is_active: Optional[bool] = None


class ScheduleResponse(BaseModel):
    schedule_id: str
    name: str
    report_type: str
    frequency: str
    format: str
    recipients: List[str]
    venue_id: Optional[int] = None
    time_of_day: str
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    is_active: bool
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    last_status: str
    last_error: Optional[str] = None


class RunResponse(BaseModel):
    run_id: str
    schedule_id: str
    report_type: str
    started_at: str
    completed_at: Optional[str] = None
    status: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    recipients_notified: int
    error_message: Optional[str] = None


# ============================================================================
# Schedule Management
# ============================================================================

@router.post("/schedules", response_model=ScheduleResponse)
@limiter.limit("30/minute")
async def create_schedule(request: Request, body: CreateScheduleRequest):
    """
    Create a new report schedule.

    Report types: daily_sales, weekly_sales, monthly_sales, inventory_status,
    labor_summary, menu_performance, customer_insights, financial_summary

    Frequencies: daily, weekly, monthly
    """
    service = get_scheduled_reports_service()

    try:
        report_type = ReportType(body.report_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {body.report_type}")

    try:
        frequency = ReportFrequency(body.frequency)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid frequency: {body.frequency}")

    try:
        format = ReportFormat(body.format)
    except ValueError:
        format = ReportFormat.PDF

    # Parse time
    try:
        hour, minute = map(int, body.time_of_day.split(":"))
        time_of_day = time(hour, minute)
    except ValueError:
        time_of_day = time(6, 0)

    schedule = service.create_schedule(
        name=body.name,
        report_type=report_type,
        frequency=frequency,
        format=format,
        recipients=body.recipients,
        time_of_day=time_of_day,
        day_of_week=body.day_of_week,
        day_of_month=body.day_of_month,
        venue_id=body.venue_id,
        parameters=body.parameters,
    )

    return _schedule_to_response(schedule)


@router.get("/schedules", response_model=List[ScheduleResponse])
@limiter.limit("60/minute")
async def list_schedules(
    request: Request,
    venue_id: Optional[int] = None,
    is_active: Optional[bool] = None,
):
    """List all report schedules."""
    service = get_scheduled_reports_service()
    schedules = service.list_schedules(venue_id=venue_id, is_active=is_active)

    return [_schedule_to_response(s) for s in schedules]


@router.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
@limiter.limit("60/minute")
async def get_schedule(request: Request, schedule_id: str):
    """Get a specific report schedule."""
    service = get_scheduled_reports_service()
    schedule = service.get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return _schedule_to_response(schedule)


@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
@limiter.limit("30/minute")
async def update_schedule(request: Request, schedule_id: str, body: UpdateScheduleRequest):
    """Update a report schedule."""
    service = get_scheduled_reports_service()

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.recipients is not None:
        updates["recipients"] = body.recipients
    if body.time_of_day is not None:
        try:
            hour, minute = map(int, body.time_of_day.split(":"))
            updates["time_of_day"] = time(hour, minute)
        except ValueError:
            pass
    if body.day_of_week is not None:
        updates["day_of_week"] = body.day_of_week
    if body.day_of_month is not None:
        updates["day_of_month"] = body.day_of_month
    if body.parameters is not None:
        updates["parameters"] = body.parameters
    if body.is_active is not None:
        updates["is_active"] = body.is_active

    schedule = service.update_schedule(schedule_id, **updates)

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return _schedule_to_response(schedule)


@router.delete("/schedules/{schedule_id}")
@limiter.limit("30/minute")
async def delete_schedule(request: Request, schedule_id: str):
    """Delete a report schedule."""
    service = get_scheduled_reports_service()

    if not service.delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {"success": True, "message": "Schedule deleted"}


@router.post("/schedules/{schedule_id}/toggle")
@limiter.limit("30/minute")
async def toggle_schedule(request: Request, schedule_id: str, is_active: bool):
    """Enable or disable a schedule."""
    service = get_scheduled_reports_service()

    schedule = service.toggle_schedule(schedule_id, is_active)

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {
        "success": True,
        "schedule_id": schedule_id,
        "is_active": schedule.is_active,
        "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
    }


# ============================================================================
# Run Reports
# ============================================================================

@router.post("/schedules/{schedule_id}/run", response_model=RunResponse)
@limiter.limit("30/minute")
async def run_schedule_now(request: Request, schedule_id: str):
    """Run a scheduled report immediately."""
    service = get_scheduled_reports_service()

    run = await service.run_report(schedule_id, force=True)

    if not run:
        raise HTTPException(status_code=404, detail="Schedule not found or inactive")

    return _run_to_response(run)


@router.get("/schedules/{schedule_id}/history", response_model=List[RunResponse])
@limiter.limit("60/minute")
async def get_schedule_history(request: Request, schedule_id: str, limit: int = 20):
    """Get run history for a schedule."""
    service = get_scheduled_reports_service()

    runs = service.get_run_history(schedule_id=schedule_id, limit=limit)

    return [_run_to_response(r) for r in runs]


@router.get("/history", response_model=List[RunResponse])
@limiter.limit("60/minute")
async def get_all_history(request: Request, limit: int = 50):
    """Get run history for all schedules."""
    service = get_scheduled_reports_service()

    runs = service.get_run_history(limit=limit)

    return [_run_to_response(r) for r in runs]


# ============================================================================
# Report Types Info
# ============================================================================

@router.get("/types")
@limiter.limit("60/minute")
async def get_report_types(request: Request):
    """Get available report types."""
    return {
        "types": [
            {
                "id": "daily_sales",
                "name": "Daily Sales Report",
                "description": "Summary of daily sales, orders, and revenue",
                "recommended_frequency": "daily",
            },
            {
                "id": "weekly_sales",
                "name": "Weekly Sales Report",
                "description": "Weekly sales trends and comparisons",
                "recommended_frequency": "weekly",
            },
            {
                "id": "monthly_sales",
                "name": "Monthly Sales Report",
                "description": "Monthly sales summary with year-over-year comparison",
                "recommended_frequency": "monthly",
            },
            {
                "id": "inventory_status",
                "name": "Inventory Status Report",
                "description": "Current stock levels, low stock alerts, and reorder suggestions",
                "recommended_frequency": "daily",
            },
            {
                "id": "labor_summary",
                "name": "Labor Summary Report",
                "description": "Staff hours, labor cost, and efficiency metrics",
                "recommended_frequency": "weekly",
            },
            {
                "id": "menu_performance",
                "name": "Menu Performance Report",
                "description": "Item popularity, profitability, and menu engineering metrics",
                "recommended_frequency": "weekly",
            },
            {
                "id": "customer_insights",
                "name": "Customer Insights Report",
                "description": "Customer behavior, loyalty metrics, and RFM analysis",
                "recommended_frequency": "monthly",
            },
            {
                "id": "financial_summary",
                "name": "Financial Summary Report",
                "description": "P&L summary, expense breakdown, and financial KPIs",
                "recommended_frequency": "monthly",
            },
        ],
        "frequencies": [
            {"id": "daily", "name": "Daily"},
            {"id": "weekly", "name": "Weekly"},
            {"id": "monthly", "name": "Monthly"},
        ],
        "formats": [
            {"id": "pdf", "name": "PDF", "extension": ".pdf"},
            {"id": "excel", "name": "Excel", "extension": ".xlsx"},
            {"id": "csv", "name": "CSV", "extension": ".csv"},
        ],
    }


# ============================================================================
# Background Task Trigger (for cron/scheduler)
# ============================================================================

@router.post("/check-due")
@limiter.limit("30/minute")
async def check_due_reports(request: Request):
    """
    Check and run any due reports.

    Call this endpoint from a cron job or scheduler (e.g., every 15 minutes).
    """
    service = get_scheduled_reports_service()
    await service.check_and_run_due_reports()

    return {"success": True, "message": "Checked and ran due reports"}


# ============================================================================
# Helper Functions
# ============================================================================

def _schedule_to_response(schedule) -> ScheduleResponse:
    """Convert schedule to response model."""
    return ScheduleResponse(
        schedule_id=schedule.schedule_id,
        name=schedule.name,
        report_type=schedule.report_type.value,
        frequency=schedule.frequency.value,
        format=schedule.format.value,
        recipients=schedule.recipients,
        venue_id=schedule.venue_id,
        time_of_day=schedule.time_of_day.strftime("%H:%M"),
        day_of_week=schedule.day_of_week,
        day_of_month=schedule.day_of_month,
        is_active=schedule.is_active,
        last_run=schedule.last_run.isoformat() if schedule.last_run else None,
        next_run=schedule.next_run.isoformat() if schedule.next_run else None,
        last_status=schedule.last_status,
        last_error=schedule.last_error,
    )


def _run_to_response(run) -> RunResponse:
    """Convert run to response model."""
    return RunResponse(
        run_id=run.run_id,
        schedule_id=run.schedule_id,
        report_type=run.report_type.value,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        status=run.status,
        file_path=run.file_path,
        file_size=run.file_size,
        recipients_notified=run.recipients_notified,
        error_message=run.error_message,
    )
