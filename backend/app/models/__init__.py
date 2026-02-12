"""SQLAlchemy models."""

from app.models.user import User
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.stock_item import StockItem
from app.models.location import Location
from app.models.stock import StockOnHand, StockMovement
from app.models.inventory import InventorySession, InventoryLine
from app.models.order import PurchaseOrder, PurchaseOrderLine, POStatus
from app.models.pos import PosRawEvent, PosSalesLine
from app.models.recipe import Recipe, RecipeLine
from app.models.ai import AIPhoto, TrainingImage, ProductFeatureCache, RecognitionLog
from app.models.reconciliation import (
    ReconciliationResult,
    ReorderProposal,
    SupplierOrderDraft,
    DeltaSeverity,
    OrderDraftStatus,
)

# New competitor feature models
from app.models.invoice import (
    Invoice,
    InvoiceLine,
    PriceHistory,
    PriceAlert,
    GLCode,
    APApprovalWorkflow,
    InvoiceStatus,
    InvoiceCaptureMethod,
)
from app.models.marketing import (
    MarketingCampaign,
    CampaignRecipient,
    CustomerSegment,
    AutomatedTrigger,
    MenuRecommendation,
    LoyaltyProgram,
    CustomerLoyalty,
    CampaignStatus,
    CampaignType,
    TriggerType,
)
from app.models.reservations import (
    Reservation,
    Waitlist,
    TableAvailability,
    ReservationSettings,
    GuestHistory,
    ReservationStatus,
    WaitlistStatus,
    BookingSource,
)
from app.models.delivery import (
    DeliveryIntegration,
    DeliveryOrder,
    DeliveryOrderItem,
    MenuSync,
    ItemAvailability,
    DeliveryPlatformMapping,
    DeliveryPlatform,
    DeliveryOrderStatus,
)
from app.models.analytics import (
    MenuAnalysis,
    ServerPerformance,
    SalesForecast,
    DailyMetrics,
    ConversationalQuery,
    Benchmark,
    BottleWeight,
    ScaleReading,
    MenuQuadrant,
)
from app.models.restaurant import (
    Table,
    Check,
    CheckItem,
    CheckPayment,
    MenuItem,
    KitchenOrder,
    GuestOrder,
)
from app.models.staff import (
    StaffUser,
    Shift,
    TimeOffRequest,
    TimeClockEntry,
    TableAssignment,
    PerformanceMetric,
    PerformanceGoal,
    TipPool,
    TipDistribution,
)
from app.models.customer import Customer
from app.models.price_lists import (
    PriceList,
    ProductPrice,
    DailyMenu,
    OperatorRecentItem,
    ManagerAlert,
    CustomerCredit,
    SubTable,
)
from app.models.hardware import (
    Keg,
    Tank,
    RFIDTag,
    InventoryCountSession,
    BarTab,
    WaiterCall,
    Integration,
    ThrottleRule,
    HotelGuest,
    OfflineQueueItem,
    OCRJob,
)
from app.models.operations import (
    AppSetting, PayrollRun, PayrollEntry, Notification,
    NotificationPreference, AlertConfig, HACCPTemperatureLog,
    HACCPSafetyCheck, FeedbackReview, AuditLogEntry,
    VIPCustomerLink, VIPOccasion, Warehouse, WarehouseTransfer,
    Promotion, Badge, Challenge, StaffAchievement, StaffPoints,
    RiskAlert, ReferralProgram, ReferralRecord, TaxFiling,
    Budget, DailyReconciliation, ShiftSchedule,
)
from app.models.restaurant import (
    MenuCategory, ModifierGroup, ModifierOption,
    MenuItemModifierGroup, ComboMeal, ComboItem,
)
# Platform compatibility models (ported from platform.zver.ai)
from app.models.platform_compat import (
    DepositStatus, ShiftStatus, OrderStatus, PaymentStatus,
    WaiterCallStatus, WaiterCallStatus as WaiterCallStatusEnum,
    GiftCardStatus, PurchaseOrderStatus,
    Venue, VenueStation, TableToken,
    Menu, MenuVersion, ItemTag, ItemTagLink,
    Order, OrderItem, OrderItemModifier, OrderEvent,
    LoyaltyTransaction, PromotionUsage,
    PurchaseOrderItem,
    AuditLog,
    AutoDiscount, StockBatch,
    DeliveryZone, DeliveryDriver,
    ReservationDeposit,
    StaffShift, ClockEvent, StaffBreak,
    CashDrawer, CashDrawerTransaction,
    OrderCancellation, ComboMenu, ComboMenuItem,
    OfflineTransaction, OfflineConnectivityLog,
    FraudScore, Stock,
    HouseAccount, HouseAccountTransaction,
    ThrottleEvent,
    Payment, LoyaltyCard, MenuItemModifier,
    KioskStatusLog, TimeEntry,
)
# Models moved to their canonical sources
from app.models.advanced_features import GiftCard, DynamicPricingRule
from app.models.menu_inventory_complete import MenuItemVariant

from app.models.advanced_features import (
    HappyHour,
    WasteTrackingEntry,
    MenuExperiment,
    LaborForecast,
    ReviewSentiment,
    WaitTimePrediction,
    KitchenStation,
)

# Integration models (missing models for untracked route files)
from app.models.integration_models import (
    SplitBill, SplitBillOrder, SplitBillGuest, SplitBillGuestItem, SplitBillStatus,
    HeldOrder, HeldOrderStatus,
    TableMerge, TableMergeItem,
    TableSession, TableSessionStatus, TableHistory,
    FloorPlan, FloorPlanTablePosition, FloorPlanArea,
    KioskConfig,
    VenueSettings,
    DriveThruOrder,
    AggregatorOrder,
)

# Complete modules (production, serial/batch)
from app.models.complete_modules import RecipeIngredient, ProductionOrder

# Missing features models
from app.models.missing_features_models import (
    ShiftTradeRequest, MenuItemReview, MenuItemRatingAggregate,
    CustomerReferral, CustomerRFMScore, RFMSegmentDefinition, SMSCampaign,
)

# Feature models
from app.models.feature_models import ProductionBatch

# Core business models (SMS, etc.)
from app.models.core_business_models import SMSMessage

# Staff enums
from app.models.staff import StaffRole

__all__ = [
    # Core models
    "User",
    "Supplier",
    "Product",
    "StockItem",
    "Location",
    "StockOnHand",
    "StockMovement",
    "InventorySession",
    "InventoryLine",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "POStatus",
    "PosRawEvent",
    "PosSalesLine",
    "Recipe",
    "RecipeLine",
    "AIPhoto",
    "TrainingImage",
    "ProductFeatureCache",
    "RecognitionLog",
    "ReconciliationResult",
    "ReorderProposal",
    "SupplierOrderDraft",
    "DeltaSeverity",
    "OrderDraftStatus",
    # Invoice & AP
    "Invoice",
    "InvoiceLine",
    "PriceHistory",
    "PriceAlert",
    "GLCode",
    "APApprovalWorkflow",
    "InvoiceStatus",
    "InvoiceCaptureMethod",
    # Marketing
    "MarketingCampaign",
    "CampaignRecipient",
    "CustomerSegment",
    "AutomatedTrigger",
    "MenuRecommendation",
    "LoyaltyProgram",
    "CustomerLoyalty",
    "CampaignStatus",
    "CampaignType",
    "TriggerType",
    # Reservations
    "Reservation",
    "Waitlist",
    "TableAvailability",
    "ReservationSettings",
    "GuestHistory",
    "ReservationStatus",
    "WaitlistStatus",
    "BookingSource",
    # Delivery
    "DeliveryIntegration",
    "DeliveryOrder",
    "DeliveryOrderItem",
    "MenuSync",
    "ItemAvailability",
    "DeliveryPlatformMapping",
    "DeliveryPlatform",
    "DeliveryOrderStatus",
    # Analytics
    "MenuAnalysis",
    "ServerPerformance",
    "SalesForecast",
    "DailyMetrics",
    "ConversationalQuery",
    "Benchmark",
    "BottleWeight",
    "ScaleReading",
    "MenuQuadrant",
    # Restaurant Operations
    "Table",
    "Check",
    "CheckItem",
    "CheckPayment",
    "MenuItem",
    "KitchenOrder",
    "GuestOrder",
    # Staff Management
    "StaffUser",
    "Shift",
    "TimeOffRequest",
    "TimeClockEntry",
    "TableAssignment",
    "PerformanceMetric",
    "PerformanceGoal",
    "TipPool",
    "TipDistribution",
    # Customers
    "Customer",
    # Price Lists & Daily Menus (TouchSale gap features)
    "PriceList",
    "ProductPrice",
    "DailyMenu",
    "OperatorRecentItem",
    "ManagerAlert",
    "CustomerCredit",
    "SubTable",
    # Bar Management & Advanced Features
    "HappyHour",
    "WasteTrackingEntry",
    "MenuExperiment",
    "LaborForecast",
    "ReviewSentiment",
    "WaitTimePrediction",
    "KitchenStation",
    # Operations
    "AppSetting",
    "PayrollRun",
    "PayrollEntry",
    "Notification",
    "NotificationPreference",
    "AlertConfig",
    "HACCPTemperatureLog",
    "HACCPSafetyCheck",
    "FeedbackReview",
    "AuditLogEntry",
    "VIPCustomerLink",
    "VIPOccasion",
    "Warehouse",
    "WarehouseTransfer",
    "Promotion",
    "Badge",
    "Challenge",
    "StaffAchievement",
    "StaffPoints",
    "RiskAlert",
    "ReferralProgram",
    "ReferralRecord",
    "TaxFiling",
    "Budget",
    "DailyReconciliation",
    "ShiftSchedule",
    # Menu (extended)
    "MenuCategory",
    "ModifierGroup",
    "ModifierOption",
    "MenuItemModifierGroup",
    "ComboMeal",
    "ComboItem",
]
