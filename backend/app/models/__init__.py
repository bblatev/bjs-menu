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
from app.models.advanced_features import (
    HappyHour,
    WasteTrackingEntry,
)

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
    # Bar Management
    "HappyHour",
    "WasteTrackingEntry",
]
