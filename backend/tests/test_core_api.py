"""Comprehensive tests for core API endpoints."""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.core.rbac import UserRole
from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.location import Location
from app.models.inventory import InventorySession, InventoryLine, SessionStatus, CountMethod
from app.models.stock import StockOnHand


# ==================== AUTH TESTS ====================

class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_login_success(self, client: TestClient, db_session, test_user):
        """Test successful login with email/password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpass123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client: TestClient, db_session, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_invalid_email(self, client: TestClient, db_session):
        """Test login with non-existent email."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "anypass"}
        )
        assert response.status_code == 401

    def test_login_inactive_user(self, client: TestClient, db_session):
        """Test login with inactive user account."""
        user = User(
            email="inactive@example.com",
            password_hash=get_password_hash("testpass123"),
            role=UserRole.STAFF,
            name="Inactive User",
            is_active=False,
        )
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": "testpass123"}
        )
        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()

    def test_login_pin_success(self, client: TestClient, db_session):
        """Test successful PIN login."""
        user = User(
            email="pinuser@example.com",
            password_hash=get_password_hash("testpass123"),
            role=UserRole.STAFF,
            name="PIN User",
            is_active=True,
            pin="1234",
        )
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login/pin",
            json={"pin": "1234"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_pin_invalid(self, client: TestClient, db_session):
        """Test PIN login with invalid PIN."""
        response = client.post(
            "/api/v1/auth/login/pin",
            json={"pin": "9999"}
        )
        assert response.status_code == 401

    def test_get_current_user(self, client: TestClient, db_session, auth_headers, test_user):
        """Test getting current user info."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"

    def test_get_current_user_unauthenticated(self, client: TestClient, db_session):
        """Test getting current user without auth."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code in [401, 403]  # Both are valid for missing auth

    def test_register_first_user(self, client: TestClient, db_session):
        """Test registering first user."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "owner@example.com",
                "password": "securepass123",
                "name": "Owner",
                "role": "owner"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "owner@example.com"

    def test_register_blocked_after_first_user(self, client: TestClient, db_session, test_user):
        """Test that registration is blocked after first user."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "second@example.com",
                "password": "securepass123",
                "name": "Second User",
                "role": "staff"
            }
        )
        assert response.status_code == 403


# ==================== PRODUCT TESTS ====================

class TestProductEndpoints:
    """Test product management endpoints."""

    def test_list_products_empty(self, client: TestClient, db_session, auth_headers):
        """Test listing products when none exist."""
        response = client.get("/api/v1/products/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_products(self, client: TestClient, db_session, auth_headers, test_product):
        """Test listing products."""
        response = client.get("/api/v1/products/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Beer"

    def test_list_products_filter_by_supplier(self, client: TestClient, db_session, auth_headers, test_product, test_supplier):
        """Test filtering products by supplier."""
        response = client.get(
            f"/api/v1/products/?supplier_id={test_supplier.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        # Non-existent supplier
        response = client.get("/api/v1/products/?supplier_id=9999", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_products_search(self, client: TestClient, db_session, auth_headers, test_product):
        """Test searching products by name."""
        response = client.get("/api/v1/products/?search=Beer", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        response = client.get("/api/v1/products/?search=Wine", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_products_active_only(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test filtering active/inactive products."""
        # Create active and inactive products
        active_product = Product(
            name="Active Product",
            barcode="1111111111111",
            supplier_id=test_supplier.id,
            active=True,
        )
        inactive_product = Product(
            name="Inactive Product",
            barcode="2222222222222",
            supplier_id=test_supplier.id,
            active=False,
        )
        db_session.add_all([active_product, inactive_product])
        db_session.commit()

        # Active only (default)
        response = client.get("/api/v1/products/", headers=auth_headers)
        assert len(response.json()) == 1

        # All products
        response = client.get("/api/v1/products/?active_only=false", headers=auth_headers)
        assert len(response.json()) == 2

    def test_get_product_by_id(self, client: TestClient, db_session, auth_headers, test_product):
        """Test getting a product by ID."""
        response = client.get(f"/api/v1/products/{test_product.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Beer"
        assert data["barcode"] == "1234567890123"

    def test_get_product_not_found(self, client: TestClient, db_session, auth_headers):
        """Test getting non-existent product."""
        response = client.get("/api/v1/products/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_product_by_barcode(self, client: TestClient, db_session, auth_headers, test_product):
        """Test getting a product by barcode."""
        response = client.get(
            f"/api/v1/products/by-barcode/{test_product.barcode}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["id"] == test_product.id

    def test_get_product_by_barcode_not_found(self, client: TestClient, db_session, auth_headers):
        """Test getting product by non-existent barcode."""
        response = client.get("/api/v1/products/by-barcode/0000000000000", headers=auth_headers)
        assert response.status_code == 404

    def test_create_product(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test creating a product."""
        response = client.post(
            "/api/v1/products/",
            headers=auth_headers,
            json={
                "name": "New Wine",
                "barcode": "9876543210123",
                "supplier_id": test_supplier.id,
                "pack_size": 12,
                "unit": "btl",
                "min_stock": "5",
                "target_stock": "20",
                "cost_price": "8.50",
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Wine"
        assert data["barcode"] == "9876543210123"

    def test_create_product_duplicate_barcode(self, client: TestClient, db_session, auth_headers, test_product):
        """Test creating product with duplicate barcode."""
        response = client.post(
            "/api/v1/products/",
            headers=auth_headers,
            json={
                "name": "Another Beer",
                "barcode": test_product.barcode,  # Duplicate
            }
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_product_minimal(self, client: TestClient, db_session, auth_headers):
        """Test creating product with minimal data."""
        response = client.post(
            "/api/v1/products/",
            headers=auth_headers,
            json={"name": "Minimal Product"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Product"
        assert data["barcode"] is None

    def test_update_product(self, client: TestClient, db_session, auth_headers, test_product):
        """Test updating a product."""
        response = client.put(
            f"/api/v1/products/{test_product.id}",
            headers=auth_headers,
            json={"name": "Updated Beer", "min_stock": "15"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Beer"
        assert float(data["min_stock"]) == 15.0

    def test_update_product_not_found(self, client: TestClient, db_session, auth_headers):
        """Test updating non-existent product."""
        response = client.put(
            "/api/v1/products/9999",
            headers=auth_headers,
            json={"name": "New Name"}
        )
        assert response.status_code == 404

    def test_update_product_duplicate_barcode(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test updating product with duplicate barcode."""
        product1 = Product(name="Product 1", barcode="1111111111111", supplier_id=test_supplier.id)
        product2 = Product(name="Product 2", barcode="2222222222222", supplier_id=test_supplier.id)
        db_session.add_all([product1, product2])
        db_session.commit()

        response = client.put(
            f"/api/v1/products/{product2.id}",
            headers=auth_headers,
            json={"barcode": "1111111111111"}  # Duplicate
        )
        assert response.status_code == 400

    def test_smart_search(self, client: TestClient, db_session, auth_headers, test_product):
        """Test smart product search."""
        response = client.get(
            "/api/v1/products/search/smart?q=Beer",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1

    def test_smart_search_by_barcode(self, client: TestClient, db_session, auth_headers, test_product):
        """Test smart search by barcode."""
        response = client.get(
            f"/api/v1/products/search/smart?q={test_product.barcode}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1

    def test_product_match(self, client: TestClient, db_session, auth_headers, test_product):
        """Test product matching endpoint."""
        response = client.post(
            f"/api/v1/products/match?barcode={test_product.barcode}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == test_product.id
        assert data["match_method"] == "barcode"


# ==================== INVENTORY TESTS ====================

class TestInventoryEndpoints:
    """Test inventory management endpoints."""

    def test_create_session(self, client: TestClient, db_session, auth_headers, test_location):
        """Test creating an inventory session."""
        response = client.post(
            "/api/v1/inventory/sessions",
            headers=auth_headers,
            json={
                "location_id": test_location.id,
                "notes": "Weekly count"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["location_id"] == test_location.id
        assert data["status"] == "draft"

    def test_create_session_invalid_location(self, client: TestClient, db_session, auth_headers):
        """Test creating session with invalid location."""
        response = client.post(
            "/api/v1/inventory/sessions",
            headers=auth_headers,
            json={"location_id": 9999}
        )
        assert response.status_code == 404

    def test_list_sessions(self, client: TestClient, db_session, auth_headers, test_location):
        """Test listing inventory sessions."""
        # Create sessions
        session1 = InventorySession(location_id=test_location.id, created_by=1)
        session2 = InventorySession(location_id=test_location.id, created_by=1, status=SessionStatus.COMMITTED)
        db_session.add_all([session1, session2])
        db_session.commit()

        response = client.get("/api/v1/inventory/sessions", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_list_sessions_filter_by_status(self, client: TestClient, db_session, auth_headers, test_location):
        """Test filtering sessions by status."""
        session = InventorySession(location_id=test_location.id, created_by=1, status=SessionStatus.DRAFT)
        db_session.add(session)
        db_session.commit()

        response = client.get("/api/v1/inventory/sessions?status=draft", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(s["status"] == "draft" for s in data)

    def test_get_session(self, client: TestClient, db_session, auth_headers, test_location):
        """Test getting a specific session."""
        session = InventorySession(location_id=test_location.id, created_by=1)
        db_session.add(session)
        db_session.commit()

        response = client.get(f"/api/v1/inventory/sessions/{session.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == session.id

    def test_get_session_not_found(self, client: TestClient, db_session, auth_headers):
        """Test getting non-existent session."""
        response = client.get("/api/v1/inventory/sessions/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_add_line_to_session(self, client: TestClient, db_session, auth_headers, test_location, test_product):
        """Test adding a line to an inventory session."""
        session = InventorySession(location_id=test_location.id, created_by=1)
        db_session.add(session)
        db_session.commit()

        response = client.post(
            f"/api/v1/inventory/sessions/{session.id}/lines",
            headers=auth_headers,
            json={
                "product_id": test_product.id,
                "counted_qty": "25.5",
                "method": "barcode",  # Valid enum: barcode, ai, manual
                "confidence": 0.95
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["product_id"] == test_product.id
        assert float(data["counted_qty"]) == 25.5

    def test_add_line_product_not_found(self, client: TestClient, db_session, auth_headers, test_location):
        """Test adding line with non-existent product."""
        session = InventorySession(location_id=test_location.id, created_by=1)
        db_session.add(session)
        db_session.commit()

        response = client.post(
            f"/api/v1/inventory/sessions/{session.id}/lines",
            headers=auth_headers,
            json={"product_id": 9999, "counted_qty": "10"}
        )
        assert response.status_code == 404

    def test_add_line_to_committed_session(self, client: TestClient, db_session, auth_headers, test_location, test_product):
        """Test adding line to committed session fails."""
        session = InventorySession(
            location_id=test_location.id,
            created_by=1,
            status=SessionStatus.COMMITTED
        )
        db_session.add(session)
        db_session.commit()

        response = client.post(
            f"/api/v1/inventory/sessions/{session.id}/lines",
            headers=auth_headers,
            json={"product_id": test_product.id, "counted_qty": "10"}
        )
        assert response.status_code == 400

    def test_add_duplicate_line_updates_existing(self, client: TestClient, db_session, auth_headers, test_location, test_product):
        """Test adding line for same product updates existing line."""
        session = InventorySession(location_id=test_location.id, created_by=1)
        db_session.add(session)
        db_session.commit()

        # Add first line
        response1 = client.post(
            f"/api/v1/inventory/sessions/{session.id}/lines",
            headers=auth_headers,
            json={"product_id": test_product.id, "counted_qty": "10"}
        )
        assert response1.status_code == 201

        # Add second line for same product - should add to qty
        response2 = client.post(
            f"/api/v1/inventory/sessions/{session.id}/lines",
            headers=auth_headers,
            json={"product_id": test_product.id, "counted_qty": "5"}
        )
        assert response2.status_code == 201
        assert float(response2.json()["counted_qty"]) == 15  # 10 + 5

    def test_update_line(self, client: TestClient, db_session, auth_headers, test_location, test_product):
        """Test updating an inventory line."""
        session = InventorySession(location_id=test_location.id, created_by=1)
        db_session.add(session)
        db_session.commit()

        line = InventoryLine(
            session_id=session.id,
            product_id=test_product.id,
            counted_qty=Decimal("10"),
            method=CountMethod.MANUAL,
        )
        db_session.add(line)
        db_session.commit()

        response = client.put(
            f"/api/v1/inventory/sessions/{session.id}/lines/{line.id}",
            headers=auth_headers,
            json={"counted_qty": "20"}
        )
        assert response.status_code == 200
        assert float(response.json()["counted_qty"]) == 20

    def test_delete_line(self, client: TestClient, db_session, auth_headers, test_location, test_product):
        """Test deleting an inventory line."""
        session = InventorySession(location_id=test_location.id, created_by=1)
        db_session.add(session)
        db_session.commit()

        line = InventoryLine(
            session_id=session.id,
            product_id=test_product.id,
            counted_qty=Decimal("10"),
        )
        db_session.add(line)
        db_session.commit()

        response = client.delete(
            f"/api/v1/inventory/sessions/{session.id}/lines/{line.id}",
            headers=auth_headers
        )
        assert response.status_code == 204

    def test_commit_session(self, client: TestClient, db_session, auth_headers, test_location, test_product):
        """Test committing an inventory session."""
        session = InventorySession(location_id=test_location.id, created_by=1)
        db_session.add(session)
        db_session.commit()

        line = InventoryLine(
            session_id=session.id,
            product_id=test_product.id,
            counted_qty=Decimal("50"),
        )
        db_session.add(line)
        db_session.commit()

        response = client.post(
            f"/api/v1/inventory/sessions/{session.id}/commit",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "committed"
        assert data["movements_created"] >= 0

    def test_commit_empty_session(self, client: TestClient, db_session, auth_headers, test_location):
        """Test committing session with no lines fails."""
        session = InventorySession(location_id=test_location.id, created_by=1)
        db_session.add(session)
        db_session.commit()

        response = client.post(
            f"/api/v1/inventory/sessions/{session.id}/commit",
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_commit_already_committed_session(self, client: TestClient, db_session, auth_headers, test_location):
        """Test committing already committed session fails."""
        session = InventorySession(
            location_id=test_location.id,
            created_by=1,
            status=SessionStatus.COMMITTED
        )
        db_session.add(session)
        db_session.commit()

        response = client.post(
            f"/api/v1/inventory/sessions/{session.id}/commit",
            headers=auth_headers
        )
        assert response.status_code == 400


# ==================== SUPPLIER TESTS ====================

class TestSupplierEndpoints:
    """Test supplier management endpoints."""

    def test_list_suppliers(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test listing suppliers."""
        response = client.get("/api/v1/suppliers/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_get_supplier(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test getting a specific supplier."""
        response = client.get(f"/api/v1/suppliers/{test_supplier.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Test Supplier"

    def test_create_supplier(self, client: TestClient, db_session, auth_headers):
        """Test creating a supplier."""
        response = client.post(
            "/api/v1/suppliers/",
            headers=auth_headers,
            json={
                "name": "New Supplier",
                "contact_email": "new@supplier.com",
                "contact_phone": "+1234567890"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Supplier"

    def test_update_supplier(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test updating a supplier."""
        response = client.put(
            f"/api/v1/suppliers/{test_supplier.id}",
            headers=auth_headers,
            json={"name": "Updated Supplier"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Supplier"


# ==================== LOCATION TESTS ====================

class TestLocationEndpoints:
    """Test location management endpoints."""

    def test_list_locations(self, client: TestClient, db_session, auth_headers, test_location):
        """Test listing locations."""
        response = client.get("/api/v1/locations/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_get_location(self, client: TestClient, db_session, auth_headers, test_location):
        """Test getting a specific location."""
        response = client.get(f"/api/v1/locations/{test_location.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Main Bar"

    def test_create_location(self, client: TestClient, db_session, auth_headers):
        """Test creating a location."""
        response = client.post(
            "/api/v1/locations/",
            headers=auth_headers,
            json={
                "name": "Storage Room",
                "description": "Back storage area"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Storage Room"

    def test_update_location(self, client: TestClient, db_session, auth_headers, test_location):
        """Test updating a location."""
        response = client.put(
            f"/api/v1/locations/{test_location.id}",
            headers=auth_headers,
            json={"name": "Updated Bar"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Bar"


# ==================== INTEGRATION TESTS ====================

class TestIntegrationWorkflows:
    """Test end-to-end workflows."""

    def test_complete_inventory_workflow(self, client: TestClient, db_session, auth_headers, test_location, test_supplier):
        """Test complete inventory counting workflow."""
        # 1. Create products
        product1 = Product(name="Beer A", barcode="1111111111111", supplier_id=test_supplier.id)
        product2 = Product(name="Beer B", barcode="2222222222222", supplier_id=test_supplier.id)
        db_session.add_all([product1, product2])
        db_session.commit()

        # 2. Create initial stock
        stock1 = StockOnHand(product_id=product1.id, location_id=test_location.id, qty=Decimal("100"))
        stock2 = StockOnHand(product_id=product2.id, location_id=test_location.id, qty=Decimal("50"))
        db_session.add_all([stock1, stock2])
        db_session.commit()

        # 3. Create inventory session
        response = client.post(
            "/api/v1/inventory/sessions",
            headers=auth_headers,
            json={"location_id": test_location.id, "notes": "Monthly count"}
        )
        assert response.status_code == 201
        session_id = response.json()["id"]

        # 4. Add counted lines
        response = client.post(
            f"/api/v1/inventory/sessions/{session_id}/lines",
            headers=auth_headers,
            json={"product_id": product1.id, "counted_qty": "95"}
        )
        assert response.status_code == 201

        response = client.post(
            f"/api/v1/inventory/sessions/{session_id}/lines",
            headers=auth_headers,
            json={"product_id": product2.id, "counted_qty": "55"}
        )
        assert response.status_code == 201

        # 5. Commit session
        response = client.post(
            f"/api/v1/inventory/sessions/{session_id}/commit",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "committed"
        assert data["movements_created"] == 2  # Two adjustments

        # 6. Verify stock was updated
        db_session.refresh(stock1)
        db_session.refresh(stock2)
        assert stock1.qty == Decimal("95")
        assert stock2.qty == Decimal("55")

    def test_product_search_workflow(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test product search and matching workflow."""
        # Create products with various attributes
        products = [
            Product(name="Corona Extra", barcode="7501064191008", supplier_id=test_supplier.id),
            Product(name="Corona Light", barcode="7501064191015", supplier_id=test_supplier.id),
            Product(name="Heineken", barcode="8711327000010", supplier_id=test_supplier.id),
        ]
        db_session.add_all(products)
        db_session.commit()

        # Test exact barcode match
        response = client.post(
            "/api/v1/products/match?barcode=7501064191008",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["product_name"] == "Corona Extra"
        assert response.json()["match_method"] == "barcode"

        # Test fuzzy name search
        response = client.get(
            "/api/v1/products/search/smart?q=corona",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["count"] == 2  # Both Corona products

        # Test name matching
        response = client.post(
            "/api/v1/products/match?name=Heineken",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["product_name"] == "Heineken"

    def test_multi_location_inventory(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test inventory across multiple locations."""
        # Create locations
        loc1 = Location(name="Bar 1", is_default=True, active=True)
        loc2 = Location(name="Bar 2", is_default=False, active=True)
        db_session.add_all([loc1, loc2])
        db_session.commit()

        # Create product
        product = Product(name="Vodka", barcode="1234567890", supplier_id=test_supplier.id)
        db_session.add(product)
        db_session.commit()

        # Create stock in both locations
        stock1 = StockOnHand(product_id=product.id, location_id=loc1.id, qty=Decimal("20"))
        stock2 = StockOnHand(product_id=product.id, location_id=loc2.id, qty=Decimal("15"))
        db_session.add_all([stock1, stock2])
        db_session.commit()

        # Count inventory at location 1
        response = client.post(
            "/api/v1/inventory/sessions",
            headers=auth_headers,
            json={"location_id": loc1.id}
        )
        session_id = response.json()["id"]

        response = client.post(
            f"/api/v1/inventory/sessions/{session_id}/lines",
            headers=auth_headers,
            json={"product_id": product.id, "counted_qty": "18"}
        )
        assert response.status_code == 201

        response = client.post(
            f"/api/v1/inventory/sessions/{session_id}/commit",
            headers=auth_headers
        )
        assert response.status_code == 200

        # Verify only location 1 stock was affected
        db_session.refresh(stock1)
        db_session.refresh(stock2)
        assert stock1.qty == Decimal("18")
        assert stock2.qty == Decimal("15")  # Unchanged


# ==================== ERROR HANDLING TESTS ====================

class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_invalid_json(self, client: TestClient, db_session, auth_headers):
        """Test handling of invalid JSON."""
        response = client.post(
            "/api/v1/products/",
            headers={**auth_headers, "Content-Type": "application/json"},
            content="invalid json"
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client: TestClient, db_session, auth_headers):
        """Test handling of missing required fields."""
        response = client.post(
            "/api/v1/products/",
            headers=auth_headers,
            json={}  # Missing required 'name'
        )
        assert response.status_code == 422

    def test_invalid_field_types(self, client: TestClient, db_session, auth_headers):
        """Test handling of invalid field types."""
        response = client.post(
            "/api/v1/products/",
            headers=auth_headers,
            json={"name": "Test", "pack_size": "not a number"}
        )
        assert response.status_code == 422

    def test_unauthenticated_access(self, client: TestClient, db_session):
        """Test accessing protected endpoints without auth."""
        response = client.get("/api/v1/products/")
        assert response.status_code in [401, 403]  # Both valid for missing auth

    def test_invalid_token(self, client: TestClient, db_session):
        """Test accessing endpoints with invalid token."""
        response = client.get(
            "/api/v1/products/",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


# ==================== PAGINATION TESTS ====================

class TestPagination:
    """Test pagination on list endpoints."""

    def test_product_list_pagination(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test product listing with many products."""
        # Create many products
        products = [
            Product(name=f"Product {i}", barcode=f"{i:013d}", supplier_id=test_supplier.id)
            for i in range(50)
        ]
        db_session.add_all(products)
        db_session.commit()

        response = client.get("/api/v1/products/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 50

    def test_smart_search_limit(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test smart search respects limit parameter."""
        products = [
            Product(name=f"Beer {i}", supplier_id=test_supplier.id)
            for i in range(20)
        ]
        db_session.add_all(products)
        db_session.commit()

        response = client.get(
            "/api/v1/products/search/smart?q=Beer&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["count"] <= 5
