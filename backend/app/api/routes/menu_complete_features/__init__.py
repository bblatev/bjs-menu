"""Menu complete features routes - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.menu_complete_features.variants_combos_tags import router as _variants_combos_tags_router
from app.api.routes.menu_complete_features.offers_86_boards import router as _offers_86_boards_router
from app.api.routes.menu_complete_features.qr_modifiers import router as _qr_modifiers_router

router.include_router(_variants_combos_tags_router)
router.include_router(_offers_86_boards_router)
router.include_router(_qr_modifiers_router)
