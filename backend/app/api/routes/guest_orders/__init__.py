"""Guest ordering routes - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.guest_orders.menu_tables import router as _menu_tables_router
from app.api.routes.guest_orders.orders_core import router as _orders_core_router
from app.api.routes.guest_orders.admin_stats import router as _admin_stats_router
from app.api.routes.guest_orders.payments import router as _payments_router
from app.api.routes.guest_orders.menu_admin import router as _menu_admin_router
from app.api.routes.guest_orders.upsell_direct import router as _upsell_direct_router

router.include_router(_menu_tables_router)
router.include_router(_orders_core_router)
router.include_router(_admin_stats_router)
router.include_router(_payments_router)
router.include_router(_menu_admin_router)
router.include_router(_upsell_direct_router)

# Re-export functions used by orders.py proxy endpoints
from app.api.routes.guest_orders.orders_core import get_table_orders
from app.api.routes.guest_orders.payments import get_table_payment_summary, pay_all_table_orders
