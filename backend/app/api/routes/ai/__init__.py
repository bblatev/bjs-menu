"""AI routes - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.ai.shelf_scan import router as _shelf_scan_router
from app.api.routes.ai.training import router as _training_router
from app.api.routes.ai.recognition import router as _recognition_router
from app.api.routes.ai.pipeline_v2 import router as _pipeline_v2_router

router.include_router(_shelf_scan_router)
router.include_router(_training_router)
router.include_router(_recognition_router)
router.include_router(_pipeline_v2_router)
