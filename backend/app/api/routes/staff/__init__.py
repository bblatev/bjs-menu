"""Staff routes - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.staff.crud_schedules import router as _crud_schedules_router
from app.api.routes.staff.timeclock_performance import router as _timeclock_performance_router
from app.api.routes.staff.advanced_features import router as _advanced_features_router

router.include_router(_crud_schedules_router)
router.include_router(_timeclock_performance_router)
router.include_router(_advanced_features_router)
