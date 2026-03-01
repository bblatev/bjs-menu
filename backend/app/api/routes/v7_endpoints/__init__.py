"""V7 API Endpoints - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter(tags=["V7 Features"])

from app.api.routes.v7_endpoints.deposits_sms import router as _deposits_sms_router
from app.api.routes.v7_endpoints.catering_displays import router as _catering_displays_router
from app.api.routes.v7_endpoints.reviews_preptime import router as _reviews_preptime_router
from app.api.routes.v7_endpoints.promo_referral import router as _promo_referral_router
from app.api.routes.v7_endpoints.rfm_price_tracker import router as _rfm_price_tracker_router
from app.api.routes.v7_endpoints.breaks_shifts_vip import router as _breaks_shifts_vip_router

router.include_router(_deposits_sms_router)
router.include_router(_catering_displays_router)
router.include_router(_reviews_preptime_router)
router.include_router(_promo_referral_router)
router.include_router(_rfm_price_tracker_router)
router.include_router(_breaks_shifts_vip_router)
