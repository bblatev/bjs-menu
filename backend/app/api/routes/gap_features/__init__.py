"""Gap features routes - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.gap_features.mobile_push_dev import router as _mobile_push_dev_router
from app.api.routes.gap_features.marketplace_integrations import router as _marketplace_integrations_router
from app.api.routes.gap_features.chat_labor_experiments import router as _chat_labor_experiments_router

router.include_router(_mobile_push_dev_router)
router.include_router(_marketplace_integrations_router)
router.include_router(_chat_labor_experiments_router)
