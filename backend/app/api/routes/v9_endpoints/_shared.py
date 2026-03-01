"""
V9 Advanced Features API Endpoints
BJ's Bar V9 - Enterprise POS System
100+ Advanced Features with Full API Coverage
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal


from app.core.rbac import get_current_user

# Import V9 Services
from app.services.advanced_operations_service import (
    AdvancedOperationsService as PermissionOverrideService,
)
# Alias the unified class for all granular usages
TerminalHealthService = PermissionOverrideService
SafeModeService = PermissionOverrideService
CashVarianceService = PermissionOverrideService
SessionTimeoutService = PermissionOverrideService
try:
    from app.services.advanced_kitchen_service import (
        AdvancedKitchenService as ProductionForecastService,
    )
except ImportError:
    ProductionForecastService = None
StationLoadBalancingService = ProductionForecastService
CourseFireService = ProductionForecastService
KitchenPerformanceService = ProductionForecastService
from app.services.advanced_supply_chain_service import (
    AdvancedSupplyChainService as AutoPurchaseOrderService,
)
SupplierLeadTimeService = AutoPurchaseOrderService
InventoryCostingService = AutoPurchaseOrderService
CrossStoreBalancingService = AutoPurchaseOrderService
from app.services.financial_controls_service import (
    FinancialControlsService as PrimeCostService,
)
AbuseDetectionService = PrimeCostService
try:
    from app.services.advanced_crm_service import (
        AdvancedCRMService as GuestPreferencesService,
    )
except ImportError:
    GuestPreferencesService = None
CustomerLifetimeValueService = GuestPreferencesService
CustomerSegmentationService = GuestPreferencesService
VIPManagementService = GuestPreferencesService
PersonalizationService = GuestPreferencesService
from app.services.iot_service import (
    IoTService as IoTDeviceService,
)
TemperatureMonitoringService = IoTDeviceService
PourMeterService = IoTDeviceService
ScaleService = IoTDeviceService
from app.services.compliance_service import (
    ComplianceService as ImmutableAuditService,
)
FiscalArchiveService = ImmutableAuditService
NRAExportService = ImmutableAuditService
AgeVerificationService = ImmutableAuditService
from app.services.ai_automation_service import (
    AIAutomationService as AIModelService,
)
PredictionService = AIModelService
AutomationRuleService = AIModelService
MenuOptimizationService = AIModelService
StaffingRecommendationService = AIModelService
try:
    from app.services.legal_training_crisis_service import (
        LegalRiskService,
        TrainingService,
        CrisisManagementService
    )
except ImportError:
    LegalRiskService = None
    TrainingService = None
    CrisisManagementService = None
from app.services.platform_qr_service import (
    PlatformService,
    QRSelfServiceService
)

# Import V9 Schemas
from app.schemas.v9_schemas import *
from app.core.rate_limit import limiter

# Create main V9 router


