"""Stock routes - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.stock.items_movements import router as _items_movements_router
from app.api.routes.stock.valuation_waste_counts import router as _valuation_waste_counts_router
from app.api.routes.stock.import_export_dashboard import router as _import_export_dashboard_router
from app.api.routes.stock.shrinkage_cycles import router as _shrinkage_cycles_router
from app.api.routes.stock.management_ops import router as _management_ops_router
from app.api.routes.stock.advanced_analytics import router as _advanced_analytics_router

router.include_router(_items_movements_router)
router.include_router(_valuation_waste_counts_router)
router.include_router(_import_export_dashboard_router)
router.include_router(_shrinkage_cycles_router)
router.include_router(_management_ops_router)
router.include_router(_advanced_analytics_router)
