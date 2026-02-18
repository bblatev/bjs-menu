"""Extended schemas from V3 that were missing in V7"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class StaffRoleEnum(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    KITCHEN = "kitchen"
    BAR = "bar"
    WAITER = "waiter"


class OrderStatusEnum(str, Enum):
    NEW = "new"
    DRAFT = "draft"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY = "ready"
    SERVED = "served"
    CANCELLED = "cancelled"


class OrderTypeEnum(str, Enum):
    DINE_IN = "dine-in"
    TAKEAWAY = "takeaway"


class WaiterCallReasonEnum(str, Enum):
    BILL = "bill"
    HELP = "help"
    COMPLAINT = "complaint"
    WATER = "water"
    OTHER = "other"


class WaiterCallStatusEnum(str, Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SPAM = "spam"


class AnalyticsEventTypeEnum(str, Enum):
    MENU_VIEW = "menu_view"
    ITEM_VIEW = "item_view"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    CHECKOUT = "checkout"
    WAITER_CALL = "waiter_call"
    ITEM_RATING = "item_rating"
    SERVICE_RATING = "service_rating"


class AutoDiscountType(str, Enum):
    HAPPY_HOUR = "happy_hour"
    APRES_SKI = "apres_ski"
    EARLY_BIRD = "early_bird"
    LATE_NIGHT = "late_night"
    WEATHER_BASED = "weather_based"
    PERCENTAGE = "percentage"


class GiftCardStatus(str, Enum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DriveThruLane(str, Enum):
    LANE_1 = "lane_1"
    LANE_2 = "lane_2"
    EXPRESS = "express"


class DriveThruOrderStatus(str, Enum):
    ORDERED = "ordered"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    AT_WINDOW = "at_window"
    COMPLETED = "completed"


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class PaymentGateway(str, Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    ADYEN = "adyen"
    EPAY = "epay"
    BORICA = "borica"


class PayrollPeriod(str, Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class SplitBillType(str, Enum):
    EQUAL = "equal"
    BY_ITEM = "by_item"
    CUSTOM = "custom"


# ============================================================================
# BASE SCHEMAS
# ============================================================================

class MultilingualText(BaseModel):
    bg: str
    en: Optional[str] = None
    de: Optional[str] = None
    ru: Optional[str] = None


# ============================================================================
# STAFF SCHEMAS (EXTENDED)
# ============================================================================

class StaffUserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: StaffRoleEnum


class StaffUserCreate(StaffUserBase):
    password: str
    venue_id: int


class StaffUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[StaffRoleEnum] = None
    active: Optional[bool] = None
    password: Optional[str] = None


# ============================================================================
# MENU MODIFIER SCHEMAS
# ============================================================================

class ModifierOptionBase(BaseModel):
    name: Dict[str, str]
    price_delta: float = 0.0
    sort_order: int = 0


class ModifierOptionCreate(ModifierOptionBase):
    group_id: int


class ModifierGroupBase(BaseModel):
    name: Dict[str, str]
    required: bool = False
    min_selections: int = 0
    max_selections: int = 1
    sort_order: int = 0


class ModifierGroupCreate(ModifierGroupBase):
    item_id: int


class MenuCategoryBase(BaseModel):
    name: Dict[str, str]
    description: Optional[Dict[str, str]] = None
    sort_order: int = 0


class MenuCategoryCreate(MenuCategoryBase):
    version_id: int


# ============================================================================
# ORDER SCHEMAS (EXTENDED)
# ============================================================================

class OrderItemModifierCreate(BaseModel):
    modifier_option_id: int


class OrderStatusUpdate(BaseModel):
    status: OrderStatusEnum


# ============================================================================
# AUTO DISCOUNT SCHEMAS
# ============================================================================

class AutoDiscountCreate(BaseModel):
    name: str
    discount_type: AutoDiscountType
    percentage: float
    start_time: str  # HH:MM format
    end_time: str
    days_of_week: List[int] = [0, 1, 2, 3, 4, 5, 6]
    applicable_categories: Optional[List[int]] = None
    weather_condition: Optional[str] = None


class AutoDiscountResponse(BaseModel):
    id: int
    name: str
    discount_type: AutoDiscountType
    percentage: float
    start_time: str
    end_time: str
    days_of_week: List[int]
    applicable_categories: Optional[List[int]]
    weather_condition: Optional[str]
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# GIFT CARD SCHEMAS
# ============================================================================

class GiftCardCreate(BaseModel):
    initial_balance: float
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    message: Optional[str] = None
    expires_at: Optional[datetime] = None


class GiftCardResponse(BaseModel):
    id: int
    code: str
    initial_balance: float
    current_balance: float
    status: GiftCardStatus
    recipient_email: Optional[str]
    recipient_name: Optional[str]
    message: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class GiftCardRedeemRequest(BaseModel):
    code: str
    amount: float
    order_id: int


class GiftCardTransaction(BaseModel):
    id: int
    gift_card_id: int
    transaction_type: str  # load, redeem
    amount: float
    order_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# BATCH & EXPIRATION TRACKING SCHEMAS
# ============================================================================

class BatchCreate(BaseModel):
    stock_item_id: int
    batch_number: str
    quantity: float
    manufacture_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    supplier_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    cost_per_unit: Optional[float] = None


class BatchResponse(BaseModel):
    id: int
    stock_item_id: int
    stock_item_name: str
    batch_number: str
    quantity: float
    initial_quantity: float
    manufacture_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    is_expired: bool = False
    is_expiring_soon: bool = False
    supplier_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# FLOOR PLAN SCHEMAS
# ============================================================================

class FloorPlanTablePosition(BaseModel):
    table_id: int
    x: int
    y: int
    width: int = 80
    height: int = 80
    rotation: int = 0
    shape: str = "rectangle"


class FloorPlanAreaCreate(BaseModel):
    name: str
    color: str = "#e5e7eb"
    x: int = 0
    y: int = 0
    width: int = 200
    height: int = 200


class FloorPlanCreate(BaseModel):
    name: str = "Floor Plan"
    width: int = 1200
    height: int = 800
    background_image: Optional[str] = None
    tables: List[FloorPlanTablePosition] = []
    areas: List[FloorPlanAreaCreate] = []


class FloorPlanResponse(BaseModel):
    id: int
    venue_id: int
    name: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    background_image: Optional[str] = None
    is_active: Optional[bool] = None
    areas: List[Dict[str, Any]] = []
    tables: List[Dict[str, Any]] = []
    table_positions: Optional[List[FloorPlanTablePosition]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# KIOSK SCHEMAS
# ============================================================================

class KioskModeConfig(BaseModel):
    venue_id: int
    idle_timeout_seconds: int = 60
    show_upsells: bool = True
    require_phone: bool = False
    enable_cash: bool = False
    default_language: str = "bg"
    theme: str = "light"


class KioskOrderCreate(BaseModel):
    items: List[Dict[str, Any]]
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    payment_method: str = "card"
    order_type: str = "takeaway"


# ============================================================================
# DRIVE THRU SCHEMAS
# ============================================================================

class DriveThruOrderCreate(BaseModel):
    venue_id: int
    lane: DriveThruLane = DriveThruLane.LANE_1
    items: List[Dict[str, Any]]
    customer_name: Optional[str] = None
    vehicle_description: Optional[str] = None


class DriveThruOrderResponse(BaseModel):
    id: int
    order_number: str
    lane: DriveThruLane
    status: DriveThruOrderStatus
    queue_position: int
    estimated_wait_minutes: int
    items: List[Dict[str, Any]]
    total: float
    customer_name: Optional[str] = None
    vehicle_description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# DELIVERY & GPS TRACKING SCHEMAS
# ============================================================================

class DriverLocationUpdate(BaseModel):
    driver_id: int
    latitude: float
    longitude: float
    heading: Optional[float] = None
    speed: Optional[float] = None


class DeliveryTrackingResponse(BaseModel):
    order_id: int
    order_number: str
    driver_id: int
    driver_name: str
    driver_phone: str
    current_location: Dict[str, float]
    destination: Dict[str, float]
    estimated_arrival_minutes: int
    status: str
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PARTIAL PAYMENT & VOUCHER SCHEMAS
# ============================================================================

class PartialPaymentCreate(BaseModel):
    order_id: int
    amount: float
    payment_method: str
    reference: Optional[str] = None
    tip_amount: float = 0.0


class PartialPaymentResponse(BaseModel):
    id: int
    order_id: int
    amount: float
    payment_method: str
    reference: Optional[str] = None
    tip_amount: float
    created_at: datetime
    staff_user_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class VoucherCreate(BaseModel):
    code: str
    voucher_type: str
    value: float
    free_item_id: Optional[int] = None
    min_order_amount: Optional[float] = None
    max_uses: Optional[int] = None
    max_uses_per_customer: Optional[int] = 1
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    applicable_items: Optional[List[int]] = None
    applicable_categories: Optional[List[int]] = None


class VoucherResponse(BaseModel):
    id: int
    code: str
    voucher_type: str
    value: float
    free_item_id: Optional[int] = None
    min_order_amount: Optional[float] = None
    max_uses: Optional[int] = None
    uses_count: int = 0
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_valid: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PAYROLL SCHEMAS
# ============================================================================

class PayrollEntryCreate(BaseModel):
    staff_user_id: int
    period_start: datetime
    period_end: datetime
    regular_hours: float
    overtime_hours: float = 0
    hourly_rate: float
    overtime_rate: Optional[float] = None
    tips_collected: float = 0
    bonuses: float = 0
    deductions: float = 0
    notes: Optional[str] = None


class PayrollEntryResponse(BaseModel):
    id: int
    staff_user_id: int
    staff_name: str
    period_start: datetime
    period_end: datetime
    regular_hours: float
    overtime_hours: float
    hourly_rate: float
    overtime_rate: float
    regular_pay: float
    overtime_pay: float
    tips_collected: float
    bonuses: float
    deductions: float
    gross_pay: float
    employee_social_contribution: float
    employer_social_contribution: float
    health_insurance: float
    tax_withheld: float
    net_pay: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# INTERNAL MESSAGING SCHEMAS
# ============================================================================

class InternalMessageCreate(BaseModel):
    recipient_id: Optional[int] = None
    recipient_role: Optional[StaffRoleEnum] = None
    subject: str
    body: str
    priority: MessagePriority = MessagePriority.NORMAL


class InternalMessageResponse(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    recipient_id: Optional[int] = None
    recipient_name: Optional[str] = None
    recipient_role: Optional[str] = None
    subject: str
    body: str
    priority: MessagePriority
    read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# MULTI-WAREHOUSE SCHEMAS
# ============================================================================

class WarehouseCreate(BaseModel):
    venue_id: int
    name: str
    address: Optional[str] = None
    warehouse_type: str = "main"
    is_default: bool = False


class WarehouseResponse(BaseModel):
    id: int
    venue_id: int
    name: str
    address: Optional[str] = None
    warehouse_type: str
    is_default: bool
    total_items: int = 0
    total_value: float = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseTransferCreate(BaseModel):
    source_warehouse_id: int
    destination_warehouse_id: int
    stock_item_id: int
    quantity: float
    notes: Optional[str] = None


class WarehouseTransferResponse(BaseModel):
    id: int
    source_warehouse_id: int
    source_warehouse_name: str
    destination_warehouse_id: int
    destination_warehouse_name: str
    stock_item_id: int
    stock_item_name: str
    quantity: float
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    created_by: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# PAYMENT GATEWAY SCHEMAS
# ============================================================================

class PaymentIntentCreate(BaseModel):
    order_id: int
    amount: float
    currency: str = "BGN"
    gateway: PaymentGateway = PaymentGateway.STRIPE
    payment_method_types: List[str] = ["card"]
    metadata: Optional[Dict[str, Any]] = None


class PaymentIntentResponse(BaseModel):
    id: str
    order_id: int
    amount: float
    currency: str
    status: str
    client_secret: Optional[str] = None
    gateway: PaymentGateway
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MobilePaymentRequest(BaseModel):
    order_id: int
    payment_token: str
    payment_type: str
    amount: float
    currency: str = "BGN"


# ============================================================================
# SPLIT BILL SCHEMAS
# ============================================================================

class SplitBillGuestItem(BaseModel):
    order_item_id: int
    quantity: int = 1


class SplitBillGuest(BaseModel):
    guest_name: str
    items: List[SplitBillGuestItem] = []
    custom_amount: Optional[float] = None


class SplitBillCreate(BaseModel):
    order_id: int
    split_type: SplitBillType
    guests: List[SplitBillGuest]


class SplitBillPayment(BaseModel):
    guest_index: int
    payment_method: str
    amount: float
    tip_amount: float = 0.0


class SplitBillResponse(BaseModel):
    id: int
    order_id: int
    split_type: SplitBillType
    guests: List[Dict[str, Any]]
    total_amount: float
    paid_amount: float
    remaining_amount: float
    is_complete: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# QR CODE SCHEMAS
# ============================================================================

class QRCodeRequest(BaseModel):
    table_id: int
    size: int = 300
    format: str = "png"


class QRCodeResponse(BaseModel):
    table_id: int
    qr_code_base64: str
    url: str


class TableResponse(BaseModel):
    id: int
    number: int
    seats: int
    venue_id: int
    active: bool = True
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VenueStationResponse(BaseModel):
    id: int
    name: Any  # JSON column: may be Dict[str, str] or plain string depending on DB backend
    station_type: str
    active: bool

    model_config = ConfigDict(from_attributes=True)
