"""API routes."""

from fastapi import APIRouter

from app.api.routes import (
    auth, suppliers, products, locations, inventory, orders,
    pos, recipes, ai, sync, reports, reconciliation,
    invoices, marketing, reservations, delivery, analytics,
    advanced_features, kitchen, tables, waiter, menu_engineering,
    enterprise, inventory_hardware, guest_orders, staff, customers,
    price_lists, menu_complete, purchase_orders,
    bar, financial, loyalty, vip, tax, shifts, payroll,
    audit_logs, benchmarking, price_tracker, referrals, haccp, warehouses,
    gift_cards, feedback, notifications, settings, integrations,
    fiscal, accounting_export, biometric,
    payments, quickbooks, printers,
    google_reserve, training, scheduled_reports, email_campaigns,
    opentable, birthday_rewards, kds_localization,
    mobile_wallet, custom_reports, card_terminals,
    stock_management, stock, inventory_complete
)

api_router = APIRouter()

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

# Kitchen and Tables (multiple prefixes for frontend compatibility)
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

# Purchase Orders Management (PO, GRN, invoices, approvals, three-way matching)
api_router.include_router(purchase_orders.router, prefix="/purchase-orders", tags=["purchase-orders", "procurement", "grn", "three-way-match"])

# Bar Management
api_router.include_router(bar.router, prefix="/bar", tags=["bar", "drinks", "spillage"])

# Financial & Budgets
api_router.include_router(financial.router, prefix="/financial", tags=["financial", "budgets"])

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

# Stock Management (transfers, adjustments, shrinkage, AI scanner, cost tracking)
api_router.include_router(stock_management.router, prefix="/stock-management", tags=["stock-management", "transfers", "shrinkage", "ai-scanner", "cost-tracking"])

# Stock routes (frontend-facing /stock/* endpoints)
api_router.include_router(stock.router, prefix="/stock", tags=["stock", "inventory"])

# Inventory Complete (comprehensive inventory management for frontend)
api_router.include_router(inventory_complete.router, prefix="/inventory-complete", tags=["inventory-complete", "stock"])
