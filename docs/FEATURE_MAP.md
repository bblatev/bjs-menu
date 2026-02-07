# FEATURE_MAP.md - De-Duplication & Canonical Feature Registry

> Generated: 2026-02-07
> Purpose: Map all features, identify duplicates, assign canonical names, prevent feature sprawl

---

## 1. DUPLICATION OVERVIEW

| Severity | Domain | Duplicate Files | Lines of Code | Action |
|----------|--------|----------------|---------------|--------|
| CRITICAL | Inventory/Stock | 6 route files | 4,622 | Consolidate to 2 files |
| CRITICAL | Order Management | 4 route files | 4,134 | Namespace clearly |
| HIGH | Supplier Mgmt | 2 route files | 273 | Merge into 1 |
| HIGH | Menu Mgmt | 3 route files | 1,035 | Consolidate to 1+analytics |
| MEDIUM | Analytics | Scattered across 5+ | 2,000+ | Centralize |
| MEDIUM | Kitchen | 3 route files | 1,100+ | Consolidate |

---

## 2. CANONICAL FEATURE REGISTRY

### 2.1 ORDER MANAGEMENT

**These are DIFFERENT business flows, not duplicates. Keep separate but namespace clearly.**

| Canonical Name | Route Prefix | Model | File | Purpose |
|---------------|-------------|-------|------|---------|
| **Purchase Orders** | `/api/v1/purchase-orders` | PurchaseOrder | `purchase_orders.py` | Supplier procurement (B2B) |
| **Guest Orders** | `/api/v1/guest-orders` | GuestOrder | `guest_orders.py` | QR/table customer ordering (B2C self-service) |
| **Checks** | `/api/v1/waiter/checks` | Check | `waiter.py` | POS terminal / waiter ordering (B2C traditional) |
| **Kitchen Orders** | `/api/v1/kitchen` | KitchenOrder | `kitchen.py` | KDS routing and tracking |
| **Delivery Orders** | `/api/v1/delivery` | DeliveryOrder | `delivery.py` | Third-party delivery platforms |
| **Curbside Orders** | `/api/v1/curbside` | CurbsideOrder | `advanced_features.py` | Curbside pickup flow |

**De-dup Action:** `orders.py` currently handles PurchaseOrders at `/orders` prefix. Redirect `/orders` to `/purchase-orders` for clarity. Guest order endpoints in `guest_orders.py` at `/orders/*` sub-paths should move to `/guest-orders/*`.

---

### 2.2 INVENTORY & STOCK

**CRITICAL: 6 files with overlapping functionality. Consolidate to canonical structure.**

| Current File | Lines | Current Prefix | Canonical Mapping |
|-------------|-------|---------------|-------------------|
| `inventory.py` | 337 | `/inventory` | KEEP as `/inventory` (sessions, reconciliation) |
| `inventory_complete.py` | 1,130 | `/inventory-complete` | MERGE into `/inventory` (barcodes, batches, auto-reorder, cycle counts) |
| `inventory_intelligence.py` | 1,100 | `/inventory-intelligence` | KEEP as `/inventory/intelligence` (ABC, turnover, COGS, EOQ) |
| `inventory_hardware.py` | 640 | `/inventory/hardware` | KEEP as `/inventory/hardware` (kegs, tanks, RFID) |
| `stock.py` | 829 | `/stock` | MERGE overlapping parts into `/inventory` |
| `stock_management.py` | 1,196 | `/stock-management` | MERGE into `/inventory/stock` |

**Duplicate Endpoints to Merge:**

| Endpoint | Exists In | Canonical Location |
|----------|-----------|-------------------|
| GET stock items | stock.py, stock_management.py | `/inventory/stock` |
| GET stock movements | inventory.py, stock.py | `/inventory/movements` |
| GET stock alerts | inventory_complete.py, stock.py, stock_management.py | `/inventory/alerts` |
| GET stock batches | inventory_complete.py, stock.py | `/inventory/batches` |
| GET stock valuation | inventory_complete.py, stock.py, stock_management.py | `/inventory/valuation` |
| POST record waste | stock.py, stock_management.py | `/inventory/waste` |
| GET par levels | stock.py, stock_management.py | `/inventory/par-levels` |
| GET transfers | inventory.py, stock_management.py | `/inventory/transfers` |

**Migration Plan:**
1. Create canonical `/inventory` router that imports from sub-modules
2. Deprecate `/stock` and `/stock-management` prefixes (keep as aliases for 1 version)
3. Frontend: Update API_URL references from `/stock/*` to `/inventory/*`

---

### 2.3 SUPPLIER MANAGEMENT

| Current File | Lines | Prefix | Status |
|-------------|-------|--------|--------|
| `suppliers.py` | 70 | `/suppliers` | CANONICAL - CRUD + performance |
| `suppliers_v11.py` | 203 | `/v11/suppliers` | MERGE - contacts, ratings, price-lists |

**Merge Plan:** Move v11 features (contacts, ratings, price-lists) into `suppliers.py` as sub-routes:
- `/suppliers/{id}/contacts` (from v11)
- `/suppliers/{id}/ratings` (from v11)
- `/suppliers/{id}/price-lists` (from v11)
- DELETE `suppliers_v11.py`

---

### 2.4 MENU MANAGEMENT

| Current File | Lines | Prefix | Canonical Mapping |
|-------------|-------|--------|-------------------|
| `menu_complete.py` | 376 | `/menu` | CANONICAL - Items, categories, modifiers, combos |
| `menu_engineering.py` | 259 | `/menu-engineering` | KEEP - Analytics only |
| `guest_orders.py` | ~400 | `/menu-items`, `/menu/categories` | DUPLICATE - Merge into menu_complete |

**Duplicate Endpoints:**

| Endpoint | guest_orders.py | menu_complete.py | Action |
|----------|----------------|------------------|--------|
| GET /menu/items | list_menu_items() | get_inventory_items() | Keep menu_complete version |
| POST /menu/items | create_menu_item() | create_menu_item() | Keep menu_complete version |
| GET /menu/categories | list_menu_categories() | get_inventory_categories() | Keep menu_complete version |
| POST /menu/categories | create_menu_category() | N/A | Move to menu_complete |
| GET /menu/combos | list_combos() | list_combos() | Keep menu_complete version |

**Migration Plan:**
1. Move all menu CRUD from `guest_orders.py` to `menu_complete.py`
2. Keep `guest_orders.py` focused on: guest ordering, QR flow, payment, table management
3. Keep `menu_engineering.py` for analytics-only endpoints

---

### 2.5 KITCHEN MANAGEMENT

| Current File | Lines | Prefix | Canonical Mapping |
|-------------|-------|--------|-------------------|
| `kitchen.py` | 1,000+ | `/kitchen` | CANONICAL - All kitchen operations |
| `kitchen_display.py` | 50 | `/kitchen-display` | MERGE into `/kitchen/display` |
| `kitchen_alerts.py` | 80 | `/kitchen-alerts` | MERGE into `/kitchen/alerts` |

**Migration Plan:** Keep `kitchen.py` as main file, merge display and alerts as sub-modules.

---

### 2.6 ANALYTICS & REPORTING

| Current File | Prefix | Canonical Mapping |
|-------------|--------|-------------------|
| `analytics.py` | `/analytics` | CANONICAL for real-time analytics |
| `reports.py` | `/reports` | CANONICAL for historical reports |
| `menu_engineering.py` | `/menu-engineering` | Sub of `/analytics/menu` |
| `benchmarking.py` | `/benchmarking` | Sub of `/analytics/benchmarking` |

**Scattered Analytics to Centralize:**
- Menu analysis in `analytics.py` AND `menu_engineering.py` -> canonical: `/analytics/menu-engineering`
- Server performance in `analytics.py` -> canonical: `/analytics/server-performance`
- Sales forecasting in `analytics.py` -> canonical: `/analytics/forecasting`
- Theft detection in `analytics.py` -> canonical: `/analytics/risk`
- RFM segmentation in `analytics.py` -> canonical: `/analytics/rfm`

---

## 3. CANONICAL MODEL REGISTRY

### 3.1 Order-Related Models (Different, Not Duplicates)

| Model | Table | Purpose | Owner File |
|-------|-------|---------|-----------|
| PurchaseOrder | purchase_orders | Supplier procurement | `models/order.py` |
| GuestOrder | guest_orders | Customer self-service | `models/restaurant.py` |
| Check | checks | POS/waiter workflow | `models/restaurant.py` |
| KitchenOrder | kitchen_orders | KDS routing | `models/restaurant.py` |
| DeliveryOrder | delivery_orders | Platform delivery | `models/delivery.py` |
| CurbsideOrder | curbside_orders | Curbside pickup | `models/advanced_features.py` |

### 3.2 Inventory-Related Models (Some Overlap)

| Model | Table | Purpose | Status |
|-------|-------|---------|--------|
| Product | products | Master product catalog | CANONICAL |
| StockItem | stock_items | Legacy V99 reference | KEEP for POS sync |
| StockOnHand | stock_on_hand | Current levels per location | CANONICAL |
| StockMovement | stock_movements | All stock changes | CANONICAL |
| InventoryBatch | inventory_batches | Batch/lot tracking | CANONICAL |
| InventorySession | inventory_sessions | Count sessions | CANONICAL |
| InventoryCountSession | inventory_count_sessions | RFID count sessions | DIFFERENT from above |

### 3.3 User/Staff Models (Different, Not Duplicates)

| Model | Table | Purpose | Status |
|-------|-------|---------|--------|
| User | users | Auth/login accounts | CANONICAL for auth |
| StaffUser | staff_users | HR/staff management | CANONICAL for HR |

---

## 4. FRONTEND PAGE REGISTRY

### No Duplicate Pages Found
All 162 frontend pages serve distinct purposes. Key relationships:

| Page | Related Page | Relationship |
|------|-------------|-------------|
| `/table/[token]` | `/tables/qr` | Token page = guest-facing, QR page = admin QR generator |
| `/orders` | `/purchase-orders` | Different order types (guest vs supplier) |
| `/stock/*` (14 pages) | `/inventory-complete` | Different views of same data - align with canonical API |
| `/analytics/*` | `/rfm-analytics` | RFM is specialized analytics sub-feature |

### Frontend API URL Mapping Needed

| Current Frontend Call | Current Backend | Canonical Backend |
|----------------------|----------------|-------------------|
| `/stock/items` | stock.py (stub) | `/inventory/stock` |
| `/stock/transfers` | stock.py (stub) | `/inventory/transfers` |
| `/stock-management/*` | stock_management.py | `/inventory/stock/*` |
| `/menu-items` | guest_orders.py | `/menu/items` |
| `/menu/categories` | guest_orders.py | `/menu/categories` |

---

## 5. SERVICE LAYER CANONICAL MAPPING

| Current Service | Status | Canonical Service |
|----------------|--------|-------------------|
| `stock_deduction_service.py` (1500 lines) | Working | KEEP - refactor into smaller units |
| `reorder_service.py` | Working | KEEP under inventory domain |
| `order_service.py` | Working (exports) | KEEP - rename to `order_export_service.py` |
| `payroll_service.py` | Working | KEEP |
| `menu_engineering_service.py` | Partial | Complete implementation |
| `google_reserve_service.py` | Mock | Complete or remove |
| `notification_service.py` | Mock SMS | Complete with real provider |
| `custom_report_builder_service.py` | Incomplete | Complete or document as future |
| `delivery_service.py` | Stub | Complete or document as future |
| `pos/pos_adapter.py` | Abstract only | Implement CSV connector at minimum |

---

## 6. DE-DUPLICATION EXECUTION ORDER

### Phase 1: Route Namespace Cleanup (Safe, Non-Breaking)
1. Add alias routes so old paths redirect to new canonical paths
2. Update frontend to use canonical paths
3. Mark old paths as deprecated

### Phase 2: Supplier Merge (Quick Win)
1. Merge `suppliers_v11.py` features into `suppliers.py`
2. Delete `suppliers_v11.py`
3. Update frontend references

### Phase 3: Menu Consolidation
1. Move menu CRUD from `guest_orders.py` to `menu_complete.py`
2. Slim down `guest_orders.py` to guest-only operations
3. Update frontend references

### Phase 4: Kitchen Consolidation
1. Merge `kitchen_display.py` and `kitchen_alerts.py` into `kitchen.py`
2. Delete small files
3. Frontend already uses `/kitchen` prefix

### Phase 5: Inventory Consolidation (Largest Change)
1. Create `/inventory` master router importing sub-modules
2. Map all stock.py and stock_management.py endpoints to canonical paths
3. Keep old paths as aliases for backward compat
4. Update all 14 frontend stock pages
5. Eventually remove old route files

---

## 7. VERSIONED API ROUTES

| Current Route | Version | Purpose | Action |
|--------------|---------|---------|--------|
| `/v5/shifts` | v5 | Shift management | KEEP - migrate to `/shifts` |
| `/v5/staff` | v5 | Staff listing | DUPLICATE of `/staff` - REMOVE |
| `/v6/*` | v6 | Cloud kitchen | KEEP - migrate to `/cloud-kitchen` |
| `/v11/suppliers/*` | v11 | Extended suppliers | MERGE into `/suppliers` |

**Goal:** Eliminate version prefixes. All canonical routes under `/api/v1/`.
