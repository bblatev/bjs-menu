"""Enterprise routes - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.enterprise.locations_integrations import router as _locations_integrations_router
from app.api.routes.enterprise.hotel_offline_mobile import router as _hotel_offline_mobile_router
from app.api.routes.enterprise.marketplace_advanced import router as _marketplace_advanced_router

router.include_router(_locations_integrations_router)
router.include_router(_hotel_offline_mobile_router)
router.include_router(_marketplace_advanced_router)
