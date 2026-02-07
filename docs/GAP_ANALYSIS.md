# GAP_ANALYSIS.md - Stubs, Security Issues, and Missing Functionality

> Generated: 2026-02-07 | Production Readiness: ~35%

---

## 1. CRITICAL SECURITY GAPS (P0)

### 1.1 No Authentication Enforcement
- **Severity:** CRITICAL
- **Scope:** ~1,270 endpoints, 0 have auth decorators applied
- **Details:** RBAC infrastructure exists (`rbac.py` defines RequireOwner, RequireManager, RequireStaff`) but is NOT applied to any endpoint
- **Impact:** All admin operations (menu changes, payments, staff management) are publicly accessible
- **Fix:** Add `Depends(get_current_user)` or role-specific deps to all non-guest endpoints

### 1.2 Exposed Credentials in .env
- **Severity:** CRITICAL
- **File:** `/opt/bjs-menu/backend/.env`
- **Details:** PostgreSQL credentials (`bjs:bjspassword`), JWT SECRET_KEY in plaintext
- **Fix:** Rotate all credentials, use secrets manager, add .env to .gitignore

### 1.3 Debug Mode Enabled
- **Severity:** CRITICAL
- **File:** `/opt/bjs-menu/backend/.env` line 6
- **Details:** `DEBUG=true` exposes stack traces, disables security checks
- **Fix:** Set `DEBUG=false` for production

### 1.4 Default Secret Key Fallback
- **Severity:** CRITICAL
- **File:** `/opt/bjs-menu/backend/app/core/config.py` line 36
- **Details:** `secret_key: str = "change-me-in-production"` - if env var missing, JWT tokens forged
- **Fix:** Crash on startup if SECRET_KEY not set in production

### 1.5 Unprotected Payment Endpoint
- **Severity:** HIGH
- **File:** `guest_orders.py:1365`
- **Details:** POST `/orders/{order_id}/payment` has no auth, accepts any payment
- **Fix:** Add auth + integrate real payment processor

---

## 2. HIGH SECURITY GAPS (P0-P1)

| ID | Issue | File:Line | Fix |
|----|-------|-----------|-----|
| S6 | No input validation on guest orders | guest_orders.py:558 | Add Pydantic schemas |
| S7 | CORS allows http:// origin in prod config | .env CORS_ORIGINS | HTTPS only in prod |
| S8 | No CSRF protection | main.py | Add CSRF middleware |
| S9 | Weak PIN space (4-6 digits = 6000 values) | security.py:40 | Add lockout + delay |
| S10 | No rate limiting beyond login (10/min) | auth.py:37 | Stricter limits + lockout |
| S11 | No HTTPS enforcement | main.py | Add HTTPS redirect middleware |
| S12 | No security headers | main.py | Add X-Frame-Options, CSP, HSTS |
| S13 | SQL injection risk in POS adapter | pos_adapter.py:704 | Fully parameterize queries |

---

## 3. STUB ENDPOINTS (Return Hardcoded/Empty Data)

### 3.1 Stock Module Stubs
**File:** `/opt/bjs-menu/backend/app/api/routes/stock.py` lines 47-79

| Endpoint | Returns | Should Query |
|----------|---------|-------------|
| GET `/stock/items` | `{"items": [], "total": 0}` | StockOnHand table |
| GET `/stock/transfers` | `{"transfers": [], "total": 0}` | StockMovement (transfer type) |
| GET `/stock/forecasting` | `{"forecasts": [], "recommendations": []}` | SalesForecast + WasteForecast |
| GET `/stock/forecasting/stats` | `{"accuracy": 0, "total_forecasts": 0}` | SalesForecast accuracy |
| GET `/stock/aging` | `{"items": [], "total_value": 0}` | InventoryBatch expiration dates |

### 3.2 Marketing Module Stubs
**File:** `/opt/bjs-menu/backend/app/api/routes/marketing.py` lines 29-46

| Endpoint | Returns | Should Query |
|----------|---------|-------------|
| GET `/marketing/promotions` | `{"promotions": [], "total": 0}` | Promotion table |
| GET `/marketing/stats` | `{"total_campaigns": 0, ...}` | MarketingCampaign aggregate |
| GET `/marketing/pricing-rules` | `{"rules": [], "total": 0}` | DynamicPricingRule table |

### 3.3 Analytics Module Stubs
**File:** `/opt/bjs-menu/backend/app/api/routes/analytics.py` lines 101-150

| Endpoint | Returns | Should Query |
|----------|---------|-------------|
| GET `/analytics/video` | `{"cameras": [], "status": "not_configured"}` | AppSetting (feature config) |
| GET `/analytics/theft` | Partial implementation | RiskAlert table |

### 3.4 Fiscal Printers Stub
**File:** `/opt/bjs-menu/backend/app/api/routes/fiscal_printers.py`

| Endpoint | Returns | Should Query |
|----------|---------|-------------|
| GET `/fiscal-printers/manufacturers` | `[]` | AppSetting or hardcoded BG fiscal list |
| GET `/fiscal-printers/devices` | `[]` | Integration table (fiscal type) |

### 3.5 Other Stubs

| File | Endpoint | Issue |
|------|----------|-------|
| `cloud_kitchen.py` | Multiple v6 endpoints | Returns empty/hardcoded |
| `suppliers_v11.py` | 8 v11 endpoints | Partially wired to DB |
| `kitchen_display.py` | GET `/tickets` | Returns `[]` stub |

---

## 4. INCOMPLETE SERVICE IMPLEMENTATIONS

### 4.1 Services with `pass` Bodies

| Service File | Lines | Issue |
|-------------|-------|-------|
| `pos/pos_adapter.py` | 205-249 | Abstract methods, no concrete implementations |
| `pos/connector_base.py` | 38-64 | Abstract base, no connectors implemented |
| `delivery_service.py` | 201, 359 | Empty `pass` in delivery logic |
| `custom_report_builder_service.py` | 298, 367 | Error handlers empty |

### 4.2 Services with Placeholder/Mock Logic

| Service File | Issue |
|-------------|-------|
| `google_reserve_service.py` | Returns mock responses (lines 146, 243) |
| `notification_service.py` | `_send_mock_sms()` instead of real Twilio |
| `advanced/waste_tracking.py` | "placeholder for actual AI integration" (line 275) |
| `payroll_service.py` | Sample data initialization removed but service logic thin |

### 4.3 ML Pipeline Mocks

| File | Issue |
|------|-------|
| `ml/inference/pipeline_v2.py` | Falls back to `_mock_detect()` and `_mock_classify()` when no YOLO model (lines 112, 153, 290, 491) |

---

## 5. MISSING FEATURES (Models Exist, No API/UI)

### 5.1 Models Without Complete API Coverage

| Model | Table | API Status |
|-------|-------|------------|
| CustomerJourneyEvent | customer_journey_events | No CRUD endpoints |
| CustomerJourneyFunnel | customer_journey_funnels | No CRUD endpoints |
| CrossSellRule | cross_sell_rules | No CRUD endpoints |
| CrossSellImpression | cross_sell_impressions | No CRUD endpoints |
| TableTurnForecast | table_turn_forecasts | No endpoints |
| TableTurnMetric | table_turn_metrics | No endpoints |
| SupplyChainTrace | supply_chain_traces | No endpoints |
| SustainabilityMetric | sustainability_metrics | No endpoints |
| ESGReport | esg_reports | No endpoints |
| VirtualBrand | virtual_brands | No endpoints |
| GuestWifiSession | guest_wifi_sessions | No endpoints |
| DynamicPriceAdjustment | dynamic_price_adjustments | No endpoints |
| PredictiveMaintenance | predictive_maintenance | No endpoints |
| EquipmentSensor | equipment_sensors | No endpoints |
| SensorReading | sensor_readings | No endpoints |
| StationLoadMetric | station_load_metrics | No endpoints |

### 5.2 Features Referenced but Not Implemented

| Feature | Evidence | Gap |
|---------|----------|-----|
| Biometric Auth | Routes + service skeleton exist | Not functional |
| Voice Ordering | Route exists | No speech-to-text integration |
| Video Analytics | Route returns stub | No camera integration |
| RFID Inventory | Models + route exist | No RFID hardware integration |
| Bluetooth Scale | Models exist | No BLE integration |
| Kiosk Mode | Frontend page exists | No dedicated kiosk backend |
| Offline Mode | Frontend page exists | Sync queue exists but untested |

---

## 6. DATA INTEGRITY GAPS

### 6.1 No Audit Logging
- AuditLogEntry model exists but is NOT used by any endpoint
- Payment transactions not logged
- Menu/price changes not logged
- Staff time modifications not logged

### 6.2 No Data Validation at DB Level
- Foreign keys defined in models but SQLite doesn't enforce them by default
- No CHECK constraints on critical fields (prices >= 0, quantities >= 0)
- JSON columns used for structured data without schema validation

### 6.3 Missing Cascade Rules
- Deleting a menu item doesn't cascade to order line items
- Deleting a staff member doesn't handle active shifts/time entries
- No soft-delete pattern implemented

---

## 7. INFRASTRUCTURE GAPS

| Gap | Current State | Production Requirement |
|-----|--------------|----------------------|
| Database | SQLite file | PostgreSQL with connection pooling |
| HTTPS | Not configured | TLS termination (nginx/certbot) |
| Secrets | Plaintext .env | Vault/AWS Secrets Manager |
| Logging | PM2 log files | Structured logging (JSON) + aggregation |
| Monitoring | None | Health checks, APM, alerting |
| Backups | None | Automated DB backups + retention |
| CI/CD | None | GitHub Actions / GitLab CI |
| Docker | None | docker-compose.prod.yml |
| Rate Limiting | Basic (SlowAPI) | Per-user + per-IP + endpoint-specific |
| Caching | None | Redis for sessions, frequently-accessed data |

---

## 8. TESTING GAPS

| Type | Current | Required |
|------|---------|----------|
| Unit Tests | Minimal (tests/ dir with mocks) | 80%+ coverage on services |
| Integration Tests | None | API endpoint tests with test DB |
| E2E Tests | None | Critical flow tests (order, payment, inventory) |
| Security Tests | None | Auth bypass, injection, CSRF tests |
| Load Tests | None | Concurrent user simulation |
| Contract Tests | None | OpenAPI spec validation |

---

## 9. GAP SUMMARY BY PRIORITY

### P0 - Must Fix Before Production
1. Add auth to all non-guest endpoints (1270 endpoints)
2. Rotate and secure all credentials
3. Disable debug mode
4. Enforce HTTPS
5. Add input validation on all POST/PUT endpoints
6. Fix SQL injection risk in POS adapter

### P1 - Must Fix Within First Sprint
1. Wire 28+ stub endpoints to real DB queries
2. Implement audit logging for critical operations
3. Add security headers
4. Implement CSRF protection
5. Add proper rate limiting
6. Complete payment processor integration

### P2 - Should Fix Before GA
1. Build complete API endpoints for 16 orphaned models
2. Implement proper error handling (replace `pass` blocks)
3. Add comprehensive test suite
4. Set up CI/CD pipeline
5. Implement data validation at DB level
6. Add monitoring and alerting

### P3 - Nice to Have
1. Implement advanced features (biometric, voice, video, RFID)
2. Add GDPR compliance endpoints
3. Implement data encryption at rest
4. Build comprehensive documentation
5. Add multi-language support for backend errors
