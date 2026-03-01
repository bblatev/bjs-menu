"""Competitor features routes - split into domain-specific sub-modules."""
from fastapi import APIRouter

router = APIRouter()

from app.api.routes.competitor_features.menu_engineering_86 import router as _menu_engineering_86_router
from app.api.routes.competitor_features.auto_po_food_cost import router as _auto_po_food_cost_router
from app.api.routes.competitor_features.par_waste_recipes import router as _par_waste_recipes_router
from app.api.routes.competitor_features.invoices import router as _invoices_router

router.include_router(_menu_engineering_86_router)
router.include_router(_auto_po_food_cost_router)
router.include_router(_par_waste_recipes_router)
router.include_router(_invoices_router)
