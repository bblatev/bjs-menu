# BASELINE.md - BJS Menu System Baseline

> Generated: 2026-02-07 | Stack: FastAPI + Next.js 14 + SQLite (dev) / PostgreSQL (prod)
> **DO NOT BREAK** any behavior documented here without explicit approval.

---

## 1. System Overview

| Component | Technology | Port | PM2 Name |
|-----------|-----------|------|----------|
| Backend API | FastAPI (Python 3.11) | 8000 | bjs-menu-backend |
| Frontend | Next.js 14.2.35 (React 18) | 3010 | bjs-menu |
| Database | SQLite (dev) / PostgreSQL (prod) | N/A | N/A |
| Process Manager | PM2 | N/A | N/A |

### Key Dependencies
- **Backend:** FastAPI, SQLAlchemy, Alembic, bcrypt, PyJWT, SlowAPI, Stripe SDK
- **Frontend:** React 18.2, TanStack Query 5, Zustand 4, Framer Motion, i18next, Tailwind CSS 3, Axios

---

## 2. Database Baseline

**Total Tables:** 136
**Tables with Data:** 1 (alembic_version only - all demo data cleared)
**Migration Version:** Current (all 22 migrations applied)

### Core Tables (All exist, all empty - ready for production data)

| Domain | Tables | Count |
|--------|--------|-------|
| Auth & Users | users, staff_users | 2 |
| Restaurant Ops | tables, subtables, checks, check_items, check_payments, kitchen_orders, kitchen_stations, waiter_calls, guest_orders, reservations, waitlist | 11 |
| Menu | menu_items, menu_categories, modifier_groups, modifier_options, menu_item_modifier_groups, combo_meals, combo_items, daily_menus, item_availability | 9 |
| Inventory/Stock | products, stock_items, stock_on_hand, stock_movements, inventory_batches, inventory_sessions, inventory_lines, inventory_count_sessions | 8 |
| Suppliers & PO | suppliers, purchase_orders, purchase_order_lines, invoices, invoice_lines | 5 |
| Customers | customers, customer_credits, customer_loyalty, customer_segments, customer_journey_events, customer_journey_funnels | 6 |
| Analytics | daily_metrics, sales_forecasts, menu_analysis, server_performance, benchmarks, conversational_queries | 6 |
| Financial | gl_codes, check_payments, price_lists, product_prices, budgets, daily_reconciliations, tax_filings | 7 |
| Staff | shifts, time_clock_entries, time_off_requests, tip_pools, tip_distributions, tip_pool_configurations, performance_goals, staff_performance_metrics | 8 |
| Bar | bar_tabs, kegs, tanks, bottle_weights, scale_readings | 5 |
| Delivery | delivery_orders, delivery_order_items, delivery_integrations, delivery_providers, delivery_platform_mappings, delivery_dispatches | 6 |
| Marketing | marketing_campaigns, campaign_recipients, loyalty_programs, gift_cards, gift_card_programs, gift_card_transactions | 6 |
| Operations | app_settings, notifications, notification_preferences, alert_configs, audit_log_entries, promotions, badges, challenges, risk_alerts | 9 |
| AI/ML | ai_photos, training_images, recognition_logs, product_feature_cache, ocr_jobs | 5 |
| Advanced | waste_tracking_entries, waste_forecasts, menu_experiments, menu_experiment_results, labor_forecasts, labor_compliance_rules, labor_compliance_violations, review_sentiments, wait_time_predictions, happy_hours | 10 |
| Other | locations, integrations, price_history, price_alerts, allergen_alerts, allergen_profiles, hotel_guests, guest_history, etc. | 33 |

---

## 3. API Endpoint Baseline

**Total Endpoints:** 1,277
**Total Paths:** 1,076
**Router Files:** 85

| Method | Count |
|--------|-------|
| GET | 659 |
| POST | 463 |
| PUT | 84 |
| DELETE | 58 |
| PATCH | 13 |

### Endpoint Health (as of baseline)
- **0 server errors (500s)** across all 659 GET endpoints
- **All endpoints return valid JSON responses**
- **Authentication:** PIN-based login via `/auth/login/pin`, JWT tokens

### Critical API Domains (DO NOT BREAK)

#### Core Operations
| Prefix | File | Endpoints | Status |
|--------|------|-----------|--------|
| `/auth` | auth.py | 5 | Working - PIN login, JWT tokens |
| `/tables` | guest_orders.py | 15+ | Working - CRUD, floor plan, subtables |
| `/orders` | guest_orders.py | 30+ | Working - Guest ordering, status, payment |
| `/kitchen-display` | kitchen_display.py | 3 | Working - KDS tickets by station |
| `/kitchen` | kitchen.py | 35+ | Working - Stations, tickets, automation |
| `/waiter` | waiter.py | 20+ | Working - Checks, split bill, payments |
| `/menu-items` | guest_orders.py | 10+ | Working - Menu CRUD |
| `/menu` | menu_complete.py | 15+ | Working - Categories, modifiers, combos |

#### Inventory & Supply Chain
| Prefix | File | Endpoints | Status |
|--------|------|-----------|--------|
| `/stock` | stock.py | 30 | Working - Items, movements, counts, waste |
| `/stock-management` | stock_management.py | 24 | Working - Transfers, adjustments, AI scan |
| `/inventory` | inventory.py | 8 | Working - Sessions, reconciliation |
| `/inventory-complete` | inventory_complete.py | 29 | Working - Barcodes, batches, cycle counts |
| `/inventory-intelligence` | inventory_intelligence.py | 10 | Working - ABC analysis, turnover, COGS |
| `/suppliers` | suppliers.py | 6 | Working - CRUD, performance stats |
| `/purchase-orders` | purchase_orders.py | 8 | Working - PO lifecycle, 3-way matching |
| `/invoices` | invoices.py | 15+ | Working - OCR, GL codes, AP approval |
| `/recipes` | recipes.py | 8 | Working - BOM, costing |

#### Staff & HR
| Prefix | File | Endpoints | Status |
|--------|------|-----------|--------|
| `/staff` | staff.py | 23+ | Working - CRUD, time clock, scheduling |
| `/payroll` | payroll.py | 9 | Working - Generation, approval, payment |
| `/v5/shifts` | shifts.py | 6 | Working - Shift CRUD |

#### Financial & Reporting
| Prefix | File | Endpoints | Status |
|--------|------|-----------|--------|
| `/financial` | financial.py | 16 | Working - GL, reconciliation, budgets |
| `/analytics` | analytics.py | 20+ | Working - Dashboard, forecasting, menu eng. |
| `/reports` | reports.py | 20+ | Working - Sales, inventory, staff, financial |
| `/accounting-export` | accounting_export.py | 9 | Working - GL export, VAT, AtomS3 |

#### Customer & Marketing
| Prefix | File | Endpoints | Status |
|--------|------|-----------|--------|
| `/customers` | customers.py | 10+ | Working - CRUD, segments, credits |
| `/reservations` | reservations.py | 15+ | Working - Booking, waitlist, platforms |
| `/marketing` | marketing.py | 15+ | Working - Campaigns, segments, triggers |
| `/loyalty` | loyalty.py | 3 | Working - Program, members |
| `/delivery` | delivery.py | 20+ | Working - Multi-platform aggregation |

#### Integrations
| Prefix | File | Endpoints | Status |
|--------|------|-----------|--------|
| `/payments` | payments.py | 12 | Working - Stripe integration |
| `/quickbooks` | quickbooks.py | 17 | Working - QB Online sync |
| `/xero` | xero.py | 8 | Working - Xero sync |
| `/printers` | printers.py | 12 | Working - ESC/POS printers |

#### Bar
| Prefix | File | Endpoints | Status |
|--------|------|-----------|--------|
| `/bar` | bar.py | 21 | Working - Tabs, spillage, happy hours, kegs |

---

## 4. Frontend Page Baseline

**Total Pages:** 162
**All pages return HTTP 200**

### Page Categories

| Category | Pages | Status |
|----------|-------|--------|
| Core Operations (dashboard, orders, tables, kitchen) | 17 | Working - Real API |
| Menu Management | 8 | Working - Real API |
| Stock & Inventory | 14 | Working - Real API |
| Bar Management | 9 | Working - Real API |
| Staff Management | 7 | Working - Real API |
| Reports | 12 | Working - Real API |
| Reservations & Customers | 6 | Working - Real API |
| Analytics | 5 | Working - Real API |
| Settings | 16 | Working - Real API |
| Marketing & Loyalty | 11 | Working - Real API |
| Financial & Accounting | 8 | Working - Real API |
| Purchasing & Suppliers | 4 | Working - Real API |
| Recipes & Menu Engineering | 3 | Working - Real API |
| Integrations | 5 | Working - Real API |
| Special Features (kiosk, offline, cloud kitchen, etc.) | 37 | Working - Real API |

### Auth Flow
1. PIN-based login at `/login` -> POST `/auth/login/pin`
2. JWT token stored in `localStorage` as `access_token`
3. All API calls include `Authorization: Bearer <token>`
4. Venue ID stored in `localStorage` (defaults to venue_id=1)

### WebSocket Channels
- Waiter calls: `ws://localhost:8000/ws/waiter-calls`
- Kitchen updates: `ws://localhost:8000/ws/kitchen`
- Order updates: `ws://localhost:8000/ws/orders`
- Venue-specific: `ws://localhost:8000/ws/venue/{venue_id}`

---

## 5. Working Features (DO NOT BREAK List)

### Verified End-to-End Flows
1. **Order Pipeline:** Create guest order -> KDS ticket -> Status updates -> Payment (cash/card) -> Completion
2. **Split Bill:** 2-6 way even split with visual selection UI
3. **Menu Management:** Create categories -> Create items with station routing -> KDS receives by station
4. **Staff Time Clock:** Real API for clock in/out (replaced mock data)
5. **Training Mode:** Real API for session start/end (replaced simulated data)
6. **Table Management:** QR code generation, floor plan, subtables
7. **Payment Recording:** Status=paid updates payment_status, payment_method, paid_at in DB

### Key Architectural Patterns
- `DbSession = Annotated[Session, Depends(get_db)]` for all DB access
- `Body()` + `Query()` dual-binding for flexible endpoint params
- `Base.metadata.create_all()` on startup for SQLite dev mode
- Alembic migrations for schema versioning
- PM2 for process management with auto-restart

---

## 6. Configuration

### Environment Variables (.env)
```
SECRET_KEY=<jwt-signing-key>
DATABASE_URL=sqlite:///./data/bjsbar.db  (dev)
CORS_ORIGINS=http://localhost:3000,http://localhost:3010
DEBUG=true
ACCESS_TOKEN_EXPIRE_MINUTES=1440
TIMEZONE=Europe/Sofia
AI_V2_ENABLED=false
RATE_LIMIT_ENABLED=true
```

### Frontend Environment
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## 7. Known Limitations (Baseline)

1. **No auth enforcement** - Most endpoints work without authentication
2. **Empty database** - All tables exist but contain no data (demo data cleared)
3. **SQLite in dev** - Some features (JSON queries, concurrent writes) limited
4. **Stub endpoints** - ~28 endpoints return hardcoded empty data
5. **No HTTPS** - Running on HTTP only
6. **Debug mode on** - Verbose error output enabled
7. **No CI/CD** - Manual deployment only
8. **No tests** - Test directory exists but no comprehensive test suite
