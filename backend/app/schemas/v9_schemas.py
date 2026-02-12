"""
V9 Advanced Features Schemas
Pydantic models for API request/response validation
BJ's Bar V9 - Enterprise POS System
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum


# ============== ENUMS ==============

class OverrideType(str, Enum):
    DISCOUNT = "discount"
    VOID = "void"
    REFUND = "refund"
    PRICE_CHANGE = "price_change"
    COMP = "comp"
    MANAGER_COMP = "manager_comp"


class TerminalStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class SafeModeType(str, Enum):
    """Safe mode types matching model definition"""
    NORMAL = "normal"
    SAFE = "safe"
    EMERGENCY = "emergency"
    OFFLINE = "offline"
    LOCKED = "locked"


# Alias for backwards compatibility
SafeModeLevel = SafeModeType


class VarianceSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IoTDeviceType(str, Enum):
    TEMPERATURE_SENSOR = "temperature_sensor"
    POUR_METER = "pour_meter"
    SCALE = "scale"
    MOTION_SENSOR = "motion_sensor"
    DOOR_SENSOR = "door_sensor"
    HUMIDITY_SENSOR = "humidity_sensor"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AbuseType(str, Enum):
    EXCESSIVE_REFUNDS = "excessive_refunds"
    EXCESSIVE_DISCOUNTS = "excessive_discounts"
    EXCESSIVE_VOIDS = "excessive_voids"
    SUSPICIOUS_TIMING = "suspicious_timing"
    UNUSUAL_PATTERN = "unusual_pattern"


class CustomerSegment(str, Enum):
    CHAMPION = "champion"
    LOYAL = "loyal"
    POTENTIAL_LOYALIST = "potential_loyalist"
    RECENT_CUSTOMER = "recent_customer"
    PROMISING = "promising"
    NEEDS_ATTENTION = "needs_attention"
    AT_RISK = "at_risk"
    CANT_LOSE = "cant_lose"
    HIBERNATING = "hibernating"
    LOST = "lost"


class VIPTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class AutomationTriggerType(str, Enum):
    THRESHOLD = "threshold"
    SCHEDULE = "schedule"
    EVENT = "event"
    PREDICTION = "prediction"


class AutomationActionType(str, Enum):
    ALERT = "alert"
    REORDER = "reorder"
    PRICE_CHANGE = "price_change"
    NOTIFICATION = "notification"
    WORKFLOW = "workflow"


class IncidentType(str, Enum):
    """Incident types matching model definition"""
    INJURY_CUSTOMER = "injury_customer"
    INJURY_STAFF = "injury_staff"
    PROPERTY_DAMAGE = "property_damage"
    FOOD_SAFETY = "food_safety"
    THEFT = "theft"
    HARASSMENT = "harassment"
    SLIP_FALL = "slip_fall"
    FIRE_HAZARD = "fire_hazard"
    OTHER = "other"


class TrainingType(str, Enum):
    ONBOARDING = "onboarding"
    SAFETY = "safety"
    SERVICE = "service"
    PRODUCT_KNOWLEDGE = "product_knowledge"
    COMPLIANCE = "compliance"
    LEADERSHIP = "leadership"


class CrisisType(str, Enum):
    PANDEMIC = "pandemic"
    ECONOMIC = "economic"
    SUPPLY_SHORTAGE = "supply_shortage"
    STAFFING_CRISIS = "staffing_crisis"
    NATURAL_DISASTER = "natural_disaster"


class QRCodeType(str, Enum):
    MENU = "menu"
    ORDER = "order"
    PAYMENT = "payment"
    FEEDBACK = "feedback"


class CostingMethod(str, Enum):
    FIFO = "fifo"
    LIFO = "lifo"
    WEIGHTED_AVERAGE = "weighted_average"


# ============== PERMISSION OVERRIDE SCHEMAS ==============

class PermissionOverrideCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "staff_id": 1,
            "override_type": "discount",
            "max_value": 100.00,
            "max_percentage": 25.0,
            "valid_from": "2024-01-01T00:00:00",
            "valid_until": "2024-01-31T23:59:59",
            "reason": "Holiday promotion authority",
            "granted_by_id": 2
        }
    })

    staff_id: int
    override_type: OverrideType
    max_value: Optional[Decimal] = None
    max_percentage: Optional[Decimal] = None
    valid_from: datetime
    valid_until: datetime
    reason: str
    granted_by_id: int


class PermissionOverrideResponse(BaseModel):
    id: int
    staff_id: int
    override_type: str
    max_value: Optional[Decimal]
    max_percentage: Optional[Decimal]
    valid_from: datetime
    valid_until: datetime
    reason: str
    granted_by_id: int
    is_active: bool
    usage_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UseOverrideRequest(BaseModel):
    override_id: int
    amount: Decimal
    transaction_id: int
    notes: Optional[str] = None


# ============== TERMINAL MANAGEMENT SCHEMAS ==============

class TerminalHealthCreate(BaseModel):
    terminal_id: str
    terminal_name: str
    ip_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TerminalHealthUpdate(BaseModel):
    status: Optional[TerminalStatus] = None
    battery_level: Optional[int] = None
    network_strength: Optional[int] = None
    printer_status: Optional[str] = None
    cash_drawer_status: Optional[str] = None
    software_version: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TerminalHealthResponse(BaseModel):
    id: int
    terminal_id: str
    terminal_name: str
    status: str
    ip_address: str
    last_heartbeat: Optional[datetime]
    battery_level: Optional[int]
    network_strength: Optional[int]
    printer_status: Optional[str]
    cash_drawer_status: Optional[str]
    software_version: Optional[str]
    last_sync_at: Optional[datetime]
    is_geo_fenced: bool
    latitude: Optional[float]
    longitude: Optional[float]
    is_locked: bool
    
    model_config = ConfigDict(from_attributes=True)


class GeoFenceConfig(BaseModel):
    terminal_id: str
    center_latitude: float
    center_longitude: float
    radius_meters: float = 100.0


# ============== EMERGENCY/SAFE MODE SCHEMAS ==============

class SafeModeActivate(BaseModel):
    level: SafeModeLevel
    reason: str
    activated_by_id: int
    auto_deactivate_after_hours: Optional[int] = None
    allowed_operations: List[str] = []


class SafeModeResponse(BaseModel):
    id: int
    level: str
    is_active: bool
    activated_at: datetime
    activated_by_id: int
    reason: str
    allowed_operations: List[str]
    deactivated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


# ============== CASH VARIANCE SCHEMAS ==============

class CashCountSubmit(BaseModel):
    shift_id: int
    terminal_id: str
    expected_amount: Decimal
    actual_amount: Decimal
    counted_by_id: int
    notes: Optional[str] = None


class CashVarianceResponse(BaseModel):
    id: int
    shift_id: int
    terminal_id: str
    expected_amount: Decimal
    actual_amount: Decimal
    variance_amount: Decimal
    variance_percentage: Decimal
    severity: str
    counted_by_id: int
    reviewed_by_id: Optional[int]
    investigation_notes: Optional[str]
    is_resolved: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============== KITCHEN FORECASTING SCHEMAS ==============

class ForecastRequest(BaseModel):
    menu_item_id: int
    forecast_date: date
    include_weather: bool = True
    include_events: bool = True


class ForecastResponse(BaseModel):
    menu_item_id: int
    forecast_date: date
    predicted_quantity: int
    confidence_score: float
    factors: Dict[str, Any]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class IngredientRequirementResponse(BaseModel):
    ingredient_id: int
    ingredient_name: str
    required_quantity: float
    unit: str
    current_stock: float
    shortage: float
    suggested_order: float


# ============== STATION LOAD BALANCING SCHEMAS ==============

class StationCreate(BaseModel):
    station_name: str
    station_type: str
    max_concurrent_orders: int = 5
    average_prep_time_minutes: int = 10


class StationLoadResponse(BaseModel):
    station_id: int
    station_name: str
    current_orders: int
    max_capacity: int
    load_percentage: float
    average_wait_time: int
    suggested_action: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class RoutingSuggestion(BaseModel):
    order_item_id: int
    current_station_id: int
    suggested_station_id: int
    reason: str
    estimated_time_saved: int


# ============== AUTO COURSE FIRE SCHEMAS ==============

class CourseFireRuleCreate(BaseModel):
    menu_item_id: int
    course_number: int
    fire_delay_minutes: int
    fire_trigger: str  # 'time', 'previous_course_served', 'manual'
    conditions: Optional[Dict[str, Any]] = None


class CourseFireRuleResponse(BaseModel):
    id: int
    menu_item_id: int
    course_number: int
    fire_delay_minutes: int
    fire_trigger: str
    conditions: Optional[Dict[str, Any]]
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


# ============== SUPPLY CHAIN SCHEMAS ==============

class AutoPOConfig(BaseModel):
    ingredient_id: int
    reorder_point: float
    reorder_quantity: float
    preferred_supplier_id: int
    auto_approve_threshold: Optional[Decimal] = None


class AutoPOResponse(BaseModel):
    id: int
    ingredient_id: int
    supplier_id: int
    quantity: float
    unit_price: Decimal
    total_amount: Decimal
    status: str
    auto_generated: bool
    trigger_reason: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SupplierLeadTimeUpdate(BaseModel):
    supplier_id: int
    ingredient_id: int
    lead_time_days: int
    reliability_score: Optional[float] = None


class InventoryCostingConfig(BaseModel):
    ingredient_id: int
    costing_method: CostingMethod
    

# ============== FINANCIAL CONTROLS SCHEMAS ==============

class PrimeCostRecord(BaseModel):
    date: date
    food_cost: Decimal
    beverage_cost: Decimal
    labor_cost: Decimal
    revenue: Decimal


class PrimeCostDashboard(BaseModel):
    current_period: Dict[str, Any]
    previous_period: Dict[str, Any]
    trend: str
    alerts: List[str]
    breakdown: Dict[str, Decimal]


class AbuseConfigUpdate(BaseModel):
    abuse_type: AbuseType
    threshold_count: int
    threshold_amount: Decimal
    time_window_hours: int
    suspicious_hours: Optional[List[int]] = None
    is_active: bool = True


class AbuseAlertResponse(BaseModel):
    id: int
    staff_id: int
    abuse_type: str
    trigger_value: Decimal
    threshold_value: Decimal
    severity: str
    is_investigated: bool
    investigated_by_id: Optional[int]
    investigation_notes: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class InvestigationSubmit(BaseModel):
    alert_id: int
    investigator_id: int
    notes: str
    action_taken: Optional[str] = None


# ============== CRM SCHEMAS ==============

class GuestPreferencesUpdate(BaseModel):
    customer_id: int
    dietary_restrictions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    favorite_items: Optional[List[int]] = None
    preferred_seating: Optional[str] = None
    preferred_server_id: Optional[int] = None
    communication_preferences: Optional[Dict[str, bool]] = None
    special_occasions: Optional[Dict[str, date]] = None
    notes: Optional[str] = None


class GuestPreferencesResponse(BaseModel):
    id: int
    customer_id: int
    dietary_restrictions: List[str]
    allergies: List[str]
    favorite_items: List[int]
    preferred_seating: Optional[str]
    preferred_server_id: Optional[int]
    communication_preferences: Dict[str, bool]
    special_occasions: Dict[str, Any]
    notes: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class ServiceAlert(BaseModel):
    alert_type: str
    severity: str
    message: str
    customer_id: int
    details: Dict[str, Any]


class CLVResponse(BaseModel):
    customer_id: int
    total_revenue: Decimal
    visit_count: int
    average_order_value: Decimal
    predicted_annual_value: Decimal
    customer_lifetime_months: int
    clv_score: Decimal
    segment: str
    last_calculated: datetime
    
    model_config = ConfigDict(from_attributes=True)


class VIPStatusUpdate(BaseModel):
    customer_id: int
    tier: VIPTier
    reason: Optional[str] = None
    valid_until: Optional[date] = None


class CustomerSegmentResponse(BaseModel):
    segment: str
    customer_count: int
    total_revenue: Decimal
    average_clv: Decimal
    churn_risk: float


class PersonalizedRecommendation(BaseModel):
    menu_item_id: int
    menu_item_name: str
    reason: str
    confidence: float
    matches_preferences: List[str]


# ============== IOT SCHEMAS ==============

class IoTDeviceRegister(BaseModel):
    device_id: str
    device_name: str
    device_type: IoTDeviceType
    location: str
    calibration_date: Optional[date] = None
    alert_thresholds: Optional[Dict[str, float]] = None


class IoTDeviceResponse(BaseModel):
    id: int
    device_id: str
    device_name: str
    device_type: str
    status: str
    location: str
    last_reading: Optional[datetime]
    last_reading_value: Optional[float]
    battery_level: Optional[int]
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class TemperatureReading(BaseModel):
    device_id: str
    temperature_celsius: float
    humidity_percent: Optional[float] = None


class TemperatureAlertResponse(BaseModel):
    id: int
    device_id: str
    location: str
    temperature: float
    threshold: float
    severity: str
    acknowledged: bool
    acknowledged_by_id: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class HACCPReport(BaseModel):
    report_date: date
    total_readings: int
    compliant_readings: int
    compliance_rate: float
    violations: List[Dict[str, Any]]
    corrective_actions: List[Dict[str, Any]]


class PourReading(BaseModel):
    device_id: str
    product_id: int
    staff_id: int
    expected_ml: float
    actual_ml: float
    order_item_id: Optional[int] = None


class PourAnalytics(BaseModel):
    staff_id: int
    staff_name: str
    total_pours: int
    accuracy_rate: float
    overpour_count: int
    underpour_count: int
    variance_ml: float
    cost_impact: Decimal


# ============== COMPLIANCE SCHEMAS ==============

class AuditLogCreate(BaseModel):
    action: str
    entity_type: str
    entity_id: int
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    staff_id: int
    ip_address: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: int
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    staff_id: int
    timestamp: datetime
    checksum: str
    previous_checksum: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class AuditChainVerification(BaseModel):
    is_valid: bool
    verified_count: int
    first_invalid_id: Optional[int]
    error_message: Optional[str]


class FiscalArchiveCreate(BaseModel):
    receipt_number: str
    receipt_content: str
    fiscal_signature: str
    order_id: int


class NRAExportRequest(BaseModel):
    start_date: date
    end_date: date
    export_format: str = "xml"  # xml or json


class NRAExportResponse(BaseModel):
    export_id: int
    filename: str
    record_count: int
    total_amount: Decimal
    status: str
    download_url: Optional[str]
    created_at: datetime


class AgeVerificationLog(BaseModel):
    customer_id: Optional[int] = None
    order_id: int
    verified_by_id: int
    document_type: str  # 'passport', 'id_card', 'drivers_license'
    document_expiry: date
    customer_dob: date


# ============== AI AUTOMATION SCHEMAS ==============

class AIModelRegister(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    model_type: str
    version: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class AIModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    model_name: str
    model_type: str
    version: str
    is_active: bool
    accuracy_score: Optional[float]
    last_trained_at: Optional[datetime]
    prediction_count: int
    created_at: datetime


class PredictionLog(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: int
    input_data: Dict[str, Any]
    prediction_value: Any
    confidence_score: float
    context: Optional[Dict[str, Any]] = None


class PredictionAccuracyReport(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: int
    model_name: str
    total_predictions: int
    accurate_predictions: int
    accuracy_rate: float
    mean_absolute_error: Optional[float]
    period_start: datetime
    period_end: datetime


class AutomationRuleCreate(BaseModel):
    rule_name: str
    trigger_type: AutomationTriggerType
    trigger_config: Dict[str, Any]
    action_type: AutomationActionType
    action_config: Dict[str, Any]
    is_active: bool = True
    priority: int = 5


class AutomationRuleResponse(BaseModel):
    id: int
    rule_name: str
    trigger_type: str
    trigger_config: Dict[str, Any]
    action_type: str
    action_config: Dict[str, Any]
    is_active: bool
    priority: int
    execution_count: int
    last_executed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class MenuOptimizationSuggestion(BaseModel):
    menu_item_id: int
    menu_item_name: str
    suggestion_type: str  # 'price_increase', 'price_decrease', 'promotion', 'discontinue'
    current_value: Any
    suggested_value: Any
    expected_impact: Dict[str, Any]
    confidence: float
    reasoning: str


class StaffingRecommendation(BaseModel):
    date: date
    time_slot: str
    current_staff: int
    recommended_staff: int
    expected_covers: int
    confidence: float
    factors: List[str]


# ============== LEGAL/TRAINING/CRISIS SCHEMAS ==============

class IncidentReportCreate(BaseModel):
    incident_type: IncidentType
    description: str
    location: str
    occurred_at: datetime
    reported_by_id: int
    involved_parties: Optional[List[Dict[str, Any]]] = None
    witnesses: Optional[List[Dict[str, Any]]] = None
    severity: str = "medium"


class IncidentReportResponse(BaseModel):
    id: int
    incident_type: str
    description: str
    location: str
    occurred_at: datetime
    reported_at: datetime
    reported_by_id: int
    status: str
    severity: str
    involved_parties: Optional[List[Dict[str, Any]]]
    witnesses: Optional[List[Dict[str, Any]]]
    investigation_notes: Optional[str]
    resolution: Optional[str]
    insurance_claim_id: Optional[int]
    
    model_config = ConfigDict(from_attributes=True)


class EvidenceAdd(BaseModel):
    incident_id: int
    evidence_type: str  # 'photo', 'video', 'document', 'statement'
    file_path: Optional[str] = None
    description: str
    collected_by_id: int


class TrainingModuleCreate(BaseModel):
    module_name: str
    module_type: TrainingType
    description: str
    content_url: Optional[str] = None
    duration_minutes: int
    passing_score: int = 80
    is_mandatory: bool = False
    expiry_days: Optional[int] = None
    prerequisites: Optional[List[int]] = None


class TrainingModuleResponse(BaseModel):
    id: int
    module_name: str
    module_type: str
    description: str
    duration_minutes: int
    passing_score: int
    is_mandatory: bool
    is_active: bool
    completion_count: int
    average_score: Optional[float]
    
    model_config = ConfigDict(from_attributes=True)


class TrainingCompletion(BaseModel):
    module_id: int
    staff_id: int
    score: int
    time_spent_minutes: int


class StaffTrainingStatus(BaseModel):
    staff_id: int
    staff_name: str
    completed_modules: int
    total_required: int
    compliance_rate: float
    expiring_certifications: List[Dict[str, Any]]
    overdue_trainings: List[Dict[str, Any]]


class CrisisModeCreate(BaseModel):
    crisis_type: CrisisType
    crisis_name: str
    simplified_menu_ids: Optional[List[int]] = None
    margin_protection_percentage: Decimal = Decimal("5.0")
    auto_activate_conditions: Optional[Dict[str, Any]] = None


class CrisisModeResponse(BaseModel):
    id: int
    crisis_type: str
    crisis_name: str
    is_active: bool
    activated_at: Optional[datetime]
    simplified_menu_ids: Optional[List[int]]
    margin_protection_percentage: Decimal
    
    model_config = ConfigDict(from_attributes=True)


# ============== PLATFORM/QR SCHEMAS ==============

class FeatureFlagCreate(BaseModel):
    flag_name: str
    description: Optional[str] = None
    is_enabled: bool = False
    rollout_percentage: int = 0
    conditions: Optional[Dict[str, Any]] = None


class FeatureFlagResponse(BaseModel):
    id: int
    flag_name: str
    description: Optional[str]
    is_enabled: bool
    rollout_percentage: int
    conditions: Optional[Dict[str, Any]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class WhiteLabelConfig(BaseModel):
    tenant_id: str
    brand_name: str
    primary_color: str
    secondary_color: str
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    custom_css: Optional[str] = None
    custom_domain: Optional[str] = None
    email_from_name: Optional[str] = None
    support_email: Optional[str] = None


class WhiteLabelResponse(BaseModel):
    id: int
    tenant_id: str
    brand_name: str
    primary_color: str
    secondary_color: str
    logo_url: Optional[str]
    custom_domain: Optional[str]
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class QRPaymentSessionCreate(BaseModel):
    table_id: int
    order_id: int


class QRPaymentSessionResponse(BaseModel):
    id: int
    session_code: str
    table_id: int
    order_id: int
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    status: str
    expires_at: datetime
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SplitPaymentConfig(BaseModel):
    session_id: int
    split_type: str  # 'equal', 'by_item', 'custom'
    split_count: Optional[int] = None
    item_assignments: Optional[Dict[int, int]] = None  # item_id: payer_number
    custom_amounts: Optional[Dict[int, Decimal]] = None  # payer_number: amount


class PaymentRecord(BaseModel):
    session_id: int
    payer_number: int
    amount: Decimal
    payment_method: str
    tip_amount: Optional[Decimal] = None


class ReorderSessionCreate(BaseModel):
    table_id: int
    original_order_id: int


class ReorderSessionResponse(BaseModel):
    id: int
    session_code: str
    table_id: int
    original_order_id: int
    available_items: List[Dict[str, Any]]
    status: str
    expires_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ReorderConfirm(BaseModel):
    session_id: int
    item_ids: List[int]
    quantities: Optional[Dict[int, int]] = None


class TableQRGenerate(BaseModel):
    table_id: int
    qr_type: QRCodeType


class TableQRResponse(BaseModel):
    table_id: int
    qr_type: str
    qr_code_data: str
    qr_code_url: str
    expires_at: Optional[datetime]


class KioskMenuResponse(BaseModel):
    categories: List[Dict[str, Any]]
    featured_items: List[Dict[str, Any]]
    popular_items: List[Dict[str, Any]]
    upsell_suggestions: List[Dict[str, Any]]


class KioskOrderSubmit(BaseModel):
    items: List[Dict[str, Any]]
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    special_instructions: Optional[str] = None
    payment_method: str


class KioskOrderResponse(BaseModel):
    order_id: int
    order_number: str
    estimated_ready_time: datetime
    total_amount: Decimal
    payment_status: str
    qr_code_url: str


# ============== KITCHEN PERFORMANCE SCHEMAS ==============

class KitchenPerformanceMetrics(BaseModel):
    period_start: datetime
    period_end: datetime
    total_tickets: int
    average_ticket_time: float
    tickets_over_sla: int
    sla_compliance_rate: float
    station_metrics: List[Dict[str, Any]]
    peak_hour_performance: Dict[str, Any]
    bottleneck_stations: List[str]


# ============== SESSION TIMEOUT SCHEMAS ==============

class SessionTimeoutConfig(BaseModel):
    role: str
    timeout_minutes: int
    warning_minutes: int = 5
    extend_allowed: bool = True
    max_extensions: int = 3


class SessionTimeoutResponse(BaseModel):
    id: int
    role: str
    timeout_minutes: int
    warning_minutes: int
    extend_allowed: bool
    max_extensions: int
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


# ============== CROSS-STORE BALANCING SCHEMAS ==============

class CrossStoreBalancingSuggestion(BaseModel):
    ingredient_id: int
    ingredient_name: str
    source_location_id: int
    source_location_name: str
    target_location_id: int
    target_location_name: str
    suggested_quantity: float
    unit: str
    reason: str
    urgency: str
    estimated_savings: Decimal


# ============== RESPONSE WRAPPERS ==============

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
