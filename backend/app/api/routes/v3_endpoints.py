"""
V3.0 API Endpoints - All Missing Features from iiko & Toast
Complete API routes for all new services
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date, time

from app.db.session import get_db
# Create V3 router
v3_router = APIRouter(tags=["V3.0 Features"])


# ==================== KITCHEN DISPLAY ====================
kitchen_router = APIRouter(prefix="/kitchen", tags=["Kitchen Display"])

class CreateTicketRequest(BaseModel):
    order_id: int
    items: List[dict]
    table_number: Optional[str] = None
    server_name: Optional[str] = None
    is_rush: bool = False

@kitchen_router.post("/tickets")
async def create_ticket(request: CreateTicketRequest, db: Session = Depends(get_db)):
    """Create kitchen tickets"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.create_ticket(
        order_id=request.order_id,
        items=request.items,
        table_number=request.table_number,
        server_name=request.server_name,
        is_rush=request.is_rush
    )

@kitchen_router.post("/tickets/{ticket_id}/bump")
async def bump_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """Bump (complete) a ticket"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.bump_ticket(ticket_id)

@kitchen_router.post("/tickets/{ticket_id}/recall")
async def recall_ticket(ticket_id: str, reason: Optional[str] = None, db: Session = Depends(get_db)):
    """Recall a bumped ticket"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.recall_ticket(ticket_id, reason)

@kitchen_router.get("/stations/{station_id}/display")
async def get_station_display(station_id: str, db: Session = Depends(get_db)):
    """Get station display"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.get_station_display(station_id)

@kitchen_router.get("/expo")
async def get_expo_display(db: Session = Depends(get_db)):
    """Get expo screen"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.get_expo_display(venue_id=1)

@kitchen_router.get("/alerts")
async def get_alerts(station_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Get cook time alerts"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.get_cook_time_alerts(venue_id=1, station_code=station_id)

@kitchen_router.get("/overview")
async def get_overview(db: Session = Depends(get_db)):
    """Get kitchen overview"""
    from app.services.kitchen_display_service import KitchenDisplayService
    service = KitchenDisplayService(db)
    return service.get_kitchen_overview(venue_id=1)

@kitchen_router.post("/orders/{order_id}/fire/{course}")
async def fire_course(order_id: int, course: str, db: Session = Depends(get_db)):
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
async def apple_pay_session(request: ApplePayRequest, db: Session = Depends(get_db)):
    """Create Apple Pay session"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.create_apple_pay_session(request.order_id, request.amount, request.currency)

@payments_router.post("/google-pay/session")
async def google_pay_session(request: ApplePayRequest, db: Session = Depends(get_db)):
    """Create Google Pay session"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.create_google_pay_session(request.order_id, request.amount, request.currency)

@payments_router.post("/table-payment/link")
async def table_payment_link(request: TablePaymentRequest, db: Session = Depends(get_db)):
    """Generate pay at table link"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.generate_table_payment_link(
        request.table_id, request.order_id, request.amount, request.include_tip
    )

@payments_router.get("/table-payment/{payment_token}")
async def get_table_payment(payment_token: str, db: Session = Depends(get_db)):
    """Get payment details"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.get_table_payment_details(payment_token)

@payments_router.post("/table-payment/{payment_token}/pay")
async def process_table_payment(
    payment_token: str, 
    request: ProcessPaymentRequest, 
    db: Session = Depends(get_db)
):
    """Process pay at table"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.process_table_payment(
        payment_token, request.payment_method, request.tip_percentage, request.tip_amount
    )

@payments_router.post("/pre-auth")
async def create_pre_auth(request: PreAuthRequest, db: Session = Depends(get_db)):
    """Create pre-authorization"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.create_pre_auth(request.order_id, request.card_token, request.amount)

@payments_router.post("/pre-auth/{auth_id}/capture")
async def capture_pre_auth(
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
async def create_split(request: SplitRequest, db: Session = Depends(get_db)):
    """Create split payment"""
    from app.services.mobile_payments_service import MobilePaymentsService
    service = MobilePaymentsService(db)
    return service.create_split_payment(request.order_id, request.total_amount, request.splits)

@payments_router.get("/tips/suggestions/{amount}")
async def tip_suggestions(amount: float, db: Session = Depends(get_db)):
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
async def start_break(request: BreakRequest, db: Session = Depends(get_db)):
    """Start break"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.start_break(
        request.staff_id, request.shift_id, request.break_type, 
        request.is_paid, request.scheduled_duration
    )

@labor_router.post("/breaks/{break_id}/end")
async def end_break(break_id: str, notes: Optional[str] = None, db: Session = Depends(get_db)):
    """End break"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.end_break(break_id, notes)

@labor_router.get("/overtime/{staff_id}")
async def get_overtime(staff_id: int, week_start: date, week_end: date, db: Session = Depends(get_db)):
    """Calculate overtime"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.calculate_overtime(staff_id, week_start, week_end)

@labor_router.get("/overtime/alerts")
async def overtime_alerts(db: Session = Depends(get_db)):
    """Get overtime alerts"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.get_overtime_alerts(venue_id=1)

@labor_router.post("/time-off/request")
async def request_time_off(request: TimeOffRequest, db: Session = Depends(get_db)):
    """Request time off"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.request_time_off(
        request.staff_id, request.start_date, request.end_date,
        request.time_off_type, request.reason
    )

@labor_router.post("/time-off/{request_id}/approve")
async def approve_time_off(request_id: str, manager_id: int, db: Session = Depends(get_db)):
    """Approve time off"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.approve_time_off(request_id, manager_id)

@labor_router.get("/time-off/balance/{staff_id}")
async def time_off_balance(staff_id: int, db: Session = Depends(get_db)):
    """Get time off balance"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.get_time_off_balance(staff_id)

@labor_router.post("/shift-swap/request")
async def request_shift_swap(request: ShiftSwapRequest, db: Session = Depends(get_db)):
    """Request shift swap"""
    from app.services.labor_compliance_service import LaborComplianceService
    service = LaborComplianceService(db)
    return service.request_shift_swap(
        request.requesting_staff_id, request.target_staff_id,
        request.requesting_shift_id, request.target_shift_id
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
async def check_address(address: str, db: Session = Depends(get_db)):
    """Check delivery address"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.check_delivery_address(address)

@delivery_router.post("/orders")
async def create_delivery(request: DeliveryOrderRequest, db: Session = Depends(get_db)):
    """Create delivery order"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.create_delivery_order(
        request.order_id, request.customer_id, request.delivery_address,
        request.latitude, request.longitude, request.contact_phone
    )

@delivery_router.get("/orders/{delivery_id}/tracking")
async def track_delivery(delivery_id: str, db: Session = Depends(get_db)):
    """Track delivery"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.get_delivery_tracking(delivery_id)

@delivery_router.post("/drivers")
async def register_driver(request: DriverRequest, db: Session = Depends(get_db)):
    """Register driver"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.register_driver(request.staff_id, request.name, request.phone, request.vehicle_type)

@delivery_router.post("/drivers/{driver_id}/location")
async def update_driver_location(driver_id: int, lat: float, lng: float, db: Session = Depends(get_db)):
    """Update driver location"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.update_driver_location(driver_id, lat, lng)

@delivery_router.get("/drivers/available")
async def available_drivers(db: Session = Depends(get_db)):
    """Get available drivers"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.get_available_drivers()

@delivery_router.get("/capacity")
async def check_capacity(db: Session = Depends(get_db)):
    """Check order capacity"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.check_order_capacity(venue_id=1)

@delivery_router.post("/curbside")
async def create_curbside(request: CurbsideRequest, db: Session = Depends(get_db)):
    """Create curbside order"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.create_curbside_order(
        request.order_id, request.customer_id, request.customer_name,
        request.customer_phone, request.vehicle_description
    )

@delivery_router.post("/curbside/{curbside_id}/arrived")
async def customer_arrived(curbside_id: str, parking_spot: Optional[str] = None, db: Session = Depends(get_db)):
    """Mark customer arrived"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.customer_arrived(curbside_id, parking_spot)

@delivery_router.post("/catering")
async def create_catering(request: CateringRequest, db: Session = Depends(get_db)):
    """Create catering order"""
    from app.services.online_ordering_service import OnlineOrderingService
    service = OnlineOrderingService(db)
    return service.create_catering_order(
        request.customer_id, request.customer_name, request.customer_email,
        request.customer_phone, request.event_date, request.event_time,
        request.guest_count, request.event_type, request.items
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
async def connect_platform(request: ConnectRequest, db: Session = Depends(get_db)):
    """Connect accounting platform"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.connect_platform(venue_id=1, platform=request.platform, credentials=request.credentials)

@accounting_router.post("/sync/{integration_id}")
async def run_sync(integration_id: str, db: Session = Depends(get_db)):
    """Run sync"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.run_sync(integration_id)

@accounting_router.get("/sync/{integration_id}/status")
async def sync_status(integration_id: str, db: Session = Depends(get_db)):
    """Get sync status"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.get_sync_status(integration_id)

@accounting_router.post("/sync-daily-sales")
async def sync_sales(sales_date: date, db: Session = Depends(get_db)):
    """Sync daily sales"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.sync_daily_sales(venue_id=1, sales_date=sales_date)

@accounting_router.post("/expenses")
async def record_expense(request: ExpenseRequest, db: Session = Depends(get_db)):
    """Record expense"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.record_expense(
        venue_id=1, expense_date=request.expense_date, vendor=request.vendor,
        category=request.category, amount=request.amount, tax_amount=request.tax_amount
    )

@accounting_router.get("/reports/profit-loss")
async def profit_loss(start_date: date, end_date: date, db: Session = Depends(get_db)):
    """Get P&L"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.get_profit_loss(venue_id=1, start_date=start_date, end_date=end_date)

@accounting_router.get("/reports/balance-sheet")
async def balance_sheet(as_of_date: date, db: Session = Depends(get_db)):
    """Get balance sheet"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.get_balance_sheet(venue_id=1, as_of_date=as_of_date)

@accounting_router.get("/reports/cash-flow")
async def cash_flow(start_date: date, end_date: date, db: Session = Depends(get_db)):
    """Get cash flow"""
    from app.services.accounting_integration_service import AccountingIntegrationService
    service = AccountingIntegrationService(db)
    return service.get_cash_flow(venue_id=1, start_date=start_date, end_date=end_date)


# ==================== REPORTS ====================
reports_router = APIRouter(prefix="/reports", tags=["Custom Reports"])

class ScheduleReportRequest(BaseModel):
    report_type: str
    frequency: str
    recipients: List[str]
    format: str = "pdf"

@reports_router.get("/sales")
async def sales_report(start_date: datetime, end_date: datetime, group_by: str = "day", db: Session = Depends(get_db)):
    """Generate sales report"""
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.generate_sales_report(venue_id=1, start_date=start_date, end_date=end_date, group_by=group_by)

@reports_router.get("/product-mix")
async def product_mix_report(start_date: datetime, end_date: datetime, db: Session = Depends(get_db)):
    """Generate product mix report"""
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.generate_product_mix_report(venue_id=1, start_date=start_date, end_date=end_date)

@reports_router.get("/staff-performance")
async def staff_report(start_date: datetime, end_date: datetime, db: Session = Depends(get_db)):
    """Generate staff performance report"""
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.generate_staff_performance_report(venue_id=1, start_date=start_date, end_date=end_date)

@reports_router.get("/inventory")
async def inventory_report(include_low_stock: bool = True, db: Session = Depends(get_db)):
    """Generate inventory report"""
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.generate_inventory_report(venue_id=1, include_low_stock=include_low_stock)

@reports_router.get("/customers")
async def customer_report(start_date: datetime, end_date: datetime, db: Session = Depends(get_db)):
    """Generate customer report"""
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.generate_customer_report(venue_id=1, start_date=start_date, end_date=end_date)

@reports_router.post("/schedule")
async def schedule_report(request: ScheduleReportRequest, db: Session = Depends(get_db)):
    """Schedule recurring report"""
    from app.services.custom_reports_service import ReportService
    service = ReportService(db)
    return service.schedule_report(
        venue_id=1, report_type=request.report_type, frequency=request.frequency,
        recipients=request.recipients, format=request.format
    )

@reports_router.get("/scheduled")
async def list_scheduled(db: Session = Depends(get_db)):
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
async def create_campaign(request: CampaignRequest, db: Session = Depends(get_db)):
    """Create campaign"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.create_campaign(
        venue_id=1, name=request.name, campaign_type=request.campaign_type,
        body=request.body, target_segment=request.target_segment, send_at=request.send_at
    )

@marketing_router.post("/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: str, test_mode: bool = False, db: Session = Depends(get_db)):
    """Send campaign"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.send_campaign(campaign_id, test_mode)

@marketing_router.get("/campaigns/{campaign_id}/stats")
async def campaign_stats(campaign_id: str, db: Session = Depends(get_db)):
    """Get campaign stats"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.get_campaign_stats(campaign_id)

@marketing_router.get("/campaigns")
async def list_campaigns(status: Optional[str] = None, db: Session = Depends(get_db)):
    """List campaigns"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.list_campaigns(venue_id=1, status=status)

@marketing_router.post("/automations")
async def create_automation(request: AutomationRequest, db: Session = Depends(get_db)):
    """Create automation"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.create_automation(
        venue_id=1, name=request.name, trigger_type=request.trigger_type,
        campaign_template=request.campaign_template
    )

@marketing_router.get("/automations")
async def list_automations(db: Session = Depends(get_db)):
    """List automations"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.list_automations(venue_id=1)

@marketing_router.get("/segments/{segment_type}/customers")
async def segment_customers(segment_type: str, db: Session = Depends(get_db)):
    """Get segment customers"""
    from app.services.marketing_service import MarketingService
    service = MarketingService(db)
    return service.get_segment_customers(venue_id=1, segment_type=segment_type)

@marketing_router.get("/templates")
async def get_templates(db: Session = Depends(get_db)):
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
