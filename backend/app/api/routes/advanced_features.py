"""API Routes for Advanced Competitor Features."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.advanced_features import (
    # Waste Tracking
    WasteTrackingEntryCreate,
    WasteTrackingEntryResponse,
    WasteForecastResponse,
    WasteSummaryResponse,
    # Labor Forecasting
    LaborForecastCreate,
    LaborForecastResponse,
    LaborComplianceRuleCreate,
    LaborComplianceRuleResponse,
    LaborComplianceViolationResponse,
    # Order Throttling
    KitchenCapacityCreate,
    KitchenCapacityResponse,
    ThrottleStatusResponse,
    # WiFi Marketing
    GuestWifiSessionCreate,
    GuestWifiSessionResponse,
    WifiMarketingStatsResponse,
    # Menu Experiments
    MenuExperimentCreate,
    MenuExperimentResponse,
    ExperimentAnalysisResponse,
    # Dynamic Pricing
    DynamicPricingRuleCreate,
    DynamicPricingRuleResponse,
    SurgePricingStatusResponse,
    # Curbside
    CurbsideOrderCreate,
    CurbsideOrderResponse,
    CurbsideArrivalRequest,
    CurbsideStatusResponse,
    # Delivery Dispatch
    DeliveryProviderCreate,
    DeliveryProviderResponse,
    DeliveryDispatchRequest,
    DeliveryDispatchResponse,
    DispatchQuoteResponse,
    # Sentiment Analysis
    ReviewSentimentCreate,
    ReviewSentimentResponse,
    SentimentSummaryResponse,
    AIResponseSuggestion,
    # Gift Cards
    GiftCardProgramCreate,
    GiftCardProgramResponse,
    GiftCardCreate,
    GiftCardResponse,
    GiftCardRedemptionRequest,
    GiftCardBalanceResponse,
    # Tip Pooling
    TipPoolConfigurationCreate,
    TipPoolConfigurationResponse,
    TipPoolDistributionResponse,
    TipCalculationRequest,
    TipCalculationResponse,
    # Cross-Sell
    CrossSellRuleCreate,
    CrossSellRuleResponse,
    CrossSellRecommendationRequest,
    CrossSellRecommendationResponse,
    CrossSellPerformanceResponse,
    # Customer Journey
    CustomerJourneyEventCreate,
    CustomerJourneyEventResponse,
    FunnelAnalysisResponse,
    # Shelf Life
    ProductShelfLifeCreate,
    ProductShelfLifeResponse,
    InventoryBatchCreate,
    InventoryBatchResponse,
    ExpirationSummaryResponse,
    # Prep Lists
    PrepListResponse,
    PrepListItemResponse,
    PrepListGenerationRequest,
    PrepListGenerationResponse,
    # Kitchen Load
    KitchenStationCreate,
    KitchenStationResponse,
    KitchenLoadSummaryResponse,
    # Wait Time
    WaitTimePredictionRequest,
    WaitTimePredictionResponse,
    WaitTimePredictionAccuracyResponse,
    # Allergens
    AllergenProfileCreate,
    AllergenProfileResponse,
    AllergenCheckRequest,
    AllergenCheckResponse,
    # Sustainability
    SustainabilityMetricCreate,
    SustainabilityMetricResponse,
    ESGReportResponse,
    ESGDashboardResponse,
    # IoT Monitoring
    EquipmentSensorCreate,
    EquipmentSensorResponse,
    SensorReadingCreate,
    SensorReadingResponse,
    EquipmentDashboardResponse,
    # Vendor Scorecard
    VendorScorecardCreate,
    VendorScorecardResponse,
    VendorComparisonResponse,
    # Virtual Brands
    VirtualBrandCreate,
    VirtualBrandResponse,
    VirtualBrandPerformanceResponse,
    # Table Turn
    TableTurnMetricCreate,
    TableTurnMetricResponse,
    TableMilestoneUpdate,
    TableTurnSummaryResponse,
    # Notifications
    OrderStatusNotificationCreate,
    OrderStatusNotificationResponse,
    NotificationStatsResponse,
    # Traceability
    SupplyChainTraceCreate,
    SupplyChainTraceResponse,
    TraceabilityQueryResponse,
    BlockchainVerificationResponse,
)
from app.services.advanced import (
    WasteTrackingService,
    LaborForecastingService,
    OrderThrottlingService,
    WifiMarketingService,
    MenuExperimentsService,
    DynamicPricingService,
    CurbsideService,
    DeliveryDispatchService,
    SentimentAnalysisService,
    GiftCardService,
    TipPoolingService,
    CrossSellService,
    CustomerJourneyService,
    ShelfLifeService,
    PrepListService,
    KitchenLoadService,
    WaitTimeService,
    AllergenService,
    SustainabilityService,
    IoTMonitoringService,
    VendorScorecardService,
    VirtualBrandsService,
    TableTurnService,
    NotificationService,
    TraceabilityService,
)

router = APIRouter(prefix="/advanced", tags=["Advanced Features"])


# ============================================================================
# 1. WASTE TRACKING
# ============================================================================

@router.post("/waste-tracking", response_model=WasteTrackingEntryResponse)
def create_waste_entry(
    data: WasteTrackingEntryCreate,
    db: Session = Depends(get_db),
):
    """Create a waste tracking entry."""
    service = WasteTrackingService(db)
    return service.create_entry(**data.model_dump())


@router.get("/waste-tracking/location/{location_id}", response_model=List[WasteTrackingEntryResponse])
def get_waste_entries(
    location_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get waste tracking entries."""
    service = WasteTrackingService(db)
    return service.get_entries(location_id, start_date, end_date, category)


@router.get("/waste-tracking/summary/{location_id}", response_model=WasteSummaryResponse)
def get_waste_summary(
    location_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
):
    """Get waste summary for a period."""
    service = WasteTrackingService(db)
    return service.get_summary(location_id, start_date, end_date)


@router.post("/waste-tracking/forecast/{location_id}", response_model=WasteForecastResponse)
def generate_waste_forecast(
    location_id: int,
    forecast_date: date,
    db: Session = Depends(get_db),
):
    """Generate AI-based waste forecast."""
    service = WasteTrackingService(db)
    return service.generate_forecast(location_id, forecast_date)


# ============================================================================
# 2. LABOR FORECASTING
# ============================================================================

@router.post("/labor/forecast/{location_id}", response_model=LaborForecastResponse)
def generate_labor_forecast(
    location_id: int,
    forecast_date: date,
    db: Session = Depends(get_db),
):
    """Generate ML-based labor forecast."""
    service = LaborForecastingService(db)
    return service.generate_forecast(location_id, forecast_date)


@router.get("/labor/forecast/{location_id}/{forecast_date}", response_model=Optional[LaborForecastResponse])
def get_labor_forecast(
    location_id: int,
    forecast_date: date,
    db: Session = Depends(get_db),
):
    """Get labor forecast for a date."""
    service = LaborForecastingService(db)
    return service.get_forecast(location_id, forecast_date)


@router.post("/labor/compliance-rules", response_model=LaborComplianceRuleResponse)
def create_compliance_rule(
    data: LaborComplianceRuleCreate,
    db: Session = Depends(get_db),
):
    """Create a labor compliance rule."""
    service = LaborForecastingService(db)
    return service.create_compliance_rule(**data.model_dump())


@router.get("/labor/violations/{location_id}", response_model=List[LaborComplianceViolationResponse])
def get_violations(
    location_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    resolved: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """Get compliance violations."""
    service = LaborForecastingService(db)
    return service.get_violations(location_id, start_date, end_date, resolved)


# ============================================================================
# 3. ORDER THROTTLING
# ============================================================================

@router.post("/throttling/config", response_model=KitchenCapacityResponse)
def create_capacity_config(
    data: KitchenCapacityCreate,
    db: Session = Depends(get_db),
):
    """Create kitchen capacity configuration."""
    service = OrderThrottlingService(db)
    return service.create_capacity_config(**data.model_dump())


@router.get("/throttling/status/{location_id}", response_model=ThrottleStatusResponse)
def get_throttle_status(
    location_id: int,
    db: Session = Depends(get_db),
):
    """Get current throttling status."""
    service = OrderThrottlingService(db)
    status = service.check_capacity(location_id, 0)
    return ThrottleStatusResponse(
        is_throttling=not status["can_accept"],
        current_load=status["current_load"],
        max_capacity=status["max_capacity"],
        load_percent=status["load_percent"],
        estimated_wait_minutes=status["estimated_wait_minutes"],
        affected_orders=0,
    )


# ============================================================================
# 4. WIFI MARKETING
# ============================================================================

@router.post("/wifi/session", response_model=GuestWifiSessionResponse)
def create_wifi_session(
    data: GuestWifiSessionCreate,
    db: Session = Depends(get_db),
):
    """Create or update a WiFi session."""
    service = WifiMarketingService(db)
    return service.create_session(**data.model_dump())


@router.get("/wifi/stats/{location_id}", response_model=WifiMarketingStatsResponse)
def get_wifi_stats(
    location_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
):
    """Get WiFi marketing statistics."""
    service = WifiMarketingService(db)
    return service.get_stats(location_id, days)


# ============================================================================
# 5. MENU EXPERIMENTS
# ============================================================================

@router.post("/experiments", response_model=MenuExperimentResponse)
def create_experiment(
    data: MenuExperimentCreate,
    db: Session = Depends(get_db),
):
    """Create a menu A/B test experiment."""
    service = MenuExperimentsService(db)
    return service.create_experiment(**data.model_dump())


@router.get("/experiments/{experiment_id}/analyze", response_model=ExperimentAnalysisResponse)
def analyze_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
):
    """Analyze experiment results."""
    service = MenuExperimentsService(db)
    try:
        return service.analyze_experiment(experiment_id)
    except (ValueError, Exception) as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise


# ============================================================================
# 6. DYNAMIC PRICING
# ============================================================================

@router.post("/pricing/rules", response_model=DynamicPricingRuleResponse)
def create_pricing_rule(
    data: DynamicPricingRuleCreate,
    db: Session = Depends(get_db),
):
    """Create a dynamic pricing rule."""
    service = DynamicPricingService(db)
    return service.create_rule(**data.model_dump())


@router.get("/pricing/status/{location_id}", response_model=SurgePricingStatusResponse)
def get_surge_status(
    location_id: int,
    db: Session = Depends(get_db),
):
    """Get current surge pricing status."""
    service = DynamicPricingService(db)
    return service.get_surge_status(location_id)


# ============================================================================
# 7. CURBSIDE PICKUP
# ============================================================================

@router.post("/curbside", response_model=CurbsideOrderResponse)
def create_curbside_order(
    data: CurbsideOrderCreate,
    db: Session = Depends(get_db),
):
    """Create a curbside pickup order."""
    service = CurbsideService(db)
    return service.create_curbside_order(**data.model_dump())


@router.post("/curbside/{order_id}/arrived", response_model=CurbsideOrderResponse)
def customer_arrived(
    order_id: int,
    data: CurbsideArrivalRequest,
    db: Session = Depends(get_db),
):
    """Mark customer as arrived."""
    service = CurbsideService(db)
    try:
        return service.customer_arrived(order_id, data.parking_spot)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/curbside/status/{location_id}", response_model=CurbsideStatusResponse)
def get_curbside_status(
    location_id: int,
    db: Session = Depends(get_db),
):
    """Get curbside pickup status."""
    service = CurbsideService(db)
    return service.get_status(location_id)


# ============================================================================
# 8. DELIVERY DISPATCH
# ============================================================================

@router.post("/delivery/providers", response_model=DeliveryProviderResponse)
def create_delivery_provider(
    data: DeliveryProviderCreate,
    db: Session = Depends(get_db),
):
    """Create a delivery provider."""
    service = DeliveryDispatchService(db)
    return service.create_provider(**data.model_dump())


@router.get("/delivery/quotes/{location_id}")
def get_delivery_quotes(
    location_id: int,
    address: str,
    distance: float = 3.0,
    db: Session = Depends(get_db),
):
    """Get delivery quotes from providers."""
    service = DeliveryDispatchService(db)
    return service.get_quotes(location_id, address, distance)


@router.post("/delivery/dispatch", response_model=DeliveryDispatchResponse)
def dispatch_delivery(
    data: DeliveryDispatchRequest,
    db: Session = Depends(get_db),
):
    """Dispatch a delivery order."""
    service = DeliveryDispatchService(db)
    return service.dispatch_order(**data.model_dump())


# ============================================================================
# 9. SENTIMENT ANALYSIS
# ============================================================================

@router.post("/reviews/analyze", response_model=ReviewSentimentResponse)
def analyze_review(
    data: ReviewSentimentCreate,
    db: Session = Depends(get_db),
):
    """Analyze a customer review."""
    service = SentimentAnalysisService(db)
    return service.analyze_review(**data.model_dump())


@router.get("/reviews/summary/{location_id}", response_model=SentimentSummaryResponse)
def get_sentiment_summary(
    location_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
):
    """Get sentiment summary."""
    service = SentimentAnalysisService(db)
    return service.get_summary(location_id, days)


@router.get("/reviews/{review_id}/suggest-response", response_model=AIResponseSuggestion)
def suggest_response(
    review_id: int,
    db: Session = Depends(get_db),
):
    """Generate AI response suggestion."""
    service = SentimentAnalysisService(db)
    try:
        return service.generate_response(review_id)
    except (ValueError, Exception) as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise


# ============================================================================
# 10. GIFT CARDS
# ============================================================================

@router.post("/gift-cards/programs", response_model=GiftCardProgramResponse)
def create_gift_card_program(
    data: GiftCardProgramCreate,
    db: Session = Depends(get_db),
):
    """Create a gift card program."""
    service = GiftCardService(db)
    return service.create_program(**data.model_dump())


@router.post("/gift-cards/purchase", response_model=GiftCardResponse)
def purchase_gift_card(
    data: GiftCardCreate,
    db: Session = Depends(get_db),
):
    """Purchase a gift card."""
    service = GiftCardService(db)
    try:
        return service.purchase_card(**data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/gift-cards/{card_number}/balance", response_model=GiftCardBalanceResponse)
def check_gift_card_balance(
    card_number: str,
    pin: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Check gift card balance."""
    service = GiftCardService(db)
    try:
        return service.check_balance(card_number, pin)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/gift-cards/redeem")
def redeem_gift_card(
    data: GiftCardRedemptionRequest,
    db: Session = Depends(get_db),
):
    """Redeem from a gift card."""
    service = GiftCardService(db)
    try:
        return service.redeem(**data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# 11. TIP POOLING
# ============================================================================

@router.post("/tips/config", response_model=TipPoolConfigurationResponse)
def create_tip_pool_config(
    data: TipPoolConfigurationCreate,
    db: Session = Depends(get_db),
):
    """Create tip pool configuration."""
    service = TipPoolingService(db)
    return service.create_configuration(**data.model_dump())


@router.post("/tips/calculate", response_model=TipCalculationResponse)
def calculate_tip_distribution(
    data: TipCalculationRequest,
    db: Session = Depends(get_db),
):
    """Calculate tip distribution."""
    service = TipPoolingService(db)
    return service.calculate_distribution(
        data.configuration_id,
        data.total_tips,
        {emp_id: {"hours": hours, "role": "server"} for emp_id, hours in data.employee_hours.items()},
    )


# ============================================================================
# 12. CROSS-SELL
# ============================================================================

@router.post("/cross-sell/rules", response_model=CrossSellRuleResponse)
def create_cross_sell_rule(
    data: CrossSellRuleCreate,
    db: Session = Depends(get_db),
):
    """Create a cross-sell rule."""
    service = CrossSellService(db)
    return service.create_rule(**data.model_dump())


@router.post("/cross-sell/recommendations", response_model=CrossSellRecommendationResponse)
def get_cross_sell_recommendations(
    data: CrossSellRecommendationRequest,
    db: Session = Depends(get_db),
):
    """Get cross-sell recommendations."""
    service = CrossSellService(db)
    return service.get_recommendations(**data.model_dump())


@router.get("/cross-sell/performance", response_model=CrossSellPerformanceResponse)
def get_cross_sell_performance(
    location_id: Optional[int] = None,
    days: int = 30,
    db: Session = Depends(get_db),
):
    """Get cross-sell performance."""
    service = CrossSellService(db)
    return service.get_performance(location_id, days)


# ============================================================================
# 13. CUSTOMER JOURNEY
# ============================================================================

@router.post("/journey/event", response_model=CustomerJourneyEventResponse)
def track_journey_event(
    data: CustomerJourneyEventCreate,
    db: Session = Depends(get_db),
):
    """Track a customer journey event."""
    service = CustomerJourneyService(db)
    return service.track_event(**data.model_dump())


@router.get("/journey/funnel", response_model=FunnelAnalysisResponse)
def get_funnel_analysis(
    location_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    channel: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get funnel analysis."""
    service = CustomerJourneyService(db)
    return service.get_funnel_analysis(location_id, start_date, end_date, channel)


# ============================================================================
# 14. SHELF LIFE
# ============================================================================

@router.post("/shelf-life/config", response_model=ProductShelfLifeResponse)
def create_shelf_life_config(
    data: ProductShelfLifeCreate,
    db: Session = Depends(get_db),
):
    """Create shelf life configuration."""
    service = ShelfLifeService(db)
    return service.create_shelf_life_config(**data.model_dump())


@router.post("/shelf-life/batch", response_model=InventoryBatchResponse)
def create_inventory_batch(
    data: InventoryBatchCreate,
    db: Session = Depends(get_db),
):
    """Create an inventory batch with expiration."""
    service = ShelfLifeService(db)
    return service.create_batch(**data.model_dump())


@router.get("/shelf-life/summary/{location_id}", response_model=ExpirationSummaryResponse)
def get_expiration_summary(
    location_id: int,
    db: Session = Depends(get_db),
):
    """Get expiration summary."""
    service = ShelfLifeService(db)
    return service.get_expiration_summary(location_id)


# ============================================================================
# 15. PREP LISTS
# ============================================================================

@router.post("/prep-lists/generate", response_model=PrepListGenerationResponse)
def generate_prep_list(
    data: PrepListGenerationRequest,
    db: Session = Depends(get_db),
):
    """Generate a prep list from forecast."""
    service = PrepListService(db)
    return service.generate_from_forecast(
        data.location_id,
        data.prep_date,
        100,  # Default forecast covers
        data.station,
    )


@router.get("/prep-lists/{location_id}", response_model=List[PrepListResponse])
def get_prep_lists(
    location_id: int,
    prep_date: Optional[date] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get prep lists."""
    service = PrepListService(db)
    return service.get_prep_lists(location_id, prep_date, status)


# ============================================================================
# 16. KITCHEN LOAD
# ============================================================================

@router.post("/kitchen/stations", response_model=KitchenStationResponse)
def create_kitchen_station(
    data: KitchenStationCreate,
    db: Session = Depends(get_db),
):
    """Create a kitchen station."""
    service = KitchenLoadService(db)
    return service.create_station(**data.model_dump())


@router.get("/kitchen/summary/{location_id}", response_model=KitchenLoadSummaryResponse)
def get_kitchen_summary(
    location_id: int,
    db: Session = Depends(get_db),
):
    """Get kitchen load summary."""
    service = KitchenLoadService(db)
    return service.get_kitchen_summary(location_id)


# ============================================================================
# 17. WAIT TIME
# ============================================================================

@router.post("/wait-time/predict", response_model=WaitTimePredictionResponse)
def predict_wait_time(
    data: WaitTimePredictionRequest,
    db: Session = Depends(get_db),
):
    """Predict wait time for an order."""
    service = WaitTimeService(db)
    return service.predict_wait_time(**data.model_dump())


@router.get("/wait-time/accuracy/{location_id}", response_model=WaitTimePredictionAccuracyResponse)
def get_wait_time_accuracy(
    location_id: int,
    days: int = 7,
    db: Session = Depends(get_db),
):
    """Get wait time prediction accuracy."""
    service = WaitTimeService(db)
    return service.get_accuracy_stats(location_id, days)


# ============================================================================
# 18. ALLERGENS
# ============================================================================

@router.post("/allergens/profile", response_model=AllergenProfileResponse)
def create_allergen_profile(
    data: AllergenProfileCreate,
    db: Session = Depends(get_db),
):
    """Create allergen profile for a product."""
    service = AllergenService(db)
    return service.create_profile(**data.model_dump())


@router.post("/allergens/check", response_model=AllergenCheckResponse)
def check_allergens(
    data: AllergenCheckRequest,
    db: Session = Depends(get_db),
):
    """Check order items against allergens."""
    service = AllergenService(db)
    return service.check_order(data.order_items, data.customer_allergens)


# ============================================================================
# 19. SUSTAINABILITY
# ============================================================================

@router.post("/sustainability/metrics", response_model=SustainabilityMetricResponse)
def record_sustainability_metrics(
    data: SustainabilityMetricCreate,
    db: Session = Depends(get_db),
):
    """Record daily sustainability metrics."""
    service = SustainabilityService(db)
    return service.record_daily_metrics(**data.model_dump())


@router.get("/sustainability/dashboard/{location_id}", response_model=ESGDashboardResponse)
def get_sustainability_dashboard(
    location_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
):
    """Get sustainability dashboard."""
    service = SustainabilityService(db)
    return service.get_dashboard(location_id, days)


# ============================================================================
# 20. IOT MONITORING
# ============================================================================

@router.post("/iot/sensors", response_model=EquipmentSensorResponse)
def create_sensor(
    data: EquipmentSensorCreate,
    db: Session = Depends(get_db),
):
    """Register an IoT sensor."""
    service = IoTMonitoringService(db)
    return service.create_sensor(**data.model_dump())


@router.post("/iot/readings", response_model=SensorReadingResponse)
def record_sensor_reading(
    data: SensorReadingCreate,
    db: Session = Depends(get_db),
):
    """Record a sensor reading."""
    service = IoTMonitoringService(db)
    return service.record_reading(**data.model_dump())


@router.get("/iot/dashboard/{location_id}", response_model=EquipmentDashboardResponse)
def get_equipment_dashboard(
    location_id: int,
    db: Session = Depends(get_db),
):
    """Get equipment monitoring dashboard."""
    service = IoTMonitoringService(db)
    return service.get_dashboard(location_id)


# ============================================================================
# 21. VENDOR SCORECARD
# ============================================================================

@router.post("/vendors/scorecard", response_model=VendorScorecardResponse)
def create_vendor_scorecard(
    data: VendorScorecardCreate,
    db: Session = Depends(get_db),
):
    """Create a vendor scorecard."""
    service = VendorScorecardService(db)
    return service.create_scorecard(**data.model_dump())


@router.get("/vendors/{supplier_id}/scorecard", response_model=Optional[VendorScorecardResponse])
def get_vendor_scorecard(
    supplier_id: int,
    db: Session = Depends(get_db),
):
    """Get vendor scorecard."""
    service = VendorScorecardService(db)
    return service.get_scorecard(supplier_id)


@router.post("/vendors/compare", response_model=VendorComparisonResponse)
def compare_vendors(
    supplier_ids: List[int],
    db: Session = Depends(get_db),
):
    """Compare multiple vendors."""
    service = VendorScorecardService(db)
    return service.compare_vendors(supplier_ids)


# ============================================================================
# 22. VIRTUAL BRANDS
# ============================================================================

@router.post("/virtual-brands", response_model=VirtualBrandResponse)
def create_virtual_brand(
    data: VirtualBrandCreate,
    db: Session = Depends(get_db),
):
    """Create a virtual brand."""
    service = VirtualBrandsService(db)
    return service.create_brand(**data.model_dump())


@router.get("/virtual-brands/{location_id}", response_model=List[VirtualBrandResponse])
def get_virtual_brands(
    location_id: int,
    db: Session = Depends(get_db),
):
    """Get virtual brands for a location."""
    service = VirtualBrandsService(db)
    return service.get_brands(location_id)


@router.get("/virtual-brands/{brand_id}/performance", response_model=VirtualBrandPerformanceResponse)
def get_brand_performance(
    brand_id: int,
    db: Session = Depends(get_db),
):
    """Get virtual brand performance."""
    service = VirtualBrandsService(db)
    try:
        return service.get_performance(brand_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# 23. TABLE TURN
# ============================================================================

@router.post("/table-turn/start", response_model=TableTurnMetricResponse)
def start_table_turn(
    data: TableTurnMetricCreate,
    db: Session = Depends(get_db),
):
    """Start tracking a table turn."""
    service = TableTurnService(db)
    return service.start_turn(**data.model_dump())


@router.post("/table-turn/{turn_id}/milestone", response_model=TableTurnMetricResponse)
def update_table_milestone(
    turn_id: int,
    data: TableMilestoneUpdate,
    db: Session = Depends(get_db),
):
    """Update a table turn milestone."""
    service = TableTurnService(db)
    try:
        return service.update_milestone(turn_id, data.milestone, data.timestamp)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/table-turn/summary/{location_id}", response_model=TableTurnSummaryResponse)
def get_table_turn_summary(
    location_id: int,
    db: Session = Depends(get_db),
):
    """Get table turn summary."""
    service = TableTurnService(db)
    return service.get_summary(location_id)


# ============================================================================
# 24. NOTIFICATIONS
# ============================================================================

@router.post("/notifications", response_model=OrderStatusNotificationResponse)
def create_notification(
    data: OrderStatusNotificationCreate,
    db: Session = Depends(get_db),
):
    """Create and send an order notification."""
    service = NotificationService(db)
    notification = service.create_notification(**data.model_dump())
    service.send_notification(notification.id)
    return notification


@router.get("/notifications/stats", response_model=NotificationStatsResponse)
def get_notification_stats(
    days: int = 7,
    db: Session = Depends(get_db),
):
    """Get notification statistics."""
    service = NotificationService(db)
    return service.get_stats(days)


# ============================================================================
# 25. TRACEABILITY
# ============================================================================

@router.post("/traceability", response_model=SupplyChainTraceResponse)
def create_trace(
    data: SupplyChainTraceCreate,
    db: Session = Depends(get_db),
):
    """Create a supply chain trace."""
    service = TraceabilityService(db)
    return service.create_trace(**data.model_dump())


@router.get("/traceability/{trace_id}", response_model=TraceabilityQueryResponse)
def get_traceability(
    trace_id: str,
    db: Session = Depends(get_db),
):
    """Query traceability information."""
    service = TraceabilityService(db)
    try:
        return service.query_traceability(trace_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/traceability/{trace_id}/verify", response_model=BlockchainVerificationResponse)
def verify_trace(
    trace_id: str,
    db: Session = Depends(get_db),
):
    """Verify trace on blockchain."""
    service = TraceabilityService(db)
    try:
        return service.verify_trace(trace_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
