# Services module

from app.services.order_service import generate_whatsapp_text, generate_pdf, generate_xlsx
from app.services.reconciliation_service import (
    ReconciliationService,
    ReconciliationConfig,
    run_reconciliation,
)
from app.services.reorder_service import (
    ReorderService,
    ReorderConfig,
    generate_reorder_proposals,
)
from app.services.export_service import (
    ExportService,
    create_and_export_orders,
)
from app.services.sku_mapping_service import (
    SKUMappingService,
    MatchMethod,
    MatchResult,
    match_product_from_scan,
)

# New competitor-matching services
from app.services.invoice_service import (
    InvoiceOCRService,
    APAutomationService,
    PriceTrackingService,
)
from app.services.menu_engineering_service import (
    MenuEngineeringService,
    ServerPerformanceService,
    DailyMetricsService,
)
from app.services.communication_service import (
    EmailService,
    SMSService,
    NotificationService,
)
from app.services.scale_service import (
    ScaleService,
    BottleWeightDatabaseService,
    InventoryCountingService,
)
from app.services.delivery_service import (
    DeliveryAggregatorService,
    MenuSyncService,
    DeliveryWebhookHandler,
    DeliveryReportingService,
)
from app.services.marketing_service import (
    MarketingAutomationService,
    AutomatedTriggerService,
    MenuRecommendationService,
    LoyaltyService,
)
from app.services.reservations_service import (
    ReservationService,
    WaitlistService,
)
from app.services.conversational_ai_service import (
    ConversationalAIService,
)

__all__ = [
    # Core services
    "generate_whatsapp_text",
    "generate_pdf",
    "generate_xlsx",
    "ReconciliationService",
    "ReconciliationConfig",
    "run_reconciliation",
    "ReorderService",
    "ReorderConfig",
    "generate_reorder_proposals",
    "ExportService",
    "create_and_export_orders",
    "SKUMappingService",
    "MatchMethod",
    "MatchResult",
    "match_product_from_scan",
    # Invoice & AP
    "InvoiceOCRService",
    "APAutomationService",
    "PriceTrackingService",
    # Menu Engineering & Analytics
    "MenuEngineeringService",
    "ServerPerformanceService",
    "DailyMetricsService",
    # Communication
    "EmailService",
    "SMSService",
    "NotificationService",
    # Scale & Inventory
    "ScaleService",
    "BottleWeightDatabaseService",
    "InventoryCountingService",
    # Delivery
    "DeliveryAggregatorService",
    "MenuSyncService",
    "DeliveryWebhookHandler",
    "DeliveryReportingService",
    # Marketing
    "MarketingAutomationService",
    "AutomatedTriggerService",
    "MenuRecommendationService",
    "LoyaltyService",
    # Reservations
    "ReservationService",
    "WaitlistService",
    # Conversational AI
    "ConversationalAIService",
]
