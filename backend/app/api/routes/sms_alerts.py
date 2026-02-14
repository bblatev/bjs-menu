"""Manager SMS Alerts API routes - automatic SMS notifications for important events."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from typing import List, Optional
from datetime import datetime, time
from pydantic import BaseModel, Field

from app.db.session import DbSession
from app.core.rbac import CurrentUser, OptionalCurrentUser
from app.core.rate_limit import limiter

router = APIRouter()


# ==================== SCHEMAS ====================

class SMSAlertConfigCreate(BaseModel):
    phone_number: str = Field(..., description="Phone number for SMS alerts")
    alert_on_voids: bool = Field(True, description="Alert on order voids")
    alert_on_refunds: bool = Field(True, description="Alert on refunds")
    alert_on_discounts: bool = Field(True, description="Alert on large discounts")
    discount_threshold: float = Field(20.0, description="Discount percentage threshold")
    alert_on_corrections: bool = Field(True, description="Alert on order corrections")
    alert_on_cash_drawer: bool = Field(True, description="Alert on cash drawer opens")
    alert_on_low_stock: bool = Field(False, description="Alert on low stock items")
    alert_on_customer_complaints: bool = Field(True, description="Alert on customer complaints")
    alert_on_eod_reports: bool = Field(True, description="Alert on end of day reports")
    min_void_amount: float = Field(0.0, description="Minimum void amount to trigger alert")
    min_refund_amount: float = Field(0.0, description="Minimum refund amount to trigger alert")
    quiet_hours_start: Optional[str] = Field(None, description="Quiet hours start time (HH:MM)")
    quiet_hours_end: Optional[str] = Field(None, description="Quiet hours end time (HH:MM)")


class SMSAlertConfigResponse(BaseModel):
    id: int
    staff_user_id: int
    staff_name: str
    phone_number: str
    alert_on_voids: bool
    alert_on_refunds: bool
    alert_on_discounts: bool
    discount_threshold: float
    alert_on_corrections: bool
    alert_on_cash_drawer: bool
    alert_on_low_stock: bool
    alert_on_customer_complaints: bool
    alert_on_eod_reports: bool
    is_active: bool
    created_at: str


class SMSAlertLogResponse(BaseModel):
    id: int
    alert_type: str
    message: str
    phone_number: str
    delivery_status: str
    sent_at: Optional[str] = None
    created_at: str


class TestSMSRequest(BaseModel):
    phone_number: str
    message: Optional[str] = Field("Test SMS from BJ's Bar POS System", description="Test message")


# ==================== In-memory stores ====================
_alert_configs: list = []
_alert_logs: list = []
_next_config_id = 1
_next_log_id = 1


# ==================== SMS SERVICE (Mock) ====================

class SMSService:
    """SMS sending service - mock implementation."""

    def __init__(self, provider: str = "mock"):
        self.provider = provider

    async def send_sms(self, phone_number: str, message: str) -> dict:
        if self.provider == "mock":
            return {
                "success": True,
                "provider_id": f"mock_{datetime.utcnow().timestamp()}",
                "status": "sent",
            }
        return {"success": False, "error": "Unknown SMS provider"}


sms_service = SMSService(provider="mock")


# ==================== ALERT CONFIGURATION ENDPOINTS ====================

@router.post("/config", response_model=SMSAlertConfigResponse)
@limiter.limit("30/minute")
def create_alert_config(request: Request, data: SMSAlertConfigCreate, db: DbSession, current_user: CurrentUser = None):
    """Create SMS alert configuration for a manager."""
    global _next_config_id

    # Check if config already exists for this user
    for cfg in _alert_configs:
        if cfg["staff_user_id"] == 0:
            raise HTTPException(status_code=400, detail="Alert configuration already exists. Use PUT to update.")

    now = datetime.utcnow().isoformat()
    config = {
        "id": _next_config_id,
        "staff_user_id": 0,
        "staff_name": "System",
        "phone_number": data.phone_number,
        "alert_on_voids": data.alert_on_voids,
        "alert_on_refunds": data.alert_on_refunds,
        "alert_on_discounts": data.alert_on_discounts,
        "discount_threshold": data.discount_threshold,
        "alert_on_corrections": data.alert_on_corrections,
        "alert_on_cash_drawer": data.alert_on_cash_drawer,
        "alert_on_low_stock": data.alert_on_low_stock,
        "alert_on_customer_complaints": data.alert_on_customer_complaints,
        "alert_on_eod_reports": data.alert_on_eod_reports,
        "is_active": True,
        "created_at": now,
        "min_void_amount": data.min_void_amount,
        "min_refund_amount": data.min_refund_amount,
        "quiet_hours_start": data.quiet_hours_start,
        "quiet_hours_end": data.quiet_hours_end,
    }
    _alert_configs.append(config)
    _next_config_id += 1
    return SMSAlertConfigResponse(**{k: v for k, v in config.items() if k in SMSAlertConfigResponse.model_fields})


@router.get("/config", response_model=List[SMSAlertConfigResponse])
@limiter.limit("60/minute")
def list_alert_configs(request: Request, db: DbSession, current_user: CurrentUser = None):
    """List all SMS alert configurations (Admin only)."""
    return [
        SMSAlertConfigResponse(**{k: v for k, v in cfg.items() if k in SMSAlertConfigResponse.model_fields})
        for cfg in _alert_configs
    ]


@router.get("/config/me", response_model=SMSAlertConfigResponse)
@limiter.limit("60/minute")
def get_my_alert_config(request: Request, db: DbSession, current_user: CurrentUser = None):
    """Get current user's SMS alert configuration."""
    for cfg in _alert_configs:
        if cfg["staff_user_id"] == 0:
            return SMSAlertConfigResponse(**{k: v for k, v in cfg.items() if k in SMSAlertConfigResponse.model_fields})
    raise HTTPException(status_code=404, detail="No SMS alert configuration found")


@router.put("/config/{config_id}", response_model=SMSAlertConfigResponse)
@limiter.limit("30/minute")
def update_alert_config(request: Request, config_id: int, data: SMSAlertConfigCreate, db: DbSession, current_user: CurrentUser = None):
    """Update SMS alert configuration."""
    for cfg in _alert_configs:
        if cfg["id"] == config_id:
            for field, value in data.model_dump().items():
                if field in cfg:
                    cfg[field] = value
            return SMSAlertConfigResponse(**{k: v for k, v in cfg.items() if k in SMSAlertConfigResponse.model_fields})
    raise HTTPException(status_code=404, detail="Configuration not found")


@router.delete("/config/{config_id}")
@limiter.limit("30/minute")
def delete_alert_config(request: Request, config_id: int, db: DbSession, current_user: CurrentUser = None):
    """Delete SMS alert configuration."""
    global _alert_configs
    original_len = len(_alert_configs)
    _alert_configs = [cfg for cfg in _alert_configs if cfg["id"] != config_id]
    if len(_alert_configs) == original_len:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration deleted"}


@router.put("/config/{config_id}/toggle")
@limiter.limit("30/minute")
def toggle_alert_config(request: Request, config_id: int, db: DbSession, current_user: CurrentUser = None):
    """Toggle SMS alerts on/off."""
    for cfg in _alert_configs:
        if cfg["id"] == config_id:
            cfg["is_active"] = not cfg["is_active"]
            return {"is_active": cfg["is_active"]}
    raise HTTPException(status_code=404, detail="Configuration not found")


# ==================== ALERT TRIGGERING ENDPOINTS ====================

async def send_alert_to_managers(alert_type: str, message: str, order_id: Optional[int] = None, amount: Optional[float] = None):
    """Send SMS alerts to all configured managers."""
    global _next_log_id

    alert_type_mapping = {
        "void": "alert_on_voids",
        "refund": "alert_on_refunds",
        "discount": "alert_on_discounts",
        "correction": "alert_on_corrections",
        "cash_drawer": "alert_on_cash_drawer",
        "low_stock": "alert_on_low_stock",
        "complaint": "alert_on_customer_complaints",
        "eod_report": "alert_on_eod_reports",
    }

    config_field = alert_type_mapping.get(alert_type)
    if not config_field:
        return

    for cfg in _alert_configs:
        if not cfg.get("is_active"):
            continue
        if not cfg.get(config_field, False):
            continue

        if alert_type == "void" and amount and amount < cfg.get("min_void_amount", 0):
            continue
        if alert_type == "refund" and amount and amount < cfg.get("min_refund_amount", 0):
            continue

        result = await sms_service.send_sms(cfg["phone_number"], message)

        log = {
            "id": _next_log_id,
            "alert_type": alert_type,
            "message": message,
            "phone_number": cfg["phone_number"],
            "delivery_status": "sent" if result.get("success") else "failed",
            "sent_at": datetime.utcnow().isoformat() if result.get("success") else None,
            "created_at": datetime.utcnow().isoformat(),
        }
        _alert_logs.append(log)
        _next_log_id += 1


@router.post("/trigger/void")
@limiter.limit("30/minute")
async def trigger_void_alert(
    request: Request,
    order_id: int, amount: float, reason: str,
    background_tasks: BackgroundTasks,
    db: DbSession, current_user: CurrentUser = None,
):
    """Trigger void alert (called when an order item is voided)."""
    message = (
        f"VOID ALERT: Order #{order_id}\n"
        f"Amount: ${amount:.2f}\n"
        f"Reason: {reason}\n"
        f"Time: {datetime.now().strftime('%H:%M')}"
    )
    background_tasks.add_task(send_alert_to_managers, "void", message, order_id, amount)
    return {"message": "Alert triggered"}


@router.post("/trigger/refund")
@limiter.limit("30/minute")
async def trigger_refund_alert(
    request: Request,
    order_id: int, amount: float, reason: str,
    background_tasks: BackgroundTasks,
    db: DbSession, current_user: CurrentUser = None,
):
    """Trigger refund alert."""
    message = (
        f"REFUND ALERT: Order #{order_id}\n"
        f"Amount: ${amount:.2f}\n"
        f"Reason: {reason}\n"
        f"Time: {datetime.now().strftime('%H:%M')}"
    )
    background_tasks.add_task(send_alert_to_managers, "refund", message, order_id, amount)
    return {"message": "Alert triggered"}


@router.post("/trigger/discount")
@limiter.limit("30/minute")
async def trigger_discount_alert(
    request: Request,
    order_id: int, discount_percent: float, discount_amount: float,
    background_tasks: BackgroundTasks,
    db: DbSession, current_user: CurrentUser = None,
):
    """Trigger discount alert for large discounts."""
    message = (
        f"DISCOUNT ALERT: Order #{order_id}\n"
        f"Discount: {discount_percent}% (${discount_amount:.2f})\n"
        f"Time: {datetime.now().strftime('%H:%M')}"
    )
    background_tasks.add_task(send_alert_to_managers, "discount", message, order_id, discount_amount)
    return {"message": "Alert triggered"}


@router.post("/trigger/cash-drawer")
@limiter.limit("30/minute")
async def trigger_cash_drawer_alert(
    request: Request,
    reason: str,
    background_tasks: BackgroundTasks,
    db: DbSession, current_user: CurrentUser = None,
):
    """Trigger cash drawer open alert."""
    message = (
        f"CASH DRAWER ALERT\n"
        f"Reason: {reason}\n"
        f"Time: {datetime.now().strftime('%H:%M')}"
    )
    background_tasks.add_task(send_alert_to_managers, "cash_drawer", message, None, None)
    return {"message": "Alert triggered"}


@router.post("/trigger/complaint")
@limiter.limit("30/minute")
async def trigger_complaint_alert(
    request: Request,
    table_number: str, complaint: str,
    background_tasks: BackgroundTasks,
    db: DbSession, current_user: CurrentUser = None,
):
    """Trigger customer complaint alert."""
    message = (
        f"COMPLAINT ALERT\n"
        f"Table: {table_number}\n"
        f"Complaint: {complaint[:100]}...\n"
        f"Time: {datetime.now().strftime('%H:%M')}"
    )
    background_tasks.add_task(send_alert_to_managers, "complaint", message, None, None)
    return {"message": "Alert triggered"}


# ==================== ALERT LOGS ====================

@router.get("/logs", response_model=List[SMSAlertLogResponse])
@limiter.limit("60/minute")
def get_alert_logs(
    request: Request,
    db: DbSession, current_user: CurrentUser = None,
    alert_type: Optional[str] = None, skip: int = 0, limit: int = 50,
):
    """Get SMS alert logs."""
    filtered = list(_alert_logs)
    if alert_type:
        filtered = [log for log in filtered if log["alert_type"] == alert_type]
    filtered.sort(key=lambda x: x["created_at"], reverse=True)
    page = filtered[skip : skip + limit]
    return [SMSAlertLogResponse(**log) for log in page]


@router.get("/stats")
@limiter.limit("60/minute")
def get_alert_stats(request: Request, db: DbSession, current_user: CurrentUser = None):
    """Get SMS alert statistics."""
    total = len(_alert_logs)
    delivered = sum(1 for log in _alert_logs if log["delivery_status"] == "sent")

    by_type: dict = {}
    for log in _alert_logs:
        t = log["alert_type"]
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "total_alerts": total,
        "delivered": delivered,
        "failed": total - delivered,
        "success_rate": round(delivered / total * 100, 2) if total > 0 else 0,
        "by_type": [{"type": t, "count": c} for t, c in by_type.items()],
    }


# ==================== TEST ENDPOINT ====================

@router.post("/test")
@limiter.limit("30/minute")
async def send_test_sms(request: Request, data: TestSMSRequest, db: DbSession, current_user: CurrentUser = None):
    """Send a test SMS to verify configuration."""
    result = await sms_service.send_sms(data.phone_number, f"BJ's Bar POS Test: {data.message}")
    return {
        "success": result.get("success"),
        "message": "Test SMS sent" if result.get("success") else f"Failed: {result.get('error')}",
    }
