"""API routes."""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

# Core imports (these must work)
from app.api.routes import (
    auth, suppliers, products, locations, inventory, orders,
    pos, recipes, ai, sync, reports, reconciliation,
    invoices, marketing, reservations, delivery, analytics,
    advanced_features, kitchen, kitchen_alerts,
    tables, waiter, menu_engineering,
    enterprise, inventory_hardware, guest_orders, staff, customers,
    price_lists, purchase_orders, menu_complete_features,
    bar, financial, loyalty, vip, tax, shifts, payroll,
    audit_logs, benchmarking, price_tracker, referrals, haccp, warehouses,
    gift_cards, feedback, notifications, settings, integrations,
    fiscal, accounting_export, biometric,
    payments, quickbooks, printers,
    google_reserve, training, scheduled_reports, email_campaigns,
    opentable, birthday_rewards, kds_localization,
    mobile_wallet, custom_reports, card_terminals,
    stock,
    inventory_intelligence, xero,
    risk_alerts, roles, voice,
    promotions, gamification,
    fiscal_printers, pos_fiscal_bridge, cloud_kitchen,
    menu, auto_reorder,
    auto_86, stock_forecasting, invoice_capture,
)

api_router = APIRouter()

# Guest/Customer Ordering - mounted WITHOUT prefix and BEFORE orders.router.
# IMPORTANT: guest_orders defines /orders/{id}/status (kitchen order status) which
# shadows orders.router's /{id}/status (purchase order status). This is intentional:
# - Kitchen/guest order status: handled here via /orders/{id}/status
# - Purchase order status: handled via /purchase-orders/{id}/approve (no conflict)
# DO NOT reorder or add a prefix without updating the frontend.
api_router.include_router(guest_orders.router, tags=["guest-ordering", "menu"])

# Core routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(products.router, prefix="/products", tags=["products", "stock"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(pos.router, prefix="/pos", tags=["pos"])
api_router.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(reconciliation.router, prefix="/reconciliation", tags=["reconciliation"])
# Note: /reports-enhanced backward-compat removed — no frontend usage found

# New competitor-matching routes
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices", "ap-automation"])
api_router.include_router(marketing.router, prefix="/marketing", tags=["marketing", "loyalty", "campaigns"])
api_router.include_router(reservations.router, prefix="/reservations", tags=["reservations", "waitlist"])
api_router.include_router(delivery.router, prefix="/delivery", tags=["delivery", "doordash", "ubereats"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics", "ai-insights", "scale"])

# Waitlist direct access (alias for /reservations/waitlist for frontend compatibility)
from app.api.routes import waitlist as waitlist_router
api_router.include_router(waitlist_router.router, prefix="/waitlist", tags=["waitlist"])

# Advanced competitor features (25 feature areas)
api_router.include_router(advanced_features.router, tags=["advanced-features"])

# Kitchen and Tables
api_router.include_router(kitchen.router, prefix="/kitchen", tags=["kitchen", "kds"])
api_router.include_router(kitchen_alerts.router, prefix="/kitchen-alerts", tags=["kitchen", "kds"])
api_router.include_router(tables.router, prefix="/tables", tags=["tables", "floor-plan"])

# Waiter Terminal
api_router.include_router(waiter.router, prefix="/waiter", tags=["waiter", "pos-terminal"])

# Menu Engineering
api_router.include_router(menu_engineering.router, prefix="/menu-engineering", tags=["menu-engineering"])

# Enterprise Features
api_router.include_router(enterprise.router, prefix="/enterprise", tags=["enterprise", "integrations", "throttling", "hotel-pms", "offline", "mobile-app", "invoice-ocr"])

# Inventory Hardware (kegs, tanks, RFID)
api_router.include_router(inventory_hardware.router, prefix="/inventory-hardware", tags=["inventory-hardware", "kegs", "tanks", "rfid"])

# Staff Management (staff, shifts, time-clock, performance, tips)
api_router.include_router(staff.router, tags=["staff", "schedules", "time-clock", "performance", "tips"])

# Customer Management (CRM)
api_router.include_router(customers.router, tags=["customers", "crm"])

# Price Lists, Daily Menus, Manager Alerts (TouchSale gap features)
api_router.include_router(price_lists.router, tags=["price-lists", "daily-menu", "alerts"])

# Menu Complete (variants, tags, combos, upsells, LTOs, 86'd items, digital boards)
# menu_complete.py removed -- merged into menu_complete_features.py
api_router.include_router(menu_complete_features.router, prefix="/menu-complete", tags=["menu-complete", "variants", "tags", "combos"])
# Note: /menu-complete-features backward-compat removed — no frontend usage found

# Purchase Orders Management (PO, GRN, invoices, approvals, three-way matching)
api_router.include_router(purchase_orders.router, prefix="/purchase-orders", tags=["purchase-orders", "procurement", "grn", "three-way-match"])

# Bar Management
api_router.include_router(bar.router, prefix="/bar", tags=["bar", "drinks", "spillage"])

# Financial & Budgets
api_router.include_router(financial.router, prefix="/financial", tags=["financial", "budgets"])
# Note: /financial-endpoints backward-compat removed — no frontend usage found

# Loyalty & Gift Cards
api_router.include_router(loyalty.router, prefix="/loyalty", tags=["loyalty"])
api_router.include_router(gift_cards.router, prefix="/gift-cards", tags=["gift-cards"])

# VIP Management
api_router.include_router(vip.router, prefix="/vip", tags=["vip", "customers"])

# Tax Management
api_router.include_router(tax.router, prefix="/tax", tags=["tax", "filings"])

# Shifts (v5 compatibility)
api_router.include_router(shifts.router, prefix="/v5", tags=["shifts", "scheduling"])

# Payroll
api_router.include_router(payroll.router, prefix="/payroll", tags=["payroll"])

# Audit Logs
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit", "logs"])

# Benchmarking
api_router.include_router(benchmarking.router, prefix="/benchmarking", tags=["benchmarking", "benchmarking-v5"])

# Price Tracker
api_router.include_router(price_tracker.router, prefix="/price-tracker", tags=["price-tracker", "alerts"])

# Referrals
api_router.include_router(referrals.router, prefix="/referrals", tags=["referrals"])

# HACCP / Food Safety
api_router.include_router(haccp.router, prefix="/haccp", tags=["haccp", "food-safety"])

# Warehouses
api_router.include_router(warehouses.router, prefix="/warehouses", tags=["warehouses", "storage"])

# Feedback & Reviews
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback", "reviews"])

# Notifications
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

# Settings
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])

# Integrations
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])

# Bulgarian Fiscal Device (NRA compliance)
api_router.include_router(fiscal.router, prefix="/fiscal", tags=["fiscal", "nra", "bulgaria"])

# Bulgarian Accounting Export (AtomS3, etc.)
api_router.include_router(accounting_export.router, prefix="/accounting-export", tags=["accounting", "atoms3", "export"])

# Biometric & Card Reader Access Control
api_router.include_router(biometric.router, prefix="/biometric", tags=["biometric", "fingerprint", "card-reader", "access-control"])

# Payment Processing (Stripe)
api_router.include_router(payments.router, prefix="/payments", tags=["payments", "stripe", "refunds"])

# QuickBooks Integration
api_router.include_router(quickbooks.router, prefix="/quickbooks", tags=["quickbooks", "accounting", "sync"])

# Receipt Printers (ESC/POS)
api_router.include_router(printers.router, prefix="/printers", tags=["printers", "receipts", "esc-pos"])

# Google Reserve Integration
api_router.include_router(google_reserve.router, prefix="/google-reserve", tags=["google-reserve", "maps-booking"])
# Note: /google-booking backward-compat removed — no frontend usage found

# Training/Sandbox Mode
api_router.include_router(training.router, prefix="/training", tags=["training", "sandbox", "practice"])

# Scheduled Reports
api_router.include_router(scheduled_reports.router, prefix="/scheduled-reports", tags=["scheduled-reports", "automation"])

# Email Campaign Builder
api_router.include_router(email_campaigns.router, prefix="/email-campaigns", tags=["email-campaigns", "marketing", "templates"])

# OpenTable Integration
api_router.include_router(opentable.router, prefix="/opentable", tags=["opentable", "reservations", "integrations"])

# Birthday & Anniversary Auto-Rewards
api_router.include_router(birthday_rewards.router, prefix="/birthday-rewards", tags=["birthday-rewards", "loyalty", "automation"])

# KDS Localization (Multilingual Kitchen Display)
api_router.include_router(kds_localization.router, prefix="/kds-localization", tags=["kds", "localization", "multilingual"])

# Mobile Wallet (Apple Pay, Google Pay)
api_router.include_router(mobile_wallet.router, prefix="/mobile-wallet", tags=["mobile-wallet", "apple-pay", "google-pay"])

# Custom Report Builder
api_router.include_router(custom_reports.router, prefix="/custom-reports", tags=["custom-reports", "report-builder", "analytics"])

# EMV Card Terminals
api_router.include_router(card_terminals.router, prefix="/card-terminals", tags=["card-terminals", "emv", "stripe-terminal"])

# Stock routes (canonical prefix)
api_router.include_router(stock.router, prefix="/stock", tags=["stock", "inventory"])

# Inventory Complete - stock.router at legacy prefix used by frontend
api_router.include_router(stock.router, prefix="/inventory-complete", tags=["inventory-complete", "stock"])

# Inventory Intelligence (ABC Analysis, Turnover, Dead Stock, COGS, Food Cost Variance, EOQ, Snapshots, Cycle Counts)
api_router.include_router(inventory_intelligence.router, prefix="/inventory-intelligence", tags=["inventory-intelligence", "abc-analysis", "turnover", "cogs", "eoq"])

# Xero Accounting Integration
api_router.include_router(xero.router, prefix="/xero", tags=["xero", "accounting", "integration"])

# Risk Alerts / Fraud Detection
api_router.include_router(risk_alerts.router, prefix="/risk-alerts", tags=["risk-alerts", "fraud-detection"])

# Roles Management
api_router.include_router(roles.router, prefix="/roles", tags=["roles", "permissions"])

# Voice Assistant
api_router.include_router(voice.router, prefix="/voice", tags=["voice", "assistant"])

# Promotions
api_router.include_router(promotions.router, prefix="/promotions", tags=["promotions"])

# Gamification
api_router.include_router(gamification.router, prefix="/gamification", tags=["gamification", "badges", "challenges"])

# Fiscal Printers
api_router.include_router(fiscal_printers.router, prefix="/fiscal-printers", tags=["fiscal-printers", "nra"])

# POS Fiscal Bridge
api_router.include_router(pos_fiscal_bridge.router, prefix="/pos-fiscal-bridge", tags=["pos-fiscal-bridge", "fiscal"])

# Cloud Kitchen / Delivery v6
api_router.include_router(cloud_kitchen.router, prefix="/v6", tags=["cloud-kitchen", "delivery", "drive-thru"])

# Menu (frontend-facing /menu/* endpoints: modifiers, combos, allergens, scheduling, inventory)
api_router.include_router(menu.router, prefix="/menu", tags=["menu", "modifiers", "combos", "allergens"])

# Auto-Reorder (frontend-facing /auto-reorder/* endpoints)
api_router.include_router(auto_reorder.router, prefix="/auto-reorder", tags=["auto-reorder", "inventory"])

# Auto-86 (automatic menu item 86/un-86 based on stock levels)
api_router.include_router(auto_86.router, prefix="/auto-86", tags=["auto-86", "menu", "stock"])

# Stock Forecasting (predictive demand forecasting, EOQ, reorder suggestions)
api_router.include_router(stock_forecasting.router, prefix="/stock-forecasting", tags=["stock-forecasting", "demand", "eoq"])

# Invoice Capture (OCR-based invoice processing and PO generation)
api_router.include_router(invoice_capture.router, prefix="/invoice-capture", tags=["invoice-capture", "ocr", "ap-automation"])

# Multi-location v3.1 (reuse locations router)
api_router.include_router(locations.router, prefix="/v3.1/locations", tags=["locations", "multi-location", "v3.1"])

# ============================================================================
# PORTED FROM platform.zver.ai (graceful loading - skip if dependencies missing)
# ============================================================================

_ported_modules = [
    ("bulgarian_payments", "/bulgarian-payments", ["bulgarian-payments", "borica", "epay"]),
    ("crypto_payments", "/crypto-payments", ["crypto", "payments"]),
    ("split_bills", "/split-bills", ["split-bills", "payments"]),
    ("cash_drawers", "/cash-drawers", ["cash-drawers", "pos"]),
    ("house_accounts", "/house-accounts", ["house-accounts"]),
    ("held_orders", "/held-orders", ["held-orders"]),
    ("currency", "/currency", ["currency", "exchange"]),
    ("hardware_bnpl", "/hardware-bnpl", ["bnpl", "klarna", "affirm"]),
    ("auto_discounts", "/auto-discounts", ["auto-discounts", "pricing"]),
    # financial_endpoints removed — merged into financial.py
    ("menu_admin", "/menu-admin", ["menu", "admin"]),
    ("menu_advanced", "/menu-advanced", ["menu", "advanced"]),
    # menu_complete_features removed — promoted to core import; mounted at /menu-complete
    ("combos", "/combos", ["combos", "menu"]),
    ("customer_self_ordering", "/self-order", ["self-order", "qr"]),
    ("drive_thru", "/drive-thru", ["drive-thru"]),
    ("telephone_integration", "/telephone", ["telephone", "phone-orders"]),
    ("table_merges", "/table-merges", ["tables", "merge"]),
    ("table_sessions", "/table-sessions", ["tables", "sessions"]),
    ("tabs", "/tabs", ["tabs", "bar"]),
    ("barcode_labels", "/barcode-labels", ["barcode", "labels", "printing"]),
    ("batches", "/batches", ["batches", "inventory"]),
    ("serial_batch", "/serial-batch", ["serial", "batch", "tracking"]),
    # enhanced_inventory_endpoints removed — ~29% duplicated stock/recipes/warehouses;
    # unique endpoints merged into menu.py, recipes.py, suppliers.py,
    # purchase_orders.py, and warehouses.py.  Backward-compat mounts below.
    # inventory_complete_features removed — merged into stock.py
    ("inventory_reports", "/inventory-reports", ["inventory", "reports"]),
    ("mobile_scanner", "/mobile-scanner", ["mobile", "scanner", "barcode"]),
    ("production", "/production", ["production", "kitchen"]),
    ("production_features", "/production-features", ["production", "features"]),
    ("purchase_order_advanced", "/purchase-order-advanced", ["purchase-orders", "advanced"]),
    # enterprise_features removed — merged into enterprise.py; backward-compat mount below
    ("external_integrations", "/external-integrations", ["integrations", "external"]),
    # google_booking removed — merged into google_reserve.py
    ("datecs", "/datecs", ["datecs", "fiscal"]),
    ("erpnet_fp", "/erpnet-fp", ["erpnet", "fiscal"]),
    ("multi_terminal", "/multi-terminal", ["multi-terminal", "pos"]),
    ("waiter_terminal", "/waiter-terminal", ["waiter", "terminal"]),
    ("delivery_platforms", "/delivery-platforms", ["delivery", "ubereats", "doordash"]),
    # reports_enhanced removed -- merged into reports.py
    ("report_export", "/report-export", ["reports", "export"]),
    ("ratings", "/ratings", ["ratings", "reviews"]),
    ("messaging", "/messaging", ["messaging", "internal"]),
    ("sms_alerts", "/sms-alerts", ["sms", "alerts"]),
    ("analytics_forecasting", "/analytics-forecasting", ["analytics", "forecasting"]),
    ("ai_assistant", "/ai-assistant", ["ai", "assistant"]),
    ("ai_recommendations", "/ai-recommendations", ["ai", "recommendations"]),
    # ai_training removed — merged into ai.py
    ("floor_plans", "/floor-plans", ["floor-plans", "tables"]),
    ("kiosk", "/kiosk", ["kiosk", "self-service"]),
    ("dynamic_pricing", "/dynamic-pricing", ["pricing", "dynamic"]),
    ("sustainability", "/sustainability", ["sustainability", "green"]),
    ("websocket_endpoints", "/ws-endpoints", ["websocket", "realtime"]),
    ("staff_advanced", "/staff-advanced", ["staff", "advanced"]),
    ("staff_scheduling_endpoints", "/staff-scheduling", ["staff", "scheduling"]),
    ("allergens", "/allergens", ["allergens", "nutrition"]),
    # bar_management removed — was 87% duplicate of bar.py
    ("competitor_features", "/competitor-features", ["competitor"]),
    ("competitor_menu_features", "/competitor-menu-features", ["competitor", "menu"]),
    ("crm_complete", "/crm", ["crm", "customers"]),
    ("gap_features", "/gap-features", ["gap-features", "enterprise"]),
    ("missing_features", "/missing-features", ["missing-features"]),
    ("v3_endpoints", "/v3", ["v3"]),
    ("v31_endpoints", "/v3.1-features", ["v3.1"]),
    ("v5_endpoints", "/v5-features", ["v5"]),
    ("v6_endpoints", "/v6-features", ["v6"]),
    ("v7_endpoints", "/v7", ["v7"]),
    ("v7_tier3_endpoints", "/v7-tier3", ["v7", "tier3"]),
    ("v9_endpoints", "/v9", ["v9", "advanced"]),
    # v9_endpoints_part2 merged into v9_endpoints — backward-compat mount below
    ("admin", "/admin", ["admin", "tables"]),
    ("waiter_calls", "/waiter-calls", ["waiter", "calls"]),
    # --- Gap-closing modules (Payment, Table, Integration, Hardware) ---
    ("paypal", "/paypal", ["paypal", "payments"]),
    ("square", "/square", ["square", "payments"]),
    ("table_enhancements", "/table-enhancements", ["tables", "enhancements"]),
    ("automation", "/automation", ["automation", "zapier", "make"]),
    ("whatsapp", "/whatsapp", ["whatsapp", "messaging"]),
    ("supplier_portal", "/supplier-portal", ["suppliers", "portal"]),
    ("label_printers", "/label-printers", ["labels", "printers", "zpl"]),
    ("customer_displays", "/customer-displays", ["displays", "pole-display", "second-screen"]),
]

_loaded = 0
_failed = 0
for _module_name, _prefix, _tags in _ported_modules:
    try:
        import importlib
        _mod = importlib.import_module(f"app.api.routes.{_module_name}")
        api_router.include_router(_mod.router, prefix=_prefix, tags=_tags)
        _loaded += 1
    except Exception as e:
        _failed += 1
        logger.warning(f"Skipped ported module {_module_name}: {e}")

logger.info(f"Ported modules: {_loaded} loaded, {_failed} skipped")

# Note: /v9-part2, /ai-training, /enterprise-features backward-compat removed — no frontend usage found

# Note: /enhanced-inventory backward-compat removed — no frontend usage found

# ============================================================================
# V99 NEW FEATURE ROUTES
# ============================================================================

_v99_modules = [
    ("prep_lists", "/prep-lists", ["prep-lists", "kitchen", "ai"]),
    ("iot", "/iot", ["iot", "sensors", "temperature"]),
    ("multi_tenant", "/admin/tenants", ["admin", "tenants", "multi-tenant"]),
    ("mobile_api", "/mobile", ["mobile", "app"]),
    ("signage", "/signage", ["signage", "digital-displays"]),
    ("shelf_life", "/inventory/shelf-life", ["inventory", "shelf-life"]),
    ("shift_swap", "/staff/shift-swaps", ["staff", "shift-swap"]),
    ("social_content", "/marketing/social-content", ["marketing", "social"]),
]

for _module_name, _prefix, _tags in _v99_modules:
    try:
        import importlib
        _mod = importlib.import_module(f"app.api.routes.{_module_name}")
        api_router.include_router(_mod.router, prefix=_prefix, tags=_tags)
        logger.info(f"V99 module loaded: {_module_name}")
    except Exception as e:
        logger.warning(f"V99 module {_module_name} skipped: {e}")
