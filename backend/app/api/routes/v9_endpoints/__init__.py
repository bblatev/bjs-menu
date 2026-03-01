"""V9 API Endpoints - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.v9_endpoints.operations import router as _operations_router
from app.api.routes.v9_endpoints.kitchen_supply import router as _kitchen_supply_router
from app.api.routes.v9_endpoints.financial_crm import router as _financial_crm_router
from app.api.routes.v9_endpoints.iot_compliance import router as _iot_compliance_router
from app.api.routes.v9_endpoints.ai_legal_platform import router as _ai_legal_platform_router

router.include_router(_operations_router)
router.include_router(_kitchen_supply_router)
router.include_router(_financial_crm_router)
router.include_router(_iot_compliance_router)
router.include_router(_ai_legal_platform_router)
