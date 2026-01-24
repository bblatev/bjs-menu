"""API endpoint tests."""

import io
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.inventory import InventorySession, SessionStatus
from app.models.location import Location
from app.models.product import Product
from app.models.stock import StockOnHand
from app.models.supplier import Supplier
from app.models.recipe import Recipe, RecipeLine


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuth:
    """Test authentication endpoints."""

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpass123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"

    def test_login_invalid_password(self, client: TestClient, test_user):
        """Test login with invalid password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_get_current_user(self, client: TestClient, auth_headers, test_user):
        """Test getting current user info."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == test_user.email


class TestSuppliers:
    """Test supplier endpoints."""

    def test_create_supplier(self, client: TestClient, auth_headers):
        """Test creating a supplier."""
        response = client.post(
            "/api/v1/suppliers/",
            json={"name": "New Supplier", "contact_phone": "+1234567890"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "New Supplier"

    def test_list_suppliers(self, client: TestClient, auth_headers, test_supplier):
        """Test listing suppliers."""
        response = client.get("/api/v1/suppliers/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestProducts:
    """Test product endpoints."""

    def test_create_product(self, client: TestClient, auth_headers, test_supplier):
        """Test creating a product."""
        response = client.post(
            "/api/v1/products/",
            json={
                "name": "New Product",
                "barcode": "9999999999999",
                "supplier_id": test_supplier.id,
                "pack_size": 12,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "New Product"

    def test_list_products(self, client: TestClient, auth_headers, test_product):
        """Test listing products."""
        response = client.get("/api/v1/products/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_product_by_barcode(self, client: TestClient, auth_headers, test_product):
        """Test getting product by barcode."""
        response = client.get(
            f"/api/v1/products/by-barcode/{test_product.barcode}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == test_product.id

    def test_import_products_csv(self, client: TestClient, auth_headers):
        """Test importing products from CSV."""
        csv_content = """name,barcode,supplier_name,pack_size,unit,min_stock,target_stock
Test Import Product,8888888888888,Import Supplier,24,pcs,10,100
Another Product,7777777777777,Import Supplier,12,pcs,5,50"""

        response = client.post(
            "/api/v1/products/import",
            files={"file": ("products.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["created"] == 2


class TestLocations:
    """Test location endpoints."""

    def test_create_location(self, client: TestClient, auth_headers):
        """Test creating a location."""
        response = client.post(
            "/api/v1/locations/",
            json={"name": "Storage Room", "description": "Back storage"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Storage Room"

    def test_list_locations(self, client: TestClient, auth_headers, test_location):
        """Test listing locations."""
        response = client.get("/api/v1/locations/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestInventory:
    """Test inventory session endpoints."""

    def test_create_session(self, client: TestClient, auth_headers, test_location):
        """Test creating an inventory session."""
        response = client.post(
            "/api/v1/inventory/sessions",
            json={"location_id": test_location.id, "notes": "Test session"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["status"] == "draft"

    def test_add_line_to_session(
        self, client: TestClient, auth_headers, test_location, test_product, db_session
    ):
        """Test adding a line to an inventory session."""
        # Create session
        session = InventorySession(
            location_id=test_location.id,
            status=SessionStatus.DRAFT,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        response = client.post(
            f"/api/v1/inventory/sessions/{session.id}/lines",
            json={
                "product_id": test_product.id,
                "counted_qty": 25,
                "method": "barcode",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert float(response.json()["counted_qty"]) == 25

    def test_commit_session(
        self, client: TestClient, auth_headers, test_location, test_product, db_session
    ):
        """Test committing an inventory session."""
        # Create session with line
        session = InventorySession(
            location_id=test_location.id,
            status=SessionStatus.DRAFT,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # Add line
        client.post(
            f"/api/v1/inventory/sessions/{session.id}/lines",
            json={
                "product_id": test_product.id,
                "counted_qty": 30,
                "method": "manual",
            },
            headers=auth_headers,
        )

        # Commit
        response = client.post(
            f"/api/v1/inventory/sessions/{session.id}/commit",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "committed"

        # Verify stock was updated
        stock = db_session.query(StockOnHand).filter(
            StockOnHand.product_id == test_product.id,
            StockOnHand.location_id == test_location.id,
        ).first()
        assert stock is not None
        assert stock.qty == Decimal("30")


class TestOrders:
    """Test order endpoints."""

    def test_get_order_suggestions(
        self, client: TestClient, auth_headers, test_location, test_product, db_session
    ):
        """Test getting order suggestions."""
        # Set stock below target
        stock = StockOnHand(
            product_id=test_product.id,
            location_id=test_location.id,
            qty=Decimal("5"),  # Below target of 50
        )
        db_session.add(stock)
        db_session.commit()

        response = client.get(
            f"/api/v1/orders/suggestions?location_id={test_location.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        suggestions = response.json()["suggestions"]
        assert len(suggestions) >= 1
        # Should suggest 45 units (50 - 5)
        suggestion = next(s for s in suggestions if s["product_id"] == test_product.id)
        assert float(suggestion["suggested_qty"]) == 45

    def test_create_order(
        self, client: TestClient, auth_headers, test_location, test_product, test_supplier
    ):
        """Test creating a purchase order."""
        response = client.post(
            "/api/v1/orders/",
            json={
                "supplier_id": test_supplier.id,
                "location_id": test_location.id,
                "lines": [{"product_id": test_product.id, "qty": 24}],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["status"] == "draft"
        assert len(response.json()["lines"]) == 1

    def test_export_order_whatsapp(
        self, client: TestClient, auth_headers, test_location, test_product, test_supplier, db_session
    ):
        """Test exporting order as WhatsApp text."""
        from app.models.order import PurchaseOrder, PurchaseOrderLine

        # Create order
        order = PurchaseOrder(
            supplier_id=test_supplier.id,
            location_id=test_location.id,
        )
        db_session.add(order)
        db_session.flush()

        line = PurchaseOrderLine(
            po_id=order.id,
            product_id=test_product.id,
            qty=Decimal("24"),
        )
        db_session.add(line)
        db_session.commit()

        response = client.get(
            f"/api/v1/orders/{order.id}/export/whatsapp",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "text" in response.json()
        assert "PURCHASE ORDER" in response.json()["text"]


class TestPOS:
    """Test POS integration endpoints."""

    def test_import_pos_csv(
        self, client: TestClient, auth_headers, test_location
    ):
        """Test importing POS sales from CSV."""
        csv_content = """timestamp,item_id,item_name,qty,is_refund
2024-01-15 12:00:00,BEER001,Corona Extra,2,false
2024-01-15 12:05:00,BEER001,Corona Extra,1,false
2024-01-15 12:10:00,WINE001,House Red Wine,1,false"""

        response = client.post(
            f"/api/v1/pos/import/csv?location_id={test_location.id}",
            files={"file": ("sales.csv", io.BytesIO(csv_content.encode()), "text/csv")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["rows_imported"] == 3

    def test_consume_sales(
        self, client: TestClient, auth_headers, test_location, test_product, db_session
    ):
        """Test converting sales to stock movements."""
        from app.models.pos import PosSalesLine
        from datetime import datetime

        # Create recipe for the product
        recipe = Recipe(
            name="Test Beer",
            pos_item_name="Test Beer",
        )
        db_session.add(recipe)
        db_session.flush()

        recipe_line = RecipeLine(
            recipe_id=recipe.id,
            product_id=test_product.id,
            qty=Decimal("1"),
            unit="pcs",
        )
        db_session.add(recipe_line)

        # Create unprocessed sales line
        sales_line = PosSalesLine(
            ts=datetime.utcnow(),
            name="Test Beer",
            qty=Decimal("3"),
            is_refund=False,
            location_id=test_location.id,
            processed=False,
        )
        db_session.add(sales_line)

        # Initialize stock
        stock = StockOnHand(
            product_id=test_product.id,
            location_id=test_location.id,
            qty=Decimal("100"),
        )
        db_session.add(stock)
        db_session.commit()

        response = client.post("/api/v1/pos/consume", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["sales_processed"] >= 1

        # Verify stock was reduced
        db_session.refresh(stock)
        assert stock.qty == Decimal("97")  # 100 - 3


class TestRecipes:
    """Test recipe endpoints."""

    def test_create_recipe(
        self, client: TestClient, auth_headers, test_product
    ):
        """Test creating a recipe."""
        response = client.post(
            "/api/v1/recipes/",
            json={
                "name": "Vodka Tonic",
                "pos_item_id": "VODKA_TONIC",
                "lines": [{"product_id": test_product.id, "qty": 0.05, "unit": "L"}],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Vodka Tonic"
        assert len(response.json()["lines"]) == 1


class TestAI:
    """Test AI shelf scan endpoints."""

    def test_shelf_scan(self, client: TestClient, auth_headers):
        """Test shelf scan with demo image."""
        # Create a simple test image (1x1 pixel PNG)
        import base64
        # Minimal PNG
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        response = client.post(
            "/api/v1/ai/shelf-scan",
            files={"image": ("test.png", io.BytesIO(png_data), "image/png")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "detections" in response.json()
        assert "meta" in response.json()


class TestSync:
    """Test sync endpoints."""

    def test_sync_pull(self, client: TestClient, auth_headers, test_product, test_supplier, test_location):
        """Test sync pull endpoint."""
        response = client.get("/api/v1/sync/pull", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "suppliers" in data
        assert "locations" in data
        assert "server_timestamp" in data
