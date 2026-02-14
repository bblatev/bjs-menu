"""
V3.1 API Endpoints - Complete Parity Features
API routes for Multi-Location, Payroll, Integrations, Benchmarking, Hardware, Support
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date

from app.db.session import get_db
from app.core.rate_limit import limiter

# Create V3.1 router
v31_router = APIRouter(tags=["V3.1 Complete Parity"])


# ==================== MULTI-LOCATION ENDPOINTS ====================
locations_router = APIRouter(prefix="/locations", tags=["Multi-Location Management"])


class CreateLocationRequest(BaseModel):
    name: str
    code: str
    address: dict
    contact: dict
    timezone: str = "Europe/Sofia"
    currency: str = "EUR"
    copy_menu_from: Optional[str] = None


class LocationGroupRequest(BaseModel):
    name: str
    description: str
    location_ids: List[str]


class InventoryTransferRequest(BaseModel):
    from_location_id: str
    to_location_id: str
    items: List[dict]
    notes: Optional[str] = None


@locations_router.post("/")
@limiter.limit("30/minute")
async def create_location(request: Request, body: CreateLocationRequest, db: Session = Depends(get_db)):
    """Create a new location"""
    from app.services.multi_location_service import MultiLocationService
    service = MultiLocationService(db)
    return service.create_location(
        name=body.name,
        code=body.code,
        address=body.address,
        contact=body.contact,
        timezone=body.timezone,
        currency=body.currency,
        copy_menu_from=body.copy_menu_from
    )


@locations_router.get("/")
@limiter.limit("60/minute")
async def list_locations(
    request: Request,
    status: Optional[str] = None,
    include_metrics: bool = False,
    db: Session = Depends(get_db)
):
    """List all locations"""
    from app.services.multi_location_service import MultiLocationService
    service = MultiLocationService(db)
    return service.list_locations(status=status, include_metrics=include_metrics)


@locations_router.get("/{location_id}")
@limiter.limit("60/minute")
async def get_location(request: Request, location_id: str, db: Session = Depends(get_db)):
    """Get location details"""
    from app.services.multi_location_service import MultiLocationService
    service = MultiLocationService(db)
    return service.get_location(location_id)


@locations_router.post("/{location_id}/status")
@limiter.limit("30/minute")
async def set_location_status(
    request: Request,
    location_id: str,
    status: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Set location status"""
    from app.services.multi_location_service import MultiLocationService
    service = MultiLocationService(db)
    return service.set_location_status(location_id, status, reason)


@locations_router.post("/groups")
@limiter.limit("30/minute")
async def create_location_group(request: Request, body: LocationGroupRequest, db: Session = Depends(get_db)):
    """Create a location group"""
    from app.services.multi_location_service import MultiLocationService
    service = MultiLocationService(db)
    return service.create_location_group(body.name, body.description, body.location_ids)


@locations_router.post("/sync-menu")
@limiter.limit("30/minute")
async def sync_menu(
    request: Request,
    source_location_id: str,
    target_location_ids: List[str],
    sync_type: str = "full",
    db: Session = Depends(get_db)
):
    """Sync menu across locations"""
    from app.services.multi_location_service import MultiLocationService
    service = MultiLocationService(db)
    return service.sync_menu_to_locations(source_location_id, target_location_ids, sync_type)


@locations_router.post("/inventory-transfer")
@limiter.limit("30/minute")
async def create_inventory_transfer(request: Request, body: InventoryTransferRequest, db: Session = Depends(get_db)):
    """Create inventory transfer between locations"""
    from app.services.multi_location_service import MultiLocationService
    service = MultiLocationService(db)
    return service.create_inventory_transfer(
        body.from_location_id,
        body.to_location_id,
        body.items,
        body.notes
    )


@locations_router.get("/reports/consolidated")
@limiter.limit("60/minute")
async def get_consolidated_report(
    request: Request,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """Get consolidated sales report across locations"""
    from app.services.multi_location_service import MultiLocationService
    service = MultiLocationService(db)
    return service.get_consolidated_sales_report(start_date, end_date)


@locations_router.get("/dashboard")
@limiter.limit("60/minute")
async def get_enterprise_dashboard(request: Request, db: Session = Depends(get_db)):
    """Get enterprise dashboard"""
    from app.services.multi_location_service import MultiLocationService
    service = MultiLocationService(db)
    return service.get_enterprise_dashboard()


# ==================== PAYROLL ENDPOINTS ====================
payroll_router = APIRouter(prefix="/payroll", tags=["Payroll Processing"])


class EmployeePayrollSetup(BaseModel):
    staff_id: int
    pay_rate: float
    pay_type: str = "hourly"
    pay_frequency: str = "monthly"
    payment_method: str = "direct_deposit"
    bank_account: Optional[dict] = None


class PayrollRunRequest(BaseModel):
    pay_period_start: date
    pay_period_end: date
    pay_date: date
    staff_ids: Optional[List[int]] = None


class DeductionRequest(BaseModel):
    staff_id: int
    deduction_type: str
    amount: float
    is_percentage: bool = False
    is_pretax: bool = True


@payroll_router.post("/employees/setup")
@limiter.limit("30/minute")
async def setup_employee_payroll(request: Request, body: EmployeePayrollSetup, db: Session = Depends(get_db)):
    """Setup payroll for an employee"""
    from app.services.payroll_service import PayrollService
    service = PayrollService(db)
    return service.setup_employee_payroll(
        staff_id=body.staff_id,
        pay_rate=body.pay_rate,
        pay_type=body.pay_type,
        pay_frequency=body.pay_frequency,
        payment_method=body.payment_method,
        bank_account=body.bank_account
    )


@payroll_router.post("/employees/{staff_id}/bank-account")
@limiter.limit("30/minute")
async def set_bank_account(
    request: Request,
    staff_id: int,
    bank_name: str,
    iban: str,
    bic: str,
    account_holder: str,
    db: Session = Depends(get_db)
):
    """Set employee bank account"""
    from app.services.payroll_service import PayrollService
    service = PayrollService(db)
    return service.set_bank_account(staff_id, bank_name, iban, bic, account_holder)


@payroll_router.post("/deductions")
@limiter.limit("30/minute")
async def add_deduction(request: Request, body: DeductionRequest, db: Session = Depends(get_db)):
    """Add a payroll deduction"""
    from app.services.payroll_service import PayrollService
    service = PayrollService(db)
    return service.add_deduction(
        staff_id=body.staff_id,
        deduction_type=body.deduction_type,
        amount=body.amount,
        is_percentage=body.is_percentage,
        is_pretax=body.is_pretax
    )


@payroll_router.post("/calculate/{staff_id}")
@limiter.limit("30/minute")
async def calculate_payroll(
    request: Request,
    staff_id: int,
    pay_period_start: date,
    pay_period_end: date,
    hours_worked: float = 0,
    overtime_hours: float = 0,
    tips: float = 0,
    db: Session = Depends(get_db)
):
    """Calculate payroll for an employee"""
    from app.services.payroll_service import PayrollService
    service = PayrollService(db)
    return service.calculate_payroll(
        staff_id=staff_id,
        pay_period_start=pay_period_start,
        pay_period_end=pay_period_end,
        hours_worked=hours_worked,
        overtime_hours=overtime_hours,
        tips=tips
    )


@payroll_router.post("/runs")
@limiter.limit("30/minute")
async def create_payroll_run(request: Request, body: PayrollRunRequest, db: Session = Depends(get_db)):
    """Create a payroll run"""
    from app.services.payroll_service import PayrollService
    service = PayrollService(db)
    return service.create_payroll_run(
        venue_id=1,
        pay_period_start=body.pay_period_start,
        pay_period_end=body.pay_period_end,
        pay_date=body.pay_date,
        staff_ids=body.staff_ids
    )


@payroll_router.post("/runs/{run_id}/approve")
@limiter.limit("30/minute")
async def approve_payroll_run(request: Request, run_id: str, approver_id: int, db: Session = Depends(get_db)):
    """Approve a payroll run"""
    from app.services.payroll_service import PayrollService
    service = PayrollService(db)
    return service.approve_payroll_run(run_id, approver_id)


@payroll_router.post("/runs/{run_id}/process")
@limiter.limit("30/minute")
async def process_payroll_run(request: Request, run_id: str, db: Session = Depends(get_db)):
    """Process a payroll run"""
    from app.services.payroll_service import PayrollService
    service = PayrollService(db)
    return service.process_payroll_run(run_id)


@payroll_router.get("/stubs/{staff_id}")
@limiter.limit("60/minute")
async def get_pay_stubs(request: Request, staff_id: int, year: Optional[int] = None, db: Session = Depends(get_db)):
    """Get employee pay stubs"""
    from app.services.payroll_service import PayrollService
    service = PayrollService(db)
    return service.get_employee_pay_stubs(staff_id, year)


@payroll_router.get("/tax-summary/{staff_id}/{year}")
@limiter.limit("60/minute")
async def get_tax_summary(request: Request, staff_id: int, year: int, db: Session = Depends(get_db)):
    """Get annual tax summary"""
    from app.services.payroll_service import PayrollService
    service = PayrollService(db)
    return service.generate_tax_summary(staff_id, year)


@payroll_router.get("/reports/labor-cost")
@limiter.limit("60/minute")
async def get_labor_cost_report(
    request: Request,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """Get labor cost report"""
    from app.services.payroll_service import PayrollService
    service = PayrollService(db)
    return service.get_labor_cost_report(venue_id=1, start_date=start_date, end_date=end_date)


# ==================== INTEGRATIONS ENDPOINTS ====================
integrations_router = APIRouter(prefix="/integrations", tags=["Third-Party Integrations"])


class ConnectIntegrationRequest(BaseModel):
    integration_id: str
    credentials: dict
    settings: Optional[dict] = None


@integrations_router.get("/")
@limiter.limit("60/minute")
async def list_integrations(
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    popular_only: bool = False,
    db: Session = Depends(get_db)
):
    """List available integrations"""
    from app.services.integrations_hub_service import IntegrationsHubService
    service = IntegrationsHubService(db)
    return service.list_integrations(category=category, search=search, popular_only=popular_only)


@integrations_router.get("/categories")
@limiter.limit("60/minute")
async def get_categories(request: Request, db: Session = Depends(get_db)):
    """Get integration categories"""
    from app.services.integrations_hub_service import IntegrationsHubService
    service = IntegrationsHubService(db)
    return service.get_categories()


@integrations_router.get("/{integration_id}")
@limiter.limit("60/minute")
async def get_integration(request: Request, integration_id: str, db: Session = Depends(get_db)):
    """Get integration details"""
    from app.services.integrations_hub_service import IntegrationsHubService
    service = IntegrationsHubService(db)
    return service.get_integration(integration_id)


@integrations_router.post("/connect")
@limiter.limit("30/minute")
async def connect_integration(request: Request, body: ConnectIntegrationRequest, db: Session = Depends(get_db)):
    """Connect an integration"""
    from app.services.integrations_hub_service import IntegrationsHubService
    service = IntegrationsHubService(db)
    return service.connect_integration(
        venue_id=1,
        integration_id=body.integration_id,
        credentials=body.credentials,
        settings=body.settings
    )


@integrations_router.post("/{integration_id}/disconnect")
@limiter.limit("30/minute")
async def disconnect_integration(request: Request, integration_id: str, db: Session = Depends(get_db)):
    """Disconnect an integration"""
    from app.services.integrations_hub_service import IntegrationsHubService
    service = IntegrationsHubService(db)
    return service.disconnect_integration(venue_id=1, integration_id=integration_id)


@integrations_router.get("/connected")
@limiter.limit("60/minute")
async def get_connected_integrations(request: Request, db: Session = Depends(get_db)):
    """Get all connected integrations"""
    from app.services.integrations_hub_service import IntegrationsHubService
    service = IntegrationsHubService(db)
    return service.get_connected_integrations(venue_id=1)


@integrations_router.post("/{integration_id}/sync")
@limiter.limit("30/minute")
async def sync_integration(request: Request, integration_id: str, sync_type: str = "full", db: Session = Depends(get_db)):
    """Trigger sync for an integration"""
    from app.services.integrations_hub_service import IntegrationsHubService
    service = IntegrationsHubService(db)
    return service.sync_integration(venue_id=1, integration_id=integration_id, sync_type=sync_type)


@integrations_router.get("/stats")
@limiter.limit("60/minute")
async def get_integration_stats(request: Request, db: Session = Depends(get_db)):
    """Get integration statistics"""
    from app.services.integrations_hub_service import IntegrationsHubService
    service = IntegrationsHubService(db)
    return service.get_integration_stats()


# ==================== BENCHMARKING ENDPOINTS ====================
benchmarking_router = APIRouter(prefix="/benchmarking", tags=["Benchmarking"])


class GoalRequest(BaseModel):
    metric: str
    target_value: float
    target_date: date
    baseline_value: float


@benchmarking_router.post("/compare/industry")
@limiter.limit("30/minute")
async def compare_to_industry(
    request: Request,
    industry_type: str,
    metrics: dict,
    db: Session = Depends(get_db)
):
    """Compare metrics to industry benchmarks"""
    from app.services.benchmarking_service import BenchmarkingService
    service = BenchmarkingService(db)
    return service.compare_to_industry(venue_id=1, industry_type=industry_type, metrics=metrics)


@benchmarking_router.post("/compare/region")
@limiter.limit("30/minute")
async def compare_to_region(
    request: Request,
    region: str,
    metrics: dict,
    db: Session = Depends(get_db)
):
    """Compare metrics to regional benchmarks"""
    from app.services.benchmarking_service import BenchmarkingService
    service = BenchmarkingService(db)
    return service.compare_to_region(venue_id=1, region=region, metrics=metrics)


@benchmarking_router.post("/peer-groups")
@limiter.limit("30/minute")
async def create_peer_group(
    request: Request,
    name: str,
    criteria: dict,
    db: Session = Depends(get_db)
):
    """Create a peer group"""
    from app.services.benchmarking_service import BenchmarkingService
    service = BenchmarkingService(db)
    return service.create_peer_group(name, criteria)


@benchmarking_router.get("/peer-groups/{group_id}/compare")
@limiter.limit("60/minute")
async def compare_to_peers(request: Request, group_id: str, period: str = "month", db: Session = Depends(get_db)):
    """Compare to peer group"""
    from app.services.benchmarking_service import BenchmarkingService
    service = BenchmarkingService(db)
    return service.compare_to_peers(venue_id=1, group_id=group_id, time_period=period)


@benchmarking_router.post("/insights")
@limiter.limit("30/minute")
async def get_insights(request: Request, metrics: dict, db: Session = Depends(get_db)):
    """Get AI-powered performance insights"""
    from app.services.benchmarking_service import BenchmarkingService
    service = BenchmarkingService(db)
    return service.get_performance_insights(venue_id=1, metrics=metrics)


@benchmarking_router.post("/goals")
@limiter.limit("30/minute")
async def set_goal(request: Request, body: GoalRequest, db: Session = Depends(get_db)):
    """Set a benchmark goal"""
    from app.services.benchmarking_service import BenchmarkingService
    service = BenchmarkingService(db)
    return service.set_benchmark_goal(
        venue_id=1,
        metric=body.metric,
        target_value=body.target_value,
        target_date=body.target_date,
        baseline_value=body.baseline_value
    )


@benchmarking_router.get("/goals")
@limiter.limit("60/minute")
async def get_goals(request: Request, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all goals"""
    from app.services.benchmarking_service import BenchmarkingService
    service = BenchmarkingService(db)
    return service.get_goals(venue_id=1, status=status)


@benchmarking_router.get("/trends")
@limiter.limit("60/minute")
async def get_trends(request: Request, metrics: str, period: str = "6_months", db: Session = Depends(get_db)):
    """Get performance trends"""
    from app.services.benchmarking_service import BenchmarkingService
    service = BenchmarkingService(db)
    return service.get_performance_trends(venue_id=1, metrics=metrics.split(","), period=period)


@benchmarking_router.get("/leaderboard/{metric}")
@limiter.limit("60/minute")
async def get_leaderboard(request: Request, metric: str, region: Optional[str] = None, db: Session = Depends(get_db)):
    """Get leaderboard for a metric"""
    from app.services.benchmarking_service import BenchmarkingService
    service = BenchmarkingService(db)
    return service.get_leaderboard(metric, region)


# ==================== HARDWARE ENDPOINTS ====================
hardware_router = APIRouter(prefix="/hardware", tags=["Hardware Management"])


class RegisterDeviceRequest(BaseModel):
    sku: str
    name: str
    location: str
    serial_number: str


class HardwareOrderRequest(BaseModel):
    items: List[dict]
    shipping_address: dict


@hardware_router.get("/catalog")
@limiter.limit("60/minute")
async def get_catalog(request: Request, device_type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get hardware catalog"""
    from app.services.hardware_management_service import HardwareManagementService
    service = HardwareManagementService(db)
    return service.get_hardware_catalog(device_type)


@hardware_router.post("/devices")
@limiter.limit("30/minute")
async def register_device(request: Request, body: RegisterDeviceRequest, db: Session = Depends(get_db)):
    """Register a new device"""
    from app.services.hardware_management_service import HardwareManagementService
    service = HardwareManagementService(db)
    return service.register_device(
        venue_id=1,
        sku=body.sku,
        name=body.name,
        location=body.location,
        serial_number=body.serial_number
    )


@hardware_router.get("/devices")
@limiter.limit("60/minute")
async def list_devices(
    request: Request,
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all devices"""
    from app.services.hardware_management_service import HardwareManagementService
    service = HardwareManagementService(db)
    return service.list_devices(venue_id=1, device_type=device_type, status=status)


@hardware_router.get("/devices/{device_id}")
@limiter.limit("60/minute")
async def get_device(request: Request, device_id: str, db: Session = Depends(get_db)):
    """Get device details"""
    from app.services.hardware_management_service import HardwareManagementService
    service = HardwareManagementService(db)
    return service.get_device(device_id)


@hardware_router.post("/devices/{device_id}/diagnostics")
@limiter.limit("30/minute")
async def run_diagnostics(request: Request, device_id: str, db: Session = Depends(get_db)):
    """Run device diagnostics"""
    from app.services.hardware_management_service import HardwareManagementService
    service = HardwareManagementService(db)
    return service.run_diagnostics(device_id)


@hardware_router.get("/devices/{device_id}/firmware")
@limiter.limit("60/minute")
async def check_firmware(request: Request, device_id: str, db: Session = Depends(get_db)):
    """Check for firmware updates"""
    from app.services.hardware_management_service import HardwareManagementService
    service = HardwareManagementService(db)
    return service.check_firmware_updates(device_id)


@hardware_router.get("/devices/{device_id}/warranty")
@limiter.limit("60/minute")
async def check_warranty(request: Request, device_id: str, db: Session = Depends(get_db)):
    """Check device warranty"""
    from app.services.hardware_management_service import HardwareManagementService
    service = HardwareManagementService(db)
    return service.check_warranty(device_id)


@hardware_router.post("/orders")
@limiter.limit("30/minute")
async def create_order(request: Request, body: HardwareOrderRequest, db: Session = Depends(get_db)):
    """Create a hardware order"""
    from app.services.hardware_management_service import HardwareManagementService
    service = HardwareManagementService(db)
    return service.create_hardware_order(
        venue_id=1,
        items=body.items,
        shipping_address=body.shipping_address
    )


@hardware_router.get("/recommendations")
@limiter.limit("60/minute")
async def get_recommendations(
    request: Request,
    venue_type: str,
    covers_per_day: int,
    db: Session = Depends(get_db)
):
    """Get hardware recommendations"""
    from app.services.hardware_management_service import HardwareManagementService
    service = HardwareManagementService(db)
    return service.get_hardware_recommendations(
        venue_id=1,
        venue_type=venue_type,
        covers_per_day=covers_per_day
    )


# ==================== SUPPORT ENDPOINTS ====================
support_router = APIRouter(prefix="/support", tags=["24/7 Support"])


class CreateTicketRequest(BaseModel):
    subject: str
    description: str
    category: str
    priority: str = "medium"


class ChatMessageRequest(BaseModel):
    content: str


@support_router.post("/tickets")
@limiter.limit("30/minute")
async def create_ticket(request: Request, body: CreateTicketRequest, db: Session = Depends(get_db)):
    """Create a support ticket"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.create_ticket(
        venue_id=1,
        user_id=1,
        subject=body.subject,
        description=body.description,
        category=body.category,
        priority=body.priority
    )


@support_router.get("/tickets")
@limiter.limit("60/minute")
async def list_tickets(
    request: Request,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List support tickets"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.list_tickets(venue_id=1, status=status, priority=priority)


@support_router.get("/tickets/{ticket_id}")
@limiter.limit("60/minute")
async def get_ticket(request: Request, ticket_id: str, db: Session = Depends(get_db)):
    """Get ticket details"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.get_ticket(ticket_id)


@support_router.post("/tickets/{ticket_id}/messages")
@limiter.limit("30/minute")
async def add_message(request: Request, ticket_id: str, body: ChatMessageRequest, db: Session = Depends(get_db)):
    """Add message to ticket"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.add_message(ticket_id, "customer", 1, body.content)


@support_router.post("/tickets/{ticket_id}/escalate")
@limiter.limit("30/minute")
async def escalate_ticket(request: Request, ticket_id: str, reason: str, db: Session = Depends(get_db)):
    """Escalate a ticket"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.escalate_ticket(ticket_id, reason)


@support_router.get("/knowledge-base")
@limiter.limit("60/minute")
async def search_kb(request: Request, query: str, category: Optional[str] = None, db: Session = Depends(get_db)):
    """Search knowledge base"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.search_knowledge_base(query, category)


@support_router.get("/knowledge-base/{article_id}")
@limiter.limit("60/minute")
async def get_article(request: Request, article_id: str, db: Session = Depends(get_db)):
    """Get KB article"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.get_article(article_id)


@support_router.post("/chat/start")
@limiter.limit("30/minute")
async def start_chat(request: Request, initial_message: str, db: Session = Depends(get_db)):
    """Start live chat session"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.start_chat_session(venue_id=1, user_id=1, initial_message=initial_message)


@support_router.post("/chat/{session_id}/message")
@limiter.limit("30/minute")
async def send_chat_message(request: Request, session_id: str, body: ChatMessageRequest, db: Session = Depends(get_db)):
    """Send chat message"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.send_chat_message(session_id, "customer", body.content)


@support_router.post("/callback")
@limiter.limit("30/minute")
async def schedule_callback(
    request: Request,
    phone_number: str,
    preferred_time: datetime,
    topic: str,
    db: Session = Depends(get_db)
):
    """Schedule phone callback"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.schedule_callback(
        venue_id=1,
        user_id=1,
        phone_number=phone_number,
        preferred_time=preferred_time,
        topic=topic
    )


@support_router.get("/hours")
@limiter.limit("60/minute")
async def get_support_hours(request: Request, db: Session = Depends(get_db)):
    """Get support availability"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.get_support_hours()


@support_router.post("/tickets/{ticket_id}/satisfaction")
@limiter.limit("30/minute")
async def submit_satisfaction(request: Request, ticket_id: str, rating: int, feedback: Optional[str] = None, db: Session = Depends(get_db)):
    """Submit satisfaction rating"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.submit_satisfaction(ticket_id, rating, feedback)


@support_router.get("/metrics")
@limiter.limit("60/minute")
async def get_support_metrics(request: Request, period_days: int = 30, db: Session = Depends(get_db)):
    """Get support metrics"""
    from app.services.support_service import SupportService
    service = SupportService(db)
    return service.get_support_metrics(venue_id=1, period_days=period_days)


# ==================== REGISTER ALL V3.1 ROUTERS ====================
v31_router.include_router(locations_router)
v31_router.include_router(payroll_router)
v31_router.include_router(integrations_router)
v31_router.include_router(benchmarking_router)
v31_router.include_router(hardware_router)
v31_router.include_router(support_router)

# Alias for dynamic module loader
router = v31_router
