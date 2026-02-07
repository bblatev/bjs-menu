"""Tests for stock deduction service and stock movements (H1.3, H2.3)."""

import pytest
from decimal import Decimal

from app.models.location import Location
from app.models.product import Product
from app.models.recipe import Recipe, RecipeLine
from app.models.restaurant import MenuItem
from app.models.stock import MovementReason, StockMovement, StockOnHand
from app.models.supplier import Supplier
from app.services.stock_deduction_service import StockDeductionService


@pytest.fixture
def stock_setup(db_session):
    """Create a full stock setup: supplier, products, location, recipes, stock."""
    supplier = Supplier(name="Stock Supplier")
    db_session.add(supplier)
    db_session.flush()

    location = Location(name="Stock Test Bar", is_default=True, active=True)
    db_session.add(location)
    db_session.flush()

    vodka = Product(
        name="Vodka", barcode="V001", supplier_id=supplier.id,
        unit="ml", cost_price=Decimal("0.05"), active=True,
    )
    lime = Product(
        name="Lime Juice", barcode="L001", supplier_id=supplier.id,
        unit="ml", cost_price=Decimal("0.02"), active=True,
    )
    garnish = Product(
        name="Garnish", barcode="G001", supplier_id=supplier.id,
        unit="pcs", cost_price=Decimal("0.10"), active=True,
    )
    db_session.add_all([vodka, lime, garnish])
    db_session.flush()

    # Seed stock
    for prod, qty in [(vodka, 5000), (lime, 3000), (garnish, 100)]:
        soh = StockOnHand(product_id=prod.id, location_id=location.id, qty=Decimal(str(qty)))
        db_session.add(soh)

    # Create recipe: "Moscow Mule" = 50ml vodka + 20ml lime + 1 garnish
    recipe = Recipe(name="Moscow Mule", pos_item_name="Moscow Mule")
    db_session.add(recipe)
    db_session.flush()

    db_session.add_all([
        RecipeLine(recipe_id=recipe.id, product_id=vodka.id, qty=Decimal("50"), unit="ml"),
        RecipeLine(recipe_id=recipe.id, product_id=lime.id, qty=Decimal("20"), unit="ml"),
        RecipeLine(recipe_id=recipe.id, product_id=garnish.id, qty=Decimal("1"), unit="pcs"),
    ])

    # Create a MenuItem linked to the recipe for order-based deduction/refund
    menu_item = MenuItem(
        name="Moscow Mule",
        price=Decimal("12.00"),
        category="Cocktails",
        available=True,
        recipe_id=recipe.id,
    )
    db_session.add(menu_item)
    db_session.commit()

    return {
        "supplier": supplier,
        "location": location,
        "vodka": vodka,
        "lime": lime,
        "garnish": garnish,
        "recipe": recipe,
        "menu_item": menu_item,
        "db": db_session,
    }


# ============== StockDeductionService unit tests ==============

class TestStockDeductionService:
    def test_find_recipe_by_pos_data(self, stock_setup):
        db = stock_setup["db"]
        svc = StockDeductionService(db)
        recipe = svc.find_recipe_by_pos_data(pos_item_id=None, name="Moscow Mule")
        assert recipe is not None
        assert recipe.name == "Moscow Mule"

    def test_find_recipe_not_found(self, stock_setup):
        db = stock_setup["db"]
        svc = StockDeductionService(db)
        recipe = svc.find_recipe_by_pos_data(pos_item_id=None, name="Nonexistent Drink")
        assert recipe is None

    def test_deduct_for_recipe(self, stock_setup):
        db = stock_setup["db"]
        recipe = stock_setup["recipe"]
        location = stock_setup["location"]
        vodka = stock_setup["vodka"]

        svc = StockDeductionService(db)
        result = svc.deduct_for_recipe(
            recipe=recipe,
            quantity=Decimal("2"),
            location_id=location.id,
            reference_type="test",
            reference_id=1,
            notes="Test deduction",
        )
        assert result["movements_created"] >= 1

        # Verify vodka stock reduced by 100ml (50ml * 2)
        soh = db.query(StockOnHand).filter(
            StockOnHand.product_id == vodka.id,
            StockOnHand.location_id == location.id,
        ).first()
        assert soh.qty == Decimal("4900")

    def test_deduct_reduces_all_ingredients(self, stock_setup):
        db = stock_setup["db"]
        recipe = stock_setup["recipe"]
        location = stock_setup["location"]
        lime = stock_setup["lime"]
        garnish = stock_setup["garnish"]

        svc = StockDeductionService(db)
        svc.deduct_for_recipe(
            recipe=recipe,
            quantity=Decimal("3"),
            location_id=location.id,
            reference_type="test",
            reference_id=2,
        )

        # Lime: 3000 - (20 * 3) = 2940
        lime_soh = db.query(StockOnHand).filter(
            StockOnHand.product_id == lime.id,
            StockOnHand.location_id == location.id,
        ).first()
        assert lime_soh.qty == Decimal("2940")

        # Garnish: 100 - (1 * 3) = 97
        garnish_soh = db.query(StockOnHand).filter(
            StockOnHand.product_id == garnish.id,
            StockOnHand.location_id == location.id,
        ).first()
        assert garnish_soh.qty == Decimal("97")

    def test_get_stock_for_recipe(self, stock_setup):
        db = stock_setup["db"]
        recipe = stock_setup["recipe"]
        location = stock_setup["location"]

        svc = StockDeductionService(db)
        result = svc.get_stock_for_recipe(recipe.id, location.id)
        assert "error" not in result
        # Returns can_make (int) for how many servings are possible
        assert result["can_make"] >= 1
        assert len(result["ingredients"]) == 3

    def test_deduct_for_order(self, stock_setup):
        db = stock_setup["db"]
        location = stock_setup["location"]

        svc = StockDeductionService(db)

        # Order items referencing a menu item name that matches recipe name
        order_items = [{
            "menu_item_id": 1,
            "name": "Moscow Mule",
            "quantity": 1,
            "price": 12.00,
        }]

        result = svc.deduct_for_order(
            order_items=order_items,
            location_id=location.id,
            reference_type="test_order",
            reference_id=100,
        )
        assert result["success"] is True


# ============== Stock refund tests (using recipe-level deduction/refund) ==============

class TestStockRefund:
    def test_refund_restores_stock(self, stock_setup):
        db = stock_setup["db"]
        recipe = stock_setup["recipe"]
        location = stock_setup["location"]
        vodka = stock_setup["vodka"]
        menu_item = stock_setup["menu_item"]

        svc = StockDeductionService(db)

        # Get initial stock
        initial_qty = db.query(StockOnHand).filter(
            StockOnHand.product_id == vodka.id,
            StockOnHand.location_id == location.id,
        ).first().qty

        # Deduct via recipe
        svc.deduct_for_recipe(
            recipe=recipe, quantity=Decimal("1"),
            location_id=location.id,
            reference_type="refund_test", reference_id=500,
        )
        db.flush()

        after_deduct = db.query(StockOnHand).filter(
            StockOnHand.product_id == vodka.id,
            StockOnHand.location_id == location.id,
        ).first().qty
        assert after_deduct < initial_qty

        # Refund using order items with the real menu_item ID
        order_items = [{
            "menu_item_id": menu_item.id,
            "name": "Moscow Mule",
            "quantity": 1,
            "price": 12.00,
        }]
        svc.refund_for_order(
            order_items=order_items,
            location_id=location.id,
            reference_type="refund_test",
            reference_id=500,
        )

        db.expire_all()
        after_refund = db.query(StockOnHand).filter(
            StockOnHand.product_id == vodka.id,
            StockOnHand.location_id == location.id,
        ).first().qty
        assert after_refund > after_deduct


# ============== Stock movement recording ==============

class TestStockMovements:
    def test_movement_created_on_deduction(self, stock_setup):
        db = stock_setup["db"]
        recipe = stock_setup["recipe"]
        location = stock_setup["location"]
        vodka = stock_setup["vodka"]

        # Clear any existing movements
        initial_count = db.query(StockMovement).filter(
            StockMovement.product_id == vodka.id,
        ).count()

        svc = StockDeductionService(db)
        svc.deduct_for_recipe(
            recipe=recipe,
            quantity=Decimal("1"),
            location_id=location.id,
            reference_type="test_movement",
            reference_id=300,
        )
        db.flush()  # Flush to make movements queryable

        new_count = db.query(StockMovement).filter(
            StockMovement.product_id == vodka.id,
        ).count()
        assert new_count > initial_count

    def test_movement_has_negative_delta(self, stock_setup):
        db = stock_setup["db"]
        recipe = stock_setup["recipe"]
        location = stock_setup["location"]
        vodka = stock_setup["vodka"]

        svc = StockDeductionService(db)
        svc.deduct_for_recipe(
            recipe=recipe,
            quantity=Decimal("1"),
            location_id=location.id,
            reference_type="delta_test",
            reference_id=600,
        )
        db.flush()  # Flush to make movements queryable

        movement = db.query(StockMovement).filter(
            StockMovement.product_id == vodka.id,
            StockMovement.ref_type == "delta_test",
        ).first()
        assert movement is not None
        assert movement.qty_delta < 0  # Negative for deduction


# ============== Stock on hand ==============

class TestStockOnHand:
    def test_stock_initialized(self, stock_setup):
        db = stock_setup["db"]
        vodka = stock_setup["vodka"]
        location = stock_setup["location"]

        soh = db.query(StockOnHand).filter(
            StockOnHand.product_id == vodka.id,
            StockOnHand.location_id == location.id,
        ).first()
        assert soh is not None
        assert soh.qty == Decimal("5000")

    def test_stock_non_negative_constraint(self, db_session, test_product, test_location):
        """Stock qty should not go below zero via validator."""
        soh = StockOnHand(
            product_id=test_product.id,
            location_id=test_location.id,
            qty=Decimal("10"),
        )
        db_session.add(soh)
        db_session.commit()

        with pytest.raises(ValueError, match="cannot be negative"):
            soh.qty = Decimal("-1")


# ============== Stock endpoint integration ==============

class TestStockEndpoints:
    def test_list_stock(self, client, auth_headers, test_location):
        res = client.get("/api/v1/stock/", headers=auth_headers)
        assert res.status_code == 200

    def test_stock_items(self, client, auth_headers):
        res = client.get("/api/v1/stock/items", headers=auth_headers)
        assert res.status_code == 200

    def test_stock_movements(self, client, auth_headers):
        res = client.get("/api/v1/stock/movements/", headers=auth_headers)
        assert res.status_code == 200

    def test_stock_categories(self, client, auth_headers):
        res = client.get("/api/v1/stock/categories", headers=auth_headers)
        assert res.status_code == 200

    def test_stock_alerts(self, client, auth_headers):
        res = client.get("/api/v1/stock/alerts/", headers=auth_headers)
        assert res.status_code == 200
