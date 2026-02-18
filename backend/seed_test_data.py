"""Seed test data for BJS Menu production endpoint testing.

Populates the database with realistic test records so that GET endpoints
that look up by ID=1 (test_production.py default) return real data
instead of 404.

Usage:
    cd /opt/bjs-menu/backend
    python seed_test_data.py
"""

import sys
import os
from datetime import datetime, date, time, timedelta, timezone
from decimal import Decimal

# Ensure the backend app is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.core.security import get_password_hash, get_pin_hash


def seed():
    """Insert test data into all key tables."""
    db = SessionLocal()
    try:
        _seed_all(db)
        db.commit()
        print("Seed data committed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


def _seed_all(db):
    """Populate every table that endpoints rely on."""
    from sqlalchemy import text, inspect

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"Found {len(existing_tables)} tables in database.")

    # Helper: skip insert if row with id=1 already exists
    def _exists(model):
        return db.query(model).filter(model.id == 1).first() is not None

    # ---------------------------------------------------------------
    # 1. Users (auth)
    # ---------------------------------------------------------------
    from app.models.user import User
    if not _exists(User):
        db.add(User(
            id=1,
            email="admin@bjs.bar",
            password_hash=get_password_hash("admin123"),
            role="owner",
            name="Admin User",
            is_active=True,
        ))
        db.add(User(
            id=2,
            email="manager@bjs.bar",
            password_hash=get_password_hash("manager123"),
            role="manager",
            name="Manager User",
            is_active=True,
        ))
        db.flush()
        print("  + Users (2)")

    # ---------------------------------------------------------------
    # 2. Locations / Venues
    # ---------------------------------------------------------------
    from app.models.location import Location
    if not _exists(Location):
        db.add(Location(
            id=1,
            name="BJS Main Bar",
            code="MAIN",
            description="Main bar location",
            is_default=True,
            active=True,
            location_type="restaurant",
            status="active",
            is_primary=True,
            street="123 Main St",
            city="Sofia",
            country="Bulgaria",
            timezone="Europe/Sofia",
            currency="BGN",
        ))
        db.add(Location(
            id=2,
            name="BJS Patio",
            code="PATIO",
            description="Outdoor patio area",
            is_default=False,
            active=True,
            location_type="restaurant",
            status="active",
        ))
        db.flush()
        print("  + Locations (2)")

    # ---------------------------------------------------------------
    # 2b. Venues (some tables reference venue_id -> venues)
    # ---------------------------------------------------------------
    if "venues" in existing_tables:
        from sqlalchemy import text as _text
        try:
            row = db.execute(_text("SELECT COUNT(*) FROM venues")).scalar()
            if not row or row == 0:
                nested = db.begin_nested()
                try:
                    db.execute(_text("""
                        INSERT INTO venues (id, name, address, phone, active)
                        VALUES (1, '"BJS Main Bar"', '123 Main St, Sofia', '+359888111111', true)
                    """))
                    nested.commit()
                    print("  + Venues (1)")
                except Exception as e:
                    nested.rollback()
                    print(f"  ! Venues skipped: {e.__class__.__name__}: {str(e)[:80]}")
        except Exception as e:
            print(f"  ! Venues check skipped: {e.__class__.__name__}: {str(e)[:80]}")

    # ---------------------------------------------------------------
    # 3. Suppliers
    # ---------------------------------------------------------------
    from app.models.supplier import Supplier
    if not _exists(Supplier):
        db.add(Supplier(
            id=1,
            name="Sofia Beverages Ltd",
            contact_phone="+359888111222",
            contact_email="orders@sofiabev.bg",
            address="45 Vitosha Blvd, Sofia",
        ))
        db.add(Supplier(
            id=2,
            name="Fresh Foods BG",
            contact_phone="+359888333444",
            contact_email="info@freshfoods.bg",
            address="12 Rakovski St, Sofia",
        ))
        db.flush()
        print("  + Suppliers (2)")

    # ---------------------------------------------------------------
    # 4. Products
    # ---------------------------------------------------------------
    from app.models.product import Product
    if not _exists(Product):
        products = [
            Product(id=1, name="Vodka Belvedere 700ml", barcode="5901041003003", supplier_id=1,
                    unit="pcs", min_stock=Decimal("5"), target_stock=Decimal("20"),
                    cost_price=Decimal("45.00"), sku="VOD-BEL-700"),
            Product(id=2, name="Gin Hendricks 700ml", barcode="5010327705217", supplier_id=1,
                    unit="pcs", min_stock=Decimal("3"), target_stock=Decimal("15"),
                    cost_price=Decimal("52.00"), sku="GIN-HEN-700"),
            Product(id=3, name="Tomato Fresh 1kg", barcode="2000001000013", supplier_id=2,
                    unit="kg", min_stock=Decimal("2"), target_stock=Decimal("10"),
                    cost_price=Decimal("3.50"), sku="VEG-TOM-1K"),
            Product(id=4, name="Lemon 1kg", barcode="2000001000020", supplier_id=2,
                    unit="kg", min_stock=Decimal("1"), target_stock=Decimal("5"),
                    cost_price=Decimal("4.00"), sku="FRU-LEM-1K"),
            Product(id=5, name="Coca-Cola 330ml", barcode="5449000000996", supplier_id=1,
                    unit="pcs", min_stock=Decimal("24"), target_stock=Decimal("96"),
                    cost_price=Decimal("1.20"), sku="SOF-COC-330"),
        ]
        db.add_all(products)
        db.flush()
        print("  + Products (5)")

    # ---------------------------------------------------------------
    # 5. Stock on hand
    # ---------------------------------------------------------------
    from app.models.stock import StockOnHand, StockMovement
    if not db.query(StockOnHand).filter(StockOnHand.product_id == 1, StockOnHand.location_id == 1).first():
        for pid in range(1, 6):
            db.add(StockOnHand(product_id=pid, location_id=1, qty=Decimal("10.00")))
        db.flush()
        print("  + StockOnHand (5)")

    # ---------------------------------------------------------------
    # 6. Stock movements
    # ---------------------------------------------------------------
    if not db.query(StockMovement).first():
        now = datetime.now(timezone.utc)
        db.add(StockMovement(
            product_id=1, location_id=1, qty_delta=Decimal("10"),
            reason="purchase", ref_type="initial_seed", notes="Initial stock",
            created_by=1,
        ))
        db.add(StockMovement(
            product_id=1, location_id=1, qty_delta=Decimal("-2"),
            reason="sale", ref_type="pos_sale", notes="Test sale",
            created_by=1,
        ))
        db.flush()
        print("  + StockMovements (2)")

    # ---------------------------------------------------------------
    # 7. Menu categories
    # ---------------------------------------------------------------
    from app.models.restaurant import MenuCategory, MenuItem, Table, Check, CheckItem
    from app.models.restaurant import KitchenOrder, GuestOrder, ComboMeal, ComboItem
    if not _exists(MenuCategory):
        categories = [
            MenuCategory(id=1, name_bg="Коктейли", name_en="Cocktails", sort_order=1, active=True),
            MenuCategory(id=2, name_bg="Храна", name_en="Food", sort_order=2, active=True),
            MenuCategory(id=3, name_bg="Безалкохолни", name_en="Soft Drinks", sort_order=3, active=True),
        ]
        db.add_all(categories)
        db.flush()
        print("  + MenuCategories (3)")

    # ---------------------------------------------------------------
    # 8. Menu items
    # ---------------------------------------------------------------
    if not _exists(MenuItem):
        items = [
            MenuItem(id=1, name="Moscow Mule", description="Classic vodka cocktail",
                     price=Decimal("14.00"), category="Cocktails", available=True,
                     prep_time_minutes=5, station="bar", location_id=1),
            MenuItem(id=2, name="Gin & Tonic", description="Hendricks with Fever Tree",
                     price=Decimal("16.00"), category="Cocktails", available=True,
                     prep_time_minutes=3, station="bar", location_id=1),
            MenuItem(id=3, name="Caesar Salad", description="Classic caesar with grilled chicken",
                     price=Decimal("18.00"), category="Food", available=True,
                     prep_time_minutes=12, station="salad", location_id=1),
            MenuItem(id=4, name="Coca-Cola", description="330ml can",
                     price=Decimal("4.00"), category="Soft Drinks", available=True,
                     prep_time_minutes=0, station="bar", location_id=1),
            MenuItem(id=5, name="Burger Classic", description="180g beef patty with fries",
                     price=Decimal("22.00"), category="Food", available=True,
                     prep_time_minutes=15, station="grill", location_id=1),
        ]
        db.add_all(items)
        db.flush()
        print("  + MenuItems (5)")

    # ---------------------------------------------------------------
    # 9. Tables
    # ---------------------------------------------------------------
    if not _exists(Table):
        tables = [
            Table(id=1, number="1", capacity=4, status="available", area="Main Floor", location_id=1),
            Table(id=2, number="2", capacity=2, status="available", area="Main Floor", location_id=1),
            Table(id=3, number="3", capacity=6, status="available", area="Patio", location_id=1),
            Table(id=4, number="B1", capacity=4, status="available", area="Bar", location_id=1),
            Table(id=5, number="VIP1", capacity=8, status="available", area="VIP", location_id=1),
        ]
        db.add_all(tables)
        db.flush()
        print("  + Tables (5)")

    # ---------------------------------------------------------------
    # 10. Checks
    # ---------------------------------------------------------------
    if not _exists(Check):
        now = datetime.now(timezone.utc)
        db.add(Check(
            id=1, table_id=1, server_id=1, location_id=1, guest_count=2,
            status="open", subtotal=Decimal("30.00"), tax=Decimal("6.00"),
            total=Decimal("36.00"), balance_due=Decimal("36.00"),
        ))
        db.add(Check(
            id=2, table_id=2, server_id=1, location_id=1, guest_count=1,
            status="closed", subtotal=Decimal("14.00"), tax=Decimal("2.80"),
            total=Decimal("16.80"), balance_due=Decimal("0.00"),
        ))
        db.flush()
        print("  + Checks (2)")

    # ---------------------------------------------------------------
    # 11. Check items
    # ---------------------------------------------------------------
    if not _exists(CheckItem):
        db.add(CheckItem(
            id=1, check_id=1, menu_item_id=1, name="Moscow Mule",
            quantity=1, price=Decimal("14.00"), total=Decimal("14.00"),
            status="served", course="main",
        ))
        db.add(CheckItem(
            id=2, check_id=1, menu_item_id=3, name="Caesar Salad",
            quantity=1, price=Decimal("18.00"), total=Decimal("18.00"),
            status="cooking", course="main",
        ))
        db.flush()
        print("  + CheckItems (2)")

    # ---------------------------------------------------------------
    # 12. Kitchen orders
    # ---------------------------------------------------------------
    if not _exists(KitchenOrder):
        db.add(KitchenOrder(
            id=1, check_id=1, table_number="1", status="cooking",
            priority=1, station="salad", course="main", location_id=1,
            items=[{"name": "Caesar Salad", "qty": 1}],
        ))
        db.flush()
        print("  + KitchenOrders (1)")

    # ---------------------------------------------------------------
    # 13. Guest orders
    # ---------------------------------------------------------------
    if not _exists(GuestOrder):
        db.add(GuestOrder(
            id=1, table_id=1, table_number="1", status="received",
            order_type="dine-in", subtotal=Decimal("14.00"),
            tax=Decimal("2.80"), total=Decimal("16.80"),
            items=[{"name": "Moscow Mule", "qty": 1, "price": 14.00}],
            customer_name="Test Guest", location_id=1,
        ))
        db.flush()
        print("  + GuestOrders (1)")

    # ---------------------------------------------------------------
    # 14. Combo meals
    # ---------------------------------------------------------------
    if not _exists(ComboMeal):
        db.add(ComboMeal(
            id=1, name="Burger Combo", description="Burger + drink",
            price=Decimal("24.00"), available=True, featured=True, category="Food",
        ))
        db.flush()
        db.add(ComboItem(
            id=1, combo_id=1, menu_item_id=1, name="Burger Classic", quantity=1,
        ))
        db.add(ComboItem(
            id=2, combo_id=1, menu_item_id=2, name="Soft Drink", quantity=1,
            is_choice=True, choice_group="Choose your drink",
        ))
        db.flush()
        print("  + ComboMeals (1) + ComboItems (2)")

    # ---------------------------------------------------------------
    # 15. Staff users
    # ---------------------------------------------------------------
    from app.models.staff import StaffUser, Shift, TimeClockEntry, TipPool, TipDistribution
    from app.models.staff import PerformanceMetric, PerformanceGoal, TableAssignment
    if not _exists(StaffUser):
        staff = [
            StaffUser(id=1, full_name="Ivan Petrov", role="waiter",
                      pin_hash=get_pin_hash("1234"), is_active=True,
                      hourly_rate=15.0, location_id=1),
            StaffUser(id=2, full_name="Maria Ivanova", role="bar",
                      pin_hash=get_pin_hash("5678"), is_active=True,
                      hourly_rate=16.0, location_id=1),
            StaffUser(id=3, full_name="Georgi Dimitrov", role="kitchen",
                      pin_hash=get_pin_hash("9012"), is_active=True,
                      hourly_rate=14.0, location_id=1),
            StaffUser(id=4, full_name="Elena Todorova", role="manager",
                      pin_hash=get_pin_hash("3456"), is_active=True,
                      hourly_rate=20.0, location_id=1),
        ]
        db.add_all(staff)
        db.flush()
        print("  + StaffUsers (4)")

    # ---------------------------------------------------------------
    # 16. Shifts
    # ---------------------------------------------------------------
    if not _exists(Shift):
        today = date.today()
        db.add(Shift(
            id=1, staff_id=1, date=today, shift_type="evening",
            start_time=time(17, 0), end_time=time(1, 0),
            break_minutes=30, status="scheduled", position="waiter",
            is_published=True, location_id=1,
        ))
        db.add(Shift(
            id=2, staff_id=2, date=today, shift_type="evening",
            start_time=time(18, 0), end_time=time(2, 0),
            break_minutes=30, status="scheduled", position="bartender",
            is_published=True, location_id=1,
        ))
        db.flush()
        print("  + Shifts (2)")

    # ---------------------------------------------------------------
    # 17. Time clock entries
    # ---------------------------------------------------------------
    if not _exists(TimeClockEntry):
        now = datetime.now(timezone.utc)
        db.add(TimeClockEntry(
            id=1, staff_id=1, clock_in=now - timedelta(hours=3),
            status="clocked_in", clock_in_method="pin", location_id=1,
        ))
        db.flush()
        print("  + TimeClockEntries (1)")

    # ---------------------------------------------------------------
    # 18. Table assignments
    # ---------------------------------------------------------------
    if not _exists(TableAssignment):
        db.add(TableAssignment(
            id=1, staff_id=1, table_id=1, area="Main Floor",
            is_active=True, location_id=1,
        ))
        db.flush()
        print("  + TableAssignments (1)")

    # ---------------------------------------------------------------
    # 19. Performance metrics and goals
    # ---------------------------------------------------------------
    if not _exists(PerformanceMetric):
        db.add(PerformanceMetric(
            id=1, staff_id=1, period="day", period_date=date.today(),
            sales_amount=450.0, orders_count=12, avg_ticket=37.5,
            items_sold=28, tips_received=65.0, customer_rating=4.5,
            hours_worked=6.0, sales_per_hour=75.0, location_id=1,
        ))
        db.flush()
        print("  + PerformanceMetrics (1)")

    if not _exists(PerformanceGoal):
        db.add(PerformanceGoal(
            id=1, metric="daily_sales", target_value=500.0,
            current_value=450.0, unit="BGN", period="day", location_id=1,
        ))
        db.flush()
        print("  + PerformanceGoals (1)")

    # ---------------------------------------------------------------
    # 20. Tip pools
    # ---------------------------------------------------------------
    if not _exists(TipPool):
        db.add(TipPool(
            id=1, date=date.today(), shift="evening",
            total_tips_cash=120.0, total_tips_card=80.0, total_tips=200.0,
            participants_count=3, distribution_method="equal",
            status="pending", location_id=1,
        ))
        db.flush()
        db.add(TipDistribution(
            id=1, pool_id=1, staff_id=1, hours_worked=6.0,
            share_percentage=33.3, amount=66.60, is_paid=False,
        ))
        db.flush()
        print("  + TipPools (1) + TipDistributions (1)")

    # ---------------------------------------------------------------
    # 21. Customers
    # ---------------------------------------------------------------
    from app.models.customer import Customer
    if not _exists(Customer):
        customers = [
            Customer(
                id=1, name="Nikolay Stoyanov", phone="+359888555111",
                email="nikolay@example.com", total_orders=15, total_spent=850.0,
                average_order=56.7, lifetime_value=850.0, segment="Champions",
                rfm_recency=5, rfm_frequency=4, rfm_monetary=5,
                marketing_consent=True, location_id=1,
            ),
            Customer(
                id=2, name="Desislava Petrova", phone="+359888555222",
                email="desi@example.com", total_orders=5, total_spent=280.0,
                average_order=56.0, lifetime_value=280.0, segment="Loyal",
                rfm_recency=4, rfm_frequency=3, rfm_monetary=3,
                marketing_consent=True, location_id=1,
            ),
        ]
        db.add_all(customers)
        db.flush()
        print("  + Customers (2)")

    # ---------------------------------------------------------------
    # 22. Recipes
    # ---------------------------------------------------------------
    from app.models.recipe import Recipe, RecipeLine
    if not _exists(Recipe):
        db.add(Recipe(
            id=1, name="Moscow Mule", pos_item_id=1, pos_item_name="Moscow Mule",
        ))
        db.flush()
        db.add(RecipeLine(id=1, recipe_id=1, product_id=1, qty=Decimal("0.05"), unit="L"))
        db.add(RecipeLine(id=2, recipe_id=1, product_id=4, qty=Decimal("0.02"), unit="kg"))
        db.flush()
        print("  + Recipes (1) + RecipeLines (2)")

    # ---------------------------------------------------------------
    # 23. Purchase orders
    # ---------------------------------------------------------------
    from app.models.order import PurchaseOrder, PurchaseOrderLine
    if not _exists(PurchaseOrder):
        db.add(PurchaseOrder(
            id=1, supplier_id=1, location_id=1, status="draft",
            created_by=1, notes="Weekly spirits order",
        ))
        db.flush()
        db.add(PurchaseOrderLine(id=1, po_id=1, product_id=1,
                                  qty=Decimal("12"), unit_cost=Decimal("45.00")))
        db.add(PurchaseOrderLine(id=2, po_id=1, product_id=2,
                                  qty=Decimal("6"), unit_cost=Decimal("52.00")))
        db.flush()
        print("  + PurchaseOrders (1) + PurchaseOrderLines (2)")

    # ---------------------------------------------------------------
    # 24. Inventory sessions
    # ---------------------------------------------------------------
    from app.models.inventory import InventorySession
    if not _exists(InventorySession):
        db.add(InventorySession(
            id=1, location_id=1, shelf_zone="Bar Back",
            status="draft", created_by=1,
        ))
        db.flush()
        print("  + InventorySessions (1)")

    # ---------------------------------------------------------------
    # 25. Reservations
    # ---------------------------------------------------------------
    from app.models.reservations import Reservation
    if "reservations" in existing_tables:
        if not _exists(Reservation):
            db.add(Reservation(
                id=1,
                guest_name="Test Reservation",
                guest_phone="+359888999111",
                guest_email="reservation@test.com",
                party_size=4,
                reservation_date=datetime.combine(date.today() + timedelta(days=1), time(19, 0)),
                duration_minutes=90,
                status="confirmed",
                location_id=1,
                table_ids=[1],
                source="manual",
            ))
            db.flush()
            print("  + Reservations (1)")

    # ---------------------------------------------------------------
    # 26. Advanced features models (settings, etc.)
    # ---------------------------------------------------------------
    _seed_settings(db, existing_tables)
    _seed_advanced_models(db, existing_tables)

    print("\nSeed complete!")


def _seed_settings(db, existing_tables):
    """Seed app_settings and related config tables."""
    if "app_settings" not in existing_tables:
        return

    from sqlalchemy import text
    row = db.execute(text("SELECT COUNT(*) FROM app_settings")).scalar()
    if row and row > 0:
        return

    db.execute(text("""
        INSERT INTO app_settings (id, key, value, category)
        VALUES
        (1, 'restaurant_name', '"BJS Bar & Grill"', 'general'),
        (2, 'currency', '"BGN"', 'general'),
        (3, 'tax_rate', '"20"', 'financial'),
        (4, 'timezone', '"Europe/Sofia"', 'general')
    """))
    db.flush()
    print("  + AppSettings (4)")


def _safe_insert(db, table_name, sql, label, existing_tables):
    """Try to insert data, using savepoint to rollback on error without affecting other inserts."""
    from sqlalchemy import text
    if table_name not in existing_tables:
        return
    try:
        row = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        if row and row > 0:
            return
        # Use nested transaction (savepoint) so errors don't rollback everything
        nested = db.begin_nested()
        try:
            db.execute(text(sql))
            nested.commit()
            print(f"  + {label}")
        except Exception as e:
            nested.rollback()
            print(f"  ! {label} skipped: {e.__class__.__name__}: {str(e)[:80]}")
    except Exception as e:
        print(f"  ! {label} skipped: {e.__class__.__name__}: {str(e)[:80]}")


def _seed_advanced_models(db, existing_tables):
    """Seed additional tables that various advanced endpoints depend on."""

    _safe_insert(db, "cash_drawers", """
        INSERT INTO cash_drawers (id, venue_id, staff_user_id, opening_balance, expected_balance, status, opened_at)
        VALUES (1, 1, 1, 500.00, 1250.00, 'open', NOW())
    """, "CashDrawers (1)", existing_tables)

    _safe_insert(db, "inventory_batches", """
        INSERT INTO inventory_batches (id, product_id, location_id, batch_number, received_quantity, current_quantity, received_date, expiration_date, unit_cost, is_expired, is_quarantined)
        VALUES (1, 1, 1, 'BATCH-2026-001', 10.00, 10.00, CURRENT_DATE, CURRENT_DATE + INTERVAL '90 days', 45.00, false, false)
    """, "InventoryBatches (1)", existing_tables)

    _safe_insert(db, "floor_plans", """
        INSERT INTO floor_plans (id, venue_id, name, width, height, is_active, created_at)
        VALUES (1, 1, 'Main Floor Plan', 800, 600, true, NOW())
    """, "FloorPlans (1)", existing_tables)

    _safe_insert(db, "marketing_campaigns", """
        INSERT INTO marketing_campaigns (id, name, campaign_type, status, subject_line, content_text, created_by)
        VALUES (1, 'Welcome Campaign', 'email', 'draft', 'Welcome to BJS!', 'Thank you for visiting.', 1)
    """, "MarketingCampaigns (1)", existing_tables)

    _safe_insert(db, "loyalty_programs", """
        INSERT INTO loyalty_programs (id, name, program_type, points_per_dollar, is_active)
        VALUES (1, 'BJS Rewards', 'points', 1.0, true)
    """, "LoyaltyPrograms (1)", existing_tables)

    _safe_insert(db, "gift_card_programs", """
        INSERT INTO gift_card_programs (id, name, denominations, custom_amount_allowed, min_amount, max_amount, bonus_enabled, dormancy_fee_enabled, is_active)
        VALUES (1, 'Standard Gift Card', '[25, 50, 100]', true, 10.00, 500.00, false, false, true)
    """, "GiftCardPrograms (1)", existing_tables)

    _safe_insert(db, "gift_cards", """
        INSERT INTO gift_cards (id, program_id, card_number, initial_balance, current_balance, bonus_balance, delivery_method, is_active, created_at)
        VALUES (1, 1, 'GC-TEST-001', 100.00, 50.00, 0.00, 'email', true, NOW())
    """, "GiftCards (1)", existing_tables)

    _safe_insert(db, "dynamic_pricing_rules", """
        INSERT INTO dynamic_pricing_rules (id, location_id, name, trigger_type, trigger_conditions, adjustment_type, adjustment_value, applies_to, is_active)
        VALUES (1, 1, 'Happy Hour', 'time_based', '{"hours": [16,17,18]}', 'percentage', 20.0, 'all', true)
    """, "DynamicPricingRules (1)", existing_tables)

    _safe_insert(db, "auto_discounts", """
        INSERT INTO auto_discounts (id, venue_id, name, discount_type, discount_percentage, start_time, end_time, valid_days, active)
        VALUES (1, 1, '10% Lunch Special', 'percentage', 10.0, '11:00', '14:00', '[1,2,3,4,5]', true)
    """, "AutoDiscounts (1)", existing_tables)

    _safe_insert(db, "happy_hours", """
        INSERT INTO happy_hours (id, location_id, name, days, start_time, end_time, discount_type, discount_value, applies_to, status, times_used, total_discount_given)
        VALUES (1, 1, 'Weekday Happy Hour', '[1,2,3,4,5]', '16:00', '18:00', 'percentage', 20.0, 'all', 'active', 0, 0.0)
    """, "HappyHours (1)", existing_tables)

    _safe_insert(db, "bar_tabs", """
        INSERT INTO bar_tabs (id, customer_name, card_on_file, status, subtotal, tax, tip, total, location_id, created_at)
        VALUES (1, 'Regular Customer', false, 'open', 40.00, 5.00, 0.00, 45.00, 1, NOW())
    """, "BarTabs (1)", existing_tables)

    _safe_insert(db, "kegs", """
        INSERT INTO kegs (id, product_id, product_name, size_liters, remaining_liters, status, location, tapped_at, location_id)
        VALUES (1, 1, 'Test Product', 50.0, 35.0, 'tapped', 'Main Bar', NOW(), 1)
    """, "Kegs (1)", existing_tables)

    # Delivery orders need an integration record first
    _safe_insert(db, "delivery_integrations", """
        INSERT INTO delivery_integrations (id, location_id, platform, api_key, store_id, is_active, auto_accept_orders, auto_confirm_ready, prep_time_minutes, sync_inventory, is_menu_synced)
        VALUES (1, 1, 'GLOVO', 'test-key', 'store-1', true, false, false, 15, false, false)
    """, "DeliveryIntegrations (1)", existing_tables)

    _safe_insert(db, "delivery_orders", """
        INSERT INTO delivery_orders (id, integration_id, platform, platform_order_id, status, customer_name, total, created_at)
        VALUES (1, 1, 'GLOVO', 'GLV-12345', 'RECEIVED', 'Delivery Customer', 32.00, NOW())
    """, "DeliveryOrders (1)", existing_tables)

    _safe_insert(db, "invoices", """
        INSERT INTO invoices (id, supplier_id, location_id, invoice_number, total_amount, status, invoice_date)
        VALUES (1, 1, 1, 'INV-2026-001', 1500.00, 'pending', CURRENT_DATE)
    """, "Invoices (1)", existing_tables)

    _safe_insert(db, "supplier_documents", """
        INSERT INTO supplier_documents (id, supplier_id, name, document_type)
        VALUES (1, 1, 'Business License', 'license')
    """, "SupplierDocuments (1)", existing_tables)

    _safe_insert(db, "notifications", """
        INSERT INTO notifications (id, user_id, title, message, type, read, created_at)
        VALUES (1, 1, 'Welcome', 'Welcome to BJS Menu', 'info', false, NOW())
    """, "Notifications (1)", existing_tables)

    _safe_insert(db, "audit_log_entries", """
        INSERT INTO audit_log_entries (id, user_id, action, entity_type, entity_id, details, created_at)
        VALUES (1, 1, 'login', 'user', '1', '{"method": "password"}', NOW())
    """, "AuditLogEntries (1)", existing_tables)

    _safe_insert(db, "promotions", """
        INSERT INTO promotions (id, name, type, value, active, start_date, end_date)
        VALUES (1, 'Weekend Special', 'percentage', 15.0, true, CURRENT_DATE, CURRENT_DATE + INTERVAL '30 days')
    """, "Promotions (1)", existing_tables)

    _safe_insert(db, "shift_definitions", """
        INSERT INTO shift_definitions (id, venue_id, name, start_time, end_time, is_active)
        VALUES (1, 1, 'Evening Shift', '17:00', '01:00', true)
    """, "ShiftDefinitions (1)", existing_tables)

    _safe_insert(db, "staff_schedules", """
        INSERT INTO staff_schedules (id, venue_id, staff_id, schedule_date, scheduled_start, scheduled_end)
        VALUES (1, 1, 1, CURRENT_DATE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '8 hours')
    """, "StaffSchedules (1)", existing_tables)


if __name__ == "__main__":
    print("=" * 60)
    print("BJS Menu - Seed Test Data")
    print("=" * 60)
    seed()
