"""V5 API Endpoints - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter(tags=["V5 - Competitive Features"])

from app.api.routes.v5_endpoints.sms_catering import router as _sms_catering_router
from app.api.routes.v5_endpoints.benchmarking_deposits import router as _benchmarking_deposits_router
from app.api.routes.v5_endpoints.rfm_referral import router as _rfm_referral_router
from app.api.routes.v5_endpoints.staff_mgmt import router as _staff_mgmt_router
from app.api.routes.v5_endpoints.price_tracker_vip import router as _price_tracker_vip_router
from app.api.routes.v5_endpoints.charity_promo import router as _charity_promo_router
from app.api.routes.v5_endpoints.tax_chargebacks import router as _tax_chargebacks_router
from app.api.routes.v5_endpoints.pairings_blocks_display import router as _pairings_blocks_display_router

router.include_router(_sms_catering_router)
router.include_router(_benchmarking_deposits_router)
router.include_router(_rfm_referral_router)
router.include_router(_staff_mgmt_router)
router.include_router(_price_tracker_vip_router)
router.include_router(_charity_promo_router)
router.include_router(_tax_chargebacks_router)
router.include_router(_pairings_blocks_display_router)
