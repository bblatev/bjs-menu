"""
V3.0 API Endpoints - All Missing Features from iiko & Toast
Complete API routes for all new services
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date, time, timedelta, timezone

from app.db.session import get_db
from app.core.rate_limit import limiter

import logging

logger = logging.getLogger(__name__)

# Create V3 router
v3_router = APIRouter(tags=["V3.0 Features"])


@v3_router.get("/")
@limiter.limit("60/minute")
async def get_v3_root(request: Request, db: Session = Depends(get_db)):
    """V3 API features status."""
    return {"module": "v3", "version": "3.0", "status": "active", "features": ["kitchen-display", "mobile-payments", "labor-management", "delivery", "accounting", "reports", "marketing"]}


# ==================== KITCHEN DISPLAY ====================
kitchen_router = APIRouter(prefix="/kitchen", tags=["Kitchen Display"])

class CreateTicketRequest(BaseModel):
    order_id: int
    items: List[dict]
    table_number: Optional[str] = None
    server_name: Optional[str] = None
    is_rush: bool = False

@kitchen_router.post("/tickets")
@limiter.limit("30/minute")
async def create_ticket(request: Request, body: CreateTicketRequest, db: Session = Depends(get_db)):
    """Create kitchen tickets"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.create_ticket(
        order_id=body.order_id,
        items=body.items,
        table_number=body.table_number,
        server_name=body.server_name,
        is_rush=body.is_rush
    )

@kitchen_router.post("/tickets/{ticket_id}/bump")
@limiter.limit("30/minute")
async def bump_ticket(request: Request, ticket_id: str, db: Session = Depends(get_db)):
    """Bump (complete) a ticket"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.bump_ticket(ticket_id)

@kitchen_router.post("/tickets/{ticket_id}/recall")
@limiter.limit("30/minute")
async def recall_ticket(request: Request, ticket_id: str, reason: Optional[str] = None, db: Session = Depends(get_db)):
    """Recall a bumped ticket"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.recall_ticket(ticket_id, reason)

@kitchen_router.get("/stations/{station_id}/display")
@limiter.limit("60/minute")
async def get_station_display(request: Request, station_id: str, db: Session = Depends(get_db)):
    """Get station display"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.get_station_display(venue_id=1, station_code=station_id)

@kitchen_router.get("/expo")
@limiter.limit("60/minute")
async def get_expo_display(request: Request, db: Session = Depends(get_db)):
    """Get expo screen"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.get_expo_display(venue_id=1)

@kitchen_router.get("/alerts")
@limiter.limit("60/minute")
async def get_alerts(request: Request, station_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Get cook time alerts"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.get_cook_time_alerts(venue_id=1, station_code=station_id)

@kitchen_router.get("/overview")
@limiter.limit("60/minute")
async def get_overview(request: Request, db: Session = Depends(get_db)):
    """Get kitchen overview"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.get_kitchen_overview(venue_id=1)

@kitchen_router.post("/orders/{order_id}/fire/{course}")
@limiter.limit("30/minute")
async def fire_course(request: Request, order_id: int, course: str, db: Session = Depends(get_db)):
    """Fire a course"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.fire_course(order_id, course)


# ==================== MOBILE PAYMENTS ====================
payments_router = APIRouter(prefix="/payments", tags=["Mobile Payments"])

class ApplePayRequest(BaseModel):
    order_id: int
    amount: float
    currency: str = "EUR"

class TablePaymentRequest(BaseModel):
    table_id: int
    order_id: int
    amount: float
    include_tip: bool = True

class ProcessPaymentRequest(BaseModel):
    payment_method: str
    tip_percentage: Optional[float] = None
    tip_amount: Optional[float] = None

class PreAuthRequest(BaseModel):
    order_id: int
    card_token: str
    amount: float

class SplitRequest(BaseModel):
    order_id: int
    total_amount: float
    splits: List[dict]

@payments_router.post("/apple-pay/session")
@limiter.limit("30/minute")
async def apple_pay_session(request: Request, body: ApplePayRequest, db: Session = Depends(get_db)):
    """Create Apple Pay session"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.create_apple_pay_session(body.order_id, body.amount, body.currency)

@payments_router.post("/google-pay/session")
@limiter.limit("30/minute")
async def google_pay_session(request: Request, body: ApplePayRequest, db: Session = Depends(get_db)):
    """Create Google Pay session"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.create_google_pay_session(body.order_id, body.amount, body.currency)

@payments_router.post("/table-payment/link")
@limiter.limit("30/minute")
async def table_payment_link(request: Request, body: TablePaymentRequest, db: Session = Depends(get_db)):
    """Generate pay at table link"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.generate_table_payment_link(
        body.table_id, body.order_id, body.amount, body.include_tip
    )

@payments_router.get("/table-payment/{payment_token}")
@limiter.limit("60/minute")
async def get_table_payment(request: Request, payment_token: str, db: Session = Depends(get_db)):
    """Get payment details"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.get_table_payment_details(payment_token)

@payments_router.post("/table-payment/{payment_token}/pay")
@limiter.limit("30/minute")
async def process_table_payment(
    request: Request,
    payment_token: str,
    body: ProcessPaymentRequest,
    db: Session = Depends(get_db)
):
    """Process pay at table"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.process_table_payment(
        payment_token, body.payment_method, body.tip_percentage, body.tip_amount
    )

@payments_router.post("/pre-auth")
@limiter.limit("30/minute")
async def create_pre_auth(request: Request, body: PreAuthRequest, db: Session = Depends(get_db)):
    """Create pre-authorization"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.create_pre_auth(body.order_id, body.card_token, body.amount)

@payments_router.post("/pre-auth/{auth_id}/capture")
@limiter.limit("30/minute")
async def capture_pre_auth(
    request: Request,
    auth_id: str,
    amount: Optional[float] = None,
    tip: float = 0,
    db: Session = Depends(get_db)
):
    """Capture pre-auth"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.capture_pre_auth(auth_id, amount, tip)

@payments_router.post("/split")
@limiter.limit("30/minute")
async def create_split(request: Request, body: SplitRequest, db: Session = Depends(get_db)):
    """Create split payment"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.create_split_payment(body.order_id, body.total_amount, body.splits)

@payments_router.get("/tips/suggestions/{amount}")
@limiter.limit("60/minute")
async def tip_suggestions(request: Request, amount: float, db: Session = Depends(get_db)):
    """Get tip suggestions"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.get_tip_suggestions(amount)


# ==================== LABOR MANAGEMENT ====================
labor_router = APIRouter(prefix="/labor", tags=["Labor Management"])

class BreakRequest(BaseModel):
    staff_id: int
    shift_id: int
    break_type: str = "rest"
    is_paid: bool = False
    scheduled_duration: int = 15

class TimeOffRequest(BaseModel):
    staff_id: int
    start_date: date
    end_date: date
    time_off_type: str
    reason: Optional[str] = None

class ShiftSwapRequest(BaseModel):
    requesting_staff_id: int
    target_staff_id: int
    requesting_shift_id: int
    target_shift_id: int

@labor_router.post("/breaks/start")
@limiter.limit("30/minute")
async def start_break(request: Request, body: BreakRequest, db: Session = Depends(get_db)):
    """Start break"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.start_break(
        body.staff_id, body.shift_id, body.break_type,
        body.is_paid, body.scheduled_duration
    )

@labor_router.post("/breaks/{break_id}/end")
@limiter.limit("30/minute")
async def end_break(request: Request, break_id: str, notes: Optional[str] = None, db: Session = Depends(get_db)):
    """End break"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.end_break(break_id, notes)

@labor_router.get("/overtime/alerts")
@limiter.limit("60/minute")
async def overtime_alerts(request: Request, db: Session = Depends(get_db)):
    """Get overtime alerts"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.get_overtime_alerts(venue_id=1)

@labor_router.get("/overtime/{staff_id}")
@limiter.limit("60/minute")
async def get_overtime(request: Request, staff_id: int, week_start: date = Query(default=None), week_end: date = Query(default=None), db: Session = Depends(get_db)):
    """Calculate overtime"""
    from app.services.labor_compliance_service import LaborComplianceService
    if week_start is None:
        week_start = date.today() - timedelta(days=date.today().weekday())
    if week_end is None:
        week_end = week_start + timedelta(days=6)
    service = LaborComplianceService(db)
    return service.calculate_overtime(staff_id, week_start, week_end)

@labor_router.post("/time-off/request")
@limiter.limit("30/minute")
async def request_time_off(request: Request, body: TimeOffRequest, db: Session = Depends(get_db)):
    """Request time off"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.request_time_off(
        body.staff_id, body.start_date, body.end_date,
        body.time_off_type, body.reason
    )

@labor_router.post("/time-off/{request_id}/approve")
@limiter.limit("30/minute")
async def approve_time_off(request: Request, request_id: str, manager_id: int, db: Session = Depends(get_db)):
    """Approve time off"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.approve_time_off(request_id, manager_id)

@labor_router.get("/time-off/balance/{staff_id}")
@limiter.limit("60/minute")
async def time_off_balance(request: Request, staff_id: int, db: Session = Depends(get_db)):
    """Get time off balance"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.get_time_off_balance(staff_id)

@labor_router.post("/shift-swap/request")
@limiter.limit("30/minute")
async def request_shift_swap(request: Request, body: ShiftSwapRequest, db: Session = Depends(get_db)):
    """Request shift swap"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.request_shift_swap(
        body.requesting_staff_id, body.target_staff_id,
        body.requesting_shift_id, body.target_shift_id
    )


# ==================== DELIVERY ====================
delivery_router = APIRouter(prefix="/delivery", tags=["Online Ordering & Delivery"])

class DeliveryOrderRequest(BaseModel):
    order_id: int
    customer_id: int
    delivery_address: str
    latitude: float
    longitude: float
    contact_phone: str

class DriverRequest(BaseModel):
    staff_id: int
    name: str
    phone: str
    vehicle_type: str = "car"

class CurbsideRequest(BaseModel):
    order_id: int
    customer_id: int
    customer_name: str
    customer_phone: str
    vehicle_description: Optional[str] = None

class CateringRequest(BaseModel):
    customer_id: int
    customer_name: str
    customer_email: str
    customer_phone: str
    event_date: date
    event_time: time
    guest_count: int
    event_type: str
    items: List[dict]

@delivery_router.post("/check-address")
@limiter.limit("30/minute")
async def check_address(request: Request, address: str = Query("123 Main St"), db: Session = Depends(get_db)):
    """Check delivery address"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.check_delivery_address(address)

@delivery_router.post("/orders")
@limiter.limit("30/minute")
async def create_delivery(request: Request, body: DeliveryOrderRequest, db: Session = Depends(get_db)):
    """Create delivery order"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.create_delivery_order(
        body.order_id, body.customer_id, body.delivery_address,
        body.latitude, body.longitude, body.contact_phone
    )

@delivery_router.get("/orders/{delivery_id}/tracking")
@limiter.limit("60/minute")
async def track_delivery(request: Request, delivery_id: str, db: Session = Depends(get_db)):
    """Track delivery"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.get_delivery_tracking(delivery_id)

@delivery_router.post("/drivers")
@limiter.limit("30/minute")
async def register_driver(request: Request, body: DriverRequest, db: Session = Depends(get_db)):
    """Register driver"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.register_driver(body.staff_id, body.name, body.phone, body.vehicle_type)

@delivery_router.post("/drivers/{driver_id}/location")
@limiter.limit("30/minute")
async def update_driver_location(request: Request, driver_id: int, lat: float = Query(42.6977), lng: float = Query(23.3219), db: Session = Depends(get_db)):
    """Update driver location"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.update_driver_location(driver_id, lat, lng)

@delivery_router.get("/drivers/available")
@limiter.limit("60/minute")
async def available_drivers(request: Request, db: Session = Depends(get_db)):
    """Get available drivers"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.get_available_drivers()

@delivery_router.get("/capacity")
@limiter.limit("60/minute")
async def check_capacity(request: Request, db: Session = Depends(get_db)):
    """Check order capacity"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.check_order_capacity(venue_id=1)

@delivery_router.post("/curbside")
@limiter.limit("30/minute")
async def create_curbside(request: Request, body: CurbsideRequest, db: Session = Depends(get_db)):
    """Create curbside order"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.create_curbside_order(
        body.order_id, body.customer_id, body.customer_name,
        body.customer_phone, body.vehicle_description
    )

@delivery_router.post("/curbside/{curbside_id}/arrived")
@limiter.limit("30/minute")
async def customer_arrived(request: Request, curbside_id: str, parking_spot: Optional[str] = None, db: Session = Depends(get_db)):
    """Mark customer arrived"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.customer_arrived(curbside_id, parking_spot)

@delivery_router.post("/catering")
@limiter.limit("30/minute")
async def create_catering(request: Request, body: CateringRequest, db: Session = Depends(get_db)):
    """Create catering order"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.create_catering_order(
        body.customer_id, body.customer_name, body.customer_email,
        body.customer_phone, body.event_date, body.event_time,
        body.guest_count, body.event_type, body.items
    )


# ==================== ACCOUNTING ====================
accounting_router = APIRouter(prefix="/accounting", tags=["Accounting Integration"])

class ConnectRequest(BaseModel):
    platform: str
    credentials: dict

class ExpenseRequest(BaseModel):
    expense_date: date
    vendor: str
    category: str
    amount: float
    tax_amount: float = 0

@accounting_router.post("/connect")
@limiter.limit("30/minute")
async def connect_platform(request: Request, body: ConnectRequest, db: Session = Depends(get_db)):
    """Connect accounting platform"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.connect_platform(venue_id=1, platform=body.platform, credentials=body.credentials)

@accounting_router.post("/sync/{integration_id}")
@limiter.limit("30/minute")
async def run_sync(request: Request, integration_id: str, db: Session = Depends(get_db)):
    """Run sync"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.run_sync(integration_id)

@accounting_router.get("/sync/{integration_id}/status")
@limiter.limit("60/minute")
async def sync_status(request: Request, integration_id: str, db: Session = Depends(get_db)):
    """Get sync status"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.get_sync_status(integration_id)

@accounting_router.post("/sync-daily-sales")
@limiter.limit("30/minute")
async def sync_sales(request: Request, sales_date: date, db: Session = Depends(get_db)):
    """Sync daily sales"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.sync_daily_sales(venue_id=1, sales_date=sales_date)

@accounting_router.post("/expenses")
@limiter.limit("30/minute")
async def record_expense(request: Request, body: ExpenseRequest, db: Session = Depends(get_db)):
    """Record expense"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.record_expense(
        venue_id=1, expense_date=body.expense_date, vendor=body.vendor,
        category=body.category, amount=body.amount, tax_amount=body.tax_amount
    )

@accounting_router.get("/reports/profit-loss")
@limiter.limit("60/minute")
async def profit_loss(request: Request, start_date: date = Query(default=None), end_date: date = Query(default=None), db: Session = Depends(get_db)):
    """Get P&L"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    try:
        from app.services.accounting_integration_service import AccountingIntegrationService
        service = AccountingIntegrationService(db)
        return service.get_profit_loss(venue_id=1, start_date=start_date, end_date=end_date)
    except Exception as e:
        logger.exception("Failed to generate P&L report")
        return {"success": False, "error": str(e), "period": {"start": start_date.isoformat(), "end": end_date.isoformat()}}

@accounting_router.get("/reports/balance-sheet")
@limiter.limit("60/minute")
async def balance_sheet(request: Request, as_of_date: date = Query(default=None), db: Session = Depends(get_db)):
    """Get balance sheet"""
    if as_of_date is None:
        as_of_date = date.today()
    try:
        from app.services.accounting_integration_service import AccountingIntegrationService
        service = AccountingIntegrationService(db)
        return service.get_balance_sheet(venue_id=1, as_of_date=as_of_date)
    except Exception as e:
        logger.exception("Failed to generate balance sheet")
        return {"success": False, "error": str(e), "as_of_date": as_of_date.isoformat()}

@accounting_router.get("/reports/cash-flow")
@limiter.limit("60/minute")
async def cash_flow(request: Request, start_date: date = Query(default=None), end_date: date = Query(default=None), db: Session = Depends(get_db)):
    """Get cash flow"""
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()
    try:
        from app.services.accounting_integration_service import AccountingIntegrationService
        service = AccountingIntegrationService(db)
        return service.get_cash_flow(venue_id=1, start_date=start_date, end_date=end_date)
    except Exception as e:
        logger.exception("Failed to generate cash flow report")
        return {"success": False, "error": str(e), "period": {"start": start_date.isoformat(), "end": end_date.isoformat()}}


# ==================== REPORTS ====================
reports_router = APIRouter(prefix="/reports", tags=["Custom Reports"])

class ScheduleReportRequest(BaseModel):
    report_type: str
    frequency: str
    recipients: List[str]
    format: str = "pdf"

@reports_router.get("/sales")
@limiter.limit("60/minute")
async def sales_report(request: Request, start_date: datetime = Query(default=None), end_date: datetime = Query(default=None), group_by: str = "day", db: Session = Depends(get_db)):
    """Generate sales report"""
    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.generate_sales_report(venue_id=1, start_date=start_date, end_date=end_date, group_by=group_by)

@reports_router.get("/product-mix")
@limiter.limit("60/minute")
async def product_mix_report(request: Request, start_date: datetime = Query(default=None), end_date: datetime = Query(default=None), db: Session = Depends(get_db)):
    """Generate product mix report"""
    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.generate_product_mix_report(venue_id=1, start_date=start_date, end_date=end_date)

@reports_router.get("/staff-performance")
@limiter.limit("60/minute")
async def staff_report(request: Request, start_date: datetime = Query(default=None), end_date: datetime = Query(default=None), db: Session = Depends(get_db)):
    """Generate staff performance report"""
    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.generate_staff_performance_report(venue_id=1, start_date=start_date, end_date=end_date)

@reports_router.get("/inventory")
@limiter.limit("60/minute")
async def inventory_report(request: Request, include_low_stock: bool = True, db: Session = Depends(get_db)):
    """Generate inventory report"""
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.generate_inventory_report(venue_id=1, include_low_stock=include_low_stock)

@reports_router.get("/customers")
@limiter.limit("60/minute")
async def customer_report(request: Request, start_date: datetime = Query(default=None), end_date: datetime = Query(default=None), db: Session = Depends(get_db)):
    """Generate customer report"""
    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.generate_customer_report(venue_id=1, start_date=start_date, end_date=end_date)

@reports_router.post("/schedule")
@limiter.limit("30/minute")
async def schedule_report(request: Request, body: ScheduleReportRequest, db: Session = Depends(get_db)):
    """Schedule recurring report"""
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.schedule_report(
        venue_id=1, report_type=body.report_type, frequency=body.frequency,
        recipients=body.recipients, format=body.format
    )

@reports_router.get("/scheduled")
@limiter.limit("60/minute")
async def list_scheduled(request: Request, db: Session = Depends(get_db)):
    """List scheduled reports"""
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.get_scheduled_reports(venue_id=1)


# ==================== MARKETING ====================
marketing_router = APIRouter(prefix="/marketing", tags=["Marketing & Campaigns"])

class CampaignRequest(BaseModel):
    name: str
    campaign_type: str
    body: dict
    target_segment: Optional[str] = None
    send_at: Optional[datetime] = None

class AutomationRequest(BaseModel):
    name: str
    trigger_type: str
    campaign_template: str

@marketing_router.post("/campaigns")
@limiter.limit("30/minute")
async def create_campaign(request: Request, body: CampaignRequest, db: Session = Depends(get_db)):
    """Create campaign"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.create_campaign(
        venue_id=1, name=body.name, campaign_type=body.campaign_type,
        body=body.body, target_segment=body.target_segment, send_at=body.send_at
    )

@marketing_router.post("/campaigns/{campaign_id}/send")
@limiter.limit("30/minute")
async def send_campaign(request: Request, campaign_id: str, test_mode: bool = False, db: Session = Depends(get_db)):
    """Send campaign"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.send_campaign(campaign_id, test_mode)

@marketing_router.get("/campaigns/{campaign_id}/stats")
@limiter.limit("60/minute")
async def campaign_stats(request: Request, campaign_id: str, db: Session = Depends(get_db)):
    """Get campaign stats"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.get_campaign_stats(campaign_id)

@marketing_router.get("/campaigns")
@limiter.limit("60/minute")
async def list_campaigns(request: Request, status: Optional[str] = None, db: Session = Depends(get_db)):
    """List campaigns"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.list_campaigns(venue_id=1, status=status)

@marketing_router.post("/automations")
@limiter.limit("30/minute")
async def create_automation(request: Request, body: AutomationRequest, db: Session = Depends(get_db)):
    """Create automation"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.create_automation(
        venue_id=1, name=body.name, trigger_type=body.trigger_type,
        campaign_template=body.campaign_template
    )

@marketing_router.get("/automations")
@limiter.limit("60/minute")
async def list_automations(request: Request, db: Session = Depends(get_db)):
    """List automations"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.list_automations(venue_id=1)

@marketing_router.get("/segments/{segment_type}/customers")
@limiter.limit("60/minute")
async def segment_customers(request: Request, segment_type: str, db: Session = Depends(get_db)):
    """Get segment customers"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.get_segment_customers(venue_id=1, segment_type=segment_type)

@marketing_router.get("/templates")
@limiter.limit("60/minute")
async def get_templates(request: Request, db: Session = Depends(get_db)):
    """Get campaign templates"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.get_templates()


# ==================== REGISTER ALL ROUTERS ====================
v3_router.include_router(kitchen_router)
v3_router.include_router(payments_router)
v3_router.include_router(labor_router)
v3_router.include_router(delivery_router)
v3_router.include_router(accounting_router)
v3_router.include_router(reports_router)
v3_router.include_router(marketing_router)

# Alias for dynamic module loader
router = v3_router
