"""Tests for order lifecycle: guest orders, status updates, void/cancel (H1.2, H2.2)."""

import pytest
from decimal import Decimal

from app.models.restaurant import GuestOrder as GuestOrderModel, MenuItem, Table
from app.models.location import Location


@pytest.fixture
def order_setup(db_session):
    """Create a table and menu items for order tests."""
    # Ensure a location exists
    location = db_session.query(Location).first()
    if not location:
        location = Location(name="Order Test Bar", is_default=True, active=True)
        db_session.add(location)
        db_session.flush()

    # Create table
    table = Table(
        number="T1",
        capacity=4,
        status="available",
        area="Main Floor",
        token="test-token-123",
    )
    db_session.add(table)
    db_session.flush()

    # Create menu items
    beer = MenuItem(
        name="House Beer",
        price=Decimal("5.00"),
        category="Drinks",
        available=True,
        station="bar",
    )
    burger = MenuItem(
        name="Classic Burger",
        price=Decimal("12.00"),
        category="Food",
        available=True,
        station="kitchen",
    )
    unavailable = MenuItem(
        name="Seasonal Special",
        price=Decimal("20.00"),
        category="Specials",
        available=False,
    )
    db_session.add_all([beer, burger, unavailable])
    db_session.commit()

    return {
        "table": table,
        "beer": beer,
        "burger": burger,
        "unavailable": unavailable,
        "location": location,
        "db": db_session,
    }


# ============== Guest order placement ==============

class TestGuestOrderPlacement:
    """POST /api/v1/orders/guest is in public_write_paths (no auth needed)."""

    def test_place_order(self, client, order_setup):
        beer = order_setup["beer"]
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "test-token-123",
            "items": [{"menu_item_id": beer.id, "quantity": 2}],
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "received"
        assert data["items_count"] == 1
        assert data["table_number"] == "T1"

    def test_place_order_multiple_items(self, client, order_setup):
        beer = order_setup["beer"]
        burger = order_setup["burger"]
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "test-token-123",
            "items": [
                {"menu_item_id": beer.id, "quantity": 1},
                {"menu_item_id": burger.id, "quantity": 1, "notes": "No onions"},
            ],
        })
        assert res.status_code == 200
        assert res.json()["items_count"] == 2

    def test_place_order_with_notes(self, client, order_setup):
        beer = order_setup["beer"]
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "test-token-123",
            "items": [{"menu_item_id": beer.id, "quantity": 1}],
            "notes": "Birthday party",
        })
        assert res.status_code == 200

    def test_unavailable_item_rejected(self, client, order_setup):
        item = order_setup["unavailable"]
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "test-token-123",
            "items": [{"menu_item_id": item.id, "quantity": 1}],
        })
        assert res.status_code == 400

    def test_invalid_menu_item_rejected(self, client, order_setup):
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "test-token-123",
            "items": [{"menu_item_id": 99999, "quantity": 1}],
        })
        assert res.status_code == 400

    def test_unknown_table_token_creates_order(self, client, order_setup):
        """System auto-creates tables for unknown tokens (QR code flexibility)."""
        beer = order_setup["beer"]
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "dynamic-token-999",
            "items": [{"menu_item_id": beer.id, "quantity": 1}],
        })
        # System creates table on-the-fly if not found
        assert res.status_code == 200

    def test_empty_items_rejected(self, client, order_setup):
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "test-token-123",
            "items": [],
        })
        assert res.status_code == 422  # Pydantic validation

    def test_quantity_zero_rejected(self, client, order_setup):
        beer = order_setup["beer"]
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "test-token-123",
            "items": [{"menu_item_id": beer.id, "quantity": 0}],
        })
        assert res.status_code == 422

    def test_order_total_calculated(self, client, order_setup):
        beer = order_setup["beer"]  # $5.00
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "test-token-123",
            "items": [{"menu_item_id": beer.id, "quantity": 3}],
        })
        assert res.status_code == 200
        assert res.json()["total"] == 15.0  # 3 * $5.00


# ============== Order retrieval (GET is public) ==============

class TestOrderRetrieval:
    def _create_order(self, client, beer_id):
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "test-token-123",
            "items": [{"menu_item_id": beer_id, "quantity": 1}],
        })
        return res.json()["order_id"]

    def test_get_order_by_id(self, client, auth_headers, order_setup):
        order_id = self._create_order(client, order_setup["beer"].id)
        res = client.get(f"/api/v1/orders/guest/{order_id}", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == order_id
        assert data["status"] == "received"

    def test_get_nonexistent_order_404(self, client, auth_headers, order_setup):
        res = client.get("/api/v1/orders/guest/99999", headers=auth_headers)
        assert res.status_code == 404

    def test_get_table_orders(self, client, order_setup):
        self._create_order(client, order_setup["beer"].id)
        res = client.get("/api/v1/orders/table/test-token-123")
        assert res.status_code == 200
        data = res.json()
        assert len(data["orders"]) >= 1


# ============== Order status updates (requires auth for PUT) ==============

class TestOrderStatusUpdates:
    def _create_order(self, client, beer_id):
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "test-token-123",
            "items": [{"menu_item_id": beer_id, "quantity": 1}],
        })
        return res.json()["order_id"]

    def test_update_status_to_confirmed(self, client, auth_headers, order_setup):
        order_id = self._create_order(client, order_setup["beer"].id)
        res = client.put(
            f"/api/v1/orders/{order_id}/status?status=confirmed",
            headers=auth_headers,
        )
        assert res.status_code == 200

        # Verify status changed
        res = client.get(f"/api/v1/orders/guest/{order_id}", headers=auth_headers)
        assert res.json()["status"] == "confirmed"

    def test_update_status_to_ready(self, client, auth_headers, order_setup):
        order_id = self._create_order(client, order_setup["beer"].id)
        # Move through states
        client.put(
            f"/api/v1/orders/{order_id}/status?status=confirmed",
            headers=auth_headers,
        )
        res = client.put(
            f"/api/v1/orders/{order_id}/status?status=ready",
            headers=auth_headers,
        )
        assert res.status_code == 200


# ============== Order void/cancel (requires auth) ==============

class TestOrderVoidCancel:
    def _create_order(self, client, beer_id):
        res = client.post("/api/v1/orders/guest", json={
            "table_token": "test-token-123",
            "items": [{"menu_item_id": beer_id, "quantity": 1}],
        })
        return res.json()["order_id"]

    def test_cancel_order(self, client, auth_headers, order_setup):
        order_id = self._create_order(client, order_setup["beer"].id)
        res = client.post(
            f"/api/v1/orders/{order_id}/cancel?reason=customer+request",
            headers=auth_headers,
        )
        assert res.status_code == 200

        # Verify cancelled
        res = client.get(f"/api/v1/orders/guest/{order_id}", headers=auth_headers)
        assert res.json()["status"] == "cancelled"

    def test_void_order(self, client, auth_headers, order_setup):
        order_id = self._create_order(client, order_setup["beer"].id)
        res = client.post(
            f"/api/v1/orders/{order_id}/void",
            json={"reason": "Wrong order"},
            headers=auth_headers,
        )
        assert res.status_code == 200


# ============== Menu management (GET is public, POST requires auth) ==============

class TestMenuManagement:
    def test_get_menu(self, client, order_setup):
        res = client.get("/api/v1/menu/display")
        assert res.status_code == 200

    def test_get_tables(self, client, order_setup):
        res = client.get("/api/v1/tables")
        assert res.status_code == 200
        data = res.json()
        assert len(data["tables"]) >= 1

    def test_create_table(self, client, auth_headers, order_setup):
        res = client.post("/api/v1/tables", json={
            "number": "T99",
            "capacity": 6,
            "area": "Patio",
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["table"]["number"] == "T99"

    def test_create_menu_item(self, client, auth_headers, order_setup):
        res = client.post("/api/v1/menu/items", json={
            "name": "New Cocktail",
            "price": 14.50,
            "category": "Cocktails",
        }, headers=auth_headers)
        assert res.status_code in (200, 201)

    def test_xss_in_item_name_sanitized(self, client, auth_headers, order_setup):
        res = client.post("/api/v1/menu/items", json={
            "name": "<script>alert(1)</script>",
            "price": 10.00,
            "category": "Test",
        }, headers=auth_headers)
        assert res.status_code in (200, 201)
        data = res.json()
        item = data.get("item", data)
        name = item.get("name", "")
        assert "<script>" not in name

    def test_list_menu_items(self, client, order_setup):
        res = client.get("/api/v1/menu/items")
        assert res.status_code == 200
