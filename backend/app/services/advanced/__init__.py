"""Advanced feature services."""

from app.services.advanced.waste_tracking import WasteTrackingService
from app.services.advanced.labor_forecasting import LaborForecastingService
from app.services.advanced.order_throttling import OrderThrottlingService
from app.services.advanced.wifi_marketing import WifiMarketingService
from app.services.advanced.menu_experiments import MenuExperimentsService
from app.services.advanced.dynamic_pricing import DynamicPricingService
from app.services.advanced.curbside import CurbsideService
from app.services.advanced.delivery_dispatch import DeliveryDispatchService
from app.services.advanced.sentiment_analysis import SentimentAnalysisService
from app.services.advanced.gift_cards import GiftCardService
from app.services.advanced.tip_pooling import TipPoolingService
from app.services.advanced.cross_sell import CrossSellService
from app.services.advanced.customer_journey import CustomerJourneyService
from app.services.advanced.shelf_life import ShelfLifeService
from app.services.advanced.prep_lists import PrepListService
from app.services.advanced.kitchen_load import KitchenLoadService
from app.services.advanced.wait_time import WaitTimeService
from app.services.advanced.allergen import AllergenService
from app.services.advanced.sustainability import SustainabilityService
from app.services.advanced.iot_monitoring import IoTMonitoringService
from app.services.advanced.vendor_scorecard import VendorScorecardService
from app.services.advanced.virtual_brands import VirtualBrandsService
from app.services.advanced.table_turn import TableTurnService
from app.services.advanced.notifications import NotificationService
from app.services.advanced.traceability import TraceabilityService

__all__ = [
    "WasteTrackingService",
    "LaborForecastingService",
    "OrderThrottlingService",
    "WifiMarketingService",
    "MenuExperimentsService",
    "DynamicPricingService",
    "CurbsideService",
    "DeliveryDispatchService",
    "SentimentAnalysisService",
    "GiftCardService",
    "TipPoolingService",
    "CrossSellService",
    "CustomerJourneyService",
    "ShelfLifeService",
    "PrepListService",
    "KitchenLoadService",
    "WaitTimeService",
    "AllergenService",
    "SustainabilityService",
    "IoTMonitoringService",
    "VendorScorecardService",
    "VirtualBrandsService",
    "TableTurnService",
    "NotificationService",
    "TraceabilityService",
]
