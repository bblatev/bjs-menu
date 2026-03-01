"""Bar routes - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.bar.dashboard_spillage import router as _dashboard_spillage_router
from app.api.routes.bar.recipes_inventory import router as _recipes_inventory_router
from app.api.routes.bar.cocktails_tracking import router as _cocktails_tracking_router

router.include_router(_dashboard_spillage_router)
router.include_router(_recipes_inventory_router)
router.include_router(_cocktails_tracking_router)
