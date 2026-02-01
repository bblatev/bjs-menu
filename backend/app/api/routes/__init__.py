"""API routes."""

from fastapi import APIRouter

from app.api.routes import (
    auth, suppliers, products, locations, inventory, orders,
    pos, recipes, ai, sync, reports, reconciliation,
    invoices, marketing, reservations, delivery, analytics,
    advanced_features, kitchen, tables, waiter, menu_engineering,
    enterprise, inventory_hardware, guest_orders, staff, customers,
    price_lists, menu_complete
)

api_router = APIRouter()

# Core routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(products.router, prefix="/stock", tags=["stock"])  # Alias for mobile app
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(pos.router, prefix="/pos", tags=["pos"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(reconciliation.router, prefix="/reconciliation", tags=["reconciliation"])

# New competitor-matching routes
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices", "ap-automation"])
api_router.include_router(marketing.router, prefix="/marketing", tags=["marketing", "loyalty", "campaigns"])
api_router.include_router(reservations.router, prefix="/reservations", tags=["reservations", "waitlist"])
api_router.include_router(delivery.router, prefix="/delivery", tags=["delivery", "doordash", "ubereats"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics", "ai-insights", "scale"])

# Waitlist direct access (also available under /reservations/waitlist)
from app.api.routes import waitlist as waitlist_router
api_router.include_router(waitlist_router.router, prefix="/waitlist", tags=["waitlist"])

# Advanced competitor features (25 feature areas)
api_router.include_router(advanced_features.router, tags=["advanced-features"])

# Kitchen and Tables
api_router.include_router(kitchen.router, prefix="/kitchen", tags=["kitchen", "kds"])
api_router.include_router(kitchen.router, prefix="/kitchen-display", tags=["kitchen-display"])
api_router.include_router(kitchen.router, prefix="/kitchen-alerts", tags=["kitchen-alerts"])
api_router.include_router(tables.router, prefix="/tables", tags=["tables", "floor-plan"])

# Waiter Terminal
api_router.include_router(waiter.router, prefix="/waiter", tags=["waiter", "pos-terminal"])

# Menu Engineering
api_router.include_router(menu_engineering.router, prefix="/menu-engineering", tags=["menu-engineering"])

# Enterprise Features
api_router.include_router(enterprise.router, prefix="/enterprise", tags=["enterprise", "integrations", "throttling", "hotel-pms", "offline", "mobile-app", "invoice-ocr"])

# Inventory Hardware (kegs, tanks, RFID)
api_router.include_router(inventory_hardware.router, prefix="/inventory-hardware", tags=["inventory-hardware", "kegs", "tanks", "rfid"])

# Guest/Customer Ordering (no auth required)
api_router.include_router(guest_orders.router, tags=["guest-ordering", "menu"])

# Staff Management (staff, shifts, time-clock, performance, tips)
api_router.include_router(staff.router, tags=["staff", "schedules", "time-clock", "performance", "tips"])

# Customer Management (CRM)
api_router.include_router(customers.router, tags=["customers", "crm"])

# Price Lists, Daily Menus, Manager Alerts (TouchSale gap features)
api_router.include_router(price_lists.router, tags=["price-lists", "daily-menu", "alerts"])

# Menu Complete (variants, tags, combos, upsells, LTOs, 86'd items, digital boards)
api_router.include_router(menu_complete.router, tags=["menu-complete", "variants", "tags", "combos"])
