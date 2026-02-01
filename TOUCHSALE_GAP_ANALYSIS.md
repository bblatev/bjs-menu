# TouchSale vs BJS Menu - Gap Analysis Report

## Executive Summary

This document provides a comprehensive analysis comparing UnrealSoft's TouchSale POS system with the BJS Menu project, identifying feature gaps and recommendations for implementation.

**Overall Finding**: BJS Menu is significantly more feature-rich than TouchSale, with modern capabilities like AI/ML, delivery integrations, and advanced analytics that TouchSale lacks. However, TouchSale has several Bulgarian market-specific features and operational conveniences that could enhance BJS Menu.

---

## 1. TouchSale Feature Inventory

### 1.1 Core POS Features
| Feature | TouchSale | BJS Menu | Gap? |
|---------|-----------|----------|------|
| TouchScreen POS terminals | Yes | Yes | No |
| Keyboard operation fallback | Yes | Partial | Minor |
| Multiple price lists per item | Yes | No | **YES** |
| Quick item search by name/code | Yes | Yes | No |
| "Most frequently sold" items list | Yes | Partial | Minor |
| "Recently used items" list | Yes | No | **YES** |
| Combo menus with add-ons | Yes | Yes | No |
| Modifiers/customizations | Yes | Yes | No |
| Happy Hour pricing | Yes | Yes | No |
| VIP client discounts | Yes | Yes | No |
| Menu of the Day | Yes | No | **YES** |

### 1.2 Order & Table Management
| Feature | TouchSale | BJS Menu | Gap? |
|---------|-----------|----------|------|
| Multi-terminal bill access | Yes | Yes | No |
| Table display with server names | Yes | Yes | No |
| Subtable management | Yes | No | **YES** |
| Quick order reordering | Yes | No | **YES** |
| Order comments/annotations | Yes | Yes | No |
| Request/Order workflow modes | Yes | No | **YES** |
| Account blocking | Yes | No | **YES** |
| Automatic logout after close | Yes | No | **YES** |

### 1.3 Kitchen Operations
| Feature | TouchSale | BJS Menu | Gap? |
|---------|-----------|----------|------|
| Kitchen display monitors | Yes | Yes | No |
| Multiple kitchen printers | Yes | Yes | No |
| Lunch menu monitoring | Yes | No | **YES** |
| Order ticket management | Yes | Yes | No |
| Recipe/ingredient control | Yes | Yes | No |

### 1.4 Payments & Fiscal
| Feature | TouchSale | BJS Menu | Gap? |
|---------|-----------|----------|------|
| Cash payments | Yes | Yes | No |
| Card payments | Yes | Yes | No |
| Mixed payments | Yes | Yes | No |
| Deferred payments | Yes | Partial | Minor |
| Bulgarian fiscal devices | Yes | No | **YES** |
| USN number generation | Yes | No | **YES** |
| QR code on receipts | Yes | No | **YES** |
| NRA real-time reporting | Yes | No | **YES** |
| Multi-station fiscal sharing | Yes | No | **YES** |
| Receipt reprinting | Yes | Yes | No |

### 1.5 Loyalty & Customer Cards
| Feature | TouchSale | BJS Menu | Gap? |
|---------|-----------|----------|------|
| Customer card integration | Yes | Yes | No |
| Accumulation points on cards | Yes | Partial | Minor |
| Point percentage redemption | Yes | Yes | No |
| Account limits by customer | Yes | No | **YES** |
| Customer payment history | Yes | Yes | No |

### 1.6 Reporting & Analytics
| Feature | TouchSale | BJS Menu | Gap? |
|---------|-----------|----------|------|
| Daily establishment reports | Yes | Yes | No |
| Personal operator reports | Yes | Partial | Minor |
| Service deduction reports | Yes | No | **YES** |
| Turnover at base prices | Yes | No | **YES** |
| Reversal/correction tracking | Yes | Yes | No |
| Chart & table visualizations | Yes | Yes | No |
| AtomS3 accounting export | Yes | No | **YES** |

### 1.7 Staff & Management
| Feature | TouchSale | BJS Menu | Gap? |
|---------|-----------|----------|------|
| Operator rights/permissions | Yes | Yes | No |
| Administrator authentication | Yes | Yes | No |
| Personnel data management | Yes | Yes | No |
| Real-time SMS alerts | Yes | No | **YES** |
| Manager remote control | Yes | Partial | Minor |

### 1.8 Mobile & Hardware
| Feature | TouchSale | BJS Menu | Gap? |
|---------|-----------|----------|------|
| MyWaiter mobile app | Yes | Yes | No |
| PocketPC handheld ordering | Yes | Yes | No |
| Offline synchronization | Yes | Yes | No |
| Fingerprint/card access | Yes | No | **YES** |
| Network printer config | Yes | Yes | No |

### 1.9 Integrations
| Feature | TouchSale | BJS Menu | Gap? |
|---------|-----------|----------|------|
| FourSeasons hotel PMS | Yes | Partial | Minor |
| External accounting export | Yes | Yes | No |
| Multi-location management | Yes | Yes | No |
| Reservation system | Yes | Yes | No |

---

## 2. Identified Gaps (TouchSale features missing in BJS Menu)

### 2.1 HIGH PRIORITY - Bulgarian Market Requirements

#### Gap 1: Bulgarian Fiscal Device Integration
**TouchSale Feature**: Full Bulgarian NRA compliance with real-time tax reporting
**Impact**: CRITICAL for Bulgarian market
**Requirements**:
- USN (Unique Sale Number) generation at transaction start
- QR code generation on fiscal receipts
- Real-time NRA (National Revenue Agency) data transmission
- Support for Bulgarian-approved fiscal printers (Datecs, Daisy, etc.)
- SUPTO declaration compliance
- Multi-station fiscal device sharing

**Implementation Estimate**: Backend fiscal service module + printer drivers

#### Gap 2: AtomS3/Bulgarian Accounting Export
**TouchSale Feature**: Export to AtomS3 accounting software
**Impact**: HIGH for Bulgarian businesses
**Requirements**:
- AtomS3 export format support
- Date handling specific to Bulgarian accounting
- GL code mapping for Bulgarian chart of accounts

### 2.2 MEDIUM PRIORITY - Operational Efficiency

#### Gap 3: Multiple Price Lists Per Item
**TouchSale Feature**: Same item can have different prices in different contexts
**Impact**: MEDIUM - Common for multi-channel restaurants
**Use Cases**:
- Dine-in vs Takeout pricing
- Happy Hour vs Regular pricing
- Delivery platform vs Direct pricing
- VIP vs Regular customer pricing
- Wholesale vs Retail pricing

**Implementation**:
```python
# New model: ProductPriceList
class ProductPriceList(Base):
    id: int
    product_id: int
    price_list_name: str  # "dine_in", "takeout", "delivery", "happy_hour", "vip"
    price: float
    start_time: Optional[time]
    end_time: Optional[time]
    days_of_week: Optional[str]  # JSON array
    is_active: bool
```

#### Gap 4: Menu of the Day
**TouchSale Feature**: Special daily menu with different pricing/availability
**Impact**: MEDIUM - Popular in European restaurants
**Requirements**:
- Daily specials creation
- Automatic menu rotation by day
- Different pricing for daily menu items
- Lunch menu printing (A5 format)
- Daily menu monitoring dashboard

**Implementation**:
```python
class DailyMenu(Base):
    id: int
    date: date
    name: str  # "Lunch Special", "Chef's Choice"
    items: JSON  # [{product_id, special_price, portion_size}]
    available_from: time
    available_until: time
    is_active: bool
```

#### Gap 5: Quick Order Reordering
**TouchSale Feature**: Quickly repeat a customer's previous order
**Impact**: MEDIUM - Improves service speed
**Requirements**:
- "Repeat Last Order" button on POS
- Customer order history quick access
- One-click reorder functionality

#### Gap 6: Recently Used Items List
**TouchSale Feature**: Quick access to recently ordered items per terminal/operator
**Impact**: MEDIUM - Speeds up order entry
**Requirements**:
- Track last N items ordered by operator
- Quick access panel on POS screen
- Configurable list size

#### Gap 7: Real-time SMS Notifications for Managers
**TouchSale Feature**: Instant SMS alerts for critical events
**Impact**: MEDIUM - Management oversight
**Alert Triggers**:
- Void/reversal transactions
- Large discounts applied
- Daily close completed
- Stock critical levels
- Cash drawer opened without sale

**Implementation**:
```python
class ManagerAlert(Base):
    id: int
    alert_type: str  # "void", "discount", "daily_close", "stock_critical"
    threshold: Optional[float]
    recipient_phone: str
    is_sms: bool
    is_email: bool
    is_push: bool
```

#### Gap 8: Subtable Management
**TouchSale Feature**: Split large tables into sub-sections
**Impact**: MEDIUM - Useful for banquets/large parties
**Requirements**:
- Create subtables under main table
- Separate checks per subtable
- Merge subtables back
- Track covers per subtable

#### Gap 9: Account Limits by Customer
**TouchSale Feature**: Set credit limits per customer account
**Impact**: MEDIUM - Credit management
**Requirements**:
- Per-customer credit limit
- Warning when approaching limit
- Block orders when limit exceeded
- Payment history tracking

### 2.3 LOW PRIORITY - Nice to Have

#### Gap 10: Automatic Logout After Account Close
**TouchSale Feature**: Auto-logout operator after closing bill
**Impact**: LOW - Security convenience
**Implementation**: Simple session timeout after close

#### Gap 11: Request/Order Workflow Modes
**TouchSale Feature**: Different workflows for different service styles
**Impact**: LOW - Specialty use case
**Modes**:
- Request mode: Items sent as requests, confirmed before kitchen
- Order mode: Direct to kitchen

#### Gap 12: Service Deduction Reports
**TouchSale Feature**: Operator reports with commission/service fee deductions
**Impact**: LOW - Specific to commission-based pay
**Requirements**:
- Commission percentage per operator
- Automatic deduction calculation
- Net earnings reports

#### Gap 13: Turnover at Base Prices
**TouchSale Feature**: Calculate revenue excluding markups
**Impact**: LOW - Specific accounting need
**Requirements**:
- Base price tracking per product
- Report showing turnover at base vs actual

#### Gap 14: Fingerprint/Card Reader Access Control
**TouchSale Feature**: Biometric login for operators
**Impact**: LOW - Hardware dependent
**Requirements**:
- Fingerprint reader integration
- Card reader integration
- Multi-factor authentication option

---

## 3. Features Where BJS Menu Exceeds TouchSale

BJS Menu has many advanced features TouchSale lacks:

### 3.1 AI/ML Capabilities
- AI-powered menu recommendations
- Demand forecasting with machine learning
- Sentiment analysis from reviews
- Conversational AI for queries
- Computer vision for inventory counting
- Video analytics for loss prevention

### 3.2 Modern Integrations
- DoorDash, Uber Eats, Grubhub integration
- QuickBooks, Xero accounting
- Advanced webhook system
- Multi-platform menu sync

### 3.3 Advanced Analytics
- RFM customer segmentation
- Predictive labor forecasting
- Dynamic/surge pricing
- A/B menu testing
- Benchmarking against industry

### 3.4 Modern Operations
- QR code table ordering
- Kiosk self-service
- Cloud kitchen support
- Drive-thru mode
- Curbside pickup
- Voice ordering

### 3.5 Marketing Automation
- Email campaign builder
- SMS marketing
- Customer journey tracking
- Gamification/rewards
- Referral programs

---

## 4. Implementation Recommendations

### Phase 1: Critical for Bulgarian Market (If Targeting Bulgaria)
1. Bulgarian fiscal device integration (NRA compliance)
2. AtomS3 accounting export
3. USN/QR code receipt support

### Phase 2: High-Value Operational Features
4. Multiple price lists per item
5. Menu of the Day functionality
6. Real-time SMS manager alerts
7. Quick order reordering
8. Recently used items list

### Phase 3: Enhancement Features
9. Subtable management
10. Account limits by customer
11. Automatic logout after close
12. Service deduction reports

---

## 5. Technical Implementation Notes

### 5.1 Database Schema Changes Required

```sql
-- Multiple Price Lists
CREATE TABLE product_price_lists (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    price_list_name VARCHAR(50) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    start_time TIME,
    end_time TIME,
    days_of_week JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Daily Menu
CREATE TABLE daily_menus (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    name VARCHAR(100) NOT NULL,
    items JSON NOT NULL,
    available_from TIME,
    available_until TIME,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Manager Alerts
CREATE TABLE manager_alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,
    threshold DECIMAL(10,2),
    recipient_phone VARCHAR(20),
    is_sms BOOLEAN DEFAULT TRUE,
    is_email BOOLEAN DEFAULT FALSE,
    is_push BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Customer Credit Limits
ALTER TABLE customers ADD COLUMN credit_limit DECIMAL(10,2) DEFAULT NULL;
ALTER TABLE customers ADD COLUMN current_balance DECIMAL(10,2) DEFAULT 0;

-- Recently Used Items (per operator)
CREATE TABLE operator_recent_items (
    id SERIAL PRIMARY KEY,
    staff_id INTEGER REFERENCES staff_users(id),
    product_id INTEGER REFERENCES products(id),
    last_used TIMESTAMP DEFAULT NOW(),
    use_count INTEGER DEFAULT 1
);
```

### 5.2 New API Endpoints Required

```
# Price Lists
GET    /api/v1/products/{id}/price-lists
POST   /api/v1/products/{id}/price-lists
PUT    /api/v1/price-lists/{id}
DELETE /api/v1/price-lists/{id}
GET    /api/v1/price-lists/active?context=dine_in

# Daily Menu
GET    /api/v1/daily-menu?date=2026-01-25
POST   /api/v1/daily-menu
PUT    /api/v1/daily-menu/{id}
DELETE /api/v1/daily-menu/{id}
GET    /api/v1/daily-menu/current

# Manager Alerts
GET    /api/v1/manager-alerts
POST   /api/v1/manager-alerts
PUT    /api/v1/manager-alerts/{id}
DELETE /api/v1/manager-alerts/{id}
POST   /api/v1/manager-alerts/test

# Quick Reorder
GET    /api/v1/customers/{id}/last-order
POST   /api/v1/orders/reorder/{order_id}

# Recently Used Items
GET    /api/v1/staff/{id}/recent-items
POST   /api/v1/staff/{id}/recent-items/{product_id}

# Bulgarian Fiscal (if needed)
POST   /api/v1/fiscal/print-receipt
GET    /api/v1/fiscal/status
POST   /api/v1/fiscal/daily-report
GET    /api/v1/fiscal/devices
```

---

## 6. Conclusion

BJS Menu is a modern, feature-rich POS system that exceeds TouchSale in most areas, particularly in AI/ML, delivery integrations, and analytics. The primary gaps are:

1. **Bulgarian-specific fiscal compliance** - Critical only if targeting Bulgarian market
2. **Operational conveniences** - Multiple price lists, daily menus, quick reorder
3. **Minor workflow features** - SMS alerts, subtables, auto-logout

The recommended approach is to implement the operational convenience features (price lists, daily menu, quick reorder) as they provide universal value, while Bulgarian fiscal features should only be prioritized if entering that market.

---

## Sources

- [UnrealSoft TouchSale](https://www.unrealsoft.net/products/sale/)
- [UnrealSoft Forums](https://www.unrealsoft.net/forums/viewforum.php?f=37)
- [UnrealSoft FourSeasons](https://www.unrealsoft.net/products/fourseasons/)
- [MyWaiter App](https://apkpure.com/mywaiter/com.unrealsoft.MySale)
- [Bulgarian POS Requirements](https://aidosbg.com/pos-systems-bulgaria/)
- [Bulgarian Fiscalization](https://www.linkedin.com/pulse/things-know-fiscalization-bulgaria-fiscalsolutions)
