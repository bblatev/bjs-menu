"""Waiter terminal routes - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.waiter_terminal.orders_tabs import router as _orders_tabs_router
from app.api.routes.waiter_terminal.payments_voids import router as _payments_voids_router
from app.api.routes.waiter_terminal.floor_plan_menu import router as _floor_plan_menu_router

router.include_router(_orders_tabs_router)
router.include_router(_payments_voids_router)
router.include_router(_floor_plan_menu_router)
