"""Kitchen routes - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.kitchen.tickets_orders import router as _tickets_orders_router
from app.api.routes.kitchen.workflow_display import router as _workflow_display_router
from app.api.routes.kitchen.localization_allergens import router as _localization_allergens_router

router.include_router(_tickets_orders_router)
router.include_router(_workflow_display_router)
router.include_router(_localization_allergens_router)
